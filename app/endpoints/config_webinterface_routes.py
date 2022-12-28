import os

from starlette.requests import Request
from starlette.responses import RedirectResponse, HTMLResponse

from sql import db


def set_routes(app, templates):
    @app.get("/", response_class=RedirectResponse)
    async def redirect_index():
        return "/public/status"

    @app.get("/status", response_class=HTMLResponse)
    async def status(request: Request):
        gameserver = [server.to_json() for server in db.get_servers()]
        demos = os.listdir(os.getenv("DEMO_FILE_PATH", "/demofiles"))
        return templates.TemplateResponse("status.html", {"request": request, "gameserver": gameserver, "demos": demos})

    @app.get("/demos", response_class=HTMLResponse)
    async def status(request: Request):
        demos = os.listdir(os.getenv("DEMO_FILE_PATH", "/demofiles"))
        return templates.TemplateResponse("demos.html", {"request": request, "demos": demos})

    @app.get("/config", response_class=HTMLResponse)
    async def status(request: Request):
        teams = [team.to_json() for team in db.get_teams()]
        servers = [host for host in db.get_hosts()]
        return templates.TemplateResponse("config.html", {"request": request, "teams": teams, "servers": servers})
