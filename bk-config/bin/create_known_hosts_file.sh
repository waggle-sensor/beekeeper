#!/bin/bash


if [ ! -e /usr/lib/waggle/bk-server/id_rsa_sage_beekeeper.pub ] ; then
    echo "beekeeper public key not found!"
    exit 1
fi


if [ $# -eq 0 ]
  then
    echo "Usage: create_known_hosts_file.sh HOST PORT"
    echo ""
    echo "    example: create_known_hosts_file.sh host.docker.internal 20022"
    echo ""
    echo "   HOST: the name of the beekeeper host the client is going to connect to"
    echo "   PORT: the port of the above mentioned host"
    echo ""
    exit 1
fi

# example prefix [host.docker.internal]:20022

echo '['$1']:'$2 $(cat /usr/lib/waggle/bk-server/id_rsa_sage_beekeeper.pub)
