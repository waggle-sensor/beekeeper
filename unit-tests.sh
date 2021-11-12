#!/bin/bash
set -x



curl localhost:5000/beehives -d '{"id": "my-beehive", "key-type": "rsa-sha2-256", "rmq-host":"host", "rmq-port": 5, "upload-host":"host", "upload-port": 6}'
cd test-data/beehive_ca
curl -F "tls-key=@tls/cakey.pem" -F "tls-cert=@tls/cacert.pem"  -F "ssh-key=@ssh/ca" -F "ssh-pub=@ssh/ca.pub" -F "ssh-cert=@ssh/ca-cert.pub"  localhost:5000/beehives/my-beehive


until docker exec -i beekeeper_bk-sshd_1 test -e /home_dirs/node-0000000000000001/rtun.sock
do
  echo waiting for /home_dirs/node-0000000000000001/rtun.sock
  sleep 1
done

### TEST BEEKEEPER API
set -x
docker exec beekeeper_bk-api_1 /bin/bash -c 'coverage run -m pytest -v  &&  coverage report -m --fail-under 85 --include=./*'


