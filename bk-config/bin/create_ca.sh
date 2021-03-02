#!/bin/bash


if [ -e /usr/lib/waggle/certca/sage_beekeeper_ca ] ; then
    echo "CA already exists.."
    exit 0
fi

set -e
set -x

mkdir -p /usr/lib/waggle/certca

ssh-keygen -f /usr/lib/waggle/certca/sage_beekeeper_ca -t rsa -b 4096 -N ''