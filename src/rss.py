# rss.py
#
# Parse rss feeds, extract article text from webpages, run NLP categorization on documents
#

from PIL import Image
import datetime
import feedparser
import hashlib
import io
import json
import logging
import numpy as np
from pymongo import MongoClient
import pytz
import re
import requests
import time
import urllib
from urllib.parse import urlparse

import logger
import scraper

from bs4 import BeautifulSoup, Comment

with open('../config/keys.json', 'r') as keys_f:
    keys = json.loads(keys_f.read())

with open('../config/server.json', 'r') as addr_f:
    addr = json.loads(addr_f.read())['address']
    
textrazor_api_key = keys['textrazor_api_key']

log = logging.getLogger('noozli')
log.setLevel(logging.INFO)
if not log.handlers:
    log.addHandler(logger.NoozliHandler())
#    log.addHandler(logger.NoozliStreamingHandler())


def resize_and_store_image(url, article_id, root_dir='/home/ubuntu/images'):

    try:
        datafile = io.BytesIO(urllib.request.urlopen(url).read())
    except urllib.error.HTTPError:
        return None
    
    try:        
        img = Image.open(datafile)
    except OSError:
        return None

    file_type = url.split('.')[-1]
    if file_type == 'png' and (img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)):
        
        premult = np.fromstring(img.tostring(), dtype=np.uint8)
        alphaLayer = premult[3::4] / 255
        premult[::4] *= alphaLayer
        premult[1::4] *= alphaLayer
        premult[2::4] *= alphaLayer
        img = Image.fromstring('RGBA', img.size, premult.tostring())
        
    else:
        img = img.convert('RGB')
    
    (width, height) = img.size

    ratio = 640.0 / width
    img = img.resize((640, round(ratio*height)), Image.ANTIALIAS)

    if file_type == 'png':
        img.save(root_dir+'/'+article_id+'.png', 'PNG')
        return addr+'images/'+article_id+'.png'
    else:
        img.save(root_dir+'/'+article_id+'.jpg', 'JPEG')
        return addr+'images/'+article_id+'.jpg'

                  

def textrazor_categorization(text):
    """
    params:   text - string containing a document

    returns:  coarse topic labels for the text document found using the TextRazor API
    """

    r = requests.post('https://api.textrazor.com', data={'apiKey': textrazor_api_key, 'extractors': 'topics', 'text': text})

    if r.json()['ok']:
        try:
            ct = r.json()['response']['coarseTopics']
        except KeyError:
            log.info('did not find any coarse topics.')
            return None
    else:
        log.warning('textrazor call failed.')
        return None
    
    try:
        return [ (topic['label'], topic['score']) for topic in ct ]
    except AttributeError as e:
        log.info("textrazor_categorization:  did not find coarse topics")
        return None



