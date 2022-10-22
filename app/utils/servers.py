import json
import logging
import random
from threading import Lock
from utils import db

import docker

PORTS = set(i for i in range(27015, 27100))


class ServerManager:
    def __init__(self):
        self.port_lock = Lock()

    def create_match(self, match_cfg: dict):
        self.__start_container(match_cfg)

    def __start_container(self, match_cfg: dict):
        client = docker.from_env()

        container_name = f"CSGO_{match_cfg['team1']['id']}_{match_cfg['team2']['id']}"

        server_id = self.create_server_id(container_name)
        port = self.reserve_free_port(server_id)

        container_variables = {
            "RCON_PASSWORD": "pass",  # TODO
            "GOTV_PASSWORD": "pass",
            "PORT": port,
            "TICKRATE": 128,
            "MAP": "cs_agency",
            "MATCH_CONFIG": json.dumps(match_cfg),
            "cvars": str({"hostname": match_cfg["matchid"], "sv_lan": 0})
        }

        container = client.containers.run("get5-csgo:latest",
                                          name=container_name,
                                          environment=container_variables,
                                          detach=True, network="host")
        logging.info(f"Started container: {container_name} -> {container}")
        self.set_server_status(server_id, 1)
        return container

    def create_server_id(self, match_name: str) -> int:
        return db.insert_basic_server(match_name)

    def reserve_free_port(self, server_id: int) -> int:
        with self.port_lock:
            available_ports = PORTS.copy()
            reserved_ports = [server[3] for server in db.get_servers()]
            free_ports = list(filter(lambda port: False if port in reserved_ports else True, available_ports))

            port = random.choice(free_ports)
            db.set_server_port(server_id, port)
            return port

    def set_server_status(self, server_id: int, status: int):
        db.set_server_status(server_id, status)
