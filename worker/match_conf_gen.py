import json
import os
import time

from playhouse.shortcuts import model_to_dict

from utils import db, db_models
from utils.utils_funcs import get_api_login_token


class MatchConfig(dict):
    def __init__(self, json_str: str = "", json_obj: dict = None):
        if json_str:
            super(MatchConfig, self).__init__(json.loads(json_str))
        elif json_obj is not None:
            super(MatchConfig, self).__init__(json_obj)
        else:
            super(MatchConfig, self).__init__()

        self["skip_veto"] = False
        self["veto_first"] = "team1"
        self["side_type"] = "standard"
        self["min_players_to_ready"] = 1
        self["min_spectators_to_ready"] = 0
        self["maplist"] = ["de_inferno", "de_mirage", "cs_agency", "de_cbble", "de_overpass", "de_vertigo",
                           "de_anubis"]
        self["cvars"] = {}

    # override print and to str because json uses " and not ' to represent strings
    def __repr__(self):
        return self.to_json()

    def __str__(self):
        return self.to_json()

    def to_json(self):
        return json.dumps(self)

    def set_match_id(self, matchid: str):
        self["matchid"] = matchid

    def set_num_of_maps(self, maps: int):
        self["num_maps"] = maps

    def add_team(self, team_id: int):
        team = db_models.Team.select().where(db_models.Team.id == team_id).get_or_none()
        if team is None:
            raise ValueError(f"Team with id {team_id} does not exist")
        key = "team1"
        if "team1" in self.keys():
            key = "team2"

        # otherwise get5 won't recognize the team
        team_dict = model_to_dict(team)
        final_team_dict = {"id": str(team_dict["id"]), "name": team_dict["name"], "tag": team_dict["tag"], "flag": "AT",
                           "players": dict((player.steam_id, player.name) for player in db.get_team_players(team_id))}

        self[key] = final_team_dict

    def add_cvar(self, cvar_key, cvar_value):
        self["cvars"][cvar_key] = cvar_value

    def generate_match_id(self):
        if "team1" in self.keys() and "team2" in self.keys():
            self.set_match_id(
                f"{self['team1']['name'].replace(' ', '_')}_vs_{self['team2']['name'].replace(' ', '_')}_{time.time_ns()}")
        else:
            raise ValueError("Cannot generate teamname, as team1 or team2 are not added yet.")


class MatchGen:
    def __init__(self):
        pass

    @staticmethod
    def from_team_ids(team1: int, team2: int, best_out_of: int = 1):
        best_out_of = 1 if best_out_of is None else best_out_of

        matchcfg = MatchConfig()
        matchcfg.add_team(team1)
        matchcfg.add_team(team2)
        matchcfg.set_num_of_maps(best_out_of)
        matchcfg.add_cvar("get5_demo_path", "demos/")
        matchcfg.add_cvar("get5_demo_name_format", "{TIME}_{MATCHID}_map{MAPNUMBER}_{MAPNAME}")
        matchcfg.add_cvar("get5_kick_when_no_match_loaded", 1)

        matchcfg.add_cvar("get5_remote_log_url",
                          f"{os.getenv('HTTP_PROTOCOL', 'http://')}{os.getenv('MANAGER_IP', 'host.docker.internal')}/api/cs2/")
        matchcfg.add_cvar("get5_remote_log_header_key", "Authorization")
        matchcfg.add_cvar("get5_remote_log_header_value", get_api_login_token())

        matchcfg.add_cvar("get5_demo_upload_url",
                          f"{os.getenv('HTTP_PROTOCOL', 'http://')}{os.getenv('MANAGER_IP', 'host.docker.internal')}/api/cs2/demo")
        matchcfg.add_cvar("get5_demo_upload_header_key", "Authorization")
        matchcfg.add_cvar("get5_demo_upload_header_value", get_api_login_token())

        matchcfg.add_cvar("get5_remote_backup_url",
                          f"{os.getenv('HTTP_PROTOCOL', 'http://')}{os.getenv('MANAGER_IP', 'host.docker.internal')}/api/cs2/backup")
        matchcfg.add_cvar("get5_remote_backup_header_key", "Authorization")
        matchcfg.add_cvar("get5_remote_backup_header_value", get_api_login_token())

        matchcfg.add_cvar("get5_print_update_notice", 0)
        matchcfg.add_cvar("get5_reset_cvars_on_end", 0)
        matchcfg.add_cvar("tv_enable", 1)
        matchcfg.add_cvar("get5_time_to_start_veto", 10 * 60)
        matchcfg.add_cvar("get5_time_to_start", 10 * 60)
        matchcfg.add_cvar("get5_auto_tech_pause_missing_players", 1)

        matchcfg.generate_match_id()

        return matchcfg
