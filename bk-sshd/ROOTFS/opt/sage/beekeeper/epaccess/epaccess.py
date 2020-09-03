#!/usr/bin/env python3
# ANL:waggle-license
#  This file is part of the Waggle Platform.  Please see the file
#  LICENSE.waggle.txt for the legal details of the copyright and software
#  license.  For more details on the Waggle project, visit:
#           http://www.wa8.gl
# ANL:waggle-license

import flask
import grp
import logging
import os
import pwd
import subprocess as sp
import stat
import sys

app = flask.Flask(__name__)

formatter = logging.Formatter(
    "%(asctime)s  [%(name)s:%(lineno)d] (%(levelname)s): %(message)s"
)
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

USER_HOME_DIR = "/home_dirs"


# TODO documentation
def _user_exists(user):
    cmd = ["id", "-u", user]
    result = sp.run(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
    return result.returncode == 0


# TODO documentation
def _add_user(user):
    logger.debug("Adding user [{}] to system".format(user))
    success = False

    if _user_exists(user):
        logger.debug("- user [{}] already exists, skipping".format(user))
        success = True
    else:
        cmd = ["useradd", "-mr", "-b", USER_HOME_DIR, "-p", user, user]
        result = sp.run(cmd, stdout=sp.PIPE, stderr=sp.PIPE)

        if result.returncode == 0:
            logger.debug("- user [{}] add: success".format(user))
            success = True
        else:
            # TODO: add more information here
            logger.error("- user [{}] add: fail".format(user))

    return success


# TODO documentation
def _save_keys(user, private_key=None, public_key=None, certificate=None):
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


# TODO documentation
def _del_user(user):
    logger.debug("Deleting user [{}] from system".format(user))
    success = False

    if not _user_exists(user):
        logger.debug("- user [{}] does not exists, skipping".format(user))
        success = True
    else:
        cmd = ["deluser", "--remove-home", user]
        result = sp.run(cmd, stdout=sp.PIPE, stderr=sp.PIPE)

        if result.returncode == 0:
            logger.debug("- user [{}] delete: success".format(user))
            success = True
        else:
            # TODO: add more information here
            logger.error("- user [{}] delete: fail".format(user))

    return success


# TODO documentation
@app.route("/deluser", methods=["POST"])
def deluser():
    user = flask.request.values.get("id")
    logger.info("Delete user [{}]".format(user))

    if not _del_user(user):
        return "Error: unable to delete user [{}]".format(user), 500
    else:
        return "User [{}] deleted".format(user)


# TODO documentation
@app.route("/adduser", methods=["POST"])
def adduser():
    user = flask.request.values.get("id")
    logger.info("Add user [{}]".format(user))

    if not _add_user(user):
        return "Error: unable to add user [{}]".format(user), 500
    else:
        try:
            # save the user's keys
            priv_key = flask.request.values.get("private_key")
            pub_key = flask.request.values.get("public_key")
            cert = flask.request.values.get("certificate")
            _save_keys(user, private_key=priv_key, public_key=pub_key, certificate=cert)
        except Exception as e:
            logger.warning("Warning: Unable to save user [{}] keys".format(user))
            logger.debug(e)
        return "User [{}] added".format(user)


if __name__ == "__main__":
    # scan through the user home directories and ensure the users exist
    logger.debug("Creating users from previous instance")
    users = [
        d
        for d in os.listdir(USER_HOME_DIR)
        if os.path.isdir(os.path.join(USER_HOME_DIR, d))
    ]
    for user in users:
        _add_user(user)

    app.run(host="0.0.0.0", port=80)
