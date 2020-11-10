#!/bin/bash



CONTAINER_CMD='docker run -i --rm --network beekeeper_default --name bk-config -v beekeeper-config_bk-secrets:/usr/lib/sage/:ro sagecontinuum/bk-config'



if [ ! $# -eq 3 ]
  then
    echo "Usage: create_client_files.sh  HOST PORT MINUTES"
    echo ""
    echo "    example: create_client_files.sh host.docker.internal 20022 15"
    echo ""
    exit 1
fi


FILES="known_hosts id_rsa_sage_registration-cert.pub id_rsa_sage_registration id_rsa_sage_registration.pub"
# sage_beekeeper_ca.pub should not be needed, key is alreadu in known_hosts

for file in ${FILES} ; do 
  if [ -e ${file} ] ; then
      echo "File ${file} already exists. Delete first."
      echo "To delete all files: rm ${FILES}"
      exit 1
  fi 
done

set -e
set -x


${CONTAINER_CMD} create_known_hosts_file.sh host.docker.internal 20022 > ./known_hosts

${CONTAINER_CMD} create_registration_cert.sh $3 | tail -n 1 > ./register-cert.pub

docker cp beekeeper_bk-sshd_1:/usr/lib/sage/registration_keys/id_rsa_sage_registration ./register.pem
docker cp beekeeper_bk-sshd_1:/usr/lib/sage/registration_keys/id_rsa_sage_registration.pub ./register.pub
#docker cp beekeeper_bk-sshd_1:/usr/lib/sage/certca/sage_beekeeper_ca.pub .

OUTPUT_FILES="known_hosts register.pem register.pub register-cert.pub"
set +x

for file in ${OUTPUT_FILES} ; do 
  if [ ! -e ${file} ] ; then
      echo "File ${file} missing. Something went wrong"
      exit 1
  fi 
done

echo "files created:"
echo "${OUTPUT_FILES}"