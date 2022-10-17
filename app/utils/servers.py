import docker


class ServerManager:
    def __init__(self):
        pass

    def __start_container(self, match_cfg: dict):
        client = docker.from_env()

        container_variables = {
            "RCON_PASSWORD": "pass",  # TODO
            "GOTV_PASSWORD": "pass",
            "PORT": 27015,  # TODO, support more servers
            "TICKRATE": 128,
            "MAP": "cs_agency",
            "MATCH_CONFIG": str(match_cfg),
            "cvars": str({"hostname": match_cfg["matchid"]})
        }

        container = client.containers.run("theobrown/csgo-get5-docker:latest", name=match_cfg["matchid"], environment=container_variables,
                                          detach=True, timestamps=True)
        return container
