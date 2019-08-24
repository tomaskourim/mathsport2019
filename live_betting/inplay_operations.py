import datetime
import logging

import psycopg2
from psycopg2._psycopg import IntegrityError

from database_operations import execute_sql_postgres


def save_set_odds(odds: tuple, bookmaker_id: int, bookmaker_matchid: str, set_number: int):
    utc_time_recorded = datetime.datetime.now()
    query = "INSERT INTO odds (bookmaker_id, match_bookmaker_id, odds_type, match_part, odd1, odd2, utc_time_recorded) \
                VALUES (%s, %s, %s, %s, %s, %s, %s)"
    set_to_save = f"set{set_number}"
    params = [bookmaker_id, bookmaker_matchid, 'home_away', set_to_save, odds[0], odds[1], utc_time_recorded]
    db_returned = execute_sql_postgres(query, params, True)
    if type(db_returned) == IntegrityError or type(db_returned) == psycopg2.errors.UniqueViolation:
        if 'duplicate key value violates unique constraint' in db_returned.args[0]:
            query = "UPDATE odds SET odd1 = %s, odd2 = %s, utc_time_recorded = %s WHERE \
                bookmaker_id  = %s AND match_bookmaker_id = %s AND odds_type = %s AND match_part = %s"
            params = [odds[0], odds[1], utc_time_recorded, bookmaker_id, bookmaker_matchid, 'home_away', set_to_save]
            execute_sql_postgres(query, params, True)
        else:
            raise db_returned
    elif 'success' in db_returned:
        pass
    else:
        raise db_returned
    pass


def home_won_set(current_set_score: tuple, last_set_score: tuple, set_number: int, match_id: int) -> bool:
    query = "INSERT INTO match_course (match_id, set_number, result, utc_time_recorded) VALUES (%s, %s, %s, %s)"
    if current_set_score[0] > last_set_score[0] and current_set_score[1] == last_set_score[1]:
        home_won = True
        result = "home"
    elif current_set_score[1] > last_set_score[1] and current_set_score[0] == last_set_score[0]:
        home_won = False
        result = "away"
    else:
        raise Exception(f"Unexpected scores: {last_set_score}, {current_set_score}")
    db_returned = execute_sql_postgres(query, [match_id, set_number, result, datetime.datetime.now()], True)
    if "success" not in db_returned:
        logging.error(f"Imposible to save result. Matchid: {match_id}. Query: {query}. Error: {db_returned}")
    return home_won


def evaluate_bet_on_set(book_id: int, bookmaker_matchid: str, set_number: int, home_won: bool):
    query = "SELECT * FROM bet WHERE bookmaker_id='%s' AND match_bookmaker_id=%s AND match_part=%s"
    match_part = "".join(['set', str(set_number)])
    placed_bet = execute_sql_postgres(query, [book_id, bookmaker_matchid, match_part])
    if placed_bet is not None:
        if placed_bet[7] is not None:
            raise Exception(f"Evaluating bet that is already evaluated: {[book_id, bookmaker_matchid, match_part]}")
        if (home_won and placed_bet[3] == 'home') or (~home_won and placed_bet[3] == 'away'):
            won = True
        else:
            won = False
        query = "UPDATE bet SET result = %s WHERE bookmaker_id='%s' AND match_bookmaker_id=%s AND match_part=%s"
        db_returned = execute_sql_postgres(query, [won, book_id, bookmaker_matchid, match_part], True)
        if "success" not in db_returned:
            logging.error(
                f"Imposible to save bet result. Matchid: {bookmaker_matchid}. Query: {query}. Error: {db_returned}")
    pass


def save_bet(book_id: int, bookmaker_matchid: str, bet_type: str, match_part: str, odd: float, probability: float):
    query = "INSERT INTO bet (bookmaker_id, match_bookmaker_id, bet_type, match_part, odd, probability, utc_time_recorded) \
                VALUES (%s, %s, %s, %s, %s, %s, %s)"
    db_returned = execute_sql_postgres(query, [book_id, bookmaker_matchid, bet_type, match_part, odd, probability,
                                               datetime.datetime.now()], True)
    if "success" not in db_returned:
        logging.error(f"Imposible to save bet. Matchid: {bookmaker_matchid}. Query: {query}. Error: {db_returned}")
    pass
