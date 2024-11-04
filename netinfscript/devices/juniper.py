#!/usr/bin/env python3.10

"""
Juniper object with all necessary parameters and functions.
"""

import logging
from base_device import BaseDevice
from connections.conn_ssh import ConnSSH


class Juniper(BaseDevice, ConnSSH):
    """Juniper device object."""
    def __init__(
            self,
            ip: str,
            port: int,
            name: str,
            vendor: str,
            connection: str,
            username: str,
            password: str,
            privilege_cmd: str,
            privilege_password: str,
            key_file: str,
            passphrase: str
            ) -> "BaseDevice":
        super().__init__(
            ip,
            port,
            name,
            vendor,
            connection,
            username,
            password,
            privilege_cmd,
            privilege_password,
            key_file,
            passphrase
            )
        self.logger = logging.getLogger(
            f"netscriptbackup.devices.juniper")
        self.logger.debug(f"{self.ip}:Creatad.")
        self.device_type = "juniper"

    def get_command_show_config(self):
        """Returns a command that display the current configuration"""
        self.logger.debug(f"{self.ip}:Returning commands.")
        return "show config | display set"

    def config_filternig(self, config):
        """Filters config from unnecessary information"""
        self.logger.debug(f"{self.ip}:Configuration filtering.")
        _tmp_config: list = []
        config: str = config.splitlines()
        for line in config:
            if "#" in line:
                self.logger.debug(f"{self.ip}:Skiping line '{line}'.")
                continue
            _tmp_config.append(line)
        config_to_return: str = "\n".join(_tmp_config)
        return config_to_return


if __name__ == "__main__":
    pass