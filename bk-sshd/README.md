

Admin ssh into beekeeper sshd container
Note: Use port 2201 internally of docker networkfor admin
```bash
ssh -i ./admin.pem -o "IdentitiesOnly=yes" -p 2201 root@localhost
```


Ssh into node `0000000000000001`:
```console
ssh -i ./beekeeper-keys/nodes-key/nodes.pem -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o IdentitiesOnly=true -o ProxyCommand="ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@localhost -p 2201 -i ./beekeeper-keys/admin/admin.pem  netcat -U /home_dirs/node-0000000000000001/rtun.sock" root@random
```



From inside beekeeper sshd container, connect to node (via reverse ssh tunnel):
```bash
ssh -o 'ProxyCommand=socat UNIX:/home_dirs/node-0000000000000001/rtun.sock -' vagrant@foo
```

ssh into node:
```bash
ssh -F ./ssh.cfg node-0000000000000001
```



ansible example:
```bash
ansible-playbook -vvv --ssh-common-args ""  -i node-0000000000000001, ./playbook.yml --ask-pass
```