# ttl syntax collection-wide
# collection.ensure_index('timestamp', expireAfterSeconds=2592000)
#    index is timestamp_1
#    30 days expiry time = 2592000
#
def parse_feed(url, debug=False, mode='streaming'):
    """
    params:  url - string for the location of an RSS feed

    returns:  writes all new articles in feed to mongo db with all relevant noozli data
    """

    feed = feedparser.parse(url)

    if len(feed['entries']) == 0:
        log.info("No items in feed: " + url)
        return None

    try:
        client = MongoClient('localhost', 27017)
    except Exception as e:
        log.warning('Failed to connect to mongo.')

    db = client.noozli


    if mode == 'prototype':
        collection = db.prototype
    else:
        collection = db.streaming

    
    if 'npr.org' in url:
        source = 'NPR - ' + feed['feed']['title']
    else:
        source = feed['feed']['title']

    # normalize fox news source
    if source == "FOXNews.com":
        source = "FOX News"

    # limit number of articles for test set
    if mode == 'prototype':
        if collection.find({'source': source}).count() > 100:
            log.info("Source '" + source + "' has " + str(collection.find({'source': source}).count()) + ' articles in database.  Skipping.')
            return None

    
    log.info('parsing feed ' + url)

    
    articles = []
    count = 0
    for item in feed['entries']:
        
        if debug and count == 100:
            break

        # don't normalize abc urls, they don't work
        if 'abcnews.go.com' in item['link']:
            rss_link = item['link']
        else:
            # normalize urls
            p_url = urlparse(item['link'])
            rss_link = p_url.scheme + "://" + p_url.netloc + p_url.path

        strip_regex = re.compile('index\.html|index\.shtml')
        rss_link = strip_regex.sub('', rss_link)

        # Business Insider occasionally has bloomberg articles, skip them
        if source == 'Business Insider' and 'bloomberg.com' in rss_link:
            continue

        article_id = hashlib.md5(str.encode(rss_link)).hexdigest()
        
        if collection.find({'links': rss_link}).count() > 0:
            log.debug('Already found "'+ source + '" article: ' + rss_link)
            continue

        title = item['title']

        try:
            if type(item['content']) == list:
                if len(item['content']) != 1:
                    log.info('RSS feed "content" field has more than 1 entry. ' + url)
                
                content = item['content'][0]['value']
            else:
                content = item['content']['value']

        except KeyError:
            try:
                content = item['summary']
            except KeyError:
                content = None

        try:
            author = item['author']
        except KeyError:
            author = None

        published = item['published']


        # add datetime stamp to data for ttl expiration
        date, zone = published.rsplit(' ', 1)
        try:
            published_dt = datetime.datetime.strptime(date, "%a, %d %b %Y %H:%M:%S")
        except:
            log.warning('unable to parse published time: ' + published)
            continue

        # add time zone awareness
        found_numerical_zone = False
        if len(zone) >= 5:
            search = re.search('(\+|\-)[0-9]+', zone)
            if search:
                found_numerical_zone = True
                zone = search.group()

        if zone == 'EDT' or zone == 'EST':
            published_tz = pytz.timezone('US/Eastern')
        elif zone == 'CDT' or zone == 'CST':
            published_tz = pytz.timezone('US/Central')
        elif zone == 'MDT' or zone == 'MST':
            published_tz = pytz.timezone('US/Mountain')
        elif zone == 'PDT' or zone == 'PST':
            published_tz = pytz.timezone('US/Western')
        elif zone == 'UTC' or zone == 'GMT':
            published_tz = pytz.timezone('UTC')        
        elif found_numerical_zone:
            zone = zone.rstrip('0')
            if len(zone) > 1:
                published_dt += datetime.timedelta(hours=int(zone))
        else:
            log.warning('unable to determine timezone: ' + published)
            continue

        if not found_numerical_zone:
            published_dt = published_tz.localize(published_dt)
            comp_dt = published_dt.astimezone(pytz.utc)
        else:
            comp_dt = published_dt
            
        # check if article is old, skip
        try:
            age = datetime.datetime.utcnow() - comp_dt
        except TypeError:
            utc_tz = pytz.timezone('UTC')
            age = utc_tz.localize(datetime.datetime.utcnow()) - comp_dt

        if age.seconds + age.days*86400 >= 2592000:
            log.debug('url ' + rss_link + ' more than 30 days old, skipping.')
            continue

        #
        # perform scrape (want to minimize this as much as possible, don't annoying hosts) 
        #
        try:
            result = scraper.scraper(rss_link, debug)
        except UnicodeEncodeError:
            # sometimes finding non utf-8 unicode characters, for now skip
            result = None
            log.warning('non utf-8 character in '+rss_link)
    
        full_text = None
        og_url = None
        if result is not None:
            full_text = result[0]
            image_url = result[1]
            display_text = result[2]
            og_url = result[3]
            
        # if og:url exists redefine the link and article_id hash, some rss feeds have badly formatted urls
        og_link = None
        if og_url is not None:
            p_url = urlparse(og_url)
            og_link = p_url.scheme + "://" + p_url.netloc + p_url.path
            
            strip_regex = re.compile('index\.html|index\.shtml')
            og_link = strip_regex.sub('', og_link)

            
            # recompute article id and check again for its existence in database (based on og:url tag)
            article_id = hashlib.md5(str.encode(og_link)).hexdigest()


        if og_link is None: 
            links = [rss_link]
        elif rss_link != og_link:
            links = [og_link, rss_link]
        else:
            links = [og_link]                

        if full_text is not None:          

            if len(full_text) < 250:
                if og_url is not None:
                    log.debug('Text too short on ' + og_link + '.  Skipping.')
                else:
                    log.debug('Text too short on ' + rss_link + '.  Skipping.')
                continue

            # check to see if article is in DB based on the text 
            #   handles sources that get resyndicated (AP, CNN, ABC, etc.)
            matching_articles = collection.find({'full_text': full_text})
            if matching_articles.count() > 0:
                if og_url is not None:
                    log.debug('Already found "'+ source + '" article by text: ' + og_link)
                else:
                    log.debug('Already found "'+ source + '" article by text: ' + rss_link)

                # if text of article was already found, associate all links that point to that same article
                for art in matching_articles:
                    new_links = list(art['links'])
                    if rss_link not in new_links:
                        new_links.append(rss_link)
                        
                    if og_link != rss_link and og_link not in new_links:
                        new_links.append(og_link)

                    if len(new_links) > len(art['links']):
                        collection.update( {'_id': art['_id']}, {'$set': {'links': new_links}} )
                
                continue

            # check og_link after checking if text was found in db, so we can add additional rss_links
            if collection.find({'links': og_link}).count() > 0:
                log.debug('Already found "'+ source + '" article: ' + og_link)
                continue

            #if mode == 'prototype':
            topics = textrazor_categorization(full_text)
            #else:
            #    topics = None

            if image_url is not None:
                server_image_url = resize_and_store_image(image_url, article_id)
            else:
                server_image_url = None

            article_data = {'article_id': article_id,
                            'title': title,
                            'author': author,
                            'summary': content,
                            'full_text': full_text,
                            'display_text': display_text,
                            'image': server_image_url,
                            'links': links,
                            'published': published,
                            'timestamp': published_dt,
                            'topics': {'text_razor': topics },
                            'source': source
                            }

        
            if debug:
                articles.append(article_data)
            else:
                
                log.debug('Adding "'+ source + '" article: ' + links[0])
                collection.insert(article_data)

            count += 1

        else:
            if og_url is not None:
                log.warning("error:  did not extract any text from - " + og_link)
            else:
                log.warning("error:  did not extract any text from - " + rss_link)

            # append empty
            if debug:
                article_data = { 'links': links, 'full_text': None, 'display_text': None, 'source': source }
                articles.append(article_data)

            # in streaming mode, append all links that failed to scrape to reduce website access
            if mode == 'streaming':

                if og_url is None:
                    links = [rss_link]
                else:
                    links = [rss_link, og_link]

                article_data = {'article_id': article_id,
                                'full_text': None,
                                'display_text': None,
                                'links': links,
                                'source': source,
                                'timestamp': published_dt
                                }
                
                if not debug:
                    collection.insert(article_data)
            
            
    log.info('Added ' + str(count) + ' articles from ' + source)

    if debug:
        return articles


