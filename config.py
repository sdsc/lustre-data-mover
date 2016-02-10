#!/opt/python/bin/python
# -*- coding: utf-8 -*-

# used as rabbitmq virtual host and rabbitmq username, reads password from rabbitmq/rabbitmq_<username>.conf file
USERNAME = 'data_move'

# filter files by atime. Files older than OLDEST_DATE won't be copied. To disable set to 0.
OLDEST_DATE = 90 * 24 * 60 * 60

# filter files by mtime. Files newer than NEWEST_DATE won't be copied. To disable set to 0.
# Useful for initial passes: the files with recent mtime are likely to change soon. Should be set to 0 for end pass.
NEWEST_DATE =  0 #24 * 60 * 60

# Minimal time between reports to memcached
REPORT_INTERVAL = 30 # seconds

# Send stats to memcached
STATS_ENABLED = True

# Copy from
source_mount = "/seahorse/dmishin/source"

# Copy to
target_mount = "/seahorse/dmishin/target"
