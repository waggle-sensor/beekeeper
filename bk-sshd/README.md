

Copy admin key for ansible

```bash
docker cp beekeeper_bk-sshd_1:/root/keys/admin.pem .
```

Admin ssh into beekeeper sshd container
```bash
ssh -i ./admin.pem -o "IdentitiesOnly=yes" -p 20022 root@localhost
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