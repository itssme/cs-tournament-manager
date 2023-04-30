import logging

from redis import asyncio as aioredis
from fastapi_cache.backends.redis import RedisBackend

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

import json
import os

import requests
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache
from starlette.responses import JSONResponse

from endpoints import csgo_events, error_routes, config_webinterface_routes, public_routes, api_liveinfos, auth_api
from endpoints.db_endpoints import get
from utils.rcon import RCON
from servers import ServerManager
from match_conf_gen import MatchGen
from utils import db, db_models

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from utils.json_objects import *

logging.info("server running")

app = FastAPI()
api = FastAPI()
auth = FastAPI()
app.mount("/api", api)
app.mount("/auth", auth)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

server_manger = ServerManager()
csgo_events.set_server_manager(server_manger)

error_routes.set_routes(app, templates)
error_routes.set_api_routes(api)
auth_api.set_api_routes(auth, templates)


@api.post("/match")
async def create_match(request: Request, match: MatchInfo):
    logging.info(
        f"Called POST /match with MatchInfo: Team1: '{match.team1}', Team2: '{match.team2}', "
        f"best_of: '{match.best_of}', 'check_auths: {match.check_auths}', 'host: {match.host}'")

    logging.info(f"Creating match on this {os.getenv('EXTERNAL_IP', '127.0.0.1')} server")
    if match.from_backup_url is not None:
        logging.info(f"Creating match from backup: {match.from_backup_url}")
        match_id = match.from_backup_url.replace("_map", "_match").split("_match")[1]
        match_old = db_models.Match.select().where(db_models.Match.matchid == match_id).get_or_none()
        if match_old is None:
            logging.error(f"Unable to find match with id: {match_id}")
            raise HTTPException(status_code=404, detail="Match not found")

        match.team1 = match_old.team1
        match.team2 = match_old.team2
        match.best_of = match_old.best_out_of

        match_old.finished = 3
        match_old.save()
        match.from_backup_url = f"http://{os.getenv('MASTER_IP', '127.0.0.1')}/api/backup/" + match.from_backup_url
        # TODO: delete server in db if exists
    else:
        logging.info(f"Creating new match not using any backup")

    match_cfg = MatchGen.from_team_ids(match.team1, match.team2, match.best_of)
    if match.check_auths is not None:
        match_cfg.add_cvar("get5_check_auths", 1 if match.check_auths else 0)

    logging.info(match_cfg)
    if match.from_backup_url is not None:
        match_cfg.set_match_id(match_id)
        new_match = server_manger.create_match(match_cfg,
                                               loadbackup_url=match.from_backup_url)
    else:
        new_match = server_manger.create_match(match_cfg)

    if new_match[0]:
        return {"ip": os.getenv('EXTERNAL_IP', '127.0.0.1'), "port": new_match[1],
                "match_id": match_cfg["matchid"]}
    else:
        raise HTTPException(status_code=500, detail="Unable to start container")


@api.get("/healthcheck")
async def healthcheck(request: Request):
    return {"status": "ok"}
