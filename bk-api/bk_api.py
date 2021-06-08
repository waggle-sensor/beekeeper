#!/usr/bin/env python3

# ### mysqlclient ###
# pip install mysqlclient
# https://github.com/PyMySQL/mysqlclient-python
# https://mysqlclient.readthedocs.io/


import os
import sys


from flask import Flask
from flask_cors import CORS
from flask.views import MethodView
from flask import jsonify
from flask.wrappers import Response

from error_response import ErrorResponse

from flask import request
from flask import abort, jsonify

from http import HTTPStatus

import config
import datetime
import time
import json
import base64
import yaml

import bk_db
from  bk_db import BeekeeperDB, table_fields , table_fields_index

#import flask

import logging

import os.path
import requests

from sshkeygen import SSHKeyGen, run_command, run_command_communicate
import traceback
from werkzeug.utils import secure_filename


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
#CA_FILE = os.path.join(BASE_KEY_DIR, "certca/beekeeper_ca_key")
CA_FILE="/usr/lib/waggle/certca/beekeeper_ca_key"


BEEKEEPER_SSHD_API = os.getenv( "BEEKEEPER_SSHD_API", "http://bk-sshd")
#BEEKEEPER_DB_API = os.getenv("BEEKEEPER_DB_API" ,"http://bk-api:5000")
BEEKEEPER_DB_API = "http://localhost:5000"
KEY_GEN_TYPE = os.getenv("KEY_GEN_TYPE", "")
KEY_GEN_ARGS = os.getenv("KEY_GEN_ARGS", "")
if not KEY_GEN_TYPE:
    sys.exit("KEY_GEN_TYPE not defined")

beehives_root = '/beehives'
node_key = "/config/nodes/node_key.pem"

# def get_all_nodes():

#     try:
#         bk_api_response = requests.get(f'{BEEKEEPER_DB_API}/state', timeout=3)
#     except Exception as e:
#         raise Exception(f"Beekeeper DB API ({BEEKEEPER_DB_API}/state) cannot be reached: {str(e)}")

#         #sys.exit(1)

#     if bk_api_response.status_code != 200:
#         #logger.error("Could not get list of nodes")
#         raise Exception("Could not get list of nodes")


#     json_str = (bk_api_response.content).decode("utf-8")
#     node_list = json.loads(json_str)
#     node_list = node_list["data"]

#     return node_list


def b64string_encode(input):
    return base64.b64encode(str.encode(input)).decode('utf-8')


def register_node(node_id, lock_tables=True):

    payload = {"node_id": node_id, "source": "beekeeper-register", "operation":"insert", "field_name": "registration_event", "field_value": datetime.datetime.now().replace(microsecond=0).isoformat()}

    #url = f'{BEEKEEPER_DB_API}/log'
    try:
        insert_log(payload, lock_tables=lock_tables)
        #bk_api_response = requests.post(url,data=json.dumps(payload), timeout=3)
    except Exception as e:
        #raise Exception(f"Error: X Beekeeper DB API ({url}) cannot be reached: {str(e)}")
        raise Exception(f"insert_log returned: {str(e)}")


    return


# register test nodes (use only in development environment)
def initialize_test_nodes():  # pragma: no cover   this code is not used in production


    test_nodes_file = os.path.join(BASE_KEY_DIR, "test-nodes.txt")
    if not os.path.isfile(test_nodes_file):
        logger.debug(f"File {test_nodes_file} not found. (only needed in testing)")
        return


    logger.debug(f"File {test_nodes_file} found. Load test nodes into DB")

    ### collect info about registered nodes to prevent multiple registrations
    try:
        bee_db = BeekeeperDB()
        node_list = bee_db.list_latest_state()
    except Exception as e:
        raise Exception(f'list_latest_state returned: {str(e)}')


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

            try:
                register_node(node_id, lock_tables=False)  # Locking mysql tables at initialization does not work for some unclear reason
            except Exception as e:
                raise Exception(f"Node registration failed: {str(e)}")

            logger.debug(f"Node {node_id} registered.")


    return



# def check_beekeper():
#     # check if BEEKEEPER_DB_API is alive
#     try:
#         bk_api_result = requests.get(f'{BEEKEEPER_DB_API}', timeout=3).content
#     except Exception as e:
#         raise Exception(f"Beekeeper DB API ({BEEKEEPER_DB_API}) cannot be reached, requests.get returned: {str(e)}")

