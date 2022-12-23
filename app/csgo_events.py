import json
import logging
from typing import Dict

import requests
from fastapi import Request

import db
from elo import calculate_elo


# TODO: check notice if both teams are ready and change `finished` for match

def demo_upload_ended(event: Dict):
    match: db.Match = db.get_match_by_matchid(event["matchid"])
    if not event["success"]:
        logging.error(
            f"Match: {match.matchid} tried to upload demo, but failed. Demo is not saved and container cannot be shut down.")
        return

    server: db.Server = db.get_server_for_match(match.matchid)

    match.finished = 2
    match.update_attribute("finished")

    res = requests.delete(f"http://{server.ip}/api/match", json={"id": server.id}, timeout=60)
    if res.status_code == 200:
        logging.info(
            f"After demo has been uploaded, container running matchid: {match.matchid}, (name={server.container_name}) has been stopped")
    else:
        logging.error(f"Unable to stop container for match: {match}, server: {server} -> {res.text}")


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


callbacks = {"player_say": player_say, "map_result": map_result, "series_end": series_end,
             "demo_upload_ended": demo_upload_ended}


def set_api_routes(app):
    @app.post("/")
    async def get5_event(request: Request):
        json_str = await request.body()
        event = json.loads(json_str)
        logging.info(f"Event: {event['event']}")
        logging.info(event)

        if event["event"] in callbacks.keys():
            callbacks[event["event"]](event)

        return ""
