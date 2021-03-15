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




# /
class Root(MethodView):
    def get(self):
        return "SAGE Beekeeper"

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


        listData = None
        if isinstance( postData, dict ):
            listData = [ postData ]
            print("Putting postData into array ", flush=True)
        else:
            listData = postData
            print("Use postData as is ", flush=True)

        if not isinstance( listData, list ):
            raise ErrorResponse("list expected", status_code=HTTPStatus.INTERNAL_SERVER_ERROR)


        bee_db = None
        try:
            bee_db = BeekeeperDB()
        except Exception as e:
            raise ErrorResponse(f"Could not create BeekeeperDB: {e}" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)


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
                raise ErrorResponse(f"Unexpected error in creating newLogDataEntry : {ex}" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

            logData.append(newLogDataEntry)
            #print("success", flush=True)

        try:
            bee_db.nodes_log_add(logData) #  effective_time=effective_time)
        except Exception as ex:
                raise ErrorResponse(f"nodes_log_add failed: {ex}" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

        response = {"success" : 1}
        return response


    def get(self):
        return "try POST..."



# /state
class LatestState(MethodView):
    def get(self):
        try:
            bee_db = BeekeeperDB()
            node_state = bee_db.list_latest_state()

        except Exception as e:
            raise ErrorResponse(f"Unexpected error: {e}" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

        return { "data" : node_state }



# TODO: add /state/ to get state of all nodes
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




app = Flask(__name__)
CORS(app)
app.config["PROPAGATE_EXCEPTIONS"] = True
#app.wsgi_app = ecr_middleware(app.wsgi_app)

app.add_url_rule('/', view_func=Root.as_view('root'))
app.add_url_rule('/log', view_func=Log.as_view('log'))
app.add_url_rule('/state', view_func=LatestState.as_view('latest_state'))
app.add_url_rule('/state/<node_id>', view_func=State.as_view('state'))


@app.errorhandler(ErrorResponse)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


def setup_app(app):
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