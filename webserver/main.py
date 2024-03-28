import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

import os

from redis import asyncio as aioredis
from fastapi_cache.backends.redis import RedisBackend

import json

import requests
from fastapi_cache import FastAPICache
from starlette.responses import JSONResponse, RedirectResponse, FileResponse

from endpoints import cs_events, error_routes
from utils.rcon import RCON
from utils import db, limiter, db_migrations

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_cache.decorator import cache

from utils.json_objects import *

logging.info("server running")

logging.info("applying migrations")
db_migrations.apply_migrations()
logging.info("applying migrations - done")

app = FastAPI()
limiter.init_limiter(app)

api = FastAPI()
public = FastAPI()
cs_api = FastAPI()

app.mount("/api", api)

api.mount("/cs", cs_api)

app.mount("/public", public)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

error_routes.set_routes(app, templates, False)
error_routes.set_api_routes(api, False)
cs_events.set_api_routes(cs_api)


@app.on_event("startup")
async def startup():
    redis = aioredis.from_url("redis://redis", encoding="utf8", decode_responses=True)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")


@app.get("/")
def rcon(request: Request):
    return RedirectResponse(url="/auth/login")


@api.post("/match", dependencies=[Depends(db.get_db)])
def create_match(request: Request):
    pass


@api.delete("/match", dependencies=[Depends(db.get_db)])
def delete_match(request: Request):
    pass


@api.post("/host", dependencies=[Depends(db.get_db)])
def create_host(request: Request):
    pass


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


@api.get("/match/{match_id}")
async def get_matchjson(match_id: int):
    # TODO: return match_json
    return {"match_id": match_id}


@api.get("/healthcheck")
async def healthcheck(request: Request):
    return {"status": "ok"}
