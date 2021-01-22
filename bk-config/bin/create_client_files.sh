#!/bin/bash -e



if [ ! $# -eq 3 ]
  then
    echo "Usage: create_client_files.sh  HOST PORT VALID"
    echo ""
    echo "    example: create_client_files.sh host.docker.internal 20022 15"
    echo ""
    echo "     HOST: the name of the beekeeper host the client is going to connect to"
    echo "     PORT: the port of the above mentioned host"
    echo "     VALID: +3m (3 minutes) , +52w (52 weeks) , forever"
    echo ""
    exit 1
fi


cd /outputs

OUTPUT_FILES="known_hosts register.pem register.pub register.pem-cert.pub"

# sage_beekeeper_ca.pub should not be needed, key is alreadu in known_hosts

for file in ${OUTPUT_FILES} ; do 
  if [ -e ${file} ] ; then
      echo "File ${file} already exists. Delete first."
      echo "To delete all files:   rm ${OUTPUT_FILES}"
      exit 1
  fi 
done

set -e
set -x


create_known_hosts_file.sh $1 $2 > ./known_hosts

# create certificate and name it ./register.pem-cert.pub
create_registration_cert.sh $3 


# copy other files
cp /usr/lib/sage/registration_keys/id_rsa_sage_registration ./register.pem
cp /usr/lib/sage/registration_keys/id_rsa_sage_registration.pub ./register.pub



set +x

for file in ${OUTPUT_FILES} ; do 
  if [ ! -e ${file} ] ; then
      echo "File ${file} missing. Something went wrong"
      exit 1
  fi 
done

echo "files created:"
echo "${OUTPUT_FILES}"