# support file to manipulate with SQLite and Postgresql database
import logging
import sqlite3
from configparser import ConfigParser
from typing import Optional

import psycopg2

from config import DATABASE_PATH


def config(filename='database.ini', section='postgresql'):
    # create a parser
    parser = ConfigParser()
    # read config file
    parser.read(filename)

    # get section, default to postgresql
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))

    return db


def create_connection(db_file: str) -> sqlite3.Connection:
    """ create a database connection to the SQLite database
        specified by the db_file
    :param db_file: database file
    :return: Connection object or None
    """
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except sqlite3.Error as e:
        logging.warning(e)

    return None


def execute_sql(db_path: str, query: str, param: Optional[str],
                modifying: bool = False) -> list:  # TODO maybe not always list
    conn = None
    cur = None
    return_value = None
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        if param is not None:
            if isinstance(param, list):
                cur.execute(query, param)
            else:
                cur.execute(query, (param,))
        else:
            cur.execute(query)
        return_value = cur.fetchall()
        if modifying:
            conn.commit()
    except (Exception, sqlite3.DatabaseError) as error:
        logging.warning("Sql exception:", error)
    finally:
        if conn is not None:
            cur.close()
            conn.close()

    return return_value


def execute_many_sql(db_path: str, query: str, param: Optional[str],
                     modifying: bool = False) -> list:  # TODO maybe not always list
    conn = None
    cur = None
    return_value = None
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        if param is not None:
            if isinstance(param, list):
                cur.executemany(query, param)
            else:
                cur.executemany(query, (param,))
        else:
            cur.executemany(query)
        return_value = cur.fetchall()
        if modifying:
            conn.commit()
    except (Exception, sqlite3.DatabaseError) as error:
        logging.warning("Sql exception:", error)
    finally:
        if conn is not None:
            cur.close()
            conn.close()

    return return_value


def execute_sql_postgres(query: str, param: Optional, modifying: bool = False, return_multiple: bool = False,
                         execute_multiple: bool = False) -> tuple:
    conn = None
    cur = None
    try:
        params = config()
        conn = psycopg2.connect(**params)
        cur = conn.cursor()
        if param is not None:
            if execute_multiple:
                for index in range(0, len(param[0])):
                    one_param = [item[index] for item in param]
                    cur.execute(query, one_param)
            else:
                cur.execute(query, param)
        else:
            cur.execute(query)
        if cur.description is not None:
            if return_multiple:
                return_value = cur.fetchall()
            else:
                return_value = cur.fetchone()
        else:
            return_value = "success"
        if modifying:
            conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        logging.debug("Sql exception:", error)
        return_value = error
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()

    return return_value


def get_match_data(odds_probability_type: str) -> list:
    sql = "SELECT matches.id, matches.home, matches.away, matches.home_sets, matches.away_sets, \
            matches.set1home, matches.set1away, matches.set2home, matches.set2away, matches.set3home, matches.set3away,\
            matches.set4home, matches.set4away, matches.set5home, matches.set5away, tournaments.name, tournaments.year,\
            home_away.odds_home, home_away.odds_away \
            FROM ( \
                (SELECT * FROM matches WHERE other_result IS NULL) AS matches \
                INNER JOIN \
                (SELECT * FROM tournaments) AS tournaments \
                ON matches.id_tournament=tournaments.id \
                INNER JOIN \
                (SELECT * FROM home_away WHERE match_part= ? ) AS home_away \
                ON matches.id=home_away.id_match)"

    match_data = execute_sql(DATABASE_PATH, sql, odds_probability_type)
    return match_data
