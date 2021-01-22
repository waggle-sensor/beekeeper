#!/bin/bash

export REG_PUB_KEY="id_rsa_sage_registration.pub"

if [ $# -eq 0 ]
  then
    echo "Usage: create_registration_cert.sh VALID"
    echo ""
    echo "    the length of time the certificate is valid for"
    echo "    examples: +3m (3 minutes) , +52w (52 weeks) , forever"
    exit 1
fi


if [ "${1}_" == "_"  ] ; then
  echo "Valid argument missing"
  exit 1
fi

VALID=""
if [ "${1}_" != "forever_"  ] ; then
  VALID="-V ${1}"
fi




set -e
set -x

mkdir -p /sage_temporary
cp /usr/lib/sage/registration_keys/${REG_PUB_KEY} /sage_temporary/


ssh-keygen -I sage_registration -s /usr/lib/sage/certca/sage_beekeeper_ca -n sage_registration ${VALID} -O no-agent-forwarding -O no-port-forwarding -O no-pty -O no-user-rc -O no-x11-forwarding -O force-command=/opt/sage/beekeeper/register/register.sh /sage_temporary/${REG_PUB_KEY}

# creates certificate for key
# ssh-keygen -I certificate_identity -s ca_key [-hU] [-D pkcs11_provider]
#                [-n principals] [-O option] [-V validity_interval]
#                [-z serial_number] file ...
# -I certificate_identity
# -s ca_key     : identifies CA
# -n principals : Specify one or more principals (user or host names) to be included in a certificate when signing a key.
# -V validity_interval


set +x

if [ ! -e /sage_temporary/id_rsa_sage_registration-cert.pub ] ; then
  echo "error, file not created: /sage_temporary/id_rsa_sage_registration-cert.pub"
  exit 1
fi

cp /sage_temporary/id_rsa_sage_registration-cert.pub ./register.pem-cert.pub
