import datetime
import logging

import math
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.stats as stat

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

    bets = len(all_bets)

    naive_betting_win = []
    prob_betting_win = []
    odds_betting_win = []
    kelly_betting_win = []

    balance_naive = [0]
    balance_prob = [0]
    balance_odds = [0]
    balance_kelly = [50]
    for index, bet in all_bets.iterrows():
        if bet.result:
            naive_betting_win.append(bet.odd - 1)
            prob_betting_win.append(bet.probability * bet.odd - bet.probability)
            odds_betting_win.append(1 - 1 / bet.odd)
        else:
            naive_betting_win.append(-1)
            prob_betting_win.append(-bet.probability)
            odds_betting_win.append(-1 / bet.odd)

        balance_naive.append(balance_naive[index] + naive_betting_win[index])
        balance_prob.append(balance_prob[index] + prob_betting_win[index])
        balance_odds.append(balance_odds[index] + odds_betting_win[index])

    all_bets.insert(0, "naive_balance", balance_naive[1:], True)
    all_bets.insert(0, "naive_wins", naive_betting_win, True)

    all_bets.insert(0, "prob_balance", balance_prob[1:], True)
    all_bets.insert(0, "prob_wins", prob_betting_win, True)

    all_bets.insert(0, "odds_balance", balance_odds[1:], True)
    all_bets.insert(0, "odds_wins", odds_betting_win, True)

    x_axis = range(1, len(all_bets) + 1)
    plt.plot(x_axis, all_bets.naive_balance, 'b-', label='naive')
    plt.plot(x_axis, all_bets.prob_balance, 'r-', label='probability')
    plt.plot(x_axis, all_bets.odds_balance, 'y-', label='1/odds')
    plt.xlabel('bet number')
    plt.ylabel('account balance')

    naive_min = min(all_bets.naive_balance)
    naive_min_coordinates = (np.where(all_bets.naive_balance == naive_min)[0][0], naive_min)
    naive_min_annotation_coordinates = (naive_min_coordinates[0] - 60, naive_min_coordinates[1] + 0.3)
    plt.annotate('global min naive', xy=naive_min_coordinates, xytext=naive_min_annotation_coordinates,
                 arrowprops=dict(facecolor='black', shrink=0.01, width=1),
                 )

    prob_min = min(all_bets.prob_balance)
    prob_min_coordinates = (np.where(all_bets.prob_balance == prob_min)[0][0], prob_min)
    prob_min_annotation_coordinates = (prob_min_coordinates[0] - 90, prob_min_coordinates[1] - 1)
    plt.annotate('global min probability and 1/odds', xy=prob_min_coordinates, xytext=prob_min_annotation_coordinates,
                 arrowprops=dict(facecolor='black', shrink=0.01, width=1),
                 )

    odds_min = min(all_bets.odds_balance)
    # odds_min_coordinates = (np.where(all_bets.odds_balance == odds_min)[0][0], odds_min)
    # odds_min_annotation_coordinates = (odds_min_coordinates[0] - 20, odds_min_coordinates[1] + 6)
    # plt.annotate('global min 1/odds', xy=odds_min_coordinates, xytext=odds_min_annotation_coordinates,
    #              arrowprops=dict(facecolor='black', shrink=0.01, width=1),
    #              )

    plt.axhline(linewidth=0.5, color='k')
    plt.legend()

    plt.savefig('account_balance_development.pdf', bbox_inches='tight')
    plt.show()

    logger.info(naive_min)
    logger.info(prob_min)
    logger.info(odds_min)

    logger.info(max(all_bets.naive_balance))
    logger.info(max(all_bets.prob_balance))
    logger.info(max(all_bets.odds_balance))

    logger.info(all_bets.naive_balance[bets - 1])
    logger.info(all_bets.prob_balance[bets - 1])
    logger.info(all_bets.odds_balance[bets - 1])

    x_mean = sum(all_bets.result) / bets
    mu_hat = sum(all_bets.probability) / bets
    var_hat = sum(all_bets.probability * (1 - all_bets.probability)) / bets
    logging.info(f"Observations: {bets}. Observed value: {x_mean}, expected value: {mu_hat}, \
            standard deviation: {math.sqrt(var_hat)}")
    expected_distribution = stat.norm()

    observed_value = math.sqrt(bets) * (x_mean - mu_hat) / math.sqrt(var_hat)

    cdf_observed = expected_distribution.cdf(observed_value)
    probability_of_more_extreme = min(cdf_observed, 1 - cdf_observed) * 2

    logger.info(f"P-value: {probability_of_more_extreme}")

    if probability_of_more_extreme < 0.1:
        logging.info("Reject H0 on 90% level.")
    else:
        logging.info("Cannot reject H0.")

    if probability_of_more_extreme < 0.05:
        logging.info("Reject H0 on 95% level.")

    if probability_of_more_extreme < 0.01:
        logging.info("Reject H0 on 99% level.")

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
