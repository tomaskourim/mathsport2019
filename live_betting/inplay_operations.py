import psycopg2
from psycopg2._psycopg import IntegrityError

from database_operations import execute_sql_postgres


def save_set_odds(odds: tuple, bookmaker_id: int, bookmaker_matchid: str, set_number: int):
    query = "INSERT INTO odds (bookmaker_id, match_bookmaker_id, odds_type, match_part, odd1, odd2) \
                VALUES (%s, %s, %s, %s, %s, %s)"
    set_to_save = f"set{set_number}"
    params = [bookmaker_id, bookmaker_matchid, 'home_away', set_to_save, odds[0], odds[1]]
    db_returned = execute_sql_postgres(query, params, True)
    if type(db_returned) == IntegrityError :#or type(db_returned) == psycopg2.errors.UniqueViolation:
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


def home_won_set(current_set_score: tuple, last_set_score: tuple) -> bool:
    if current_set_score[0] > last_set_score[0] and current_set_score[1] == last_set_score[1]:
        return True
    elif current_set_score[1] > last_set_score[1] and current_set_score[0] == last_set_score[0]:
        return False
    else:
        raise Exception(f"Unexpected scores: {last_set_score}, {current_set_score}")


def evaluate_bet_on_set(last_set_score: tuple, current_set_score: tuple, book_id: int, bookmaker_matchid: str,
                        set_number: int):
    query = "SELECT * FROM bet WHERE bookmaker_id='%s' AND match_bookmaker_id=%s AND match_part=%s"
    placed_bet = execute_sql_postgres(query, [book_id, bookmaker_matchid, "".join(['set', str(set_number)])])
    if placed_bet is not None:
        if placed_bet[7] is not None:
            raise Exception(f"Evaluating bet that is already \
                    evaluated: {[book_id, bookmaker_matchid, ''.join(['set', str(set_number)])]}")
        if home_won_set(current_set_score, last_set_score):
            home = True
        else:
            home = False

        if (home and placed_bet[3] == 'home') or (~home and placed_bet[3] == 'away'):
            won = True
        else:
            won = False
        query = "UPDATE bet SET result = %s WHERE bookmaker_id='%s' AND match_bookmaker_id=%s AND match_part=%s"
        execute_sql_postgres(query, [won, book_id, bookmaker_matchid, "".join(['set', str(set_number)])], True)
    pass


def save_bet(book_id: int, bookmaker_matchid: str, bet_type: str, match_part: str, odd: float, probability: float):
    query = "INSERT INTO bet (bookmaker_id, match_bookmaker_id, bet_type, match_part, odd, probability) \
                VALUES (%s, %s, %s, %s, %s, %s)"
    execute_sql_postgres(query, [book_id, bookmaker_matchid, bet_type, match_part, odd, probability], True)
    pass
