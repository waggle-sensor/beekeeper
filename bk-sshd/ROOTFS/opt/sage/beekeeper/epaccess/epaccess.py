#!/usr/bin/env python3
# ANL:waggle-license
#  This file is part of the Waggle Platform.  Please see the file
#  LICENSE.waggle.txt for the legal details of the copyright and software
#  license.  For more details on the Waggle project, visit:
#           http://www.wa8.gl
# ANL:waggle-license

import flask
import logging
import os
import subprocess as sp
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
    user = flask.request.values.get("user")
    logger.info("Delete user [{}]".format(user))

    if not _del_user(user):
        return "Error: unable to delete user [{}]".format(user), 500
    else:
        return "User [{}] deleted".format(user)


# TODO documentation
@app.route("/adduser", methods=["POST"])
def adduser():
    user = flask.request.values.get("user")
    logger.info("Add user [{}]".format(user))

    if not _add_user(user):
        return "Error: unable to add user [{}]".format(user), 500
    else:
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
