#!/opt/python/bin/python
# -*- coding: utf-8 -*-

import settings

from celery import Celery
from celery.decorators import periodic_task
import sys

from config import *

with open('rabbitmq/rabbitmq.conf','r') as f:
    rabbitmq_server = f.read().rstrip()

with open('rabbitmq/rabbitmq_%s.conf'%USERNAME,'r') as f:
    rabbitmq_password = f.read().rstrip()

app = Celery(USERNAME, broker='amqp://%s:%s@%s/%s'%(USERNAME, rabbitmq_password, rabbitmq_server, USERNAME))
app.config_from_object(settings)


if __name__ == "__main__":
    
    if (len(sys.argv)< 2 ):
        print "Usage: %s [start|stop]"
        sys.exit

    if(str(sys.argv[1]) == "start"):
        app.send_task('cmover_del.procDir', args=["%s"%target_mount], kwargs={})
    elif(str(sys.argv[1]) == "stop"):
        app.control.broadcast('shutdown', destination=[])

    else:
        print "Wrong argument"
        sys.exit


