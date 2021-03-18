#!/bin/bash -e
# ANL:waggle-license
#  This file is part of the Waggle Platform.  Please see the file
#  LICENSE.waggle.txt for the legal details of the copyright and software
#  license.  For more details on the Waggle project, visit:
#           http://www.wa8.gl
# ANL:waggle-license


bk_register_url=http://bk-api:5000
if [ -e /config/BEEKEEPER_REGISTER_API ]; then
  # env variables cannot be passed to this script, thus we read config from file
  bk_register_url=$(cat /config/BEEKEEPER_REGISTER_API)
fi

#echo "bk_register_url: ${bk_register_url}"

run_command() {
  input=($1)

  case ${input[0]} in
    register)

      curl -s -X GET "${bk_register_url}/register?id=${input[1]}"

      ;;
    *)
      echo "invalid command"
      exit 1
      ;;
  esac
}

run_command "$SSH_ORIGINAL_COMMAND"
