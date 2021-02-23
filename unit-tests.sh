#!/bin/bash
set -e
set -x


bk-config/unit-tests/test_register.sh

docker exec beekeeper_bk-api_1 /bin/ash -c 'coverage run -m pytest -v  &&  coverage report -m --fail-under 90'

# Run unit-tests (bk-sshd)
# ./bk-sshd/unit-tests/unit-tests.sh
# Run unit-tests (bk-register)
# ./bk-register/unit-tests/unit-tests.sh

