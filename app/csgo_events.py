import json
import logging
from typing import Dict

from fastapi import Request


def player_say(event: Dict):
    logging.info(f"Player said: {event['message']}")


callbacks = {"player_say": player_say}


def set_api_routes(app):
    @app.post("/")
    async def get5_event(request: Request):
        json_str = await request.body()
        event = json.loads(json_str)
        logging.info(event)

        if event["event"] in callbacks.keys():
            callbacks[event["event"]](event)

        return ""
