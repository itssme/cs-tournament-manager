import json
import logging
import time

import psycopg2


class Player:
    pass


class Player(object):
    @staticmethod
    def from_json(dict: dict) -> Player:
        return Player(dict["id"] if "id" in dict.keys() else None, dict["name"], dict["steam_id"])

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
    pass


class Team(object):
    @staticmethod
    def from_json(dict: dict) -> Team:
        return Team(dict["id"] if "id" in dict.keys() else None, dict["tag"], dict["name"])

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
                    cursor.execute("drop table team_assignments;")
                    cursor.execute("drop table teams;")
                    cursor.execute("drop table players;")
                    cursor.execute(open("utils/sql/db.sql", "r").read())
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
        insert_team(team_obj)
        for player in team["players"]:
            player_obj = Player.from_json(player)
            insert_player(player_obj)
            insert_team_assignment(team_obj, player_obj)


def insert_player(player: Player):
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("insert into players values(default, %s, %s) returning id", player.tuple()[1:])
            player.id = cursor.fetchall()[0][0]
            logging.info(str(player))


def insert_team(team: Team):
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("insert into teams values(default, %s, %s) returning id", team.tuple()[1:])
            team.id = cursor.fetchall()[0][0]
            logging.info(str(team))


def insert_team_assignment(team: Team, player: Player):
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("insert into team_assignments values(%s, %s)", (team.id, player.id))


def get_player(id: int):
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select * from players where id = %s", (id,))
            player_tuple = cursor.fetchall()
            return Player(player_tuple[0], player_tuple[1], player_tuple[2])


def get_team(id: int):
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select * from teams where id = %s", (id,))
            team_tuple = cursor.fetchall()
            return Team(team_tuple[0], team_tuple[1])
