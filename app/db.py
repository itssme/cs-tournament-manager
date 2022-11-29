import json
import logging
import time
from typing import List, Tuple, TypeVar, Generic

import psycopg2


class DbObject(object):
    def tuple(self):
        return tuple(vars(self).values())

    def to_json(self) -> dict:
        return vars(self)

    def __str__(self):
        return str(self.to_json())

    def __repr__(self):
        return str(self.to_json())

    def insert_into_db(self, cursor):
        stmt = f"insert into {self.__class__.__name__.lower()} ({', '.join(list(filter(lambda key: (key != 'id'), list(vars(self).keys()))))}) values ({', '.join(['%s' for elm in list(filter(lambda key: (key != 'id'), list(vars(self).keys())))])}) {'returning id' if 'id' in list(vars(self).keys()) else ''}"
        values = tuple(
            self.__getattribute__(elm) for elm in list(filter(lambda key: (key != 'id'), list(vars(self).keys()))))
        logging.info(f"Running query: {stmt}\nwith values: {values}")
        cursor.execute(stmt, values)


class Player(DbObject):
    def __init__(self, id: int = None, name: str = "", steam_id: str = ""):
        self.id: int = id
        self.name: str = name
        self.steam_id: str = steam_id


class Team(DbObject):
    def __init__(self, id: int = None, tag: str = "", name: str = ""):
        self.id: int = id
        self.tag: str = tag
        self.name: str = name


class Server(DbObject):
    def __init__(self, id: int = None, status: int = -1, port: int = None, gslt_token: str = "",
                 container_name: str = None, match: int = None):
        self.id: int = id
        self.status: int = status
        self.port: int = port
        self.gslt_token: str = gslt_token
        self.container_name: str = container_name
        self.match: int = match


class Match(DbObject):
    def __init__(self, id: int = None, name: str = "", team1: int = None, team2: int = None,
                 best_out_of: int = None, number_in_map_series: int = None, current_score_team1: int = None,
                 current_score_team2: int = None, finished: int = None):
        self.id: int = id
        self.name: str = name
        self.team1: int = team1
        self.team2: int = team2
        self.best_out_of: int = best_out_of
        self.number_in_map_series: int = number_in_map_series
        self.current_score_team1: int = current_score_team1
        self.current_score_team2: int = current_score_team2
        self.finished: int = finished


T = TypeVar("T", Player, Team, Server, Match)


class DbObjImpl(Generic[T]):
    def from_json(self, dict: dict) -> T:
        obj = self.__orig_class__.__args__[0]()
        for attr in vars(obj).keys():
            if attr in dict.keys():
                obj.__setattr__(attr, dict[attr])

        return self.from_tuple(tuple(vars(obj).values()))

    def from_tuple(self, tuple: tuple) -> T:
        return self.__orig_class__.__args__[0](*tuple)


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
        team_obj = DbObjImpl[Team]().from_json(team)
        insert_team_or_set_id(team_obj)
        for player in team["players"]:
            player_obj = DbObjImpl[Player]().from_json(player)
            try:
                insert_player_or_set_id(player_obj)
            except psycopg2.errors.UniqueViolation:
                player_obj = get_player_by_steam_id(player_obj.steam_id)
            insert_team_assignment_if_not_exists(team_obj, player_obj)


def insert_player_or_set_id(player: Player):
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select id from player where steam_id = %s", (player.steam_id,))
            res = cursor.fetchall()
            if len(res) != 0:
                player.id = res[0][0]
                logging.info(f"Found player: '{player.name}' in database -> '{player.steam_id}'")
                return

        with conn.cursor() as cursor:
            player.insert_into_db(cursor)
            player.id = cursor.fetchall()[0][0]
            logging.info(f"Inserted team: '{player}' into database")


def insert_team_or_set_id(team: Team):
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select id from team where name = %s", (team.name,))
            res = cursor.fetchall()
            if len(res) != 0:
                team.id = res[0][0]
                logging.info(f"Found team: '{team.name}' in database -> '{team.id}'")
                return

        with conn.cursor() as cursor:
            team.insert_into_db(cursor)
            team.id = cursor.fetchall()[0][0]
            logging.info(f"Inserted team: '{team}' into database")


def insert_team_assignment_if_not_exists(team: Team, player: Player):
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select * from team_assignment where team = %s and player = %s", (team.id, player.id))
            res = cursor.fetchall()
            if len(res) != 0:
                return

        with conn.cursor() as cursor:
            cursor.execute("insert into team_assignment values(%s, %s)", (team.id, player.id))


def get_player(player_id: int) -> Player:
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select * from player where id = %s", (player_id,))
            player_tuple = cursor.fetchall()[0]
            return DbObjImpl[Player]().from_tuple(player_tuple)


def get_player_by_steam_id(player_steam_id: str):
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select * from player where steam_id = %s", (player_steam_id,))
            player_tuple = cursor.fetchall()[0]
            return DbObjImpl[Player]().from_tuple(player_tuple)


def get_team(team_id: int) -> Team:
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select * from team where id = %s", (team_id,))
            team_tuple = cursor.fetchall()[0]
            return DbObjImpl[Team]().from_tuple(team_tuple)


def get_all_teams() -> List[Team]:
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select * from team")
            team_tuple_list = cursor.fetchall()
            return [DbObjImpl[Team]().from_tuple(team_tuple) for team_tuple in team_tuple_list]


def get_team_players(team_id: int) -> List[Player]:
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "select player.id, player.name, player.steam_id from player join team_assignment on player.id = team_assignment.player where team_assignment.team = %s",
                (team_id,))
            players = cursor.fetchall()
            return [DbObjImpl[Player]().from_tuple(player) for player in players]


def get_servers() -> List[Server]:
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select * from server")
            servers = cursor.fetchall()
            return [DbObjImpl[Server]().from_tuple(server) for server in servers]


def insert_server(server: Server):
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            server.insert_into_db(cursor)
            server.id = cursor.fetchall()[0][0]


def set_server_port(server_id: int, port: int):
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("update server set port = %s where id = %s", (port, server_id))


def set_server_status(server_id: int, status: int):
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("update server set status = %s where id = %s", (status, server_id))


def set_server_token(server_id: int, gslt_token: str):
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("update server set gslt_token = %s where id = %s", (gslt_token, server_id))


def get_server_by_id(server_id: int) -> Server:
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select * from server where id = %s", (server_id,))
            return DbObjImpl[Server]().from_tuple(cursor.fetchall()[0])


def delete_server(server_id: int):
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("delete from server where id = %s", (server_id,))


def insert_match(match: Match):
    with psycopg2.connect(
            host="db",
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            match.insert_into_db(cursor)
            match.id = cursor.fetchall()[0][0]


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
    json_object = json.dumps(team_config, indent=4)

    with open("teams.json", "w") as outfile:
        outfile.write(json_object)
