import datetime
import logging
import threading
import time
from typing import List

import pandas as pd
import pytz

from config import COLUMN_NAMES
from data_operations import transform_home_favorite, get_probabilities_from_odds
from database_operations import execute_sql_postgres, get_match_data
from live_betting.bookmaker import Bookmaker
from live_betting.config_betting import TIME_TO_MATCHSTART_MINUTES
from live_betting.prematch_operations import get_save_tournaments, process_tournaments_save_matches
from live_betting.tipsport import Tipsport
from live_betting.utils import save_screenshot
from main import find_single_lambda


def get_starting_matches() -> List[tuple]:
    utc_time = pytz.utc.localize(datetime.datetime.utcnow())
    limit_start_time = utc_time + datetime.timedelta(minutes=TIME_TO_MATCHSTART_MINUTES)
    # input correct tournament
    query = "SELECT match_bookmaker_id FROM \
                (SELECT * FROM matches WHERE start_time_utc > %s AND start_time_utc < %s) AS matches \
                JOIN \
                matches_bookmaker ON matches.id = match_id \
                JOIN \
                tournament ON matches.tournament_id = tournament.id \
                WHERE name = 'ATP Australian Open' AND sex = 'men' AND type = 'singles' \
                EXCEPT \
                SELECT match_bookmaker_id FROM inplay"
    params = [utc_time, limit_start_time]
    return execute_sql_postgres(query, params, False, True)


def insert_inplay(bookmaker_matchid: str, book_id: int):
    query = "INSERT INTO inplay (bookmaker_id, match_bookmaker_id, utc_time_recorded) VALUES (%s, %s, %s)"
    execute_sql_postgres(query, [book_id, bookmaker_matchid, datetime.datetime.now()], True)
    pass


def remove_inplay(bookmaker_matchid: str, book_id: int):
    query = "DELETE FROM inplay WHERE bookmaker_id=%s AND  match_bookmaker_id=%s"
    execute_sql_postgres(query, [str(book_id), str(bookmaker_matchid)], True)
    pass


def clear_inplay():
    query = "DELETE FROM inplay"
    execute_sql_postgres(query, None, True)
    logger.info("Table inplay cleared.")
    pass


def get_clambda() -> float:
    odds_probability_type = '1.set'
    matches_data = pd.DataFrame(get_match_data(odds_probability_type, '../mathsport2019.sqlite'), columns=COLUMN_NAMES)
    matches_data = transform_home_favorite(matches_data)

    # get probabilities from odds
    probabilities = pd.DataFrame(get_probabilities_from_odds(matches_data, odds_probability_type))
    matches_data = matches_data.assign(probability_predicted_player=probabilities[0],
                                       probability_not_predicted_player=probabilities[1])
    training_set = matches_data[matches_data["year"] == datetime.datetime.utcnow().year - 1]
    c_lambda = find_single_lambda(training_set)
    logger.info(f"Optimal lambda is {c_lambda}")
    return c_lambda


def handle_match(bookmaker_matchid: str, c_lambda: float):
    logger.info(f"Starting handling match: {bookmaker_matchid}")
    book = Tipsport()
    try:
        book.login()
        insert_inplay(bookmaker_matchid, book.database_id)
        book.handle_match(bookmaker_matchid, c_lambda)
    except Exception as error:
        logger.exception(f"Top level error while handling match {bookmaker_matchid}. Error: {error}")
        save_screenshot(book.driver, f"top_match_handling_{str(error)}", bookmaker_matchid)
    finally:
        remove_inplay(bookmaker_matchid, book.database_id)
        book.close()

    logger.info(f"Finished handling match: {bookmaker_matchid}")
    pass


def scan_update(book: Bookmaker):
    # get tournaments & their IDs. Check database, save new ones.
    main_tournaments = get_save_tournaments(book)

    # for each tournament, get matches and their IDs. Check database, save new ones, update starting times
    # optional save odds (all or many or some) to DB
    process_tournaments_save_matches(book, main_tournaments)
    pass


if __name__ == '__main__':

    # Create a custom logger
    logger = logging.getLogger()
    logger.setLevel('DEBUG')

    # Create handlers
    total_handler = logging.FileHandler('logfile_total.log', mode='w')
    info_handler = logging.FileHandler('logfile_info.log')
    error_handler = logging.FileHandler('logfile_error.log')
    stdout_handler = logging.StreamHandler()

    total_handler.setLevel(logging.DEBUG)
    info_handler.setLevel(logging.INFO)
    error_handler.setLevel(logging.WARNING)
    stdout_handler.setLevel(logging.INFO)

    # Create formatters and add it to handlers
    logging_format = logging.Formatter('%(asctime)s - %(process)d - %(levelname)s - %(name)s - %(message)s')
    total_handler.setFormatter(logging_format)
    info_handler.setFormatter(logging_format)
    error_handler.setFormatter(logging_format)
    stdout_handler.setFormatter(logging_format)

    # Add handlers to the logger
    logger.addHandler(total_handler)
    logger.addHandler(info_handler)
    logger.addHandler(error_handler)
    logger.addHandler(stdout_handler)

    # in case it crashed with inplay games
    clear_inplay()

    # get lambda coefficient
    clambda = get_clambda()
    # initialize bookmaker bettor
    main_book = Tipsport()

    # regularly repeat
    while True:  # TODO use Flask and cron or something more reasonable then while true
        # get matches about to start, start new thread for each, process
        starting_matches_ids = get_starting_matches()
        logger.info(f"Matches to start: {len(starting_matches_ids)}")
        for bookmaker_match_id_tuple in starting_matches_ids:
            thread = threading.Thread(target=handle_match, args=(bookmaker_match_id_tuple[0], clambda))
            thread.start()
            time.sleep(30)

        # update database
        start_time_run = datetime.datetime.now()
        try:
            scan_update(main_book)
        except Exception as error:
            logger.exception(f"While updating DB error occurred: {error}")
            save_screenshot(main_book.driver, f"mainrun_{str(error)}", 'null')
        end_time = datetime.datetime.now()
        logger.info(f"Duration update run: {(end_time - start_time_run)}")
        time.sleep(60)  # wait a minute
