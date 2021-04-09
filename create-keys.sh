#!/bin/bash


if [ "${1}_" != "native_" ] ; then


    docker run -it -v `pwd`:/workdir/:rw --workdir=/workdir --env KEY_GEN_TYPE=${KEY_GEN_TYPE}  waggle/waggle-pki-tools ./create-keys.sh native ${@}

    exit 0
fi


if [ "${2}_" == "_" ] ; then
    echo "Usage: ./create-keys.sh init"
    echo "       ./create-keys.sh cert <name> <validity_interval>"
    echo "       examples:"
    echo "         ./create-keys.sh cert until20211201 +20211201"
    echo "         ./create-keys.sh cert untilforever forever"
    exit 0
fi

set -e
export DATADIR=/workdir/beekeeper-keys
mkdir -p ${DATADIR}

if [ "${2}_" == "cert_" ] ; then
    ### REGISTRATION CERTIFICATE ###

    if [ "${3}_" == "_" ] ; then
        echo "Name for output directory is missing"
        exit 1
    fi

    if [ "${4}_" == "_" ] ; then
        echo "validity_interval for certificate is missing"
        exit 1
    fi

    # example: +20211201
    REL_OUTPUT_DIR="registration_certs/${3}"
    OUTPUT_DIR=${DATADIR}/${REL_OUTPUT_DIR}
    if [ -e ${OUTPUT_DIR} ] ; then
        echo "Error: Directory already exists: ${OUTPUT_DIR}"
        exit 1
    fi


    VALID=""
    if [ "${4}_" != "forever_"  ] ; then
    VALID="-V ${4}"
    fi
    set -x

    mkdir -p ${OUTPUT_DIR}
    cp ${DATADIR}/registration_keys/registration.pub ${OUTPUT_DIR}  # needed for creation of certificate
    cp ${DATADIR}/registration_keys/registration ${OUTPUT_DIR}      # needed on node for registartion (for convenience, we copy private key in directory with new certificate)
    ssh-keygen -I sage_registration -s ${DATADIR}/certca/beekeeper_ca_key -n sage_registration ${VALID} -O no-agent-forwarding -O no-port-forwarding -O no-pty -O no-user-rc -O no-x11-forwarding -O force-command=/opt/sage/beekeeper/register/register.sh ${OUTPUT_DIR}/registration.pub

    set +x
    echo ""
    echo ""
    echo "Output in ./beekeeper-keys/${REL_OUTPUT_DIR}"
    echo ""

    exit 0
fi

if [ "${2}_" != "init_" ] ; then
    echo "Unknown argument"
    exit 1
fi

### INIT ###

if [ -z "${KEY_GEN_TYPE}" ] ; then
    KEY_GEN_TYPE="ed25519"
fi

echo "KEY_GEN_TYPE: ${KEY_GEN_TYPE}"


if [ "${3}_" != "--nopassword_" ] ; then
    echo "Enter password for new CA:"
    read -s ca_password
else
    # needed for automated testing
    export ca_password=""
fi



set -e

### admin key-pair ###
if [ ! -e ${DATADIR}/admin/admin.pem  ] ; then
    set -x
    mkdir -p ${DATADIR}/admin
    ssh-keygen -f ${DATADIR}/admin/admin.pem -t ${KEY_GEN_TYPE} ${KEY_GEN_ARGS} -N ''
    set +x
fi


CERT_CA_TARGET_DIR="${DATADIR}/certca"
### CA ###
if [ ! -e ${CERT_CA_TARGET_DIR}/beekeeper_ca_key ] ; then


    mkdir -p ${CERT_CA_TARGET_DIR}

    echo ssh-keygen -f ${CERT_CA_TARGET_DIR}/beekeeper_ca_key -t ${KEY_GEN_TYPE} ${KEY_GEN_ARGS} -N "*****"
    ssh-keygen -f ${CERT_CA_TARGET_DIR}/beekeeper_ca_key -t ${KEY_GEN_TYPE} ${KEY_GEN_ARGS} -N "${ca_password}"


else
    echo "CA already exists"
fi

# beekeeper server key-pair and cert

if [ ! -e ${DATADIR}/bk-server/beekeeper_server_key-cert.pub ] ; then
    echo "creating beekeeper server key-pair and certificate... "


    CERT_SERVER_TARGET_DIR="${DATADIR}/bk-server"

    set -x
    mkdir -p ${CERT_SERVER_TARGET_DIR}


    # create key pair
    if [ ! -e ${CERT_SERVER_TARGET_DIR}/beekeeper_server_key ] ; then
        ssh-keygen -f ${CERT_SERVER_TARGET_DIR}/beekeeper_server_key -t ${KEY_GEN_TYPE} ${KEY_GEN_ARGS} -N ''
    fi
    set +x
    # sign key (creates beekeeper_server_key-cert.pub) This creates the sshd "HostCertificate" file
    echo sshpass -v -P passphrase -p "******"  ssh-keygen -I beekeeper_server -s ${CERT_CA_TARGET_DIR}/beekeeper_ca_key -h ${CERT_SERVER_TARGET_DIR}/beekeeper_server_key.pub
    sshpass -v -P passphrase -p "${ca_password}"  ssh-keygen -I beekeeper_server -s ${CERT_CA_TARGET_DIR}/beekeeper_ca_key -h ${CERT_SERVER_TARGET_DIR}/beekeeper_server_key.pub

else
    echo "beekeeper server key-pair and cert already exist"
fi


# registration key-pair (NOT reg certificate ! )

if [ ! -e ${DATADIR}/registration_keys/registration ] ; then

    mkdir -p ${DATADIR}/registration_keys/

    ssh-keygen -f ${DATADIR}/registration_keys/registration -t ${KEY_GEN_TYPE} ${KEY_GEN_ARGS} -N ''
else
    echo "reg key already exists"

fi