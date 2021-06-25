import asyncio
import json
import logging
import os
import sqlite3
import time

import aiorcon
import telegram
from telegram.ext import Updater, CommandHandler
from tqdm import tqdm

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

log = logging.getLogger(__name__)
chat_ids = []

last_status = []


class RCONConnection:
    id = -1
    loop = None
    rcon = None


try:
    server_config = json.loads(open("config.json", "r").read())
    teams = json.loads(open("teams.json", "r").read())
except:
    log.warning("Could not open config file in . context, trying app/config")
    server_config = json.loads(open("app/config.json", "r").read())
    teams = json.loads(open("app/teams.json", "r").read())

players = []
player_counter = 0
for team in teams:
    for player in team["players"]:
        player["id"] = player_counter
        players.append(player)
        player_counter += 1

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


def rcon_get_status():
    status = []

    for connection in connections:
        # need to parse values: CPU   NetIn   NetOut    Uptime  Maps   FPS   Players  Svms    +-ms   ~tick
        stats = connection.loop.run_until_complete(connection.rcon("stats"))

        # because get5 is awesome they already return json
        get5_stats = json.loads(connection.loop.run_until_complete(connection.rcon("get5_status")))
        status.append(
            {"id": connection.id,
             "ip": server_config[connection.id]["ip"] + ":" + str(server_config[connection.id]["port"]),
             "get5_stats": get5_stats,
             "stats": [float(value) for value in stats.split("\n")[1].split(" ") if value != '']})

    log.info(status)

    return json.dumps(status)


def help(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Usage:\n"
                                                                    "/help - prints this help\n"
                                                                    "/register - saves your chat id for getting "
                                                                    "messages\n"
                                                                    "/current_games - prints info about currently "
                                                                    "running games")


def current_games(update, context):
    msg = ""
    server = 0
    status = last_status[:]
    for game in status:
        get5_stats = game["get5_stats"]

        if get5_stats['gamestate'] == 1:
            msg += f"Server {server}: {get5_stats['matchid']}\nState: {get5_stats['gamestate_string']}\nMap Number: {get5_stats['map_number']}\n{get5_stats['team1']['name']}: {get5_stats['team1']['current_map_score']}\n  Series Score: {get5_stats['team1']['series_score']}\n{get5_stats['team2']['name']}: {get5_stats['team2']['current_map_score']}\n  Series Score: {get5_stats['team2']['series_score']}\n--------\n"
        else:
            msg += f"Server {server}: No Game\n--------\n"

        server += 1

    context.bot.send_message(chat_id=update.effective_chat.id, text=msg)


def add_chat_id(update, context):
    if len(chat_ids) > 0:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Only one user can be registered at the same time!")
        return

    chat_id = update.message.chat_id
    db = sqlite3.connect("chats.db")
    try:
        cur = db.cursor()
        cur.execute("insert into chats values(?);", [chat_id])
        cur.close()
        db.commit()
        logging.info("inserted new chat id -> {}".format(chat_id))
    except Exception as e:
        logging.error("error while inserting new chat id -> {}".format(str(e)))
    finally:
        db.close()
    update_ids()
    context.bot.send_message(chat_id=update.effective_chat.id, text="Saved your chat id")


def update_ids():
    global chat_ids
    db = sqlite3.connect("chats.db")
    cur = db.cursor()
    cur.execute("select * from chats;")
    chat_ids = [chat_id[0] for chat_id in cur.fetchall()]
    cur.close()
    log.info("updated ids -> {}".format(str(chat_ids)))


def error(update, context):
    log.warning('Update "%s" caused error "%s"', update, context.error)


if __name__ == '__main__':
    db = None
    if not os.path.isfile("chats.db"):
        db = sqlite3.connect("chats.db")
        cur = db.cursor()
        cur.executescript("""create table chats (id varchar(256) primary key);""")
        cur.close()
    else:
        db = sqlite3.connect("chats.db")

    cur = db.cursor()
    cur.execute("select * from chats;")
    chat_ids = [chat_id[0] for chat_id in cur.fetchall()]
    cur.close()
    log.info("got chat ids from db -> {}".format(str(chat_ids)))

    bot = telegram.Bot(token=os.environ["bot_token"])


    def send_all(text):
        for chat_id in chat_ids:
            bot.send_message(chat_id=chat_id, text=text)


    updater = Updater(os.environ["bot_token"], use_context=True)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("register", add_chat_id,
                                  pass_args=True,
                                  pass_job_queue=True,
                                  pass_chat_data=True))
    dp.add_handler(CommandHandler("help", help,
                                  pass_args=True,
                                  pass_job_queue=True,
                                  pass_chat_data=True))
    dp.add_handler(CommandHandler("current_games", current_games,
                                  pass_args=True,
                                  pass_job_queue=True,
                                  pass_chat_data=True))

    dp.add_error_handler(error)
    updater.start_polling()


    class Server:
        def __init__(self):
            self.reset()

        def reset(self):
            self.game_running = False
            self.matchid = ""
            self.team1_name = ""
            self.team2_name = ""
            self.team1_series_score = 0
            self.team2_series_score = 0
            self.team1_current_map_score = 0
            self.team2_current_map_score = 0
            self.mapnumber = 0


    matches = []
    log.info("getting rcon")
    status = json.loads(rcon_get_status())
    print(status)

    for i in range(0, len(status)):
        matches.append(Server())

    while True:
        log.info("getting rcon")
        try:
            status = json.loads(rcon_get_status())
        except Exception as e:
            log.error(f"Error getting rcon: {e}")
            continue

        last_status = status

        print(status)

        server = 0
        for game in status:
            get5_stats = game["get5_stats"]
            gamestate = game["get5_stats"]["gamestate"]

            if matches[server].game_running:
                if gamestate == 0:
                    send_all(
                        f"Game on Server #{server} has finished: {matches[server].matchid}\n\n{matches[server].team1_name} scored {matches[server].team1_current_map_score}, series score {matches[server].team1_series_score}\n{matches[server].team2_name} scored {matches[server].team2_current_map_score}, series score {matches[server].team2_series_score}\nGame was decided on map {matches[server].mapnumber}")
                    matches[server].game_running = False
                    matches[server].reset()
                else:
                    matches[server].matchid = get5_stats['matchid']
                    matches[server].team1_name = get5_stats['team1']['name']
                    matches[server].team2_name = get5_stats['team2']['name']
                    matches[server].team1_series_score = get5_stats['team1']['series_score']
                    matches[server].team2_series_score = get5_stats['team2']['series_score']
                    matches[server].team1_current_map_score = get5_stats['team1']['current_map_score']
                    matches[server].team2_current_map_score = get5_stats['team2']['current_map_score']
                    matches[server].mapnumber = get5_stats['map_number']
            else:
                if gamestate == 1:
                    send_all(f"Game on Server #{server} has been started: {get5_stats['matchid']}")
                    matches[server].game_running = True

            server += 1

        time.sleep(5)
