import logging.handlers

class NoozliHandler(logging.handlers.RotatingFileHandler):

    def __init__(self, filename='noozli.log'):

        logging.handlers.RotatingFileHandler.__init__(self,'/home/ubuntu/noozli-server/log/'+filename, maxBytes=5242880, backupCount=10)
        fmt = '%(asctime)s - %(filename)s - %(levelname)s - %(message)s'
        fmt_date = '%Y-%m-%dT%T%Z'        
        formatter = logging.Formatter(fmt, fmt_date)
        
        self.setFormatter(formatter)


class NoozliStreamingHandler(logging.StreamHandler):

    def __init__(self):

        logging.StreamHandler.__init__(self)
        fmt = '%(asctime)s - %(filename)s - %(levelname)s - %(message)s'
        fmt_date = '%Y-%m-%dT%T%Z'        
        formatter = logging.Formatter(fmt, fmt_date)
        
        self.setFormatter(formatter)
