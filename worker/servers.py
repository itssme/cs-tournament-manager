import json
import logging
import os
import random
from threading import Lock
from typing import List

from utils import db, db_models

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

    def create_match(self, match_cfg: dict, loadbackup_url: str = None) -> tuple[bool, int]:
        logging.info(f"Creating match in server manager: {match_cfg['matchid']}")
        return self.__start_container(match_cfg, loadbackup_url)

    def stop_match(self, server_id: int, finished: int = 3):
        container_name: str = db_models.Server.select().where(db_models.Server.id == server_id).get().container_name
        self.__stop_container_and_delete(container_name)
        match = db.get_match_by_serverid(server_id)
        match.finished = finished
        match.save()
        db_models.Server.select().where(db_models.Server.id == server_id).get().delete_instance()

    def __start_container(self, match_cfg: dict, loadbackup_url: str = None) -> tuple[bool, int]:
        client = docker.from_env()

        container_name = f"cs2_{match_cfg['team1']['id']}_{match_cfg['team2']['id']}"

        if loadbackup_url is None:
            match: db_models.Match = db_models.Match.create(name=container_name, matchid=match_cfg["matchid"],
                                                            team1=match_cfg['team1']['id'],
                                                            team2=match_cfg['team2']['id'],
                                                            best_out_of=match_cfg['num_maps'])
        else:
            match: db_models.Match = db_models.Match.select().where(
                db_models.Match.matchid == match_cfg["matchid"]).get()
            match.finished = 0
            match.save()

        server: db_models.Server = db_models.Server.create(container_name=container_name, match=match.id,
                                                           ip=os.getenv("EXTERNAL_IP", "host.docker.internal"))

        port = self.reserve_free_port(server)

        container_variables = {
            "RCON_PASSWORD": os.getenv("RCON_PASSWORD", "pass"),
            "GOTV_PASSWORD": os.getenv("GOTV_PASSWORD", "pass"),
            "PORT": port,
            "TICKRATE": 128,
            "MAP": "cs_agency",
            "MATCH_CONFIG": json.dumps(match_cfg),
            "cvars": str({"hostname": match_cfg["matchid"], "sv_lan": 1, "tv_enable": 1})
        }

        if len(self.gslt_tokens):
            logging.info(f"Tying to reserving GSLT token for match: {match.matchid}")
            try:
                container_variables["SERVER_TOKEN"] = self.reserve_free_gslt_token(server)
            except IndexError:
                logging.error(f"No GSLT tokens left for match: {match.matchid}, starting without gstl token")

        if loadbackup_url is not None:
            logging.info(f"Loading backup for match: {match.matchid} -> {loadbackup_url}")
            container_variables["LOAD_BACKUP"] = loadbackup_url

        try:
            logging.info(f"Starting container for match: {match.matchid}")
            if os.getenv("WINDOWS", "0") == "1":
                logging.info("Starting container on Windows")
                container = client.containers.run("get5-cs2:latest",
                                                  name=container_name,
                                                  environment=container_variables,
                                                  detach=True, ports={port: port})
            else:
                logging.info("Starting container on linux host")
                container = client.containers.run("get5-cs2:latest",
                                                  name=container_name,
                                                  environment=container_variables,
                                                  detach=True, network="host")
            logging.info(f"Started container: {container_name} -> {container}")
            return True, port
        except Exception as e:
            logging.error(f"Failed to start container ({match.matchid}) in server manager: {e}")
            match.finished = 3
            match.save()
            db_models.Server.select().where(db_models.Server.id == server.id).get().delete_instance()
            return False, port

    def __stop_container_and_delete(self, container_name: str):
        client = docker.from_env()
        logging.info(f"Stopping container: {container_name}")
        try:
            container = client.containers.get(container_name)
            container.stop(timeout=10)
            logging.info(f"Stopped container: {container_name}")
            container.remove()
            logging.info(f"Removed container: {container_name}")
        except docker.errors.NotFound:
            logging.error(f"Container not found: {container_name}")

    def reserve_free_port(self, server: db_models.Server) -> int:
        with self.port_lock:
            available_ports = PORTS.copy()
            reserved_ports = [server.port for server in
                              db_models.Server.select()]  # TODO: only on servers that are running on this instance?
            free_ports = list(filter(lambda port: False if port in reserved_ports else True, available_ports))

            port = random.choice(free_ports)
            server.port = port
            server.save()

            return port

    def reserve_free_gslt_token(self, server: db_models.Server) -> str:
        with self.gslt_lock:
            # TODO: make request from main server and get tokens from there
            available_tokens = self.gslt_tokens.copy()
            reserved_tokens = [server.gslt_token for server in db_models.Server.select()]
            free_tokens = list(filter(lambda token: False if token in reserved_tokens else True, available_tokens))

            gslt_token = random.choice(free_tokens)
            server.gslt_token = gslt_token
            server.save()
            return gslt_token
