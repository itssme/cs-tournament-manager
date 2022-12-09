import json
import logging
from typing import Dict

from fastapi import Request

import db


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


def series_end(event: Dict):
    match: db.Match = db.get_match_by_matchid(event["matchid"])
    match.series_score_team1 = event["team1_series_score"]
    match.series_score_team2 = event["team2_series_score"]
    match.finished = 1
    match.update_attribute("finished")


def player_say(event: Dict):
    logging.info(f"Player said: {event['message']}")


callbacks = {"player_say": player_say, "map_result": map_result}


def set_api_routes(app):
    @app.post("/")
    async def get5_event(request: Request):
        json_str = await request.body()
        event = json.loads(json_str)
        logging.info(event)

        if event["event"] in callbacks.keys():
            callbacks[event["event"]](event)

        return ""
