import os

from fastapi import Depends
from playhouse.shortcuts import model_to_dict
from starlette.requests import Request
from starlette.responses import RedirectResponse, HTMLResponse

from endpoints import auth_api
from utils import db, db_models


def set_routes(app, templates):
    @app.get("/")
    def redirect_index():
        return RedirectResponse("/public/status")

    @app.get("/status", response_class=HTMLResponse, dependencies=[Depends(db.get_db)])
    def status(request: Request, current_user: db_models.Account = Depends(auth_api.get_admin_user)):
        gameserver = [model_to_dict(server) for server in db_models.Server.select()]
        demos = os.listdir(os.getenv("DEMO_FILE_PATH", "/demofiles"))
        return templates.TemplateResponse("status.html", {"request": request, "gameserver": gameserver, "demos": demos})

    @app.get("/demos", response_class=HTMLResponse, dependencies=[Depends(db.get_db)])
    def demos(request: Request, current_user: db_models.Account = Depends(auth_api.get_admin_user)):
        demos = os.listdir(os.getenv("DEMO_FILE_PATH", "/demofiles"))
        return templates.TemplateResponse("demos.html", {"request": request, "demos": demos})

    @app.get("/backups", response_class=HTMLResponse, dependencies=[Depends(db.get_db)])
    def backups(request: Request, current_user: db_models.Account = Depends(auth_api.get_admin_user)):
        backups = os.listdir(os.getenv("BACKUP_FILE_PATH", "/backupfiles"))
        try:
            backups = sorted(sorted(backups, key=lambda backup: int(backup.split("_")[-3])))
        except Exception as e:
            pass

        return templates.TemplateResponse("backups.html", {"request": request, "backups": backups})

    @app.get("/config", response_class=HTMLResponse, dependencies=[Depends(db.get_db)])
    def config(request: Request, current_user: db_models.Account = Depends(auth_api.get_admin_user)):
        teams = [model_to_dict(team) for team in db_models.Team.select()]
        servers = [model_to_dict(server) for server in db_models.Server.select()]

        return templates.TemplateResponse("config.html", {"request": request, "teams": teams, "servers": servers})
