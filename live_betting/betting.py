import argparse
import datetime
import logging
import os.path
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
from main import find_single_lambda


def scan_update(book: Bookmaker):
    # get tournaments & their IDs. Check database, save new ones.
    main_tournaments = get_save_tournaments(book)

    # for each tournament, get matches and their IDs. Check database, save new ones, update starting times
    # optional save odds (all or many or some) to DB
    process_tournaments_save_matches(book, main_tournaments)
    pass


def get_starting_matches() -> List[tuple]:
    utc_time = pytz.utc.localize(datetime.datetime.utcnow())
    limit_start_time = utc_time + datetime.timedelta(minutes=TIME_TO_MATCHSTART_MINUTES)
    query = "SELECT match_bookmaker_id FROM \
                (SELECT * FROM matches WHERE start_time_utc > %s AND start_time_utc < %s) AS matches \
                JOIN \
                matches_bookmaker ON matches.id = match_id \
                EXCEPT \
                SELECT match_bookmaker_id FROM inplay"
    params = [utc_time, limit_start_time]
    return execute_sql_postgres(query, params, False, True)


def insert_inplay(bookmaker_matchid: str, book_id: int):
    query = "INSERT INTO inplay (bookmaker_id, match_bookmaker_id) VALUES (%s, %s)"
    execute_sql_postgres(query, [book_id, bookmaker_matchid], True)
    pass


def remove_inplay(bookmaker_matchid: str, book_id: int):
    query = "DELETE FROM inplay WHERE bookmaker_id=%s AND  match_bookmaker_id=%s"
    execute_sql_postgres(query, [str(book_id), str(bookmaker_matchid)], True)
    pass


def handle_match(bookmaker_matchid: str, c_lambda: float):
    logging.info(f"Handling match:{bookmaker_matchid}")
    book = Tipsport()
    try:
        book.login()
        insert_inplay(bookmaker_matchid, book.database_id)
        book.handle_match(bookmaker_matchid, c_lambda)
    except Exception as error:
        logging.exception(f"While handling match {bookmaker_matchid} error occurred: {error}")
        screen_order = 1
        screen_filename = f"screens/{bookmaker_matchid}-{screen_order}.png"
        while os.path.isfile(screen_filename):
            screen_order = screen_order + 1
            screen_filename = f"screens/{bookmaker_matchid}-{screen_order}.png"
        book.driver.save_screenshot(screen_filename)
    finally:
        remove_inplay(bookmaker_matchid, book.database_id)
        book.close()

    logging.info(f"Finished handling match: {bookmaker_matchid}")
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
    logging.info(f"Optimal lambda is {c_lambda}")
    return c_lambda


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(process)d - %(levelname)s - %(name)s - %(message)s')
    parser = argparse.ArgumentParser(
        description="")

    # get lambda coefficient
    clambda = get_clambda()
    # initialize bookmaker bettor
    main_book = Tipsport()

    # regularly repeat
    while True:  # TODO use Flask and cron or something more reasonable then while true
        # get matches about to start, start new thread for each, process
        starting_matches_ids = get_starting_matches()
        logging.info(f"Matches to start: {len(starting_matches_ids)}")
        for bookmaker_match_id_tuple in starting_matches_ids:
            thread = threading.Thread(target=handle_match, args=(bookmaker_match_id_tuple[0], clambda))
            thread.start()
            logging.info(f"Main thread handling match: {bookmaker_match_id_tuple[0]}")
            time.sleep(30)

        # update database
        start_time_run = datetime.datetime.now()
        scan_update(main_book)
        end_time = datetime.datetime.now()
        logging.info(f"Duration update run: {(end_time - start_time_run)}")
        time.sleep(60)  # wait a minute
