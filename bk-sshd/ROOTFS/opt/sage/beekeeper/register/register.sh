#!/bin/bash
# ANL:waggle-license
#  This file is part of the Waggle Platform.  Please see the file
#  LICENSE.waggle.txt for the legal details of the copyright and software
#  license.  For more details on the Waggle project, visit:
#           http://www.wa8.gl
# ANL:waggle-license

# NOTE(sean) This script forwards JSON output directly to a consumer, so do not write anything else to stdout!

set -eu

bk_register_url=http://bk-api:5000
if [ -e /config/BEEKEEPER_REGISTER_API ]; then
  # env variables cannot be passed to this script, thus we read config from file
  bk_register_url=$(cat /config/BEEKEEPER_REGISTER_API)
fi

# process args baked into authorized command
beehive=""

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
    params="node_id=${node}"

    if [ ! -z "${beehive}" ]; then
      params="${params}&beehive_id=${beehive}"
    fi

    curl -s --fail -X POST "${bk_register_url}/register?${params}"
    ;;
  *)
    echo "invalid command"
    exit 1
    ;;
esac
