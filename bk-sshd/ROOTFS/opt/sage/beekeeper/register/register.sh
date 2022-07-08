#!/bin/bash
# ANL:waggle-license
#  This file is part of the Waggle Platform.  Please see the file
#  LICENSE.waggle.txt for the legal details of the copyright and software
#  license.  For more details on the Waggle project, visit:
#           http://www.wa8.gl
# ANL:waggle-license

set -eu

bk_register_url=http://bk-api:5000
if [ -e /config/BEEKEEPER_REGISTER_API ]; then
  # env variables cannot be passed to this script, thus we read config from file
  bk_register_url=$(cat /config/BEEKEEPER_REGISTER_API)
fi

# process args baked into authorized command
# TODO(sean) make part of configmap
beehive="beehive-sage"

while getopts "b:" opt; do
  case "${opt}" in
    b) beehive="${OPTARG}" ;;
  esac
done

# process args provided via ssh
user_args=(${SSH_ORIGINAL_COMMAND})
command="${user_args[0]}"

case "${command}" in
  register)
    node="${user_args[1]}"
    echo "registering ${node} with ${beehive}"
    curl -s -X GET "${bk_register_url}/register?id=${node}&beehive=${beehive}"
    ;;
  *)
    echo "invalid command: ${command}"
    exit 1
    ;;
esac
