
This container 


```bash

docker build -t sagecontinuum/bk-config .

```



# Create CA and beekeeper key-pairs and certificates and registration key (NOT registration cert)

```bash
docker run -ti --rm --network beekeeper_default --name bk-config -v beekeeper-config_bk-secrets:/usr/lib/sage/ sagecontinuum/bk-config


init-keys.sh
```

Afterwards you can start beekeeper.


# create client files (e.g. for a node) 

```bash
./create_client_files.sh
```


# registration example:


```bash
ssh -o UserKnownHostsFile=./known_hosts  sage_registration@localhost -p 20022 -i id_rsa_sage_registration register 0000000000000001
```


OR within bk-config container
```bash
ssh -o UserKnownHostsFile=./known_hosts  sage_registration@bk-sshd -p 22 -i registration_keys/id_rsa_sage_registration register 0000000000000001
```