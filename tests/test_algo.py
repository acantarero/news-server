import sys
sys.path.append('../src/algos')
sys.path.append('../src')

import algo

def test_engagement_mapping_bad():
    
    analytics = {}
    algo_id = -1

    value_error = False
    try:
        algo.engagement_mapping(analytics, algo_id)
    except ValueError:
        value_error = True
        
    assert value_error
        

def test_engagement_mapping_1_share_coeffs():

    analytics = [{"article_id": "fcce9e950368569c72d1dae0c3023a94", "action": "done", "total_time": 30, "time_zero": 3, "down": 0, "up": 0, "percent": 0, "share": ["twitter"]},
                 {"article_id": "fcce9e950368569c72d1dae0c3023a94", "action": "done", "total_time": 130, "time_zero": 3, "down": 8, "up": 0, "percent": 100, "share": ["twitter"]}]
               
    failed = False
    for i in range(len(analytics)):
        coeff = algo.engagement_mapping(analytics[i], 1)
        if coeff != 0.8:
            failed = True

    assert not failed

def test_engagement_mapping_1_full_read():
    
    analytics = [{"article_id": "fcce9e950368569c72d1dae0c3023a94", "action": "done", "total_time": 130, "time_zero": 3, "down": 3, "up": 1, "percent": 88, "share": []}]

    failed = False
    for i in range(len(analytics)):
        coeff = algo.engagement_mapping(analytics[i], 1)
        if coeff != 0.7:
            failed = True

    assert not failed
    
def test_engagement_mapping_1_medium():

    analytics = [{"article_id": "fcce9e950368569c72d1dae0c3023a94", "action": "done", "total_time": 30, "time_zero": 3, "down": 5, "up": 0, "percent": 55, "share": []},
                 {"article_id": "fcce9e950368569c72d1dae0c3023a94", "action": "done", "total_time": 150, "time_zero": 3, "down": 2, "up": 0, "percent": 100, "share": []}]

    failed = False
    for i in range(len(analytics)):
        coeff = algo.engagement_mapping(analytics[i], 1)
        if coeff != 0.5:
            failed = True

    assert not failed

def test_engagement_mapping_1_minimal():

    analytics = [{"article_id": "fcce9e950368569c72d1dae0c3023a94", "action": "done", "total_time": 15, "time_zero": 3, "down": 1, "up": 0, "percent": 0, "share": []},
                 {"article_id": "fcce9e950368569c72d1dae0c3023a94", "action": "done", "total_time": 20, "time_zero": 3, "down": 1, "up": 0, "percent": 100, "share": []}]
                 
    failed = False
    for i in range(len(analytics)):
        coeff = algo.engagement_mapping(analytics[i], 1)
        if coeff != 0.2:
            failed = True

    assert not failed

def test_engagement_mapping_1_zero_coeffs():

    analytics = [{"article_id": "fcce9e950368569c72d1dae0c3023a94", "action": "done", "total_time": 30, "time_zero": 3, "down": 0, "up": 0, "percent": 0, "share": []}]

    failed = False
    for i in range(len(analytics)):
        coeff = algo.engagement_mapping(analytics[i], 1)
        if coeff != 0.0:
            failed = True

    assert not failed

def test_engagement_mapping_1_save_coeffs():
    
    analytics = [{"article_id": "fcce9e950368569c72d1dae0c3023a94", "action": "save", "total_time": 20, "time_zero": 3, "down": 1, "up": 0, "percent": 100, "share": []},
                 {"article_id": "fcce9e950368569c72d1dae0c3023a94", "action": "save", "total_time": 150, "time_zero": 3, "down": 2, "up": 0, "percent": 100, "share": []},
                 {"article_id": "fcce9e950368569c72d1dae0c3023a94", "action": "save", "total_time": 130, "time_zero": 3, "down": 3, "up": 1, "percent": 88, "share": []}]

    failed = False
    for i in range(len(analytics)):
        coeff = algo.engagement_mapping(analytics[i], 1)
        if coeff != 0.1:
            failed = True

    assert not failed

    
