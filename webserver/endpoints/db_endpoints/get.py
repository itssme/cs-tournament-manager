import logging
import os

from playhouse.shortcuts import model_to_dict
from starlette.responses import JSONResponse, FileResponse
from fastapi import FastAPI, Request, HTTPException, Depends

from endpoints import auth_api
from utils import db_models, db


def set_api_routes(app, cache, server_manger):
    @app.get("/players", response_class=JSONResponse, dependencies=[Depends(db.get_db)])
    def players(request: Request, current_user: db_models.Account = Depends(auth_api.get_admin_user)):
        return [model_to_dict(player, recurse=False) for player in db_models.Player.select()]

    @app.get("/teams", response_class=JSONResponse, dependencies=[Depends(db.get_db)])
    def teams(request: Request, current_user: db_models.Account = Depends(auth_api.get_admin_user)):
        return [model_to_dict(team, recurse=False) for team in db_models.Team.select()]

    @app.get("/teams/free", response_class=JSONResponse, dependencies=[Depends(db.get_db)])
    def teams(request: Request, current_user: db_models.Account = Depends(auth_api.get_admin_user)):
        return [model_to_dict(team, recurse=False) for team in db.get_free_teams()]

    @app.get("/servers", response_class=JSONResponse, dependencies=[Depends(db.get_db)])
    def servers(request: Request, current_user: db_models.Account = Depends(auth_api.get_admin_user)):
        return [model_to_dict(server) for server in db_models.Server.select()]

    @app.get("/matches", response_class=JSONResponse, dependencies=[Depends(db.get_db)])
    def matches(request: Request, current_user: db_models.Account = Depends(auth_api.get_admin_user)):
        return [model_to_dict(match, recurse=False) for match in db_models.Match.select()]

    @app.get("/demo/{filename}", dependencies=[Depends(db.get_db)])
    def get_demo(filename: str, current_user: db_models.Account = Depends(auth_api.get_admin_user)):
        logging.info(f"Called GET /demo filename: {filename}")
        filename = os.path.split(filename)[-1]
        return FileResponse(os.path.join(os.getenv("DEMO_FILE_PATH", "/demofiles"), filename))

    @app.get("/backup/{filename}", dependencies=[Depends(db.get_db)])
    def get_backup_file(request: Request, filename: str, current_user: db_models.Account = Depends(auth_api.get_admin_user)):
        logging.info(f"Called GET /backup filename: {filename}")
        filename = os.path.split(filename)[-1]
        return FileResponse(os.path.join(os.getenv("BACKUP_FILE_PATH", "/backupfiles"), filename))

    @app.get("/backup", dependencies=[Depends(db.get_db)])
    def list_backup_files(request: Request, current_user: db_models.Account = Depends(auth_api.get_admin_user)):
        logging.info(f"Called GET /backup")
        return os.listdir(os.getenv("BACKUP_FILE_PATH", "/backupfiles"))
