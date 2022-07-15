#!/bin/bash
set -x

#
# Note that the pytests delete nodes_log table !
#

curl -s localhost:5000/beehives -d '{"id": "my-beehive", "key-type": "rsa-sha2-256", "rmq-host":"host", "rmq-port": 5, "upload-host":"host", "upload-port": 6}'

# TODO(sean) If we're going to use test keys which are valid forever, we may as well hard code them as test
# data. Then, we can just init new beehives with a function.
(
cd test-data/beehive_ca
curl -s -F "tls-key=@tls/cakey.pem" -F "tls-cert=@tls/cacert.pem"  -F "ssh-key=@ssh/ca" -F "ssh-pub=@ssh/ca.pub" -F "ssh-cert=@ssh/ca-cert.pub"  localhost:5000/beehives/my-beehive
)

# NOTE(sean) --no-TTY allows docker-compose exec to run correctly in CI.
until docker-compose exec --no-TTY bk-sshd test -e /home_dirs/node-0000000000000001/rtun.sock; do
  echo waiting for /home_dirs/node-0000000000000001/rtun.sock
  sleep 1
done

### TEST BEEKEEPER API
set -x
docker-compose exec bk-api /bin/bash -c 'coverage run -m pytest -v &&  coverage report -m --fail-under 85 --include=./*'
