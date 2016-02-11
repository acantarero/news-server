import json
import pymongo
import time

import database
import logging

log = logging.getLogger('noozli_api')
log.setLevel(logging.INFO)
if not log.handlers:
    #log.addHandler(logger.NoozliHandler('api.log'))
    log.addHandler(logger.NoozliStreamingHandler())


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

try:
    cassandra_client = database.NoozliClient()
    cassandra_client.connect(['127.0.0.1'])
except Exception as e:
    log.warning('Failed to connect to cassandra.')
    

try:
    mongo_client = pymongo.MongoClient('localhost', 27017)

    db = mongo_client.noozli
    collection = db.streaming
except Exception as e:
    log.warning('Failed to connect to mongo.')
    
            
    

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
        

def update_dna(user_dna, article_dna, coeff, algo):
    """
    Compute update dna

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


def update(user_id, analytics):
    """
    Update a user's dna based on their recent reading habits
    
    :param user_id: string corresponding to user uuid
    :param analytics: dictionary of per article analytics data
    """
    
    start = time.time()
    
    user_data = cassandra_client.find_user(user_id)

    log.info(user_id)
    for data in analytics:

        coeff = engagement_mapping(data, user_data.engagement_mapping)
        log.info('mapping coeff:  ' + str(coeff))
        article = collection.find_one({'article_id': data['article_id']})
        article_dna = article_to_dna_mapping(article['topics']['text_razor'])
        log.info('article_dna:  ' + str(article_dna))

        user_dna = json.loads(user_data.dna)['dna']
        log.info('user_dna:  ' + str(user_dna))
        updated_dna = update_dna(user_dna, article_dna, coeff, user_data.dna_update_algo)
        log.info('updated:  ' + str(updated_dna))

        # check for 'PE' and 'NE' (positive and negative engagement. pe engagement_mapping coeff > 0, ne, engagement mapping coeff < 0
        #   use new (untested table noozli.user_articles_ordered, this table should be sorted in DESC order by time_uuid
        #   using LIMIT # in CQL, should return the N most recent items
        
        # proposed first set of metrics:
        #  PE / 10 for last 10
        #  PE / 100 for last 100
        # overall, PE / (PE+NE)
        

    end = time.time()
    log.info('time to update dna: ' + str(end-start) + ' s.')
    
    
