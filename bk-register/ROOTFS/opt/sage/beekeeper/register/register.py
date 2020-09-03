#!/usr/bin/env python3
"""
Provides API interface to register an end-point to the beekeeper.

ANL:waggle-license
 This file is part of the Waggle Platform.  Please see the file
 LICENSE.waggle.txt for the legal details of the copyright and software
 license.  For more details on the Waggle project, visit:
          http://www.wa8.gl
ANL:waggle-license
"""

import flask
import json
import logging
import os
import requests
import sys
from sshkeygen import sshkeygen

app = flask.Flask(__name__)

formatter = logging.Formatter(
    "%(asctime)s  [%(name)s:%(lineno)d] (%(levelname)s): %(message)s"
)
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

BASE_KEY_DIR = "/usr/lib/sage"
CA_FILE = os.path.join(BASE_KEY_DIR, "certca/sage_beekeeper_ca")
USER_SERVER = "http://bk-sshd"


@app.route("/register")
def register():
    """API to create keys, certificate and user for end-point.

    Arguments:
        id (str): unique ID for this end-point

    Returns:
        dict: end-point id, private key, public key and certificate
    """
    id = flask.request.args.get("id", type=str)

    logger.debug("Register user [{}]".format(id))
    try:
        # generate new keys sizgned by the CA for custom tunnel to beekeeper
        # create a user somewhere to allow the "node specific user" to connect
        logger.debug("- generate keys and certificates")
        client_keys = sshkeygen()
        client_keys.create_key_pair(id)
        client_keys.create_certificate(id, CA_FILE)

        data = {
            "id": client_keys.results["user"],
            "private_key": client_keys.results["private_key"],
            "public_key": client_keys.results["public_key"],
            "certificate": client_keys.results["certificate"],
        }

        # request for EP user be added
        url = os.path.join(USER_SERVER, "adduser")
        post_results = requests.post(url, data=data)
        if not post_results.ok:
            raise Exception(
                "Unable to add user [{}]".format(client_keys.results["user"])
            )

        logger.debug(
            "- successfully created user [{}]".format(client_keys.results["user"])
        )
    except Exception as e:
        logger.error(e)
        return "Error: unable to register id [{}]\n".format(id), 500

    return json.dumps(data)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