# low-quality feeds
skip_me = [ 'http://www.npr.org/rss/rss.php?id=1021'
            ]


# i.e. unsolved
# pop-sci /science  photo slide shows, problem
# npr 1027, 2 divs with class=storytext
tough_feeds = [
               'http://www.popsci.com/full-feed/science'
               ]

# politico splits their stories across 2 divs, break around 2-3rd paragraph
slight_issues = [
         'http://gizmodo.com/rss',
         'http://sploid.gizmodo.com/rss',
         'http://www.politico.com/rss/magazine.xml',
         'http://www.politico.com/rss/politicopicks.xml'
    ]

# politico top blogs - author info not in og or rss feed, can scrape from site if necessary
# npr.org feeds divs inserted in middle of content, need to strip
# all popsci tech/diy feed needs to strip extra divs from content
# npr 1017, 1027, possibly others, have copyright info at top and bottom for transcript pages
still_working_feeds = [
         'http://www.politico.com/rss/Top10Blogs.xml',
         'http://www.npr.org/rss/rss.php?id=1053',
         'http://www.npr.org/rss/rss.php?id=1001',
         'http://www.npr.org/rss/rss.php?id=1017',
         'http://www.npr.org/rss/rss.php?id=1027'
]
"""
         'http://www.popsci.com/full-feed/technology',
         'http://www.popsci.com/full-feed/gadgets',
         'http://www.popsci.com/full-feed/diy',
         'http://feeds.popsci.com/c/34567/f/632419/index.rss'
         ]
"""

# huffpo scrape returns boilerplate page with no text
#'http://www.huffingtonpost.com/feeds/index.xml'

# abcnews international and us headlines is all video or wire stories
#'http://feeds.abcnews.com/abcnews/internationalheadlines'
#'http://feeds.abcnews.com/abcnews/usheadlines'

