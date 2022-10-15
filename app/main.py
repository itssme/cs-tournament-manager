import json
import logging
import os
import time
from utils import db
from functools import wraps

from utils import error_routes
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logging.info("server running")
logging.getLogger('pika').setLevel(logging.WARNING)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

db.setup_db()

error_routes.set_routes(app, templates)


@app.get("/", response_class=RedirectResponse)
async def redirect_index():
    return "/status"


@app.get("/status", response_class=HTMLResponse)
async def status(request: Request):
    return templates.TemplateResponse("status.html", {"request": request})
