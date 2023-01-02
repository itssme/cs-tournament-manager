import logging
import os
import time

from fastapi import Depends
from starlette.requests import Request
from starlette.responses import RedirectResponse, HTMLResponse

from endpoints import auth_api
from endpoints import auth_api
from sql import db


def set_routes(app, templates):
    @app.get("/", response_class=RedirectResponse)
    async def redirect_index():
        return "/public/status"

    @app.get("/status", response_class=HTMLResponse)
    async def status(request: Request, current_user: auth_api.User = Depends(auth_api.get_current_user)):
        gameserver = [server.to_json() for server in db.get_servers()]
        demos = os.listdir(os.getenv("DEMO_FILE_PATH", "/demofiles"))
        return templates.TemplateResponse("status.html", {"request": request, "gameserver": gameserver, "demos": demos})

    @app.get("/demos", response_class=HTMLResponse)
    async def demos(request: Request, current_user: auth_api.User = Depends(auth_api.get_current_user)):
        demos = os.listdir(os.getenv("DEMO_FILE_PATH", "/demofiles"))
        return templates.TemplateResponse("demos.html", {"request": request, "demos": demos})

    @app.get("/backups", response_class=HTMLResponse)
    async def backups(request: Request, current_user: auth_api.User = Depends(auth_api.get_current_user)):
        backups = os.listdir(os.getenv("BACKUP_FILE_PATH", "/backupfiles"))
        try:
            backups = sorted(sorted(backups, key=lambda backup: int(backup.split("_")[-3])))
        except Exception as e:
            pass

        return templates.TemplateResponse("backups.html", {"request": request, "backups": backups})

    @app.get("/config", response_class=HTMLResponse)
    async def config(request: Request, current_user: auth_api.User = Depends(auth_api.get_current_user)):
        teams = [team.to_json() for team in db.get_teams()]
        servers = [host for host in db.get_hosts()]
        return templates.TemplateResponse("config.html", {"request": request, "teams": teams, "servers": servers})