#     result_message = bk_api_result.decode("utf-8").strip()
#     if 'SAGE Beekeeper' != result_message:
#         raise Exception("Beekeeper DB API ({BEEKEEPER_DB_API}) cannot be reached: \"{result_message}\"")

#     return

def get_node_keypair(node_id):

    #url = f'{BEEKEEPER_DB_API}/credentials/{node_id}'
    #try:
    #    bk_api_result = requests.get(url, timeout=3)
    #except Exception as e:
    #    raise Exception(f"Beekeeper DB API ({BEEKEEPER_DB_API}) cannot be reached, requests.get returned: {str(e)}")


    try:
        bee_db = BeekeeperDB()
        return_obj = bee_db.get_node_keypair(node_id)
    except Exception as e:
        raise Exception(f"bee_db.get_node_keypair returned: {str(e)}")

    if not return_obj:
        return None

    if not "ssh_key_private" in return_obj:
        raise Exception(f"Key ssh_key_private missing")

    if not "ssh_key_public" in return_obj:
        raise Exception(f"Key ssh_key_public missing")

    private_key = return_obj["ssh_key_private"]
    public_key = return_obj["ssh_key_public"]

    creds = {"private_key": private_key, "public_key": public_key}
    return creds



def post_node_credentials(node_id, private_key, public_key):

    #ssh_key_private", "ssh_key_public
    bee_db = BeekeeperDB()
    post_creds = {"ssh_key_private": private_key, "ssh_key_public": public_key}

    try:
        bee_db.set_node_keypair(node_id, post_creds)
    except Exception as e:
        raise Exception(f"set_node_keypair returned: {str(e)}")

    return
    #url = f'{BEEKEEPER_DB_API}/credentials/{node_id}'

    #try:
    #    bk_api_result = requests.post(url, data=json.dumps(post_creds), timeout=3)
    #except Exception as e:
    #    raise Exception(f"Could not post to {url}, requests.get returned: {str(e)}")

    #if bk_api_result.status_code == 200:
    #    return

    #if bk_api_result.content:
    #    result_message = bk_api_result.content.decode("utf-8").strip()


    #raise Exception(f"{url} returned status_code {bk_api_result.status_code} and response: {result_message}")




def _register(node_id):
    #check_beekeper()

    if not node_id:
        raise Exception("node_id no defined")

    # check if key-pair is available
    try:
        creds = get_node_keypair(node_id)
    except Exception as e:
        raise Exception(f"get_node_keypair returned: {str(e)}")



    key_generator = SSHKeyGen()

    if creds:
        print("got credentials from DB")
        # Files found in DB,nor write to disk so they can be used to create certififcate
        try:
            key_generator.write_keys_to_files(node_id, creds["private_key"], creds["public_key"])
        except Exception as e:
            raise Exception(f"key_generator.write_keys_to_files returned: {type(e)}: {str(e)}")

    else:

        # generate new keys sizgned by the CA for custom tunnel to beekeeper
        # create a user somewhere to allow the "node specific user" to connect
        logger.debug("- generate key pair (no credentials in DB yet)")
        try:
            creds = key_generator.create_key_pair(node_id, KEY_GEN_TYPE, KEY_GEN_ARGS)
        except Exception as e:
            raise Exception(f"key_generator.create_key_pair returned: {str(e)}")

        try:
            post_node_credentials(node_id, creds["private_key"], creds["public_key"])
        except Exception as e:
            raise Exception(f"post_node_credentials returned: {str(e)}")

    for key in ["private_key", "public_key"]:
        if not key in creds:
            raise Exception(f"{key} is missing")




    logger.debug("- generate certificate")
    try:
        cert_obj = key_generator.create_reverse_tunnel_certificate(node_id, CA_FILE) # returns { "certificate": certificate, "user": user}
    except Exception as e:
            raise Exception(f"key_generator.create_reverse_tunnel_certificate returned: {str(e)}")
    data = dict(creds)

    user = cert_obj["user"]

    data["id"] = user # note that this is ID prefixed with "node_"
    data["certificate"] = cert_obj["certificate"]



    #data = {
    #    "id": key_generator.results["user"], # note that this is ID prfixed with "node_"
    #    "private_key": key_generator.results["private_key"],
    #    "public_key": key_generator.results["public_key"],
    #    "certificate": key_generator.results["certificate"],
    #}

    # request for EP user be added
    logger.debug("- request for EP user be added")
    url = os.path.join(BEEKEEPER_SSHD_API, "adduser")
    post_results = requests.post(url, data=data, timeout=3)
    if not post_results.ok:
        raise Exception(f"Unable to add user [{user}]")

    logger.debug(f"- successfully created user [{user}]")

    #payload = {"node_id": node_id, "source": "beekeeper-register", "operation":"insert", "field_name": "registration_event", "field_value": datetime.datetime.now().replace(microsecond=0).isoformat()}
    return data


