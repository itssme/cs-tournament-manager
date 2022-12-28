from starlette.requests import Request


def set_routes(app, templates):
    @app.get("/status")
    async def status(request: Request):
        return templates.TemplateResponse("public_status.html", {"request": request})
