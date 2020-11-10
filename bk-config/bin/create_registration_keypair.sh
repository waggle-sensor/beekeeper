#!/bin/bash



if [ -e /usr/lib/sage/registration_keys/id_rsa_sage_registration ] ; then
    echo id_rsa_sage_registration already exists
    exit 0
fi

set -e
set -x



mkdir -p /usr/lib/sage/registration_keys

ssh-keygen -f /usr/lib/sage/registration_keys/id_rsa_sage_registration -t rsa -b 4096 -N ''
