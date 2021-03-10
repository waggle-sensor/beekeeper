#!/bin/bash


if [ -z "${KEY_GEN_ARGS}" ] ; then
    echo "Env variable KEY_GEN_ARGS not defined"
    exit 1
fi



if [ -e /usr/lib/waggle/registration_keys/id_rsa_sage_registration ] ; then
    echo id_rsa_sage_registration already exists
    exit 0
fi

set -e
set -x



mkdir -p /tmp/new_reg_keypair
rm -f /tmp/new_reg_keypair/*

ssh-keygen -f /tmp/new_reg_keypair/registration ${KEY_GEN_ARGS} -N ''
