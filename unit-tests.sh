#!/bin/bash



### TEST REGISTRATION

echo "waiting for registration service"
while [ "$(docker exec -i beekeeper_bk-register_1 curl localhost)_" != "Beekeeper Registration Server_" ] ; do sleep 2 ; done

set -e
set -x

JSON=$(docker exec -i beekeeper_bk-sshd_1 bash -c 'ssh -o StrictHostKeyChecking=no  sage_registration@bk-sshd -p 22 -i /usr/lib/waggle/registration_keys/registration register 0000000000000001')
set +x
echo "JSON: ${JSON}"
echo "---------------------------"
NEW_ID=$(echo ${JSON} | jq -r -j .id | tail -n 1)

if [ "${NEW_ID}_" != "node-0000000000000001_" ] ; then
  echo "registration test failed, expected \"node-0000000000000001\", got \"${NEW_ID}\""
  exit 1
fi

echo "correct node_id was returned in registration process"

# verify node is in database
set -x
NEW_ID2=$(docker exec -i beekeeper_bk-api_1  ash -c "curl localhost:5000/state/0000000000000001" | jq -r -j .data.id)
set +x
if [ "${NEW_ID2}_" != "0000000000000001_" ] ; then
  echo "database test failed, expected \"0000000000000001\", got \"${NEW_ID2}\""
  exit 1
fi




### TEST BEEKEEPER API
set -x
docker exec beekeeper_bk-api_1 /bin/ash -c 'coverage run -m pytest -v  &&  coverage report -m --fail-under 90'
