


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


# mysql: load schema, create user/password in myswl + create secret
```bash

echo Password : $(kubectl get secret --namespace default mysql -o jsonpath="{.data.mysql-root-password}" | base64 --decode)

kubectl exec -t mysql-0 -- mysql -u root -p<PASSWORD> < ../schema.sql

kubectl exec -ti mysql-0 -- mysql -u root -p<PASSWORD>

CREATE USER 'beekeeper'@'%' identified by 'test';
GRANT ALL PRIVILEGES ON Beekeeper.* TO 'beekeeper'@'%';

```



```bash
kubectl apply -k .
```


Copy keys into persistemt volume
```bash

POD_NAME=$(kubectl get pods -l k8s-app=beekeeper-sshd -o jsonpath="{.items[0].metadata.name}")


for folder in bk-server certca registration_keys ; do
    set -x
    kubectl cp test-keys/${folder} ${POD_NAME}:/usr/lib/waggle/
    set +x
done

kubectl delete pod ${POD_NAME}
```

Copy admin key
```bash
kubectl cp $(kubectl get pods -l k8s-app=beekeeper-sshd -o jsonpath="{.items[0].metadata.name}"):/root/keys/admin.pem ./admin.pem

```