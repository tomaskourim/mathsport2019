from psycopg2._psycopg import IntegrityError

from database_operations import execute_sql_postgres


def save_set_odds(odds: tuple, bookmaker_id: int, bookmaker_matchid: str, set_number: int):
    query = "INSERT INTO odds (bookmaker_id, match_bookmaker_id, odds_type, match_part, odd1, odd2) \
                VALUES (%s, %s, %s, %s, %s, %s)"
    set_to_save = f"set{set_number}"
    params = [bookmaker_id, bookmaker_matchid, 'home_away', set_to_save, odds[0], odds[1]]
    db_returned = execute_sql_postgres(query, params, True)
    if type(db_returned) == IntegrityError:
        if 'duplicate key value violates unique constraint' in db_returned.args[0]:
            query = "UPDATE odds SET odd1 = %s, odd2 = %s WHERE \
                bookmaker_id  = %s AND match_bookmaker_id = %s AND odds_type = %s AND match_part = %s"
            params = [odds[0], odds[1], bookmaker_id, bookmaker_matchid, 'home_away', set_to_save]
            execute_sql_postgres(query, params, True)
        else:
            raise db_returned
    elif 'success' in db_returned:
        pass
    else:
        raise db_returned
    pass
