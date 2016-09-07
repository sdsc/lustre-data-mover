# Description
This application clones large LUSTRE filesystems by parallelizing the data copy between worker nodes.

In general it's a good idea to copy data in several passes. Migrating a large filesystem involves HPC cluster downtime, which can be minimised by copying most of the data from live filesystem and then finalising the copy during a downtime, when no changes are made by users.

One copy pass can contain either of 3 actions:

* Copying the data. The files on source different from ones on target (including the case when those don't exist) are copied. Also involves creating folders on target.

* Delete. Needed for the final pass, when we want to delete files on target which were deleted by users from source after the last migration happened.

* Dirs mtime sync. After all changes to files are made on target filesystem, this pass will synchronize the target folders mtimes with ones on source to create an identical copy of the filesystem.

_(source: the filesystem with users' data; target: the filesystem where data is being migrated to)_

On the first run during the first-level folders creation on target filesystem the folders will be alternated between 2 MDS'es (0 and 1). THis is done to better balance the load in case we have 2 MDS. Adjust the code if needed otherwise.

#Dependencies:
* RabbitMQ server
* Python (tested with 2.7)
* Celery python package
* Memcached server
* Lustre filesystems mounted on all mover nodes
* Graphite server for statistics collection
* cloghandler python package
* put lustreapi.py from pcp project ( https://github.com/wtsi-ssg/pcp/blob/master/pcplib/lustreapi.py ) and its required liblustreapi.so module into "lustre" folder

#Configuring:

All celery task files are using  rabbitmq/rabbitmq.conf and rabbitmq/rabbitmq_data_move.conf files to connect to the rabbitmq server.

The rabbitmq/rabbitmq_data_move.conf file should have the data_move user password. To set a password and create the file run rabbitmq_init.sh script on rabbitmq server. The file should be synced to all nodes which will perform the data migration. The rabbitmq/rabbitmq.conf file should contain the RabbitMQ server hostname. Same hostname will be used for memcached server.

Most data migration settings can be set in config.py file:

```USERNAME = 'data_move'```

used as rabbitmq virtual hostname and rabbitmq username. The passord for the user should be in rabbitmq/rabbitmq_<username>.conf file

```OLDEST_DATE = 90 * 24 * 60 * 60```

filter files by atime. Files older than OLDEST_DATE won't be copied. To disable set to 0.

```NEWEST_DATE =  0 #24 * 60 * 60```

filter files by mtime. Files newer than NEWEST_DATE won't be copied. To disable set to 0.
Useful for initial pass: the files with recent mtime are likely to be changed by a user during the migration. Should be set to 0 for the final pass.

```STATS_ENABLED = True```

Enable statistics to memcached

```REPORT_INTERVAL = 30 # seconds```

Minimal time interval between stats reports

```source_mount = "/mnt/source"```

Source filesystem mount point

```target_mount = "/mnt/target"```

Target filesystem mount point

#Running:

To start regular file copy celery workers on a node, run run.sh script. The run_del.sh script will run delete workers, and run_dirtime.sh runs directories mtime fix workers. To run the same scripts in debug mode, use "try_f" (files worker) and "try_d" (dirs worker) parameters for run.sh and run_del.sh scripts. Those will run in foreground and display all debugging information.

By default scripts run 16 file and 16 dir celery workers, which connect to RabbitMQ server and wait for a job to perform.

Once all workers have been started, an initial message should be added to the queue containing the root location of source filesystem. To start files copy run:

```python cmover_control.py start```

To start files delete pass:

```python cmover_control_del.py start```

To start folders mtime fix pass:

```python cmover_control_dirtime.py start```

To stop operation and shutdown all the workers, run:

```python cmover_control.py stop```

This will stop all the workers in virtual host. To send the command to a specific node, modify the cmover_control<_*>.py file and add destination parameter, f.e.:

```app.control.broadcast('shutdown', destination=["celery@file_node02", "celery@dir_node02"])```

The workers pool on all nodes can be extended by n workers with command:

```celery control -A cmover_control pool_grow n```

or on a single node:
```celery control -A cmover_control -d "celery@file_<hostname>" pool_grow n ```

To get the list of current tasks for all nodes:

```celery inspect active -A cmover_control```

#Monitoring:

The statistics of data moving process can be collected by a graphite server. The send_graphite.py script collects known fields from memcached service and sends these to graphite. The script can be run periodically with a crontab task at the frequency defined in graphite for the collection.

