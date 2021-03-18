#!/usr/bin/env python3
"""
Helper class to assist in creating ssh key-pairs and certificates.

ANL:waggle-license
 This file is part of the Waggle Platform.  Please see the file
 LICENSE.waggle.txt for the legal details of the copyright and software
 license.  For more details on the Waggle project, visit:
          http://www.wa8.gl
ANL:waggle-license
"""

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


class SSHKeyGen:
    """Create ssh key-pairs and certificates"""

    base_dir = None
    #results = {}
    _key_file = None



    def __init__(self):
        self.base_dir = tempfile.TemporaryDirectory()


    def create_key_pair(self, file, key_gen_type, key_gen_args):
        """Create a ssh key-pair (`file` and `file`.pub)

        Arguments:
            file (str): the filename for the private key (public will be `file`.pub)
            type (str): the type of key to create (default: 'rsa')
            bits (str): the bit depth of the key (default: '4096')

        Returns:
            none
        """

        if not file:
            raise Exception("file undefined")
        priv_file = os.path.join(self.base_dir.name, file)

        if not key_gen_type:
            raise Exception("key_gen_type undefined")

        cmd = ["ssh-keygen", "-f", priv_file, "-N", "", "-t" , key_gen_type ] + key_gen_args.split()
        logger.debug("Creating key-pair: {}".format(" ".join(cmd)))
        result = sp.run(cmd, stdout=sp.PIPE, stderr=sp.PIPE)

        if result.returncode != 0:
            logger.error(
                f"Error: Unable to create key-pair [{file}][key_gen_type: {key_gen_type}, key_gen_args: {key_gen_args}]"
            )
            # raise exception
            result.check_returncode()

        with open(priv_file, "r") as priv_key:
            private_key = priv_key.read()
        with open(f"{priv_file}.pub", "r") as pub_key:
            public_key = pub_key.read()

        self._key_file = priv_file

        return {"private_key" : private_key, "public_key":public_key }

    # writes key-pair files (in case key pair came from database)
    def write_keys_to_files(self, node_id, priv_key, public_key):

        priv_file = os.path.join(self.base_dir.name, node_id)

        with open(priv_file, "w") as fp:
            fp.write(priv_key)

        self._key_file = priv_file


        public_key_file = os.path.join(self.base_dir.name, f"{node_id}.pub")
        with open(public_key_file, "w") as fp:
            fp.write(public_key)

        return







    def create_certificate(self, name, ca_path):
        """Create the certificate from the key-pair. Key-pair must be created first.

        Arguments:
            name (str): the username to put in the certificate
            ca_path (str): the path to the certificate authority

        Returns:
            none
        """

        if not self._key_file:
            raise Exception("self._key_file is empty")
        #priv_file = os.path.join(self.base_dir.name, name)

        #if not (self.results.get("private_key") and self.results.get("public_key")):
        #    raise Exception("Must create key-pair first")

        user = "node-{}".format(name)
        cmd = [
            "ssh-keygen",
            "-I", # certificate_identity
            name,
            "-s",
            ca_path,
            "-n", # one or more principals (user or host names)
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

        if result.returncode != 0:
            logger.error(
                "Unable to create certificate [name: {}][ca: {}]".format(name, ca_path)
            )
            # raise exception
            result.check_returncode()

        #self.results["user"] = user
        certificate = ""
        with open("{}-cert.pub".format(self._key_file), "r") as cert_key:
            #self.results["certificate"] = cert_key.read()
            certificate = cert_key.read()

        return { "certificate": certificate, "user": user}



