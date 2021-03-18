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


import bk_db
from  bk_db import BeekeeperDB, table_fields , table_fields_index

#import flask

import logging

import os.path
import requests

from sshkeygen import SSHKeyGen
import traceback



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
#BEEKEEPER_DB_API = os.getenv("BEEKEEPER_DB_API" ,"http://bk-api:5000")
BEEKEEPER_DB_API = "http://localhost:5000"
KEY_GEN_TYPE = os.getenv("KEY_GEN_TYPE", "")
KEY_GEN_ARGS = os.getenv("KEY_GEN_ARGS", "")
if not KEY_GEN_TYPE:
    sys.exit("KEY_GEN_TYPE not defined")



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

def register_node(node_id):

    payload = {"node_id": node_id, "source": "beekeeper-register", "operation":"insert", "field_name": "registration_event", "field_value": datetime.datetime.now().replace(microsecond=0).isoformat()}

    #url = f'{BEEKEEPER_DB_API}/log'
    try:
        insert_log(payload)
        #bk_api_response = requests.post(url,data=json.dumps(payload), timeout=3)
    except Exception as e:
        #raise Exception(f"Error: X Beekeeper DB API ({url}) cannot be reached: {str(e)}")
        raise Exception(f"insert_log returned: {str(e)}")


    return


# wait for beekeeper API and check for test nodes that may have to be registered
def setup_app_registration():


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


            register_node(node_id)

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

def get_node_credentials(node_id):

    #url = f'{BEEKEEPER_DB_API}/credentials/{node_id}'
    #try:
    #    bk_api_result = requests.get(url, timeout=3)
    #except Exception as e:
    #    raise Exception(f"Beekeeper DB API ({BEEKEEPER_DB_API}) cannot be reached, requests.get returned: {str(e)}")


    try:
        bee_db = BeekeeperDB()
        return_obj = bee_db.get_node_credentials(node_id)
    except Exception as e:
        raise Exception(f"bee_db.get_node_credentials returned: {str(e)}")

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
        bee_db.set_node_credentials(node_id, post_creds)
    except Exception as e:
        raise Exception(f"set_node_credentials returned: {str(e)}")

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
        creds = get_node_credentials(node_id)
    except Exception as e:
        raise Exception(f"get_node_credentials returned: {str(e)}")



    client_keys = SSHKeyGen()

    if creds:
        print("got credentials from DB")
        # Files found in DB,nor write to disk so they can be used to create certififcate
        try:
            client_keys.write_keys_to_files(node_id, creds["private_key"], creds["public_key"])
        except Exception as e:
            raise Exception(f"client_keys.write_keys_to_files returned: {str(e)}")

    else:

        # generate new keys sizgned by the CA for custom tunnel to beekeeper
        # create a user somewhere to allow the "node specific user" to connect
        logger.debug("- generate key pair (no credentials in DB yet)")
        try:
            creds = client_keys.create_key_pair(node_id, KEY_GEN_TYPE, KEY_GEN_ARGS)
        except Exception as e:
            raise Exception(f"client_keys.create_key_pair returned: {str(e)}")

        try:
            post_node_credentials(node_id, creds["private_key"], creds["public_key"])
        except Exception as e:
            raise Exception(f"post_node_credentials returned: {str(e)}")

    for key in ["private_key", "public_key"]:
        if not key in creds:
            raise Exception(f"{key} is missing")




    logger.debug("- generate certificate")
    try:
        cert_obj = client_keys.create_certificate(node_id, CA_FILE) # returns { "certificate": certificate, "user": user}
    except Exception as e:
            raise Exception(f"client_keys.create_certificate returned: {str(e)}")
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
    post_results = requests.post(url, data=data, timeout=3)
    if not post_results.ok:
        raise Exception(f"Unable to add user [{user}]")

    logger.debug(f"- successfully created user [{user}]")

    #payload = {"node_id": node_id, "source": "beekeeper-register", "operation":"insert", "field_name": "registration_event", "field_value": datetime.datetime.now().replace(microsecond=0).isoformat()}
    return data




# /
class Root(MethodView):
    def get(self):
        return "SAGE Beekeeper API"


def insert_log(postData):
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


        try:
            newLogDataEntry = {
                "node_id": op["node_id"],
                "table_name": "nodes_log" ,
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
        bee_db.nodes_log_add(logData) #  effective_time=effective_time)
    except Exception as ex:
        raise Exception(f"nodes_log_add failed: {ex}" )



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


class Credentials(MethodView):
    def get(self, node_id):


        try:

            bee_db = BeekeeperDB()
            results = bee_db.get_node_credentials(node_id)

        except Exception as e:
            raise ErrorResponse(f"Unexpected error: {e}" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

        if not results:
            raise ErrorResponse(f"Not found." , status_code=HTTPStatus.NOT_FOUND )

        return results

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
            results = bee_db.set_node_credentials(node_id, postData)

        except Exception as e:
            raise ErrorResponse(f"Unexpected error: {e}" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)



        return "success"

    def delete(self, node_id):


        try:

            bee_db = BeekeeperDB()
            result_count = bee_db.delete_object( "node_credentials", "id", node_id)

        except Exception as e:
            raise ErrorResponse(f"Unexpected error: {e}" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

        return {"deleted": result_count}





#@app.route("/register")
class Registration(MethodView):
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

app.add_url_rule('/register', view_func=Registration.as_view('registration'))

@app.errorhandler(ErrorResponse)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


def setup_app(app):

    #setup_app_registration()


   # All your initialization code
    bee_db = BeekeeperDB()


    for table_name in ['nodes_log', 'nodes_history']:

        stmt = f'SHOW COLUMNS FROM `{table_name}`'
        print(f'statement: {stmt}')
        bee_db.cur.execute(stmt)
        rows = bee_db.cur.fetchall()


        table_fields[table_name] = []
        table_fields_index[table_name] ={}
        for row in rows:
            #print(row, flush=True)
            table_fields[table_name].append(row[0])

        for f in range(len(table_fields[table_name])):
            table_fields_index[table_name][table_fields[table_name][f]] = f


    print(table_fields, flush=True)
    print(table_fields_index, flush=True)





setup_app(app)


if __name__ == '__main__':

    app.run(debug=False, host='0.0.0.0')
    #app.run()