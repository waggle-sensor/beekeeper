# Beekeeper Server

The beekeeper server is the administration server for the cyberinfrastructure.
All nodes must register with the beekeeper in order to be added to the ecosystem.

The beekeeper is responsible for the following:
1. front end for provisioning and administrative management of all nodes
2. certificate authority responsible for generating and validating all
communication keys used by the nodes (i.e. services running on them)
3. administrative portal for collecting the general health of all nodes


## start beekeeper

The docker-compose file has override values for different local dev environments. 

Here is a list of files:
1. `docker-compose.vm.yml`: overrides node1 service with a vm cloned repo (manually by the user).

Setup for each override docker-compose `.yml` file (same enumeration as above):
1. Setup
    ```
    git clone git@github.com:iperezx/node-platforms.git
    ```

Generate keys:
```bash
./create-keys.sh init --nopassword
./create-keys.sh cert untilforever forever
```
Note: Options above like `--nopassword` and `forever` should not be used in production.

Start beekeeper with no overriden values:
```
docker-compose up --build
```

Start beekeeper with overriden values depending on the use-case:
1. Setup
    ```
    docker-compose -f docker-compose.yml -f docker-compose.vm.yml up --build
    ```

# Register a beehive with beekeeper (example)

1) The first step creates a beehive but credentials will be missing.
```bash
kubectl port-forward service/beekeeper-api 5000:5000  # if needed

curl localhost:5000/beehives -d '{"id": "my-beehive", "key-type": "rsa-sha2-256", "rmq-host":"host", "rmq-port": 5, "upload-host":"host", "upload-port": 6}'
```
Verify:
```bash
curl localhost:5000/beehives | jq .
```

2) Create beehive (not beekeeper) CA credentials: [https://github.com/waggle-sensor/waggle-pki-tools](https://github.com/waggle-sensor/waggle-pki-tools)

3) Add credentials for beehive to beekeeper
```bash
cd test-data/beehive_ca
curl -F "tls-key=@tls/cakey.pem" -F "tls-cert=@tls/cacert.pem"  -F "ssh-key=@ssh/ca" -F "ssh-pub=@ssh/ca.pub" -F "ssh-cert=@ssh/ca-cert.pub"  localhost:5000/beehives/my-beehive
```

Verify
```bash
curl localhost:5000/beehives/my-beehive | jq .
```
# assign node to a beehive

This will only work once node has registered.

```bash
curl localhost:5000/node/0000000000000001 -d '{"assign_beehive": "my-beehive"}'
curl localhost:5000/node/0000000000000001 -d '{"deploy_wes": true}'
```

Check the logs:
```bash
docker logs beekeeper_bk-api_1
```

SSH to the node (via reverse ssh tunnel)
```bash
ssh -i ./beekeeper-keys/nodes-key/nodes.pem -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o IdentitiesOnly=true -o ProxyCommand="ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@localhost -p 2201 -i ./beekeeper-keys/admin/admin.pem  netcat -U /home_dirs/node-0000000000000001/rtun.sock" root@foo
```


# Node registration example:


```bash
ssh -o UserKnownHostsFile=./known_hosts  sage_registration@localhost -p 20022 -i id_rsa_sage_registration register 0000000000000001
```


OR within bk-config container
```bash
ssh -o UserKnownHostsFile=./known_hosts  sage_registration@bk-sshd -p 22 -i registration_keys/id_rsa_sage_registration register 0000000000000001
```


`/etc/ssh/ssh_known_hosts` example:
```text
@cert-authority beehive.honeyhouse.one ssh-ed25519 AAAAC.....
```



# example: copy key files into vagrant

```bash
cp known_hosts register.pem register.pem-cert.pub ~/git/waggle-edge-stack/ansible/private/
```

ansible will copy these files if detected

# create Certs for node

Got to the directory that contains your `beekeeper-keys` folder. Copy `create-keys.sh`, then create the certificate file, for example:
```
cp ~/git/beekeeper/create-keys.sh .
./create-keys.sh cert until20220530 +20220530
```



## Unit Testing

Unit-testing is executed via
- `./unit-tests.sh`

Requires running docker-compose enviornment.

## Development

### Access MySQL Console

```sh
docker-compose exec db mysql -u root -ptesttest -D Beekeeper
```

### Access Shell on Test Node

```sh
docker-compose exec node1 bash
```
