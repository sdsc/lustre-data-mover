#!/bin/bash
admin_pass=$(< /dev/urandom tr -dc _A-Z-a-z-0-9 | head -c26)
/usr/sbin/rabbitmqctl add_user data_move ${admin_pass}
/usr/sbin/rabbitmqctl add_vhost data_move
/usr/sbin/rabbitmqctl set_permissions -p data_move data_move ".*" ".*" ".*"
/usr/sbin/rabbitmqctl set_permissions -p data_move admin ".*" ".*" ".*"
mkdir -p rabbitmq
echo "${admin_pass}" > rabbitmq/rabbitmq_data_move.conf
chmod 400 rabbitmq/rabbitmq_data_move.conf

hostname > rabbitmq/rabbitmq.conf
