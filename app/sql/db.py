import json
import logging
import os
import time
from typing import List, TypeVar, Generic

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

    def insert_into_db(self):
        with psycopg2.connect(
                host=os.getenv("DB_HOST", "db"),
                database="postgres",
                user="postgres",
                password="pass") as conn:
            with conn.cursor() as cursor:
                self.insert_into_db_with_cursor(cursor)

    def insert_into_db_with_cursor(self, cursor):
        stmt = f"insert into {self.__class__.__name__.lower()} ({', '.join(list(filter(lambda key: (key != 'id'), list(vars(self).keys()))))}) values ({', '.join(['%s' for elm in list(filter(lambda key: (key != 'id'), list(vars(self).keys())))])}) {'returning id' if 'id' in list(vars(self).keys()) else ''}"
        values = tuple(
            self.__getattribute__(elm) for elm in
            list(filter(lambda key: (key != 'id'), list(vars(self).keys()))))
        logging.info(f"Running query: {stmt}\nwith values: {values}")
        cursor.execute(stmt, values)
        if "id" in vars(self).keys():
            self.__setattr__("id", cursor.fetchall()[0][0])

    # WARNING: Currently only works if the object is using the 'id' attribute as primary key
    def update_attribute(self, attr: str):
        if "id" not in vars(self).keys():
            raise NotImplemented("Cannot insert object that does not use 'id' as primary key")

        with psycopg2.connect(
                host=os.getenv("DB_HOST", "db"),
                database="postgres",
                user="postgres",
                password="pass") as conn:
            with conn.cursor() as cursor:
                self.update_attribute_with_cursor(cursor, attr)

    def update_attribute_with_cursor(self, cursor, attr: str):
        stmt = f"update {self.__class__.__name__.lower()} set {attr} = %s where id = %s"
        values = (self.__getattribute__(attr), self.__getattribute__("id"))
        logging.info(f"Running query: {stmt}\nwith values: {values}")
        cursor.execute(stmt, values)


class Player(DbObject):
    def __init__(self, id: int = None, name: str = "", steam_id: str = ""):
        self.id: int = id
        self.name: str = name
        self.steam_id: str = steam_id


class Team(DbObject):
    def __init__(self, id: int = None, tag: str = "", name: str = "", elo: int = 0, competing: int = 0):
        self.id: int = id
        self.tag: str = tag
        self.name: str = name
        self.elo: int = elo
        self.competing: int = competing


class Server(DbObject):
    def __init__(self, id: int = None, ip: str = "host.docker.internal", port: int = None, gslt_token: str = "",
                 container_name: str = None, match: int = None):
        self.id: int = id
        self.ip: str = ip
        self.port: int = port
        self.gslt_token: str = gslt_token
        self.container_name: str = container_name
        self.match: int = match


class Match(DbObject):
    def __init__(self, id: int = None, matchid: str = "", name: str = "", team1: int = None, team2: int = None,
                 best_out_of: int = None, number_in_map_series: int = 0, series_score_team1: int = 0,
                 series_score_team2: int = 0, finished: int = 0):
        self.id: int = id
        self.matchid: str = matchid
        self.name: str = name
        self.team1: int = team1
        self.team2: int = team2
        self.best_out_of: int = best_out_of
        self.number_in_map_series: int = number_in_map_series
        self.series_score_team1: int = series_score_team1
        self.series_score_team2: int = series_score_team2
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
    if os.getenv("MASTER", "1") != "1":
        logging.info("Not a master instance, wont create tables in db and ignore teams.json")
        return

    logging.info("Creating tables..")
    connected = False

    while not connected:
        with psycopg2.connect(
                host=os.getenv("DB_HOST", "db"),
                database="postgres",
                user="postgres",
                password="pass") as conn:
            connected = True

            with conn.cursor() as cursor:
                try:
                    cursor.execute(open("db.sql", "r").read())
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
            host=os.getenv("DB_HOST", "db"),
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
            player.insert_into_db_with_cursor(cursor)
            logging.info(f"Inserted team: '{player}' into database")


