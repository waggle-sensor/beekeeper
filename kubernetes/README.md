

# Beekeeper kubernetes resources

For production use, please use a kustomize overlay directory, that contains your secrets and other modifications needed.


# install mysql ( if not already available )

doc: https://artifacthub.io/packages/helm/bitnami/mysql


install helm, see https://helm.sh/docs/intro/install/
```bash
#linux
wget https://get.helm.sh/helm-v3.5.2-linux-amd64.tar.gz
tar xvfz ./helm-v3.5.2-linux-amd64.tar.gz
cp linux-amd64/helm /usr/local/bin/
#osx
brew install helm
```


```bash
helm repo list
helm repo add bitnami https://charts.bitnami.com/bitnami

# in k3s: export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
# or: kubectl config set-context docker-desktop
# or: export KUBECONFIG=${HOME}/.kube/docker-desktop.config


helm list

helm install mysql --set image.tag=8.0.23-debian-10-r30 --set primary.persistence.size=1Gi bitnami/mysql

# INFO: sometimes the pv is created too late, may have to restart pod

#in production:
#   --set architecture=replication
#   --set secondary.replicaCount=3
#   --set primary.persistence.size=10Gi
#   TODO: check why primary and seconday persistence can be configured separatly

# Examples:
#To connect to your database:
#  1. Run a pod that you can use as a client:
#
#      kubectl run mysql-client --rm --tty -i --restart='Never' --image  docker.io/bitnami/mysql:8.0.23-debian-10-r30 --namespace default --command -- bash
#  2. To connect to primary service (read/write):
#      mysql -h mysql.default.svc.cluster.local -uroot -p my_database


#get password:
echo Password : $(kubectl get secret --namespace default mysql -o jsonpath="{.data.mysql-root-password}" | base64 --decode)

```


# mysql: load schema, create user/password in mysql + create secret

Specify MYSQL_PASSWORD and upload as secret:

```
# For production please update your overlay beekeeper-api.secret.yaml
kubectl apply -f overlay/beekeeper-api.secret.yaml
or
kubectl apply -f example-overlay/beekeeper-api.secret.yaml
```


load schema
```bash
MYSQL_ROOT_PASSWORD=$(kubectl get secret --namespace default mysql -o jsonpath="{.data.mysql-root-password}" | base64 --decode)
echo "MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}"

kubectl exec -i mysql-0 -- mysql -u root -p${MYSQL_ROOT_PASSWORD} < ../schema.sql
```

Create MySQL user
```bash

export MYSQL_PASSWORD=$(kubectl get secret beekeeper-api-secret -o jsonpath="{.data.MYSQL_PASSWORD}" | base64 --decode)
echo "MYSQL_PASSWORD: ${MYSQL_PASSWORD}"

kubectl exec -ti mysql-0 -- mysql -u root -p${MYSQL_ROOT_PASSWORD}

CREATE USER 'beekeeper'@'%' identified by '<MYSQL_PASSWORD>';
GRANT ALL PRIVILEGES ON Beekeeper.* TO 'beekeeper'@'%';
exit

#verify
kubectl exec -ti mysql-0 -- mysql -u root -p${MYSQL_ROOT_PASSWORD} -e "SELECT User, Host  FROM mysql.user;"
```



# prepare beekeeper secrets

> The below steps have been deprecated since the split of the CA key between a public key configMap and a private key secret. The content below remains as a potential helpful reference.

`beekeeper-api.secret.yaml` has been loaded in the previous step.


Credentials have been created in directory `beekeeper-keys`.



Load beekeeper credentials into secrets
```bash
export BEEKEEPER_KEYS_DIR=~/git/beekeeper/beekeeper-keys

# WARNING
# Your production key should be password protected. Copy the key into your trusted execution environment,
# remove the password and *then* create the secret: ssh-keygen -p -f ./beekeeper_ca_key

# for unprotected key in test env:
kubectl create secret generic beekeeper-sshd-ca-secret \
  --from-file=${BEEKEEPER_KEYS_DIR}/certca/beekeeper_ca_key \
  --from-file=${BEEKEEPER_KEYS_DIR}/certca/beekeeper_ca_key.pub
# OR (for protected key on the target host)
kubectl create secret generic beekeeper-sshd-ca-secret \
  --from-file=./beekeeper_ca_key \
  --from-file=./beekeeper_ca_key.pub

kubectl create secret generic beekeeper-sshd-server-secret \
  --from-file=${BEEKEEPER_KEYS_DIR}/bk-server/beekeeper_server_key \
  --from-file=${BEEKEEPER_KEYS_DIR}/bk-server/beekeeper_server_key-cert.pub \
  --from-file=${BEEKEEPER_KEYS_DIR}/bk-server/beekeeper_server_key.pub


kubectl create secret generic beekeeper-sshd-authorized-keys-secret \
  --from-file=${BEEKEEPER_KEYS_DIR}/admin/admin.pem \
  --from-file=${BEEKEEPER_KEYS_DIR}/admin/admin.pem.pub

# If this is password-protected, copy over to target host, unpack and create secret there.
kubectl create secret generic beekeeper-api-nodes-secret \
  --from-file=${BEEKEEPER_KEYS_DIR}/nodes-key/nodes.pem



cd ./kubernetes
# test first: kubectl kustomize example-overlay/
kubectl apply -k ./example-overlay
#  or
kubectl apply -k ./your-secret-overlay

```





