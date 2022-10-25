import subprocess
from bk_api import create_app
from bk_db import BeekeeperDB
import datetime
import pytest
import json
import io
from http import HTTPStatus
import re
import os
from contextlib import closing


@pytest.fixture
def app():
    # TODO(sean) This is a hack to prevent accidentally wiping the production tables if someone accidentally. We
    # should move to a dedicated TestBeekeeper database instead.
    if os.getenv("TESTING") != "1":
        raise RuntimeError("Bailing out on running tests as they wipe the database! If you are not running in production and are sure you want to proceed, you must set the env var TESTING=1.")

    # TODO(sean) It would be nice to setup a fresh database here, so different unit tests can't affect each other.
    # For example, we could generate some BeekeeperTestRandomID database and init the tables.
    app = create_app()
    truncate_all_tables()
    yield app


def truncate_all_tables():
    with closing(BeekeeperDB()) as db:
        for table_name in ["nodes_log", "nodes_history", "beehives"]:
            db.truncate_table(table_name)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


# TODO(sean) setup ability to decouple node ssh from testing. we just want to enforce the contract here.


def test_root(client):
    rv = client.get('/')
    assert b'SAGE Beekeeper API' in rv.data


def test_registration(client):
    # fuzz test registration
    for _ in range(10):
        node_id = rand_node_id()

        r = client.post(f'/register?node_id={node_id}')
        assert r.status_code == HTTPStatus.OK
        result = r.get_json()
        # NOTE(sean) I'm assuming we're using ed25519 just to keep the expected output slim. If we allow multiple key types, we'll need to update this.
        assert re.match(r"-----BEGIN OPENSSH PRIVATE KEY-----(.|\n)+-----END OPENSSH PRIVATE KEY-----", result["private_key"])
        assert re.match(r"ssh-ed25519 \S+", result["public_key"])
        assert re.match(r"ssh-ed25519-cert-v01@openssh.com \S+", result["certificate"])

        # Do it twice to make sure the code for the cached version is included
        r = client.post(f'/register?node_id={node_id}')
        assert r.status_code == HTTPStatus.OK
        result2 = r.get_json()
        assert result["private_key"] == result2["private_key"]
        assert result["public_key"] == result2["public_key"]

        r = client.get(f'/credentials/{node_id}')
        result = r.get_json()
        assert re.match(r"-----BEGIN OPENSSH PRIVATE KEY-----(.|\n)+-----END OPENSSH PRIVATE KEY-----", result["ssh_key_private"])
        assert re.match(r"ssh-ed25519 \S+", result["ssh_key_public"])


def test_registration_missing_node_id(client):
    r = client.post('/register')
    assert r.status_code == HTTPStatus.BAD_REQUEST


def test_registration_invalid_node_id(client):
    for node_id in ["SHORT", "NOLOwERCASE", "AVOIDUSING_", "AREALLYREALLYREALLYLONGNODEIDTHATISNOTALLOWED"]:
        r = client.post(f'/register?node_id={node_id}')
        assert r.status_code == HTTPStatus.BAD_REQUEST


def test_registration_get_not_allowed(client):
    node_id = rand_node_id()
    beehive_id = rand_beehive_id()
    r = client.get(f'/register?node_id={node_id}&beehive_id={beehive_id}')
    assert r.status_code == HTTPStatus.METHOD_NOT_ALLOWED


def test_registration_with_specific_beehive(client):
    node_id = rand_node_id()
    beehive_id = rand_beehive_id()

    r = client.post('/beehives', data=json.dumps({"id": beehive_id, "key-type":"rsa-sha2-256"}))

    r = client.post(f'/register?node_id={node_id}&beehive_id={beehive_id}')
    assert r.status_code == HTTPStatus.OK

    r = client.get(f'/state/{node_id}')
    assert r.status_code == HTTPStatus.OK
    data = r.get_json()["data"]
    assert data["beehive"] == beehive_id

    # TODO(sean) This behavior test is somewhat incomplete as it never confirms whether
    # the credentials match the specified beehive's. (We will catch this during integration
    # testing for now, though.)


def test_registration_with_nonexistant_beehive(client):
    r = client.post(f'/register?node_id=NODE123&beehive_id=nonexistant-beehive')
    assert r.status_code == HTTPStatus.NOT_FOUND


