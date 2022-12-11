import json
import logging
import os
import time
from threading import Thread
from typing import Union

import aiofiles
from starlette.responses import JSONResponse

import csgo_events
import rcon
from rcon import RCON
from servers import ServerManager
from match_conf_gen import MatchGen
import db

import error_routes
from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logging.info("server running")
logging.getLogger('pika').setLevel(logging.WARNING)

app = FastAPI()
api = FastAPI()
csgo_api = FastAPI()
app.mount("/api", api)
api.mount("/csgo", csgo_api)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

db.setup_db()

error_routes.set_routes(app, templates)
error_routes.set_api_routes(api)
csgo_events.set_api_routes(csgo_api)

server_manger = ServerManager()


@app.get("/", response_class=RedirectResponse)
async def redirect_index():
    return "/status"


@app.get("/status", response_class=HTMLResponse)
async def status(request: Request):
    gameserver = [server.to_json() for server in db.get_servers()]
    return templates.TemplateResponse("status.html", {"request": request, "gameserver": gameserver})


@app.get("/config", response_class=HTMLResponse)
async def status(request: Request):
    teams = [team.to_json() for team in db.get_teams()]
    return templates.TemplateResponse("config.html", {"request": request, "teams": teams})


@api.get("/players", response_class=JSONResponse)
async def players(request: Request):
    return [player.to_json() for player in db.get_players()]


@api.get("/teams", response_class=JSONResponse)
async def teams(request: Request):
    return [team.to_json() for team in db.get_teams()]


@api.get("/servers", response_class=JSONResponse)
async def servers(request: Request):
    return [server.to_json() for server in db.get_servers()]


@api.get("/matches", response_class=JSONResponse)
async def matches(request: Request):
    return [match.to_json() for match in db.get_matches()]


@api.get("/info", response_class=JSONResponse)
async def status(request: Request):
    servers = db.get_servers()

    for server in servers:
        server.gslt_token = None

    status_json = []

    for server in servers:
        logging.info(f"Collecting stats for server: {server}")
        get5_stats = rcon.get5_status(server.port)

        with RCON("host.docker.internal", server.port, "pass") as rconn:
            # logging.info(rconn.exec_command("sm_slay Jöl"))
            # logging.info(rconn.exec_command("cvarlist"))

            # need to parse values: CPU   NetIn   NetOut    Uptime  Maps   FPS   Players  Svms    +-ms   ~tick
            stats = rconn.exec_command("stats")
            stats_parsed = [float(value) for value in stats.split("\\n")[1].split(" ") if value != '']

            match = db.get_match_by_id(server.match)
            team_1 = db.get_team_by_id(match.team1)
            team_2 = db.get_team_by_id(match.team2)

            get5_stats["matchid"] = f"{team_1.name} vs {team_2.name}"

            status_json.append({"id": server.id,
                                "ip": "127.0.0.1" + ":" + str(server.port),
                                "get5_stats": get5_stats,
                                "stats": stats_parsed,
                                "team1": team_1,
                                "team2": team_2})

    logging.info(f"Requested /info -> {status_json}")
    return status_json


class SlayPlayer(BaseModel):
    player_name: str
    server_port: int


@api.get("/slay", response_class=JSONResponse)
async def slay_player(request: Request, slay: SlayPlayer):
    logging.info(f"Slaying player: {slay.player_name} on server: {slay.server_port}")
    with RCON("host.docker.internal", slay.server_port, "pass") as rconn:
        logging.info(rconn.exec_command(f"sm_slay {slay.player_name}"))
    return {"status": 0}


class ServerID(BaseModel):
    id: int


@api.post("/stopMatch", response_class=JSONResponse)
async def status(request: Request, server: ServerID):
    logging.info(f"Called /stopMatch with server id: {server.id}")
    server_manger.stop_match(server.id)
    return {"status": 0}


class MatchInfo(BaseModel):
    team1: int
    team2: int
    best_of: Union[int, None] = None
    check_auths: Union[bool, None] = None


@api.post("/createMatch")
async def create_match(request: Request, match: MatchInfo):
    logging.info(
        f"Called /createMatch with MatchInfo: Team1: '{match.team1}', Team2: '{match.team2}', "
        f"best_of: '{match.best_of}', 'check_auths: {match.check_auths}'")

    match_cfg = MatchGen.from_team_ids(match.team1, match.team2, match.best_of)
    if match.check_auths is not None:
        match_cfg.add_cvar("get5_check_auths", "1" if match.check_auths else "0")

    server_manger.create_match(match_cfg)

    return match_cfg


class TeamInfo(BaseModel):
    name: str
    tag: str


class PlayerInfo(BaseModel):
    steam_id: str
    name: str


@api.post("/team")
async def create_team(request: Request, team: TeamInfo):
    logging.info(
        f"Called POST /team with TeamInfo: TeamName: '{team.name}', TeamTag: '{team.tag}'")

    db.insert_team_or_set_id(db.Team(tag=team.tag, name=team.name, id=0))

    db.update_config()


@api.post("/player")
async def create_player(request: Request, player: PlayerInfo):
    logging.info(f"Called POST /player with PlayerInfo: PlayerName: '{player.name}', SteamID: '{player.steam_id}'")
    db.insert_player_or_set_id(db.Player(name=player.name, steam_id=player.steam_id))


@api.delete("/team")
async def delete_team(request: Request, team_id: int):
    logging.info(f"Called DELETE /team player_id: {team_id}")

    db.delete_team(team_id)
    db.update_config()


@api.delete("/player")
async def delete_player(request: Request, player_id: int):
    logging.info(f"Called DELETE /player player_id: {player_id}")
    db.delete_player(player_id)

    db.update_config()


@api.post("/demo")
async def upload_demo(file: UploadFile):
    logging.info(f"Called POST /demo filename: {file.filename}")

    async with aiofiles.open(os.getenv("DEMO_FILE_PATH", "/demofiles"), 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)

    return {"filename": file.filename}
