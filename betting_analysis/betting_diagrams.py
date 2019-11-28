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
    betting_win_naive = []
    betting_win_prob = []
    betting_win_odds = []

    expected_betting_win_naive = []
    expected_betting_win_prob = []
    expected_betting_win_odds = []

    variance_betting_win_naive = []
    variance_betting_win_prob = []
    variance_betting_win_odds = []

    balance_naive = [0]
    balance_prob = [0]
    balance_odds = [0]
    for index, bet in all_bets.iterrows():
        probability = bet.probability
        odd = bet.odd
        if bet.result:
            betting_win_naive.append(odd - 1)
            betting_win_prob.append(probability * odd - probability)
            betting_win_odds.append(1 - 1 / odd)
        else:
            betting_win_naive.append(-1)
            betting_win_prob.append(-probability)
            betting_win_odds.append(-1 / odd)

        balance_naive.append(balance_naive[index] + betting_win_naive[index])
        balance_prob.append(balance_prob[index] + betting_win_prob[index])
        balance_odds.append(balance_odds[index] + betting_win_odds[index])

        expected_betting_win_naive.append(probability * odd - 1)
        expected_betting_win_prob.append(probability * (probability * odd - 1))
        expected_betting_win_odds.append(probability - 1 / odd)

        variance_betting_win_naive.append(probability * (odd ** 2) * (1 - probability))
        variance_betting_win_prob.append((probability ** 3) * (odd ** 2) * (1 - probability))
        variance_betting_win_odds.append(probability * (1 - probability))

    all_bets.insert(0, "naive_balance", balance_naive[1:], True)
    all_bets.insert(0, "naive_expected_wins", expected_betting_win_naive, True)
    all_bets.insert(0, "naive_variance_wins", variance_betting_win_naive, True)
    all_bets.insert(0, "naive_wins", betting_win_naive, True)

    all_bets.insert(0, "prob_balance", balance_prob[1:], True)
    all_bets.insert(0, "prob_expected_wins", expected_betting_win_prob, True)
    all_bets.insert(0, "prob_variance_wins", variance_betting_win_prob, True)
    all_bets.insert(0, "prob_wins", betting_win_prob, True)

    all_bets.insert(0, "odds_balance", balance_odds[1:], True)
    all_bets.insert(0, "odds_expected_wins", expected_betting_win_odds, True)
    all_bets.insert(0, "odds_variance_wins", variance_betting_win_odds, True)
    all_bets.insert(0, "odds_wins", betting_win_odds, True)

    return all_bets


def get_p_value(computing_type: str, observed_values: np.ndarray, expected_values: np.ndarray,
                variances: np.ndarray) -> float:
    logging.info(f"----------------------------------------\n\t\tTesting {computing_type}:")
    number_observations = len(observed_values)
    x_mean = sum(observed_values) / number_observations
    mu_hat = sum(expected_values) / number_observations
    var_hat = sum(variances) / number_observations
    logging.info(
        f"Observations: {number_observations}. \
        Observed value: {x_mean:.3f}, expected value: {mu_hat:.3f}, standard deviation: {math.sqrt(var_hat):.3f}")
    expected_distribution = stat.norm()

    observed_value = math.sqrt(number_observations) * (x_mean - mu_hat) / math.sqrt(var_hat)

    cdf_observed = expected_distribution.cdf(observed_value)
    p_value = min(cdf_observed, 1 - cdf_observed) * 2

    logger.info(f"P-value: {p_value:.3f}")

    if p_value < 0.1:
        logging.info("Reject H0 on 90% level.")
    else:
        logging.info("Cannot reject H0.")

    if p_value < 0.05:
        logging.info("Reject H0 on 95% level.")

    if p_value < 0.01:
        logging.info("Reject H0 on 99% level.")

    return p_value


def log_result(betting_type: str, minimum: float, maximum: float, final_balance: float, expected_win: float,
               variance: float):
    logger.info(
        f"{betting_type}: \
        Min = {minimum:.2f}; \
        Max = {maximum:.2f}; \
        Final bal: {final_balance:.2f}; \
        ROI: {final_balance/abs(minimum):.2f} \
        E_win: {expected_win:.2f}; \
        Var: {variance:.2f}.")


def get_expected_resulst(expected_wins: np.ndarray, variance_wins: np.ndarray) -> Tuple[float, float]:
    return sum(expected_wins), sum(variance_wins)


def generate_diagrams():
    all_bets = get_all_bets()
    all_bets = get_betting_results(all_bets)
    number_bets = len(all_bets)

    x_axis = range(1, len(all_bets) + 1)
    plt.plot(x_axis, all_bets.naive_balance, 'b-', label='naive')
    plt.plot(x_axis, all_bets.prob_balance, 'r-', label='probability')
    plt.plot(x_axis, all_bets.odds_balance, 'y-', label='1/odds')
    plt.xlabel('bet number')
    plt.ylabel('account balance')

    naive_min, naive_max, naive_min_coordinates = get_global_extremes_coordinates(all_bets.naive_balance)
    naive_expected_win, naive_variance = get_expected_resulst(all_bets.naive_expected_wins,
                                                              all_bets.naive_variance_wins)
    naive_min_annotation_coordinates = (naive_min_coordinates[0] - 60, naive_min_coordinates[1] + 0.3)
    plt.annotate('global min naive', xy=naive_min_coordinates, xytext=naive_min_annotation_coordinates,
                 arrowprops=dict(facecolor='black', shrink=0.01, width=1),
                 )

    prob_min, prob_max, prob_min_coordinates = get_global_extremes_coordinates(all_bets.prob_balance)
    prob_expected_win, prob_variance = get_expected_resulst(all_bets.prob_expected_wins,
                                                            all_bets.prob_variance_wins)
    prob_min_annotation_coordinates = (prob_min_coordinates[0] - 90, prob_min_coordinates[1] - 1)
    plt.annotate('global min probability and 1/odds', xy=prob_min_coordinates, xytext=prob_min_annotation_coordinates,
                 arrowprops=dict(facecolor='black', shrink=0.01, width=1),
                 )

    odds_min, odds_max, _ = get_global_extremes_coordinates(all_bets.odds_balance)
    odds_expected_win, odds_variance = get_expected_resulst(all_bets.odds_expected_wins,
                                                            all_bets.odds_variance_wins)

    plt.axhline(linewidth=0.5, color='k')
    plt.legend()

    plt.savefig('account_balance_development.pdf', bbox_inches='tight')
    plt.show()

    log_result("Naiv betting", naive_min, naive_max, all_bets.naive_balance[number_bets - 1], naive_expected_win,
               naive_variance)
    log_result("Prob betting", prob_min, prob_max, all_bets.prob_balance[number_bets - 1], prob_expected_win,
               prob_variance)
    log_result("Odds betting", odds_min, odds_max, all_bets.odds_balance[number_bets - 1], odds_expected_win,
               odds_variance)

    get_p_value("result", all_bets.result, all_bets.probability, all_bets.probability * (1 - all_bets.probability))
    get_p_value("naive", all_bets.naive_wins, all_bets.naive_expected_wins, all_bets.naive_variance_wins)
    get_p_value("prob", all_bets.prob_wins, all_bets.prob_expected_wins, all_bets.prob_variance_wins)
    get_p_value("odds", all_bets.odds_wins, all_bets.odds_expected_wins, all_bets.odds_variance_wins)

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
