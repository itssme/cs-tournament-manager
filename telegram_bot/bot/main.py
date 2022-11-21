import logging

import os
import telegram
import requests
from telegram.ext import Updater, CommandHandler
from utils import escape_string

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
                                      "/createTeam `teamName` `teamTag`\n"
                                      "/createUser `steamId` `Name`\n"
                                      "/createMatch `teamId1` `teamId2` `bestOf?`\n"
                                      "/deleteTeam `teamId`\n"
                                      "/listTeams\n"
                                      "/addMember `userId` `teamId`\n"
                                      "/info\n",
                             parse_mode="MarkdownV2")

        @REQUIRE_AUTH
        def create_team(update, context):
            bot: telegram.bot.Bot = context.bot
            chat_id = update.effective_chat["id"]
            user_id = update.effective_user["id"]

            if len(context.args) != 2:
                bot.send_message(chat_id, "Invalid number of arguments")
                return
            if len(context.args[1]) > 15:
                bot.send_message(chat_id, "Team tag too long")
                return
            if len(context.args[0]) < 3:
                bot.send_message(chat_id, "Team name too short")
                return
            if len(context.args[1]) < 3:
                bot.send_message(chat_id, "Team tag too short")
                return

            data = {"name": context.args[0], "tag": context.args[1]}

            logging.info(f"Parsed /createMatch -> {data}")

            res = requests.post("http://csgo_manager/api/createTeam", json=data)
            if res.status_code == 200:
                bot.send_message(chat_id, f"Successfully created team {data['name']} with tag {data['tag']}")
            else:
                bot.send_message(chat_id, f"Unable to create team: {res.status_code}, {res.text}")

        @REQUIRE_AUTH
        def create_user(update, context):
            bot: telegram.bot.Bot = context.bot
            chat_id = update.effective_chat["id"]
            user_id = update.effective_user["id"]
            bot.send_message(chat_id, "Not yet implemented",
                             parse_mode="MarkdownV2")

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
            bot.send_message(chat_id, "Not yet implemented",
                             parse_mode="MarkdownV2")

        @REQUIRE_AUTH
        def add_member(update, context):
            bot: telegram.bot.Bot = context.bot
            chat_id = update.effective_chat["id"]
            user_id = update.effective_user["id"]
            bot.send_message(chat_id, "Not yet implemented",
                             parse_mode="MarkdownV2")

        @REQUIRE_AUTH
        def info(update, context):
            bot: telegram.bot.Bot = context.bot
            chat_id = update.effective_chat["id"]
            user_id = update.effective_user["id"]
            bot.send_message(chat_id, "Not yet implemented",
                             parse_mode="MarkdownV2")
            res = requests.post("http://csgo_manager/api/createMatch")
            if res.status_code == 200:
                bot.send_message(chat_id, res.text)
            else:
                bot.send_message(chat_id, f"Unable to create match: {res.status_code}, {res.text}")

        @REQUIRE_AUTH
        def create_match(update, context):
            bot: telegram.bot.Bot = context.bot
            chat_id = update.effective_chat["id"]
            user_id = update.effective_user["id"]

            if 2 > len(context.args) or len(context.args) > 3:
                logging.error("/createMatch called with invalid amount of arguments.")
                bot.send_message(chat_id,
                                 escape_string("/createMatch called with invalid amount of arguments. See /help"),
                                 parse_mode="MarkdownV2")
                return

            data = {"team1": context.args[0], "team2": context.args[1], "best_of": None}

            if len(context.args) == 3:
                data["best_of"] = int(context.args[2])

            logging.info(f"Parsed /createMatch -> {data}")

            res = requests.post("http://csgo_manager/api/createMatch", json=data)
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
        dp.add_handler(CommandHandler("createUser", create_user,
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
        dp.add_handler(CommandHandler("addMember", add_member,
                                      pass_args=True,
                                      pass_job_queue=True,
                                      pass_chat_data=True))
        dp.add_handler(CommandHandler("ingo", info,
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