def test_update():
    
    user_id = '6bc3a6b4-568e-4e0b-bfcd-256231e03e7c'
    analytics = [{"article_id": "42724e2a2851bbd541210953ece2c6fd", "action": "done", "total_time": 30, "time_zero": 3, "down": 0, "up": 0, "percent": 0, "share": []},
                 {"article_id": "cc5cd5fd4348133200b5b3dd95b4f467", "action": "save", "total_time": 150, "time_zero": 3, "down": 2, "up": 0, "percent": 100, "share": []},
                 {"article_id": "87b68d146a9d38e716d6684df7d2fb95", "action": "done", "total_time": 20, "time_zero": 3, "down": 1, "up": 0, "percent": 100, "share": []},
                 {"article_id": "0acc061213d471991240343dcd9a0a37", "action": "done", "total_time": 150, "time_zero": 3, "down": 2, "up": 0, "percent": 100, "share": []},
                 {"article_id": "2ab20657329de532a4f211c0f297ae83", "action": "done", "total_time": 130, "time_zero": 3, "down": 3, "up": 1, "percent": 88, "share": []},
                 {"article_id": "5b8dfd5e3937f8a90698da487d2ad472", "action": "done", "total_time": 130, "time_zero": 3, "down": 8, "up": 0, "percent": 100, "share": ["twitter"]}]

    rule = algo.WeightedAverage(user_id)
    rule.learn(analytics)

    # need test condition
    assert False

def test_article_to_dna():

    # missing history, education, people, 
    topics_tests = [ [[u'Culture', 1], [u'Technology', 0.708148], [u'Business', 0.670305], [u'Science', 0.568386], [u'Leisure', 0.466582], [u'Politics', 0.438614]],
                     [[u'Culture', 1], [u'Health', 0.538165], [u'Politics', 0.519362], [u'Environment', 0.46733], [u'Leisure', 0.453688], [u'Nature', 0.39718]],
                     [[u'Politics', 1], [u'Law', 0.868527], [u'Culture', 0.671432], [u'Science', 0.528494], [u'Violence', 0.441865], [u'Belief', 0.367361]],
                     [[u'Technology', 1], [u'Science', 0.52817], [u'Business', 0.39163], [u'Nature', 0.277146], [u'Mathematics', 0.22946], [u'Belief', 0.223398]],
                     [[u'Science', 1], [u'Culture', 0.994332], [u'Nature', 0.603257], [u'Arts', 0.597176], [u'Weather', 0.402805], [u'Business', 0.402102]],
                     [[u'Sports', 1], [u'Leisure', 0.623654], [u'Language', 0.345093], [u'Belief', 0.202001], [u'Culture', 0.169815], [u'Environment', 0.0926147]]
                     ]
 


    results = [ str('[0.0, 0.0, 0.670305, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.466582, 0.0, 0.0, 0.0, 0.438614, 0.568386, 0.0, 0.708148, 0.0, 0.0]'),
                str('[0.0, 0.0, 0.0, 1.0, 0.0, 0.46733, 0.538165, 0.0, 0.0, 0.0, 0.453688, 0.0, 0.39718, 0.0, 0.519362, 0.0, 0.0, 0.0, 0.0, 0.0]'),
                str('[0.0, 0.367361, 0.0, 0.671432, 0.0, 0.0, 0.0, 0.0, 0.0, 0.868527, 0.0, 0.0, 0.0, 0.0, 1.0, 0.528494, 0.0, 0.0, 0.441865, 0.0]'),
                str('[0.0, 0.223398, 0.39163, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.22946, 0.277146, 0.0, 0.0, 0.52817, 0.0, 1.0, 0.0, 0.0]'),
                str('[0.597176, 0.0, 0.402102, 0.994332, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.603257, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.402805]'),
                str('[0.0, 0.202001, 0.0, 0.169815, 0.0, 0.0926147, 0.0, 0.0, 0.345093, 0.0, 0.623654, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]') ]

    correct = True
    for i in range(len(topics_tests)):
        if str(algo.article_to_dna_mapping(topics_tests[i])) != results[i]:
            correct = False
        
    assert correct
