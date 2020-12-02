
This container 


```bash

docker build -t sagecontinuum/bk-config .

```



# Create CA and beekeeper key-pairs and certificates and registration key (NOT registration cert)

```bash
cd ..
./init-keys.sh new
```

Afterwards you can start beekeeper.


# create client files (e.g. for a node) 

```bash
./create_client_files.sh  HOST PORT MINUTES

# for docker:
./create_client_files.sh host.docker.internal 20022 15


# for vagrant (if beekeeper runs on the host):
./create_client_files.sh 10.0.2.2 20022 15


```


# registration example:


```bash
ssh -o UserKnownHostsFile=./known_hosts  sage_registration@localhost -p 20022 -i id_rsa_sage_registration register 0000000000000001
```


OR within bk-config container
```bash
ssh -o UserKnownHostsFile=./known_hosts  sage_registration@bk-sshd -p 22 -i registration_keys/id_rsa_sage_registration register 0000000000000001
```


# example: copy key files into vagrant

```bash
cp known_hosts register.pem register.pem-cert.pub ~/git/waggle-edge-stack/ansible/private/
```

ansible will copy these files if detected