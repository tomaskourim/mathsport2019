# functions to extract some descriptive statistics about the available tennis data set
import logging

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import PROBABILITY_BINS
from data_operations import transform_home_favorite, get_probabilities_from_odds


def compute_results(matches_data: pd.DataFrame):
    results = []
    for match_data in matches_data.iterrows():
        results.append(
            " - ".join([str(match_data[1].predicted_player_sets), str(match_data[1].not_predicted_player_sets)]))
    results = np.array(results)
    unique_results, result_indexes, result_count = np.unique(results, return_counts=True, return_index=True)
    for elem in zip(unique_results, result_count):
        logging.info(f"Result {elem[0]} occurs {elem[1]} times.")
    pass


def analyze_data(matches_data: pd.DataFrame, odds_probability_type: str):
    logging.info(f"There were {len(matches_data)} with all necessary information in the dataset.")
    # total players, max, min, avg, med games played
    players = np.concatenate((np.array(matches_data.predicted_player), np.array(matches_data.not_predicted_player)))
    unique_players, player_count = np.unique(players, return_counts=True)
    player_statistics = pd.DataFrame(columns=['Player', 'Matches'])
    player_statistics.Player = unique_players
    player_statistics.Matches = player_count
    player_statistics.sort_values('Matches', ascending=False, inplace=True)
    player_statistics.reset_index(drop=True, inplace=True)
    logging.info(f"There were {len(player_statistics)} unique players involved in the {len(matches_data)} matches.")
    logging.info(f"The most ({player_statistics.Matches[0]}) matches were played by {player_statistics.Player[0]}")
    # this is not very clever, but given the dataset, it will probably be always true
    logging.info(f"The minimum, 1, was played by several players.")
    logging.info(f"The average number of matches played was {np.mean(player_statistics.Matches)}")
    logging.info(f"The median was {np.median(player_statistics.Matches)}.")

    # result histogram
    logging.info(f"Original player ordering from the database.")
    compute_results(matches_data)
    # transform data to favorite first
    matches_data = transform_home_favorite(matches_data)
    logging.info(f"Transformed data, favorite first.")
    compute_results(matches_data)

    # create histogram for data analysis
    # get probabilities from odds
    probabilities = pd.DataFrame(get_probabilities_from_odds(matches_data, odds_probability_type))
    matches_data = matches_data.assign(probability_predicted_player=probabilities[0],
                                       probability_not_predicted_player=probabilities[1])

    matches_data.probability_predicted_player.plot.hist(grid=True, rwidth=0.4, bins=PROBABILITY_BINS)
    plt.xlabel('First set favourite winning probability')
    plt.title(r'Histogram of winning probabilities')
    plt.show()

    # result histogram of groups
    # groups: by odds, selected players, by tournaments
    # most retired and retired against
    # most tournament wins
    # most wins
    # best winning ratio

    pass
