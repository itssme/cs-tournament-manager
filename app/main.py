import json
import logging
import os
import time
from typing import Union

import aiofiles
import requests
from starlette.responses import JSONResponse

import csgo_events
import rcon
from rcon import RCON
from servers import ServerManager
from match_conf_gen import MatchGen
import db

import error_routes
from fastapi import FastAPI, Request, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

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

if os.getenv("MASTER", "1") != "1":
    logging.info("Running as slave instance.")
    if os.getenv("MASTER_IP", None) is None:
        logging.error("MASTER_IP not set.")
        exit(1)

    if os.getenv("MASTER_IP", None) is None:
        logging.error("MASTER_IP not set.")
        exit(1)

    if os.getenv("DB_HOST", None) is None:
        logging.error("DB_HOST not set.")
        exit(1)

    if os.getenv("EXTERNAL_IP", None) is None:
        logging.error("EXTERNAL_IP not set.")
        exit(1)

    logging.info("ENV Variables are: MASTER_IP: %s, DB_HOST: %s, EXTERNAL_IP: %s", os.getenv("MASTER_IP"),
                 os.getenv("DB_HOST"), os.getenv("EXTERNAL_IP"))
    logging.info("Checking if master is online...")

    res = requests.get("http://" + os.getenv("MASTER_IP") + "/api/healthcheck")
    if res.status_code == 200:
        logging.info("Master is online.")
    else:
        logging.error("Master is not online.")
        exit(1)


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
    servers = [host for host in db.get_hosts()]
    return templates.TemplateResponse("config.html", {"request": request, "teams": teams, "servers": servers})


@api.get("/players", response_class=JSONResponse)
async def players(request: Request):
    return [player.to_json() for player in db.get_players()]


@api.get("/teams", response_class=JSONResponse)
async def teams(request: Request):
    return [team.to_json() for team in db.get_teams()]


@api.get("/freeTeams", response_class=JSONResponse)
async def teams(request: Request):
    return [team.to_json() for team in db.get_free_teams()]


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
        get5_stats = rcon.get5_status(server.ip, server.port)

        with RCON(server.ip, server.port, "pass") as rconn:
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
                                "ip": server.ip + ":" + str(server.port),
                                "get5_stats": get5_stats,
                                "stats": stats_parsed,
                                "team1": team_1,
                                "team2": team_2})

    logging.info(f"Requested /info -> {status_json}")
    return status_json


class SlayPlayer(BaseModel):
    player_name: str
    server_ip: Union[str, None] = "host.docker.internal"
    server_port: int


@api.post("/slay", response_class=JSONResponse)
async def slay_player(request: Request, slay: SlayPlayer):
    logging.info(f"Slaying player: {slay.player_name} on server: ip={slay.server_ip} port={slay.server_port}")
    try:
        with RCON(slay.server_ip, slay.server_port, "pass") as rconn:
            logging.info(rconn.exec_command(f"sm_slay {slay.player_name}"))
    except ConnectionError as e:
        logging.error(f"Unable to slay player: {e}")
        return {"error": "Unable to connect to this server"}
    return {"status": 0}


class RconCommand(BaseModel):
    rcon: str
    server_ip: Union[str, None] = "host.docker.internal"
    server_port: int


@api.post("/rcon", response_class=JSONResponse)
async def slay_player(request: Request, rcon_command: RconCommand):
    logging.info(
        f"Running command: {rcon_command.rcon} on server: ip={rcon_command.server_ip} port={rcon_command.server_port}")
    try:
        with RCON(rcon_command.server_ip, rcon_command.server_port, "pass") as rconn:
            res = rconn.exec_command(rcon_command.rcon)
    except ConnectionError as e:
        logging.error(f"Unable to run rcon command: {e}")
        return {"error": "Unable to connect to this server"}
    return res


class ServerID(BaseModel):
    id: int


@api.delete("/match", response_class=JSONResponse)
async def status(request: Request, server: ServerID):
    logging.info(f"Called DELETE /match with server id: {server.id}")
    server_manger.stop_match(server.id)
    return {"status": 0}


class MatchInfo(BaseModel):
    team1: int
    team2: int
    best_of: Union[int, None] = None
    check_auths: Union[bool, None] = None
    host: Union[str, None] = None


