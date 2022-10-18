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
            "cvars": str({"hostname": match_cfg["matchid"]})
        }

        container = client.containers.run("theobrown/csgo-get5-docker:latest",
                                          name=match_cfg["matchid"].replace(" ", "_"),
                                          environment=container_variables,
                                          detach=False, network_mode="host")
        logging.info(container)
        return container
