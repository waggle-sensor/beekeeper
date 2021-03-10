

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

For production please update your overlay beekeeper-api.secret.yaml
```
kubectl apply -f overlay/beekeeper-api.secret.yaml
or
kubectl apply -f beekeeper-api.secret.yaml
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

kubectl exec -ti mysql-0 -- mysql -u root -p${MYSQL_ROOT_PASSWORD} -e "CREATE USER 'beekeeper'@'%' identified by '${MYSQL_PASSWORD}';"
kubectl exec -ti mysql-0 -- mysql -u root -p${MYSQL_ROOT_PASSWORD} -e "GRANT ALL PRIVILEGES ON Beekeeper.* TO 'beekeeper'@'%';"

#verify
kubectl exec -ti mysql-0 -- mysql -u root -p${MYSQL_ROOT_PASSWORD} -e "SELECT User, Host  FROM mysql.user;"
```


# start beekeeper
Note: When started without credential files, new ones will be created automatically, but they are not persistent.
```bash
cd ./kubernetes
# or
cd ./overlay
kubectl apply -k .
```


# After first start: persistent credentials

Skip this step if you want to use test credentials.

To keep credentials persistent, fetch credential files, save and stick them into Secrets:

```bash
cd overlay

mkdir -p certca
for file in beekeeper_ca_key beekeeper_ca_key.pub ; do
    kubectl cp $(kubectl get pods -l k8s-app=beekeeper-sshd -o jsonpath="{.items[0].metadata.name}"):/new_config/certca/${file} ./certca/${file}
done


mkdir -p bk-server
for file in beekeeper_server_key beekeeper_server_key.pub beekeeper_server_key-cert.pub ; do
    kubectl cp $(kubectl get pods -l k8s-app=beekeeper-sshd -o jsonpath="{.items[0].metadata.name}"):/new_config/bk-server/${file} ./bk-server/${file}
done

# SAVE THESE FILES IN A SECURE LOCATION !
```


Load beekeeper credentials into secrets
```bash

# For test keys: cd ../test-keys

kubectl create secret generic beekeeper-sshd-ca-secret \
  --from-file=certca/beekeeper_ca_key \
  --from-file=certca/beekeeper_ca_key.pub

kubectl create secret generic beekeeper-sshd-server-secret \
  --from-file=bk-server/beekeeper_server_key \
  --from-file=bk-server/beekeeper_server_key-cert.pub \
  --from-file=bk-server/beekeeper_server_key.pub


# restart
kubectl rollout restart deployment beekeeper-sshd

```

# Get admin ssh key to access nodes.
In a private config repository:

```bash
cd ../bk-sshd/
kubectl cp $(kubectl get pods -l k8s-app=beekeeper-sshd -o jsonpath="{.items[0].metadata.name}"):/root/keys/admin.pem ./admin.pem
chmod 600 ./admin.pem

# check port number: kubectl get services
ssh -i ./admin.pem -o "IdentitiesOnly=yes" -p 30036 root@localhost
```



# Create registration key-pair
In a private config repository:

```bash
cd registration-keys
kubectl exec -ti $(kubectl get pods -l k8s-app=beekeeper-sshd -o jsonpath="{.items[0].metadata.name}") -- create_registration_keypair.sh
# be sure to use a unique name (here registration01)
kubectl cp $(kubectl get pods -l k8s-app=beekeeper-sshd -o jsonpath="{.items[0].metadata.name}"):/tmp/new_reg_keypair/registration ./registration01
kubectl cp $(kubectl get pods -l k8s-app=beekeeper-sshd -o jsonpath="{.items[0].metadata.name}"):/tmp/new_reg_keypair/registration.pub ./registration01.pub
# keep these files in SAFE place (e.g. private git)

# load all public registration files (including existing ones) into a secret
kubectl delete secret beekeeper-sshd-public-registration-keys
kubectl create secret generic beekeeper-sshd-public-registration-keys $(for file in $(ls -1 *.pub) ; do echo -n "--from-file=${file} " ; done)
# verify
kubectl describe secret beekeeper-sshd-public-registration-keys
# restart (to mount new registration key into beekeeper-sshd)
kubectl rollout restart deployment beekeeper-sshd
```


# Create registration certitificate
Create a new certificate and save it in your private config repository.
```bash
cd registration-keys
# create certificate that is valid for 12 weeks
export PUB_KEY=registration01
export CERT_EXPIRE_DATE=20211201
kubectl exec -ti $(kubectl get pods -l k8s-app=beekeeper-sshd -o jsonpath="{.items[0].metadata.name}") -- create_registration_cert.sh ${PUB_KEY}.pub +${CERT_EXPIRE_DATE}
# choose a unique filename/folder name for the certificate
mkdir cert-${CERT_EXPIRE_DATE}
kubectl cp $(kubectl get pods -l k8s-app=beekeeper-sshd -o jsonpath="{.items[0].metadata.name}"):/tmp/new_reg/${PUB_KEY}-cert.pub ./cert-${CERT_EXPIRE_DATE}/${PUB_KEY}-cert.pub

```


# create /etc/ssh/ssh_known_hosts file
Create this file once in your private config repository.
```bash
cd registration-keys
BEEKEEPER_HOST=<beekeeper hostname or ip>
BEEKEEPER_PORT=30036
echo '['${BEEKEEPER_HOST}']:'${BEEKEEPER_PORT} $(cat bk-server/beekeeper_server_key.pub) > ssh_known_hosts

