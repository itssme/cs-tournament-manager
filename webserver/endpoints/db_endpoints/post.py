import logging
import os
import time

import aiofiles
from playhouse.shortcuts import model_to_dict
from starlette.responses import JSONResponse
from fastapi import FastAPI, Request, HTTPException, Depends

from utils import db_models, db
from utils.json_objects import *


def set_api_routes(app, cache, server_manger):
    @app.post("/team")
    async def create_team(request: Request, team: TeamInfo):  # TODO: maybe make put? And use post only to update?
        logging.info(
            f"Called POST /team with TeamInfo: TeamName: '{team.name}', TeamTag: '{team.tag}'")

        if db_models.Team.select().where(db_models.Team.name == team.name).exists():
            raise HTTPException(status_code=400, detail="A team with that name already exists")

        db_models.Team.create(name=team.name, tag=team.tag)

    @app.post("/player")
    async def create_player(request: Request, player: PlayerInfo):
        logging.info(f"Called POST /player with PlayerInfo: PlayerName: '{player.name}', SteamID: '{player.steam_id}'")

        db.insert_player_or_set_id(db.Player(name=player.name, steam_id=player.steam_id))

    @app.get("/teamPlayers")
    async def get_team_players(request: Request, team_id: int):
        logging.info(f"Called GET /teamPlayers for team: {team_id}")
        return [team_player.to_json() for team_player in db.get_team_players(team_id)]

    @app.post("/teamAssignment")
    async def create_team_assignment(request: Request, team_assignment: TeamAssignmentInfo):
        logging.info(
            f"Called POST /teamAssignment with TeamAssignmentInfo: TeamID: '{team_assignment.team_id}', PlayerID: '{team_assignment.player_id}'")
        team = db.get_team_by_id(team_assignment.team_id)
        player = db.get_player(team_assignment.player_id)
        db.insert_team_assignment_if_not_exists(team, player)
        db.update_config()

    @app.delete("/teamAssignment")
    async def delete_team_assignment(request: Request, team_assignment: TeamAssignmentInfo):
        logging.info(
            f"Called DELETE /teamAssignment with TeamAssignment: TeamID: '{team_assignment.team_id}', PlayerID: '{team_assignment.player_id}'")
        team = db.get_team_by_id(team_assignment.team_id)
        player = db.get_player(team_assignment.player_id)
        db.delete_team_assignment(team, player)
        db.update_config()

    @app.delete("/team")
    async def delete_team(request: Request, team_id: int):
        logging.info(f"Called DELETE /team player_id: {team_id}")

        db.delete_team(team_id)
        db.update_config()

    @app.post("/competing", response_class=JSONResponse)
    async def set_competing(request: Request, competing_info: CompetingInfo):
        team = db.get_team_by_id(competing_info.team_id)
        team.competing = competing_info.competing
        team.update_attribute("competing")

    @app.delete("/player")
    async def delete_player(request: Request, player_id: int):
        logging.info(f"Called DELETE /player player_id: {player_id}")
        db.delete_player(player_id)
        db.update_config()

    @app.post("/host")
    async def add_host(request: Request, host: str):
        logging.info(f"Called POST /host host: {host}")
        db.insert_host(host)

    @app.delete("/host")
    async def delete_host(request: Request, host: str):
        logging.info(f"Called DELETE /host host: {host}")
        db.delete_host(host)

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
