"""
scraper.py

Basic webscraper, extracts some og content, plain text, and html formatted text with no attributes
"""

from bs4 import BeautifulSoup, Comment
import logging
import re
import requests

log = logging.getLogger('noozli')

"""
Domain specific scrapers, assume the text has already been soup'ed

Modifies and returns existing soup for continued use in main scraper
"""
# look for <p> section made up primarily of tags and remove
def extract_p_tags(soup, tags_list):
    """
    tags_list:  list of strings for html tag types to remove in partial '<a' or complete '<i>' form
    """

    for p in soup.find_all('p'):
        string_rep = str(p)
        found_p = True

        for tag in tags_list:
            if tag not in string_rep:
                found_p = False

        if found_p:

            to_extract = []
            for child in p.descendants:
                for tag in tags_list:
                    if str(child).find(tag) == 0:
                        to_extract.append(str(child))

            for tag in to_extract:
                string_rep = string_rep.replace(tag, '')
                
            remaining_text = BeautifulSoup(string_rep).get_text().lower()
            
            if len(remaining_text) <= 2 or (re.match('photos|watch|more from|bonus', remaining_text) and len(remaining_text) <= 30):
                p.extract()

    return soup


def cnn_scraper(soup):

    for div in soup.find_all('div', class_=re.compile('c_sharetitle|c_shareweb|share|cnnByline|cnn_strytmstmp|cnn_strylctcntr|cnn_strylftcntnt|cnnTitle|cnnCoverage|cnn_html_media_title|(a|A)rticleGallery|cnn_stryspcvh|cnn_cb_lc')):
        div.extract()

    for p in soup.find_all('p', class_=re.compile('cnnEditorialNote')):
        p.extract()

    # cnn sometimes embeds links as paragraphs in a story
    for p in soup.find_all('p', class_=re.compile('cnn_storypgraph')):
        string_rep = str(p)
        if '<a href' in string_rep:
            new_string = string_rep.replace(str(p.a), '')
            if len(BeautifulSoup(new_string).get_text()) <= 2:
                p.extract()

    # cnn occasionally uses h1 for non story items
    for header in soup.find_all('h1'):
        header.extract()

    return soup

def foxnews(soup):

    soup = extract_p_tags(soup, ['<a '])

    for div in soup.find_all('div', class_=re.compile('fb-post')):
        div.extract()

    return soup


def abcnews(soup):
    
    soup = extract_p_tags(soup, ['<a '])
    soup = extract_p_tags(soup, ['<strong>', '<a '])

    for header in soup.find_all('h6'):
        header.extract()

    return soup


def mashable(soup):

    soup = extract_p_tags(soup, ['<strong>', '<a '])
    soup = extract_p_tags(soup, ['<em>'])

    return soup


