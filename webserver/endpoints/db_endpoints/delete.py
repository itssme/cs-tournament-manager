import logging

from starlette.responses import JSONResponse
from fastapi import FastAPI, Request, HTTPException, Depends

from endpoints import auth_api
from utils import db_models, db
from utils.json_objects import ServerID


def set_api_routes(app, cache, server_manger):
    @app.delete("/match", response_class=JSONResponse, dependencies=[Depends(db.get_db)])
    def status(request: Request, server: ServerID,
               current_user: db_models.Account = Depends(auth_api.get_admin_user)):
        logging.info(f"Called DELETE /match with server id: {server.id}")
        server_manger.stop_match(server.id)
        return {"status": 0}
