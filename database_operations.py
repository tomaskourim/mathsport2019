# support file to manipulate with SQLite database

import sqlite3
from sqlite3 import Error
from typing import Optional


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
