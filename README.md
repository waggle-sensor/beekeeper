# Beekeeper Server

The beekeeper server is the administration server for the SAGE cyberinfrastructure.
All nodes must register with the beekeeper in order to be added to the SAGE ecosystem.

The beekeeper is responsible for the following:
1. front end for provisioning and administrative management of all nodes
2. certificate authority responsible for generating and validating all
communication keys used by the nodes (i.e. services running on them)
3. administrative portal for collecting the general health of all nodes


## start beekeeper

```bash
docker-compose up --build
```







# registration example:


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





## Unit Testing

Unit-testing is executed via
- `./unit-tests.sh`

Requires running docker-compose enviornment.