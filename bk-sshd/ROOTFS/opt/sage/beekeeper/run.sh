#!/bin/bash

# start EP access process
/opt/sage/beekeeper/epaccess/epaccess.py &
# TODO this does nothing now that the above command was run in background
status=$?
if [ $status -ne 0 ]; then
  echo "Failed to start epaccess: $status"
  exit $status
fi

# start sshd
/usr/sbin/sshd -D -e &
status=$?
if [ $status -ne 0 ]; then
  echo "Failed to start sshd: $status"
  exit $status
fi

# do process checking more better
while sleep 1; do
  ps aux |grep epaccess |grep -q -v grep
  PROCESS_1_STATUS=$?
  ps aux |grep sshd |grep -q -v grep
  PROCESS_2_STATUS=$?
  # If the greps above find anything, they exit with 0 status
  # If they are not both 0, then something is wrong
  if [ $PROCESS_1_STATUS -ne 0 -o $PROCESS_2_STATUS -ne 0 ]; then
    echo "One of the processes has already exited."
    exit 1
  fi
done
