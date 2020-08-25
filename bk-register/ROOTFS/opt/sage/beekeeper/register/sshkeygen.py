#!/usr/bin/env python3
# ANL:waggle-license
#  This file is part of the Waggle Platform.  Please see the file
#  LICENSE.waggle.txt for the legal details of the copyright and software
#  license.  For more details on the Waggle project, visit:
#           http://www.wa8.gl
# ANL:waggle-license

import logging
import tempfile
import os
import subprocess as sp
import sys

formatter = logging.Formatter(
    "%(asctime)s  [%(name)s:%(lineno)d] (%(levelname)s): %(message)s"
)
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)


class sshkeygen:
    base_dir = None
    results = {}
    _key_file = None

    def __init__(self):
        self.base_dir = tempfile.TemporaryDirectory()

    def create_key_pair(self, file, type="rsa", bits="4096"):
        priv_file = os.path.join(self.base_dir.name, file)

        cmd = ["ssh-keygen", "-f", priv_file, "-t", type, "-b", bits, "-N", ""]
        logger.debug("Creating keypair: {}".format(" ".join(cmd)))
        result = sp.run(cmd, stdout=sp.PIPE, stderr=sp.PIPE)

        # TODO: error checking on result

        with open(priv_file, "r") as priv_key:
            self.results["private_key"] = priv_key.read()
        with open("{}.pub".format(priv_file), "r") as pub_key:
            self.results["public_key"] = pub_key.read()

        self._key_file = priv_file

    def create_certificate(self, name, ca_path):
        priv_file = os.path.join(self.base_dir.name, name)

        if not (self.results.get("private_key") and self.results.get("public_key")):
            raise Exception("Must create key pair first")

        user = "ep-{}".format(name)
        cmd = [
            "ssh-keygen",
            "-I",
            name,
            "-s",
            ca_path,
            "-n",
            user,
            "-O",
            "no-agent-forwarding",
            "-O",
            "no-pty",
            "-O",
            "no-user-rc",
            "-O",
            "no-x11-forwarding",
            "{}.pub".format(self._key_file),
        ]

        logger.debug("Creating certificate: {}".format(" ".join(cmd)))
        result = sp.run(cmd, stdout=sp.PIPE, stderr=sp.PIPE)

        # TODO: error checking on result

        self.results["user"] = user
        with open("{}-cert.pub".format(self._key_file), "r") as cert_key:
            self.results["certificate"] = cert_key.read()