def test_assign_node_to_beehive(client):
    # TODO(sean) Would be nice if this were generalized to a random node ID, but this is hard as it requires
    # deploying WES. If we plan on exercising that with an integration test, then we might simplify what this
    # unit test is actually checking.
    node_id = f"0000000000000001"
    beehive_id = rand_beehive_id()

    # create new node
    r = client.post(f'/register?node_id={node_id}')
    assert r.status_code == HTTPStatus.OK

    # create new beehive
    r = client.post('/beehives', data = json.dumps({"id": beehive_id, "key-type":"rsa-sha2-256"}))
    result = r.get_json()
    assert "modified" in result
    assert result["modified"] > 0

    rv = client.get('/beehives')
    result = rv.get_json()
    assert "data" in result
    assert len(result["data"]) > 0

    # upload beehive certs
    data = {
        "tls-key": (open("/test-data/beehive_ca/tls/cakey.pem", "rb"), "dummmy"),
        'tls-cert': (open("/test-data/beehive_ca/tls/cacert.pem", "rb"), "dummmy"),
        'ssh-key': (open("/test-data/beehive_ca/ssh/ca", "rb"), "dummmy"),
        'ssh-pub': (open("/test-data/beehive_ca/ssh/ca.pub", "rb"), "dummmy"),
        'ssh-cert': (open("/test-data/beehive_ca/ssh/ca-cert.pub", "rb"), "dummmy")
    }
    rv = client.post(f'/beehives/{beehive_id}', content_type='multipart/form-data', data=data)
    result = rv.get_json()
    assert "modified" in result

    # assign node
    rv = client.post(f'/node/{node_id}', data = json.dumps({"assign_beehive": beehive_id, "deploy_wes": True}))
    result = rv.get_json()
    assert "success" in result

    # assign node with force
    rv = client.post(f'/node/{node_id}?force=true', data = json.dumps({"assign_beehive": beehive_id, "deploy_wes": True}))
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


def test_vsn_insert_contract(client):
    """
    Tests the underlying SSH communication contract with a node during add VSN trigger.

    NOTE The expected VSN comes from docker-compose WAGGLE_NODE_VSN environment variable.
    """
    node_id = "0000000000000001"

    # assume node has registered
    r = client.post(f"/register?node_id={node_id}")
    assert r.status_code == HTTPStatus.OK

    # check initial value is null
    r = client.get(f'/state/{node_id}')
    resp = must_get_valid_json_response(r)
    assert resp["data"]["vsn"] == None

    # call add vsn trigger endpoint
    r = client.post(f'/node/{node_id}', data=json.dumps({"vsn": True}))
    assert r.status_code == HTTPStatus.OK
    assert r.get_json() == {"success": True}

    # check that response matches expected vsn
    r = client.get(f'/state/{node_id}')
    resp = must_get_valid_json_response(r)
    assert resp["data"]["vsn"] == "V001"


def test_vsn_insert_success(app, client):
    """
    Tests add VSN success behavior.
    """
    app.node_subprocess_proxy_factory = MockNodeSubprocessProxy.make_factory([
        (["cat", "/etc/waggle/vsn"], 0, "V001"),
    ])

    node_id = "0000000000000001"

    # assume node has registered
    r = client.post(f"/register?node_id={node_id}")
    assert r.status_code == HTTPStatus.OK

    # test initial value is null
    r = client.get(f'/state/{node_id}')
    assert r.status_code == HTTPStatus.OK
    resp = must_get_valid_json_response(r)
    assert resp["data"]["vsn"] == None

    # test insert vsn endpoint
    r = client.post(f'/node/{node_id}', data=json.dumps({"vsn": True}))
    assert r.get_json() == {"success": True}

    # check that response matches expected vsn
    r = client.get(f'/state/{node_id}')
    resp = must_get_valid_json_response(r)
    assert resp["data"]["vsn"] == "V001"


def test_add_vsn_proxy_error(app, client):
    """
    Tests add vsn behavior when proxy commands fail.
    """
    app.node_subprocess_proxy_factory = MockNodeSubprocessProxy.make_factory([
        (["cat", "/etc/waggle/vsn"], 1, "V123"),
    ])

    node_id = "0000000000000001"

    # assume node has registered
    r = client.post(f"/register?node_id={node_id}")
    assert r.status_code == HTTPStatus.OK

    # test insert vsn endpoint
    data = {"vsn": True}
    r = client.post(f'/node/{node_id}', data=json.dumps(data))
    assert r.status_code == HTTPStatus.INTERNAL_SERVER_ERROR

    # ensure state has not changed on failure
    r = client.get(f'/state/{node_id}')
    resp = must_get_valid_json_response(r)
    assert resp["data"]["vsn"] is None


