# Beekeeper Server

The beekeeper server is the administration server for the SAGE cyberinfrastructure.
All end-points (i.e. nodes, beehives, etc.) must register with the beekeeper
in order to be added to the SAGE ecosystem.

The beekeeper is responsible for the following:
1. front end for provisioning and administrative management of all end-points
2. certificate authority responsible for generating and validating all
communication keys used by the end-points
3. administrative portal for collecting the general health of all end-points


## start beekeeper

### 1) Initialize: Create CA and server keys

To create new CA and server keys:
```bash
./init-keys.sh new
```

For testing purposes you can also use existing keys from sub-directory `./test-keys`:

```bash
./init-keys.sh test  # WARNING: Only use for testing/development
```

### 2) Start beekeeper

```bash
docker-compose up --build
```



## Beekeeper Config Dependency

The beekeeper server is dependent on the (beekeeper-config)[https://github.com/waggle-sensor/beekeeper-config] (private repo) to generate and share necessary
key-pairs and certificates via the `beekeeper-config_bk-secrets` docker
volume.

## Beekeeper Registration & Certificate Authority

Once an end-point registers with the beekeeper it will issued an original
key-pair and certificate for the end-point to establish a reverse SSH tunnel
with the beekeeper.  This SSH tunnel will then be used to facilitate
administration and health check reporting.

This is done by issuing the `register` command over `ssh` as the
`sage_registration` user to the beekeeper's SSH port (20022) using the
`id_rsa_sage_registration` private key and certificate.  See
(beekeeper-config)[https://github.com/waggle-sensor/beekeeper-config]
for more details.

An example of a registration `ssh` command would be as follows:

```
ssh sage_registration@<beekeeper url> -p 20022 -i ~/path/to/id_rsa_sage_registration register <ep ID>

# specific example for end-point `123456`
ssh -vv sage_registration@127.0.0.1 -p 20022 -i ~/workspace/waggle-sensor/beekeeper-config/bk-config/ROOTFS/secrets/registration_keys/id_rsa_sage_registration register 123456
```

See section [bk-sshd](#bksshd) for details on using the `register` command.

_Note_: The beekeeper only accepts valid registration certificates.  See
(beekeeper-config)[https://github.com/waggle-sensor/beekeeper-config] for
details in generating a registration certificate.

### Establishing Reverse SSH Tunnel to Beekeeper

Once the registration process is successful a reverse SSH tunnel can be
established between the end-point and beekeeper.

An example of the `ssh` command to establish the tunnel is:

```
ssh -N  -R /home_dir/<end-point id>/rtun.sock:localhost:22 <node id>@<beekeeper url> -p 20022 -i /path/to/id_rsa_beekeeper_tunnel

# specific example for end-point `123456`
ssh -N  -R /home_dirs/node-123456/rtun.sock:localhost:22 node-123456@127.0.0.1 -p 20022 -i id_rsa_beekeeper_tunnel
```

The beekeeper creates a private socket for the end-point to facilitate the
reverse SSH tunnel @ `/home_dirs/<end-point id>/rtun.sock` where `<end-point id>`
is the end-point's ID that was returned with a successful registration.
The `id_rsa_beekeeper_tunnel` is also the private key that was created by
beekeeper during the registration process.

_Note_: the payload returned from the `register` command will be needed to
establish the tunnel.  See section [bk-sshd](#bk-sshd) for details.

### Administrating End-Point via Reverse SSH Tunnel

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

## Unit Testing

Unit-testing is executed via
- `./bk-sshd/unit-tests/unit-tests.sh`
- `./bk-register/unit-tests/unit-tests.sh`
