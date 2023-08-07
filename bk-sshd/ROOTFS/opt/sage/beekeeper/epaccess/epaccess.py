#!/usr/bin/env python3
"""
Defines API interface to add / delete users from the Linux system.

ANL:waggle-license
 This file is part of the Waggle Platform.  Please see the file
 LICENSE.waggle.txt for the legal details of the copyright and software
 license.  For more details on the Waggle project, visit:
          http://www.wa8.gl
ANL:waggle-license
"""

import flask
import grp
import logging
import os
import pwd
import subprocess as sp
import stat
import sys
import time
import requests
import json
from os.path import exists

formatter = logging.Formatter(
    "%(asctime)s  [%(name)s:%(lineno)d] (%(levelname)s): %(message)s"
)
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

USER_HOME_DIR = "/home_dirs"

BEEKEEPER_DB_API = os.getenv("BEEKEEPER_DB_API", "http://bk-api:5000")


def setup_app():
    while True:
        try:
            bk_api_result = requests.get(f"{BEEKEEPER_DB_API}", timeout=3).content
        except Exception as e:
            logger.warning(
                f"Error: Beekeeper DB API ({BEEKEEPER_DB_API}) cannot be reached, requests.get returned: {str(e)}"
            )
            time.sleep(2)
            continue

        # print(bk_api_result)
        result_message = bk_api_result.decode(
            "utf-8"
        ).strip()  # bk_api_result.decode("utf-8").strip()
        expected_response = "SAGE Beekeeper API"
        if expected_response != result_message:
            logger.warning(
                f'Error: Beekeeper DB API ({BEEKEEPER_DB_API}) cannot be reached: "{result_message}", expected  "{expected_response}"'
            )
            time.sleep(2)
            continue

        break

    logger.debug(
        "Getting list of nodes from beekeeper DB to create home directories and users"
    )

    try:
        bk_api_response = requests.get(f"{BEEKEEPER_DB_API}/state", timeout=3)
    except Exception as e:
        logger.Error(
            f"Beekeeper DB API ({BEEKEEPER_DB_API}/state) cannot be reached: {str(e)}"
        )
        sys.exit(1)

    if bk_api_response.status_code != 200:
        # logger.error("Could not get list of nodes")
        sys.exit("Could not get list of nodes")

    json_str = (bk_api_response.content).decode("utf-8")
    node_list = json.loads(json_str)
    node_list = node_list["data"]

    logger.debug(f"Got {len(node_list)} nodes.")

    for node_object in node_list:
        if "id" not in node_object:
            logger.error("Field id missing")
            continue

        node_id = node_object["id"]
        logger.debug(f"Adding node {node_id}.")

        user = f"node-{node_id}"

        _add_user(user)

    run_membership_script()

    return


