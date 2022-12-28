import json
import logging
import os
import time
from typing import Union

import aiofiles
import requests
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache
from starlette.responses import JSONResponse, FileResponse

from endpoints import csgo_events, error_routes, config_webinterface_routes, public_routes
from endpoints.csgo_stats_event import event_map
from rcon import RCON
from rcon import get5_status
from servers import ServerManager
from match_conf_gen import MatchGen
from sql import db, db_stats

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pydantic import BaseModel

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logging.info("server running")
logging.getLogger('pika').setLevel(logging.WARNING)

app = FastAPI()
api = FastAPI()
public = FastAPI()
csgo_api = FastAPI()
app.mount("/api", api)
api.mount("/csgo", csgo_api)
app.mount("/public", public)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

db.setup_db()

error_routes.set_routes(app, templates)
error_routes.set_api_routes(api)
csgo_events.set_api_routes(csgo_api)
config_webinterface_routes.set_routes(app, templates)
public_routes.set_routes(public, templates)

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


@app.on_event("startup")
async def startup():
    FastAPICache.init(InMemoryBackend())


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


@api.get("/status", response_class=JSONResponse)
@cache(namespace="status", expire=4)
async def status(request: Request):
    matches = []
    teams = []

    matches_db = db.get_matches()
    for match in matches_db:
        if match.finished <= 0:
            score = [0, 0]
            team1 = db.get_team_by_id(match.team1)
            team2 = db.get_team_by_id(match.team2)
            server = db.get_server_for_match(match.matchid)

            try:
                get5_stats = get5_status(server.ip, server.port)
                if "team1" in get5_stats.keys() and "team2" in get5_stats.keys():
                    score = [get5_stats["team1"]["current_map_score"], get5_stats["team2"]["current_map_score"]]
            except ConnectionRefusedError as e:
                get5_stats = {"gamestate": "unreachable"}

            matches.append({"score": score, "teamnames": [team1.name, team2.name], "team_elo": [team1.elo, team2.elo],
                            "server_ip": f"{server.ip}:{server.port}",
                            "status": get5_stats["gamestate"]})

    for team in db.get_teams():
        if team.competing != 2:
            wins = 0
            losses = 0
            draws = 0  # currently not used

            for match in matches_db:
                if 1 <= match.finished <= 2:
                    if match.team1 == team.id:
                        wins += match.series_score_team1
                        losses += match.series_score_team2
                    elif match.team2 == team.id:
                        wins += match.series_score_team2
                        losses += match.series_score_team1

            teams.append({"teamname": team.name, "elo": team.elo, "wins": wins, "losses": losses, "draws": draws})

    # sort teams by elo
    teams.sort(key=lambda x: x["elo"], reverse=True)

    return {"matches": matches, "teams": teams}

    # for testing
    # return {"matches": [
    #     {"score": [5, 14], "teamnames": ["airplebs", "Faceit LVL 1"],
    #      "server_ip": "10.20.0.20:27015", "team_elo": [1406, 1326], "status": "running"},
    #     {"score": [4, 8], "teamnames": ["Unranked", "Die Globale Elite"],
    #      "server_ip": "10.20.0.20:27027", "team_elo": [1203, 1260], "status": "running"}
    # ], "teams": [{"teamname": "airplebs", "elo": 1406, "wins": 5, "losses": 2, "draws": 0},
    #              {"teamname": "Faceit LVL 1", "elo": 1326, "wins": 3, "losses": 4, "draws": 0},
    #              {"teamname": "Die Globale Elite", "elo": 1260, "wins": 4, "losses": 3, "draws": 0},
    #              {"teamname": "Unranked", "elo": 1203, "wins": 2, "losses": 5, "draws": 0}
    #              ]}


@api.get("/stats", response_class=JSONResponse)
@cache(namespace="stats", expire=1)
async def stats(request: Request):
    stats = {}

    for event in event_map.keys():
        stats[event] = {}
        stats[event]["occurred"] = db_stats.count_event_type(event_map[event])
        stats[event]["player"] = db_stats.player_with_most(event_map[event])

    return stats


@api.get("/info", response_class=JSONResponse)
@cache(namespace="info", expire=1)
async def status(request: Request):
    servers = db.get_servers()

    for server in servers:
        server.gslt_token = None  # avoid leaking gslt tokens

    status_json = []

    for server in servers:
        get5_stats = None
        stats = None
        try:
            get5_stats = get5_status(server.ip, server.port)
            with RCON(server.ip, server.port, "pass") as rconn:
                # logging.info(rconn.exec_command("sm_slay Jöl"))
                # logging.info(rconn.exec_command("cvarlist"))

                # need to parse values: CPU   NetIn   NetOut    Uptime  Maps   FPS   Players  Svms    +-ms   ~tick
                stats = rconn.exec_command("stats")
        except ConnectionRefusedError as e:
            pass

        stats_parsed = [float(value) for value in stats.split("\\n")[1].split(" ") if
                        value != ''] if stats is not None else []

        match = db.get_match_by_id(server.match)
        team_1 = db.get_team_by_id(match.team1)
        team_2 = db.get_team_by_id(match.team2)

        if get5_stats is None:
            get5_stats = {"gamestate": "unreachable"}

        get5_stats["matchid"] = f"{team_1.name} vs {team_2.name}"

        status_json.append({"id": server.id,
                            "ip": server.ip + ":" + str(server.port),
                            "get5_stats": get5_stats,
                            "stats": stats_parsed,
                            "team1": team_1,
                            "team2": team_2})

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
async def rcon(request: Request, rcon_command: RconCommand):
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


