import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

import os

from redis import asyncio as aioredis
from fastapi_cache.backends.redis import RedisBackend

from endpoints.auth_api import get_password_hash

import json

import requests
from fastapi_cache import FastAPICache
from starlette.responses import JSONResponse, RedirectResponse, FileResponse

from endpoints import csgo_events, error_routes, config_webinterface_routes, auth_api, team_api
from utils.rcon import RCON
from utils import db, db_models, limiter, db_migrations

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_cache.decorator import cache

from utils.json_objects import *

logging.info("server running")

logging.info("applying migrations")
db_migrations.apply_migrations()
logging.info("applying migrations - done")

# uncomment for dev stuff
# db_models.Account.create(username="admin@admin.com", password=get_password_hash("admin"), verification_code="", verified=1, role="admin")

app = FastAPI()
limiter.init_limiter(app)

api = FastAPI()
public = FastAPI()
csgo_api = FastAPI()
team = FastAPI()
auth = FastAPI()
limiter.init_limiter(auth)

app.mount("/api", api)

api.mount("/csgo", csgo_api)
api.mount("/team", team)

app.mount("/public", public)
app.mount("/auth", auth)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

error_routes.set_routes(app, templates, False)
error_routes.set_api_routes(api, False)
csgo_events.set_api_routes(csgo_api)
team_api.set_api_routes(team, cache)
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

    if match.host is None or match.host == "None":
        try:
            match.host = db.get_least_used_host_ips()
        except ValueError as e:
            raise HTTPException(status_code=404, detail="No hosts available")
        logging.info(f"No host specified, using least used host -> {match.host}")

    host = db_models.Host.select().where(db_models.Host.ip == match.host).get_or_none()
    if host is None:
        logging.error(f"Unable to find host with ip: {match.host}")
        raise HTTPException(status_code=404, detail="Host not found")

    match.host = f"{host.ip}:{host.port}"

    logging.info(f"Creating match on remote server: {match.host} -> {match.json()}")
    if request.headers.get("Authorization", None) is None:
        res = requests.post(f"{os.getenv('HTTP_PROTOCOL', 'http://')}{match.host}/api/match",
                            json=json.loads(match.json()),
                            cookies={"access_token": request.cookies.get("access_token")})
    else:
        res = requests.post(f"{os.getenv('HTTP_PROTOCOL', 'http://')}{match.host}/api/match",
                            json=json.loads(match.json()),
                            headers={"Authorization": request.headers["Authorization"]})

    try:
        response_data = res.json()
        return response_data
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Unable to start container on remote host: {match.host}, status={res.status_code}<br>{res.text}")


@api.delete("/match", response_class=JSONResponse, dependencies=[Depends(db.get_db)])
def status(request: Request, server: ServerID, current_user: db_models.Account = Depends(auth_api.get_admin_user)):
    logging.info(f"Called DELETE /match with server id: {server.id}")

    server_db = db_models.Server.select().where(db_models.Server.id == server.id).get_or_none()
    host = db_models.Host.select().where(db_models.Host.ip == server_db.ip).get_or_none()

    res = requests.delete(f"{os.getenv('HTTP_PROTOCOL', 'http://')}{host.ip}:{host.port}/api/match",
                          json={"id": server.id},
                          cookies={"access_token": request.cookies.get("access_token")})

    if res.status_code == 200:
        return {"status": "ok"}
    else:
        raise HTTPException(status_code=500,
                            detail=f"Unable to stop container on remote host: {host.ip}:{host.port}, status={res.status_code}<br>{res.text}")


@api.post("/host", dependencies=[Depends(db.get_db)])
def create_host(request: Request, host: HostInfo,
                current_user: db_models.Account = Depends(auth_api.get_admin_user)):
    logging.info(f"Called POST /host with Host: Ip: '{host.ip}', Port: '{host.port}'")

    try:
        res = requests.get(f"{os.getenv('HTTP_PROTOCOL', 'http://')}{host.ip}:{host.port}/api/healthcheck", timeout=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unable to connect to host: {host.ip}:{host.port} ({e})")

    if res.status_code == 200:
        db_models.Host.create(ip=host.ip, port=host.port)
        return {"status": "ok"}
    else:
        raise HTTPException(status_code=500,
                            detail=f"Unable to connect to host: {host.ip}:{host.port} , status={res.status_code}<br>{res.text}")


@api.get("/demo/{filename}")
async def get_demo(filename: str):
    logging.info(f"Called GET /demo filename: {filename}")
    filename = os.path.split(filename)[-1]
    return FileResponse(os.path.join(os.getenv("DEMO_FILE_PATH", "/demofiles"), filename))


@api.get("/backup/{filename}")
async def get_backup(request: Request, filename: str):
    logging.info(f"Called GET /backup filename: {filename}")
    filename = os.path.split(filename)[-1]
    return FileResponse(os.path.join(os.getenv("BACKUP_FILE_PATH", "/backupfiles"), filename))


@api.get("/healthcheck")
async def healthcheck(request: Request):
    return {"status": "ok"}