@api.post("/match")
async def create_match(request: Request, match: MatchInfo):
    logging.info(
        f"Called POST /match with MatchInfo: Team1: '{match.team1}', Team2: '{match.team2}', "
        f"best_of: '{match.best_of}', 'check_auths: {match.check_auths}', 'host: {match.host}'")

    def create_match_local():
        logging.info("Creating match on master server")

        match_cfg = MatchGen.from_team_ids(match.team1, match.team2, match.best_of)
        if match.check_auths is not None:
            match_cfg.add_cvar("get5_check_auths", "1" if match.check_auths else "0")

        if server_manger.create_match(match_cfg):
            return match_cfg
        else:
            raise HTTPException(status_code=500, detail="Unable to start container")

    def create_match_remote():
        logging.info(f"Creating match on remote server: {match.host} -> {match.json()}")
        res = requests.post(f"http://{match.host}/api/match", json=json.loads(match.json()))

        try:
            match_cfg = res.json()
            return match_cfg
        except Exception as e:
            raise HTTPException(status_code=500,
                                detail=f"Unable to start container on remote host: {match.host}, status={res.status_code}<br>{res.text}")

    if os.getenv("MASTER", "1") == "1" and match.host is None or match.host == "host.docker.internal":
        return create_match_local()
    elif match.host == os.getenv("EXTERNAL_IP", "127.0.0.1"):
        return create_match_local()
    elif match.host is not None:
        return create_match_remote()
    else:
        raise HTTPException(status_code=500, detail=f"Unable to start server on {match.host}")


class TeamInfo(BaseModel):
    name: str
    tag: str


class PlayerInfo(BaseModel):
    steam_id: str
    name: str


class TeamAssignmentInfo(BaseModel):
    team_id: int
    player_id: int


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


@api.get("/teamPlayers")
async def get_team_players(request: Request, team_id: int):
    logging.info(f"Called GET /teamPlayers for team: {team_id}")
    return [team_player.to_json() for team_player in db.get_team_players(team_id)]


@api.post("/teamAssignment")
async def create_team_assignment(request: Request, team_assignment: TeamAssignmentInfo):
    logging.info(
        f"Called POST /teamAssignment with TeamAssignmentInfo: TeamID: '{team_assignment.team_id}', PlayerID: '{team_assignment.player_id}'")
    team = db.get_team_by_id(team_assignment.team_id)
    player = db.get_player(team_assignment.player_id)
    db.insert_team_assignment_if_not_exists(team, player)
    db.update_config()


@api.delete("/teamAssignment")
async def delete_team_assignment(request: Request, team_assignment: TeamAssignmentInfo):
    logging.info(
        f"Called DELETE /teamAssignment with TeamAssignment: TeamID: '{team_assignment.team_id}', PlayerID: '{team_assignment.player_id}'")
    team = db.get_team_by_id(team_assignment.team_id)
    player = db.get_player(team_assignment.player_id)
    db.delete_team_assignment(team, player)
    db.update_config()


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
async def upload_demo(request: Request):
    logging.info(
        f"Called POST /demo -> Header Keys: {request.headers.keys()}")  # 2022-12-23T19:15:14.975986996Z 2022-12-23 19:15:14,975 - root - INFO - Called POST /demo -> Header Keys: ['user-agent', 'get5-version', 'content-type', 'get5-filename', 'get5-matchid', 'get5-mapnumber', 'host', 'accept', 'accept-encoding', 'accept-charset', 'content-length']

    if "Get5-DemoName" in request.headers.keys():
        logging.info(f"Get5-DemoName: {request.headers['Get5-DemoName']}")
        filename = os.path.split(request.headers["Get5-DemoName"])[-1]
    else:
        logging.info("No Get5-DemoName header found, using default name")
        filename = f"{time.time()}.dem"

    logging.info(f"Called POST /demo filename: {filename}")

    async with aiofiles.open(os.path.join(os.getenv("DEMO_FILE_PATH", "/demofiles"), filename), 'wb') as out_file:
        content = await request.body()
        await out_file.write(content)

    logging.info(f"Done writing file: {filename}")
    return {"filename": filename}


@api.get("/healthcheck")
async def healthcheck(request: Request):
    teams = db.get_teams()
    players = db.get_players()
    matches = db.get_matches()
    servers = db.get_servers()
    hosts = db.get_hosts()

    return {"status": "ok"}
