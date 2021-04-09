import bk_api
import datetime
import tempfile
import pytest
import os

import json
import io

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
    assert b'SAGE Beekeeper API' in rv.data

def test_registration(client):

    # Do it twice to make sure the code for the cached version is included
    rv = client.get('/register?id=foobar')
    assert rv.status_code == 200
    result = rv.get_json()
    assert 'certificate'  in result

    rv = client.get('/register?id=foobar')
    assert rv.status_code == 200
    result = rv.get_json()
    assert 'certificate'  in result


    rv = client.get('/credentials/foobar')
    result = rv.get_json()
    assert "ssh_key_private" in result
    assert "ssh_key_public" in result


def test_assign_node_to_beehive(client):

    # create new beehive
    rv = client.delete('/beehives/test-beehive2')
    result = rv.get_json()
    assert "deleted" in result  # 0 or 1, either is fine here

    rv = client.post('/beehives', data = json.dumps({"id": "test-beehive2", "key-type":"rsa-sha2-256"}))
    result = rv.get_json()
    assert "success" in result

    # upload beehive certs
    #data = {
    #    "tls-key": (io.BytesIO(b'a'), "dummmy"),
    #    'tls-cert': (io.BytesIO(b'b'), "dummmy"),
    #    'ssh-key': (io.BytesIO(b'c'), "dummmy"),
    #    'ssh-pub': (io.BytesIO(b'd'), "dummmy"),
    #    'ssh-cert': (io.BytesIO(b'e'), "dummmy")
    #}
    data = {
        "tls-key": (open("/test-data/beehive_ca/tls/cakey.pem", "rb"), "dummmy"),
        'tls-cert': (open("/test-data/beehive_ca/tls/cacert.pem", "rb"), "dummmy"),
        'ssh-key': (open("/test-data/beehive_ca/ssh/ca", "rb"), "dummmy"),
        'ssh-pub': (open("/test-data/beehive_ca/ssh/ca.pub", "rb"), "dummmy"),
        'ssh-cert': (open("/test-data/beehive_ca/ssh/ca-cert.pub", "rb"), "dummmy")
    }
    rv = client.post('/beehives/test-beehive2', content_type='multipart/form-data', data=data)
    result = rv.get_json()
    assert "modified" in result

    #register node
    rv = client.get('/register?id=testnode2')
    assert rv.status_code == 200
    result = rv.get_json()
    assert 'certificate'  in result


    #assign node
    rv = client.post('/node/testnode2', data = json.dumps({"assign_beehive": "test-beehive2"}))
    result = rv.get_json()
    assert "success" in result








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

def test_log_insert_fail(client):

    rv = client.post('/log', data = "foobar")

    result = rv.get_json()
    assert 'error'  in result



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

def test_credentials(client):


    rv = client.post('/credentials/dummy', data = "test")

    assert rv.status_code != 200

    rv = client.post('/credentials/cred-test', data = json.dumps({"ssh_key_private":"x", "ssh_key_public":"y"}))

    assert rv.status_code == 200


    rv = client.get('/credentials/cred-test')
    result = rv.get_json()
    assert "ssh_key_private" in result
    assert "ssh_key_public" in result

    assert result["ssh_key_private"] == "x"
    assert result["ssh_key_public"] == "y"

    # clean-up
    rv = client.delete('/credentials/cred-test')
    assert rv.status_code == 200
    result = rv.get_json()
    assert "deleted" in result
    assert result["deleted"] == 2


def test_beehives(client):

    rv = client.delete('/beehives/test-beehive')
    result = rv.get_json()
    assert "deleted" in result  # 0 or 1, either is fine here

    rv = client.post('/beehives', data = json.dumps({"id": "test-beehive", "key-type": "rsa-sha2-256"}))
    result = rv.get_json()
    assert "success" in result

    # TODO form upload does not work here
    #data = {"tls-key": (None, "a"), 'tls-cert': (None ,'b'), 'ssh-key': (None, 'c'), 'ssh-pub': (None, 'd'), 'ssh-cert': (None, 'e')}

    data = {
        "tls-key": (io.BytesIO(b'a'), "dummmy"),
        'tls-cert': (io.BytesIO(b'b'), "dummmy"),
        'ssh-key': (io.BytesIO(b'c'), "dummmy"),
        'ssh-pub': (io.BytesIO(b'd'), "dummmy"),
        'ssh-cert': (io.BytesIO(b'e'), "dummmy")
    }
    rv = client.post('/beehives/test-beehive', content_type='multipart/form-data', data=data)
    result = rv.get_json()
    assert "modified" in result

    rv = client.get('/beehives/test-beehive')
    result = rv.get_json()
    assert "id" in result  # 0 or 1, either is fine here
    assert result["id"] == "test-beehive"
    assert result["tls-key"] == "a"
    assert result["ssh-cert"] == "e"

def test_error(client):
    rv = client.get(f'/state/foobar')

    result = rv.get_json()
    print(result)
    assert b'error' in rv.data
