import json
import logging

import docker


class ServerManager:
    def __init__(self):
        pass

    def create_match(self, match_cfg: dict):
        self.__start_container(match_cfg)

    def __start_container(self, match_cfg: dict):
        client = docker.from_env()

        container_variables = {
            "RCON_PASSWORD": "pass",  # TODO
            "GOTV_PASSWORD": "pass",
            "PORT": 27015,  # TODO, support more servers
            "TICKRATE": 128,
            "MAP": "cs_agency",
            "MATCH_CONFIG": json.dumps(match_cfg),
            "cvars": str({"hostname": match_cfg["matchid"], "sv_lan": 0})
        }

        container_name = f"CSGO_{match_cfg['team1']['id']}_{match_cfg['team2']['id']}"

        container = client.containers.run("get5-csgo:latest",
                                          name=container_name,
                                          environment=container_variables,
                                          detach=True, network="host")
        logging.info(f"Started container: {container_name} -> {container}")
        return container