def create_beehive_files(beehive_obj):


    #if not os.path.exists(beehives_root):
    #    os.makedirs(beehives_root)

    beehive_id =  beehive_obj["id"]
    beehive_dir = os.path.join(beehives_root, beehive_id )
    beehive_dir_ssh = os.path.join(beehive_dir , "ssh")
    beehive_dir_tls = os.path.join(beehive_dir , "tls")
    if not os.path.exists(beehive_dir_ssh):
        os.makedirs(beehive_dir_ssh)
    if not os.path.exists(beehive_dir_tls):
        os.makedirs(beehive_dir_tls)

 # url -F "tls-key=@tls/ca/cakey.pem" -F "tls-cert=@tls/ca/cacert.pem"  -F "ssh-key=@ssh/ca/ca" -F "ssh-pub=@ssh/ca/ca.pub" -F "ssh-cert=@ssh/ca/ca-cert.pub"  localhost:5000/beehives/sage-beehive
    files = {   "tls/cakey.pem": "tls-key",
                "tls/cacert.pem": "tls-cert",
                "ssh/ca" : "ssh-key",
                "ssh/ca.pub" : "ssh-pub",
                "ssh/ca-cert.pub" :  "ssh-cert"}

    for file in files:
        full_filename = os.path.join(beehive_dir, file )

        if os.path.exists(full_filename):
            continue

        key = files[file]
        data = beehive_obj.get(key, "")
        if not data:
            obj_str = ",".join(beehive_obj.keys())
            raise Exception(f"Data for beehive not found ({key}) (got: {obj_str})")
        with open(full_filename, 'a') as cert_file:
            cert_file.write(data)

        os.chmod(full_filename, 0o600)


    return

# /
class Root(MethodView):
    def get(self):
        return "SAGE Beekeeper API"


def insert_log(postData, lock_tables=True, force=False):
    listData = None
    if isinstance( postData, dict ):
        listData = [ postData ]
        #print("Putting postData into array ", flush=True)
    else:
        listData = postData
        #print("Use postData as is ", flush=True)

    if not isinstance( listData, list ):
        raise Exception("list expected")


    bee_db = None
    try:
        bee_db = BeekeeperDB()
    except Exception as e:
        raise Exception(f"Could not create BeekeeperDB: {e}" )


    logData = []
    default_effective_time = datetime.datetime.now(datetime.timezone.utc) # this way all operations in this submission have the exact same time
    for op in listData:

        for f in ["node_id", "operation", "field_name", "field_value", "source"]:
            if f not in op:
                raise Exception(f'Field {f} missing. Got: {json.dumps(op)}')

        if not force:
            if op["field_name"] == "beehive":
                raise Exception("Field \"beehive\" cannot be set via the /log resource")


        try:
            newLogDataEntry = {
                "node_id": op["node_id"],
                "table_name": "nodes_history" ,
                "operation": op["operation"],
                "field_name": op["field_name"],
                "new_value": op["field_value"],
                "source": op["source"],
                "effective_time" : op.get("effective_time", default_effective_time.isoformat()) }

        except Exception as ex:
            raise Exception(f"Unexpected error in creating newLogDataEntry : {ex}")

        logData.append(newLogDataEntry)
        #print("success", flush=True)

    try:
        bee_db.nodes_log_add(logData, lock_tables=lock_tables) #  effective_time=effective_time)
    except Exception as ex:
        raise Exception(f"nodes_log_add failed: {ex}" )

    return



# /log
class Log(MethodView):

    # example: curl -X POST -d '[{"node_id": "123", "operation":"insert", "field_name": "name", "field_value": "Rumpelstilzchen"}]' localhost:5000/log

    def post(self):

        try:
