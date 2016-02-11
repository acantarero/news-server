import sys
sys.path.append('../')

import datetime
import database
import logging
import pymongo
import json
import random
import time

random.seed(time.time())

log = logging.getLogger('noozli_api')
log.setLevel(logging.INFO)
if not log.handlers:
    log.addHandler(logger.NoozliHandler('api.log'))
#    log.addHandler(logger.NoozliStreamingHandler())

#
# Init once
#

try:
    mongo_client = pymongo.MongoClient('localhost', 27017)
except Exception as e:
    log.warning('Failed to connect to mongo.')
    
db = mongo_client.noozli
collection = db.streaming

try:
    cassandra_client = database.NoozliClient()
    cassandra_client.connect(['127.0.0.1'])
except Exception as e:
    log.warning('Failed to connect to cassandra.')
    

"""
asyncrhonously calling a method is not straightforward
use wrapper function
"""
def learn(user_id, analytics, algo):

    if algo == 1:
        user = NoozliBasic(user_id)
        user.learn(analytics)

    else:
        raise RuntimeError("unsupported algorithm number "+str(algo))
        
    
""" 
generic interface for noozli algorithms.  always must have two parts:
    1:  learn method:   this takes engagement analytics data and learns how to better serve
                        the user
    2:  serve:   serve new articles to the user
"""
class NoozliAlgo:

    def __init__(self, user_id):
        self.user_id = user_id

    def learn(self, article_analytics):
        raise NotImplementedError("learn method not implemented")

    def serve(self, count):
        raise NotImplementedError("serve method not implemented")

# textrazor
topic_to_index = {
    'Arts': 0,
    'Belief': 1,
    'Business': 2,
    'Culture': 3,
    'Education': 4,
    'Environment': 5,
    'Health': 6,
    'History': 7,     
    'Language': 8,
    'Law': 9,
    'Leisure': 10,
    'Mathematics': 11,
    'Nature': 12,
    'People': 13,
    'Politics': 14,
    'Science': 15,
    'Sports': 16,
    'Technology': 17,
    'Violence': 18,
    'Weather': 19
    }

index_to_topic = [
    'Arts',
    'Belief',
    'Business',
    'Culture',
    'Education',
    'Environment',
    'Health',
    'History',     
    'Language',
    'Law',
    'Leisure',
    'Mathematics',
    'Nature',
    'People',
    'Politics',
    'Science',
    'Sports',
    'Technology',
    'Violence',
    'Weather'
]

topic_to_bucket = {
    'Arts': ['Arts', 'Culture', 'Leisure'],
    'Belief': ['Belief'],
    'Business': ['Business'],
    'Culture': ['Arts', 'Culture', 'Leisure'],
    'Education': ['Education'],
    'Environment': ['Environment', 'Nature'],
    'Health': ['Health'],
    'History': ['History'],
    'Language': ['Language'],
    'Law': ['Law', 'Politics'],
    'Leisure': ['Arts', 'Culture', 'Leisure'],
    'Mathematics': ['Mathematics'],
    'Nature': ['Environment', 'Nature'],
    'People': ['People'],
    'Politics': ['Law', 'Politics'],
    'Science': ['Science', 'Technology'],
    'Sports': ['Sports'],
    'Technology': ['Science', 'Technology'],
    'Violence': ['Violence'],
    'Weather': ['Weather']
}
        
def article_to_dna_mapping(topics):
    """
    Take topics stored with article and convert to dna vector
    
    :param topics: list of lists, each sublist has [string: Topic Name, float: score] 
    :returns: list of floats in same order as user dna (alphabetical by topic name)
    """
    
    article_dna = [float(0) for i in range(20)]
    for topic in topics:
        article_dna[topic_to_index[topic[0]]] = float(topic[1])
    return article_dna
    
def inner_product(a, b):
    try:
        return sum( p*q for p,q in zip(a, b) )
    except:
        return 0

"""
#
# Engagement mapping
#
# algorithm maps engagement analytics to a number in [0,1]
#    = 0 is labeled an as negative engagement (NE)
#    > 0 is labeled as a positive engagement (PE)
"""

