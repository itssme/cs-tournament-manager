import hashlib
from starlette.requests import Request

from starlette.templating import Jinja2Templates

with open("/app/templates/public_status.html", "r") as f:
    version = hashlib.sha256(f.read().encode('utf-8')).hexdigest()


def set_routes(app, templates: Jinja2Templates):
    @app.get("/status")
    async def status(request: Request):
        return templates.TemplateResponse("public_status.html", {"request": request, "version": version})
