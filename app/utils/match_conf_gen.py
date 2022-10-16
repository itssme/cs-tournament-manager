import logging

from utils import db
from jinja2 import Environment, select_autoescape, FileSystemLoader

env = Environment(loader=FileSystemLoader("templates"),
                  autoescape=select_autoescape()
                  )
template = env.get_template("match.cfg")


class MatchGen:
    def __init__(self):
        pass

    @staticmethod
    def matchcfg_from_team_ids(team1: int, team2: int):
        team1 = db.get_team(team1)
        team2 = db.get_team(team2)

        logging.info(team1)
        logging.info(team2)

        data = {"team1": team1.to_json(), "team2": team2.to_json()}
        data["team1"]["players"] = [db.get_team_players(team1.id)]
        data["team2"]["players"] = [db.get_team_players(team2.id)]

        logging.info(data)

        return template.render(**data)
