import json
import logging
import os
import time
from typing import Union

from utils.servers import ServerManager
from utils.match_conf_gen import MatchGen
from utils import db
from functools import wraps

from utils import error_routes
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


class MatchInfo(BaseModel):
    team1: int
    team2: int
    best_of: Union[int, None] = None


@api.post("/createMatch")
async def createMatch(request: Request, match: MatchInfo):
    match_json = jsonable_encoder(match)

    match_cfg = MatchGen.from_team_ids(match_json["team1"], match_json["team2"], match_json["best_of"])

    server_manger.create_match(match_cfg)

    return match_cfg
