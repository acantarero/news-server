# test_scraper.py
# Tests for webscraper.  For each site, run stored rss feed through scraper, compare
#   sites against stored extracted full_text.  One test per each unique site / feed
#
#

import sys

sys.path.append('../src')

import scraper
import pymongo


def test_sources():

    try:
        client = pymongo.MongoClient('localhost', 27017)
    except Exception as e:
        print('Failed to connect to mongo.')
        print(e.message)

    db = client.noozli_test
    collection = db.webscraper


    for doc in collection.find():
        for article in doc['articles']:
            yield check_source, doc['source'], article

def check_source(source, article):

    
    results = scraper.scraper(article['link'])

    if results == None:
        text1 = None
    else:
        text1 = results[0]

    text2 = article['full_text']

    assert text1 == text2