def scraper(url, debug=False):
    """
    params:  url - string that is link to a webpage

    returns:  tuple (full_text:string, image_url:string, display_text:string)
              image_url will be None if an og:image tag is not found
              
              returns None if an error occured
    """

    try:
        r = requests.get(url)
    except:
        log.warning('Failed to connect to ' + url)
        return None
    
    if r.status_code != 200:
        log.info('Error scraping webpage: ' + url)
        return None

    
    # fix abc news articles on multiple pages
    if 'abcnews.go.com' in url:
        soup = BeautifulSoup(r.text)
        for a in soup.find_all('a'):
            if a.get_text().lower() == 'view single page':

                try:
                    a_str = str(a)
                    href_ind = a_str.find('href')
                    start_ind = href_ind + 5

                    other_inds = [i for i, letter in enumerate(a_str) if letter == '"']
                    for ind in other_inds:
                        if ind > start_ind:
                            end_ind = ind
                            break

                    single_page_url = a_str[start_ind:end_ind+1].rstrip('"').lstrip('"')
                    single_page_url = 'http://www.abcnews.go.com' + single_page_url.replace('&amp;', '&')
                    r = requests.get(single_page_url)

                except:
                    log.warning('Failed to connect to ' + single_page_url)
                    return None

                if r.status_code != 200:
                    log.info('Error scraping webpage: ' + single_page_url)
                    return None


    p_regex = re.compile("</p>")
    raw_text = p_regex.sub('</p>\n', r.text)
    soup = BeautifulSoup(raw_text)

    final_text = ''
    display_text = ''

    """
    #
    # Process tags
    #
    """
    
    try:
        og_url = soup.find('meta', {'property': 'og:url'})['content']
    except Exception as e:
        log.debug('no og:url tag for ' + url)
        og_url = None

    try:
        value = soup.find('meta', {'property': 'og:type'})['content']
        
        if 'video' in value:
            if og_url is not None:
                log.debug('found video at ' + og_url)
            else:
                log.debug('found video at ' + url)

            final_text = None
            display_text = None


    except Exception as e:
        if og_url is not None:
            log.debug('no og:type tag for ' + og_url)
        else:
            log.debug('no og:type tag for ' + url)

    try:
        og_title = soup.find('meta', {'property': 'og:title'})['content']
        
        search_obj = re.search('\d+ of \d+|\d+.+photo(s)?', og_title)

        found_slideshow = False
        if 'cnn_gallery_images' in raw_text:
            found_slideshow = True

        if search_obj or found_slideshow:
            if og_url is not None:
                log.debug('possible photo slide show at ' + og_url + ' skipping.')
            else:
                log.debug('possible photo slide show at ' + url + ' skipping.')
            final_text = None
            display_text = None

    except Exception as e:
        log.debug('no og:title field found for ' + url)
    
    try:
        image = soup.find('meta', {'property': 'og:image'})['content']
    except Exception as e:
        if og_url is not None:
            log.debug('no og:image for ' + og_url)
        else:
            log.debug('no og:image for ' + url)
        image = None


    """
    #
    # Domain specific issues where article should be skipped
    #
    """
    
    divs = soup.find_all('div', id=re.compile('skrollr-body'))
    if len(divs) > 0:
        log.debug('Found scrolling body type on Mashable.  Skipping.  ' + url)
        final_text = None
        display_text = None

    if 'businessinsider.com' in url:
        divs = soup.find_all('div', class_=re.compile('slideshow'))
        if len(divs) > 0:
            if og_url is not None:
                log.debug('Found slideshow at:  ' + og_url)
            else:
                log.debug('Found slideshow at:  ' + og_url)
            final_text = None
            display_text = None
        
    if 'abcnews.go.com' in url:
        if 'wireStory' in url or 'photos' in url or "<div id='listItems'>" in raw_text:
            final_text = None
            display_text = None


    if og_url is not None and re.search('abcnews\.go\.com/[A-Za-z]*[/]?$', og_url):
        final_text = None
        display_text = None


    # return if there are any errors or bad article type
    if final_text is None:
        return (final_text, image, display_text, og_url)


    """
    #
    # Remove domain specific content
    #
    """

    if 'cnn.com' in url:
        soup = cnn_scraper(soup)

    if 'foxnews.com' in url:
        soup = foxnews(soup)

    if 'abcnews.go.com' in url:
        soup = abcnews(soup)

    if 'mashable' in url:
        soup = mashable(soup)

    """
    #
    # Remove content in main text regions
    #
    # NOTE: have not simplified all regex's yet.  leave til end
    """

    # some scripts showing up in mashable, strip all scripts
    for script in soup.find_all('script'):
        script.extract()

    for aside in soup.find_all('aside'):
        aside.extract()

    for span in soup.find_all('span', class_=re.compile('credit|vishidden')):
        span.extract()

    for div in soup.find_all('div', class_=re.compile('(caption|credit|bucketblock|see(-)?also|bonus|headline-author|date|social-buttons|share|embederror)')):
        div.extract()

    for div in soup.find_all('div', id=re.compile('(caption|credit|bucketblock|see(-)?also|bonus)')):
        div.extract()

    for div in soup.find_all('div', class_=re.compile('imagewrap')):
        div.extract()
                                     
    for div in soup.find_all('div', class_=re.compile('slide-intro|follow-us|ctrl')):
        div.extract()

    for p in soup.find_all('p', class_=re.compile('(source|caption|advert-txt)')):
        p.extract()

    for sec in soup.find_all('section', class_=re.compile('gallery')):
        sec.extract()

    for area in soup.find_all('textarea', id=re.compile('embed')):
        area.extract()

    for a in soup.find_all('a', id=re.compile('copy')):
        a.extract()
    
    # cnn specific  - maybe leave here, could show up elsewhere
    for style in soup.find_all('style'):
        style.extract()
    

    """
    #
    # find text
    # 
    """

    text = soup.find_all('div', class_=re.compile('(intro|entry|post|article|stack-l)-(content|entry)'))

    # text may be in 'section' tag rather than 'div'
    if len(text) == 0:
        text = soup.find_all('section', class_=re.compile('(intro|entry|post|article)-(content|entry)'))

    if len(text) == 0:
        text = soup.find_all('div', class_=re.compile('(story)(-)?text'))

        # some npr pages split the text into two different sections
        #if len(text) == 2 and url.find('npr.org') >= 0:
        #    return (text[0].get_text() + text[1].get_text(), image)

    if len(text) == 0:
        text = soup.find_all('div', class_=re.compile('(content)-main|cnn_storyarea'))

    if len(text) == 0:
        text = soup.find_all('div', itemprop=re.compile('articleBody'))

    if len(text) == 0:
        text = soup.find_all('div', id=re.compile('storyText'))


# for huffpo, but not getting any text back
#    if len(text) == 0:
#        text = soup.find_all('div', id=re.compile('mainentrycontent'))


    if len(text) != 1:
        if debug:
            import pdb
            pdb.set_trace()
        log.warning("Found multiple text divs on: " + url)
        final_text = None
        display_text = None
        return (final_text, image, display_text, og_url)


    """
    #
    # domain specific post cleaning
    #
    """


    """
    #
    # text clean
    #
    """

    full_text = text[0].get_text()

    line_breaks = re.compile('\r')
    final_text = line_breaks.sub('\n', full_text)

    spacing_regex = re.compile('\n+')
    final_text = spacing_regex.sub('\n\n', final_text)

    nbsp_regex = re.compile('\xa0|&nbsp[;]?')
    final_text = nbsp_regex.sub(' ', final_text)


    """
    #
    # Clean html formatted text
    #
    """
    
    display_soup = BeautifulSoup(str(text[0]))

    for img in display_soup.find_all('img'):
        img.extract()

    for tag in display_soup.findAll(True):
        # remove empty divs and empty paragraphs
        if len(tag.get_text()) == 0 or tag.get_text().isspace():
            tag.extract()
        
        # remove all attributes except href
        if 'href' in tag.attrs:
            tag.attrs = {'href': tag.attrs['href']}
        else:
            tag.attrs = []

    # remove comments
    comments = display_soup.findAll(text=lambda text:isinstance(text, Comment))
    for comment in comments:
        comment.extract()

    display_text = str(display_soup)
    line_break = re.compile('\n+')
    display_text = line_break.sub('', display_text)


    # fix for bad characters on some fox news articles, show up as lower case and upper case A with hat accent
    bad_chars = re.compile('\xe2|\x80|\x93|\xc2|\xa0')
    display_text = bad_chars.sub('', display_text)

    # skip short articles
    if len(final_text) < 500:
        return (None, image, None, og_url)

    return (final_text.lstrip().rstrip(), image, display_text, og_url)
