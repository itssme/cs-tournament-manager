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
        return RedirectResponse("/auth/login")

    @app.get("/team")
    def redirect_index():
        return RedirectResponse("/public/matches")

    @app.get("/matches", response_class=HTMLResponse, dependencies=[Depends(db.get_db)])
    def matches(request: Request, current_user: db_models.Account = Depends(auth_api.get_admin_user)):
        matches = [model_to_dict(match) for match in db_models.Match.select()]
        return templates.TemplateResponse("public/matches.html",
                                          {"request": request, "matches": matches})

    @app.get("/servers", response_class=HTMLResponse, dependencies=[Depends(db.get_db)])
    def servers(request: Request, current_user: db_models.Account = Depends(auth_api.get_admin_user)):
        servers = [model_to_dict(server) for server in db_models.Server.select()]
        return templates.TemplateResponse("public/servers.html",
                                          {"request": request, "servers": servers})

    @app.get("/demos", response_class=HTMLResponse, dependencies=[Depends(db.get_db)])
    def demos(request: Request, current_user: db_models.Account = Depends(auth_api.get_admin_user)):
        demos = os.listdir(os.getenv("DEMO_FILE_PATH", "/demofiles"))
        return templates.TemplateResponse("public/demos.html", {"request": request, "demos": demos})

    @app.get("/backups", response_class=HTMLResponse, dependencies=[Depends(db.get_db)])
    def backups(request: Request, current_user: db_models.Account = Depends(auth_api.get_admin_user)):
        backups = os.listdir(os.getenv("BACKUP_FILE_PATH", "/backupfiles"))
        try:
            backups = sorted(sorted(backups, key=lambda backup: int(backup.split("_")[-3])))
        except Exception as e:
            pass

        return templates.TemplateResponse("public/backups.html", {"request": request, "backups": backups})

    @app.get("/config", response_class=HTMLResponse, dependencies=[Depends(db.get_db)])
    def config(request: Request, current_user: db_models.Account = Depends(auth_api.get_admin_user)):
        teams = [model_to_dict(team) for team in db_models.Team.select()]
        servers = [model_to_dict(server) for server in db_models.Server.select()]
        hosts = [model_to_dict(host) for host in db_models.Host.select()]

        return templates.TemplateResponse("public/config.html",
                                          {"request": request, "teams": teams, "servers": servers, "hosts": hosts})

    @app.get("/create_match", response_class=HTMLResponse, dependencies=[Depends(db.get_db)])
    def backups(request: Request, current_user: db_models.Account = Depends(auth_api.get_admin_user)):
        return templates.TemplateResponse("public/create_match.html",
                                          {"request": request, "players": db_models.Player.select(),
                                           "teams": db_models.Team.select(), "hosts": db_models.Host.select()})

    @app.get("/analytics", response_class=HTMLResponse, dependencies=[Depends(db.get_db)])
    def config(request: Request, current_user: db_models.Account = Depends(auth_api.get_admin_user)):
        teams = [model_to_dict(team) for team in db_models.Team.select()]
        servers = [model_to_dict(server) for server in db_models.Server.select()]
        hosts = [model_to_dict(host) for host in db_models.Host.select()]

        return templates.TemplateResponse("public/analytics.html",
                                          {"request": request, "teams": teams, "servers": servers, "hosts": hosts})
