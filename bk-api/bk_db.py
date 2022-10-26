import MySQLdb
import dateutil.parser
import os
import time
import logging

logger = logging.getLogger(__name__)

# TODO(sean) this should probably not be a global... we should look at how to either not need this at all or move it into the DB object.
table_fields = {}
table_fields_index = {}


class BeekeeperDB:

    # TODO(sean) make this a context manager to ensure cleanup after operations

    def __init__(self, host, database, user, password, retries=60):
        if not host:
            raise Exception("MYSQL_HOST is not defined")

        if not database:
            raise Exception("MYSQL_DATABASE is not defined")

        if not user:
            raise Exception("MYSQL_USER is not defined")

        if not password:
            raise Exception("MYSQL_PASSWORD is not defined")

        # NOTE(sean) I don't think we want the retry logic to live inside this function but instead managed by the caller.
        #
        # For example, if there is a database problem and a client connects to the API, this will keep retrying for multiple
        # minutes. Even if the client closes the request, the server will continue this retry loop until it times out.
        #
        # I think it would be better to immediately fail with some kind of "Service Unavailable" status code instead and leave
        # it to clients to retry.
        count = 0
        while True:
            try:
                self.db = MySQLdb.connect(host=host, user=user, passwd=password, db=database)
            except Exception as e: # pragma: no cover
                if count > retries:
                    raise
                logger.error(f'Could not connnect to database, error={e}, retry in 2 seconds')
                time.sleep(2)
                count += 1
                continue
            break

        self.cur=self.db.cursor()
        return

    def close(self):
        self.cur.close()
        self.db.close()

    def nodes_log_add(self, logData, lock_tables=True, lock_requested_by="", replay=True):
        # TODO(sean) It seems like lock_tables and lock_requested_by are unused, but calls to this
        # use it throughout the code base. Just based on the name, I assume lock_tables means that
        # a series of operations is done transactionally? If that true, then I don't understand why
        # we would ever disable that?

        #node_id, table_name, operation, field_name, new_value, source, effective_time=None
        fields = '`node_id`, `table_name`, `operation`, `field_name`, `new_value`, `source`, `effective_time`'
        values_s = '%s, %s, %s, %s, %s, %s, %s'
        #values = [node_id, table_name, operation, field_name, new_value, source]

        smallest_timestamp = None
        values = []
        for log in logData:
            effective_time =  dateutil.parser.parse(log["effective_time"]).replace(microsecond=0)

            if (not smallest_timestamp) or (effective_time < smallest_timestamp):
                smallest_timestamp = effective_time

            # do some sanity check
            table_name = log["table_name"]
            if not table_name in table_fields_index:
                raise Exception(f"table_name {table_name} unknown")

            field_name = log["field_name"]

            if not field_name in table_fields_index[table_name]:
                raise Exception(f"{field_name} not a valid field name in table {table_name}")

            value_tuple =(log["node_id"], table_name, log["operation"], field_name, log["new_value"], log["source"], effective_time)
            values.append(value_tuple)

        #if lock_tables:
        #    stmt = "LOCK TABLES `nodes_log` WRITE, `nodes_history` WRITE "
        #    logger.debug(f'(nodes_log_add) {stmt} (by {lock_requested_by})')
        #    self.cur.execute(stmt)
        #    logger.debug(f'(nodes_log_add) got lock')

        stmt = f'INSERT INTO `nodes_log` ( {fields} ) VALUES ({values_s})'
        #debug_stmt = stmt
        for tup in values:
            debug_stmt = stmt
            for i in tup:
                debug_stmt = debug_stmt.replace("%s", f'"{i}"', 1)
            logger.debug(f'debug_stmt: {debug_stmt}')

        logger.debug(f'debug_stmt: {debug_stmt}')

        self.cur.executemany(stmt, values )

        self.db.commit()

        if replay:
            try:

                #self.replay_log(replay_from_timestamp = smallest_timestamp, get_locks=False)
                self.replay_log()
            except Exception as e:
            #    if lock_tables:
            #        logger.debug(f'nodes_log_add exists with exception: UNLOCK TABLES')
            #        self.cur.execute("UNLOCK TABLES")
            #        self.db.commit()
                raise Exception("Log replay failed: "+str(e))

        #if lock_tables:
        #    logger.debug(f'(nodes_log_add) UNLOCK TABLES (by {lock_requested_by})')
        #    self.cur.execute("UNLOCK TABLES")
        #    self.db.commit()
        #    logger.debug(f'(nodes_log_add) locks released')
        return


    # a) replay log from scratch/zero
    # b) replay log from effective_time (as changes)
    # replay has to merge log entries with same timestamp !
    def replay_log(self, replay_from_timestamp=None, get_locks=True):
        logger.debug(f'replay_log')
        #fields = ['node_id', 'table_name', 'operation', 'field_name', 'new_value', 'source', 'effective_time', 'modified_time']
        #fieldIndex = {}
        #for f in range(len(fields)):
        #    fieldIndex[fields[f]] = f
        fields = table_fields['nodes_log']
        fieldIndex = table_fields_index['nodes_log']

        fields_str = ', '.join(fields)

        #if get_locks:
        #    stmt = 'LOCK TABLES `nodes_history` WRITE , `nodes_log` READ'
        #    logger.debug(f'replay_log, execute: {stmt}')
       #self.cur.execute(stmt)
       # stmt = 'LOCK TABLES `nodes_log` READ'
        #    self.cur.execute(stmt)
        #self.db.commit()
        #    logger.debug(f'(replay_log) got lock')

        self.cur.execute('SET autocommit = OFF')
        self.cur.execute('START TRANSACTION')

        execute_args = []
        if replay_from_timestamp:
            # delete all entries newer than replay_from_timestamp in history

            # microseconds in the timestamp lead to wrong behaviour, because microseconds are not in mysql it seems
            replay_from_timestamp = replay_from_timestamp.replace(microsecond=0)

            stmt = f'DELETE FROM `nodes_history` WHERE `timestamp` >= %s'

            debug_stmt = stmt
            debug_stmt = debug_stmt.replace("%s", f'"{replay_from_timestamp.isoformat()}"', 1)
            execute_args = [replay_from_timestamp]
        else:
            stmt = f'DELETE FROM `nodes_history`'
            debug_stmt = stmt


        logger.debug(f'debug_stmt: {debug_stmt}')
        try:

            self.cur.execute(stmt, execute_args)

            #self.db.commit()
        except Exception as e:
            raise Exception("Deleting latest history failed:" + str(e))


        nodes_last_state = {}

        reading_cur = self.db.cursor()

        total_count = None
        if replay_from_timestamp:
            stmt = f'SELECT {fields_str} FROM `nodes_log` WHERE `effective_time` >= %s ORDER BY `effective_time`'
            #print(f'statement: {stmt}', flush=True)
            total_count = reading_cur.execute(stmt, (replay_from_timestamp,))
            debug_stmt = stmt
            debug_stmt = debug_stmt.replace("%s", f'"{replay_from_timestamp}"', 1)
            logger.debug(f'debug_stmt: {debug_stmt}')
        else:
            stmt = f'SELECT {fields_str} FROM `nodes_log` ORDER BY `effective_time`'
            logger.debug(f'statement: {stmt}')
            total_count = reading_cur.execute(stmt)


        logger.debug(f'total_count: {total_count}')
        while rows := reading_cur.fetchmany(size=100) :


            #logger.debug(f'______loop: {len(rows)}')
            for row in rows:
                logger.debug("row: "+str(row))

                #print(rows, flush=True)
                node_id = row[fieldIndex['node_id']]
                op = row[fieldIndex['operation']]
                if op != "insert":
                    #print(f"ERROR: skipping invalid operation {op}")
                    raise Exception(f"Operation {op} not supported")

                col = row[fieldIndex['field_name']]
                value = row[fieldIndex['new_value']]
                effective_time = row[fieldIndex['effective_time']]

                # first try to find node_object in cache
                node_object = nodes_last_state.get(node_id)

                # then try to find last state in history table (which might be empty)
                if not node_object:
                    node_object = self.get_node_state(node_id)

                # if not found exitsing node_state, create new one
                if not node_object:
                    node_object = {}
                    node_object['id']=node_id

                previous_timestamp = None
                if 'timestamp' in node_object:
                    previous_timestamp = node_object['timestamp']


                # insert previous state only if timestamp is different from previous one to prevent "Duplicate entry" issue in mysql
                # delaying insertion allows us to collect changes within the same timestamp and prevents "Duplicate entry"
                if previous_timestamp != None and previous_timestamp != effective_time:
                    try:
                        self.insert_object("nodes_history", node_object)
                    except Exception as e:
                        raise Exception("insert_object failed:" + str(e))


                # modfiy state (insert later!)
                node_object[col]=value
                node_object['timestamp'] = effective_time



                # put into cache:
                nodes_last_state[node_id] = node_object
                #print("end of current row", flush=True)

        # now insert the last entries of each node:
        for node_id in nodes_last_state:
            node_object = nodes_last_state[node_id]
            try:
                self.insert_object("nodes_history", node_object, commit=False)
            except Exception as e:
                        raise Exception("insert_object failed:" + str(e))

        # now all is done an we can commit
        self.db.commit()

        #if get_locks:
        #    logger.debug("(replay_log) UNLOCK TABLES")
        #    stmt = 'UNLOCK TABLES'
        #    self.cur.execute(stmt)
        #    self.db.commit()

    def get_node_state(self, node_id, timestamp=None, iso=True):
        table_name = 'nodes_history'
        fields = table_fields[table_name]
        fields_str = ", ".join(fields)

        stmt = f'SELECT {fields_str} FROM `{table_name}` WHERE `id` = %s ORDER by `timestamp` DESC LIMIT  1'
        logger.debug(f'statement: {stmt} (with node_id: {node_id})')
        self.cur.execute(stmt, (node_id,))
        row = self.cur.fetchone()
        if not row:
            return None


        result = {}
        for i in range(len(row)):
            result[fields[i]] = row[i]

        if not result:
            raise Exception("Result dict empty, should not happen")

        if iso:
            for key in ["timestamp", "registration_event", "wes_deploy_event"]:
                if key in result:
                    if result[key] != None:
                        result[key] = result[key].isoformat()


        return result

    def get_node_keypair(self, node_id):

        return self.get_node_credentials_all(node_id, "_beekeeper_")


    def set_node_keypair(self, node_id, creds):

        #creds["id"] = node_id

        #ssh_key_private = creds["ssh_key_private"]
        #ssh_key_public = creds["ssh_key_public"]
        for field in [ "ssh_key_private", "ssh_key_public"  ]:
            if not field in creds:
                raise Exception(f"Field {field} missing.")
            if not creds[field]:
                raise Exception(f"Field {field} empty.")

        count = self.set_node_credentials(node_id, "_beekeeper_", creds)

        if count != 2:
            raise Exception(f"Insertions failed")

        return

    def set_node_credentials(self, node_id, namespace, values, force=False):

        count = 0
        for field in values:
            load_obj = {"id": node_id, "namespace": namespace, "name": field, "value": values[field] }
            count += self.insert_object("node_credentials", load_obj, force=force)

        return count


    def get_node_credentials_all(self, node_id, namespace):

        stmt = f'SELECT name, value FROM `node_credentials` WHERE `id` = %s AND `namespace` = %s'
        logger.debug(f'statement: {stmt}')

        self.cur.execute(stmt, (node_id,namespace))
        rows = self.cur.fetchall()
        if not rows:
            #raise Exception("Node not found")
            return None

        return_obj = {}
        for row in rows:
            return_obj[row[0]] = row[1]

        return return_obj

    def get_node_credential(self, node_id, namespace, name):

        stmt = f'SELECT value FROM `node_credentials` WHERE `id` = %s AND `namespace` = %s AND `name` = %s'
        logger.debug(f'statement: {stmt}')

        self.cur.execute(stmt, (node_id,namespace, name))
        row = self.cur.fetchone()
        if not row:
            #raise Exception("Node not found")
            return None

        return row[0]


    def get_beehive(self, id):
        result = self.get_object("beehives", "id", id)
        if not result:
            return None

        if not isinstance(result, dict):
            raise Exception("get_object did not return a dict")


        for user_visible_field in ["tls-key", "tls-cert", "ssh-key", "ssh-pub", "ssh-cert"]:
            col_name = user_visible_field.replace("-", "_ca_")
            result[user_visible_field] = result[col_name]
            del result[col_name]

        for user_visible_field in ["key-type", "key-type-args"]:
            col_name = user_visible_field.replace("-", "_")
            result[user_visible_field] = result[col_name]
            del result[col_name]



        return result




    def list_latest_state(self):
        table_name = 'nodes_history'
        fields = table_fields[table_name]
        fields_str = ", ".join(fields)

        stmt = f'''
            SELECT {fields_str}
            FROM {table_name} t1
            WHERE t1.timestamp = (SELECT MAX(t2.timestamp)
                               FROM {table_name} t2
                               WHERE t2.id = t1.id)
        '''

        logger.debug("statement: %r", stmt)
        self.cur.execute(stmt)

        # create list of dicts
        results = []
        for row in self.cur.fetchall():
            results.append(dict(zip(fields, row)))

        for node in results:
            for key in ["timestamp", "registration_event", "wes_deploy_event"]:
                if key in node:
                    if node[key] != None:
                        node[key] = node[key].isoformat()

        return results


    def update_object_field(self, table_name, column, value, filter_key, filter_value):

        stmt = f"UPDATE {table_name} SET {column} = %s WHERE {filter_key} = %s"
        values = (value, filter_value,)
        debug_stmt = stmt
        for i in values:
            debug_stmt = debug_stmt.replace("%s", f'"{i}"', 1)
        logger.debug(f'(update_object_field) statement: {debug_stmt}')

        self.cur.execute(stmt, (*values, ))
        self.db.commit()
        return self.cur.rowcount

    # updates is a dict {column: value}
    def update_object_fields(self, table_name, updates, filter_key, filter_value):

        setter = []
        values = []
        for key in updates:
            setter.append(f"{key} = %s ")
            #logger.debug(f"pair: {key} {updates[key]}")
            values.append(updates[key])

        setter_str = ", ".join(setter)
        #logger.debug(f"setter_str: {setter_str}")

        stmt = f"UPDATE {table_name} SET {setter_str} WHERE {filter_key} = %s"
        values.append(filter_value)
        debug_stmt = stmt
        for i in values:
            debug_stmt = debug_stmt.replace("%s", f'"{i}"', 1)
        logger.debug(f'(update_object_fields) statement: {debug_stmt}')

        self.cur.execute(stmt, (*values, ))
        self.db.commit()

        return self.cur.rowcount

    def get_object(self, table_name, key, value):

        fields = table_fields['beehives']
        fields_str = ", ".join(fields)

        stmt = f'SELECT {fields_str} FROM `{table_name}` WHERE `{key}` = %s'
        logger.debug(f'statement: {stmt}')

        self.cur.execute(stmt, (value,))
        row = self.cur.fetchone()
        if not row:
            #raise Exception("Node not found")
            return None



        return dict(zip(fields, row))

    def get_objects(self, table_name, fields=None):
        if not fields:
            fields = table_fields['beehives']

        fields_str = ", ".join(fields)

        stmt = f'SELECT {fields_str} FROM `{table_name}`'
        logger.debug(f'statement: {stmt}')

        self.cur.execute(stmt)
        rows = self.cur.fetchall()

        result = []
        for row in rows:
            result.append(dict(zip(fields, row)))

        return result


    def insert_object(self, table_name, row_object, force=False, commit=True):
        fields_str , values, replacement_str = self.dict2mysql(row_object)

        stmt = f'INSERT INTO {table_name} ({fields_str}) VALUES ({replacement_str})'
        if force:
            stmt = f'INSERT INTO {table_name} ({fields_str}) VALUES ({replacement_str}) ON DUPLICATE KEY UPDATE '
            for key in row_object:
                stmt += f" {key}=%s,"
                values.append(row_object[key])
            stmt = stmt[:-1] # remove last comma

        debug_stmt = stmt
        for i in values:
            debug_stmt = debug_stmt.replace("%s", f'"{i}"', 1)



        logger.debug("debug_stmt: %r", stmt)
        self.cur.execute(stmt, (*values, ))
        if commit:
            self.db.commit()

        if (not force) and self.cur.rowcount != 1:
            raise Exception(f"insertion went wrong (self.cur.rowcount: {self.cur.rowcount})")

        return self.cur.rowcount

    # simple delete based on WHERE KEY=VALUE
    def delete_object(self, table_name, key, value):

        stmt = f"DELETE FROM `{table_name}` WHERE {key} = %s ;"

        debug_stmt = stmt.replace("%s", f"'{value}'", 1)

        logger.debug(f'debug_stmt: {debug_stmt}')
        try:
            self.cur.execute(stmt, (value,))
            self.db.commit()
        except Exception as e:
            raise Exception(f"Error deleting object: {str(e)}")

        return self.cur.rowcount

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
        logger.debug(f'statement: {stmt}')
        self.cur.execute(stmt)
