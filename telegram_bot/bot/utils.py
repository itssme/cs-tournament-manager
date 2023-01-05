import logging
import os

import requests


def escape_string(input_str: str) -> str:
    input_str = input_str.replace("_", "\\_")
    input_str = input_str.replace("[", "\\[")
    input_str = input_str.replace("]", "\\]")
    input_str = input_str.replace("(", "\\(")
    input_str = input_str.replace(")", "\\)")
    input_str = input_str.replace("~", "\\~")
    input_str = input_str.replace("`", "\\`")
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
    logging.info(f"Logging in to master -> {os.getenv('MASTER_URL')}")
    session = requests.Session()
    res = session.post(f"{os.getenv('HTTP_PROTOCOL', 'http://')}{os.getenv('MASTER_IP')}/auth/token",
                       data={"username": "api_req", "password": os.getenv("API_PASSWORD", "admin")})
    return session.cookies.get("access_token")


def login_to_master_headers() -> dict:
    return {"Authorization": login_to_api()}
