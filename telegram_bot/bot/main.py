import json
import logging
import os

import requests
import telegram
from telegram.ext import Updater, CommandHandler

from utils import escape_string
from utils import str2bool

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s', level=logging.INFO)

chat_ids = []


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
                                      "/listMembers `teamId`\n",
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

            res = requests.post("http://csgo_manager/api/createTeam", json=data)
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

            res = requests.post("http://csgo_manager/api/createPlayer", json=data)
            if res.status_code == 200:
                bot.send_message(chat_id,
                                 f"Successfully created player {data['name']} with steam id {data['steam_id']}")
            else:
                bot.send_message(chat_id, f"Unable to create team: {res.status_code}, {res.text}")

        @REQUIRE_AUTH
        def delete_team(update, context):
            bot: telegram.bot.Bot = context.bot
            chat_id = update.effective_chat["id"]
            user_id = update.effective_user["id"]
            bot.send_message(chat_id, "Not yet implemented",
                             parse_mode="MarkdownV2")

        @REQUIRE_AUTH
        def list_teams(update, context):
            bot: telegram.bot.Bot = context.bot
            chat_id = update.effective_chat["id"]
            user_id = update.effective_user["id"]

            res = requests.get("http://csgo_manager/api/teams")
            if res.status_code == 200:
                parsed = json.loads(res.text)
                result = f"Teams:\n```json\n{json.dumps(parsed, indent=4)}\n```"
                bot.send_message(chat_id, result, parse_mode="MarkdownV2")
            else:
                bot.send_message(chat_id, f"Unable to list teams: {res.status_code}, {res.text}")

        @REQUIRE_AUTH
        def list_players(update, context):
            bot: telegram.bot.Bot = context.bot
            chat_id = update.effective_chat["id"]
            user_id = update.effective_user["id"]

            res = requests.get("http://csgo_manager/api/players")
            if res.status_code == 200:
                parsed = json.loads(res.text)
                result = f"Players:\n```json\n{json.dumps(parsed, indent=4)}\n```"
                bot.send_message(chat_id, result, parse_mode="MarkdownV2")
            else:
                bot.send_message(chat_id, f"Unable to list players: {res.status_code}, {res.text}")

        @REQUIRE_AUTH
        def list_matches(update, context):
            bot: telegram.bot.Bot = context.bot
            chat_id = update.effective_chat["id"]
            user_id = update.effective_user["id"]

            res = requests.get("http://csgo_manager/api/matches")
            if res.status_code == 200:
                parsed = json.loads(res.text)
                result = f"Matches:\n```json\n{json.dumps(parsed, indent=4)}\n```"
                bot.send_message(chat_id, result, parse_mode="MarkdownV2")
            else:
                bot.send_message(chat_id, f"Unable to list matches: {res.status_code}, {res.text}")

        @REQUIRE_AUTH
        def add_member(update, context):
            bot: telegram.bot.Bot = context.bot
            chat_id = update.effective_chat["id"]
            user_id = update.effective_user["id"]
            bot.send_message(chat_id, "Not yet implemented",
                             parse_mode="MarkdownV2")

        @REQUIRE_AUTH
        def create_match(update, context):
            bot: telegram.bot.Bot = context.bot
            chat_id = update.effective_chat["id"]
            user_id = update.effective_user["id"]
            logging.info("Arguments: " + str(len(context.args)))

            if len(context.args) < 2 or len(context.args) > 4:
                logging.error("/createMatch called with invalid amount of arguments.")
                bot.send_message(chat_id,
                                 escape_string("/createMatch called with invalid amount of arguments. See /help"),
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
            res = requests.post("http://csgo_manager/api/match", json=data)
            if res.status_code == 200:
                bot.send_message(chat_id, res.text)
            else:
                bot.send_message(chat_id, f"Unable to create match: {res.status_code}, {res.text}")

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
        dp.add_handler(CommandHandler("addMember", add_member,
                                      pass_args=True,
                                      pass_job_queue=True,
                                      pass_chat_data=True))

        dp.add_error_handler(self.error)
        self.updater.start_polling()
        logging.info("Started Telegram bot")

    def error(self, update, context):
        """Log Errors caused by Updates."""
        logging.warning('Update "%s" caused error "%s"', update, context.error)

    def send_all(self, text):
        for chat_id in self.chat_ids:
            self.bot.send_message(chat_id=chat_id, text=text)


def main():
    global chat_ids
    chat_ids.extend([int(elm) for elm in os.environ['CHAT_IDS'].split(",")])
    TelegramBOT(os.environ['BOT_TOKEN'])


if __name__ == '__main__':
    main()
