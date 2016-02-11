import requests
import json

local_host = 'http://127.0.0.1:5000/'

test_user_id = '6bc3a6b4-568e-4e0b-bfcd-256231e03e7c'
test_data_base = {'count': 1, 'user_id': test_user_id, 'articles': [{'article_id': 'fcce9e950368569c72d1dae0c3023a94', 'action': 'done', 'total_time': 30, 'time_zero': 3}]}
test_data_full = {'count': 1, 'user_id': test_user_id, 'articles': [{'article_id': 'fcce9e950368569c72d1dae0c3023a94', 'action': 'done', 'total_time': 30, 'time_zero': 3, 'percent': 35, 'down': 5, 'up': 1, 'share': ['twitter']}]}
test_data_multiple = {'count': 3, 'user_id': test_user_id, 'articles': [{'article_id': '61c65810b97b17bf0998ca6856c40929', 'action': 'done', 'total_time': 30, 'time_zero': 3, 'percent': 35, 'down': 5, 'up': 1, 'share': ['twitter']}, {'article_id': '39d67d9e9e5c0fb70c1fa1eb3c6a96e9', 'action': 'save', 'total_time': 15, 'time_zero': 13, 'percent': 75, 'down': 1, 'up': 0, 'share': ['facebook', 'twitter']}, {'article_id': '38d9628c5cc1eb3282cf641f29d0386e', 'action': 'done', 'total_time': 140, 'time_zero': 33, 'percent': 5, 'down': 3, 'up': 2, 'share': []}]}



def test_user_post_content_type():

    r = requests.post(local_host+'1.0/users', data=json.dumps(test_data_base))
    assert r.status_code == 404 and r.json()['message'] == 'content-type must be application/json'

def test_user_post_user_id():

    test_no_uid = {'count': 1, 'articles': [{'action': 'done', 'total_time': 30, 'time_zero': 3}]}
    r = requests.post(local_host+'1.0/users', data=json.dumps(test_no_uid), headers={'content-type': 'application/json'})
    assert r.status_code == 404 and r.json()['message'] == 'required parameter user_id missing'

def test_user_post_count_wrong():

    test_wrong_count = {'count': 3, 'user_id': test_user_id, 'articles': [{'action': 'done', 'total_time': 30, 'time_zero': 3}]}
    r = requests.post(local_host+'1.0/users', data=json.dumps(test_wrong_count), headers={'content-type': 'application/json'})
    assert r.status_code == 404 and r.json()['message'] == 'length of articles data does not match count'

def test_user_post_invalid_uuid():

    test_wrong_uid = {'count': 1, 'user_id': '380c6f49-71ba-4259-8f13-1379874cff42', 'articles': [{'action': 'done', 'total_time': 30, 'time_zero': 3}]}
    r = requests.post(local_host+'1.0/users', data=json.dumps(test_wrong_uid), headers={'content-type': 'application/json'})
    assert r.status_code == 404 and r.json()['message'] == 'invalid user_id'

def test_user_post_non_json():

    test_non_json = 'this is a string.'
    r = requests.post(local_host+'1.0/users', data=test_non_json, headers={'content-type': 'application/json'})
    assert r.status_code == 404 and r.json()['message'] == 'posted data not in json format'

def test_user_post_no_count():

    test_no_count = {'user_id': test_user_id, 'articles': [{'action': 'done', 'total_time': 30, 'time_zero': 3}]}
    r = requests.post(local_host+'1.0/users', data=json.dumps(test_no_count), headers={'content-type': 'application/json'})
    assert r.status_code == 404 and r.json()['message'] == 'must provide a count'

def test_user_post_no_articles():

    test_no_articles = {'count': 1, 'user_id': test_user_id}
    r = requests.post(local_host+'1.0/users', data=json.dumps(test_no_articles), headers={'content-type': 'application/json'})
    assert r.status_code == 404 and r.json()['message'] == 'articles not found'

def test_user_post_bad_action():

    test_bad_action = {'count': 1, 'user_id': test_user_id, 'articles': [{'article_id': 'fcce9e950368569c72d1dae0c3023a94', 'action': 'hi', 'total_time': 30, 'time_zero': 3}]}
    r = requests.post(local_host+'1.0/users', data=json.dumps(test_bad_action), headers={'content-type': 'application/json'})
    assert r.status_code == 404 and r.json()['message'] == 'invalid action'

def test_user_post_missing_required_field():

    test_bad_action = {'count': 1, 'user_id': test_user_id, 'articles': [{'action': 'hi', 'total_time': 30, 'time_zero': 3}]}
    r = requests.post(local_host+'1.0/users', data=json.dumps(test_bad_action), headers={'content-type': 'application/json'})
    assert r.status_code == 404 and r.json()['message'] == 'missing required fields'

def test_user_post_base():

    r = requests.post(local_host+'1.0/users', data=json.dumps(test_data_base), headers={'content-type': 'application/json'})
    assert r.status_code == 200

def test_user_post_full():

    r = requests.post(local_host+'1.0/users', data=json.dumps(test_data_full), headers={'content-type': 'application/json'})
    assert r.status_code == 200

def test_user_post_multiple():

    r = requests.post(local_host+'1.0/users', data=json.dumps(test_data_multiple), headers={'content-type': 'application/json'})
    assert r.status_code == 200
