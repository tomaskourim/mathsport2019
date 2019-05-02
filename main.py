# main file to run the algorithms

import argparse
from datetime import datetime

DATABASE_PATH = 'mathsport2019.sqlite'


def fit_and_evaluate(first_year, last_year, training_type, odds_probability_type):
    # get matches, results and from database
    # get probabilities from odds
    # iterate over training sets
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
                        default='fulltime', required=False)
    parser.add_argument("--database_path", help="Path to the original database", required=False)

    args = parser.parse_args()

    first_year = args.first_year
    last_year = args.last_year
    training_type = args.training_type
    odds_probability_type = args.odds_probability_type
    if args.database_path is not None:
        DATABASE_PATH = args.database_path

    fit_and_evaluate(first_year, last_year, training_type, odds_probability_type)

    end_time = datetime.now()
    print('Duration: {}'.format(end_time - start_time))
