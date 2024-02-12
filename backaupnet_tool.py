#!/usr/bin/env python3

from configparser import ConfigParser
import logging
import json
from modules.devices import Device, Cisco, Mikrotik
import paramiko
import subprocess



class Config_Load():


    def __init__(self):
        self._config = ConfigParser()
        try:
            self._config.read("config.ini")
            self.load_config()
        except Exception as e:
            print()
            print("#! CAN'T LOAD CONFIG FILE")
            print(f"#! Problem: {e}")
            print("#! Exiting...")
            print()
            exit()


    def load_config(self):
        self.devices_path = self._config["Application_Setup"]["Devices_Path"]
        self.passwords_path = self._config["Application_Setup"]["Passwords_Path"]
        self.configs_path = self._config["Application_Setup"]["Configs_Path"]

        _logging_lv_lst = ["debug", "info", "warning", "error", "critical"]
        _logging_level = self._config["Logging"]["Level"]
        if _logging_level not in _logging_lv_lst:
            print()
            print("#! Not allowed loggin level")
            print(f"#! Allowed logging level list: {_logging_lv_lst}")
            print("#! Exiting...")
            print()
            exit()
        else:
            self.logging_level = _logging_level.lower()
        self._logging_path = self._config["Logging"]["File_Path"]
    
    ## Logging setup
    def set_logging(self):
        logger = logging.getLogger("backup_app")
        if self.logging_level.lower() == "debug":
            logger.setLevel(logging.DEBUG)

        elif self.logging_level.lower() == "info":
            logger.setLevel(logging.INFO)

        elif self.logging_level.lower() == "warning":
            logger.setLevel(logging.WARNING)

        elif self.logging_level.lower() == "error":
            logger.setLevel(logging.ERROR)

        elif self.logging_level.lower() == "critical":
            logger.setLevel(logging.CRITICAL)

        file_handler = logging.FileHandler(self._logging_path)
        if self.logging_level.lower() == "debug":
            file_handler.setLevel(logging.DEBUG)

        elif self.logging_level.lower() == "info":
            file_handler.setLevel(logging.INFO)

        elif self.logging_level.lower() == "warning":
            file_handler.setLevel(logging.WARNING)

        elif self.logging_level.lower() == "error":
            file_handler.setLevel(logging.ERROR)

        elif self.logging_level.lower() == "critical":
            file_handler.setLevel(logging.CRITICAL)

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.ERROR)

        formatter = logging.Formatter(
            "%(asctime)s:%(name)s:%(levelname)s:\n\t%(message)s"
            )
        file_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

        return logger



CONFIG_LOADED = Config_Load()
LOGGER = CONFIG_LOADED.set_logging()



class Devices_Load():
    """Class loads device and store this in object."""


    def __init__(self) -> None:
        self.logger = logging.getLogger("backup_app.Devices_Load")


    def load_jsons(self):
        try:
            self.logger.debug("Loading basic devices list.")
            with open(CONFIG_LOADED.devices_path) as f:
                _basic_devs = json.load(f)
            self.logger.debug("Loading passwords list.")
            with open(CONFIG_LOADED.passwords_path) as f:
                _passwords = json.load(f)

            def mergign_dcts(dct1, dct2):
                self.logger.debug("Merging lists.")
                for key in dct1.keys():
                    try:
                        dct1[key]["password"] = dct2[key]["password"]
                        dct1[key]["passphrase"] = dct2[key]["passphrase"]

                    except KeyError as e:
                        print()
                        self.logger.error(
                            f"Key error, check devices or passwords file for ip: {e}"
                            )
                        print("#! Exiting...")
                        print()
                        exit()

                return dct1
            
            self.devices_data = mergign_dcts(_basic_devs, _passwords)

        except FileNotFoundError as e:
            print()
            self.logger.error(f"{e}")
            print("#! Exiting...")
            exit()

        except json.decoder.JSONDecodeError as e:
            print()
            self.logger.error(f"{e}")
            print("#! Exiting...")
            print()
            exit()

        except Exception as e:
            print()
            self.logger.error(f"{e}")
            print("#! Exiting...")
            print()
            exit()



