#!/bin/bash -e




if [ ! $# -eq 3 ]
  then
    echo "Usage: create_client_files.sh  HOST PORT VALID"
    echo ""
    echo "    example: create_client_files.sh host.docker.internal 20022 15"
    echo ""
    echo "     HOST: the name of the beekeeper host the client is going to connect to"
    echo "     PORT: the port of the above mentioned host"
    echo "     VALID: +3m (3 minutes) , +52w (52 weeks) , forever"
    echo ""
    exit 1
fi



set -x
docker build -t sagecontinuum/bk-config .
docker run -i --rm --name bk-config -v `pwd`:/outputs/ -v beekeeper-config_bk-secrets:/usr/lib/waggle/:ro sagecontinuum/bk-config create_client_files.sh $@


