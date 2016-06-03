#!/bin/bash

DIRNAME=`dirname $0`
pushd $DIRNAME > /dev/null 2>&1 

export C_FORCE_ROOT=1 # allow serializing jobs to pickles; json serializer gives errors for filenames in weird encodings

worker=`hostname |  sed s/\.local//g | sed s/-/_/g`

celery -A cmover -n "dir_$worker" -c 4 -Q mover.dir worker --pidfile=/var/run/celeryd_%n.pid -l debug

popd > /dev/null 2>&1
