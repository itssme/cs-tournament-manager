import logging
import time
from typing import Optional, List

from fastapi import Depends, HTTPException
from pydantic import BaseModel
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response

from endpoints.auth_api import get_current_user, get_admin_user
from utils import db, db_models
from utils import steam


# TODO: eventually merge this with the registration backend?

class TeamJson(BaseModel):
    team_id: Optional[int] = None
    tag: Optional[str] = None
    name: Optional[str] = None
    elo: Optional[int] = None
    competing: Optional[int] = None
    paid_registration_fee: Optional[int] = None
    registration_fee_rnd: Optional[str] = None
    verified: Optional[int] = None
    account: Optional[str] = None
    locked_changes: Optional[int] = None
    sponsored: Optional[int] = None


class PlayerJson(BaseModel):
    player_id: Optional[int] = None
    name: Optional[str] = None
    steam_id: Optional[str] = None
    steam_name: Optional[str] = None
    profile_url: Optional[str] = None
    avatar_url: Optional[str] = None
    last_updated: Optional[int] = None


class TeamAssignmentJson(BaseModel):
    team_id: int = None
    player_id: int = None


class Player(BaseModel):
    name: str
    profile_url: str


def set_api_routes(app, cache):
    @app.post("/{team_id}/member", dependencies=[Depends(db.get_db)])
    def add_team_member(request: Request, player: Player, team_id: int,
                        user: db_models.Account = Depends(get_admin_user)):
        team: db_models.Team = db_models.Team.get(db_models.Team.id == team_id)

        if team.locked_changes == 1:
            raise HTTPException(status_code=400, detail="Players cannot be added to that team anymore (locked)")

        if len(db.get_team_players(team.id)) >= 5:
            raise HTTPException(status_code=400, detail="Team already has five members")

        steam_id = steam.get_steam_id(player.profile_url)
        if steam_id is None:
            raise HTTPException(status_code=400, detail="Invalid Profile-URL")

        if db.get_player_by_steam_id(steam_id) is not None:
            raise HTTPException(status_code=400,
                                detail="Player is already in a team")

        steam_players = steam.get_profiles([steam_id])

        if steam_id is None or len(steam_players) != 1:
            raise HTTPException(status_code=400, detail="Invalid Profile-URL")
        steam_players = steam_players[0]

        db_player = db_models.Player.create(name=player.name, steam_id=steam_id, steam_name=steam_players.steam_name,
                                            profile_url=steam_players.profile_url, avatar_url=steam_players.avatar_url,
                                            last_updated=time.time())
        db_models.TeamAssignment.create(team=team, player=db_player)

        return Response(status_code=200)

    @app.delete("/player/{player_id}", dependencies=[Depends(db.get_db)])
    def remove_team_member(request: Request, player_id: int, user: db_models.Account = Depends(get_admin_user)):
        team_assignments: List[db_models.TeamAssignment] = db_models.TeamAssignment.select().where(
            db_models.TeamAssignment.player == player_id)

        for assignment in team_assignments:
            if assignment.team.locked_changes == 1:
                raise HTTPException(status_code=403,
                                    detail=f"Players cannot be removed from that team ({assignment.team.name}) anymore")

        db_player = db_models.Player.get(db_models.Player.id == player_id)
        db_player.delete_instance()

        return Response(status_code=200)

    @app.post("/update", dependencies=[Depends(db.get_db)])
    def update_team(request: Request, team: TeamJson, user: db_models.Account = Depends(get_admin_user)):
        update_team_with_json(team)
        return Response(status_code=200)

    def update_team_with_json(team: TeamJson):
        team_in_db = db_models.Team.get(db_models.Team.id == team.team_id)

        for key in TeamJson.dict(team).keys():
            if TeamJson.dict(team).get(key) is not None and key != "team_id" and key != "id":
                if key == "name":
                    if len(team.name) > 30:
                        raise HTTPException(status_code=400, detail="Teamname ist zu lang")
                    elif len(team.name) < 1:
                        raise HTTPException(status_code=400, detail="Teamname ist zu kurz")
                elif key == "tag":
                    if len(team.tag) > 10:
                        raise HTTPException(status_code=400, detail="Tag ist zu lang")
                    elif len(team.tag) < 1:
                        raise HTTPException(status_code=400, detail="Tag ist zu kurz")
                team_in_db.__setattr__(key, team.__getattribute__(key))

        team_in_db.save()

    @app.post("/update/player", dependencies=[Depends(db.get_db)])
    def update_player(request: Request, player: PlayerJson, user: db_models.Account = Depends(get_admin_user)):
        update_player_with_json(player)
        return Response(status_code=200)

    def update_player_with_json(player: PlayerJson):
        player_in_db = db_models.Player.get(db_models.Player.id == player.player_id)

        for key in PlayerJson.dict(player).keys():
            if TeamJson.dict(player).get(key) is not None and key != "player_id" and key != "id":
                player_in_db.__setattr__(key, player.__getattribute__(key))

        player_in_db.save()

    @app.post("/update/verify", dependencies=[Depends(db.get_db)])
    def verify_team(request: Request, team: TeamJson, user: db_models.Account = Depends(get_admin_user)):
        team: db_models.Team = db_models.Team.get(db_models.Team.id == team.team_id)
        team.verified = 1
        team.competing = 0
        team.save()

        return Response(status_code=200)
