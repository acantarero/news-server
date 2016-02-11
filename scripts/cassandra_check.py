#!/usr/bin/python

# script is meant to be run by cron to check if cassandra is still running
# if not, restart cassandra and webserver services

import logging
import subprocess
import sys
import time

sys.path.append('/home/ubuntu/noozli-server/src')

import logger

log = logging.getLogger('noozli_error')
log.setLevel(logging.INFO)
if not log.handlers:
    log.addHandler(logger.NoozliHandler('error.log'))

p1 = subprocess.Popen(['ps', '-aux'], stdout=subprocess.PIPE)
p2 = subprocess.Popen(['grep', 'cassandra'], stdin=p1.stdout, stdout=subprocess.PIPE)
p1.stdout.close()
output = p2.communicate()[0]

found = False
for line in output.split('\n'):
    if line.find('java') >= 0 and line.find('/usr/share/cassandra') >= 0:
        found = True

if not found:
    log.warning('found cassandra not running.  restarting')
    subprocess.call(['nohup', 'sudo', 'cassandra'])
    time.sleep(120)
    subprocess.call(['sudo', 'service', 'apache2', 'reload'])


        
