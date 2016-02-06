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

from os.path import lexists, relpath, exists, join, dirname, samefile, isfile, \
    islink, isdir, ismount
import os

from lustre import lustreapi

import subprocess

from celery import Celery
from celery.decorators import periodic_task
from billiard import current_process

import memcache


clib = ctypes.CDLL('libc.so.6', use_errno=True)

logger = logging.getLogger(__name__)
rotateHandler = ConcurrentRotatingFileHandler("/var/log/cmover.log", "a", 128*1024*1024)
formatter = logging.Formatter('%(asctime)s - %(levelname)s [%(filename)s:%(lineno)s - %(funcName)20s()] - %(message)s')
rotateHandler.setFormatter(formatter)
logger.addHandler(rotateHandler)

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

    SPLIT_FILES_CHUNK = 1000  # how many files to parse before passing job to others

    def procDir(self, dir, mds_num):
        cur_depth = len(dir.split('/'))

        if(dir != source_mount):
            #logger.info("Creating dir %s"%dir)
            self.createDir(dir, join(target_mount,
                           relpath(dir, source_mount)), mds_num)

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
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
        while True:
            line = proc.stderr.readline().rstrip()
            if line:
                logger.error("Got error scanning %s folder: %s"%(dir, line))
            else:
                break

        proc = subprocess.Popen([
            'lfs',
            'find',
            dir,
            '-maxdepth',
            '1',
            '-type',
            'd'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        cur_mds_num = 0
        while True:
            line = proc.stdout.readline().rstrip()
            if line:
                if line != dir:
                    procDir.delay(line, cur_mds_num)
            else:
                break
            cur_mds_num = 1-cur_mds_num
        while True:
            line = proc.stderr.readline().rstrip()
            if line:
                logger.error("Got error scanning %s folder: %s"%(dir, line))
            else:
                break

    def createDir(self, sourcedir, destdir, mds_num):

        if not exists(sourcedir):
            return

        if not exists(destdir):
            level = len(filter(None, destdir.replace(target_mount,'').split("/")))
            if(level > 1):
                os.mkdir(destdir)
            else:
                subprocess.Popen(['lfs setdirstripe -i %s %s'%(mds_num, destdir)], 
                    shell=True).communicate()

        sstat = self.safestat(sourcedir)
        dstat = self.safestat(destdir)
        if(sstat.st_mode != dstat.st_mode):
            os.chmod(destdir, sstat.st_mode)
        if((sstat.st_uid != dstat.st_uid) or (sstat.st_gid != dstat.st_gid)):
            os.chown(destdir, sstat.st_uid, sstat.st_gid)
        
        slayout = lustreapi.getstripe(sourcedir)
        dlayout = lustreapi.getstripe(destdir)
        if slayout.isstriped() != dlayout.isstriped() or slayout.stripecount != dlayout.stripecount:
            lustreapi.setstripe(destdir, stripecount=slayout.stripecount)

    def copyFile(self, src, dst):
        try:
            logger.debug("looking at %s"%src)
            srcstat = self.safestat(src)
            mode = srcstat.st_mode
            size = srcstat.st_size
            blksize = srcstat.st_blksize

            if OLDEST_DATE and srcstat.st_atime + OLDEST_DATE \
                < int(time.time()):
                if stat.S_ISLNK(mode): # check the mtime of file which symlink points to. If new, copy symlink
                    linkstat = self.safestat(src, follow_symlink=True)
                    if(linkstat.st_atime + OLDEST_DATE) \
                        < int(time.time()):
                        return
                else:
                    return

            if NEWEST_DATE and srcstat.st_mtime + NEWEST_DATE \
                > int(time.time()):
                if stat.S_ISLNK(mode): # check the mtime of file which symlink points to. If new, copy symlink
                    linkstat = self.safestat(src, follow_symlink=True)
                    if(linkstat.st_mtime + NEWEST_DATE) \
                        > int(time.time()):
                        return
                else:
                    return

            # regular files

            if stat.S_ISREG(mode):
                layout = lustreapi.getstripe(src)
                if layout.stripecount < 16:
                    count = layout.stripecount
                else:
                    count = -1

                done = False
                while not done:
                    try:
                        if exists(dst):
                            deststat = self.safestat(dst)
                            if srcstat.st_size == deststat.st_size \
                                and srcstat.st_mtime == deststat.st_mtime \
                                and srcstat.st_uid == deststat.st_uid \
                                and srcstat.st_gid == deststat.st_gid \
                                and srcstat.st_mode == deststat.st_mode:
                                return

                            # file exists; blow it away

                            os.remove(dst)
                            #logger.warn('%s has changed' % dst)
                        lustreapi.setstripe(dst, stripecount=count)
                        done = True
                    except IOError, error:
                        if error.errno != 17:
                            raise
                        logger.warn('Restart %s' % dst)

                copied_data = self.bcopy(src, dst, blksize)
                os.chown(dst, srcstat.st_uid, srcstat.st_gid)
                os.chmod(dst, srcstat.st_mode)
                os.utime(dst, (srcstat.st_atime, srcstat.st_mtime))
                return copied_data

            # symlinks

            if stat.S_ISLNK(mode):
                linkto = os.readlink(src)
                try:
                    os.symlink(linkto, dst)
                except OSError, error:
                    if error.errno == 17:
                        os.remove(dst)
                        os.symlink(linkto, dst)
                    else:
                        raise
                try:
                    os.lchown(dst, srcstat.st_uid, srcstat.st_gid)
                    return
                except OSError, error:
                    raise

            logger.error("Unknown filetype %s"%src)
        except:
            logger.exception("Error copying file %s"%src)

    def fadviseSeqNoCache(self, fileD):
        """Advise the kernel that we are only going to access file-descriptor
        fileD once, sequentially."""

        POSIX_FADV_SEQUENTIAL = 2
        POSIX_FADV_DONTNEED = 4
        offset = ctypes.c_int64(0)
        length = ctypes.c_int64(0)
        clib.posix_fadvise(fileD, offset, length, POSIX_FADV_SEQUENTIAL)
        clib.posix_fadvise(fileD, offset, length, POSIX_FADV_DONTNEED)

    def bcopy(
        self,
        src,
        dst,
        blksize,
        ):

        try:
            with open(src, 'rb') as infile:
                with open(dst, 'wb') as outfile:
                    self.fadviseSeqNoCache(infile.fileno())
                    self.fadviseSeqNoCache(outfile.fileno())
                    logger.debug("bcopy %s"%src)
                    tot_size = 0
                    while True:
                        data = infile.read(blksize)
                        if not data:
                            break
                        outfile.write(data)
                        tot_size += len(data)
                    return tot_size
        except:
            logger.exception('Error copying %s'%src)

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

def report_files_progress(copied_files, copied_data):
    mc = get_mc_conn()
    if(copied_files):
        if(not mc.incr("%s.files"%get_worker_name(), "%s"%copied_files)):
            mc.set("%s.files"%get_worker_name(), "%s"%copied_files)

    if(copied_data):
        if(not mc.incr("%s.data"%get_worker_name(), "%s"%copied_data)):
            mc.set("%s.data"%get_worker_name(), "%s"%copied_data)
    mc.disconnect_all()

@app.task(ignore_result=True)
def procDir(dir, mds_num):
    isProperDirection(dir.rstrip())
    if(not dir.startswith( tuple(exceptions) )):
        dataPlugin.procDir(dir, mds_num)

    mc = get_mc_conn()
    if(not mc.incr("%s.dirs"%get_worker_name()) ):
        mc.set("%s.dirs"%get_worker_name(), "1")
    mc.disconnect_all()

@app.task(ignore_result=True)
def procFiles(files):

    copied_files = 0
    copied_data = 0

    last_report = 0

    for file in files:

        if(file.startswith( tuple(exceptions) )):
            return

        isProperDirection(file)
        copied_data_cur = dataPlugin.copyFile(file,
                join(target_mount, relpath(file,
                source_mount)))

        if(copied_data_cur):
            copied_data = copied_data + copied_data_cur
        copied_files = copied_files+1

        if(time.time()-last_report > REPORT_INTERVAL):
            report_files_progress(copied_files, copied_data)
            copied_files = 0
            copied_data = 0
            last_report = time.time()

    report_files_progress(copied_files, copied_data)

from cmover import procDir, procFiles

def get_worker_name():
    return "cmover.%s_%s"%(current_process().initargs[1].split('@')[1],current_process().index)
