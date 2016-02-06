# Description
This application clones large LUSTRE filesystems by parallelizing the data copy between worker nodes.

In general it's a good idea to copy data in several passes. Migrating a large filesystem involves HPC cluster downtime, which can be minimised by copying most of the data from live filesystem and then finalising the copy during a downtime, when no changes are made by users.

(sourse: the filesystem with users' data. target: the filesystem where data is being migrated to.)

One copy pass can contain either of 3 actions:

* Copying the data. The files on source different from ones on target (including the case when those don't exist) are copied. Also involves creating folders on target.

* Delete. Needed for the final pass, when we want to delete files on target which were deleted by users from source after the last migration happened.

* Dirs mtime sync. After all changes to files are made on target filesystem, this pass will synchronize the target folders mtimes with ones on source to create an identical copy of the filesystem.



#Installation:

The /opt/rocks/etc/rabbitmq_data_move.conf file should have the data_move user password. This can be done by running rabbitmq_init.sh on rabbitmq server node. After that the file should be synced to all nodes that will perform the data migration. The /opt/rocks/etc/rabbitmq.conf file should contain the RabbitMQ server name.

#Configuring:

Most settings can be set in config.py file.

Example:

`USERNAME = 'data_move'`
used as rabbitmq virtual host and rabbitmq username, reads password from rabbitmq/rabbitmq_<username>.conf file

OLDEST_DATE = 90 * 24 * 60 * 60
filter files by atime. Files older than OLDEST_DATE won't be copied. To disable set to 0.

NEWEST_DATE =  0 #24 * 60 * 60
filter files by mtime. Files newer than NEWEST_DATE won't be copied. To disable set to 0.
Useful for initial pass: the files with recent mtime are likely to change soon. Should be set to 0 for end pass.

REPORT_INTERVAL = 30 # seconds
Minimal time between stats reports to memcached

source_mount = "/seahorse/dmishin/source"
Source filesystem mount point

target_mount = "/seahorse/dmishin/target"
Target filesystem mount point

#Running:



#Notes
2 MDS
graphite, memcached
3 passes
