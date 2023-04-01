import logging
import os

from playhouse.shortcuts import model_to_dict
from starlette.responses import JSONResponse, FileResponse
from fastapi import FastAPI, Request, HTTPException, Depends

from utils import db_models, db


def set_api_routes(app, cache, server_manger):
    @app.get("/players", response_class=JSONResponse)
    async def players(request: Request):
        return [model_to_dict(player, recurse=False) for player in db_models.Player.select()]

    @app.get("/teams", response_class=JSONResponse)
    async def teams(request: Request):
        return [model_to_dict(team, recurse=False) for team in db_models.Team.select()]

    @app.get("/teams/free", response_class=JSONResponse)
    async def teams(request: Request):
        return [model_to_dict(team, recurse=False) for team in db.get_free_teams()]

    @app.get("/servers", response_class=JSONResponse)
    async def servers(request: Request):
        return [model_to_dict(server) for server in db_models.Server.select()]

    @app.get("/matches", response_class=JSONResponse)
    async def matches(request: Request):
        return [model_to_dict(match, recurse=False) for match in db_models.Match.select()]

    @app.get("/demo/{filename}")
    async def get_demo(filename: str):
        logging.info(f"Called GET /demo filename: {filename}")
        filename = os.path.split(filename)[-1]
        return FileResponse(os.path.join(os.getenv("DEMO_FILE_PATH", "/demofiles"), filename))

    @app.get("/backup/{filename}")
    async def get_backup_file(request: Request, filename: str):
        logging.info(f"Called GET /backup filename: {filename}")
        filename = os.path.split(filename)[-1]
        return FileResponse(os.path.join(os.getenv("BACKUP_FILE_PATH", "/backupfiles"), filename))

    @app.get("/backup")
    async def list_backup_files(request: Request):
        logging.info(f"Called GET /backup")
        return os.listdir(os.getenv("BACKUP_FILE_PATH", "/backupfiles"))
