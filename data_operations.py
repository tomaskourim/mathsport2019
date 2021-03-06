# support functions handling specific data structures

import numpy as np
import pandas as pd

from config import FAIR_ODDS_PARAMETER, COLUMN_NAMES
from odds_to_probabilities import probabilities_from_odds


def get_probabilities_from_odds(match_data: pd.DataFrame, odds_probability_type: str) -> list:
    probabilities = []
    for i in range(0, len(match_data)):
        odds = np.array([match_data['odds_predicted_player'][i], match_data['odds_not_predicted_player'][i]])
        probabilities.append(probabilities_from_odds(odds, odds_probability_type, FAIR_ODDS_PARAMETER))

    return probabilities


def predicted_player_won_set(match_data: pd.Series, _set: int) -> bool:
    return match_data[f"set{_set}predicted_player"] > match_data[f"set{_set}not_predicted_player"]


def transform_home_favorite_single(match_data: pd.Series) -> pd.Series:
    transformed_data = pd.Series(index=COLUMN_NAMES)
    transformed_data.id = match_data.id
    transformed_data.predicted_player = match_data.not_predicted_player
    transformed_data.not_predicted_player = match_data.predicted_player
    transformed_data.predicted_player_sets = match_data.not_predicted_player_sets
    transformed_data.not_predicted_player_sets = match_data.predicted_player_sets
    transformed_data.set1predicted_player = match_data.set1not_predicted_player
    transformed_data.set1not_predicted_player = match_data.set1predicted_player
    transformed_data.set2predicted_player = match_data.set2not_predicted_player
    transformed_data.set2not_predicted_player = match_data.set2predicted_player
    transformed_data.set3predicted_player = match_data.set3not_predicted_player
    transformed_data.set3not_predicted_player = match_data.set3predicted_player
    transformed_data.set4predicted_player = match_data.set4not_predicted_player
    transformed_data.set4not_predicted_player = match_data.set4predicted_player
    transformed_data.set5predicted_player = match_data.set5not_predicted_player
    transformed_data.set5not_predicted_player = match_data.set5predicted_player
    transformed_data.tournament_name = match_data.tournament_name
    transformed_data.year = match_data.year
    transformed_data.odds_predicted_player = match_data.odds_not_predicted_player
    transformed_data.odds_not_predicted_player = match_data.odds_predicted_player

    return transformed_data


def transform_home_favorite(matches_data: pd.DataFrame) -> pd.DataFrame:
    transformed_matches = []
    for match_data in matches_data.iterrows():
        if match_data[1].odds_predicted_player <= match_data[1].odds_not_predicted_player:
            transformed_matches.append(list(match_data[1]))
        else:
            transformed_matches.append(list(transform_home_favorite_single(match_data[1])))

    transformed_matches = pd.DataFrame(transformed_matches, columns=COLUMN_NAMES)

    return transformed_matches
