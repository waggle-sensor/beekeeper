#!/bin/bash


cd ./bk-config

rm known_hosts register.pem register.pub register.pem-cert.pub


set -e

./create_client_files.sh bk-sshd 22 forever


# TODO: The known_hosts file did not work here for some reason

NEW_ID=$(docker run --rm  --network beekeeper_default -v `pwd`:/keys/:ro -w /keys -v beekeeper-config_bk-secrets:/usr/lib/waggle/:ro sagecontinuum/bk-config bash -c 'apt-get install -y jq ; ssh -o StrictHostKeyChecking=no  sage_registration@bk-sshd -p 22 -i register.pem register 0000000000000001 | jq -r -j .id' | tail -n 1)
if [ "${NEW_ID}_" != "node-0000000000000001_" ] ; then
  echo "registartion test failed, expected \"node-0000000000000001\", got \"${NEW_ID}\""
  exit 1
fi

echo "correct node_id was returned in registration process"

# verify node is in database

NEW_ID2=$(docker run --rm  --network beekeeper_default sagecontinuum/bk-config bash -c "curl bk-api:5000/state/0000000000000001 | jq -r -j .data.id")
if [ "${NEW_ID2}_" != "0000000000000001_" ] ; then
  echo "database test failed, expected \"0000000000000001\", got \"${NEW_ID2}\""
  exit 1
fi


echo "test successful."