def insert_team_or_set_id(team: Team):
    with psycopg2.connect(
            host=os.getenv("DB_HOST", "db"),
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
            team.insert_into_db_with_cursor(cursor)
            logging.info(f"Inserted team: '{team}' into database")


def insert_team_assignment_if_not_exists(team: Team, player: Player):
    with psycopg2.connect(
            host=os.getenv("DB_HOST", "db"),
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


def delete_team_assignment(team: Team, player: Player):
    with psycopg2.connect(
            host=os.getenv("DB_HOST", "db"),
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("delete from team_assignment where team = %s and player = %s", (team.id, player.id))


def get_player(player_id: int) -> Player:
    with psycopg2.connect(
            host=os.getenv("DB_HOST", "db"),
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select * from player where id = %s", (player_id,))
            player_tuple = cursor.fetchall()[0]
            return DbObjImpl[Player]().from_tuple(player_tuple)


def delete_player(player_id: int):
    with psycopg2.connect(
            host=os.getenv("DB_HOST", "db"),
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("delete from player where id = %s", (player_id,))


def delete_team(team_id: int):
    with psycopg2.connect(
            host=os.getenv("DB_HOST", "db"),
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("delete from team where id = %s", (team_id,))


def get_players() -> List[Player]:
    with psycopg2.connect(
            host=os.getenv("DB_HOST", "db"),
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select * from player")
            player_tuple_list = cursor.fetchall()
            return [DbObjImpl[Player]().from_tuple(player_tuple) for player_tuple in player_tuple_list]


def get_player_by_steam_id(player_steam_id: str):
    with psycopg2.connect(
            host=os.getenv("DB_HOST", "db"),
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select * from player where steam_id = %s", (player_steam_id,))
            player_tuple = cursor.fetchall()[0]
            return DbObjImpl[Player]().from_tuple(player_tuple)


def get_team_by_id(team_id: int) -> Team:
    with psycopg2.connect(
            host=os.getenv("DB_HOST", "db"),
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select * from team where id = %s", (team_id,))
            team_tuple = cursor.fetchall()[0]
            return DbObjImpl[Team]().from_tuple(team_tuple)


def get_teams() -> List[Team]:
    with psycopg2.connect(
            host=os.getenv("DB_HOST", "db"),
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select * from team order by id")
            team_tuple_list = cursor.fetchall()
            return [DbObjImpl[Team]().from_tuple(team_tuple) for team_tuple in team_tuple_list]


def get_free_teams() -> List[Team]:
    with psycopg2.connect(
            host=os.getenv("DB_HOST", "db"),
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "select * from team except select team.* from team join match on team.id = match.team1 or team.id = match.team2 where match.finished < 1 and team.competing = 1;")
            team_tuple_list = cursor.fetchall()
            return [DbObjImpl[Team]().from_tuple(team_tuple) for team_tuple in team_tuple_list]


def get_team_players(team_id: int) -> List[Player]:
    with psycopg2.connect(
            host=os.getenv("DB_HOST", "db"),
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
            host=os.getenv("DB_HOST", "db"),
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select * from server")
            servers = cursor.fetchall()
            return [DbObjImpl[Server]().from_tuple(server) for server in servers]


def insert_server(server: Server):
    with psycopg2.connect(
            host=os.getenv("DB_HOST", "db"),
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            server.insert_into_db_with_cursor(cursor)


def get_server_by_id(server_id: int) -> Server:
    with psycopg2.connect(
            host=os.getenv("DB_HOST", "db"),
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select * from server where id = %s", (server_id,))
            return DbObjImpl[Server]().from_tuple(cursor.fetchall()[0])


def delete_server(server_id: int):
    with psycopg2.connect(
            host=os.getenv("DB_HOST", "db"),
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("delete from server where id = %s", (server_id,))


def get_matches() -> List[Match]:
    with psycopg2.connect(
            host=os.getenv("DB_HOST", "db"),
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select * from match")
            matches = cursor.fetchall()
            return [DbObjImpl[Match]().from_tuple(match) for match in matches]


def get_match_by_id(match_id: int) -> Match:
    with psycopg2.connect(
            host=os.getenv("DB_HOST", "db"),
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select * from match where id = %s", (match_id,))
            return DbObjImpl[Match]().from_tuple(cursor.fetchall()[0])


def get_match_by_matchid(matchid: int) -> Match:
    with psycopg2.connect(
            host=os.getenv("DB_HOST", "db"),
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select * from match where matchid = %s", (matchid,))
            return DbObjImpl[Match]().from_tuple(cursor.fetchall()[0])


def get_match_by_serverid(server_id: int) -> Match:
    with psycopg2.connect(
            host=os.getenv("DB_HOST", "db"),
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select match.* from match join server on server.match = match.id where server.id = %s",
                           (server_id,))
            return DbObjImpl[Match]().from_tuple(cursor.fetchall()[0])


def insert_match(match: Match):
    with psycopg2.connect(
            host=os.getenv("DB_HOST", "db"),
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            match.insert_into_db_with_cursor(cursor)


def get_server_for_match(matchid: str) -> Server:
    with psycopg2.connect(
            host=os.getenv("DB_HOST", "db"),
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select server.* from server join match on server.id = match.id where match.matchid = %s",
                           (matchid,))
            return DbObjImpl[Server]().from_tuple(cursor.fetchall()[0])


def get_hosts() -> List[str]:
    with psycopg2.connect(
            host=os.getenv("DB_HOST", "db"),
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select * from host")
            server_tuple_list = cursor.fetchall()
            return [host[0] for host in server_tuple_list]


def get_least_used_host_ips():
    with psycopg2.connect(
            host=os.getenv("DB_HOST", "db"),
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "select host.* from host left join server on host.ip = server.ip group by host.ip order by count(server.ip) asc")
            host_list = cursor.fetchall()
            logging.info(host_list)
            return host_list[0][0]


def update_config():
    if os.getenv("MASTER", "1") != "1":
        logging.warning("Not a master instance, writing teams.json will have no effect.")

    team_config = []
    teams = get_teams()
    for team in teams:
        players = get_team_players(team.id)
        team_config.append({
            "name": team.name,
            "tag": team.tag,
            "players": [{"steam_id": player.steam_id, "name": player.name} for player in players],
            "elo": team.elo,
            "competing": team.competing
        })

    with open("teams.json", mode="w", encoding="utf-8") as outfile:
        json.dump(team_config, outfile, indent=2, ensure_ascii=False)
