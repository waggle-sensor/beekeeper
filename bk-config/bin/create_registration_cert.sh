#!/bin/bash



if [ $# -eq 0 ]
  then
    echo "Usage: create_registration_cert.sh MINUTES"
    echo ""
    echo "    MINUTES: the length of time (in minutes) the certificate is valid for"
    exit 1
fi


mkdir -p /sage_temporary
cp /usr/lib/sage/registration_keys/id_rsa_sage_registration.pub /sage_temporary/

set -e
set -x

ssh-keygen -I sage_registration -s /usr/lib/sage/certca/sage_beekeeper_ca -n sage_registration -V +${1}m -O no-agent-forwarding -O no-port-forwarding -O no-pty -O no-user-rc -O no-x11-forwarding -O force-command=/opt/sage/beekeeper/register/register.sh /sage_temporary/id_rsa_sage_registration.pub

ls /sage_temporary

set +x
cat /sage_temporary/id_rsa_sage_registration-cert.pub