#request.get
            postData = request.get_json(force=True, silent=False)

        except Exception as e:
            raise ErrorResponse(f"Error parsing json: { sys.exc_info()[0] }  {e}" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

        if not postData:
            raise ErrorResponse(f"Could not parse json." , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

        try:
            insert_log(postData)
        except Exception as e:
            raise ErrorResponse(f"Could not insert log: {str(e)}" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

        response = {"success" : 1}
        return response


    def get(self):
        return "try POST..."



# /state
class ListStates(MethodView):
    def get(self):
        try:
            bee_db = BeekeeperDB()
            node_state = bee_db.list_latest_state()

        except Exception as e:
            raise ErrorResponse(f"Unexpected error: {e}" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

        return { "data" : node_state }




# /state/<node_id>
class State(MethodView):
    def get(self, node_id):
        try:

            bee_db = BeekeeperDB()
            node_state = bee_db.get_node_state(node_id)

        except Exception as e:
            raise ErrorResponse(f"Unexpected error: {e}" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

        if "timestamp" in node_state:
            node_state["timestamp"] = node_state["timestamp"].isoformat()

        if "registration_event" in node_state:
            node_state["registration_event"] = node_state["registration_event"].isoformat()

        return { "data" : node_state }


#def scp(source, node_id, target):
#    command_array = ["scp",
#            "-i", node_key ,
#            "-o" , "UserKnownHostsFile=/dev/null",
#            "-o", "StrictHostKeyChecking=no",
#            "-o", "IdentitiesOnly=true",
#            "-o" ,f"ProxyCommand=ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@bk-sshd -p 2201 -i /config/admin-key/admin.pem  netcat -U /home_dirs/node-{node_id}/rtun.sock",
#            source,
#            f"root@foo:{target}"]
#
#    result_stdout = run_command(command_array, return_stdout=True)
#    return result_stdout



def node_ssh(node_id, command, input_str=None):
    ssh_cmd =  ["ssh",
            #"-tt",
            "-i", node_key , # this must be the key that allows ssh into the node , this key might be the same for all nodes
            "-o" , "UserKnownHostsFile=/dev/null",
            "-o", "StrictHostKeyChecking=no",
            "-o", "IdentitiesOnly=true",
            "-o" ,f"ProxyCommand=ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@bk-sshd -p 2201 -i /config/admin-key/admin.pem  netcat -U /home_dirs/node-{node_id}/rtun.sock",
            f"root@foo:",
            command]


    ssh_cmd_str = " ".join(ssh_cmd)
    logger.debug(ssh_cmd_str)


    result_stdout ,result_stderr = run_command_communicate(ssh_cmd, input_str = input_str)

    result_stdout_str = ""
    result_stderr_str = ""

    if result_stdout:
        result_stdout_str = result_stdout.decode('utf-8')

    if result_stderr:
        result_stderr_str = result_stderr.decode('utf-8')

    return (result_stdout_str ,result_stderr_str)



# kube_resource: a dict
def kubectl_apply(node_id, kube_resource):

    try:
        result_stdout_str ,result_stderr_str = node_ssh(node_id, "kubectl apply -f -", input_str= yaml.dump(kube_resource))
    except Exception as e:
        raise Exception(f"node_ssh failed: {str(e)}")

    if (not "unchanged" in result_stdout_str) and (not "created" in result_stdout_str)and (not "configured" in result_stdout_str):
         raise Exception(f"result_stdout_str:{result_stdout_str} result_stderr_str:{result_stderr_str}")

    return result_stdout_str ,result_stderr_str



def node_assign_beehive(node_id, assign_beehive, this_debug):

    logger.debug("start assign_beehive")

    try:
        bee_db = BeekeeperDB()
        beehive_obj = bee_db.get_beehive(assign_beehive)
    except Exception as e:
        raise Exception(f"get_beehive returned: {str(e)}")


    if not beehive_obj:
        raise Exception(f"Beehive {assign_beehive} unknown" )

    if not isinstance(beehive_obj, dict):
        raise Exception(f"beehive_obj is not a dict")


    beehive_id = beehive_obj.get("id", "")
    if not beehive_id:
        raise Exception(f"beehive_id is missing")



    try:
        create_ssh_upload_cert(bee_db, node_id, beehive_obj )
    except Exception as e:
        raise Exception(f"create_ssh_upload_cert failed: {type(e).__name__} {str(e)}")

    try:
        create_tls_cert_for_node(bee_db, node_id, beehive_obj)
    except Exception as e:
        raise Exception(f"create_tls_cert_for_node failed: {type(e).__name__} {str(e)}")

    node_keypair = bee_db.get_node_keypair(node_id)

    ssh_key_private = node_keypair["ssh_key_private"]
    ssh_key_public = node_keypair["ssh_key_public"]

    try:
        node_creds = bee_db.get_node_credentials_all(node_id, beehive_id)
    except Exception as e:
        raise Exception(f"get_node_credentials_all failed: {type(e).__name__} {str(e)}")

    ssh_upload_cert = node_creds["ssh_upload_cert"]

    # create and push secret for upload-ssh-key

    upload_secret = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata":
            {"name": "wes-beehive-upload-ssh-key"},
        "type": "Opaque",
        "data":{
            "ssh-key": b64string_encode(ssh_key_private),
            "ssh-key.pub": b64string_encode(ssh_key_public),
            "ssh-key-cert.pub": b64string_encode(ssh_upload_cert)
            }
    }

    result_stdout, result_stderr = kubectl_apply(node_id, upload_secret)
    logger.debug(result_stdout)
    if result_stderr:
        logger.error(result_stderr)

    # create and upload tls secret

    tls_cert = node_creds["tls_cert"]
    tls_key  = node_creds["tls_key"]
    tls_secret = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata":
            {"name": f"{node_id}-tls-secret"},
        "type": "Opaque",
        "data":{
            "cert.pem": b64string_encode(tls_cert),
            "key.pem": b64string_encode(tls_key)
            }
    }

    result_stdout, result_stderr = kubectl_apply(node_id, tls_secret)
    logger.debug(result_stdout)
    if result_stderr:
        logger.error(result_stderr)

    ####################

    #for key in ["rmq_host", "rmq_port", "upload_host", "upload_port"]:
    #    if not key in beehive_obj:
    #        raise Exception(f"Beekeeper field {key} missing")

    rmq_host = beehive_obj.get("rmq_host", "missing")
    rmq_port = beehive_obj.get("rmq_port", "missing")
    upload_host = beehive_obj.get("upload_host", "missing")
    upload_port = beehive_obj.get("upload_port", "missing")


    waggle_ConfigMap = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
            "name": "waggle-config"
        },
        "data": {
            "WAGGLE_NODE_ID": node_id,
            "WAGGLE_BEEHIVE_RABBITMQ_HOST": rmq_host,
            "WAGGLE_BEEHIVE_RABBITMQ_PORT": str(rmq_port),
            "WAGGLE_BEEHIVE_UPLOAD_HOST": upload_host,
            "WAGGLE_BEEHIVE_UPLOAD_PORT": str(upload_port)
        }
    }

    result_stdout, result_stderr = kubectl_apply(node_id, waggle_ConfigMap)
    logger.debug(result_stdout)
    if result_stderr:
        logger.error(result_stderr)


    deploy_script= \
"""\
#!/bin/sh
### This script was generated by beekeeper ###
set -e
set -x


if [ ! -e "/opt/waggle-edge-stack" ] ; then
    cd /opt
    git clone https://github.com/waggle-sensor/waggle-edge-stack.git
fi

cd /opt/waggle-edge-stack
git pull origin main
#git checkout tags/v.1.0

cd /opt/waggle-edge-stack/kubernetes

./deploy-stack.sh skip-env
"""

    result_stdout, result_stderr = node_ssh(node_id, "cat > /tmp/deploy.sh", input_str=deploy_script)
    logger.debug(result_stdout)
    if result_stderr:
        logger.error(result_stderr)

    result_stdout, result_stderr =  node_ssh(node_id, "sh /tmp/deploy.sh", input_str=deploy_script)
    logger.debug(result_stdout)
    if result_stderr:
        logger.error(result_stderr)



    if this_debug:
        return {"waggle_ConfigMap": waggle_ConfigMap ,
                 "tls_secret":tls_secret,
                 "upload_secret": upload_secret}

        #node_creds["tls_result_stdout"] = result_stdout
        #node_creds["tls_result_stderr"] = result_stderr

    return {"success":True}

    #TODO:
    # - trigger/notify ansible update

    # works: ssh -i /config/nodes/node_key.pem -o IdentitiesOnly=true -o "ProxyCommand=ssh root@bk-sshd -p 2201 -i /config/admin-key/admin.pem  netcat -U /home_dirs/node-0000000000000001/rtun.sock" root@foo





def create_ssh_upload_cert(bee_db, node_id, beehive_obj ):

    beehive_id = beehive_obj.get("id", "")
    if not beehive_id:
        raise Exception(f"beehive_id is missing")

    ssh_upload_cert = bee_db.get_node_credential(node_id, beehive_id, "ssh_upload_cert")
    if ssh_upload_cert:
        # already exists      TODO check expiration date (store explicitly)
        return

    # what key type is this beehive using ?
    beehive_key_type = beehive_obj.get("key-type", "")
    if not beehive_key_type:
        fields = ",".join(beehive_obj.keys())
        raise Exception(f"key-type is missing in beehive_obj (got: { fields })")

    beehive_key_type_args = beehive_obj.get("key-type-args", "")


    logger.debug("call create_beehive_files")
    # make sure /beehives/... files exist
    try:
        create_beehive_files(beehive_obj)
    except Exception as e:
        raise Exception(f"create_beehive_files returned: {type(e)}: {str(e)}")

    ca_path = os.path.join(beehives_root, beehive_id, "ssh", "ca")

    if not os.path.exists(ca_path):
        raise Exception(f"ssh ca file {ca_path} not found")


    logger.debug("call get_node_keypair")
    # check if key-pair is available
    try:
        creds = get_node_keypair(node_id)
    except Exception as e:
        raise Exception(f"get_node_keypair returned: {str(e)}")

    if not creds:
        raise Exception(f"Node credentials not found")

    logger.debug("got node credentials from DB")

    #beehive_obj["comment":"found creds"]
    key_generator = SSHKeyGen(deleteDirectory=False)

    try:
        key_generator.write_keys_to_files(node_id, creds["private_key"], creds["public_key"])
    except Exception as e:
        raise Exception(f"key_generator.write_keys_to_files returned: {type(e)}: {str(e)}")

    try:
        upload_certificate = key_generator.create_upload_certificate(ca_path, beehive_key_type, beehive_key_type_args, node_id)
    except Exception as e:
        raise Exception(f"key_generator.create_upload_certificate returned: {type(e)}: {str(e)}")

        #{ "certificate": certificate, "user": user}

    upload_certificate_values = {}
    upload_certificate_values["ssh_upload_cert"] = upload_certificate["certificate"]
    upload_certificate_values["ssh_upload_user"] = upload_certificate["user"]

    count = bee_db.set_node_credentials(node_id, beehive_id, upload_certificate_values)
    if count != 2 :
        raise Exception("Saving ssh upload cert in mysql seems to have failed, expected 2 insertions, but got {count}")

    return

def create_tls_cert_for_node(bee_db, node_id, beehive_obj ):

    beehive_id = beehive_obj.get("id", "")
    if not beehive_id:
        raise Exception(f"beehive_id is missing")

    node_tls_cert = bee_db.get_node_credential(node_id, beehive_id, "tls_cert")
    if node_tls_cert:
        # already exists      TODO check expiration date (store explicitly)
        return

    logger.debug("call create_beehive_files")
    # make sure /beehives/... files exist
    try:
        create_beehive_files(beehive_obj)
    except Exception as e:
        raise Exception(f"create_beehive_files returned: {type(e)}: {str(e)}")

    tls_ca_path = os.path.join(beehives_root, beehive_id, "tls", "cakey.pem")
    tls_ca_cert_path = os.path.join(beehives_root, beehive_id, "tls", "cacert.pem")

    if not os.path.exists(tls_ca_path):
        raise Exception(f"tls ca file {tls_ca_path} not found")


    logger.debug("call get_node_keypair")
    # check if key-pair is available
    try:
        creds = get_node_keypair(node_id)
    except Exception as e:
        raise Exception(f"get_node_keypair returned: {str(e)}")

    if not creds:
        raise Exception(f"Node credentials not found")


    # creds["private_key"]

    key_generator = SSHKeyGen(deleteDirectory=False)


    #create node TLS (returns keyfile and certfile)
    result = key_generator.create_node_tls_certificate(tls_ca_path, tls_ca_cert_path, node_id)


    # store results
    upload_values = {}
    upload_values["tls_key"] = result["keyfile"]
    upload_values["tls_cert"] = result["certfile"]
    upload_values["tls_user"] = result["user"]

    count = bee_db.set_node_credentials(node_id, beehive_id, upload_values)
    if count != 3 :
        raise Exception("Saving node tls files in mysql seems to have failed, expected 3 insertions, but got {count}")


    return


# /node/<node_id>
class Node(MethodView):
    def get(self, node_id):
        return { "error" : "nothing here, use the /state resource instead " }

    # example: curl localhost:5000/node/xxx -d '{"assign_beehive": "sage-beehive"}'
    def post(self, node_id):
        try:
#request.get
            postData = request.get_json(force=True, silent=False)

        except Exception as e:

            raise ErrorResponse(f"Error parsing json: { sys.exc_info()[0] }  {e}" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

        this_debug = request.args.get('debug', "false") in ["true", "1"]

        if "assign_beehive" in postData:
            try:
                result = node_assign_beehive(node_id, postData["assign_beehive"], this_debug)
            except Exception as e:
                logger.error(e)
                raise ErrorResponse(f"node_assign_beehive retruned: { type(e).__name__ }: {str(e)}" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)





        return jsonify(result)


class BeehivesList(MethodView):

    def get(self):

        view = request.args.get('view', "")

        try:
            bee_db = BeekeeperDB()
            fields = ["id"]
            if view == "full":
                fields=None

            result =  bee_db.get_objects('beehives', fields = fields)
        except Exception as e:
            raise ErrorResponse(f"Error getting list of beehives: { type(e).__name__ }  {e}" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

        return jsonify({"data":result})


    # create/update  beehive
    # example: curl localhost:5000/beehives -d '{"id": "sage-beehive", "key-type": "rsa-sha2-256", "rmq-host":"foobar4", "rmq-port": 7, "upload-host":"x", "upload-port": 123}'
    # key-type: rsa-sha2-256  or Ed25519
    def post(self):
        try:
#request.get
            postData = request.get_json(force=True, silent=False)

        except Exception as e:

            raise ErrorResponse(f"Error parsing json: { sys.exc_info()[0] }  {e}" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)


        if not "id" in postData:
            raise ErrorResponse(f"Field id is missing" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

        if not "key-type" in postData:
            raise ErrorResponse(f"Field key-type is missing" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

        beehive_id = postData["id"]
        key_type = postData["key-type"]
        key_type_args = postData.get("key-type-args", "")

        bee_db = BeekeeperDB()

        #TODO check if beehive already exists

        obj = bee_db.get_beehive(beehive_id)
        if obj:
            #raise ErrorResponse(f"Beehive {beehive_id} already exists" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)
            # update

            modified = 0
            updates = {}
            for key in ["key_type", "key_type_args", "rmq_host", "rmq_port" , "upload_host" , "upload_port"]:
                key_dash = key.replace("_", "-")
                if not key_dash in postData:
                    continue

                updates[key] = postData[key_dash]

            modified = bee_db.update_object_fields("beehives", updates, "id", beehive_id)
            # modified is always 0 or 1, not more



            return jsonify({"success": True})

        # create
        result = bee_db.create_beehive(beehive_id, key_type, key_type_args)
        if result != 1:
            raise ErrorResponse(f"Could not create beehive {beehive_id}  ({result})" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

        return jsonify({"success": True})



class Beehives(MethodView):

    # get beehive object including all credentials
    def get(self, beehive_id):


        bee_db = BeekeeperDB()
        obj = bee_db.get_beehive(beehive_id)
        if not obj:
            raise Exception(f"Beehive {beehive_id} not found" )



        return jsonify(obj)


    # configure beehive credentials
    # curl -F "tls-key=@tls/ca/cakey.pem" -F "tls-cert=@tls/ca/cacert.pem"  -F "ssh-key=@ssh/ca/ca" -F "ssh-pub=@ssh/ca/ca.pub" -F "ssh-cert=@ssh/ca/ca-cert.pub"  localhost:5000/beehives/sage-beehive
    def post(self, beehive_id):


        #postData = request.get_json(force=True, silent=False)

       # for field in

        expected_forms = ["tls-key", "tls-cert", "ssh-key", "ssh-pub", "ssh-cert"]

        count_updated = 0
        data={}
        try:

            bee_db = BeekeeperDB()
            obj = bee_db.get_beehive(beehive_id)
            if not obj:
                raise Exception(f"Beehive {beehive_id} not found" )



            for formname in request.files:
                if not formname in expected_forms:
                    raise Exception(f"Formname {formname} not supported" )

            # we could remove this check...
            for formname in expected_forms:
                if not formname in request.files:
                    raise Exception(f"Formname {formname} missing" )


            for formname in request.files:


                formdata = request.files.get(formname).read().decode("utf-8")
                if not formdata:
                    raise Exception(f"Field {formname} empty" )

                data[formname] = formdata
                #logger.debug(f"data: {formname} {data[formname]}")
                #filename = secure_filename(file.filename)
                #logger.debug(f"filename: {filename}")


            for formname in data:

                col_name = formname.replace("-", "_ca_")

                count_updated += bee_db.update_object_field("beehives", col_name, data[formname], "id", beehive_id)


        except Exception as e:
            raise ErrorResponse(f"something failed: {str(e)}" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

        return jsonify({"modified": count_updated})


    def delete(self, beehive_id):

        bee_db = BeekeeperDB()
        result = bee_db.delete_object("beehives", "id", beehive_id )

        return jsonify({"deleted": result})


class Credentials(MethodView):
    def get(self, node_id):


        try:

            bee_db = BeekeeperDB()
            results = bee_db.get_node_keypair(node_id)

        except Exception as e:
            raise ErrorResponse(f"Unexpected error: {e}" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

        if not results:
            raise ErrorResponse(f"Not found." , status_code=HTTPStatus.NOT_FOUND )

        return jsonify(results)

    # example: {"ssh_key_private":"x", "ssh_key_public":"y"}
    def post(self, node_id):



        try:
#request.get
            postData = request.get_json(force=True, silent=False)

        except Exception as e:

            raise ErrorResponse(f"Error parsing json: { sys.exc_info()[0] }  {e}" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

        if not postData:
            raise ErrorResponse(f"Could not parse json." , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

        valid_keys = {"ssh_key_private", "ssh_key_public"}
        expected_keys  = valid_keys

        for key in postData:
            if key not in valid_keys:
                raise ErrorResponse(f"Key {key} not supported" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

        for key in expected_keys:
            if key not in postData:
                raise ErrorResponse(f"Key {key} missing" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)



        try:

            bee_db = BeekeeperDB()
            results = bee_db.set_node_keypair(node_id, postData)

        except Exception as e:
            raise ErrorResponse(f"Unexpected error: {e}" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)



        return "success"

    def delete(self, node_id):


        try:

            bee_db = BeekeeperDB()
            result_count = bee_db.delete_object( "node_credentials", "id", node_id)

        except Exception as e:
            raise ErrorResponse(f"Unexpected error: {e}" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

        return jsonify({"deleted": result_count})





#@app.route("/register")
class Registration(MethodView):

    # example: curl localhost:5000/register?id=xxx
    # this creates id: node-xxx
    def get(self):
        """API to create keys, certificate and user for end-point.

        Arguments:
            id (str): unique ID for this end-point

        Returns:
            dict: end-point id, private key, public key and certificate
        """
        node_id = request.args.get("id", type=str)
        if not node_id:
            return f"Error: id missing\n", 500

        logger.debug("Register user [{}]".format(node_id))

        try:
            registration_result =  _register(node_id)
        except Exception as e:
            logger.error(f"_register failed: {str(e)}")
            traceback.print_exc()
            return f"Error: unable to register id [{node_id} , {str(e)}]\n", 500

        # update beekeeper db


        try:
            register_node(node_id)
        except Exception as e:
            return f"Error: Registration failed: {str(e)}", 500




        #return json.dumps(registration_result)
        return registration_result




app = Flask(__name__)
CORS(app)
app.config["PROPAGATE_EXCEPTIONS"] = True
#app.wsgi_app = ecr_middleware(app.wsgi_app)

app.add_url_rule('/', view_func=Root.as_view('root'))
app.add_url_rule('/log', view_func=Log.as_view('log'))
app.add_url_rule('/state', view_func=ListStates.as_view('list_states'))
app.add_url_rule('/state/<node_id>', view_func=State.as_view('state'))
app.add_url_rule('/credentials/<node_id>', view_func=Credentials.as_view('credentials'))

# administrative functionality: e.g. assign beehive
app.add_url_rule('/node/<node_id>', view_func=Node.as_view('node'))
app.add_url_rule('/beehives', view_func=BeehivesList.as_view('beehivesList'))
app.add_url_rule('/beehives/<beehive_id>', view_func=Beehives.as_view('beehives'))

# this is where nodes register
app.add_url_rule('/register', view_func=Registration.as_view('registration'))

@app.errorhandler(ErrorResponse)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


def setup_app(app):




   # All your initialization code
    bee_db = BeekeeperDB()


    for table_name in ['nodes_log', 'nodes_history', 'beehives']:

        stmt = f'SHOW COLUMNS FROM `{table_name}`'
        logger.debug(f'statement: {stmt}')
        bee_db.cur.execute(stmt)
        rows = bee_db.cur.fetchall()


        table_fields[table_name] = []
        table_fields_index[table_name] ={}
        for row in rows:
            #print(row, flush=True)
            table_fields[table_name].append(row[0])

        for f in range(len(table_fields[table_name])):
            table_fields_index[table_name][table_fields[table_name][f]] = f


    logger.debug(table_fields)
    logger.debug(table_fields_index)


    initialize_test_nodes()




setup_app(app)


if __name__ == '__main__':

    app.run(debug=False, host='0.0.0.0')
    #app.run()