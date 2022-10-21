import subprocess


class NodeSubprocessProxy:

    def __init__(self, node_id, node_key, proxy_host, proxy_port, proxy_key, proxy_user="root", quiet=True):
        self.node_id = node_id
        self.node_key = node_key
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.proxy_key = proxy_key
        self.proxy_user = proxy_user
        self.extra_args = []

        if quiet:
            self.extra_args += ["-q"]

    def _wrap(self, cmd):
        return [
            "ssh",
            *self.extra_args,
            "-i", self.node_key,
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "StrictHostKeyChecking=no",
            "-o", "IdentitiesOnly=true",
            "-o", f"ProxyCommand=ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no {self.proxy_user}@{self.proxy_host} -p {self.proxy_port} -i {self.proxy_key} netcat -U /home_dirs/node-{self.node_id.upper()}/rtun.sock",
            "root@foo", # proxy command will set proxy settings
            "--",
            *cmd,
        ]

    def run(self, cmd, *args, **kwargs):
        return subprocess.run(self._wrap(cmd), *args, **kwargs)

    def check_call(self, cmd, *args, **kwargs):
        return subprocess.check_call(self._wrap(cmd), *args, **kwargs)

    def check_output(self, cmd, *args, **kwargs):
        return subprocess.check_output(self._wrap(cmd), *args, **kwargs)