# create /etc/ssh/ssh_known_hosts file
Create this file once in your private config repository.
```bash
cd registration-keys
BEEKEEPER_HOST=testhost
BEEKEEPER_PORT=49190  # not sure if that should be included
CA_PUB_FILE=${BEEKEEPER_KEYS_DIR}/certca/beekeeper_ca_key.pub
echo '@cert-authority' ${BEEKEEPER_HOST} $(cat ${CA_PUB_FILE} | cut -f 1,2 -d ' ') > ssh_known_hosts

```


# Get admin ssh key to access nodes.
In a private config repository:

```bash

# check port number: kubectl get services

ssh -i ./admin.pem -o "IdentitiesOnly=yes" -p 49190 root@localhost
```

# Development environment
The development environment provides users the following benefits:
- Test a recently pushed image of beekeeper on k8s
- Test integration with other development services
- Virtual nodes to test new code changes against

[Nautilus](https://ucsd-prp.gitlab.io/) is used for deploying the development version of Beekeeper.

Overlays:
- dev: development overlay that modifies the `base` with the following changes:
  - Ingress controller is modified to the [Nautilus' controller](https://ucsd-prp.gitlab.io/userdocs/tutorial/basic2/)
  - [test-nodes.txt](../test-keys/test-nodes.txt) file to easily pass in values to the API/DB and not be dependent on having virtual or real nodes. Mileage may vary for testing new changes.
  - Exclude volume mounts meant for production
  - Change the compute resources (CPU and memory) on each deployment
  - Generates all the secrets and confimaps for beekeeper using the kustomize generator.
- dev-vm: development overlay that modifies the `dev` overlay with the following changes:
  - Adds a [virtual node](https://github.com/waggle-sensor/node-platforms/tree/main/vm) to populate the DB and stress test the SSHD service
  - Adds certs and keys to virtual node so that the `SSHD` service is able to establish a connection

This assumes that the mysql helm chart is deployed:
```
helm install beekeeper-mysql --set image.tag=8.0.23-debian-10-r30 --set primary.persistence.size=1Gi bitnami/mysql --set startupProbe.initialDelaySeconds=480
```

Note:
- CEPH on Nautilus can be slow for some nodes so the startupProbe is delayed to take that into account.
- The name `beekeeper-mysql` used in the helm install command is used in the configmap `beekeeper-api-config` as `MYSQL_HOST` environment variable, so it needs to match.
- To initilize the DB reference the top of this [README](#mysql-load-schema-create-userpassword-in-mysql--create-secret) the MYSQL password will be stored in `dev/mysql-secrets.env` and used in the next sections.

Generate dev Beekeeper keys (if not generated):
```
docker run --rm -it \
    -v ${PWD}:/workdir:rw \
    waggle/beekeeper-key-tools:latest \
    create-init-keys.sh -p -o beekeeper-keys
docker run --rm -it \
    -v ${PWD}:/workdir:rw \
    waggle/beekeeper-key-tools:latest \
    create-key-cert.sh \
    -b my-beehive \
    -c beekeeper-keys/bk-ca/beekeeper_ca_key \
    -k beekeeper-keys/node-registration-key/registration \
    -o beekeeper-keys/registration_certs/untilforever
```

Get Nautilus kube config file from [here](https://portal.nrp-nautilus.io/)

Make sure to change to the `kubernetes` directory: `cd kubernetes`

Deploy:
```
kubectl kustomize dev --load-restrictor LoadRestrictionsNone $target | kubectl apply -f -
```

Note:
- The flag `--load-restrictor LoadRestrictionsNone $target` is to allow kustomize to search for files outside of the dev overlay directory. This is primarily used for the secrets and configmaps.

Delete:
```
kubectl kustomize dev --load-restrictor LoadRestrictionsNone $target | kubectl delete -f -
```

Check the manifest files:
```
kubectl kustomize dev --load-restrictor LoadRestrictionsNone $target >> bk-dev.yaml
```

Check the state of beekeeper:
```
curl https://bk.nrp-nautilus.io/state | jq
```

Spawn many virtual nodes for the `dev-vm` overlay:
```
kubectl scale --replicas=25 deployment beekeeper-virtual-node 
```