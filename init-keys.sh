#!/bin/bash
set -e


SECRET_VOLUME="beekeeper-config_bk-secrets"



if [ "${1}_" == "_" ] ; then
    echo "./init-keys.sh [new|test]"
    echo "     new: create new CA and server keys"
    echo "     test: use existing test CA and server keys (WARNING: only for testing/development"
    exit 1
fi



set +e
docker volume inspect ${SECRET_VOLUME}
if [ $? -eq 0 ] ; then
    echo "Error: Docker volume ${SECRET_VOLUME} already exists. Please delete first."
    exit 1
fi
set -e


if [ "${1}_" == "new_" ] ; then

    set -x
    pushd bk-config
    docker build -t sagecontinuum/bk-config .
    popd
    docker run --rm --name bk-config -v ${SECRET_VOLUME}:/usr/lib/waggle/ sagecontinuum/bk-config init-keys.sh

    set +x
    exit 0
fi

if [ "${1}_" == "test_" ] ; then
    set -x

    docker volume create  ${SECRET_VOLUME}
    pushd bk-config
    docker build -t sagecontinuum/bk-config .
    popd
    docker create --name beekeeper-temporary -v ${SECRET_VOLUME}:/usr/lib/waggle/ sagecontinuum/bk-config

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
    exit 0
fi


echo "Error: Argument ${1} not supported"
exit 1
