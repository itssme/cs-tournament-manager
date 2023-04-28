import json
import logging
import os
import random
from typing import Dict

import requests
from fastapi import Request, Depends

from endpoints import csgo_stats_event, auth_api
from utils.rcon import RCON
from servers import ServerManager
from utils import db, db_models
from elo import calculate_elo

server_manger: ServerManager = None


def going_live(event: Dict):
    match: db_models.Match = db_models.Match.select().where(db_models.Match.matchid == event["matchid"]).get()
    match.finished = 0
    match.update_attribute("finished")


def demo_upload_ended(event: Dict):
    match: db_models.Match = db_models.Match.select().where(db_models.Match.matchid == event["matchid"]).get()
    if not event["success"]:
        logging.error(
            f"Match: {match.matchid} tried to upload demo, but failed. Demo is not saved and container cannot be shut down.")
        return

    if match.finished != 1:
        logging.info(
            f"Demo upload for match: {match.matchid} but the series is not finished yet, not shutting down container.")
        return

    server: db_models.Server = db.get_server_for_match(match.matchid)

    match.finished = 2
    match.update_attribute("finished")

    if os.getenv("EXTERNAL_IP", "127.0.0.1") != server.ip and server.ip != "host.docker.internal":
        logging.info(f"Shutting down remote container: server={server.ip}, match_id={match.matchid}")
        res = requests.delete(f"{os.getenv('HTTP_PROTOCOL', 'http://')}{server.ip}/api/match", json={"id": server.id},
                              timeout=60,
                              headers=auth_api.login_to_master_headers())  # TODO: fix login by creating token from secret

        if res.status_code == 200:
            logging.info(
                f"After demo has been uploaded, container running matchid: {match.matchid}, (name={server.container_name}) has been stopped")
        else:
            logging.error(f"Unable to stop container for match: {match}, server: {server} -> {res.text}")
    else:
        logging.info(f"Shutting down local container: server={server.ip}, match_id={match.matchid}")
        server_manger.stop_match(server.id, 2)


def map_result(event: Dict):
    match: db_models.Match = db_models.Match.select().where(db_models.Match.matchid == event["matchid"]).get()
    if event["winner"]["team"] == "team1":
        match.series_score_team1 += 1
        match.update_attribute("series_score_team1")
    elif event["winner"]["team"] == "team2":
        match.series_score_team2 += 1
        match.update_attribute("series_score_team2")
    else:
        logging.error(f"Got a map_result event with no team winning? -> {event}")

    team1: db_models.Team = db_models.Team.select().where(db_models.Team.id == match.team1).get()
    team2: db_models.Team = db_models.Team.select().where(db_models.Team.id == match.team2).get()

    team1_elo = team1.elo
    team2_elo = team2.elo
    logging.info(f"Updating ELO: {team1.elo}, {team2.elo}, {event['team1_score']}, {event['team2_score']}")

    team1.elo, team2.elo = calculate_elo(team1.elo, team2.elo, event["team1_score"], event["team2_score"])
    team1.update_attribute("elo")
    team2.update_attribute("elo")

    logging.info(f"Updated ELO: {team1.elo}, {team2.elo}, {event['team1_score']}, {event['team2_score']}")

    server: db_models.Server = db.get_server_for_match(match.matchid)
    with RCON(server.ip, server.port) as rconn:
        rconn.exec_command("say ELO updated:")
        rconn.exec_command(f"say {team1.name}: {team1.elo}, diff: {team1.elo - team1_elo}")
        rconn.exec_command(f"say {team2.name}: {team2.elo}, diff: {team2.elo - team2_elo}")


def series_end(event: Dict):
    match: db_models.Match = db_models.Match.select().where(db_models.Match.matchid == event["matchid"]).get()
    match.series_score_team1 = event["team1_series_score"]
    match.series_score_team2 = event["team2_series_score"]
    match.finished = 1
    match.update_attribute("finished")


def player_say(event: Dict):
    message = event["message"]
    logging.info(f"Player said: {message}")

    challenges = [
        "You have to play with the car mouse",
        "Your whole team can only use the Desert Eagle",
        "Everyone has to switch to another setup",
        "Everyone in your team has to switch headphones with someone else",
        "Everyone in your team has to flip their headset",
        "Your team is not allowed to use voice chat",
        "Everyone has to multiply their sensitivity by 5",
        "Everyone has to divide their sensitivity by 5",
        "Your whole team can only use Shotguns",
        "Your whole team has to set \"cl_draw_only_deathnotices\" to 1",
        "Your whole team must hold down the \"W\" key all the time",
        "Only one person in your team is allowed to fight at once",
        "Your whole team has to play with the \"cl_crosshairsize 0\" set to 0",
        "Your whole team has to mute the game"
    ]

    if "!spin" in message.lower():
        server = db.get_server_for_match(event["matchid"])

        with RCON(server.ip, server.port) as rconn:
            rconn.exec_command("say A new challenge has been set for the team that used the command:")
            rconn.exec_command("say " + random.choice(challenges))


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
    @app.post("/", dependencies=[Depends(db.get_db)])
    async def get5_event(request: Request,
                         current_user=Depends(auth_api.get_current_user)):  # TODO: check if this auth still works
        json_str = await request.body()  # TODO: remove async, but how to access body?
        event = json.loads(json_str)
        logging.info(f"Event: {event['event']}")
        logging.info(event)

        if event["event"] in callbacks.keys():
            callbacks[event["event"]](event)

        return ""


def set_server_manager(server_manager: ServerManager):
    global server_manger
    server_manger = server_manager
