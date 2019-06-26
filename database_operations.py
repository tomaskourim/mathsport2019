# support file to manipulate with SQLite database

import sqlite3
from sqlite3 import Error
from typing import Optional

from config import DATABASE_PATH


def create_connection(db_file: str) -> sqlite3.Connection:
    """ create a database connection to the SQLite database
        specified by the db_file
    :param db_file: database file
    :return: Connection object or None
    """
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)

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
        print("Sql exception:", error)
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
        print("Sql exception:", error)
    finally:
        if conn is not None:
            cur.close()
            conn.close()

    return return_value


def get_match_data(odds_probability_type: str) -> list:
    sql = "select matches.id, matches.home, matches.away, matches.home_sets, matches.away_sets, \
            matches.set1home, matches.set1away, matches.set2home, matches.set2away, matches.set3home, matches.set3away,\
            matches.set4home, matches.set4away, matches.set5home, matches.set5away, tournaments.name, tournaments.year,\
            home_away.odds_home, home_away.odds_away \
            from ( \
                (select * from matches where other_result is null) as matches \
                inner join \
                (select * from tournaments) as tournaments \
                ON matches.id_tournament=tournaments.id \
                inner join \
                (select * from home_away where match_part= ? ) as home_away \
                on matches.id=home_away.id_match)"

    match_data = execute_sql(DATABASE_PATH, sql, odds_probability_type)
    return match_data
