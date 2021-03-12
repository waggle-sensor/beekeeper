#!/bin/bash

export REG_DIR="/usr/lib/waggle/registration_keys"

if [ $# -ne 2 ]
  then
    echo "Usage: create_registration_cert.sh REG-KEY VALID"
    echo ""
    echo "    VALID: the length of time the certificate is valid for"
    echo "            examples: +3m (3 minutes) , +52w (52 weeks) , forever"
    echo ""
    echo "    REG-KEY: any of these public files"
    ls -1 ${REG_DIR}
    echo ""
    exit 1
fi


if [ "${1}_" == "_"  ] ; then
  echo "Valid argument missing"
  exit 1
fi

if [ "${2}_" == "_"  ] ; then
  echo "Valid argument missing"
  exit 1
fi

VALID=""
if [ "${2}_" != "forever_"  ] ; then
  VALID="-V ${2}"
fi

export REG_PUB_KEY=${1}

if [ ! -e  ${REG_DIR}/${REG_PUB_KEY}  ] ; then
  echo "File ${REG_PUB_KEY} not found"
  echo "$(ls -1 ${REG_DIR} | wc -l) registration files available:"
  ls -1 ${REG_DIR}
  exit 1
fi

set -e
set -x


mkdir -p /tmp/new_reg
rm -f /tmp/new_reg/*

# the public registration key is in a directory ssh-keygen cannot write to, thus we copy it
cp ${REG_DIR}/${REG_PUB_KEY} /tmp/new_reg/

# this only needs the public registration key (an CA of course) as input
ssh-keygen -I sage_registration -s /usr/lib/waggle/certca/beekeeper_ca_key -n sage_registration ${VALID} -O no-agent-forwarding -O no-port-forwarding -O no-pty -O no-user-rc -O no-x11-forwarding -O force-command=/opt/sage/beekeeper/register/register.sh /tmp/new_reg/${REG_PUB_KEY}

# creates certificate for key
# ssh-keygen -I certificate_identity -s ca_key [-hU] [-D pkcs11_provider]
#                [-n principals] [-O option] [-V validity_interval]
#                [-z serial_number] file ...
# -I certificate_identity
# -s ca_key     : identifies CA
# -n principals : Specify one or more principals (user or host names) to be included in a certificate when signing a key.
# -V validity_interval

