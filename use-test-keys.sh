#!/bin/bash
set -e


SECRET_VOLUME="beekeeper-config_bk-secrets"



#if [ "${1}_" == "_" ] ; then
#    echo "./use-test-keys.sh "
#    exit 1
#fi



set +e
docker volume inspect ${SECRET_VOLUME}
if [ $? -eq 0 ] ; then
    echo "Error: Docker volume ${SECRET_VOLUME} already exists. Please delete first."
    exit 1
fi
set -e




set -x

docker volume create  ${SECRET_VOLUME}
pushd bk-config
docker build -t waggle/bk-config .
popd
docker create --name beekeeper-temporary -v ${SECRET_VOLUME}:/usr/lib/waggle/ waggle/bk-sshd

sleep 1
set +x
for folder in  bk-server certca registration_keys ; do
    set -x
    docker cp test-keys/${folder} beekeeper-temporary:/usr/lib/waggle/
    set +x
done

set -x
docker cp test-keys/test-nodes.txt beekeeper-temporary:/usr/lib/waggle/



docker rm beekeeper-temporary

set +x

