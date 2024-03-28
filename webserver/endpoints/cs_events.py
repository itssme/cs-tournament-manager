import logging

from starlette.responses import JSONResponse

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

import json
import os
import random
import time
from typing import Dict

import aiofiles
import requests
from fastapi import Request, Depends

from endpoints import cs2_stats_event


def going_live(event: Dict):
    pass


def demo_upload_ended(event: Dict):
    pass


def map_result(event: Dict):
    pass


def series_end(event: Dict):
    pass


callbacks = {
    "map_result": map_result,
    "series_end": series_end,
    "demo_upload_ended": demo_upload_ended,
    "going_live": going_live,
    "round_mvp": cs2_stats_event.stats_event,
    "grenade_thrown": cs2_stats_event.stats_event,
    "player_death": cs2_stats_event.stats_event,
    "hegrenade_detonated": cs2_stats_event.stats_event,
    "molotov_detonated": cs2_stats_event.stats_event,
    "flashbang_detonated": cs2_stats_event.stats_event,
    "smokegrenade_detonated": cs2_stats_event.stats_event,
    "decoygrenade_started": cs2_stats_event.stats_event,
    "bomb_planted": cs2_stats_event.stats_event,
    "bomb_defused": cs2_stats_event.stats_event,
    "bomb_exploded": cs2_stats_event.stats_event
}


def set_api_routes(app):
    @app.post("/")
    async def get5_event(request: Request):
        body = await request.body()
        json_str = body.decode("utf-8")
        event = json.loads(json_str)
        logging.info(f"Event: {event['event']}")
        logging.info(event)

        if event["event"] in callbacks.keys():
            callbacks[event["event"]](event)

        return ""

    @app.post("/demo")
    async def upload_demo(request: Request):
        if "get5-filename" in request.headers.keys():
            logging.info(f"get5-filename: {request.headers['get5-filename']}")
            filename = os.path.split(request.headers["get5-filename"])[-1]
        else:
            logging.info("No get5-filename header found, using default name")
            filename = f"{time.time()}.dem"

        logging.info(f"Called POST /demo filename: {filename} and matchid: {request.headers['get5-matchid']}")

        async with aiofiles.open(os.path.join(os.getenv("DEMO_FILE_PATH", "/demofiles"), filename), 'wb') as out_file:
            content = await request.body()
            await out_file.write(content)

        logging.info(f"Done writing file: {filename}")
        return {"filename": filename}

    @app.post("/backup")
    async def upload_backup(request: Request):
        if "get5-filename" in request.headers.keys():
            logging.info(f"get5-filename: {request.headers['get5-filename']}")
            filename = os.path.split(request.headers["get5-filename"])[-1]
        else:
            logging.info("No get5-filename header found, using default name")
            filename = f"{time.time()}.cfg"

        logging.info(f"Called POST /backup filename: {filename} and matchid: {request.headers['get5-matchid']}")

        async with aiofiles.open(os.path.join(os.getenv("BACKUP_FILE_PATH", "/backupfiles"), filename),
                                 'wb') as out_file:
            content = await request.body()
            await out_file.write(content)

        logging.info(f"Done writing file: {filename}")
        return {"filename": filename}
