import json
import logging
import os
import time

import requests


def escape_string(input_str: str) -> str:
    input_str = input_str.replace("_", "\\_")
    input_str = input_str.replace("[", "\\[")
    input_str = input_str.replace("]", "\\]")
    input_str = input_str.replace("(", "\\(")
    input_str = input_str.replace(")", "\\)")
    input_str = input_str.replace("~", "\\~")
    # input_str = input_str.replace("`", "\\`")
    input_str = input_str.replace(">", "\\>")
    input_str = input_str.replace("#", "\\#")
    input_str = input_str.replace("+", "\\+")
    input_str = input_str.replace("-", "\\-")
    input_str = input_str.replace("=", "\\=")
    input_str = input_str.replace("|", "\\|")
    input_str = input_str.replace("{", "\\{")
    input_str = input_str.replace("}", "\\}")
    input_str = input_str.replace(".", "\\.")
    input_str = input_str.replace("!", "\\!")
    return input_str


def str2bool(v):
    return v.lower() in ("yes", "y", "true", "t", "1")


def login_to_api() -> str:
    logging.info(
        f"Logging in to master -> {os.getenv('HTTP_PROTOCOL', 'http://')}{os.getenv('MANAGER_IP', 'host.docker.internal')}/auth/token")
    session = requests.Session()
    res = session.post(
        f"{os.getenv('HTTP_PROTOCOL', 'http://')}{os.getenv('MANAGER_IP', 'host.docker.internal')}/auth/token",
        data={"username": "api_req", "password": os.getenv("API_PASSWORD", "admin")})
    return session.cookies.get("access_token")


def login_to_master_headers() -> dict:
    return {"Authorization": login_to_api()}


def send_long_message(bot, message, chat_id):
    if len(message.split("\n")) < 50:
        logging.info(f"short message > {message}")
        result = f"```json\n{message}\n```"
        bot.send_message(chat_id, result, parse_mode="MarkdownV2")
    else:
        message_lines = message.split("\n")
        bot.send_message(chat_id, "Teams:", parse_mode="MarkdownV2")
        for i in range(0, len(message_lines), 50):
            result = '\n'.join(message_lines[i:i + 50])
            result = f"```json\n{result}\n```"
            bot.send_message(chat_id, result, parse_mode="MarkdownV2")
            time.sleep(2)
