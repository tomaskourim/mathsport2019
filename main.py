# main file to run the algorithms
import argparse
from datetime import datetime
from typing import Optional, Tuple, List

import math
import numpy as np
import pandas as pd
import scipy.optimize as opt
import scipy.stats as stat

import constants
from data_operations import transform_home_favorite, get_probabilities_from_odds, predicted_player_won_set
from database_operations import get_match_data
from descriptive_statistics import analyze_data


def log_likelihood_single_lambda(c_lambda: float, matches_data: pd.DataFrame, return_observations: bool = False) -> \
        Tuple[float, Optional[pd.DataFrame]]:
    log_likelihood = 0
    if return_observations:
        observations = pd.DataFrame(
            columns=["predicted_player", "not_predicted_player", "tournament_name", "year",
                     "first_set_prob", "set_number", "probability", "result"])
    for match_data in matches_data.iterrows():
        p_set = match_data[1][
            "probability_predicted_player"]  # probability of winning 1.set, not subject to optimization
        if return_observations:
            current_observation = {"predicted_player": match_data[1].predicted_player,
                                   "not_predicted_player": match_data[1].not_predicted_player,
                                   "tournament_name": match_data[1].tournament_name,
                                   "year": match_data[1].year,
                                   "first_set_prob": match_data[1].probability_predicted_player}
        for _set in range(1, match_data[1]["predicted_player_sets"] + match_data[1]["not_predicted_player_sets"]):
            p_set = c_lambda * p_set + 1 / 2 * (1 - c_lambda) * (
                    1 + (1 if predicted_player_won_set(match_data[1], _set) else -1))
            result = 1 if predicted_player_won_set(match_data[1], _set + 1) else 0
            log_likelihood = log_likelihood + np.log(p_set * result + (1 - p_set) * (1 - result))
            if return_observations:
                set_observation = {
                    "set_number": _set + 1,
                    "probability": p_set,
                    "result": result
                }
                current_observation.update(set_observation)
                observations = observations.append(current_observation, ignore_index=True)

    if return_observations:
        return log_likelihood, observations
    else:
        return log_likelihood, None


# just for the sake of minimization
def negative_log_likelihood(c_lambda: float, matches_data: pd.DataFrame) -> float:
    return - log_likelihood_single_lambda(c_lambda, matches_data)[0]


def find_single_lambda(training_set: pd.DataFrame) -> Optional[float]:
    opt_result = opt.minimize_scalar(negative_log_likelihood, bounds=(0, 1), method='bounded', args=training_set)
    if opt_result.success:
        print("Fitted successfully.")
        return opt_result.x
    else:
        return None


def evaluate_observations_single_lambda(observations: pd.DataFrame) -> float:
    num_observations = len(observations)
    if num_observations == 0:
        print("No observations for current setting, skipping.")
        return 1
    x_mean = sum(observations.result) / num_observations
    mu_hat = sum(observations.probability) / num_observations
    var_hat = sum(observations.probability * (1 - observations.probability)) / num_observations
    print(f"Observations: {len(observations)}. Observed value: {x_mean}, expected value: {mu_hat}, \
            standard deviation: {math.sqrt(var_hat)}")
    expected_distribution = stat.norm()

    observed_value = math.sqrt(num_observations) * (x_mean - mu_hat) / math.sqrt(var_hat)

    cdf_observed = expected_distribution.cdf(observed_value)
    probability_of_more_extreme = min(cdf_observed, 1 - cdf_observed) * 2

    print(f"Cumulative distribution function at observed value F({observed_value}) = {cdf_observed}.")
    print(f"Probability of more extreme value: {probability_of_more_extreme}.")

    if probability_of_more_extreme < 0.1:
        print("Reject H0 on 90% level.")
    else:
        print("Cannot reject H0.")

    if probability_of_more_extreme < 0.05:
        print("Reject H0 on 95% level.")

    if probability_of_more_extreme < 0.01:
        print("Reject H0 on 99% level.")
    return probability_of_more_extreme


def evaluate_single_lambda_tournaments(observations: pd.DataFrame) -> List[float]:
    result = []
    for tournament in constants.TOURNAMENTS:
        print(f"\nEvaluating {tournament}")
        observations_current = observations[observations.tournament_name == tournament]
        result.append(evaluate_observations_single_lambda(observations_current))

    print(f"\nEvaluating probability groups.")
    for i in range(0, len(constants.PROBABILITY_BINS) - 1):
        lower_bound = constants.PROBABILITY_BINS[i]
        upper_bound = constants.PROBABILITY_BINS[i + 1]
        print(f"\nEvaluating: {lower_bound} <= probability < {upper_bound}")
        observations_current = observations[
            (lower_bound <= observations.first_set_prob) & (observations.first_set_prob < upper_bound)]
        result.append(evaluate_observations_single_lambda(observations_current))

    print(f"\nEvaluating all set groups together.")
    result.append(evaluate_observations_single_lambda(observations))

    return result