@api.post("/pause", response_class=JSONResponse)
async def status(request: Request, server: ServerID):
    logging.info(f"Running command: pause on server: id={server.id}")

    server = db.get_server_by_id(server.id)
    try:
        with RCON(server.ip, server.port, "pass") as rconn:
            res = rconn.exec_command("sm_pause")
    except ConnectionError as e:
        logging.error(f"Unable to run pause rcon command: {e}")
        return {"error": "Unable to connect to this server"}
    return res


@api.post("/unpause", response_class=JSONResponse)
async def status(request: Request, server: ServerID):
    logging.info(f"Running command: unpause on server: id={server.id}")

    server = db.get_server_by_id(server.id)
    try:
        with RCON(server.ip, server.port, "pass") as rconn:
            res = rconn.exec_command("sm_unpause")
    except ConnectionError as e:
        logging.error(f"Unable to run unpause rcon command: {e}")
        return {"error": "Unable to connect to this server"}
    return res


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

    if match.host is None:
        match.host = db.get_least_used_host_ips()
        logging.info(f"No host specified, using least used host -> {match.host}")

    def create_match_local():
        logging.info(f"Creating match on this {os.getenv('EXTERNAL_IP', '127.0.0.1')} server")

        match_cfg = MatchGen.from_team_ids(match.team1, match.team2, match.best_of)
        if match.check_auths is not None:
            match_cfg.add_cvar("get5_check_auths", "1" if match.check_auths else "0")

        new_match = server_manger.create_match(match_cfg)
        if new_match[0]:
            return {"ip": os.getenv('EXTERNAL_IP', '127.0.0.1'), "port": new_match[1],
                    "match_id": match_cfg["matchid"]}
        else:
            raise HTTPException(status_code=500, detail="Unable to start container")

    def create_match_remote():
        logging.info(f"Creating match on remote server: {match.host} -> {match.json()}")
        res = requests.post(f"http://{match.host}/api/match", json=json.loads(match.json()))

        try:
            response_data = res.json()
            return response_data
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


class CompetingInfo(BaseModel):
    team_id: int
    competing: int


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


@api.post("/competing", response_class=JSONResponse)
async def set_competing(request: Request, competing_info: CompetingInfo):
    team = db.get_team_by_id(competing_info.team_id)
    team.competing = competing_info.competing
    team.update_attribute("competing")


@api.delete("/player")
async def delete_player(request: Request, player_id: int):
    logging.info(f"Called DELETE /player player_id: {player_id}")
    db.delete_player(player_id)
    db.update_config()


@api.post("/demo")
async def upload_demo(request: Request):
    logging.info(
        f"Called POST /demo -> Header Keys: {request.headers.keys()}")  # 2022-12-23T19:15:14.975986996Z 2022-12-23 19:15:14,975 - root - INFO - Called POST /demo -> Header Keys: ['user-agent', 'get5-version', 'content-type', 'get5-filename', 'get5-matchid', 'get5-mapnumber', 'host', 'accept', 'accept-encoding', 'accept-charset', 'content-length']

    if "get5-filename" in request.headers.keys():
        logging.info(f"get5-filename: {request.headers['get5-filename']}")
        filename = os.path.split(request.headers["get5-filename"])[-1]
    else:
        logging.info("No get5-filename header found, using default name")
        filename = f"{time.time()}.dem"

    logging.info(f"Called POST /demo filename: {filename}")

    async with aiofiles.open(os.path.join(os.getenv("DEMO_FILE_PATH", "/demofiles"), filename), 'wb') as out_file:
        content = await request.body()
        await out_file.write(content)

    logging.info(f"Done writing file: {filename}")
    return {"filename": filename}


@api.get("/demo/{filename}")
async def get_demo(filename: str):
    logging.info(f"Called GET /demo filename: {filename}")
    filename = os.path.split(filename)[-1]
    return FileResponse(os.path.join(os.getenv("DEMO_FILE_PATH", "/demofiles"), filename))


@api.get("/healthcheck")
async def healthcheck(request: Request):
    teams = db.get_teams()
    players = db.get_players()
    matches = db.get_matches()
    servers = db.get_servers()
    hosts = db.get_hosts()

    return {"status": "ok"}
