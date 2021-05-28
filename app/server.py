import asyncio
import json
import logging
import os

import aiorcon
from flask import Flask, request, render_template, redirect
from tqdm import tqdm

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logging.info("server running")

app = Flask(__name__, static_url_path="", static_folder="static")


class RCONConnection:
    id = -1
    loop = None
    rcon = None


try:
    config = json.loads(open("config.json", "r").read())
    teams = json.loads(open("teams.json", "r").read())
except:
    logging.warning("Could not open config file in . context, trying app/config")
    config = json.loads(open("app/config.json", "r").read())
    teams = json.loads(open("app/teams.json", "r").read())

os.makedirs(f"configs", exist_ok=True)

# https://github.com/skmendez/aiorcon
connections = []
id = 0
for server in tqdm(config):
    connections.append(RCONConnection())
    connections[-1].id = id
    connections[-1].loop = asyncio.get_event_loop()

    # initialize the RCON connection with ip, port, password and the event loop.
    connections[-1].rcon = connections[-1].loop.run_until_complete(
        aiorcon.RCON.create(server["ip"], server["port"],
                            server["rcon_pw"],
                            connections[-1].loop))
    id += 1

gameservers = []
for server in connections:
    gameservers.append({"id": server.id})


@app.route("/")
def index():
    return redirect("/status")


@app.route('/status')
def status():
    return render_template("status.html", gameserver=gameservers)


@app.route('/config')
def config():
    return render_template("config.html", gameserver=gameservers, teams=teams)


@app.route('/status/info')
def info():
    status = []

    for connection in connections:
        # need to parse values: CPU   NetIn   NetOut    Uptime  Maps   FPS   Players  Svms    +-ms   ~tick
        stats = connection.loop.run_until_complete(connection.rcon("stats"))

        # because get5 is awesome they already return json
        get5_stats = json.loads(connection.loop.run_until_complete(connection.rcon("get5_status")))
        status.append(
            {"id": connection.id, "get5_stats": get5_stats, "stats": [float(value) for value in stats.split("\n")[1].split(" ") if value != '']})

        print(status)

    return json.dumps(status)


@app.errorhandler(401)
def error401(err):
    logging.error(f"401 error -> {err}")
    return render_template("401.html"), 401


@app.errorhandler(404)
def error404(err):
    logging.error(f"404 error -> {err} caused by {request.url}")
    return render_template("404.html"), 404


@app.errorhandler(500)
def error500(err):
    logging.error(f"500 error -> {err}")
    return render_template("500.html"), 500


if __name__ == '__main__':
    app.run(os.getenv("SERVER"))
