#!/bin/bash


if [ ! -e /usr/lib/sage/certca/sage_beekeeper_ca.pub ] ; then
    echo CA public key not found!
    exit 1
fi 


if [ $# -eq 0 ]
  then
    echo "Usage: create_known_hosts_file.sh HOST PORT"
    echo ""
    echo "    example: create_known_hosts_file.sh host.docker.internal 20022"
    echo ""
    exit 1
fi

# example prefix [host.docker.internal]:20022

echo '['$1']:'$2 $(cat /usr/lib/sage/certca/sage_beekeeper_ca.pub)
