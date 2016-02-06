#!/bin/bash

module load python

DIRNAME=`dirname $0`
pushd $DIRNAME > /dev/null 2>&1 

export C_FORCE_ROOT=1 # allow serializing jobs to pickles; json serializer gives errors for filenames in weird encodings

worker=`hostname | sed s/\.local//g | sed s/-/_/g`

rm -f /var/log/cmover_del.lo*

celery -A cmover_del -n "del_file_"$worker -c 8 -Q "mover"$PREFIX"_del.files" worker --pidfile=/var/run/celeryfdel_%n.pid -l debug

popd > /dev/null 2>&1