def engagement_mapping(article_analytics, algo):
    """
    Map a single article's engagement analytics to a weighting coefficient

    :param article_analytics: dict containing analytics for an article
    :param algo: int selecting from different engagement mapping algorithms
    :returns: weighting coefficient
    """

    if algo == 1:

        # original coeffs 0.1, 0.2, 0.5, 0.7, 0.8 - dna updates fast
        # slower coeffs (same relative importance):  0.0625, 0.125, 0.3125, 0.4375, 0.5
        down = article_analytics['down']
        total_time = article_analytics['total_time']
        percent = article_analytics['percent']

        if len(article_analytics['share']) > 0:
            return 0.5

        if article_analytics['action'] == 'save':
            return 0.0625

        if down > 0:
            if total_time > 60 and down >= 3 and percent > 85:
                return .4375
            elif total_time > 20:
                return 0.3125
            else:
                return 0.125
        
        return float(0)

    else:
        raise ValueError('algorithm value not supported: %d', algo)

"""
Initial testing algorithms:
1)  Basic:  weighted averaging of feature vector
2)  ML (Naive Bayes)  not implemented
3)  Item Collaborative Filtering
"""

# Basic Algorithm:  weighted averaging of feature vector
class WeightedAverage(NoozliAlgo):

    def update_dna(self, user_dna, article_dna, coeff, algo):
        """
        Compute updated dna

        :param user_dna: list of floats, current dna
        :param article_dna: list of floats, dna of article
        :param coeff: float, weighting coefficient
        :param algo: int, choose between different update algos
        :returns:  list of floats, updated user_dna
        """

        if algo == 1:
            assert len(user_dna) == len(article_dna)
            if coeff == 0:
                # if user did not engage with article, reduce those categories
                result = []
                for i in range(len(user_dna)):
                    if article_dna[i] > 0:
                        result.append(0.0625*user_dna[i])
                    else:
                        result.append(user_dna[i])
                return result
            else:
                return [ (1.0-coeff)*user_dna[i] + coeff*article_dna[i] for i in range(len(user_dna)) ]
        else:
            raise ValueError('algorithm value not supported: %d', algo)

        
    def learn(self, analytics):

        start = time.time()
    
        user_data = cassandra_client.find_user(self.user_id)

        log.info(self.user_id)
        for data in analytics:

            coeff = engagement_mapping(data, user_data.engagement_mapping)
            log.info('mapping coeff:  ' + str(coeff))
            article = collection.find_one({'article_id': data['article_id']})
            article_dna = article_to_dna_mapping(article['topics']['text_razor'])
            log.info('article_dna:  ' + str(article_dna))

            user_dna = json.loads(user_data.dna)['dna']
            log.info('user_dna:  ' + str(user_dna))
            updated_dna = self.update_dna(user_dna, article_dna, coeff, user_data.dna_update_algo)
            log.info('updated:  ' + str(updated_dna))

            # check for 'PE' and 'NE' (positive and negative engagement. pe engagement_mapping coeff > 0, ne, engagement mapping coeff < 0
            engagements = cassandra_client.get_analytics(self.user_id, 100)
            engagement_coeffs = [ 1 if engagement_mapping(json.loads(e[0]),1) > 0 else 0 for e in engagements ]

            # need to double check if first 100 are most recent or last 100
            if len(engagement_coeffs) < 100:
                success_rate_100 = sum(engagement_coeffs) / len(engagement_coeffs)
            else:
                success_rate_100 = sum(engagement_coeffs[:100]) / len(engagement_coeffs[:100])

            # need to double check if first 10 are most recent or last 10
            if len(engagement_coeffs) < 10:
                success_rate_10 = sum(engagement_coeffs) / len(engagement_coeffs)
            else:
                success_rate_10 = sum(engagement_coeffs[:10]) / len(engagement_coeffs[:10])

            if len(engagement_coeffs) < 100 and (success_rate_100 < .5 or success_rate_10 < .5):                
                # perturb dna
                for i in range(len(updated_dna)):
                    val = updated_dna[i] + random.uniform(-0.1,0.1)
                    if val > 1:
                        val = 1
                    if val < 0:
                        val = 0
                    updated_dna[i] = val
                    
            elif len(engagement_coeffs) == 100 and success_rate_100 < .5:
                # entirely reset dna
                updated_dna = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]


        end = time.time()
        log.info('time to update dna: ' + str(end-start) + ' s.')

        
        
    def serve(self, requested_count):

        user_id = self.user_id

        try:
            user_data = cassandra_client.find_user(user_id)
        except IndexError as e:
            return None

        user_dna = json.loads(user_data[4])['dna']

        final_articles_list = []
        article_ids_list = []
        matched_article_count = 0
        # search hour by hour for 4 hours
        # then 4-12
        # then 12-72
        # then 72-144
        time_deltas = [ datetime.timedelta(hours=1), datetime.timedelta(hours=1), datetime.timedelta(hours=1), datetime.timedelta(hours=1), datetime.timedelta(hours=8), datetime.timedelta(hours=60), datetime.timedelta(hours=72)]
        current = datetime.datetime.utcnow()
        for delta in time_deltas:
            articles = []
            start_time = current - delta

            for art in collection.find({"timestamp": {"$gte": start_time, "$lt": current}}):

                if art['full_text'] is None:
                    continue

                try:
                    if not cassandra_client.check_if_served(self.user_id, art['article_id']):
                        shortened_doc = {k: v for k, v in art.items() if not k in ['_id', 'author', 'summary', 'links', 'full_text']}
                        shortened_doc['link'] = art['links'][0]
                        articles.append(shortened_doc)
                except TypeError:
                    shortened_doc = {k: v for k, v in art.items() if not k in ['_id', 'author', 'summary', 'links', 'full_text']}
                    shortened_doc['link'] = art['links'][0]
                    articles.append(shortened_doc)

                     
            # find 5 top categories in user dna
            user_dna_copy = list(user_dna)
            top_buckets = []
            for i in range(5):
                top_buckets.append(topic_to_bucket[index_to_topic[user_dna_copy.index(max(user_dna_copy))]])
                for category in top_buckets[-1]:
                    user_dna_copy[topic_to_index[category]] = 0
            
            
            all_topics = [[], [], [], [], [], []]
            for art in articles:
                art_dna = article_to_dna_mapping(art['topics']['text_razor'])
                
                # find top article
                all_topics[0].append((inner_product(art_dna, user_dna), art['article_id']))
                
                # find top articles in zero'ed out categories
                count = 1
                for bucket in top_buckets:
                    art_dna_copy = list(art_dna)
                    for category in bucket:
                        art_dna_copy[topic_to_index[category]] = 0
                    all_topics[count].append((inner_product(art_dna_copy, user_dna), art['article_id']))
                    count += 1
                
            # create alternating stream of articles in different categories
            #log.info(all_topics)
            for scores in all_topics:
                scores.sort(key=lambda x: x[0], reverse=True)

            #log.info(all_topics)
            # only guarantees alternating buckets if there are enough articles in current time bucket
            for topic in all_topics:

                if len(topic) == 0:
                    continue

                top_item = topic.pop(0)
                if collection.find({'article_id': top_item[1]}).count() > 1:
                    log.warning('Non-unique article_id found: ' + top_item[1])
                    
                for doc in collection.find({'article_id': top_item[1]}):
                    art = doc
                shortened_doc = {k: v for k, v in art.items() if not k in ['_id', 'author', 'timestamp', 'topics', 'summary', 'links', 'full_text']}
                shortened_doc['link'] = art['links'][0]

                if shortened_doc['article_id'] not in article_ids_list:
                    final_articles_list.append(shortened_doc)
                    article_ids_list.append(shortened_doc['article_id'])

                if len(final_articles_list) == requested_count:
                    return final_articles_list
                            
            current -= delta

        return final_articles_list
