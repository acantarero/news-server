import flask
from flask import Flask
from flask.ext import restful
from flask.ext.restful import reqparse

import database
import multiprocessing
import pymongo
import json
import logging
import logger
import os
import uuid
import time
import sys
import subprocess

sys.path.append(os.path.dirname(os.path.realpath(__file__))+'/algos')

import algo

log = logging.getLogger('noozli_api')
log.setLevel(logging.INFO)
if not log.handlers:
    log.addHandler(logger.NoozliHandler('api.log'))
    #log.addHandler(logger.NoozliStreamingHandler())

app = Flask(__name__)
api = restful.Api(app)

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

def make_error(status_code, message):

    response = flask.jsonify({'status':  status_code, 'message': message})
    response.status_code = status_code

    return response

# test end point for experimenting
class ArticlesTest(restful.Resource):

    def __init__(self):

        self.parser = reqparse.RequestParser()
        self.parser.add_argument('count', type=int, help='Count must be an integer number')

    def get(self):

        args = self.parser.parse_args()
        count = args['count']

        counter = 0
        articles = []
        for doc in collection.find():
            
            if counter == count:
                break

            if doc['full_text'] is None:
                continue
            
            shortened_doc = {k: v for k, v in doc.items() if not k in ['_id', 'topics', 'timestamp', 'author', 'summary', 'links', 'full_text']}
            shortened_doc['link'] = doc['links'][0]
            
            # swap out image
            shortened_doc['image'] = 'https://c6050166-a-62cb3a1a-s-sites.googlegroups.com/site/cantarer/personal/noozli_test_image_1.png?attachauth=ANoY7cqk6Xzyuif7i4Pwj6aqHQa9M3fN8P3rRRBruHomVrywKnj_37558ixdS3qV1VYolT6JptcEzUnpOFwX843j-y00NV7JGQJEQWSNerLYfFFuuR54rVl9dmVzB57BaKAFDzHKpF2gJQZukEeQlpsUbE5zozwnpst2jHDAa9Szboo23YKRp3ajAfvr6cyDQpD30RM4z9AavPBBp5iImj32mxgllDWtsHC6mbn456Kt7ECQqjri6Ho%3D&attredirects=0'

            articles.append(shortened_doc)
            counter += 1

        return flask.jsonify({'count': len(articles), 'articles': articles})


class Articles(restful.Resource):

    def __init__(self):
        self.parser = reqparse.RequestParser()

        self.parser.add_argument('user_id', type=str, help='user_id must be a valid user id')
        self.parser.add_argument('count', type=int, help='count must be an integer number')

    def get(self):

        start = time.time()

        args = self.parser.parse_args()
        count = args['count']
        user_id = args['user_id']

        try:
            user_data = cassandra_client.find_user(user_id)
        except IndexError as e:
            return make_error(404, 'user_id not found')

        article_algo = user_data[1]

        if article_algo == 1:
            server = algo.WeightedAverage(user_id)
        else:
            raise RuntimeError("unsupported article serving algorithm "+str(article_algo))

        articles = server.serve(count)

        if articles is None:
            log.warning('something went wrong, did not find articles')
            return make_error(500, 'article serving error')
    
        cassandra_client.add_served_articles(user_id, [art['article_id'] for art in articles])
        end = time.time()
        log.info('request for articles completed in ' + str(end-start) +  ' s')

        return flask.jsonify({'count': len(articles), 'articles': articles})
    


class Users(restful.Resource):
    
    def get(self):

        user_id = str(uuid.uuid4())        
        while cassandra_client.check_user_exists(user_id):
            user_id = str(uuid.uuid4())

        cassandra_client.create_user(user_id)
        return flask.jsonify({'value': user_id})


    def post(self):

        start_time = time.time()

        if flask.request.headers['Content-Type'] != 'application/json':
            return make_error(404, 'content-type must be application/json')

        try:
            data = json.loads(bytes.decode(flask.request.data))            
        except:
            return make_error(404, 'posted data not in json format')

        try:
            count = data['count']
        except KeyError:
            return make_error(404, 'must provide a count')
        
        try:
            user_id = data['user_id']
        except KeyError:
            return make_error(404, 'required parameter user_id missing')

        if not cassandra_client.check_user_exists(user_id):
            return make_error(404, 'invalid user_id')

        try:
            articles = data['articles']
        except KeyError:
            return make_error(404, 'articles not found')

        if len(articles) != count:
            return make_error(404, 'length of articles data does not match count')

        
        required_keys = ['article_id', 'action', 'total_time', 'time_zero']
        analytics = []
        sources = []
        article_ids = []
        for art in articles:
            for key in required_keys:
                if key not in art.keys():
                    return make_error(404, 'missing required fields')
        
            article_ids.append(art['article_id'])

            if art['action'] not in ['done', 'save']:
                return make_error(404, 'invalid action')

            analytics.append({'action': art['action'], 'total_time': art['total_time'], 'time_zero': art['time_zero']})

            try:
                analytics[-1]['percent'] = art['percent']
            except KeyError:
                analytics[-1]['percent'] = 0

            try:
                analytics[-1]['up'] = art['up']
            except KeyError:
                analytics[-1]['up'] = 0

            try:
                analytics[-1]['down'] = art['down']
            except KeyError:
                analytics[-1]['down'] = 0

            try:
                for item in art['share']:
                    if item not in ['twitter', 'facebook', 'email']:
                        return make_error(404, 'invalid share type')

                analytics[-1]['share'] = art['share']

            except KeyError:
                analytics[-1]['share'] = []
                

            for doc in collection.find({'article_id': art['article_id']}):
                sources.append(doc['source'])
                break

        analytics_strings = [ json.dumps(item) for item in analytics ]
        cassandra_client.add_article_analytics(user_id, article_ids, analytics_strings, sources)
        end_time = time.time()

        log.info('post of analytics completed in ' + str(end_time-start_time) + 's.')

        # launch learning procedure and return
        pool = multiprocessing.Pool(processes=1)
        r = pool.apply_async(algo.learn, [user_id, analytics, cassandra_client.get_article_algo(user_id)])

        response = flask.jsonify({'status':  200, 'message': 'success'})
        response.status_code = 200
        return response



class Alive(restful.Resource):

    def get(self):
        response = flask.jsonify({'status': 'alive'})
        response.status_code = 200
        return response


# note this only works in non-dockerized version where scraper and webserver are running in same environment and on the same machine    
class Scraper(restful.Resource):

    def get(self):
        
        p1 = subprocess.Popen(['ps', '-aux'], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(['grep', 'rss.py'], stdin=p1.stdout, stdout=subprocess.PIPE)
        p1.stdout.close()
        output = p2.communicate()[0]

        found = False
        for line in output.split('\n'):
            if 'python rss.py' in line:
                found = True

        if found:
            response = flask.jsonify({'status': 'running'})
            response.status_code = 200
        else:
            response = flask.jsonify({'status': 'down'})
            response.status_code = 200
    

        return response
    
api.add_resource(Articles, '/1.0/articles')
api.add_resource(Users, '/1.0/users')
api.add_resource(Alive, '/1.0/alive')
api.add_resource(ArticlesTest, '/test/articles')
api.add_resource(Scraper, '/1.0/scraper')

if __name__ == '__main__':
    log.info('starting api services')
    #app.run(port=80)
    app.run()
