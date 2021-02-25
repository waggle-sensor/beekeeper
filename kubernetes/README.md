


# install helm, e.g:
```bash
wget https://get.helm.sh/helm-v3.5.2-linux-amd64.tar.gz
tar xvfz ./helm-v3.5.2-linux-amd64.tar.gz
cp linux-amd64/helm /usr/local/bin/
```


# install mysql ( if not already available )

doc: https://artifacthub.io/packages/helm/bitnami/mysql

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
```bash

echo Password : $(kubectl get secret --namespace default mysql -o jsonpath="{.data.mysql-root-password}" | base64 --decode)

kubectl exec -t mysql-0 -- mysql -u root -p<PASSWORD> < ../schema.sql

kubectl exec -ti mysql-0 -- mysql -u root -p<PASSWORD>

CREATE USER 'beekeeper'@'%' identified by 'test';
GRANT ALL PRIVILEGES ON Beekeeper.* TO 'beekeeper'@'%';

```




# Load beekeeper credentials into secrets
```bash

cd ../test-keys
kubectl create secret generic beekeeper-sshd-ca-secret \
  --from-file=certca/sage_beekeeper_ca \
  --from-file=certca/sage_beekeeper_ca.pub

kubectl create secret generic beekeeper-sshd-server-secret \
  --from-file=bk-server/id_rsa_sage_beekeeper \
  --from-file=bk-server/id_rsa_sage_beekeeper-cert.pub \
  --from-file=bk-server/id_rsa_sage_beekeeper.pub

cd ../kubernetes
kubectl apply -k .
```



Get pod name to do something...
```bash

POD_NAME=$(kubectl get pods -l k8s-app=beekeeper-sshd -o jsonpath="{.items[0].metadata.name}")



kubectl delete pod ${POD_NAME}
```

Copy admin key
```bash
cd ../bk-sshd/
kubectl cp $(kubectl get pods -l k8s-app=beekeeper-sshd -o jsonpath="{.items[0].metadata.name}"):/root/keys/admin.pem ./admin.pem
chmod 600 ./admin.pem

# check port number: kubectl get services
ssh -i ./admin.pem -o "IdentitiesOnly=yes" -p 30036 root@localhost
```