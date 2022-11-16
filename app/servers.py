import json
import logging
import os
import random
from threading import Lock
from typing import List

import db

import docker

PORTS = set(i for i in range(27015, 27100))


class ServerManager:
    def __init__(self):
        self.port_lock = Lock()
        self.gslt_lock = Lock()
        self.gslt_tokens: List[str] = []

        self.read_gslt_tokens()

    def read_gslt_tokens(self):
        with self.gslt_lock:
            logging.info("Parsing gslt.json")
            self.gslt_tokens = None
            with open("gslt.json", "r") as gslt:
                self.gslt_tokens = json.loads(gslt.read())

    def create_match(self, match_cfg: dict):
        self.__start_container(match_cfg)

    def stop_match(self, server_id: int):
        container_name = db.get_server_by_id(server_id).name
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

        if len(self.gslt_tokens):
            # TODO: catch exception if no tokens are available
            container_variables["SERVER_TOKEN"] = self.reserve_free_gslt_token(server_id)

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
            reserved_ports = [server.port for server in db.get_servers()]
            free_ports = list(filter(lambda port: False if port in reserved_ports else True, available_ports))

            port = random.choice(free_ports)
            db.set_server_port(server_id, port)
            return port

    def reserve_free_gslt_token(self, server_id: int) -> str:
        with self.gslt_lock:
            available_tokens = self.gslt_tokens.copy()
            reserved_tokens = [server.gslt_token for server in db.get_servers()]
            free_tokens = list(filter(lambda token: False if token in reserved_tokens else True, available_tokens))

            gslt_token = random.choice(free_tokens)
            db.set_server_token(server_id, gslt_token)
            return gslt_token

    def set_server_status(self, server_id: int, status: int):
        db.set_server_status(server_id, status)
