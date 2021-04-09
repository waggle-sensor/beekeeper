#!/bin/bash



### TEST REGISTRATION


DOCKER_NETWORK=$(docker network ls --format '{{.Name}}' | grep beekeeper)

echo "DOCKER_NETWORK: ${DOCKER_NETWORK}"

set -e
set -x



JSON=$(docker run -i --rm --network ${DOCKER_NETWORK} -v ${PWD}/beekeeper-keys/registration_certs/untilforever/:/untilforever/ waggle/beekeeper-api bash -c 'ssh -o StrictHostKeyChecking=no  sage_registration@bk-sshd -p 22 -i /untilforever/registration register 0000000000000001')
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
NEW_ID2=$(docker exec -i beekeeper_bk-api_1  bash -c "curl localhost:5000/state/0000000000000001" | jq -r -j .data.id)
set +x
if [ "${NEW_ID2}_" != "0000000000000001_" ] ; then
  echo "database test failed, expected \"0000000000000001\", got \"${NEW_ID2}\""
  exit 1
fi




### TEST BEEKEEPER API
set -x
docker exec beekeeper_bk-api_1 /bin/bash -c 'coverage run -m pytest -v  &&  coverage report -m --fail-under 85 --include=./*'
