#!/bin/bash

# Using a admin user did not work, it did not have file permisison to access the reverse ssh tuinnel socket.
#if ! id "admin" &>/dev/null; then
#
#    set -x
#    adduser admin --disabled-password --gecos ""
#    set +x
#else
#    echo "admin user already exists"
#fi



if [ -z "${KEY_GEN_TYPE}" ] ; then
    echo "Env variable KEY_GEN_TYPE not defined"
    exit 1
fi

set -e

# create keys
echo "USE_CONFIG_VOLUME: ${USE_CONFIG_VOLUME}"

if [ "${USE_CONFIG_VOLUME}_" == "1_" ] ; then

    if [ ! -e /usr/lib/waggle/admin/admin.pem  ] ; then
        set -x
        mkdir -p /usr/lib/waggle/admin
        ssh-keygen -f /usr/lib/waggle/admin/admin.pem -t ${KEY_GEN_TYPE} ${KEY_GEN_ARGS} -N ''
        set +x
    fi

    if [ ! -e /root/.ssh/authorized_keys ] ; then
        set -x
        mkdir -p /root/.ssh/
        cp /usr/lib/waggle/admin/admin.pem.pub /root/.ssh/authorized_keys
        chmod 644 /root/.ssh/authorized_keys
        set +x
    fi

else
    # kubernetes

    if [ ! -s /root/.ssh/authorized_keys ] ; then
        set -x
        mkdir -p /root/keys/
        ssh-keygen -f /root/keys/admin.pem -t ${KEY_GEN_TYPE} ${KEY_GEN_ARGS} -N ''
        set +x
    fi

fi





INFINITE_WAIT=0
# create CA if needed


if [ -e /usr/lib/waggle/certca/beekeeper_ca_key ] ; then
    echo "CA already exists.."
else

    if [ -e "/usr/lib/waggle/certca" ] && [ ! -w "/usr/lib/waggle/certca" ] ; then
        # in case of kubernetes (optional secret is not mounted, but volume is not writeable)
        CERT_CA_TARGET_DIR="/new_config/certca"
        INFINITE_WAIT=1
    else
        CERT_CA_TARGET_DIR="/usr/lib/waggle/certca"
    fi

    set -x
    mkdir -p ${CERT_CA_TARGET_DIR}

    ssh-keygen -f ${CERT_CA_TARGET_DIR}/beekeeper_ca_key -t ${KEY_GEN_TYPE} ${KEY_GEN_ARGS} -N ''
    set +x
fi

# beekeeper server key-pair and cert

if [ ! -e /usr/lib/waggle/bk-server/beekeeper_server_key-cert.pub ] ; then
    echo "creating beekeeper server key-pair and certificate... "

    if [ -e "/usr/lib/waggle/bk-server" ] &&  [ ! -w "/usr/lib/waggle/bk-server" ] ; then
        # in case of kubernetes (optional secret is not mounted, but volume is not writeable)
        CERT_SERVER_TARGET_DIR="/new_config/bk-server"
        INFINITE_WAIT=1
    else
        CERT_SERVER_TARGET_DIR="/usr/lib/waggle/bk-server"
    fi

    set -x
    mkdir -p ${CERT_SERVER_TARGET_DIR}


    # create key pair
    ssh-keygen -f ${CERT_SERVER_TARGET_DIR}/beekeeper_server_key -t ${KEY_GEN_TYPE} ${KEY_GEN_ARGS} -N ''

    # sign key (creates beekeeper_server_key-cert.pub)
    ssh-keygen -I beekeeper_server -s ${CERT_CA_TARGET_DIR}/beekeeper_ca_key -h ${CERT_SERVER_TARGET_DIR}/beekeeper_server_key.pub
    set +x
else
    echo "beekeeper server key-pair and cert already exist"
fi


if [ "${USE_CONFIG_VOLUME}_" == "1_" ] ; then
    # this happens only in docker-compose enviornment
    echo "creating registration key"
    if [ ! -e /usr/lib/waggle/registration_keys/registration ] ; then
        set -x
        create_registration_keypair.sh
        mkdir -p /usr/lib/waggle/registration_keys/
        mv /tmp/new_reg_keypair/registration* /usr/lib/waggle/registration_keys/

        create_registration_cert.sh registration.pub forever
        cp /tmp/new_reg/registration-cert.pub /usr/lib/waggle/registration_keys/
        set +x
    fi



fi



if [ ${INFINITE_WAIT} -eq 1 ] ; then

    echo "This container was started without credentials. Because the config directory is not writable, new credentials have been created in /new_config/."
    echo " Download credentials (kubectl cp ...) and create kubernetes secrets. (see documentation for details)"
    sleep infinity
    exit 1
fi

set -x
/usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
