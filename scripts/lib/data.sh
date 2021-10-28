get_recent_data_for_node() {
    nodeID="$1"
    curl -s -k -H 'Content-Type: application/json' https://data.sagecontinuum.org/api/v1/query -d "{\"start\": \"-3m\", \"filter\": {\"node\": \"$nodeID\"}}"
}

wait_for_recent_data_for_node() {
    nodeID="$1"
    while ! get_recent_data_for_node "$nodeID" | awk 'END { if (NR > 0) { exit 0 } else { exit 1 } }'; do
        echo "waiting for data..."
        sleep 15
    done
}