def run_membership_script():
    # entrypoints for this function are the API (addUser) and start of the container

    membership_script = "/entrypoint-config/run.sh"
    if exists(membership_script):
        cmd = [membership_script]
        result = sp.run(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
        if result.returncode == 0:
            logger.info(f"{membership_script} run successfully")
        else:
            logger.error(f"{membership_script} had an error")
        # ignore output for now
    return


def _user_exists(user):
    """Test if the user `user` exists in the system

    Arguments:
        user (str): the user to test for existance

    Returns:
        bool: True if the user exists; False otherwise
    """
    cmd = ["id", "-u", user]
    result = sp.run(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
    return result.returncode == 0


def _add_user(user):
    """Add the user `user` to the system

    Arguments:
        user (str): the user to add

    Returns:
        None; Exception on failure
    """
    logger.debug("Adding user [{}] to system".format(user))

    if _user_exists(user):
        logger.debug("- user [{}] already exists, skipping".format(user))
        return

    cmd = [
        "useradd",
        "--create-home",
        "--system",
        "--base-dir",
        USER_HOME_DIR,
        "--password",
        user,
        user,
    ]
    result = sp.run(cmd, stdout=sp.PIPE, stderr=sp.PIPE)

    if result.returncode == 0:
        logger.debug("- user [{}] add: success".format(user))
        return

    logger.error("- user [{}] add: fail".format(user))
    # raise exception
    result.check_returncode()


def _save_keys(user, private_key=None, public_key=None, certificate=None):
    """Save keys and/or certificate to the `user` home directory

    Arguments:
        user (str): the user to add the keys / certificate
        private_key (str): private key to save to "id_rsa-tunnel"
        public_key (str): public key to save to "id_rsa-tunnel.pub"
        certificate (str): certificate to save to "id_rsa-tunnel-cert.pub"

    Returns:
        None
    """
    logger.debug("Saving user [{}] credentials".format(user))

    uid = pwd.getpwnam(user).pw_uid
    gid = grp.getgrnam(user).gr_gid

    if private_key:
        logger.debug("- saving private key")
        path = os.path.join(USER_HOME_DIR, user, "id_rsa-tunnel")
        with open(path, "w+") as f:
            f.write(private_key)
        os.chown(path, uid, gid)
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)

    if public_key:
        logger.debug("- saving public key")
        path = os.path.join(USER_HOME_DIR, user, "id_rsa-tunnel.pub")
        with open(path, "w+") as f:
            f.write(public_key)
        os.chown(path, uid, gid)
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

    if certificate:
        logger.debug("- saving certificate")
        path = os.path.join(USER_HOME_DIR, user, "id_rsa-tunnel-cert.pub")
        with open(path, "w+") as f:
            f.write(certificate)
        os.chown(path, uid, gid)
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)


def _del_user(user):
    """Delete the user `user` from the system

    Arguments:
        user (str): the user to delete from the system

    Returns:
        None; Exception on failure
    """
    logger.debug("Deleting user [{}] from system".format(user))

    if not _user_exists(user):
        logger.debug("- user [{}] does not exists, skipping".format(user))
    else:
        cmd = ["deluser", "--remove-home", user]
        result = sp.run(cmd, stdout=sp.PIPE, stderr=sp.PIPE)

        if result.returncode == 0:
            logger.debug("- user [{}] delete: success".format(user))
        else:
            logger.error("- user [{}] delete: fail".format(user))
            # raise exception
            result.check_returncode()


setup_app()

app = flask.Flask(__name__)


@app.route("/deluser", methods=["POST"])
def deluser():
    """API to delete the user `user` from the system

    Arguments:
        user (str): the user to delete from the system

    Returns:
        str: human-readable string; includes HTML error code 500 on failure
    """
    user = flask.request.values.get("id")
    logger.info("Delete user [{}]".format(user))

    try:
        _del_user(user)
    except Exception as e:
        logger.error(e)
        return "Error: unable to delete user [{}]".format(user), 500

    return "User [{}] deleted".format(user)


@app.route("/adduser", methods=["POST"])
def adduser():
    """API to add the user `user` to the system

    Arguments:
        user (str): the user to add to the system

    Returns:
        str: human-readable string; includes HTML error code 500 on failure
    """
    user = flask.request.values.get("id")
    logger.info("Add user [{}]".format(user))

    try:
        _add_user(user)
    except Exception as e:
        logger.error(e)
        return "Error: unable to add user [{}]".format(user), 500

    run_membership_script()

    # try:
    # save the user's keys
    #    priv_key = flask.request.values.get("private_key")
    #    pub_key = flask.request.values.get("public_key")
    #    cert = flask.request.values.get("certificate")
    # except Exception as e:
    #    logger.error(f"could not get data: {str(e)}")
    #    return f"Warning: Unable to save user [{user}] keys -- ({str(e)})", 500

    # try:

    #    _save_keys(user, private_key=priv_key, public_key=pub_key, certificate=cert)
    # except Exception as e:
    # raise Exception("Could not save keys: "+str(e))
    #    logger.warning("Warning: Unable to save user [{}] keys".format(user))
    #    logger.error(f"_save_keys returned: {str(e)}")
    #    return f"Warning: Unable to save user [{user}] keys -- ({str(e)})", 500

    return "User [{}] added".format(user)


# if __name__ == "__main__":


# app.run(host="0.0.0.0", port=80)
# app.run(host="0.0.0.0")
