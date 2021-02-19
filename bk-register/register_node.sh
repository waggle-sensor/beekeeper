#!/bin/bash


# This script registers a node an returns key-pair and certificates
# this is script expects a bk-register docker container



if [ $# -eq 0 ] ; then
    echo "Usage: ./register_node.sh <node-id>"
    exit 1
fi




mkdir -p temp
cd temp

if [ -e registration_result.json ] ; then
    echo "delete files first, e.g.  rm temp/*"
    exit 1
fi

set -e
set -x


docker exec -ti beekeeper_bk-register_1 curl 'localhost:80/register?id='${1} | jq . > ./registration_result.json



cat registration_result.json | jq -r ."private_key" > id_rsa-tunnel
cat registration_result.json | jq -r ."certificate" > id_rsa-tunnel-cert.pub
cat registration_result.json | jq -r ."public_key" > id_rsa-tunnel.pub

chmod 600 ./id_rsa-tunnel
set +x
echo ""
echo "Files creates in ./temp/ directory"
echo "--------------------"
ls -1
echo "--------------------"
