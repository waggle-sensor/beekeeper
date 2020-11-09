#!/bin/bash


if [ -e /usr/lib/sage/certca/sage_beekeeper_ca ] ; then
    echo CA already exists..
    exit 0
fi 

set -e
set -x

mkdir -p /usr/lib/sage/certca

ssh-keygen -f /usr/lib/sage/certca/sage_beekeeper_ca -t rsa -b 4096 -N ''