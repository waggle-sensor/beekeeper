import bk_nodes
import datetime
import tempfile
import pytest
import os

import json


# from https://flask.palletsprojects.com/en/1.1.x/testing/
@pytest.fixture
def client():
    app = bk_nodes.app
    db_fd, app.config['DATABASE'] = tempfile.mkstemp()
    app.config['TESTING'] = True

    with app.test_client() as client:
        #with app.app_context():
        #    init_db()
        yield client

    os.close(db_fd)
    os.unlink(app.config['DATABASE'])


def test_root(client):
    rv = client.get('/')
    assert b'SAGE Beekeeper' in rv.data


def test_log_insert(client):
    bee_db = bk_nodes.BeekeeperDB()
    bee_db.truncate_table("nodes_log")
    bee_db.truncate_table("nodes_history")

    test_data = []
    test_time = datetime.datetime.now()
    
    test_data.append({"node_id": "123", "source": "testing", "operation":"insert", "field_name": "name", "field_value": "Rumpelstilzchen", "effective_time": str(test_time -datetime.timedelta(days= 1))})
    test_data.append({"node_id": "123", "source": "testing", "operation":"insert", "field_name": "project_id", "field_value": "project_X", "effective_time": str(test_time -datetime.timedelta(days= 2))})
    test_data.append({"node_id": "123", "source": "testing", "operation":"insert", "field_name": "mode", "field_value": "active", "effective_time": str(test_time -datetime.timedelta(days= 3))})
    test_data.append({"node_id": "123", "source": "testing", "operation":"insert", "field_name": "name", "field_value": "Rumpelstilzchen2", "effective_time": str(test_time -datetime.timedelta(days= 4))})

    rv = client.post('/log', data = json.dumps(test_data))
    
    result = rv.get_json()
    assert 'error' not in result
    assert 'success' in result
    






