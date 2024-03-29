import json
import logging
import os
import random
import threading
import time
import itertools

import requests
import telegram
from telegram.ext import Updater, CommandHandler
from typing import Union

from utils import login_to_master_headers
from utils import send_long_message
from utils import escape_string
from utils import str2bool

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s', level=logging.INFO)

chat_ids = []
matchmaking_enabled = False


def REQUIRE_AUTH(func):
    def wrapper(update: telegram.Update, context: telegram.ext.callbackcontext.CallbackContext):
        if update.effective_chat["id"] in chat_ids:
            func(update, context)
        else:
            logging.warning(
                f"unauthorized telegram user tried to contact bot -> {update}, chat_id: {update.effective_chat['id']}")
            return None

    return wrapper


class TelegramBOT:
    def __init__(self, bot_token):
        logging.info("Starting Telegram bot")
        self.bot = telegram.Bot(token=bot_token)

        self.chat_ids = chat_ids
        self.verification_callback = None

        # self.send_all("Bot started")

        self.updater = Updater(bot_token, use_context=True)
        dp = self.updater.dispatcher

        @REQUIRE_AUTH
        def help_msgs(update, context):
            bot: telegram.bot.Bot = context.bot
            chat_id = update.effective_chat["id"]
            user_id = update.effective_user["id"]
            bot.send_message(chat_id, "Commands:\n"
                                      "/help\n"
                                      "/createTeam `teamTag` `teamName`\n"
                                      "/createPlayer `steamId` `Name`\n"
                                      "/createMatch `teamId1` `teamId2` `bestOf?` `checkAuths?`\n"
                                      "/addMember `teamId` `playerId`\n"
                                      "/deleteTeam `teamId`\n"
                                      "/deletePlayer `playerId\n`"
                                      "/deleteMatch `matchId`\n"
                                      "/removeMember `teamId` `playerId`\n"
                                      "/listTeams\n"
                                      "/listPlayers\n"
                                      "/listMatches\n"
                                      "/listMembers `teamId`\n"
                                      "/setCompeting `teamId` `competing`\n"
                                      "/startMatchmaking\n"
                                      "/stopMatchmaking\n",
                             parse_mode="MarkdownV2")

        @REQUIRE_AUTH
        def create_team(update, context):
            bot: telegram.bot.Bot = context.bot
            chat_id = update.effective_chat["id"]
            user_id = update.effective_user["id"]

            if len(context.args) < 2:
                bot.send_message(chat_id, "Invalid number of arguments")
                return

            team_tag = context.args[0]
            team_name = " ".join(context.args[1:])
            if len(team_tag) > 15:
                bot.send_message(chat_id, "Team tag must have at most 15 characters")
                return
            if len(team_tag) < 3:
                bot.send_message(chat_id, "Team name must have at least 3 characters")
                return
            if len(team_name) < 3:
                bot.send_message(chat_id, "Team tag too short")
                return

            data = {"name": team_name, "tag": team_tag}

            logging.info(f"Parsed /createMatch -> {data}")

            res = requests.post(f"{os.getenv('HTTP_PROTOCOL', 'http://')}{os.getenv('MASTER_IP')}/api/team", json=data,
                                headers=login_to_master_headers())
            if res.status_code == 200:
                bot.send_message(chat_id, f"Successfully created team '{data['name']}' with tag '{data['tag']}'")
            else:
                bot.send_message(chat_id, f"Unable to create team: {res.status_code}, {res.text}")

        @REQUIRE_AUTH
        def create_player(update, context):
            bot: telegram.bot.Bot = context.bot
            chat_id = update.effective_chat["id"]
            user_id = update.effective_user["id"]

            steam_id = context.args[0]
            # all context args are joined together to form the name
            name = " ".join(context.args[1:])

            data = {"steam_id": steam_id, "name": name}

            res = requests.post(f"{os.getenv('HTTP_PROTOCOL', 'http://')}{os.getenv('MASTER_IP')}/api/player",
                                json=data,
                                headers=login_to_master_headers())
            if res.status_code == 200:
                bot.send_message(chat_id,
                                 f"Successfully created player {data['name']} with steam id {data['steam_id']}")
            else:
                bot.send_message(chat_id, f"Unable to create player: {res.status_code}, {res.text}")

        @REQUIRE_AUTH
        def delete_team(update, context):
            bot: telegram.bot.Bot = context.bot
            chat_id = update.effective_chat["id"]
            user_id = update.effective_user["id"]

            team_id = context.args[0]

            res = requests.delete(f"{os.getenv('HTTP_PROTOCOL', 'http://')}{os.getenv('MASTER_IP')}/api/team/",
                                  params={"team_id": team_id},
                                  headers=login_to_master_headers())

            if res.status_code == 200:
                bot.send_message(chat_id, f"Successfully deleted team {team_id}")
            else:
                bot.send_message(chat_id, f"Unable to delete team: {res.status_code}, {res.text}")

        @REQUIRE_AUTH
        def list_teams(update, context):
            bot: telegram.bot.Bot = context.bot
            chat_id = update.effective_chat["id"]
            user_id = update.effective_user["id"]

            res = requests.get(f"{os.getenv('HTTP_PROTOCOL', 'http://')}{os.getenv('MASTER_IP')}/api/teams",
                               headers=login_to_master_headers())
            if res.status_code == 200:
                parsed = json.loads(res.text)
                message = json.dumps(parsed, indent=4, ensure_ascii=False)
                send_long_message(bot, message, chat_id)
            else:
                bot.send_message(chat_id, f"Unable to list teams: {res.status_code}, {res.text}")

        @REQUIRE_AUTH
        def list_players(update, context):
            bot: telegram.bot.Bot = context.bot
            chat_id = update.effective_chat["id"]
            user_id = update.effective_user["id"]

            res = requests.get(f"{os.getenv('HTTP_PROTOCOL', 'http://')}{os.getenv('MASTER_IP')}/api/players",
                               headers=login_to_master_headers())
            if res.status_code == 200:
                parsed = json.loads(res.text)
                message = json.dumps(parsed, indent=4, ensure_ascii=False)
                send_long_message(bot, message, chat_id)
            else:
                bot.send_message(chat_id, f"Unable to list players: {res.status_code}, {res.text}")

        @REQUIRE_AUTH
        def list_matches(update, context):
            bot: telegram.bot.Bot = context.bot
            chat_id = update.effective_chat["id"]
            user_id = update.effective_user["id"]

            res = requests.get(f"{os.getenv('HTTP_PROTOCOL', 'http://')}{os.getenv('MASTER_IP')}/api/matches",
                               headers=login_to_master_headers())
            if res.status_code == 200:
                parsed = json.loads(res.text)
                message = json.dumps(parsed, indent=4, ensure_ascii=False)
                send_long_message(bot, message, chat_id)
            else:
                bot.send_message(chat_id, f"Unable to list matches: {res.status_code}, {res.text}")

        @REQUIRE_AUTH
        def add_member(update, context):
            bot: telegram.bot.Bot = context.bot
            chat_id = update.effective_chat["id"]
            user_id = update.effective_user["id"]

            team_id = context.args[0]
            player_id = context.args[1]
            data = {"team_id": team_id, "player_id": player_id}
            res = requests.post(f"{os.getenv('HTTP_PROTOCOL', 'http://')}{os.getenv('MASTER_IP')}/api/teamAssignment",
                                json=data, headers=login_to_master_headers())
            if res.status_code == 200:
                bot.send_message(chat_id, f"Successfully added player {player_id} to team {team_id}")
            else:
                bot.send_message(chat_id, f"Unable to add player to team: {res.status_code}, {res.text}")

        @REQUIRE_AUTH
        def remove_member(update, context):
            bot: telegram.bot.Bot = context.bot
            chat_id = update.effective_chat["id"]
            user_id = update.effective_user["id"]

            team_id = context.args[0]
            player_id = context.args[1]
            data = {"team_id": team_id, "player_id": player_id}
            res = requests.delete(f"{os.getenv('HTTP_PROTOCOL', 'http://')}{os.getenv('MASTER_IP')}/api/teamAssignment",
                                  json=data,
                                  headers=login_to_master_headers())
            if res.status_code == 200:
                bot.send_message(chat_id, f"Successfully removed player {player_id} from team {team_id}")
            else:
                bot.send_message(chat_id, f"Unable to remove player from team: {res.status_code}, {res.text}")

        @REQUIRE_AUTH
        def list_members(update, context):
            bot: telegram.bot.Bot = context.bot
            chat_id = update.effective_chat["id"]
            user_id = update.effective_user["id"]

            team_id = context.args[0]
            res = requests.get(f"{os.getenv('HTTP_PROTOCOL', 'http://')}{os.getenv('MASTER_IP')}/api/teamPlayers/",
                               params={"team_id": team_id},
                               headers=login_to_master_headers())
            if res.status_code == 200:
                parsed = json.loads(res.text)
                message = json.dumps(parsed, indent=4, ensure_ascii=False)
                send_long_message(bot, message, chat_id)
            else:
                bot.send_message(chat_id, f"Unable to list members: {res.status_code}, {res.text}")

        @REQUIRE_AUTH
        def create_match(update, context):
            bot: telegram.bot.Bot = context.bot
            chat_id = update.effective_chat["id"]
            user_id = update.effective_user["id"]
            logging.info("Arguments: " + str(len(context.args)))

            if len(context.args) < 2 or len(context.args) > 4:
                logging.error("/createMatch called with invalid amount of arguments.")
                bot.send_message(chat_id,
                                 "/createMatch called with invalid amount of arguments. See /help",
                                 parse_mode="MarkdownV2")
                return

            team1_id = int(context.args[0])
            team2_id = int(context.args[1])
            best_of = int(context.args[2]) if len(context.args) > 2 else 1
            checkAuths = str2bool(context.args[3]) if len(context.args) > 3 else True

            data = {"team1": team1_id,
                    "team2": team2_id,
                    "best_of": best_of,
                    "check_auths": checkAuths}

            logging.info(f"Parsed POST /match -> {data}")
            res = requests.post(f"{os.getenv('HTTP_PROTOCOL', 'http://')}{os.getenv('MASTER_IP')}/api/match", json=data,
                                headers=login_to_master_headers())
            if res.status_code == 200:
                bot.send_message(chat_id, res.text)
            else:
                bot.send_message(chat_id, f"Unable to create match: {res.status_code}, {res.text}")

        @REQUIRE_AUTH
        def set_competing(update, context):
            bot: telegram.bot.Bot = context.bot
            chat_id = update.effective_chat["id"]
            user_id = update.effective_user["id"]
            logging.info("Arguments: " + str(len(context.args)))

            if len(context.args) != 2:
                logging.error("/setCompeting called with invalid amount of arguments.")
                bot.send_message(chat_id,
                                 "/setCompeting called with invalid amount of arguments. See /help",
                                 parse_mode="MarkdownV2")
                return

            team_id = int(context.args[0])
            competing = int(str2bool(context.args[1]))

            data = {"team_id": team_id,
                    "competing": competing}

            logging.info(f"Parsed POST /competing -> {data}")
            res = requests.post(f"{os.getenv('HTTP_PROTOCOL', 'http://')}{os.getenv('MASTER_IP')}/api/competing",
                                json=data, headers=login_to_master_headers())
            if res.status_code == 200:
                bot.send_message(chat_id,
                                 f"Successfully set team {team_id} to **{'' if competing else 'not'} compete**",
                                 parse_mode="MarkdownV2")
            else:
                bot.send_message(chat_id, f"Unable to set competing: {res.status_code}, {res.text}")

        @REQUIRE_AUTH
        def start_matchmaking(update, context):
            global matchmaking_enabled
            bot: telegram.bot.Bot = context.bot
            chat_id = update.effective_chat["id"]
            user_id = update.effective_user["id"]

            if matchmaking_enabled:
                bot.send_message(chat_id, "Matchmaking is already enabled.")
                return
            matchmaking_enabled = True
            bot.send_message(chat_id, "Matchmaking enabled.")

        @REQUIRE_AUTH
        def stop_matchmaking(update, context):
            global matchmaking_enabled
            bot: telegram.bot.Bot = context.bot
            chat_id = update.effective_chat["id"]
            user_id = update.effective_user["id"]

            if not matchmaking_enabled:
                bot.send_message(chat_id, "Matchmaking is already disabled.")
                return
            matchmaking_enabled = False
            bot.send_message(chat_id, "Matchmaking disabled.")

        @REQUIRE_AUTH
        def announce(update, context):
            global matchmaking_enabled
            bot: telegram.bot.Bot = context.bot
            chat_id = update.effective_chat["id"]
            user_id = update.effective_user["id"]

            announcement = " ".join(context.args)
            logging.info("Announcement: " + announcement)
            self.send_announcement("Announcement:\n" + announcement)

        dp.add_handler(CommandHandler("help", help_msgs,
                                      pass_args=True,
                                      pass_job_queue=True,
                                      pass_chat_data=True))
        dp.add_handler(CommandHandler("createTeam", create_team,
                                      pass_args=True,
                                      pass_job_queue=True,
                                      pass_chat_data=True))
        dp.add_handler(CommandHandler("createPlayer", create_player,
                                      pass_args=True,
                                      pass_job_queue=True,
                                      pass_chat_data=True))
        dp.add_handler(CommandHandler("createMatch", create_match,
                                      pass_args=True,
                                      pass_job_queue=True,
                                      pass_chat_data=True))
        dp.add_handler(CommandHandler("setCompeting", set_competing,
                                      pass_args=True,
                                      pass_job_queue=True,
                                      pass_chat_data=True))
        dp.add_handler(CommandHandler("deleteTeam", delete_team,
                                      pass_args=True,
                                      pass_job_queue=True,
                                      pass_chat_data=True))
        dp.add_handler(CommandHandler("listTeams", list_teams,
                                      pass_args=True,
                                      pass_job_queue=True,
                                      pass_chat_data=True))
        dp.add_handler(CommandHandler("listPlayers", list_players,
                                      pass_args=True,
                                      pass_job_queue=True,
                                      pass_chat_data=True))
        dp.add_handler(CommandHandler("listMatches", list_matches,
                                      pass_args=True,
                                      pass_job_queue=True,
                                      pass_chat_data=True))
        dp.add_handler(CommandHandler("listMembers", list_members,
                                      pass_args=True,
                                      pass_job_queue=True,
                                      pass_chat_data=True))
        dp.add_handler(CommandHandler("addMember", add_member,
                                      pass_args=True,
                                      pass_job_queue=True,
                                      pass_chat_data=True))
        dp.add_handler(CommandHandler("removeMember", remove_member,
                                      pass_args=True,
                                      pass_job_queue=True,
                                      pass_chat_data=True))
        dp.add_handler(CommandHandler("startMatchmaking", start_matchmaking,
                                      pass_args=True,
                                      pass_job_queue=True,
                                      pass_chat_data=True))
        dp.add_handler(CommandHandler("stopMatchmaking", stop_matchmaking,
                                      pass_args=True,
                                      pass_job_queue=True,
                                      pass_chat_data=True))
        dp.add_handler(CommandHandler("announce", announce,
                                      pass_args=True,
                                      pass_job_queue=True,
                                      pass_chat_data=True))

        dp.add_error_handler(self.error)
        self.updater.start_polling()
        logging.info("Started Telegram bot")

    def error(self, update, context):
        """Log Errors caused by Updates."""
        logging.warning('Update "%s" caused error "%s"', update, context.error)

    def send_admin(self, text):
        for chat_id in self.chat_ids:
            self.bot.send_message(chat_id=chat_id, text=escape_string(text), parse_mode="MarkdownV2")

    def send_announcement(self, text):
        if os.getenv("PUBLIC_ID", "0") != "0":
            self.bot.send_message(chat_id=int(os.getenv("PUBLIC_ID", "")), text=escape_string(text),
                                  parse_mode="MarkdownV2")
        self.send_admin(text)