class SSH_Connection():


    def __init__(self, device) -> None:
        self.logger = logging.getLogger("backup_app.SSH_Connection")
        self.device = device


    def connect(self):
        try:
            self.logger.debug(f"Checking if the host {self.device.ip} is responding")
            ping = ["ping", "-W", "1", "-c", "4", self.device.ip]
            subprocess.check_output(ping).decode()

        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Host {self.device.ip} is not responding. Skip")
            return False

        try:
            self.logger.debug(f"Trying create connection with public key to: {self.device.ip}")
            self.client = paramiko.SSHClient()
            self.client.load_system_host_keys()
            self.client.connect(
                hostname = self.device.ip,
                port = self.device.port,
                username = self.device.username,
                passphrase = self.device.passphrase,
            )
            return True
        
        except paramiko.BadHostKeyException as e:
            self.logger.warning(f"Bad host key{e}")
            return False
        
        except paramiko.AuthenticationException as e:
            self.logger.warning(f"{e}: {self.device.ip}")
            return False
        
        except paramiko.SSHException as e:
            if "known_hosts" in str(e):
                self.logger.info(
                    f"Can't connect. You need to add key policy for host: {self.device.ip}"
                    )
                return False
            else:
                self.logger.debug(f"Trying create connection with password to: {self.device.ip}")
                self.client = paramiko.SSHClient()
                self.client.connect(
                    hostname = self.device.ip,
                    port = self.device.port,
                    username = self.device.username,
                    password = self.device.password,
                    allow_agent = False,
                    look_for_keys = False
                )
                return True
        
        except Exception as e:
            self.logger.debug(f"Exceptation {e}")
            return False


    def close(self):
        try:
            if self.client.get_transport().is_active():
                self.client.close()

            else:
                pass

        except:
            pass


    def get_config(self):

        self.logger.debug(f"Opening a connection to: {self.device.ip}")
        connection = self.connect()

        if connection:
            
            self.logger.debug(f"Getting command for device: {self.device.ip}")
            cli_command = self.device.command_show_config()
            if not cli_command:
                self.logger.warning(
                    f"Can't get command. Check soft for: {self.device.ip}"
                    )
                return False
            
            else:
                self.logger.debug(f"Sending commands to: {self.device.ip}")
                stdin, stdout, stderr = self.client.exec_command(
                    command = cli_command,
                    bufsize = 10_000,
                    timeout = 2
                    )
                stdout = stdout.readlines()

                self.close()

                return stdout
        
        else:
            self.logger.warning(f"Can't get config from: {self.device.ip}")
            self.close()
            return False



class Backup():


    def __init__(self) -> None:
        self.logger = logging.getLogger("backup_app.Backup")
        self.devices = Devices_Load()
        self.devices.load_jsons()


    def create_devices(self):
        devices = self.devices.devices_data

        for ip in devices:
            if devices[ip]["vendor"] == "cisco":
                Cisco(
                    name = devices[ip]["name"],
                    vendor = devices[ip]["vendor"],
                    ip = ip,
                    username = devices[ip]["username"],
                    port = devices[ip]["port"],
                    connection = devices[ip]["connection"],
                    soft = devices[ip]["soft"],
                    password = devices[ip]["password"],
                    passphrase = devices[ip]["passphrase"]
                )

            elif devices[ip]["vendor"] == "mikrotik":
                Mikrotik(
                    name = devices[ip]["name"],
                    vendor = devices[ip]["vendor"],
                    ip = ip,
                    username = devices[ip]["username"],
                    port = devices[ip]["port"],
                    connection = devices[ip]["connection"],
                    soft = devices[ip]["soft"],
                    password = devices[ip]["password"],
                    passphrase = devices[ip]["passphrase"]
                )
                
            else:
                self.logger.warning(f"Device is not supported. IP: {ip}")
                pass


    def get_configuration(self):
        for dev in Device.devices_lst:
            self.logger.debug(f"Start creating backup for: {dev.ip}")
            ssh = SSH_Connection(dev)
            stdout = ssh.get_config()

            if not stdout:
                pass

            else:
                self.write_config(dev.ip, dev.name, stdout)


    def write_config(self, ip, name, stdout):
        try:
            file_path = f"{CONFIG_LOADED.configs_path}/{name}_{ip}.txt"
            with open(file_path, "w") as f:
                f.writelines(stdout)

        except FileNotFoundError as e:
            self.logger.error(f"File or dictionary not found: {file_path}")
            pass



if __name__ == "__main__":
    pass