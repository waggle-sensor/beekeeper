#!/bin/bash
set -x

#
# Note that the pytests delete nodes_log table !
#

curl localhost:5000/beehives -d '{"id": "my-beehive", "key-type": "rsa-sha2-256", "rmq-host":"host", "rmq-port": 5, "upload-host":"host", "upload-port": 6}'

# TODO(sean) If we're going to use test keys which are valid forever, we may as well hard code them as test
# data. Then, we can just init new beehives with a function.
(
cd test-data/beehive_ca
curl -F "tls-key=@tls/cakey.pem" -F "tls-cert=@tls/cacert.pem"  -F "ssh-key=@ssh/ca" -F "ssh-pub=@ssh/ca.pub" -F "ssh-cert=@ssh/ca-cert.pub"  localhost:5000/beehives/my-beehive
)


until docker-compose exec bk-sshd test -e /home_dirs/node-0000000000000001/rtun.sock; do
  echo waiting for /home_dirs/node-0000000000000001/rtun.sock
  sleep 1
done

### TEST BEEKEEPER API
set -x
docker-compose exec bk-api /bin/bash -c 'coverage run -m pytest -v &&  coverage report -m --fail-under 85 --include=./*'
