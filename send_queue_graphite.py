#!/usr/bin/env python

import socket
import time
import subprocess
import memcache
import os.path

cur_dir = os.path.dirname(os.path.realpath(__file__))
with open('%s/rabbitmq/rabbitmq.conf'%cur_dir,'r') as f:
    rabbitmq_server = f.read().rstrip()

CARBON_SERVER = 'graphite.sdsc.edu'
CARBON_PORT = 2003

sock = socket.socket()
sock.connect((CARBON_SERVER, CARBON_PORT))

start_time = int(time.time())

mc = memcache.Client(['%s:11211'%rabbitmq_server], debug=0)

for key in ("mover.dir", "mover.files", "mover_del.dir", "mover_del.files"):
        value = mc.get(key)
        if(value):
            message = 'system.hpc.datamove.bobcat_queue.%s %s %d\n' %(key, value, start_time)
            sock.sendall(message) # comment to test
            #print message
sock.close()
