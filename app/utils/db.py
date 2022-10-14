import logging
import time

import psycopg2


def setup_db():
    logging.info("creating tables..")
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
                    cursor.execute(open("db.sql", "r").read())
                except Exception as e:
                    # for some reason postgres has some trouble handling "create table if not exists"
                    #   in combination with multiprocessing
                    logging.warning("Could not create tables -> {}".format(str(e)))

            logging.info("creating tables done")

        if not connected:
            logging.warning("Could not setup database, retrying in 5 sec...")
            time.sleep(5)
