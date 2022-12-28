import logging

import uvicorn
from fastapi import Request
from fastapi.responses import HTMLResponse
from starlette.exceptions import HTTPException
from starlette.responses import Response, JSONResponse


def set_routes(app, templates):
    @app.exception_handler(HTTPException)
    def errors(request: Request, exc: HTTPException):
        logging.error(f"{exc.status_code} error -> {exc.detail}")

        if exc.status_code == 404:
            return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
        elif exc.status_code == 401:
            return templates.TemplateResponse("401.html", {"request": request}, status_code=401)
        elif exc.status_code == 500:
            return templates.TemplateResponse("500.html", {"request": request}, status_code=500)
        return templates.TemplateResponse("err.html", {"request": request, "status_code": exc.status_code},
                                          status_code=exc.status_code)


def set_api_routes(app):
    @app.exception_handler(HTTPException)
    def errors(request: Request, exc: HTTPException):
        logging.error(f"API: {exc.status_code} error -> {exc.detail}")
        return JSONResponse({"status": exc.status_code, "detail": exc.detail}, status_code=exc.status_code)
