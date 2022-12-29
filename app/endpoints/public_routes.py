from starlette.requests import Request
import time

time_start = time.time()


def set_routes(app, templates):
    @app.get("/status")
    async def status(request: Request):
        return templates.TemplateResponse("public_status.html", {"request": request, "version": time_start})
