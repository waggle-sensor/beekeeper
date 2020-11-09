


```bash

docker build -t sagecontinuum/bk-config .


docker run -ti --rm --network beekeeper_default --name bk-config -v beekeeper-config_bk-secrets:/usr/lib/sage/ sagecontinuum/bk-config
```



# Create CA and beekeeper key-pairs and certificates and registration key

```bash
init-keys.sh
```

Afterwards you can start beekeeper.


# create client files (e.g. node) 

a) known_hosts file (`ssh -o UserKnownHostsFile=...`)

```bash
create_known_hosts_file.sh host.docker.internal 20022
```

b) Time-limited registration certificate (time limit !)
```bash
create_registration_cert.sh
```



copy via sshd container to disk:
docker cp beekeeper_bk-sshd_1:/usr/lib/sage/registration_keys/id_rsa_sage_registration .
docker cp beekeeper_bk-sshd_1:/usr/lib/sage/registration_keys/id_rsa_sage_registration.pub .
docker cp beekeeper_bk-sshd_1:/usr/lib/sage/registration_keys/id_rsa_sage_registration-cert.pub .
docker cp beekeeper_bk-sshd_1:/usr/lib/sage/certca/sage_beekeeper_ca.pub .
OR (if you have a local virtual waggle)

mkdir -p ~/git/waggle-node/private/
docker cp beekeeper_bk-sshd_1:/usr/lib/sage/registration_keys/id_rsa_sage_registration ~/git/waggle-node/private/register.pem
docker cp beekeeper_bk-sshd_1:/usr/lib/sage/registration_keys/id_rsa_sage_registration-cert.pub ~/git/waggle-node/private/register.pem-cert.pub
docker cp beekeeper_bk-sshd_1:/usr/lib/sage/certca/sage_beekeeper_ca.pub ~/git/waggle-node/private/sage_beekeeper_ca.pub



registration process:


ssh -o UserKnownHostsFile=sage_beekeeper_ca.pub  sage_registration@localhost -p 20022 -i id_rsa_sage_registration register 0000000000000001

OR within bk-config container
ssh -o UserKnownHostsFile=certca/sage_beekeeper_ca.pub  sage_registration@bk-sshd -p 22 -i registration_keys/id_rsa_sage_registration register 0000000000000001