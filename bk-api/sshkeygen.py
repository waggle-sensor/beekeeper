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
    base_dir_name = ""
    #results = {}
    _key_file = None



    def __init__(self, deleteDirectory=True):
        if deleteDirectory:
            self.base_dir = tempfile.TemporaryDirectory()
            self.base_dir_name = self.base_dir.name
        else:
            self.base_dir_name= tempfile.mkdtemp() # only for debugging purposes

            logger.debug(f"SSHKeyGen base_dir: {self.base_dir_name}")



    def create_key_pair(self, file, key_gen_type, key_gen_args):
        """Create a ssh key-pair (`file` and `file`.pub)

        Arguments:
            file (str): the filename for the private key (public will be `file`.pub)
            key_gen_type (str): the type of key to create (e.g. Ed25519 or rsa)
            key_gen_args (str): e.g. "-b 4096" the bit depth of the key in case of rsa

        Returns:
            none
        """

        if not file:
            raise Exception("file undefined")
        priv_file = os.path.join(self.base_dir_name, file)

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

        priv_file = os.path.join(self.base_dir_name, node_id)

        with open(priv_file, "w") as fp:
            fp.write(priv_key)

        self._key_file = priv_file


        public_key_file = os.path.join(self.base_dir_name, f"{node_id}.pub")
        with open(public_key_file, "w") as fp:
            fp.write(public_key)

        return







    def create_reverse_tunnel_certificate(self, name, ca_path):
        """Create the certificate from the key-pair. Key-pair must be created first.

        Arguments:
            name (str): the username to put in the certificate
            ca_path (str): the path to the certificate authority

        Returns:
            none
        """

        if not self._key_file:
            raise Exception("self._key_file is empty")
        #priv_file = os.path.join(self.base_dir_name, name)

        #if not (self.results.get("private_key") and self.results.get("public_key")):
        #    raise Exception("Must create key-pair first")

        user = "node-{}".format(name)
        cmd = [
            "ssh-keygen",
            "-I", name,  # certificate_identity
            "-s", ca_path,
            "-n", user, # one or more principals (user or host names)
            "-O", "no-agent-forwarding",
            "-O", "no-pty",
            "-O", "no-user-rc",
            "-O", "no-x11-forwarding",
            "{}.pub".format(self._key_file),
        ]

        logger.debug("Creating reverse tunnel certificate: {}".format(" ".join(cmd)))
        #result = sp.run(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
        result = sp.run(cmd, capture_output=True)


        if result.returncode != 0:
            logger.error("Unable to create certificate [name: {name}][ca: {ca_path}]")
            logger.error(f"result.stdout: {result.stdout}")
            logger.error(f"result.stderr: {result.stderr}")
            # raise exception
            result.check_returncode()

        #self.results["user"] = user
        certificate = ""
        with open("{}-cert.pub".format(self._key_file), "r") as cert_key:
            #self.results["certificate"] = cert_key.read()
            certificate = cert_key.read()

        return { "certificate": certificate, "user": user}

    def create_upload_certificate(self, ca_path, key_type, key_type_args, node_id):
        # key_type e.g. rsa-sha2-256 or Ed25519
        # dsa | ecdsa | ecdsa-sk | ed25519 | ed25519-sk AND rsa-sha2-256 , rsa-sha2-512
        # see https://man7.org/linux/man-pages/man1/ssh-keygen.1.html


       # export CAKEYFILE=/beehives/test-beehive2/ssh/ca
        #export name=node-testnode2
        #export keyfile=testnode2
        #ssh-keygen -s "$CAKEYFILE" \
        #  -t rsa-sha2-256 \
        #  -I "$name ssh host key" \
        #  -n "$name" \
        #  -V "-5m:+365d" \
        # "$keyfile"

        if not key_type_args:
            key_type_args = ""

        user = "node-{}".format(node_id)
        cmd = [
            "ssh-keygen",
            "-t", key_type
            ] + key_type_args.split() + [
            "-I", f"{user} ssh host key", # certificate_identity
            "-s", ca_path,
            "-n", user, # one or more principals (user or host names)
            "-V", "-5m:+365d",
            "-O", "no-agent-forwarding",
            "-O", "no-pty",
            "-O", "no-user-rc",
            "-O", "no-x11-forwarding",
            "{}.pub".format(self._key_file),
            ]

        logger.debug("Creating uploader certificate: {}".format(" ".join(cmd)))
        result = sp.run(cmd, capture_output=True ) #stdout=sp.PIPE, stderr=sp.PIPE
        logger.debug("f{result.stdout}")
        if result.returncode != 0:
            logger.error(
                f"Unable to create uploader certificate [name: {user}][ca: {ca_path}] result.stderr: {result.stderr}"
            )
            # raise exception
            result.check_returncode()

        #self.results["user"] = user
        certificate = ""
        with open("{}-cert.pub".format(self._key_file), "r") as cert_key:
            #self.results["certificate"] = cert_key.read()
            certificate = cert_key.read()

        return { "certificate": certificate, "user": user}
