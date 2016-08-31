#!/usr/bin/env python

import socket
import time
import subprocess
import memcache
import os.path

cur_dir = os.path.dirname(os.path.realpath(__file__))
with open('%s/rabbitmq/rabbitmq.conf'%cur_dir,'r') as f:
    rabbitmq_server = f.read().rstrip()

mc = memcache.Client(['%s:11211'%rabbitmq_server], debug=0)

rabbit_stats = subprocess.Popen(["/usr/sbin/rabbitmqctl", "list_queues", "-p", "data_move"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
out, err = rabbit_stats.communicate()
for stat in out.splitlines():
    if(stat.startswith("mover")):
        (key, value) = stat.split()
        mc.set(key, value)
        #print ("%s %s"%(key,value))
