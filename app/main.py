import json
import logging
import time
from threading import Thread
from typing import Union

from starlette.responses import JSONResponse

from rcon import RCON
from servers import ServerManager
from match_conf_gen import MatchGen
import db

import error_routes
from fastapi import FastAPI, Request
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
app.mount("/api", api)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

db.setup_db()

error_routes.set_routes(app, templates)
error_routes.set_api_routes(api)

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


@app.get("/teams", response_class=JSONResponse)
async def teams(request: Request):
    return [team.to_json() for team in db.get_teams()]


@app.get("/servers", response_class=JSONResponse)
async def servers(request: Request):
    return [server.to_json() for server in db.get_servers()]


@app.get("/matches", response_class=JSONResponse)
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
        with RCON("host.docker.internal", server.port, "pass") as rconn:
            # logging.info(rconn.exec_command("sm_slay Jöl"))
            # logging.info(rconn.exec_command("cvarlist"))

            # need to parse values: CPU   NetIn   NetOut    Uptime  Maps   FPS   Players  Svms    +-ms   ~tick
            stats = rconn.exec_command("stats")

            get5_stats: str = rconn.exec_command("get5_status")
            get5_stats = get5_stats[get5_stats.find("{"):(get5_stats.rfind("}") + 1)].replace("\\n", "")
            get5_stats = json.loads(get5_stats)

            stats_parsed = [float(value) for value in stats.split("\\n")[1].split(" ") if value != '']

            status_json.append({"id": server.id,
                                "ip": "127.0.0.1" + ":" + str(server.port),
                                "get5_stats": get5_stats,
                                "stats": stats_parsed})

    logging.info(f"Requested /info -> {status_json}")
    return status_json


class ServerID(BaseModel):
    id: int


@api.post("/stopMatch", response_class=JSONResponse)
async def status(request: Request, server: ServerID):
    # TODO: extract demo files from the container, should be located at: /home/user/csgo-server/csgo/demos
    logging.info(f"Called /stopMatch with server id: {server.id}")
    server_manger.stop_match(server.id)
    return {"status": 0}


class MatchInfo(BaseModel):
    team1: int
    team2: int
    best_of: Union[int, None] = None
    check_auths: Union[bool, None] = None


@api.post("/createMatch")
async def createMatch(request: Request, match: MatchInfo):
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


@api.post("/createTeam")
async def createTeam(request: Request, team: TeamInfo):
    logging.info(
        f"Called /createTeam with TeamInfo: TeamName: '{team.name}', TeamTag: '{team.tag}'")

    db.insert_team_or_set_id(db.Team(tag=team.tag, name=team.name, id=0))

    db.update_config()


def elo_updater():
    while True:
        time.sleep(1)
        # TODO: check if a match is over
        # TODO: update elo


elo_update_thread = Thread(target=elo_updater)
elo_update_thread.setDaemon(daemonic=True)
elo_update_thread.start()