def evaluate_single_lambda(c_lambda: float, matches_data: pd.DataFrame) -> pd.DataFrame:
    _, observations = log_likelihood_single_lambda(c_lambda, matches_data, True)

    possible_sets = list(range(2, 2 * constants.SETS_TO_WIN))
    result = pd.DataFrame(
        columns=constants.TOURNAMENTS + constants.PROBABILITY_BINS[1:len(constants.PROBABILITY_BINS)] + [
            "All groups"], index=possible_sets + ["All sets"])

    print("Starting evaluation:")
    for set_number in possible_sets:
        print('-----------------------------------------------------------')
        print(f"\nEvaluating set number {set_number}:")
        observations_set = observations[observations.set_number == set_number]
        result.loc[set_number, :] = evaluate_single_lambda_tournaments(observations_set)

    print('-----------------------------------------------------------')
    print(f"\nEvaluating all sets together:")
    result.loc["All sets", :] = evaluate_single_lambda_tournaments(observations)

    return result


def fit_and_evaluate(matches_data: pd.DataFrame, first_year: int, last_year: int, training_type: str,
                     odds_probability_type: str, do_transform_home_favorite: bool):
    # transform data so that home <=> favorite. Originally, home player, i.e. the player listed first, is considered
    # predicted player. However, predicting the favorite seems reasonable.
    if do_transform_home_favorite:
        matches_data = transform_home_favorite(matches_data)

    # get probabilities from odds
    probabilities = pd.DataFrame(get_probabilities_from_odds(matches_data, odds_probability_type))
    matches_data = matches_data.assign(probability_predicted_player=probabilities[0],
                                       probability_not_predicted_player=probabilities[1])

    results = {}
    lambdas = {}
    # iterate over training sets
    years = matches_data.year.unique()
    for year in range(first_year, last_year):  # TODO try different training/testing splits
        if year == years[len(years) - 1]:
            break
        # fit the model - find optimal lambda
        print('----------------------------------------------------------------------------------------------')
        print('----------------------------------------------------------------------------------------------')
        print(year)
        training_set = matches_data[matches_data["year"] == year]
        if len(training_set) == 0:
            continue
        c_lambda = find_single_lambda(training_set)  # lambda is a Python keyword
        if c_lambda is None:
            print(f"Unable to find optimal lambda in year {year}")
            continue

        print(f"Optimal lambda is: {c_lambda}. Value of corresponding log-likelihood is: "
              f"{log_likelihood_single_lambda(c_lambda, training_set)[0]}")

        # apply the model - evaluate success rate
        testing_set = matches_data[matches_data["year"] == year + 1]
        results[year + 1] = evaluate_single_lambda(c_lambda, testing_set)
        lambdas[year + 1] = c_lambda

    # export results
    results_df = pd.concat(results)
    results_df.to_excel(f"results/output_favorite_first_{do_transform_home_favorite}.xlsx")

    lambdas_df = pd.DataFrame.from_dict(lambdas, orient='index', columns=['Optimal lambda'])
    lambdas_df.to_excel(f"results/lambdas_favorite_first_{do_transform_home_favorite}.xlsx")

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
    parser.add_argument("--do_transform_home_favorite",
                        help="Boolean specifying whether to use default player to predict or to transform data" +
                             "so that favorite odds are always predicted.", required=False, default="True")

    args = parser.parse_args()

    input_first_year = args.first_year
    input_last_year = args.last_year
    input_training_type = args.training_type
    input_odds_probability_type = args.odds_probability_type
    input_do_transform_home_favorite = args.do_transform_home_favorite == "True"
    if args.database_path is not None:
        constants.DATABASE_PATH = args.database_path
    if args.fair_odds_parameter is not None:
        constants.FAIR_ODDS_PARAMETER = args.fair_odds_parameter

    # get matches, results and odds from database
    initial_matches_data = pd.DataFrame(get_match_data(input_odds_probability_type), columns=constants.COLUMN_NAMES)

    fit_and_evaluate(initial_matches_data, input_first_year, input_last_year, input_training_type,
                     input_odds_probability_type, input_do_transform_home_favorite)

    analyze_data(initial_matches_data, input_odds_probability_type)

    end_time = datetime.now()
    print(f"\nDuration: {(end_time - start_time)}")
