import logging
import os
from typing import Tuple, List

import psycopg2

from endpoints.csgo_stats_event import Events
from sql.db import DbObjImpl, Stats


def count_event_type(event: Events) -> int:
    with psycopg2.connect(
            host=os.getenv("DB_HOST", "db"),
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute("select count(*) from stats where type = %s", (event.value,))
            return cursor.fetchall()[0][0]


def player_with_most(event: Events) -> List[Tuple[str, int]]:
    with psycopg2.connect(
            host=os.getenv("DB_HOST", "db"),
            database="postgres",
            user="postgres",
            password="pass") as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "select player.name, count(*) from stats join player on stats.player = player.id where stats.type = %s group by player.name order by count(*) desc limit 5",
                (event.value,))
            result = cursor.fetchall()
            if len(result) == 0:
                return []
            return result
