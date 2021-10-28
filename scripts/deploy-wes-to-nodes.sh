#!/bin/bash -e

# TODO(sean) Find correct location for this script to live.

# change workdir to script location and load libs
cd $(dirname $0)
source lib/data.sh

fatal() {
    echo $*
    exit 1
}

# check kubectl
if [[ $(kubectl get nodes -o name)_ != "node/beehive-beekeeper_" ]] ; then
    echo "kubectl could not connect"
    exit
fi

# check beekeeper API
beekeeper_api="localhost"
if [[  $(hostname)_ == "beehive-beekeeper_" ]] ; then
    beekeeper_api=$(kubectl get services beekeeper-api -o jsonpath={.spec.clusterIP})
    if [[ ${beekeeper_api}_ == "_" ]] ; then
        echo "beekeeper API not found"
        exit 1
    fi
fi

if [[ $(curl -s "${beekeeper_api}:5000/")_ != "SAGE Beekeeper API_" ]] ; then

    echo "Could not reach Beekeeper API"
    echo "if on your laptop, use port-forwarding:"
    echo "> kubectl port-forward service/beekeeper-api 5000:5000"
    exit 1
fi

COUNT=0
for nodeID in $*; do
    # ensure nodeID is lowercase
    nodeID_lower=$(echo "$nodeID" | awk '{print tolower($0)}')
    nodeID_upper=$(echo "$nodeID" | awk '{print toupper($0)}')

    BASE_DIR=`pwd`

    echo "starting deployment to $nodeID"

    echo "adding users for beehive for node $nodeID"
    if [ -d /root/git/waggle-beehive-v2 ] ; then
        # in case we are on rhoney
        cd /root/git/waggle-beehive-v2
    elif [ -d ~/git/waggle-beehive-v2 ] ; then
        # in case we are on a laptop
        cd ~/git/waggle-beehive-v2
    else
        echo "waggle-beehive-v2 directory not found"
        exit 1
    fi

    # (this uses kubectl right now)
    while ! ./register-node.sh "${nodeID_lower}"; do
        echo "failed to register node... will retry."
        sleep 3
    done


    cd ${BASE_DIR}
    set -x
    curl "${beekeeper_api}:5000/node/${nodeID_upper}" -d '{"assign_beehive": "sage-beehive"}'
    set +x

    echo "waiting for data from node"
    wait_for_recent_data_for_node "$nodeID_lower"

    echo "success! wes has been deployed to node $nodeID_lower!"

    COUNT=$((COUNT+1))
done


echo ${COUNT} nodes updated.
