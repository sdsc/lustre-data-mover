#!/usr/bin/env python

import socket
import time
import memcache
import os.path

cur_dir = os.path.dirname(os.path.realpath(__file__))
with open('%s/rabbitmq/rabbitmq.conf'%cur_dir,'r') as f:
    rabbitmq_server = f.read().rstrip()

mc = memcache.Client(['%s:11211'%rabbitmq_server], debug=0)

CARBON_SERVER = 'graphite.sdsc.edu'
CARBON_PORT = 2003

sock = socket.socket()
sock.connect((CARBON_SERVER, CARBON_PORT))

start_time = int(time.time())-15

for node in ["mover_7_1", "mover_7_2", "mover_7_3", "mover_7_4"]: # list of hostnames running workers
    for j in range(0,17): # max number of workers per node + 1
            for type in ["files", "dirs", "data"]:
                worker_type = 'file' if type in ['files', 'data'] else 'dir'
                worker_name = "cmover.%s_%s_%s.%s"%(worker_type, node, j, type)
                res = mc.get(worker_name)
                if(res):
                    mc.delete(worker_name)
                    message = 'system.hpc.datamove.%s %s %d\n' %(worker_name, res, start_time) # set your own prefix
                    sock.sendall(message) # comment to test
                    #print "%s"%message # uncomment to test

            for type in ["files", "dirs"]:
                worker_type = 'del_file' if type in ['files', 'data'] else 'del_dir'
                worker_name = "cmover.%s_%s_%s.%s"%(worker_type, node, j, type)
                res = mc.get(worker_name)
                if(res):
                    mc.delete(worker_name)
                    message = 'system.hpc.datamove.%s %s %d\n' %(worker_name, res, start_time) # set your own prefix
                    sock.sendall(message) # comment to test
                    #print "%s"%message # uncomment to test
sock.close()
