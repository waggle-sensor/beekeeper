#!/bin/bash

# Using a admin user did not work, it did not have file permisison to access the reverse ssh tuinnel socket.
#if ! id "admin" &>/dev/null; then
#
#    set -x
#    adduser admin --disabled-password --gecos ""
#    set +x
#else
#    echo "admin user already exists"
#fi

# create keys

if [ ! -e /root/.ssh/authorized_keys ] ; then

    set -e
    set -x


    mkdir -p /root/keys/
    ssh-keygen -f /root/keys/admin.pem -t rsa -b 4096 -N ''

    mkdir -p /root/.ssh/
    cp /root/keys/admin.pem.pub /root/.ssh/authorized_keys
    chmod 644 /root/.ssh/authorized_keys

    set +x

fi

set -x
/usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
