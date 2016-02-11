import datetime
import pymongo


def articles_per_day():
    """
    count number of articles being added per day
    """

    try:
        client = pymongo.MongoClient('localhost', 27017)
    except Exception as e:
        print('Failed to connect to mongo')

    db = client.noozli
    collection = db.streaming

    now = datetime.datetime.utcnow()

    current_dt = datetime.datetime(now.year, now.month, now.day) - datetime.timedelta(hours=24)

    # this count is inaccurate, need to check for None is display_text
    article_counts = []
    for i in range(30):
        article_counts.append(collection.find({"timestamp": {"$gte": current_dt - datetime.timedelta(hours=24), "$lt": current_dt}}).count())
        current_dt -= datetime.timedelta(hours=24)

    return article_counts


def topic_percentages(thres=0):
    
    try:
        client = pymongo.MongoClient('localhost', 27017)
    except Exception as e:
        print('Failed to connect to mongo')

    db = client.noozli
    collection = db.streaming

    topic_counts = {
        'Arts': 0,
        'Belief': 0,
        'Business': 0,
        'Culture': 0,
        'Education': 0,
        'Environment': 0,
        'Health': 0,
        'History': 0,     
        'Language': 0,
        'Law': 0,
        'Leisure': 0,
        'Mathematics': 0,
        'Nature': 0,
        'People': 0,
        'Politics': 0,
        'Science': 0,
        'Sports': 0,
        'Technology': 0,
        'Violence': 0,
        'Weather': 0
        }
    
    for post in collection.find():
        if post['display_text'] is not None:
            for topic in post['topics']['text_razor']:
                if topic[1] > thres:
                    topic_counts[topic[0]] += 1

    return topic_counts


def topics_by_day(thres=0):
    
    try:
        client = pymongo.MongoClient('localhost', 27017)
    except Exception as e:
        print('Failed to connect to mongo')

    db = client.noozli
    collection = db.streaming

    topic_counts = {
        'Arts': [],
        'Belief': [],
        'Business': [],
        'Culture': [],
        'Education': [],
        'Environment': [],
        'Health': [],
        'History': [],     
        'Language': [],
        'Law': [],
        'Leisure': [],
        'Mathematics': [],
        'Nature': [],
        'People': [],
        'Politics': [],
        'Science': [],
        'Sports': [],
        'Technology': [],
        'Violence': [],
        'Weather': []
        }
    
    now = datetime.datetime.utcnow()
    current_dt = datetime.datetime(now.year, now.month, now.day) - datetime.timedelta(hours=24)

    no_topics = []
    for i in range(30):

        no_topics.append(0)
        print('Processing day ' + str(i))
        for key in topic_counts.keys():
            topic_counts[key].append(0)

        for post in collection.find({"timestamp": {"$gte": current_dt - datetime.timedelta(hours=24), "$lt": current_dt}}):
            if post['display_text'] is not None:
                try:
                    for topic in post['topics']['text_razor']:
                        if topic[1] > thres:
                            topic_counts[topic[0]][-1] += 1
                except:
                    no_topics[-1] += 1

        current_dt -= datetime.timedelta(hours=24)

    return topic_counts, no_topics
    
