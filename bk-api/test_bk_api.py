import bk_api
import datetime
import tempfile
import pytest
import os

import json


# from https://flask.palletsprojects.com/en/1.1.x/testing/
@pytest.fixture
def client():
    app = bk_api.app
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


def get_test_data():
    data = []
    test_time = datetime.datetime.now().replace(microsecond=0)

    data.append({"node_id": "123", "source": "testing", "operation":"insert", "field_name": "name", "field_value": "Rumpelstilzchen", "effective_time": (test_time -datetime.timedelta(days= 1)).isoformat()})
    data.append({"node_id": "123", "source": "testing", "operation":"insert", "field_name": "project_id", "field_value": "project_X", "effective_time": (test_time -datetime.timedelta(days= 2)).isoformat()})
    for i in range(1, 100):
        data.append({"node_id": "123", "source": "testing", "operation":"insert", "field_name": "project_id", "field_value": "project_X", "effective_time": (test_time -datetime.timedelta(days=2, minutes = i)).isoformat()})
    data.append({"node_id": "123", "source": "testing", "operation":"insert", "field_name": "mode", "field_value": "active", "effective_time": (test_time -datetime.timedelta(days= 2)).isoformat()})
    data.append({"node_id": "123", "source": "testing", "operation":"insert", "field_name": "mode", "field_value": "failed", "effective_time": (test_time -datetime.timedelta(days= 3)).isoformat()})
    data.append({"node_id": "789", "source": "testing", "operation":"insert", "field_name": "mode", "field_value": "active", "effective_time": (test_time -datetime.timedelta(days= 3)).isoformat()})
    data.append({"node_id": "123", "source": "testing", "operation":"insert", "field_name": "name", "field_value": "Rumpelstilzchen2", "effective_time": (test_time -datetime.timedelta(days= 4)).isoformat()})
    data.append({"node_id": "123", "source": "testing", "operation":"insert", "field_name": "registration_event", "field_value": (test_time -datetime.timedelta(days= 5)).isoformat(), "effective_time": (test_time -datetime.timedelta(days= 5)).isoformat()})
    data.append({"node_id": "789", "source": "testing", "operation":"insert", "field_name": "registration_event", "field_value": (test_time -datetime.timedelta(days= 5)).isoformat(), "effective_time": (test_time -datetime.timedelta(days= 5)).isoformat()})

    return {'test_time': test_time, 'data': data}



# TODO test full replay without timestamp
def test_log_insert(client):
    bee_db = bk_api.BeekeeperDB()
    bee_db.truncate_table("nodes_log")
    bee_db.truncate_table("nodes_history")

    test_data = get_test_data()
    data = test_data['data']
    test_time = test_data['test_time']

    rv = client.post('/log', data = json.dumps(data))

    result = rv.get_json()
    assert 'error' not in result
    assert 'success' in result

    rv = client.get(f'/state/123')

    result = rv.get_json()
    print(result)
    assert 'error' not in result
    assert 'data' in result

    d = result["data"]
    assert d == {
        'address': None,
        'altitude': None,
        'beehive': None,
        'id': '123',
        'internet_connection': None,
        'mode': 'active',
        'name': 'Rumpelstilzchen',
        'position': None,
        'project_id': 'project_X',
        'server_node': None,
        'timestamp': (test_time - datetime.timedelta(days= 1)).isoformat(),
        'registration_event': (test_time - datetime.timedelta(days= 5)).isoformat()
    }



def test_list_recent_state(client):
    bee_db = bk_api.BeekeeperDB()
    bee_db.truncate_table("nodes_log")
    bee_db.truncate_table("nodes_history")

    test_data = get_test_data()
    data = test_data['data']
    test_time = test_data['test_time']

    # update data
    rv = client.post('/log', data = json.dumps(data))
    result = rv.get_json()
    assert 'error' not in result
    assert 'success' in result

    # fetch state
    rv = client.get(f'/state')
    result = rv.get_json()
    assert 'error' not in result
    assert 'data' in result

    # basic checks on data structure / ids
    d = result["data"]
    assert len(d) == 2
    assert d[0]['id'] == '123'
    assert d[1]['id'] == '789'

    # test a mode change
    new_state = [{
        'node_id': '123',
        'source': 'testing',
        'operation': 'insert',
        'field_name': 'mode',
        'field_value': 'failed',
        'effective_time': (test_time - datetime.timedelta(days = 1)).isoformat()
    }]
    rv = client.post('/log', data = json.dumps(new_state))
    rv = client.get(f'/state')

    result = rv.get_json()
    assert 'error' not in result
    assert 'data' in result
    d = result["data"]

    assert d[0]['id'] == '123'
    assert d[0]['mode'] == 'failed'




def test_error(client):
    rv = client.get(f'/state/foobar')

    result = rv.get_json()
    print(result)
    assert b'error' in rv.data
