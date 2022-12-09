import json
import logging
from typing import Dict

from fastapi import Request

import db
from elo import calculate_elo


def map_result(event: Dict):
    match: db.Match = db.get_match_by_matchid(event["matchid"])
    if event["winner"]["team"] == "team1":
        match.series_score_team1 += 1
        match.update_attribute("series_score_team1")
    elif event["winner"]["team"] == "team2":
        match.series_score_team2 += 1
        match.update_attribute("series_score_team2")
    else:
        logging.error(f"Got a map_result event with no team winning? -> {event}")

    team1 = db.get_team_by_id(match.team1)
    team2 = db.get_team_by_id(match.team2)
    logging.info(f"Updating ELO: {team1.elo}, {team2.elo}, {event['team1_score']}, {event['team2_score']}")

    team1.elo, team2.elo = calculate_elo(team1.elo, team2.elo, event["team1_score"], event["team2_score"])
    team1.update_attribute("elo")
    team2.update_attribute("elo")

    logging.info(f"Updated ELO: {team1.elo}, {team2.elo}, {event['team1_score']}, {event['team2_score']}")


def series_end(event: Dict):
    match: db.Match = db.get_match_by_matchid(event["matchid"])
    match.series_score_team1 = event["team1_series_score"]
    match.series_score_team2 = event["team2_series_score"]
    match.finished = 1
    match.update_attribute("finished")


def player_say(event: Dict):
    logging.info(f"Player said: {event['message']}")


callbacks = {"player_say": player_say, "map_result": map_result, "series_end": series_end}


def set_api_routes(app):
    @app.post("/")
    async def get5_event(request: Request):
        json_str = await request.body()
        event = json.loads(json_str)
        logging.info(event)

        if event["event"] in callbacks.keys():
            callbacks[event["event"]](event)

        return ""
