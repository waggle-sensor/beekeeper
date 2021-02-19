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
import os.path
import requests
import sys
from sshkeygen import sshkeygen
import datetime
import time


formatter = logging.Formatter(
    "%(asctime)s  [%(name)s:%(lineno)d] (%(levelname)s): %(message)s"
)
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

BASE_KEY_DIR = "/usr/lib/waggle"
CA_FILE = os.path.join(BASE_KEY_DIR, "certca/sage_beekeeper_ca")
BK_SSHD_SERVER = os.getenv( "BK_SSHD_SERVER", "http://bk-sshd")
BEEKEEPER_DB_API = os.getenv("BEEKEEPER_DB_API" ,"http://bk-nodes:5000")


def get_all_nodes():

    try:
        bk_api_response = requests.get(f'{BEEKEEPER_DB_API}/state')
    except Exception as e:
        raise Exception(f"Beekeeper DB API ({BEEKEEPER_DB_API}/state) cannot be reached: {str(e)}")

        #sys.exit(1)

    if bk_api_response.status_code != 200:
        #logger.error("Could not get list of nodes")
        raise Exception("Could not get list of nodes")


    json_str = (bk_api_response.content).decode("utf-8")
    node_list = json.loads(json_str)
    node_list = node_list["data"]

    return node_list

def register_node(node_id):

    payload = {"node_id": node_id, "source": "beekeeper-register", "operation":"insert", "field_name": "registration_event", "field_value": datetime.datetime.now().replace(microsecond=0).isoformat()}

    try:
        bk_api_response = requests.post(f'{BEEKEEPER_DB_API}/log',data=json.dumps(payload))
    except Exception as e:
        raise Exception(f"Error: X Beekeeper DB API ({BEEKEEPER_DB_API}) cannot be reached: {str(e)}")

    if bk_api_response.status_code != 200 :
        con  = bk_api_response.content
        con_str = con.decode("utf-8")
        raise Exception(f"Error: Submission to beekeeper DB failed: {con_str}")

    return


# wait for beekeeper API and check for test nodes that may have to be registered
def setup_app():
    logger.debug("loop")
    while True:
        # check if BEEKEEPER_DB_API is alive
        logger.debug(f"checking connection to {BEEKEEPER_DB_API}...")
        try:
            bk_api_result = requests.get(f'{BEEKEEPER_DB_API}').content
        except Exception as e:
            logger.warning(f"Error: Beekeeper DB API ({BEEKEEPER_DB_API}) cannot be reached, requests.get returned: {str(e)}")
            time.sleep(2)
            continue

        result_message = bk_api_result.decode("utf-8").strip()
        if 'SAGE Beekeeper' != result_message:
            logger.warning(f"Error: Beekeeper DB API ({BEEKEEPER_DB_API}) cannot be reached: \"{result_message}\"")
            time.sleep(2)
            continue

        break

    test_nodes_file = os.path.join(BASE_KEY_DIR, "test-nodes.txt")
    if not os.path.isfile(test_nodes_file):
        logger.debug(f"File {test_nodes_file} not found. (only needed in testing)")
        return


    logger.debug(f"File {test_nodes_file} found. Load test nodes into DB")

    ### collect info about registered nodes to prevent multiple registrations
    try:
        node_list = list(get_all_nodes())
    except Exception as e:
        raise Exception(f'get_all_nodes returned: {str(e)}')


    registered_nodes={}
    node_list_len = len(node_list)
    logger.debug(f"Got {node_list_len} nodes from beekeeper API.")
    for node_object in node_list:
        if "id" not in node_object:
            logger.error("Field id missing")
            continue

        node_id = node_object["id"]
        registered_nodes[node_id]=True


    # check if nodes are registered already
    with open(test_nodes_file) as f:
        for line in f:
            if len(line) <= 1: # skip empty lines
                continue
            if line[0]=="#": # skip comments
                continue

            node_id = line
            logger.debug(f"got node: {node_id}")
            if node_id in registered_nodes:
                logger.debug(f"Node {node_id} already registered.")
                continue

            # register node


            register_node(node_id)

            logger.debug(f"Node {node_id} registered.")


    return


setup_app()
#logger.debug("sleep")
#time.sleep(10)
app = flask.Flask(__name__)


@app.route("/register")
def register():
    """API to create keys, certificate and user for end-point.

    Arguments:
        id (str): unique ID for this end-point

    Returns:
        dict: end-point id, private key, public key and certificate
    """
    node_id = flask.request.args.get("id", type=str)

    # check if BEEKEEPER_DB_API is alive
    try:
        bk_api_result = requests.get(f'{BEEKEEPER_DB_API}').content
    except Exception as e:
        return f"Error: Beekeeper DB API ({BEEKEEPER_DB_API}) cannot be reached, requests.get returned: {str(e)}", 500

    result_message = bk_api_result.decode("utf-8").strip()
    if 'SAGE Beekeeper' != result_message:
        return "Error: Beekeeper DB API ({BEEKEEPER_DB_API}) cannot be reached: \"{result_message}\"", 500

    logger.debug("Register user [{}]".format(node_id))
    try:
        # generate new keys sizgned by the CA for custom tunnel to beekeeper
        # create a user somewhere to allow the "node specific user" to connect
        logger.debug("- generate keys and certificates")
        client_keys = sshkeygen()
        client_keys.create_key_pair(node_id)
        client_keys.create_certificate(node_id, CA_FILE)

        data = {
            "id": client_keys.results["user"], # note that this is ID prfixed with "node_"
            "private_key": client_keys.results["private_key"],
            "public_key": client_keys.results["public_key"],
            "certificate": client_keys.results["certificate"],
        }

        # request for EP user be added
        url = os.path.join(BK_SSHD_SERVER, "adduser")
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
        return "Error: unable to register id [{}]\n".format(node_id), 500

    # update beekeeper db
    payload = {"node_id": node_id, "source": "beekeeper-register", "operation":"insert", "field_name": "registration_event", "field_value": datetime.datetime.now().replace(microsecond=0).isoformat()}

    try:
        register_node(node_id)
    except Exception as e:
        return f"Error: Registration failed: {str(e)}", 500




    return json.dumps(data)


@app.route("/")
def root():
    return "Beekeeper Registration Server"


#if __name__ == "__main__":

    # see setup_app above, that will be excuted on start

    #app.run(host="0.0.0.0", port=80)
#    app.run(debug=False, host='0.0.0.0')
