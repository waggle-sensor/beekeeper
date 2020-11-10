#!/bin/bash -e




if [ ! $# -eq 3 ]
  then
    echo "Usage: create_client_files.sh  HOST PORT MINUTES"
    echo ""
    echo "    example: create_client_files.sh host.docker.internal 20022 15"
    echo ""
    echo "     HOST: the name of the beekeeper host the client is going to connect to"
    echo "     PORT: the port of the above mentioned host"
    echo "     MINUTES: the length of time (in minutes) the certificate is valid for"
    echo ""
    exit 1
fi



set -x

docker run -i --rm --name bk-config -v `pwd`:/outputs/ -v beekeeper-config_bk-secrets:/usr/lib/sage/:ro sagecontinuum/bk-config create_client_files.sh $@


