#!/opt/python/bin/python
# -*- coding: utf-8 -*-

import settings

from celery import Celery
from celery.decorators import periodic_task
import sys, os.path
from celery.task.control import revoke

from config import *

cur_dir = os.path.dirname(os.path.realpath(__file__))

with open('%s/rabbitmq/rabbitmq.conf'%cur_dir,'r') as f:
    rabbitmq_server = f.read().rstrip()

with open('%s/rabbitmq/rabbitmq_%s.conf'%(cur_dir, USERNAME),'r') as f:
    rabbitmq_password = f.read().rstrip()

app = Celery(USERNAME, broker='amqp://%s:%s@%s/%s'%(USERNAME, rabbitmq_password, rabbitmq_server, USERNAME))
app.config_from_object(settings)


if __name__ == "__main__":
    
    if (len(sys.argv)< 2 ):
        print "Usage: %s [start|stop]"
        sys.exit

    if(str(sys.argv[1]) == "start"):
        app.send_task('cmover.procDir', args=["%s"%source_mount,0], kwargs={})
    elif(str(sys.argv[1]) == "stop"):
        app.control.broadcast('shutdown')

    else:
        print "Wrong argument"
        sys.exit


