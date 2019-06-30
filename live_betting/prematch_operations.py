from datetime import datetime

import pandas as pd
from psycopg2._psycopg import IntegrityError
from selenium.common.exceptions import StaleElementReferenceException

from database_operations import execute_sql_postgres
from live_betting.bookmaker import Bookmaker


def get_tournament_id(book_id: int, tournament_bookmaker_id: str, tournament_bookmaker_year_id: str) -> tuple:
    query = "SELECT tournament_id FROM tournament_bookmaker WHERE bookmaker_id=%s AND tournament_bookmaker_id=%s AND \
                tournament_bookmaker_extra_id=%s"
    return execute_sql_postgres(query, [book_id, tournament_bookmaker_id, tournament_bookmaker_year_id])


def save_tournament(params: list) -> tuple:
    query = f"INSERT INTO tournament (name, sex, type, surface, year) VALUES ({', '.join(['%s'] * 5)}) RETURNING id"
    return execute_sql_postgres(query, params, True)


def save_match(params: list) -> tuple:
    query = f"INSERT INTO matches (home, away, start_date, start_time, tournament_id) VALUES ({', '.join(['%s'] * 5)}) \
                    RETURNING id"
    return execute_sql_postgres(query, params, True)


def save_tournament_bookmaker(params: list) -> tuple:
    query = f"INSERT INTO tournament_bookmaker (tournament_id, bookmaker_id, tournament_bookmaker_id, \
                    tournament_bookmaker_extra_id) VALUES ({', '.join(['%s'] * 4)})"
    return execute_sql_postgres(query, params, True)


def save_match_bookmaker(params: list) -> tuple:
    query = f"INSERT INTO matches_bookmaker (match_id, bookmaker_id, match_bookmaker_id) VALUES\
                    ({', '.join(['%s'] * 3)})"
    return execute_sql_postgres(query, params, True)


def get_save_tournaments(book: Bookmaker) -> pd.DataFrame:
    tournaments = book.get_tournaments()
    print("------------------------------------------------------\nPrematch")
    print(tournaments)

    book_id = book.database_id
    year = datetime.now().year

    for i, tournament in tournaments.iterrows():
        if tournament['sex'] is None or tournament['type'] is None or tournament['surface'] is None:
            continue
        params = tournament[['tournament_name', 'sex', 'type', 'surface']].tolist()
        params.append(year)
        db_returned = save_tournament(params)
        if type(db_returned) == IntegrityError:
            if 'duplicate key value violates unique constraint' in db_returned.args[0]:
                continue
            else:
                raise db_returned
        elif type(db_returned) == tuple and type(db_returned[0]) == int:
            params = [db_returned[0], book_id, tournament.tournament_bookmaker_id,
                      tournament.tournament_bookmaker_year_id]
            save_tournament_bookmaker(params)
            print(f"Processed tournament {tournament.tournament_name}")
        else:
            raise db_returned

    return tournaments


def update_match_start(match: pd.Series, tournament_id: int):
    query = "SELECT start_date, start_time FROM matches WHERE tournament_id=%s AND home=%s AND away=%s"
    params = [tournament_id, match.home, match.away]
    db_returned = execute_sql_postgres(query, params)
    if datetime.strptime(match.start_time, '%H:%M').time() == db_returned[1] and datetime.strptime(
            match.start_date, '%d.%m.%Y').date() == db_returned[0]:
        pass
    else:
        query = "UPDATE matches SET start_date = %s, start_time = %s WHERE tournament_id=%s AND home=%s AND away=%s"
        time_params = [match.start_date, match.start_time]
        params = time_params.extend(params)
        execute_sql_postgres(query, params, True)
    pass


def save_matches(matches: pd.DataFrame, tournament_id: int, book_id: int):
    for i, match in matches.iterrows():
        params = match[["home", "away", "start_date", "start_time"]].tolist()
        params.append(tournament_id)
        db_returned = save_match(params)
        if type(db_returned) == IntegrityError:
            if 'duplicate key value violates unique constraint' in db_returned.args[0]:
                update_match_start(match, tournament_id)
                continue
            else:
                raise db_returned
        elif type(db_returned) == tuple and type(db_returned[0]) == int:
            params = [db_returned[0], book_id, match.bookmaker_matchid]
            save_match_bookmaker(params)
        else:
            raise db_returned

    pass


def process_tournaments_save_matches(book: Bookmaker, tournaments: pd.DataFrame):
    for i, tournament in tournaments.iterrows():
        # print("------------------------------------------------------")
        try:
            matches = book.get_matches_tournament(tournament)
            if len(matches) > 0:
                tournament_id = get_tournament_id(book.database_id, tournament.tournament_bookmaker_id,
                                                  tournament.tournament_bookmaker_year_id)
                if type(tournament_id) != tuple:
                    continue
                save_matches(matches, tournament_id[0], book.database_id)
            print(f"Matches from tournament {tournament.tournament_name} processed and saved.")
        except StaleElementReferenceException as error:
            print(f"Imposible to parse tournament {tournament.tournament_name}. Error: {error}")
            continue
    pass
