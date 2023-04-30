import logging

from redis import asyncio as aioredis
from fastapi_cache.backends.redis import RedisBackend

from endpoints.auth_api import get_password_hash

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

import json

import requests
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache
from starlette.responses import JSONResponse, RedirectResponse

from endpoints import csgo_events, error_routes, config_webinterface_routes, auth_api
from utils.rcon import RCON
from servers import ServerManager
from utils import db, db_models, limiter, db_migrations

from fastapi import FastAPI, Request, HTTPException, Depends
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
app.mount("/public", public)
app.mount("/auth", auth)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

server_manger = ServerManager()
csgo_events.set_server_manager(server_manger)

error_routes.set_routes(app, templates)
error_routes.set_api_routes(api)
csgo_events.set_api_routes(csgo_api)
config_webinterface_routes.set_routes(public, templates)
auth_api.set_api_routes(auth, templates)


@app.on_event("startup")
async def startup():
    redis = aioredis.from_url("redis://redis", encoding="utf8", decode_responses=True)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")


@app.get("/")
def rcon(request: Request):
    return RedirectResponse(url="/auth/login")


@api.post("/rcon", response_class=JSONResponse, dependencies=[Depends(db.get_db)])
def rcon(request: Request, rcon_command: RconCommand,
         current_user: db_models.Account = Depends(auth_api.get_admin_user)):
    logging.info(
        f"Running command: {rcon_command.rcon} on server: ip={rcon_command.server_ip} port={rcon_command.server_port}")
    try:
        with RCON(rcon_command.server_ip, rcon_command.server_port) as rconn:
            res = rconn.exec_command(rcon_command.rcon)
    except ConnectionError as e:
        logging.error(f"Unable to run rcon command: {e}")
        return {"error": "Unable to connect to this server"}
    return res


@api.post("/pause", response_class=JSONResponse, dependencies=[Depends(db.get_db)])
def pause(request: Request, server_id: ServerID,
          current_user: db_models.Account = Depends(auth_api.get_admin_user)):
    logging.info(f"Running command: pause on server: id={server_id.id}")

    server = db_models.Server.select().where(db_models.Server.id == server_id.id).get_or_none()
    if server is None:
        logging.error(f"Unable to find server with id: {server_id.id}")
        raise HTTPException(status_code=404, detail="Server not found")

    try:
        with RCON(server.ip, server.port) as rconn:
            res = rconn.exec_command("sm_pause")
    except ConnectionError as e:
        logging.error(f"Unable to run pause rcon command: {e}")
        return {"error": "Unable to connect to this server"}
    return res


@api.post("/unpause", response_class=JSONResponse, dependencies=[Depends(db.get_db)])
def unpause(request: Request, server_id: ServerID,
            current_user: db_models.Account = Depends(auth_api.get_admin_user)):
    logging.info(f"Running command: unpause on server: id={server_id.id}")

    server = db_models.Server.select().where(db_models.Server.id == server_id.id).get_or_none()
    if server is None:
        logging.error(f"Unable to find server with id: {server_id.id}")
        raise HTTPException(status_code=404, detail="Server not found")

    try:
        with RCON(server.ip, server.port) as rconn:
            res = rconn.exec_command("sm_unpause")
    except ConnectionError as e:
        logging.error(f"Unable to run unpause rcon command: {e}")
        return {"error": "Unable to connect to this server"}
    return res


@api.post("/match", dependencies=[Depends(db.get_db)])
def create_match(request: Request, match: MatchInfo,
                 current_user: db_models.Account = Depends(auth_api.get_admin_user)):
    logging.info(
        f"Called POST /match with MatchInfo: Team1: '{match.team1}', Team2: '{match.team2}', "
        f"best_of: '{match.best_of}', 'check_auths: {match.check_auths}', 'host: {match.host}'")

    if match.host is None:
        match.host = db.get_least_used_host_ips()
        logging.info(f"No host specified, using least used host -> {match.host}")

    logging.info(f"Creating match on remote server: {match.host} -> {match.json()}")
    if request.headers.get("Authorization", None) is None:
        res = requests.post(f"http://{match.host}/api/match", json=json.loads(match.json()),
                            cookies={"access_token": request.cookies.get("access_token")})
    else:
        res = requests.post(f"http://{match.host}/api/match", json=json.loads(match.json()),
                            headers={"Authorization": request.headers["Authorization"]})

    try:
        response_data = res.json()
        return response_data
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Unable to start container on remote host: {match.host}, status={res.status_code}<br>{res.text}")


@api.get("/healthcheck")
async def healthcheck(request: Request):
    return {"status": "ok"}
