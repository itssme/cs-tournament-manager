import logging

from starlette.responses import JSONResponse

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

import json
import os
import random
import time
from typing import Dict

import aiofiles
import requests
from fastapi import Request, Depends

from endpoints import cs2_stats_event, auth_api
from utils.rcon import RCON, get5_status
from utils import db, db_models
from utils.elo import calculate_elo
from utils.utils_funcs import get_body, get_api_login_token


def going_live(event: Dict):
    match: db_models.Match = db_models.Match.select().where(db_models.Match.matchid == event["matchid"]).get()
    match.finished = 0
    match.save()


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
    match.save()

    logging.info(f"Shutting down remote container: server={server.ip}, match_id={match.matchid}")
    res = requests.delete(f"{os.getenv('HTTP_PROTOCOL', 'http://')}{server.ip}/api/match", json={"id": server.id},
                          timeout=60,
                          cookies={"access_token": get_api_login_token()})

    if res.status_code == 200:
        logging.info(
            f"After demo has been uploaded, container running matchid: {match.matchid}, (name={server.container_name}) has been stopped")
    else:
        logging.error(f"Unable to stop container for match: {match}, server: {server} -> {res.text}")


def map_result(event: Dict):
    match: db_models.Match = db_models.Match.select().where(db_models.Match.matchid == event["matchid"]).get()
    if event["winner"]["team"] == "team1":
        match.series_score_team1 += 1
        match.save()
    elif event["winner"]["team"] == "team2":
        match.series_score_team2 += 1
        match.save()
    else:
        logging.error(f"Got a map_result event with no team winning? -> {event}")

    team1: db_models.Team = db_models.Team.select().where(db_models.Team.id == match.team1).get()
    team2: db_models.Team = db_models.Team.select().where(db_models.Team.id == match.team2).get()

    team1_elo = team1.elo
    team2_elo = team2.elo
    logging.info(f"Updating ELO: {team1.elo}, {team2.elo}, {event['team1_score']}, {event['team2_score']}")

    team1.elo, team2.elo = calculate_elo(team1.elo, team2.elo, event["team1_score"], event["team2_score"],
                                         int(db_models.Config.get(db_models.Config.key == "elo_k_factor").value))
    team1.save()
    team2.save()

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
    match.save()


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

        with RCON(str(server.ip.ip), server.port) as rconn:
            rconn.exec_command("say A new challenge has been set for the team that used the command:")
            rconn.exec_command("say " + random.choice(challenges))


callbacks = {
    "player_say": player_say,
    "map_result": map_result,
    "series_end": series_end,
    "demo_upload_ended": demo_upload_ended,
    "going_live": going_live,
    "round_mvp": cs2_stats_event.stats_event,
    "grenade_thrown": cs2_stats_event.stats_event,
    "player_death": cs2_stats_event.stats_event,
    "hegrenade_detonated": cs2_stats_event.stats_event,
    "molotov_detonated": cs2_stats_event.stats_event,
    "flashbang_detonated": cs2_stats_event.stats_event,
    "smokegrenade_detonated": cs2_stats_event.stats_event,
    "decoygrenade_started": cs2_stats_event.stats_event,
    "bomb_planted": cs2_stats_event.stats_event,
    "bomb_defused": cs2_stats_event.stats_event,
    "bomb_exploded": cs2_stats_event.stats_event
}


def set_api_routes(app):
    @app.post("/", dependencies=[Depends(db.get_db)])
    def get5_event(body=Depends(get_body),
                   current_user: db_models.Account = Depends(auth_api.get_admin_user)):
        json_str = body.decode("utf-8")
        event = json.loads(json_str)
        logging.info(f"Event: {event['event']}")
        logging.info(event)

        if event["event"] in callbacks.keys():
            callbacks[event["event"]](event)

        return ""

    @app.post("/demo")
    async def upload_demo(request: Request, current_user: db_models.Account = Depends(auth_api.get_admin_user)):
        if "get5-filename" in request.headers.keys():
            logging.info(f"get5-filename: {request.headers['get5-filename']}")
            filename = os.path.split(request.headers["get5-filename"])[-1]
        else:
            logging.info("No get5-filename header found, using default name")
            filename = f"{time.time()}.dem"

        logging.info(f"Called POST /demo filename: {filename} and matchid: {request.headers['get5-matchid']}")

        async with aiofiles.open(os.path.join(os.getenv("DEMO_FILE_PATH", "/demofiles"), filename), 'wb') as out_file:
            content = await request.body()
            await out_file.write(content)

        logging.info(f"Done writing file: {filename}")
        return {"filename": filename}

    @app.post("/backup")
    async def upload_backup(request: Request, current_user: db_models.Account = Depends(auth_api.get_admin_user)):
        if "get5-filename" in request.headers.keys():
            logging.info(f"get5-filename: {request.headers['get5-filename']}")
            filename = os.path.split(request.headers["get5-filename"])[-1]
        else:
            logging.info("No get5-filename header found, using default name")
            filename = f"{time.time()}.cfg"

        logging.info(f"Called POST /backup filename: {filename} and matchid: {request.headers['get5-matchid']}")

        async with aiofiles.open(os.path.join(os.getenv("BACKUP_FILE_PATH", "/backupfiles"), filename),
                                 'wb') as out_file:
            content = await request.body()
            await out_file.write(content)

        logging.info(f"Done writing file: {filename}")
        return {"filename": filename}

    @app.get("/info", response_class=JSONResponse, dependencies=[Depends(db.get_db)])
    # @cache(namespace="info", expire=1)
    def status(request: Request, current_user: db_models.Account = Depends(auth_api.get_current_user)):
        servers = db_models.Server.select()  # do not call server.update() later! It will overwrite the gslt token

        for server in servers:
            server.gslt_token = None  # avoid leaking gslt tokens

        status_json = []

        for server in servers:
            get5_stats = None
            stats = None
            try:
                get5_stats = get5_status(server.ip.ip, server.port)
                with RCON(server.ip.ip, server.port) as rconn:
                    # need to parse values: CPU   NetIn   NetOut    Uptime  Maps   FPS   Players  Svms    +-ms   ~tick
                    stats = rconn.exec_command("stats")
            except ConnectionRefusedError as e:
                pass

            stats_parsed = [float(value) for value in stats.split("\\n")[1].split(" ") if
                            value != ''] if stats is not None else []

            match = db_models.Match.select().where(db_models.Match.id == server.match).get()
            team_1 = db_models.Team.get(db_models.Team.id == match.team1)
            team_2 = db_models.Team.get(db_models.Team.id == match.team2)

            if get5_stats is None:
                get5_stats = {"gamestate": "unreachable"}

            get5_stats["matchid"] = f"{team_1.name} vs {team_2.name}"

            status_json.append({"id": server.id,
                                "ip": server.ip.ip + ":" + str(server.port),
                                "get5_stats": get5_stats,
                                "stats": stats_parsed,
                                "team1": team_1,
                                "team2": team_2})

        return status_json