def test_add_vsn_validation(app, client):
    """
    Tests add VSN validation checks.
    """
    node_id = "0000000000000001"

    # assume node has registered
    r = client.post(f"/register?node_id={node_id}")
    assert r.status_code == HTTPStatus.OK

    for testvalue in ["", "V01", "V 123", "v001", "2x13", "V1234"]:
        app.node_subprocess_proxy_factory = MockNodeSubprocessProxy.make_factory([
            (["cat", "/etc/waggle/vsn"], 0, testvalue),
        ])

        # trigger add vsn
        data = {"vsn": True}
        r = client.post(f'/node/{node_id}', data=json.dumps(data))
        assert r.status_code == HTTPStatus.INTERNAL_SERVER_ERROR

        # ensure state has not changed on failure
        r = client.get(f'/state/{node_id}')
        resp = must_get_valid_json_response(r)
        assert resp["data"]["vsn"] is None


# TODO test full replay without timestamp
def test_log_insert(client):
    # TODO(sean) Can we use a public endpoint which exercises this rather than test the internals?

    test_data = get_test_data()
    data = test_data['data']
    test_time = test_data['test_time']

    rv = client.post('/log', data = json.dumps(data))

    result = rv.get_json()
    assert 'error' not in result
    assert 'success' in result

    rv = client.get(f'/state/123')

    result = rv.get_json()
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
        'registration_event': (test_time - datetime.timedelta(days= 5)).isoformat(),
        'vsn': None,
        'wes_deploy_event': None
    }



def test_list_recent_state(client):
    # TODO(sean) Can we use a public endpoint which exercises this rather than test the internals?

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
    assert rv.status_code != HTTPStatus.OK

    rv = client.post('/credentials/cred-test', data = json.dumps({"ssh_key_private":"x", "ssh_key_public":"y"}))
    assert rv.status_code == HTTPStatus.OK


    rv = client.get('/credentials/cred-test')
    result = rv.get_json()
    assert "ssh_key_private" in result
    assert "ssh_key_public" in result

    assert result["ssh_key_private"] == "x"
    assert result["ssh_key_public"] == "y"

    # clean-up
    rv = client.delete('/credentials/cred-test')
    assert rv.status_code == HTTPStatus.OK
    result = rv.get_json()
    assert "deleted" in result
    assert result["deleted"] == 2


def test_beehives(client):
    rv = client.delete('/beehives/test-beehive')
    result = rv.get_json()
    assert "deleted" in result  # 0 or 1, either is fine here

    rv = client.post('/beehives', data = json.dumps({"id": "test-beehive", "key-type": "rsa-sha2-256"}))
    result = rv.get_json()
    assert "modified" in result

    assert result["modified"] > 0

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
    assert b'error' in rv.data



def must_get_valid_json_response(r):
    assert r.status_code == HTTPStatus.OK
    resp = r.get_json()
    assert "error" not in resp
    assert "data" in resp
    return resp


def rand_node_id():
    return rand_string(6, 16, "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")


def rand_beehive_id():
    return rand_string(3, 64, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")


def rand_string(min_length, max_length, characters):
    from random import randint
    from random import choice
    length = randint(min_length, max_length)
    return "".join(choice(characters) for _ in range(length))


class MockNodeSubprocessProxy:
    """
    MockNodeSubprocessProxy provides a mock for the check_call and check_output node subprocess proxy methods.
    """

    @classmethod
    def make_factory(cls, return_values):
        from functools import partial
        return partial(MockNodeSubprocessProxy, return_values=return_values)

    def __init__(self, node_id, return_values=[]):
        self.node_id = node_id
        self.return_values = {tuple(cmd): (returncode, output) for cmd, returncode, output in return_values}

    def check_output(self, cmd, *args, **kwargs):
        returncode, output = self.return_values[tuple(cmd)]
        if returncode != 0:
            raise subprocess.CalledProcessError(returncode=returncode, cmd=cmd, output=output)
        return output

    def check_call(self, cmd, *args, **kwargs):
        self.check_output(cmd, *args, **kwargs)
