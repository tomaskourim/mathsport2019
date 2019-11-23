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

def generate_diagrams():
    logger.info("sd")
    tournament='US Open'
    sex='men'
    type='singles'
    params=[tournament,sex,type]
    query="SELECT home, away, start_time_utc, bet_type, match_part, odd, probability, result, utc_time_recorded " \
        "FROM matches " \
            "JOIN tournament t ON matches.tournament_id = t.id " \
            "JOIN matches_bookmaker mb ON matches.id = mb.match_id " \
            "JOIN bet b ON mb.bookmaker_id = b.bookmaker_id AND mb.match_bookmaker_id = b.match_bookmaker_id " \
        "WHERE name = %s AND sex = %s AND type = %s AND result NOTNULL " \
        "ORDER BY utc_time_recorded;"

    all_bets=pd.DataFrame(execute_sql_postgres(query, params, False, True))

    pass


if __name__ == '__main__':
    # Create a custom logger
    logger = logging.getLogger()
    logger.setLevel('DEBUG')

    # Create handlers
    stdout_handler = logging.StreamHandler()
    stdout_handler.setLevel(logging.INFO)

    # Create formatters and add it to handlers
    logging_format = logging.Formatter('%(asctime)s - %(process)d - %(levelname)s - %(name)s - %(message)s')
    stdout_handler.setFormatter(logging_format)

    # Add handlers to the logger
    logger.addHandler(stdout_handler)


    start_time_run = datetime.datetime.now()
    generate_diagrams()
    end_time = datetime.datetime.now()
    logger.info(f"Duration update run: {(end_time - start_time_run)}")