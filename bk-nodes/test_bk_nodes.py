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
    test_time = datetime.datetime.now().replace(microsecond=0)
    
    test_data.append({"node_id": "123", "source": "testing", "operation":"insert", "field_name": "name", "field_value": "Rumpelstilzchen", "effective_time": (test_time -datetime.timedelta(days= 1)).isoformat()})
    test_data.append({"node_id": "123", "source": "testing", "operation":"insert", "field_name": "project_id", "field_value": "project_X", "effective_time": (test_time -datetime.timedelta(days= 2)).isoformat()})
    for i in range(1, 100):
        test_data.append({"node_id": "123", "source": "testing", "operation":"insert", "field_name": "project_id", "field_value": "project_X", "effective_time": (test_time -datetime.timedelta(days=2, minutes = i)).isoformat()})
    test_data.append({"node_id": "123", "source": "testing", "operation":"insert", "field_name": "mode", "field_value": "active", "effective_time": (test_time -datetime.timedelta(days= 3)).isoformat()})
    test_data.append({"node_id": "789", "source": "testing", "operation":"insert", "field_name": "mode", "field_value": "active", "effective_time": (test_time -datetime.timedelta(days= 3)).isoformat()})
    test_data.append({"node_id": "123", "source": "testing", "operation":"insert", "field_name": "name", "field_value": "Rumpelstilzchen2", "effective_time": (test_time -datetime.timedelta(days= 4)).isoformat()})
    test_data.append({"node_id": "123", "source": "testing", "operation":"insert", "field_name": "registration_event", "field_value": (test_time -datetime.timedelta(days= 5)).isoformat(), "effective_time": (test_time -datetime.timedelta(days= 5)).isoformat()})
    test_data.append({"node_id": "789", "source": "testing", "operation":"insert", "field_name": "registration_event", "field_value": (test_time -datetime.timedelta(days= 5)).isoformat(), "effective_time": (test_time -datetime.timedelta(days= 5)).isoformat()})


    rv = client.post('/log', data = json.dumps(test_data))
    
    result = rv.get_json()
    assert 'error' not in result
    assert 'success' in result
    


    rv = client.get(f'/state/123')
    
    result = rv.get_json()
    print(result)
    assert 'error' not in result
    assert 'data' in result
    d =  result["data"]

    assert d ==  {
        'address': None, 
        'altitude': None, 
        'id': '123', 
        'internet_connection': None, 
        'mode': 'active', 
        'name': 'Rumpelstilzchen', 
        'position': None, 
        'project_id': 'project_X', 
        'server_node': None, 
        'timestamp': (test_time -datetime.timedelta(days= 1)).isoformat(), 
        'registration_event': (test_time -datetime.timedelta(days= 5)).isoformat()}




def test_error(client):
    rv = client.get(f'/state/foobar')
    
    result = rv.get_json()
    print(result)
    assert b'error' in rv.data
