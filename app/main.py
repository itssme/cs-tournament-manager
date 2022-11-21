import logging
from typing import Union

from starlette.responses import JSONResponse

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
    return templates.TemplateResponse("status.html", {"request": request})


@api.get("/info", response_class=JSONResponse)
async def status(request: Request):
    servers = db.get_servers()

    for server in servers:
        server.gslt_token = None

    logging.info(f"Requested /info -> {servers}")
    return servers


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


@api.post("/createMatch")
async def createMatch(request: Request, match: MatchInfo):
    logging.info(
        f"Called /createMatch with MatchInfo: Team1: '{match.team1}', Team2: '{match.team2}', best_of: '{match.best_of}'")

    match_cfg = MatchGen.from_team_ids(match.team1, match.team2, match.best_of)

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
