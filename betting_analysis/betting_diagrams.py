import datetime
import logging

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from database_operations import execute_sql_postgres

BET_COLUMN_NAMES = ["home", "away", "start_time_utc", "bet_type", "match_part", "odd", "probability", "result",
                    "utc_time_recorded"]


def generate_diagrams():
    tournament = 'US Open'
    sex = 'men'
    type = 'singles'
    params = [tournament, sex, type]
    query = "SELECT home, away, start_time_utc, bet_type, match_part, odd, probability, result, utc_time_recorded " \
            "FROM matches " \
            "JOIN tournament t ON matches.tournament_id = t.id " \
            "JOIN matches_bookmaker mb ON matches.id = mb.match_id " \
            "JOIN bet b ON mb.bookmaker_id = b.bookmaker_id AND mb.match_bookmaker_id = b.match_bookmaker_id " \
            "WHERE name = %s AND sex = %s AND type = %s AND result NOTNULL " \
            "ORDER BY utc_time_recorded;"

    all_bets = pd.DataFrame(execute_sql_postgres(query, params, False, True), columns=BET_COLUMN_NAMES)
    naive_betting_win = []
    prob_betting_win = []
    kelly_betting_win = []
    balance_naive = [0]
    balance_prob = [0]
    balance_kelly = [50]
    for index, bet in all_bets.iterrows():
        if bet.result:
            naive_betting_win.append(bet.odd - 1)
            balance_naive.append(balance_naive[index] + naive_betting_win[index])

            prob_betting_win.append(bet.probability * bet.odd - bet.probability)
            balance_prob.append(balance_prob[index] + prob_betting_win[index])
        else:
            naive_betting_win.append(-1)
            balance_naive.append(balance_naive[index] + naive_betting_win[index])

            prob_betting_win.append(-bet.probability)
            balance_prob.append(balance_prob[index] + prob_betting_win[index])

    all_bets.insert(0, "naive_balance", balance_naive[1:], True)
    all_bets.insert(0, "naive_wins", naive_betting_win, True)

    all_bets.insert(0, "prob_balance", balance_prob[1:], True)
    all_bets.insert(0, "prob_wins", prob_betting_win, True)

    naive_min = min(all_bets.naive_balance)
    prob_min = min(all_bets.prob_balance)

    x_axis = range(1, len(all_bets) + 1)
    plt.plot(x_axis, all_bets.naive_balance, 'b-', label='naive')
    plt.plot(x_axis, all_bets.prob_balance, 'r-', label='probability')
    plt.xlabel('bet number')
    plt.ylabel('account balance')

    naive_min_coordinates = (np.where(all_bets.naive_balance == naive_min)[0][0], naive_min)
    naive_min_annotation_coordinates = (naive_min_coordinates[0] - 60, naive_min_coordinates[1] + 0.3)
    prob_min_coordinates = (np.where(all_bets.prob_balance == prob_min)[0][0], prob_min)
    prob_min_annotation_coordinates = (prob_min_coordinates[0] - 60, prob_min_coordinates[1] - 1)
    plt.annotate('global min naive', xy=naive_min_coordinates, xytext=naive_min_annotation_coordinates,
                 arrowprops=dict(facecolor='black', shrink=0.01, width=1),
                 )
    plt.annotate('global min probability', xy=prob_min_coordinates, xytext=prob_min_annotation_coordinates,
                 arrowprops=dict(facecolor='black', shrink=0.01, width=1),
                 )
    plt.axhline(linewidth=0.5, color='k')
    plt.legend()

    plt.savefig('account_balance_development.pdf', bbox_inches='tight')
    plt.show()

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
