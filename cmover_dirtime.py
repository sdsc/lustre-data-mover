#!/opt/python/bin/python
# -*- coding: utf-8 -*-

import logging
import json
import sys
import stat
import ctypes
import time
import copy
import datetime
import shutil

import settings

from config import *

from cloghandler import ConcurrentRotatingFileHandler

from random import normalvariate

from os.path import relpath, exists, lexists, join, dirname, samefile, isfile, \
    islink, isdir, ismount
import os
import re

from lustre import lustreapi

import subprocess

from celery import Celery
from celery.decorators import periodic_task
from billiard import current_process

import memcache

clib = ctypes.CDLL('libc.so.6', use_errno=True)

logger = logging.getLogger(__name__)
rotateHandler = ConcurrentRotatingFileHandler("/var/log/cmover_dir.log", "a", 5*1024*1024*1024)
formatter = logging.Formatter('%(asctime)s - %(levelname)s [%(filename)s:%(lineno)s - %(funcName)20s()] - %(message)s')
rotateHandler.setFormatter(formatter)
logger.addHandler(rotateHandler)

REPORT_INTERVAL = 30 # seconds

with open('rabbitmq/rabbitmq.conf','r') as f:
    rabbitmq_server = f.read().rstrip()

with open('rabbitmq/rabbitmq_%s.conf'%USERNAME,'r') as f:
    rabbitmq_password = f.read().rstrip()

exceptions = []
if (isfile('exceptions')):
    with open('exceptions','r') as f:
        exceptions = f.read().splitlines()                                                                                                                              

app = Celery(USERNAME, broker='amqp://%s:%s@%s/%s'%(USERNAME, rabbitmq_password, rabbitmq_server, USERNAME))
app.config_from_object(settings)

class ActionError(Exception):                                                                                                                                 
    pass

class LustreSource(object):

    def procDir(self, dir):
        cur_depth = len(dir.split('/'))

        if(dir != source_mount):
            self.fixDir(dir, join(target_mount,
                           relpath(dir, source_mount)))

        proc = subprocess.Popen([
            'lfs',
            'find',
            dir,
            '-maxdepth',
            '1',
            '-type',
            'd'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while True:
            line = proc.stdout.readline().rstrip()
            if line:
                if line != dir:
                    procDir.delay(line)
            else:
                break
        while True:
            line = proc.stderr.readline().rstrip()
            if line:
                logger.error("Got error scanning %s folder: %s"%(dir, line))
            else:
                break

    def fixDir(self, sourcedir, destdir):

        if not exists(sourcedir):
            return

        if not exists(destdir):
            logger.error("Destdir not exist %s"%destdir)

        sstat = self.safestat(sourcedir)
        dstat = self.safestat(destdir)
        if(sstat.st_atime != dstat.st_atime or sstat.st_mtime != dstat.st_mtime):
            os.utime(destdir, (sstat.st_atime, sstat.st_mtime))

    def safestat(self, filename, follow_symlink=False):
        while True:
            try:
                if(follow_symlink):
                    return os.stat(filename)
                else:
                    return os.lstat(filename)
            except IOError, error:
                if error.errno != 4:
                    raise



dataPlugin = LustreSource()

def get_mc_conn():
    mc = memcache.Client(['%s:11211'%rabbitmq_server], debug=0)
    return mc

def isProperDirection(path):
    if not path.startswith(source_mount):
        raise Exception("Wrong direction param, %s not starts with %s"%(path, source_mount)) 
    if (not ismount(source_mount)):
       logger.error("%s not mounted"%source_mount)
       raise Exception("%s not mounted"%source_mount) 
    if (not ismount(target_mount)):
       logger.error("%s not mounted"%target_mount)
       raise Exception("%s not mounted"%target_mount) 

@app.task(ignore_result=True)
def procDir(dir):
    isProperDirection(dir.rstrip())
    if(not dir.startswith( tuple(exceptions) )):
        dataPlugin.procDir(dir)

    mc = get_mc_conn()
    if(not mc.incr("%s.dirs"%get_worker_name()) ):
        mc.set("%s.dirs"%get_worker_name(), "1")
    mc.disconnect_all()

from cmover_dirtime import procDir

def get_worker_name():
    return "cmover.%s_%s"%(current_process().initargs[1].split('@')[1],current_process().index)

