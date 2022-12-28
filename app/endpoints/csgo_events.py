import json
import logging
from typing import Dict
from time import sleep

import requests
from fastapi import Request

from endpoints import csgo_stats_event
from rcon import RCON
from sql import db
from elo import calculate_elo


def going_live(event: Dict):
    match: db.Match = db.get_match_by_matchid(event["matchid"])
    match.finished = 0
    match.update_attribute("finished")


def demo_upload_ended(event: Dict):
    match: db.Match = db.get_match_by_matchid(event["matchid"])
    if not event["success"]:
        logging.error(
            f"Match: {match.matchid} tried to upload demo, but failed. Demo is not saved and container cannot be shut down.")
        return

    if match.finished == 1:  # TODO: check why this is not true
        logging.info(
            f"Demo upload for match: {match.matchid} but the series is not finished yet, not shutting down container.")
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
    message = event["message"]
    logging.info(f"Player said: {message}")
    if "!spin" in message:
        logging.info("Spinning")

        server = db.get_server_for_match(event["matchid"])

        with RCON(server.ip, server.port, "pass") as rconn:
            rconn.exec_command("say spinning")
            rconn.exec_command("say done")
            # TODO add random messages


callbacks = {
    "player_say": player_say,
    "map_result": map_result,
    "series_end": series_end,
    "demo_upload_ended": demo_upload_ended,
    "going_live": going_live,
    "round_mvp": csgo_stats_event.stats_event,
    "grenade_thrown": csgo_stats_event.stats_event,
    "player_death": csgo_stats_event.stats_event,
    "hegrenade_detonated": csgo_stats_event.stats_event,
    "molotov_detonated": csgo_stats_event.stats_event,
    "flashbang_detonated": csgo_stats_event.stats_event,
    "smokegrenade_detonated": csgo_stats_event.stats_event,
    "decoygrenade_started": csgo_stats_event.stats_event,
    "bomb_planted": csgo_stats_event.stats_event,
    "bomb_defused": csgo_stats_event.stats_event,
    "bomb_exploded": csgo_stats_event.stats_event
}


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
