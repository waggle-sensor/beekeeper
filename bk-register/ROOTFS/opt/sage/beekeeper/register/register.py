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
from sshkeygen import SSHKeyGen
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


for k, v in sorted(os.environ.items()):
    print(k+':', v)
print('\n')

BASE_KEY_DIR = "/usr/lib/waggle"
CA_FILE = os.path.join(BASE_KEY_DIR, "certca/beekeeper_ca_key")
BEEKEEPER_SSHD_API = os.getenv( "BEEKEEPER_SSHD_API", "http://bk-sshd")
BEEKEEPER_DB_API = os.getenv("BEEKEEPER_DB_API" ,"http://bk-api:5000")
KEY_GEN_TYPE = os.getenv("KEY_GEN_TYPE", "")
KEY_GEN_ARGS = os.getenv("KEY_GEN_ARGS", "")
if not KEY_GEN_TYPE:
    sys.exit("KEY_GEN_TYPE not defined")

def get_all_nodes():

    try:
        bk_api_response = requests.get(f'{BEEKEEPER_DB_API}/state', timeout=3)
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
            bk_api_result = requests.get(f'{BEEKEEPER_DB_API}', timeout=3).content
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



def check_beekeper():
    # check if BEEKEEPER_DB_API is alive
    try:
        bk_api_result = requests.get(f'{BEEKEEPER_DB_API}', timeout=3).content
    except Exception as e:
        raise Exception(f"Beekeeper DB API ({BEEKEEPER_DB_API}) cannot be reached, requests.get returned: {str(e)}")

    result_message = bk_api_result.decode("utf-8").strip()
    if 'SAGE Beekeeper' != result_message:
        raise Exception("Beekeeper DB API ({BEEKEEPER_DB_API}) cannot be reached: \"{result_message}\"")

    return

def get_node_credentials(node_id):

    url = f'{BEEKEEPER_DB_API}/credentials/{node_id}'
    try:
        bk_api_result = requests.get(url, timeout=3)
    except Exception as e:
        raise Exception(f"Beekeeper DB API ({BEEKEEPER_DB_API}) cannot be reached, requests.get returned: {str(e)}")


    if bk_api_result.status_code == 200:

        result_message = bk_api_result.content.decode("utf-8").strip()
        print(f"got result_message:{result_message}")
        return_obj = json.loads(result_message)

        if not "ssh_key_private" in return_obj:
            raise Exception(f"Key ssh_key_private missing")

        private_key = return_obj["ssh_key_private"]
        public_key = return_obj["ssh_key_public"]
        return {"private_key": private_key, "public_key": public_key}

    if bk_api_result.status_code == 404:
        return None

    result_message = ""
    if bk_api_result.content:
        result_message = bk_api_result.content.decode("utf-8").strip()

    raise Exception(f"{url} returned status_code {bk_api_result.status_code} and response: {result_message}")

def post_node_credentials(node_id, private_key, public_key):

    #ssh_key_private", "ssh_key_public


    post_creds = {"ssh_key_private": private_key, "ssh_key_public": public_key}

    url = f'{BEEKEEPER_DB_API}/credentials/{node_id}'

    try:
        bk_api_result = requests.post(url, data=json.dumps(post_creds), timeout=3)
    except Exception as e:
        raise Exception(f"Could not post to {url}, requests.get returned: {str(e)}")

    if bk_api_result.status_code == 200:
        return

    if bk_api_result.content:
        result_message = bk_api_result.content.decode("utf-8").strip()


    raise Exception(f"{url} returned status_code {bk_api_result.status_code} and response: {result_message}")




def _register(node_id):
    check_beekeper()

    # check if key-pair is available
    creds = get_node_credentials(node_id)




    client_keys = SSHKeyGen()

    if creds:
        print("got credentials from DB")
        # Files found in DB,nor write to disk so they can be used to create certififcate
        client_keys.write_keys_to_files(node_id, creds["private_key"], creds["public_key"])

    else:

        # generate new keys sizgned by the CA for custom tunnel to beekeeper
        # create a user somewhere to allow the "node specific user" to connect
        logger.debug("- generate key pair (no credentials in DB yet)")

        creds = client_keys.create_key_pair(node_id, KEY_GEN_TYPE, KEY_GEN_ARGS)

        post_node_credentials(node_id, creds["private_key"], creds["public_key"])

    for key in ["private_key", "public_key"]:
        if not key in creds:
            raise Exception(f"{key} is missing")




    logger.debug("- generate certificate")
    cert_obj = client_keys.create_certificate(node_id, CA_FILE) # returns { "certificate": certificate, "user": user}

    data = dict(creds)

    user = cert_obj["user"]

    data["id"] = user # note that this is ID prefixed with "node_"
    data["certificate"] = cert_obj["certificate"]



    #data = {
    #    "id": client_keys.results["user"], # note that this is ID prfixed with "node_"
    #    "private_key": client_keys.results["private_key"],
    #    "public_key": client_keys.results["public_key"],
    #    "certificate": client_keys.results["certificate"],
    #}

    # request for EP user be added
    logger.debug("- request for EP user be added")
    url = os.path.join(BEEKEEPER_SSHD_API, "adduser")
    post_results = requests.post(url, data=data)
    if not post_results.ok:
        raise Exception(f"Unable to add user [{user}]")

    logger.debug(f"- successfully created user [{user}]")

    #payload = {"node_id": node_id, "source": "beekeeper-register", "operation":"insert", "field_name": "registration_event", "field_value": datetime.datetime.now().replace(microsecond=0).isoformat()}
    return data

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
    logger.debug("Register user [{}]".format(node_id))

    try:
       registration_result =  _register(node_id)
    except Exception as e:
        logger.error(f"_register failed: {str(e)}")
        return f"Error: unable to register id [{node_id} , {str(e)}]\n", 500

    # update beekeeper db


    try:
        register_node(node_id)
    except Exception as e:
        return f"Error: Registration failed: {str(e)}", 500




    return json.dumps(registration_result)


@app.route("/")
def root():
    return "Beekeeper Registration Server"


#if __name__ == "__main__":

    # see setup_app above, that will be excuted on start

    #app.run(host="0.0.0.0", port=80)
#    app.run(debug=False, host='0.0.0.0')
