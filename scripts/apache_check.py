#!/usr/bin/python

# script is meant to be run by cron to check if apache2 is still running
# if not, restart apache2
#
# Note, once apache crashes, the first time it tends to crash frequently and the machine needs to be 
#   rebooted

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
p2 = subprocess.Popen(['grep', 'apache2'], stdin=p1.stdout, stdout=subprocess.PIPE)
p1.stdout.close()
output = p2.communicate()[0]

found = False
for line in output.split('\n'):
    if line.find('/usr/sbin/apache2') >= 0:
        found = True

if not found:
    log.warning('found apache2 not running.  restarting')
    subprocess.call(['sudo', 'service', 'apache2', 'start'])


        
