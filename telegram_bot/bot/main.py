import logging

import os
import telegram
import requests
from telegram.ext import Updater, CommandHandler

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s', level=logging.INFO)
logging.info("started bots")

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
                                      "/help - prints this help")

        @REQUIRE_AUTH
        def createMatch(update, context):
            bot: telegram.bot.Bot = context.bot
            chat_id = update.effective_chat["id"]
            user_id = update.effective_user["id"]

            if len(context.args) < 2:
                logging.error("/createMatch called with less than two arguments.")
                bot.send_message(chat_id, "/createMatch called with to less than two arguments. See /help")
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
        dp.add_handler(CommandHandler("createMatch", createMatch,
                                      pass_args=True,
                                      pass_job_queue=True,
                                      pass_chat_data=True))

        dp.add_error_handler(self.error)
        self.updater.start_polling()

    def error(self, update, context):
        """Log Errors caused by Updates."""
        logging.warning('Update "%s" caused error "%s"', update, context.error)

    def send_all(self, text):
        for chat_id in self.chat_ids:
            self.bot.send_message(chat_id=chat_id, text=text)


def main():
    global chat_ids
    chat_ids.extend([int(elm) for elm in os.environ['CHAT_IDS'].split(",")])
    logging.info(f"Chat ids: {os.environ['CHAT_IDS']}, parsed: {chat_ids}")
    TelegramBOT(os.environ['BOT_TOKEN'])


if __name__ == '__main__':
    main()
