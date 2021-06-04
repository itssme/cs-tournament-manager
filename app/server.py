import asyncio
import json
import logging
import os
import time

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
    server_config = json.loads(open("config.json", "r").read())
    teams = json.loads(open("teams.json", "r").read())
except:
    logging.warning("Could not open config file in . context, trying app/config")
    server_config = json.loads(open("app/config.json", "r").read())
    teams = json.loads(open("app/teams.json", "r").read())

os.makedirs(f"configs", exist_ok=True)

# https://github.com/skmendez/aiorcon
connections = []
id = 0
for server in tqdm(server_config):
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

for i in range(0, len(teams)):
    teams[i]["id"] = i


@app.route("/config/startTeamMatch", methods=["POST"])
def startTeamMatch():
    print(request.json)
    req = request.json

    req["team1"] = int(req["team1"])
    req["team2"] = int(req["team2"])

    team1 = {"name": teams[req["team1"]]["name"], "tag": teams[req["team1"]]["tag"],
             "players": teams[req["team1"]]["players"]}
    team2 = {"name": teams[req["team2"]]["name"], "tag": teams[req["team2"]]["tag"],
             "players": teams[req["team2"]]["players"]}

    matchname = f"{teams[req['team1']]['name']} vs {teams[req['team2']]['name']}"
    matchcfg = render_template("match.cfg", team1=team1, team2=team2, serverid=req["server"],
                               matchname=matchname)

    logging.debug(matchcfg)
    os.makedirs("match_config", exist_ok=True)
    filename = os.path.join("match_config", str(time.time()).replace(".", "_") + ".cfg")
    with open(filename, "w") as matchfile:
        matchfile.write(matchcfg)

    server_conf = server_config[int(req["server"])]
    logging.debug(server_conf)
    os.system(
        f"scp -P {server_conf['ssh_port']} {filename} {server_conf['ssh_user']}@{server_conf['ip']}:{server_conf['ssh_path_to_conf_folder']}")

    connection = connections[int(req["server"])]
    loadmatch_res = connection.loop.run_until_complete(connection.rcon(f"get5_loadmatch {filename}"))
    logging.debug(loadmatch_res)

    logging.info(f"Created an loaded match {matchname}")

    return "{'status': 'ok'}"


@app.route("/config/startPlayerMatch", methods=["POST"])
def startPlayerMatch():
    print(request.json)

    return ""


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
            {"id": connection.id, "ip": server_config[connection.id]["ip"] + ":" + str(server_config[connection.id]["port"]), "get5_stats": get5_stats, "stats": [float(value) for value in stats.split("\n")[1].split(" ") if value != '']})

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
