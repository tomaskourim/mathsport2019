# main file to run the algorithms

import argparse
from datetime import datetime
from typing import Tuple, Union

import numpy as np
import pandas as pd
import scipy.optimize as opt

from database_operations import execute_sql
from odds_to_probabilities import probabilities_from_odds

DATABASE_PATH = 'mathsport2019.sqlite'
FAIR_ODDS_PARAMETER = 0.5


def get_match_data(odds_probability_type: str) -> list:
    sql = "select matches.id, matches.home, matches.away, matches.home_sets, matches.away_sets, \
            matches.set1home, matches.set1away, matches.set2home, matches.set2away, matches.set3home, matches.set3away,\
            matches.set4home, matches.set4away, matches.set5home, matches.set5away, tournaments.name, tournaments.year,\
            home_away.odds_home, home_away.odds_away \
            from ( \
                (select * from matches where other_result is null) as matches \
                inner join \
                (select * from tournaments) as tournaments \
                ON matches.id_tournament=tournaments.id \
                inner join \
                (select * from home_away where match_part= ? ) as home_away \
                on matches.id=home_away.id_match)"

    match_data = execute_sql(DATABASE_PATH, sql, odds_probability_type)
    return match_data


def get_probabilities_from_odds(match_data: pd.DataFrame, odds_probability_type: str) -> list:
    probabilities = []
    for i in range(0, len(match_data)):
        probabilities.append(
            probabilities_from_odds(np.array([match_data['odds_home'][i], match_data['odds_away'][i]]),
                                    odds_probability_type, FAIR_ODDS_PARAMETER))
    return probabilities


def home_won_set(match_data: pd.Series, set: int) -> bool:
    return match_data[f"set{set}home"] > match_data[f"set{set}away"]


def log_likelihood_single_lambda(c_lambda: int, matches_data: pd.DataFrame, return_observations: bool = False) -> \
        Union[int, Tuple[int, pd.DataFrame]]:
    log_likelihood = 0
    if return_observations:
        observations = pd.DataFrame(columns=['probability', 'result'])
    for match_data in matches_data.iterrows():
        p_set = match_data[1]["probability_home"]  # probability of home winning 1.set, not subject to optimization
        for set in range(1, match_data[1]["home_sets"] + match_data[1]["away_sets"]):
            p_set = c_lambda * p_set + 1 / 2 * (1 - c_lambda) * (1 + (1 if home_won_set(match_data[1], set) else -1))
            result = 1 if home_won_set(match_data[1], set + 1) else 0
            log_likelihood = log_likelihood + np.log(p_set * result + (1 - p_set) * (1 - result))
            if return_observations:
                observations = observations.append({
                    "probability": p_set,
                    "result": result
                }, ignore_index=True)

    if return_observations:
        return log_likelihood, observations
    else:
        return log_likelihood


# just for the sake of minimalization
def negative_log_likelihood(c_lambda: int, matches_data: pd.DataFrame) -> int:
    return - log_likelihood_single_lambda(c_lambda, matches_data)


def find_single_lambda(training_set: pd.DataFrame) -> int:
    return opt.minimize_scalar(negative_log_likelihood, bounds=(0, 1), method='bounded', args=training_set).x


def evaluate_single_lambda(c_lambda: int, matches_data: pd.DataFrame):
    pass


def fit_and_evaluate(first_year: int, last_year: int, training_type: str, odds_probability_type: str):
    # get matches, results and from database
    matches_data = pd.DataFrame(get_match_data(odds_probability_type))
    matches_data.columns = ["id", "home", "away", "home_sets", "away_sets",
                            "set1home", "set1away", "set2home", "set2away", "set3home", "set3away",
                            "set4home", "set4away", "set5home", "set5away",
                            "tournament_name", "year", "odds_home", "odds_away"]

    # get probabilities from odds
    probabilities = pd.DataFrame(get_probabilities_from_odds(matches_data, odds_probability_type))
    matches_data = matches_data.assign(probability_home=probabilities[0], probability_away=probabilities[1])

    # iterate over training sets
    years = matches_data.year.unique()
    for year in range(first_year, last_year):
        if year == years[len(years) - 1]:
            continue
        # fit the model - find optimal lambda
        print('-----------------------')
        print(year)
        training_set = matches_data[matches_data["year"] == year]
        if len(training_set) == 0:
            continue
        c_lambda = find_single_lambda(training_set)  # lambda is a Python keyword
        print(f"Optimal lambda is: {c_lambda}. Value of corresponding log-likelihood is: "
              f"{log_likelihood_single_lambda(c_lambda, training_set)}")

        # apply the model - evaluate success rate
        testing_set = matches_data[matches_data["year"] == year + 1]
        evaluate_single_lambda(c_lambda, testing_set)

    # export results
    pass


if __name__ == '__main__':
    start_time = datetime.now()

    parser = argparse.ArgumentParser(
        description="Prepares a relevant, lightweight database for the purpose of this project out of a much larger \
        and complex database available to the author.")
    parser.add_argument("--first_year", help="The first tennis season to be considered", default=2009, required=False)
    parser.add_argument("--last_year", help="The last tennis season to be considered", default=2018, required=False)
    parser.add_argument("--training_type", help="Whether to learn from one previous season only or from all",
                        default='all', required=False)
    parser.add_argument("--odds_probability_type", help="How to get probabilities from odds",
                        default='1.set', required=False)
    parser.add_argument("--database_path", help="Path to the original database", required=False)
    parser.add_argument("--fair_odds_parameter", help="Parameter used to compute probabilities from odds",
                        required=False)

    args = parser.parse_args()

    first_year = args.first_year
    last_year = args.last_year
    training_type = args.training_type
    odds_probability_type = args.odds_probability_type
    if args.database_path is not None:
        DATABASE_PATH = args.database_path
    if args.fair_odds_parameter is not None:
        FAIR_ODDS_PARAMETER = args.fair_odds_parameter

    fit_and_evaluate(first_year, last_year, training_type, odds_probability_type)

    end_time = datetime.now()
    print(f"Duration: {(end_time - start_time)}")