telegram_bot: Union[TelegramBOT, None] = None


def matchmaker():
    # TODO: make these variables configurable via env vars or the telegram bot
    MAX_DIFF = 10000
    PLAY_PUNISH = 400

    # TODO refactor this mess
    logging.info("Starting matchmaker")
    while True:
        time.sleep(10)
        if matchmaking_enabled:
            free_teams = [(team["id"], team["elo"], team["tag"]) for team in
                          requests.get(f"{os.getenv('HTTP_PROTOCOL', 'http://')}{os.getenv('MASTER_IP')}/api/freeTeams",
                                       headers=login_to_master_headers()).json()]
            all_matches = [(match["team1"], match["team2"]) for match in
                           list(filter(lambda x: 0 < x["finished"] < 3,
                                       requests.get(
                                           f"{os.getenv('HTTP_PROTOCOL', 'http://')}{os.getenv('MASTER_IP')}/api/matches",
                                           headers=login_to_master_headers()).json()))]
            logging.info(f"Found {len(free_teams)} free teams and {len(all_matches)} matches.")
            if len(free_teams) < 3:
                continue
            if len(free_teams) % 2 == 1:
                remove_team = random.randint(0, len(free_teams) - 1)
                logging.info(f"Odd number of teams, removing one. {free_teams[remove_team]}")
                del free_teams[remove_team]
            matchups = {}
            for team in free_teams:
                matchups[team[0]] = {}
                for match in all_matches:
                    if team[0] in match:
                        if matchups[team[0]].get(match[0] if match[0] != team[0] else match[1], 0) == 0:
                            matchups[team[0]][match[0] if match[0] != team[0] else match[1]] = 1
                        else:
                            matchups[team[0]][match[0] if match[0] != team[0] else match[1]] += 1
            logging.info(f"Matchups: {matchups}")
            match_combinations = [
                [match, abs(match[0][1] - match[1][1]) + matchups[match[0][0]].get(match[1][0], 0) * PLAY_PUNISH] for
                match in list(itertools.combinations(free_teams, 2))]
            consider_matches = sorted(match_combinations, key=lambda x: x[1])

            start_matches = []
            matched_matches = set()
            logging.info(f"Consider matches: {consider_matches}")
            for potential_match in consider_matches:
                if not potential_match[0][0][0] in matched_matches and not potential_match[0][1][0] in matched_matches \
                        and abs(potential_match[0][0][1] - potential_match[0][1][1]) < MAX_DIFF:
                    matched_matches.add(potential_match[0][0][0])
                    matched_matches.add(potential_match[0][1][0])
                    start_matches.append((potential_match[0][0][0], potential_match[0][1][0],
                                          abs(potential_match[0][0][1] - potential_match[0][1][1]), potential_match[1],
                                          potential_match[0][0][1], potential_match[0][1][1],  # elo team 1 and 2
                                          potential_match[0][0][2], potential_match[0][1][2]))

            announcement = "\n".join([
                f"{match[-2].ljust(len(max(start_matches, key=lambda x: len(x[-2]))[-2]))} vs {match[-1].rjust(len(max(start_matches, key=lambda x: len(x[-1]))[-1]))} ed={str(match[2]).ljust(3)}, td={str(match[3]).ljust(3)}"
                for match in start_matches])
            for match in start_matches:
                data = {"team1": match[0], "team2": match[1], "best_of": 1, "check_auths": True}
                res = requests.post(f"{os.getenv('HTTP_PROTOCOL', 'http://')}{os.getenv('MASTER_IP')}/api/match",
                                    json=data, headers=login_to_master_headers())
                json_res = res.json()
                name_length = max(len(match[-2]), len(match[-1]))
                ip = json_res["ip"]
                port = json_res["port"]
                telegram_bot.send_announcement(
                    f"New match created:\n"
                    f"```text\n"
                    f"{match[-2].ljust(name_length)} ELO: {match[4]}\n"
                    f"vs\n"
                    f"{match[-1].ljust(name_length)} ELO: {match[5]}\n"
                    f"Command: connect {ip}:{port}\n"
                    f"```\n"
                    f"Type `!ready` in the csgo chat as soon as you are ready to play.\n"
                    f"See your stats at: csgo.robo4you.at\n"
                )
            logging.info(f"Starting matches: {start_matches}")


def main():
    global chat_ids
    global telegram_bot
    chat_ids.extend([int(elm) for elm in os.environ['CHAT_IDS'].split(",")])
    logging.info(f"Chat ids: {chat_ids}")
    matchmaking_thread = threading.Thread(target=matchmaker)
    telegram_bot = TelegramBOT(os.environ['BOT_TOKEN'])
    matchmaking_thread.start()
    matchmaking_thread.join()


if __name__ == '__main__':
    main()
