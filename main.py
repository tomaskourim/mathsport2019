# main file to run the algorithms

import argparse
from datetime import datetime

import numpy as np
import pandas as pd

from database_operations import execute_sql
from odds_to_probabilities import probabilities_from_odds

DATABASE_PATH = 'mathsport2019.sqlite'
FAIR_ODDS_PARAMETER = 0.5


def get_match_data(odds_probability_type):
    sql = "select matches.id, \
            case when home_away.odds_home >= home_away.odds_away then matches.home else matches.away end as favorite, \
            case when home_away.odds_home >= home_away.odds_away then matches.away else matches.home end as outsider, \
            matches.home_sets, matches.away_sets, matches.set1, matches.set2, matches.set3, matches.set4, matches.set5,\
            tournaments.name, tournaments.year, home_away.odds_home, home_away.odds_away from ( \
                (select * from matches where other_result is null) as matches \
                inner join \
                (select * from tournaments) as tournaments \
                ON matches.id_tournament=tournaments.id \
                inner join \
                (select * from home_away where match_part= ? ) as home_away \
                on matches.id=home_away.id_match)"

    match_data = execute_sql(DATABASE_PATH, sql, odds_probability_type)
    return match_data


def get_probabilities_from_odds(match_data, odds_probability_type):
    probabilities = []
    for i in range(0, len(match_data)):
        probabilities.append(
            probabilities_from_odds(np.array([match_data['odds_home'][i], match_data['odds_away'][i]]),
                                    odds_probability_type, FAIR_ODDS_PARAMETER))
    return probabilities


def fit_and_evaluate(first_year, last_year, training_type, odds_probability_type):
    # get matches, results and from database
    match_data = pd.DataFrame(get_match_data(odds_probability_type))
    match_data.columns = ["id", "home", "away", "home_sets", "away_sets", "set1", "set2", "set3", "set4", "set5",
                          "tournament_name", "year", "odds_home", "odds_away"]

    # get probabilities from odds
    probabilities = pd.DataFrame(get_probabilities_from_odds(match_data, odds_probability_type))
    match_data = match_data.assign(probability_home=probabilities[0], probability_away=probabilities[1])

    # iterate over training sets
    years = match_data.year.unique()

    # fit the model - find optimal lambda
    # apply the model - evaluate success rate
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
