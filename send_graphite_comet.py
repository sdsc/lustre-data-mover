#!/usr/bin/env python

import socket
import time
import memcache

with open('rabbitmq/rabbitmq.conf','r') as f:
    rabbitmq_server = f.read().rstrip()

mc = memcache.Client(['%s:11211'%rabbitmq_server], debug=0)

CARBON_SERVER = 'graphite.hostname.edu'
CARBON_PORT = 2003

sock = socket.socket()
sock.connect((CARBON_SERVER, CARBON_PORT))

start_time = int(time.time())-15

for node in ["14_01", "14_02", "14_03", "14_04", "14_05", "14_06", "14_07", "14_08", "17_06","17_23","17_41","17_42","17_43","17_44","17_45","17_46","25_02","25_03","25_04","25_05","25_06","25_07","25_08","25_09"]: # list of hostnames running workers
    for j in range(0,16): # max number of workers per node + 1
            for type in ["files", "dirs", "data"]:
                worker_type = 'file' if type in ['files', 'data'] else 'dir'
                worker_name = "cmover.%s_%s_%s.%s"%(worker_type, node, j, type)
                res = mc.get(worker_name)
                if(res):
                    mc.delete(worker_name)
                    message = 'system.hpc.datamove.%s %s %d\n' %(worker_name, res, start_time) # set your own prefix
                    sock.sendall(message) # comment to test
                    #print "%s"%message # uncomment to test
sock.close()

