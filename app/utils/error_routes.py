import logging

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse


def set_routes(app, templates):
    @app.exception_handler(HTTPException, response_class=HTMLResponse)
    def error401(request: Request, exc: HTTPException):
        logging.error(f"{exc.status_code} error -> {exc.detail}")
        if exc.status_code == 404:
            return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
        elif exc.status_code == 401:
            return templates.TemplateResponse("401.html", {"request": request}, status_code=401)
        elif exc.status_code == 500:
            return templates.TemplateResponse("500.html", {"request": request}, status_code=500)
        return "Error", exc.status_code
