import datetime
import logging
from typing import Tuple

import math
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.stats as stat

from database_operations import execute_sql_postgres

BET_COLUMN_NAMES = ["home", "away", "start_time_utc", "bet_type", "match_part", "odd", "probability", "result",
                    "utc_time_recorded"]


def get_global_extremes_coordinates(array: np.ndarray) -> Tuple[float, float, Tuple[int, float]]:
    minimum = min(array)
    min_coordinates = (np.where(array == minimum)[0][0], minimum)
    return minimum, max(array), min_coordinates


def get_all_bets() -> pd.DataFrame:
    tournament = 'US Open'
    sex = 'men'
    match_type = 'singles'
    params = [tournament, sex, match_type]
    query = "SELECT home, away, start_time_utc, bet_type, match_part, odd, probability, result, utc_time_recorded " \
            "FROM matches " \
            "JOIN tournament t ON matches.tournament_id = t.id " \
            "JOIN matches_bookmaker mb ON matches.id = mb.match_id " \
            "JOIN bet b ON mb.bookmaker_id = b.bookmaker_id AND mb.match_bookmaker_id = b.match_bookmaker_id " \
            "WHERE name = %s AND sex = %s AND type = %s AND result NOTNULL " \
            "ORDER BY utc_time_recorded;"

    return pd.DataFrame(execute_sql_postgres(query, params, False, True), columns=BET_COLUMN_NAMES)


def get_betting_results(all_bets: pd.DataFrame) -> pd.DataFrame:
    naive_betting_win = []
    prob_betting_win = []
    odds_betting_win = []

    balance_naive = [0]
    balance_prob = [0]
    balance_odds = [0]
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

    return all_bets


def get_p_value(observed_values: np.ndarray, expected_values: np.ndarray, variances: np.ndarray) -> float:
    number_observations = len(observed_values)
    x_mean = sum(observed_values) / number_observations
    mu_hat = sum(expected_values) / number_observations
    var_hat = sum(variances) / number_observations
    logging.info(
        f"Observations: {number_observations}. \
        Observed value: {x_mean}, expected value: {mu_hat}, standard deviation: {math.sqrt(var_hat)}")
    expected_distribution = stat.norm()

    observed_value = math.sqrt(number_observations) * (x_mean - mu_hat) / math.sqrt(var_hat)

    cdf_observed = expected_distribution.cdf(observed_value)
    p_value = min(cdf_observed, 1 - cdf_observed) * 2

    logger.info(f"P-value: {p_value}")

    if p_value < 0.1:
        logging.info("Reject H0 on 90% level.")
    else:
        logging.info("Cannot reject H0.")

    if p_value < 0.05:
        logging.info("Reject H0 on 95% level.")

    if p_value < 0.01:
        logging.info("Reject H0 on 99% level.")

    return p_value


def log_result(betting_type: str, minimum: float, maximum: float, final_balance: float):
    logger.info(
        f"{betting_type}: \
        Min = {minimum:.2f}; \
        Max = {maximum:.2f}. \
        Final balance: {final_balance:.2f}")


def generate_diagrams():
    all_bets = get_all_bets()

    all_bets = get_betting_results(all_bets)

    bets = len(all_bets)

    x_axis = range(1, len(all_bets) + 1)
    plt.plot(x_axis, all_bets.naive_balance, 'b-', label='naive')
    plt.plot(x_axis, all_bets.prob_balance, 'r-', label='probability')
    plt.plot(x_axis, all_bets.odds_balance, 'y-', label='1/odds')
    plt.xlabel('bet number')
    plt.ylabel('account balance')

    naive_min, naive_max, naive_min_coordinates = get_global_extremes_coordinates(all_bets.naive_balance)
    naive_min_annotation_coordinates = (naive_min_coordinates[0] - 60, naive_min_coordinates[1] + 0.3)
    plt.annotate('global min naive', xy=naive_min_coordinates, xytext=naive_min_annotation_coordinates,
                 arrowprops=dict(facecolor='black', shrink=0.01, width=1),
                 )

    prob_min, prob_max, prob_min_coordinates = get_global_extremes_coordinates(all_bets.prob_balance)
    prob_min_annotation_coordinates = (prob_min_coordinates[0] - 90, prob_min_coordinates[1] - 1)
    plt.annotate('global min probability and 1/odds', xy=prob_min_coordinates, xytext=prob_min_annotation_coordinates,
                 arrowprops=dict(facecolor='black', shrink=0.01, width=1),
                 )

    odds_min, odds_max, _ = get_global_extremes_coordinates(all_bets.odds_balance)

    plt.axhline(linewidth=0.5, color='k')
    plt.legend()

    plt.savefig('account_balance_development.pdf', bbox_inches='tight')
    plt.show()

    log_result("Naive betting", naive_min, naive_max, all_bets.naive_balance[bets - 1])
    log_result("Prob betting", prob_min, prob_max, all_bets.prob_balance[bets - 1])
    log_result("1/pdds betting", odds_min, odds_max, all_bets.odds_balance[bets - 1])

    get_p_value(all_bets.result, all_bets.probability, all_bets.probability * (1 - all_bets.probability))

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
