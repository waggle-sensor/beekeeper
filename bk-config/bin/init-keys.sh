#!/bin/bash

set -e
set -x


create_ca.sh

create_beekeeper_cert.sh

create_registration_keypair.sh