# notes:  many mashable pages not returning any text, getting boilerplate page with no content
#  cnn articles with a photo gallery at the top are not all working correctly
feeds = [
    'http://www.businessinsider.com/rss',
    'http://techcrunch.com/feed/',
    'http://mashable.com/rss/',
    'http://rss.cnn.com/rss/cnn_us.rss',
    'http://rss.cnn.com/rss/cnn_world.rss',
    'http://rss.cnn.com/rss/cnn_allpolitics.rss',
    'http://rss.cnn.com/rss/cnn_crime.rss',
    'http://rss.cnn.com/rss/cnn_tech.rss',
    'http://rss.cnn.com/rss/cnn_health.rss',
    'http://rss.cnn.com/rss/cnn_showbiz.rss',
    'http://rss.cnn.com/rss/cnn_travel.rss',
    'http://rss.cnn.com/rss/cnn_living.rss',
    'http://feeds.foxnews.com/foxnews/latest',
    'http://feeds.foxnews.com/foxnews/entertainment',
    'http://feeds.foxnews.com/foxnews/health',
    'http://feeds.foxnews.com/foxnews/section/lifestyle',
    'http://feeds.foxnews.com/foxnews/opinion',
    'http://feeds.foxnews.com/foxnews/politics',
    'http://feeds.foxnews.com/foxnews/science',
    'http://feeds.foxnews.com/foxnews/sports',
    'http://feeds.foxnews.com/foxnews/tech',
    'http://feeds.foxnews.com/foxnews/internal/travel/mixed',
    'http://feeds.foxnews.com/foxnews/national',
    'http://feeds.foxnews.com/foxnews/world',
    'http://feeds.abcnews.com/abcnews/technologyheadlines',
    'http://feeds.abcnews.com/abcnews/moneyheadlines',
    'http://feeds.abcnews.com/abcnews/politicsheadlines',
    'http://feeds.abcnews.com/abcnews/internationalheadlines',
    'http://feeds.abcnews.com/abcnews/healthheadlines',
    'http://feeds.abcnews.com/abcnews/entertainmentheadlines',
    'http://feeds.abcnews.com/abcnews/travelheadlines'
    #'http://rss.cnn.com/rss/money_latest.rss'
    #'http://rss.cnn.com/rss/money_latest.rss'
#    'http://www.npr.org/rss/rss.php?id=1053'
]


def add_test_case(article):
    """
    add a document article entry from the feed parser to the test database
    """

    try:
        client = MongoClient('localhost', 27017)
    except Exception as e:
        log.warning('Failed to connect to mongo.')


    db = client.noozli_test
    collection = db.webscraper

    res = collection.find_one({"source": article['source']})
    if res is None:

        if 'abcnews.go.com' in article['links'][0]:
            post = {'source': article['source'], 
                    'articles': [{'link': article['links'][1], 'full_text': article['full_text']}]
                    }
        else:
            post = {'source': article['source'], 
                    'articles': [{'link': article['links'][0], 'full_text': article['full_text']}]
                    }
            
        collection.insert(post)
    else:
        if 'abcnews.go.com' in article['links'][0]:
            articles = res['articles'] + [{'link': article['links'][1], 'full_text': article['full_text']}]
        else:
            articles = res['articles'] + [{'link': article['links'][0], 'full_text': article['full_text']}]
            
        collection.update({"source": article['source']}, {"$set": {"articles": articles}})



def update_db():
    """
    script used to update entire article database when a change to structure is made
    """

    try:
        client = MongoClient('localhost', 27017)
    except Exception as e:
        log.warning('Failed to connect to mongo.')

    db = client.noozli
    collection = db.streaming

    for article in collection.find():
        if article['display_text'] is None:
            continue

        display_soup = BeautifulSoup(article['display_text'])

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
        display_text = line_break.sub('\n', display_text)

        collection.update({'_id': article['_id']}, {"$set": {'display_text': display_text}})
    
#
# investigate bad mashable link:  http://mashable.com/2014/06/17/year-one-businesses/
#

# mode = 'streaming'|'prototype'
def run(debug=False, mode='streaming'):

    num = -1

    if debug:
        log.info(feeds[num])
        return parse_feed(feeds[num], debug, mode=mode)

    else:
        for feed in feeds:
            parse_feed(feed, mode=mode)



if __name__ == '__main__':

    # pull down rss feeds every xx minutes, for testing purposes let's do every 20
    while True:

        try:
            run(debug=False, mode='streaming')
        except Exception as e:
            log.error('something went wrong')
            log.error(str(e))

        log.debug('rss sleeping.')
        time.sleep(1100)
