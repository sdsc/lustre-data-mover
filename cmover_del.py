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

import settings

from config import *

from cloghandler import ConcurrentRotatingFileHandler

from random import random

from os.path import relpath, exists, lexists, join, dirname, samefile, isfile, \
    islink, isdir, ismount
import os

from lustre import lustreapi

import subprocess

from celery import Celery
from celery.decorators import periodic_task
from billiard import current_process

import memcache

import shutil

clib = ctypes.CDLL('libc.so.6', use_errno=True)

logger = logging.getLogger(__name__)
rotateHandler = ConcurrentRotatingFileHandler("/var/log/cmover_del.log", "a", 128*1024*1024)
formatter = logging.Formatter('%(asctime)s - %(levelname)s [%(filename)s:%(lineno)s - %(funcName)20s()] - %(message)s')
rotateHandler.setFormatter(formatter)
logger.addHandler(rotateHandler)

REPORT_INTERVAL = 30 # seconds

with open('rabbitmq/rabbitmq.conf','r') as f:
    rabbitmq_server = f.read().rstrip()

with open('rabbitmq/rabbitmq_%s.conf'%USERNAME,'r') as f:
    rabbitmq_password = f.read().rstrip()

app = Celery(USERNAME, broker='amqp://%s:%s@%s/%s'%(USERNAME, rabbitmq_password, rabbitmq_server, USERNAME))
app.config_from_object(settings)

class ActionError(Exception):                                                                                                                                 
    pass

class LustreSource(object):

    SPLIT_FILES_CHUNK = 1000  # how many files to parse before passing job to others

    def procDir(self, dir):
        cur_depth = len(dir.split('/'))

        if(dir != target_mount and
            not os.path.exists(join(source_mount,
                       relpath(dir, target_mount)))):
        
            self.delDir(dir)
            return

        cur_files = []
        proc = subprocess.Popen([
            'lfs',
            'find',
            dir,
            '-maxdepth',
            '1',
            '!',
            '--type',
            'd'],
            stdout=subprocess.PIPE)
        while True:
            line = proc.stdout.readline().rstrip()
            if line:
                cur_files.append(line)
                if(len(cur_files) >= self.SPLIT_FILES_CHUNK):
                    procFiles.delay(cur_files)
                    cur_files = []
            else:
                if(len(cur_files)):
                    procFiles.delay(cur_files)
                    cur_files = []
                break
        proc.communicate()

        proc = subprocess.Popen([
            'lfs',
            'find',
            dir,
            '-maxdepth',
            '1',
            '-type',
            'd'],
            stdout=subprocess.PIPE)
        while True:
            line = proc.stdout.readline().rstrip()
            if line:
                if line != dir:
                    procDir.delay(line)
            else:
                break
        proc.communicate()

    def delDir(self, dir):
        try:
            shutil.rmtree(dir)
            #logger.warning("Deleting %s"%dir)
        except:
            logger.exception("Error removing dir %s"%dir)

    def safestat(self, filename):
        """lstat sometimes get Interrupted system calls; wrap it up so we can
        retry"""

        while True:
            try:
                statdata = os.lstat(filename)
                return statdata
            except IOError, error:
                if error.errno != 4:
                    raise



dataPlugin = LustreSource()

def get_mc_conn():
    mc = memcache.Client(['%s:11211'%rabbitmq_server], debug=0)
    return mc

def isProperDirection(path):
    if not path.startswith(target_mount):
        raise Exception("Wrong direction param, %s not starts with %s"%(path, target_mount)) 
    if (not ismount(source_mount)):
       logger.error("%s not mounted"%source_mount)
       raise Exception("%s not mounted"%source_mount) 
    if (not ismount(target_mount)):
       logger.error("%s not mounted"%target_mount)
       raise Exception("%s not mounted"%target_mount) 


def report_files_progress(copied_files):
    if(not STATS_ENABLED):
        return
    mc = get_mc_conn()
    if(copied_files):
        if(not mc.incr("%s.files"%get_worker_name(), "%s"%copied_files)):
            mc.set("%s.files"%get_worker_name(), "%s"%copied_files)
    mc.disconnect_all()

def safestat(filename, follow_symlink=False):
    while True:
        try:
            if(follow_symlink):
                return os.stat(filename)
            else:
                return os.lstat(filename)
        except IOError, error:
            if error.errno != 4:
                raise

def is_delete():
    return random() <= (percent_to_delete/100.0)

def checkFile(src, dst):
    try:
        if (not lexists(src)) or (percent_to_delete and is_delete()):
            os.remove(dst)
            #logger.warning("Deleting %s"%dst)
            return

    except:
        logger.exception("Error removing file %s"%dst)


@app.task(ignore_result=True)
def procDir(dir):
    isProperDirection(dir.rstrip())
    dataPlugin.procDir(dir)

    if(STATS_ENABLED):
        mc = get_mc_conn()
        if(not mc.incr("%s.dirs"%get_worker_name()) ):
            mc.set("%s.dirs"%get_worker_name(), "1")
        mc.disconnect_all()

@app.task(ignore_result=True)
def procFiles(files):

    copied_files = 0

    last_report = 0

    for file in files:

        isProperDirection(file)
        checkFile(
                join(source_mount, relpath(file,
                target_mount)),
                file)


        copied_files = copied_files+1

        if(time.time()-last_report > REPORT_INTERVAL):
            report_files_progress(copied_files)
            copied_files = 0
            last_report = time.time()

    report_files_progress(copied_files)

from cmover_del import procDir, procFiles

def get_worker_name():
    return "cmover.%s_%s"%(current_process().initargs[1].split('@')[1],current_process().index)

