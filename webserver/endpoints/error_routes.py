import logging

from fastapi import Request
from fastapi import HTTPException
from starlette.responses import JSONResponse, RedirectResponse

from utils.rabbitmq import ErrorMessage
from utils.utils_funcs import sanitize_header_cookies


def set_routes(app, templates):
    @app.exception_handler(HTTPException)
    def errors(request: Request, exc: HTTPException):
        if exc.headers is not None and "location" in exc.headers.keys():
            return RedirectResponse(exc.headers["location"])

        ErrorMessage(f"Page Error: {exc.status_code} error -> {exc.detail}, url={str(request.url)}, request_headers:",
                     json_data=sanitize_header_cookies(dict(request.headers))).send()

        logging.error(f"{exc.status_code} error -> {exc.detail}")
        return templates.TemplateResponse("err.html",
                                          {"request": request, "code": exc.status_code, "message": exc.detail},
                                          status_code=exc.status_code)


def set_api_routes(app):
    @app.exception_handler(HTTPException)
    def errors(request: Request, exc: HTTPException):
        if exc.headers is not None and "location" in exc.headers.keys():
            return RedirectResponse(exc.headers["location"])

        ErrorMessage(f"API Error: {exc.status_code} error -> {exc.detail}, url={str(request.url)}, request_headers:",
                     json_data=sanitize_header_cookies(dict(request.headers))).send()

        logging.error(f"API: {exc.status_code} error -> {exc.detail}")
        return JSONResponse({"status": exc.status_code, "detail": exc.detail}, status_code=exc.status_code)