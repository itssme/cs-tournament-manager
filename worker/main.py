import logging
import os

import docker
from redis import asyncio as aioredis
from fastapi_cache.backends.redis import RedisBackend

from match_conf_gen import MatchGen
from servers import ServerManager

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

from fastapi_cache import FastAPICache

from endpoints import error_routes, auth_api
from utils import db_models, limiter, db_migrations

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from utils.json_objects import *

logging.info("server running")

logging.info("applying migrations")
db_migrations.apply_migrations()
logging.info("applying migrations - done")

# uncomment for dev stuff
# db_models.Account.create(username="admin", password=get_password_hash("admin"), verification_code="", verified=1, role="admin")

app = FastAPI()
limiter.init_limiter(app)

api = FastAPI()
public = FastAPI()
csgo_api = FastAPI()
auth = FastAPI()
limiter.init_limiter(auth)

app.mount("/api", api)

api.mount("/csgo", csgo_api)
app.mount("/auth", auth)

templates = Jinja2Templates(directory="templates")

error_routes.set_routes(app, templates, False)
error_routes.set_api_routes(api, False)
auth_api.set_api_routes(auth, templates)

server_manager = ServerManager()


@app.on_event("startup")
async def startup():
    redis = aioredis.from_url("redis://redis", encoding="utf8", decode_responses=True)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")


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
        new_match = server_manager.create_match(match_cfg,
                                                loadbackup_url=match.from_backup_url)
    else:
        new_match = server_manager.create_match(match_cfg)

    if new_match[0]:
        return {"ip": os.getenv('EXTERNAL_IP', '127.0.0.1'), "port": new_match[1],
                "match_id": match_cfg["matchid"]}
    else:
        raise HTTPException(status_code=500, detail="Unable to start container")


@api.get("/healthcheck")
async def healthcheck(request: Request):
    client = docker.from_env()
    try:
        client.images.get("get5-csgo")
        return {"status": "ok"}
    except docker.errors.ImageNotFound:
        raise HTTPException(status_code=500, detail="CSGO Docker image not found")
