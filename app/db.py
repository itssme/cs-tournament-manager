import json
import logging
import time
from typing import List, Tuple

import psycopg2


class Player:
    def __init__(self):
        self.id: int = 0
        self.name: str = ""
        self.steam_id: str = ""


class Player(object):
    @staticmethod
    def from_json(dict: dict) -> Player:
        return Player(dict["id"] if "id" in dict.keys() else None, dict["name"], dict["steam_id"])

    @staticmethod
    def from_tuple(tuple: tuple) -> Player:
        return Player(tuple[0], tuple[1], tuple[2])

    def __init__(self, id, name, steam_id):
        self.id = id
        self.name = name
        self.steam_id = steam_id

    def tuple(self):
        return self.id, self.name, self.steam_id

    def to_json(self) -> dict:
        return {"id": self.id, "name": self.name, "steam_id": self.steam_id}

    def __str__(self):
        return str(self.to_json())

    def __repr__(self):
        return str(self.to_json())


class Team:
    def __init__(self):
        self.id: int = 0
        self.tag: str = ""
        self.name: str = ""


class Team(object):
    @staticmethod
    def from_json(dict: dict) -> Team:
        return Team(dict["id"] if "id" in dict.keys() else None, dict["tag"], dict["name"])

    @staticmethod
    def from_tuple(tuple: tuple) -> Team:
        return Team(tuple[0], tuple[1], tuple[2])

    def __init__(self, id, tag, name):
        self.id = id
        self.tag = tag
        self.name = name

    def tuple(self):
        return self.id, self.tag, self.name

    def to_json(self) -> dict:
        return {"id": self.id, "tag": self.tag, "name": self.name}

    def __str__(self):
        return str(self.to_json())

    def __repr__(self):
        return str(self.to_json())


class Server:
    id: int
    name: str
    status: int
    port: int
    team1: int
    team2: int
    gslt_token: str


class Server(object):
    @staticmethod
    def from_json(dict: dict) -> Server:
        return Server(dict["id"] if "id" in dict.keys() else None, dict["name"], dict["status"], dict["port"],
                      dict["team1"] if "team1" in dict.keys() else None,
                      dict["team2"] if "team2" in dict.keys() else None,
                      dict["gslt_token"] if "gslt_token" in dict.keys() else None)

    @staticmethod
    def from_tuple(tuple: tuple) -> Server:
        return Server(tuple[0], tuple[1], tuple[2], tuple[3], tuple[4], tuple[5], tuple[6])

    def __init__(self, id, name, status, port, team1, team2, gslt_token):
        self.id = id
        self.name = name
        self.status = status
        self.port = port
        self.team1 = team1
        self.team2 = team2
        self.gslt_token = gslt_token

    def tuple(self):
        return self.id, self.name, self.status, self.port, self.team1, self.team2, self.gslt_token

    def to_json(self) -> dict:
        return {"id": self.id, "name": self.name, "status": self.status, "port": self.port, "team1": self.team1,
                "team2": self.team2, "gslt_token": self.gslt_token}

    def __str__(self):
        return str(self.to_json())

    def __repr__(self):
        return str(self.to_json())


def setup_db():
    logging.info("Creating tables..")
    connected = False

    while not connected:
        with psycopg2.connect(
                host="db",
                database="postgres",
                user="postgres",
                password="pass") as conn:
            connected = True

            with conn.cursor() as cursor:
                try:
                    cursor.execute("drop table if exists team_assignments;")
                    cursor.execute("drop table if exists teams;")
                    cursor.execute("drop table if exists players;")
                    cursor.execute(open("sql/db.sql", "r").read())
                except Exception as e:
                    # for some reason postgres has some trouble handling "create table if not exists"
                    #   in combination with multiprocessing
                    logging.warning("Could not create tables -> {}".format(str(e)))

            logging.info("Creating tables done")

        if not connected:
            logging.warning("Could not setup database, retrying in 5 sec...")
            time.sleep(5)

    logging.info("Parsing teams.json")
    teams = None
    with open("teams.json", "r") as teams:
        teams = json.loads(teams.read())

    if teams is None:
        raise Exception("Unable to parse team.json")

    for team in teams:
        team_obj = Team.from_json(team)
        insert_team_or_set_id(team_obj)
        for player in team["players"]:
            player_obj = Player.from_json(player)
            try:
                insert_player(player_obj)
            except psycopg2.errors.UniqueViolation:
                player_obj = get_player_by_steam_id(player_obj.steam_id)
            insert_team_assignment_if_not_exists(team_obj, player_obj)


