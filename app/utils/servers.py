import json
import logging
import os
import random
from threading import Lock
from utils import db

import docker

PORTS = set(i for i in range(27015, 27100))
USE_GSLT = True if os.getenv("USE_GSLT", "0") != "1" else False


class ServerManager:
    def __init__(self):
        self.port_lock = Lock()
        self.gslt_lock = Lock()

    def create_match(self, match_cfg: dict):
        self.__start_container(match_cfg)

    def stop_match(self, server_id: int):
        container_name = db.get_server_name_from_id(server_id)
        self.__stop_container_and_delete(container_name)
        db.delete_server(server_id)

    def __start_container(self, match_cfg: dict):
        client = docker.from_env()

        container_name = f"CSGO_{match_cfg['team1']['id']}_{match_cfg['team2']['id']}"

        server_id = self.create_server_id(container_name, match_cfg['team1']['id'], match_cfg['team2']['id'])
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

        if USE_GSLT:
            container_variables["SERVER_TOKEN"] = self.reserve_free_gslttoken(server_id)

        container = client.containers.run("get5-csgo:latest",
                                          name=container_name,
                                          environment=container_variables,
                                          detach=True, network="host")
        logging.info(f"Started container: {container_name} -> {container}")
        self.set_server_status(server_id, 1)
        return container

    def __stop_container_and_delete(self, container_name: str):
        client = docker.from_env()
        logging.info(f"Stopping container: {container_name}")
        container = client.containers.get(container_name)
        container.stop(timeout=10)
        logging.info(f"Stopped container: {container_name}")
        container.remove()
        logging.info(f"Removed container: {container_name}")

    def create_server_id(self, match_name: str, team1: int, team2: int) -> int:
        return db.insert_basic_server_with_teams(match_name, team1, team2)

    def reserve_free_port(self, server_id: int) -> int:
        with self.port_lock:
            available_ports = PORTS.copy()
            reserved_ports = [server[3] for server in db.get_servers()]
            free_ports = list(filter(lambda port: False if port in reserved_ports else True, available_ports))

            port = random.choice(free_ports)
            db.set_server_port(server_id, port)
            return port

    def reserve_free_gslttoken(self, server_id: int) -> str:
        with self.port_lock:
            pass
        return "todo"

    def set_server_status(self, server_id: int, status: int):
        db.set_server_status(server_id, status)
