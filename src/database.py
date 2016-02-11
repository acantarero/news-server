"""
database.py
routines to access cassandra

cassandra is currently storing:

-  all user data
-  all article interaction data (coming soon)
-  all source data (coming soon)
"""

from cassandra.cluster import Cluster
import datetime
import json
import logger
import logging
import uuid

log = logging.getLogger('noozli_api')
log.setLevel(logging.INFO)
if not log.handlers:
#    log.addHandler(logger.NoozliStreamingHandler())
    log.addHandler(logger.NoozliHandler('api.log'))

class NoozliClient:
    session = None

    def connect(self, nodes):
        cluster = Cluster(nodes)
        metadata = cluster.metadata
        self.session = cluster.connect()
        log.info('Connected to cluster: ' + metadata.cluster_name)
        for host in metadata.all_hosts():
            log.info('Datacenter: %s; Host: %s; Rack: %s', host.datacenter, host.address, host.rack)

        self.user_create_cql = self.session.prepare("""
           INSERT INTO noozli.users (id, dna, article_serve_algo, dna_update_algo, danger_metric, danger_fix, engagement_mapping)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """)

        self.query_user_cql = self.session.prepare("SELECT * FROM noozli.users WHERE id = ?;")
        self.query_dna_cql = self.session.prepare("SELECT dna FROM noozli.users WHERE id = ?;")
        self.query_if_served_cql = self.session.prepare("SELECT * FROM noozli.users_served WHERE user_id = ? AND article_id = ?;")
        self.query_article_algo_cql = self.session.prepare("SELECT article_serve_algo FROM noozli.users WHERE id = ?;")



    def close(self):
        self.session.cluster.shutdown()
        self.session.shutdown()
        log.info('Connection closed.')
        
        
    def create_schema(self):
        """
        Run once to create schema
        """

        self.session.execute("""
            CREATE KEYSPACE noozli WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};
            """
         )
        
        self.session.execute("""
            CREATE TABLE noozli.users (
                id uuid PRIMARY KEY,
                dna text,
                article_serve_algo int,
                dna_update_algo int,
                danger_metric int,
                danger_fix int,
                engagement_mapping int
            );
            """
        )

        self.session.execute("""
            CREATE TABLE noozli.users_served (
                user_id uuid,
                article_id text,
                PRIMARY KEY (user_id, article_id)
            );
        """
        )

        self.session.execute("""
            CREATE TABLE noozli.user_articles_ordered (
               user_id uuid,
               event_time timeuuid,
               analytics text,
               PRIMARY KEY (user_id, event_time))
             WITH CLUSTERING ORDER BY (event_time DESC);
        """
        )
        
        self.session.execute("""
            CREATE TABLE noozli.user_articles (
               user_id uuid,
               article_id text,
               analytics text,
               PRIMARY KEY (user_id, article_id)
            );
        """
        )

        self.session.execute("""
            CREATE TABLE noozli.articles (
               article_id text,
               event_time timeuuid,
               analytics text,
               PRIMARY KEY (article_id, event_time)
            );
        """
        )

        self.session.execute("""
            CREATE TABLE noozli.sources (
                month_year text,
                source text,
                event_time timeuuid,
                analytics text,
                PRIMARY KEY ((source, month_year), event_time)
            );
        """
        )
        

        # eventually need articles table
        # sources table
        # user-sources table

        log.info('Noozli keyspace and schema created.')

    def delete_keyspace(self, name):

        ### this does not work for some reason
        self.session.execute("DROP KEYSPACE %s;", ['noozli'])
        log.info('Removed keyspace: ' + name)

    #
    # Accessors
    #

    def check_user_exists(self, user_id):
        results = self.session.execute(self.query_user_cql.bind((uuid.UUID(user_id),)))
        if len(results) == 0:
            return False
        else:
            return True
        
        
    def check_if_served(self, user_id, article_id):        
        results = self.session.execute(self.query_if_served_cql.bind((uuid.UUID(user_id),article_id)))
        if len(results) >= 1:
            return True
        else:
            return False

    def get_dna(self, user_id):
        results = self.session.execute(self.query_dna_cql.bind((uuid.UUID(user_id),)))
        if len(results) > 1:
            log.warning('more than one row with id: ' + user_id)
        return json.loads(results[0].dna)['dna']

    def find_user(self, user_id):
        results = self.session.execute(self.query_user_cql.bind((uuid.UUID(user_id),)))
        if len(results) > 1:
            log.warning('more than one row with id: ' + user_id)
        return results[0]

    def get_article_algo(self, user_id):
        results = self.session.execute(self.query_article_algo_cql.bind((uuid.UUID(user_id),)))
        if len(results) > 1:
            log.warning('more than one row with id: ' + user_id)
        return results[0][0]

    def get_analytics(self, user_id, count):
        results = self.session.execute("SELECT analytics FROM noozli.user_articles_ordered WHERE user_id = " + user_id + " ORDER BY event_time DESC LIMIT " + str(count) + ";")
        return results

    #
    # Database modification methods
    # 

    def create_user(self, user_id):
        """
        create a new user in the database

        user_id:uuid
        """

        dna = []
        for i in range(20):
            dna.append(float(0.5))

        dna_string = '{"dna": ' + str(dna) + '}'

        self.session.execute(self.user_create_cql.bind((
                    uuid.UUID(user_id),
                    dna_string,
                    1, 1, 1, 1, 1,
                    ))
        )

    def add_served_articles(self, user_id, article_ids):
        """
        add articles sent to a client to the database to prevent serving the same article more than once
        
        user_id:uuid - user that was sent articles
        article_ids:list[str] - list of article ids to add to the user database for user with user_id
        """
        
        cql_command = "BEGIN BATCH\n"
        for i in range(len(article_ids)):
            cql_command += "INSERT INTO noozli.users_served (user_id, article_id) VALUES (" + user_id + ", '" + article_ids[i] + "') USING TTL 2595600\n"
        cql_command += "APPLY BATCH;"

        self.session.execute(cql_command)
        return True


    def add_article_analytics(self, user_id, article_ids, analytics_strings, sources):
        """
        store analytics for each article for a user
        
        user_id:string - string version of uuid for a user
        article_ids:list<string> - list of strings of article ids
        analytics_strings:list<string> - list of strings representations of json containing all analytics data
        sources:list<string> - list of the sources for each article
        """

        month_year_str = datetime.datetime.utcnow().strftime("%Y-%m")
        cql_command = "BEGIN BATCH\n"
        for i in range(len(article_ids)):
            cql_command += "INSERT INTO noozli.user_articles (user_id, article_id, analytics) VALUES (" + user_id + ", '" + article_ids[i] + "', '" + analytics_strings[i]  + "')\n" 
            cql_command += "INSERT INTO noozli.articles (article_id, event_time, analytics) VALUES ('" + article_ids[i] + "', now(), '" + analytics_strings[i]  + "')\n" 
            cql_command += "INSERT INTO noozli.sources (month_year, source, event_time, analytics) VALUES ('" + month_year_str + "', '" + sources[i] + "', now(), '" + analytics_strings[i]  + "')\n" 
            cql_command += "INSERT INTO noozli.user_articles_ordered (user_id, event_time, analytics) VALUES (" + user_id + ", now(), '" + analytics_strings[i] + "')\n"
        cql_command += "APPLY BATCH;"

        self.session.execute(cql_command)
        return True