def insert_player(player: Player):
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select id from players where steam_id = %s", (player.steam_id,))
            res = cursor.fetchall()
            if len(res) != 0:
                player.id = res[0][0]
                logging.info(f"Found player: '{player.name}' in database -> '{player.steam_id}'")
                return

        with conn.cursor() as cursor:
            cursor.execute("insert into players values(default, %s, %s) returning id", player.tuple()[1:])
            player.id = cursor.fetchall()[0][0]
            logging.info(f"Inserted team: '{player}' into database")


def insert_team_or_set_id(team: Team):
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select id from teams where name = %s", (team.name,))
            res = cursor.fetchall()
            if len(res) != 0:
                team.id = res[0][0]
                logging.info(f"Found team: '{team.name}' in database -> '{team.id}'")
                return

        with conn.cursor() as cursor:
            cursor.execute("insert into teams values(default, %s, %s) returning id", team.tuple()[1:])
            team.id = cursor.fetchall()[0][0]
            logging.info(f"Inserted team: '{team}' into database")


def insert_team_assignment_if_not_exists(team: Team, player: Player):
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select * from team_assignments where team = %s and player = %s", (team.id, player.id))
            res = cursor.fetchall()
            if len(res) != 0:
                return

        with conn.cursor() as cursor:
            cursor.execute("insert into team_assignments values(%s, %s)", (team.id, player.id))


def get_player(player_id: int) -> Player:
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select * from players where id = %s", (player_id,))
            player_tuple = cursor.fetchall()[0]
            return Player.from_tuple(player_tuple)


def get_player_by_steam_id(player_steam_id: str):
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select * from players where steam_id = %s", (player_steam_id,))
            player_tuple = cursor.fetchall()[0]
            return Player.from_tuple(player_tuple)


def get_team(team_id: int) -> Team:
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select * from teams where id = %s", (team_id,))
            team_tuple = cursor.fetchall()[0]
            return Team.from_tuple(team_tuple)


def get_all_teams() -> List[Team]:
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select * from teams")
            team_tuple_list = cursor.fetchall()
            return [Team.from_tuple(team_tuple) for team_tuple in team_tuple_list]


def get_team_players(team_id: int) -> List[Player]:
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "select * from players join team_assignments on players.id = team_assignments.player where team_assignments.team = %s",
                (team_id,))
            players = cursor.fetchall()
            return [Player.from_tuple(player) for player in players]


def get_servers() -> List[Server]:
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select * from servers")
            servers = cursor.fetchall()
            return [Server.from_tuple(server) for server in servers]


def insert_server(server: Tuple) -> int:
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("insert into servers values(default, %s, %s, %s) returning id", server)
            return cursor.fetchall()[0][0]


def insert_basic_server(name: str) -> int:
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("insert into servers values(default, %s, default, default) returning id", (name,))
            return cursor.fetchall()[0][0]


def insert_basic_server_with_teams(name: str, team1: int, team2: int) -> int:
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("insert into servers values(default, %s, default, default, %s, %s) returning id",
                           (name, team1, team2))
            return cursor.fetchall()[0][0]


def set_server_port(server_id: int, port: int):
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("update servers set port = %s where id = %s", (port, server_id))


def set_server_status(server_id: int, status: int):
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("update servers set status = %s where id = %s", (status, server_id))


def set_server_token(server_id: int, gslt_token: str):
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("update servers set gslt_token = %s where id = %s", (gslt_token, server_id))


def get_server_by_id(server_id: int) -> Server:
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select * from servers where id = %s", (server_id,))
            return Server.from_tuple(cursor.fetchall()[0])


def delete_server(server_id: int):
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("delete from servers where id = %s", (server_id,))


def update_config():
    team_config = []
    teams = get_all_teams()
    for team in teams:
        players = get_team_players(team.id)
        team_config.append({
            "name": team.name,
            "tag": team.tag,
            "players": [{"steam_id": player.steam_id, "name": player.name} for player in players]
        })
    print(team_config)
    print("test")
