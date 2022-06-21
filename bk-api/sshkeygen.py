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
import subprocess
import sys
from pathlib import Path

formatter = logging.Formatter(
    "%(asctime)s  [%(name)s:%(lineno)d] (%(levelname)s): %(message)s"
)
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)


def run_command_communicate(command, input_str=None):
    try:
        p = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except Exception as e:
        raise Exception(f"subprocess.Popen: {str(e)}")

    # returns output_stdout,output_stderr
    input=None
    if input_str:
        input=input_str.encode()

    stdout, stderr =  p.communicate(input=input)
    exit_code = p.wait()
    return stdout, stderr , exit_code


def run_command(cmd, return_stdout=False):
    cmd_str = " ".join(cmd)
    logger.debug(f"Executing: {cmd_str}")

    result = subprocess.run(cmd, capture_output=True)


    if result.returncode != 0:
        logger.error(f"Command failed with result.returncode: {result.returncode}")
        logger.error(f"result.stdout: {result.stdout}")
        logger.error(f"result.stderr: {result.stderr}")
        # raises exception
        result.check_returncode()

    if return_stdout:
        logger.error(f"result.stdout: {result.stdout}")
        #return "xxx"
        return result.stdout.decode("utf-8")

    return



class SSHKeyGen:
    """SSHKeyGen creates ssh key-pairs and certificates."""

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

        run_command(cmd)


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


        run_command(cmd)

        #self.results["user"] = user
        certificate = ""
        with open("{}-cert.pub".format(self._key_file), "r") as cert_key:
            #self.results["certificate"] = cert_key.read()
            certificate = cert_key.read()

        return { "certificate": certificate, "user": user}


    # ca_path: beehive-specific CA for ssh (e.g. upload)
    def create_upload_certificate(self, ca_path, key_type, key_type_args, node_id):
        # key_type e.g. rsa-sha2-256 or Ed25519
        # dsa | ecdsa | ecdsa-sk | ed25519 | ed25519-sk AND rsa-sha2-256 , rsa-sha2-512
        # see https://man7.org/linux/man-pages/man1/ssh-keygen.1.html




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

        run_command(cmd)


        #self.results["user"] = user
        certificate = ""
        with open("{}-cert.pub".format(self._key_file), "r") as cert_key:
            #self.results["certificate"] = cert_key.read()
            certificate = cert_key.read()

        return { "certificate": certificate, "user": user}
    
    def create_service_tls_credentials(self, tls_ca_path, tls_ca_cert_path, name):
        """
        Returns a newly generated TLS key / cert for a Beehive service.
        """
        basedir = Path(self.base_dir_name, "beehives")
        basedir.mkdir(parents=True, exist_ok=True)

        keyfile = Path(basedir, name+'.key.pem').absolute()
        csrfile = Path(basedir, name+'.csr.pem').absolute()
        certfile = Path(basedir, name+'.cert.pem').absolute()

        run_command([
            "openssl",
            "req",
            "-new",
            "-nodes",
            "-newkey", "rsa:4096",
            "-keyout", str(keyfile),
            "-out" , str(csrfile),
            "-subj", f'/CN={name}'
        ])

        run_command([
            "openssl",
            "x509",
            "-req",
            "-in",  str(csrfile),
            "-out", str(certfile),
            "-CAkey", str(tls_ca_path),
            "-CA", str(tls_ca_cert_path),
            "-CAcreateserial",
            "-sha256",
            "-days", "365"
        ])

        return {
            "keyfile": Path(keyfile).read_text(),
            "certfile": Path(certfile).read_text(),
        }

    def create_node_tls_certificate(self, tls_ca_path, tls_ca_cert_path, name):
        # these certificates should be more short lived and renewing them should be easy.
        basedir = Path(self.base_dir_name, "nodes")
        basedir.mkdir(parents=True, exist_ok=True)

        keyfile = Path(basedir, name+'.key.pem').absolute()
        csrfile = Path(basedir, name+'.csr.pem').absolute()
        certfile = Path(basedir, name+'.cert.pem').absolute()

        run_command([
            "openssl",
            "req",
            "-new",
            "-nodes",
            "-newkey", "rsa:4096",
            "-keyout", str(keyfile),
            "-out" , str(csrfile),
            "-subj", f'/CN={name}'
        ])

        run_command([
            "openssl",
            "x509",
            "-req",
            "-in",  str(csrfile),
            "-out", str(certfile),
            "-CAkey", str(tls_ca_path),
            "-CA", str(tls_ca_cert_path),
            "-CAcreateserial",
            "-sha256",
            "-days", "365"
        ])

        return {
            "user": name,
            "keyfile": Path(keyfile).read_text(),
            "certfile": Path(certfile).read_text(),
        }
