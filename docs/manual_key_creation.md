

This document contains commands to help developing and testing beekeeper.

# go into sshd container

docker exec -it beekeeper_bk-sshd_1 /bin/bash


# create reg key certificate

```bash
cd /tmp
cp /usr/lib/waggle/registration_keys/id_rsa_sage_registration.pub .
cp /usr/lib/waggle/registration_keys/id_rsa_sage_registration .

chmod 600 id_rsa_sage_registration

ssh-keygen -I sage_registration -s /usr/lib/waggle/certca/beekeeper_ca_key -n sage_registration -O no-agent-forwarding -O no-port-forwarding -O no-pty -O no-user-rc -O no-x11-forwarding -O force-command=/opt/sage/beekeeper/register/register.sh ./id_rsa_sage_registration.pub
```


# do registration (on the node)
```bash
ssh -o UserKnownHostsFile=./known_hosts sage_registration@localhost -p 22 -i id_rsa_sage_registration register 0000000000000001  > test.txt

apt-get install -y jq
cat test.txt | jq -r ."private_key" > id_rsa-tunnel
cat test.txt | jq -r ."certificate" > id_rsa-tunnel-cert.pub
cat test.txt | jq -r ."public_key" > id_rsa-tunnel.pub

chmod 600 id_rsa-tunnel
```

# create tunnel (from node to beekeeper ,)
```bash
ssh -vv -N -R /home_dirs/node-0000000000000001/rtun.sock:localhost:22 node-0000000000000001@127.0.0.1 -p 22 -i id_rsa-tunnel
```

# access tunnel from within beekeeper
```bash
docker exec -it beekeeper_bk-sshd_1 /bin/bash
ssh -o 'ProxyCommand=socat UNIX:/home_dirs/node-0000000000000001/rtun.sock -' vagrant@foo
(password: vagrant)
```