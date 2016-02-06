#!/bin/bash

module load python

DIRNAME=`dirname $0`
pushd $DIRNAME > /dev/null 2>&1 

export C_FORCE_ROOT=1 # allow serializing jobs to pickles; json serializer gives errors for filenames in weird encodings

worker=`hostname | sed s/\.local//g | sed s/-/_/g`

rm -f /var/log/cmover.lo*

celery -A cmover -n "dir_$worker" -c 8 -Q mover.dir worker --detach --pidfile=/var/run/celeryd_%n.pid -l info
celery -A cmover -n "file_$worker" -c 8 -Q mover.files worker --detach --pidfile=/var/run/celeryf_%n.pid -l info

popd > /dev/null 2>&1
