#!/usr/bin/env python3

# ### mysqlclient ###
# pip install mysqlclient
# https://github.com/PyMySQL/mysqlclient-python
# https://mysqlclient.readthedocs.io/


import os
import sys


from flask import Flask
from flask.views import MethodView
from flask import jsonify
from flask.wrappers import Response

from error_response import ErrorResponse


import MySQLdb
from flask import request
from flask import abort, jsonify

from http import HTTPStatus

import config
import datetime
import time

import dateutil.parser

table_fields = {}
table_fields_index ={}


class BeekeeperDB():
    def __init__ ( self , retries=60) :

        if not config.mysql_host:
            raise Exception("mysql_host is not defined")
        
        count = 0
        while True:
            try:
                self.db=MySQLdb.connect(host=config.mysql_host,user=config.mysql_user,
                  passwd=config.mysql_password,db=config.mysql_db)
            except Exception as e: # pragma: no cover
                if count > retries:
                    raise
                print(f'Could not connnect to database, error={e}, retry in 2 seconds', file=sys.stderr)
                time.sleep(2)
                count += 1
                continue
            break

        self.cur=self.db.cursor()
        return


    def nodes_log_add(self, logData):
        #node_id, table_name, operation, field_name, new_value, source, effective_time=None
        fields = '`node_id`, `table_name`, `operation`, `field_name`, `new_value`, `source`, `effective_time`'
        values_s = '%s, %s, %s, %s, %s, %s, %s'
        #values = [node_id, table_name, operation, field_name, new_value, source]
        
        smallest_timestamp = None 
        values = []
        for log in logData:
            effective_time =  dateutil.parser.parse(log["effective_time"])
            
            if (not smallest_timestamp) or (effective_time < smallest_timestamp):
                smallest_timestamp = effective_time

            value_tuple =(log["node_id"], log["table_name"], log["operation"], log["field_name"], log["new_value"], log["source"], effective_time)
            values.append(value_tuple)




        self.cur.execute("LOCK TABLES `nodes_log` WRITE")

        stmt = f'INSERT INTO `nodes_log` ( {fields} ) VALUES ({values_s})'
        #debug_stmt = stmt
        for tup in values:
            debug_stmt = stmt
            for i in tup:
                debug_stmt = debug_stmt.replace("%s", f'"{i}"', 1)
            print(f'debug_stmt: {debug_stmt}', file=sys.stderr, flush=True)

        #print(f'debug_stmt: {debug_stmt}', file=sys.stderr)
        
        self.cur.executemany(stmt, values )
        #self.cur.execute("UNLOCK TABLES")
        self.db.commit()

        try:

            self.replay_log(replay_from_timestamp = smallest_timestamp)
        except Exception as e:
            raise Exception("Log replay failed: "+str(e))

        return

    
    # a) replay log from scratch/zero
    # b) replay log from effective_time (as changes)
    # replay has to merge log entries with same timestamp !
    def replay_log(self, replay_from_timestamp=None):


        #fields = ['node_id', 'table_name', 'operation', 'field_name', 'new_value', 'source', 'effective_time', 'modified_time']
        #fieldIndex = {}
        #for f in range(len(fields)):
        #    fieldIndex[fields[f]] = f
        fields = table_fields['nodes_log']
        fieldIndex = table_fields_index['nodes_log']

        fields_str = ', '.join(fields)

        stmt = 'LOCK TABLES `nodes_history` WRITE , `nodes_log` READ'
       #self.cur.execute(stmt)
       # stmt = 'LOCK TABLES `nodes_log` READ'
        self.cur.execute(stmt)
        #self.db.commit()

        if replay_from_timestamp:
            # delete all entries newer than replay_from_timestamp in history

           

            stmt = f'DELETE FROM `nodes_history` WHERE `timestamp` >= %s'
            print(f'statement: {stmt}')
            try:
                self.cur.execute(stmt, (replay_from_timestamp,))
                self.db.commit()
            except Exception as e:
                raise Exception("Deleting lastes history failed:" + str(e))


        nodes_last_state = {}

        
        if replay_from_timestamp:
            stmt = f'SELECT {fields_str} FROM `nodes_log` WHERE `effective_time` >= %s ORDER BY `effective_time`'
            print(f'statement: {stmt}')
            self.cur.execute(stmt, (replay_from_timestamp,))
        else: 
            stmt = f'SELECT {fields_str} FROM `nodes_log` ORDER BY `effective_time`'
            print(f'statement: {stmt}')
            self.cur.execute(stmt)

        while True:
            print(f'loop')
            rows = self.cur.fetchmany(size=10)
            if not rows:
                break

            for row in rows:
                print(row, flush=True)
                #print(rows, flush=True)
                node_id = row[fieldIndex['node_id']]
                op = row[fieldIndex['operation']]
                if op != "insert":
                    print(f"ERROR: skipping invalid operation {op}")
                    #raise Exception(f"Operation {op} not supported")
                    
                col = row[fieldIndex['field_name']]
                value = row[fieldIndex['new_value']]
                effective_time = row[fieldIndex['effective_time']]
                node_object = nodes_last_state.get(node_id, {})
                #if not node_object:
                # TODO get object from db
                
                if 'timestamp' in node_object and node_object['timestamp'] != effective_time:
                    # this is a new timestamp, process old history point first
                    try:
                        self.insert_object("nodes_history", node_object)
                    except Exception as e:
                        raise Exception("insert_object failed:" + str(e))
                # this could be either a new one OR an old one with the same timestamp
                node_object['id']=node_id

                node_object[col]=value
                node_object['timestamp'] = effective_time
                print('node_object:')
                print(node_object, flush=True)
                nodes_last_state[node_id] = node_object

        # now insert the last entries of each node:
        for node_id in nodes_last_state:
            node_object = nodes_last_state[node_id]
            try:
                self.insert_object("nodes_history", node_object)
            except Exception as e:
                        raise Exception("insert_object failed:" + str(e))

        stmt = 'UNLOCK TABLES'
        self.cur.execute(stmt)
                

    def getNodeState(self, node_id, timestamp=None):

        table_name = 'nodes_history'
        fields = table_fields[table_name]
        fields_str = ", ".join(fields)
        
        stmt = f'SELECT {fields_str} FROM `{table_name}` WHERE `id` = %s ORDER by `timestamp` DESC LIMIT  1'
        print(f'statement: {stmt}', flush=True)
        self.cur.execute(stmt, (node_id,))
        row = self.cur.fetchone()

        result = {}
        for i in range(len(row)):
            result[fields[i]] = row[i]

        return result




    def insert_object(self, table_name, row_object):

       

        fields_str , values, replacement_str = self.dict2mysql(row_object)
        
        stmt = f'INSERT INTO {table_name} ({fields_str}) VALUES ({replacement_str})'

        debug_stmt = stmt
        for i in values:
            debug_stmt = debug_stmt.replace("%s", f'"{i}"', 1)
        
        print(f'debug_stmt: {debug_stmt}', file=sys.stderr)
        self.cur.execute(stmt, (*values, ))
        self.db.commit()

    def dict2mysql(self, obj):
        fields = []
        values = []
        
        for f in obj:
            fields.append(f)
            values.append(obj[f])
            

        fields_str = ", ".join(fields)
        replacement_str = "%s " + ", %s" * ( len(values) -1 )

        return fields_str, values, replacement_str



    def truncate_table(self, table_name):
        stmt = f'TRUNCATE TABLE `{table_name}`'
        print(f'statement: {stmt}')
        self.cur.execute(stmt)

       



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

        

        if not isinstance( postData, list ):
            raise ErrorResponse("array expected", status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

        try:
            bee_db = BeekeeperDB()

            logData = []
            default_effective_time = datetime.datetime.now(datetime.timezone.utc) # this way all operations in this submission have the exact same time
            for op in postData:
                
                for f in ["node_id", "operation", "field_name", "field_value", "source"]:
                    if f not in op:
                        raise Exception(f'Field {f} missing.')

                
                try:
                    newLogDataEntry = {
                        "node_id" : op["node_id"],
                        "table_name": "nodes_log" , 
                        "operation": op["operation"],  
                        "field_name" : op["field_name"], 
                        "new_value" : op["field_value"] , 
                        "source": op["source"],
                        "effective_time" : op.get("effective_time", default_effective_time) }

                except Exception as ex:
                    raise ErrorResponse(f"Unexpected error: {e}" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

                logData.append(newLogDataEntry)
                #print("success", flush=True)
                

            bee_db.nodes_log_add(logData) #  effective_time=effective_time)



        
            
           
        except Exception as e:
            #raise ErrorResponse(f"Unexpected error: { sys.exc_info()[0] } {e}" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)
            raise ErrorResponse(f"Unexpected error: {e}" , status_code=HTTPStatus.INTERNAL_SERVER_ERROR)
        
        response = {"success" : 1}
        return response


    def get(self):
        return "try POST..."




app = Flask(__name__)
app.config["PROPAGATE_EXCEPTIONS"] = True
#app.wsgi_app = ecr_middleware(app.wsgi_app)


app.add_url_rule('/', view_func=Root.as_view('root'))
app.add_url_rule('/log', view_func=Log.as_view('log'))


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