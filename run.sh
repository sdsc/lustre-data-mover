#!/bin/bash

DIRNAME=`dirname $0`
pushd $DIRNAME > /dev/null 2>&1 

export C_FORCE_ROOT=1 # allow serializing jobs to pickles; json serializer gives errors for filenames in weird encodings

worker=`hostname | sed s/\.local//g | sed s/-/_/g`


if [[ $1 = "try_f" ]]; then
    celery -A cmover -n "file_$worker" -c 1 -Q mover.files worker --pidfile=/var/run/celeryf_%n.pid -l debug
elif [[ $1 = "try_d" ]]; then
    celery -A cmover -n "dir_$worker" -c 1 -Q mover.dir worker --pidfile=/var/run/celeryd_%n.pid -l debug
else
    rm -f /var/log/cmover.lo*
    celery -A cmover -n "dir_$worker" -c 16 -Q mover.dir worker --detach --pidfile=/var/run/celeryd_%n.pid -l info
    celery -A cmover -n "file_$worker" -c 16 -Q mover.files worker --detach --pidfile=/var/run/celeryf_%n.pid -l info
fi


popd > /dev/null 2>&1
