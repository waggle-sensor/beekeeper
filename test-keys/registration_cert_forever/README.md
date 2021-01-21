
This certified registration key can be used by a node to register with beekeeper and get keys (e.g. key-pair, RMQ certificate). The waggle-edge-stack should already come with test keys, thus this registration key should not be needed.

The `known_hosts` file has a prefix `[10.0.2.2]:20022` in front of the beekeeper CA public key, which is used when beekeeper runs on the same host as the vagrant deployment of the waggle edge stack. `10.0.2.2` is the static IP VirtualBox VMs use to address the host. If beekeeper or waggle edge stack run somewhere else, and registration is required, the IP address has to be replaced by an IP address with which the node can reach beekeeper.

