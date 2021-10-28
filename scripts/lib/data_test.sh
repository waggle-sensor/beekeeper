#!/bin/bash

source data.sh

fatal() {
    echo $*
    exit 1
}

NODE_ID=${1:-00004cd98fc686c9}

if ! get_recent_data_for_node "$NODE_ID" | grep -q -m 1 timestamp; then
    fatal "FAIL!! get_recent_data_for_node"
fi

if ! wait_for_recent_data_for_node "$NODE_ID"; then
    fatal "FAIL!! wait_for_recent_data_for_node"
fi
