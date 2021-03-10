
## Beekeeper Registration & Certificate Authority

Once an end-point registers with the beekeeper it will issued an original key-pair and certificate for the end-point to establish a reverse SSH tunnel with the beekeeper.  This SSH tunnel will then be used to facilitate administration and health check reporting.

This is done by issuing the `register` command over `ssh` as the `sage_registration` user to the beekeeper's SSH port (20022) using the private registration key and certificate.

An example of a registration `ssh` command would be as follows:

```
ssh sage_registration@<beekeeper url> -p 20022 -i ~/path/to/registration register <node ID>
```
The registration service that does exactly this can be found here:

[https://github.com/waggle-sensor/node-registration-service](https://github.com/waggle-sensor/node-registration-service)


See section [bk-sshd](#bksshd) for details on using the `register` command.


### Establishing Reverse SSH Tunnel to Beekeeper

Once the registration process is successful a reverse SSH tunnel can be
established between the node and beekeeper.

An example of the `ssh` command to establish the tunnel is:

```
ssh -N  -R /home_dir/<end-point id>/rtun.sock:localhost:22 <node id>@<beekeeper url> -p 20022 -i /path/to/id_rsa_beekeeper_tunnel

```

The code for the reverse ssh tunnel service can be found here:

[https://github.com/waggle-sensor/node-reverse-tunnel-service](https://github.com/waggle-sensor/node-reverse-tunnel-service)


The beekeeper creates a private socket for the end-point to facilitate the
reverse SSH tunnel @ `/home_dirs/<end-point id>/rtun.sock` where `<end-point id>`
is the end-point's ID that was returned with a successful registration.
The `id_rsa_beekeeper_tunnel` is also the private key that was created by
beekeeper during the registration process.

_Note_: the payload returned from the `register` command will be needed to
establish the tunnel.  See section [bk-sshd](#bk-sshd) for details.

### Administrating nodes via Reverse SSH Tunnel

Once the reverse SSH tunnel is established by the end-point, administration
can be performed over the end-point's private socket (i.e. `/home_dirs/<end-point id>/rtun.sock`).  The following command is an example of how to ssh into a shell
on the end-point via the socket.

```
ssh -o 'ProxyCommand=socat UNIX:/home_dirs/<end-point id>/rtun.sock -' <user>@foo

# specific example for end-point 123456 (note: my test environment did not have a node-123456 user)
ssh -o 'ProxyCommand=socat UNIX:/home_dirs/node-123456/rtun.sock -' jswantek@foo
```

In this case the `<user>` is a valid user on the end-point.  It is **recommended**
that all end-points create a user (with `sudo` access) matching the
`<end-point id>` to ease administration.  The `foo` value is invalid and only
exists as a "hostname" is required by the `ssh` command.

_Note_: The above `ssh` command back to the end-point would require a password
for the `<user>`.  It is expected this can be updated to use a key.

## Beekeeper Services

There are 2 core services that run within beekeeper
1. bk-sshd
2. bk-register

### <a name="bksshd"></a>bk-sshd

The `bk-sshd` service is a docker container running the `sshd` deamon that
enables the beekeeper to receive `ssh` connections from end-points.

During registration (which is only with the registration certificate) only the
`register` command is supported.  All other commands sent will result in an
error.

The `register` command requires 1 argument for the end-point ID (`<ep ID>`).
The `<ep ID>` value is used to create unique keys for this end-point and therefore
it is **highly recommended** that the end-point's mac address be used for this
value to ensure uniqueness.

```
ssh sage_registration@<beekeeper url> -p 20022 -i ~/path/to/id_rsa_sage_registration register <ep ID>
```

During the registration process the following activities occur:
1. The [bk-register](#bkregister) service is triggered to create a ssh key-pair
and certificate for this end-point.
2. The [bk-register](#bkregister) triggers this `bk-sshd` service to create
a user (and home directory within the `bk-homedirs` docker volume) for the
end-point and save the ssh key-pair and certificate within the new
end-point user folder.

_Note_: The `bk-sshd` makes use of a `bk-homedirs` docker volume to store the
end-point user folders.  These user folders contain the end-points keys,
certificate, and socket file.  The ownership of these files belong to the
end-point user, thus blocking an end-point from accidentally connecting to
the wrong socket.

### <a name="bkregister"></a>bk-register

The `bk-register` service sits behind the [bk-sshd](#bksshd) service waiting
for end-point registration requests.  Upon receiving a registration request
the following actions are taken:

1. An ssh key-pair and certificate are created for this end-point using the
certificate authority provided by the (beekeeper-config)[https://github.com/waggle-sensor/beekeeper-config]
2. The [bk-sshd](#bksshd) is requested to create a user for the end-point and
to save the keys and certificate within the new user's home folder.
