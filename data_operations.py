import numpy as np
import pandas as pd

from constants import FAIR_ODDS_PARAMETER, COLUMN_NAMES
from odds_to_probabilities import probabilities_from_odds


def get_probabilities_from_odds(match_data: pd.DataFrame, odds_probability_type: str) -> list:
    probabilities = []
    for i in range(0, len(match_data)):
        odds = np.array([match_data['odds_predicted_player'][i], match_data['odds_not_predicted_player'][i]])
        probabilities.append(probabilities_from_odds(odds, odds_probability_type, FAIR_ODDS_PARAMETER))

    return probabilities


def predicted_player_won_set(match_data: pd.Series, set: int) -> bool:
    return match_data[f"set{set}predicted_player"] > match_data[f"set{set}not_predicted_player"]


def transform_home_favorite_single(match_data: pd.Series) -> pd.Series:
    tranformed_data = pd.Series(index=COLUMN_NAMES)
    tranformed_data.id = match_data.id
    tranformed_data.predicted_player = match_data.not_predicted_player
    tranformed_data.not_predicted_player = match_data.predicted_player
    tranformed_data.predicted_player_sets = match_data.not_predicted_player_sets
    tranformed_data.not_predicted_player_sets = match_data.predicted_player_sets
    tranformed_data.set1predicted_player = match_data.set1not_predicted_player
    tranformed_data.set1not_predicted_player = match_data.set1predicted_player
    tranformed_data.set2predicted_player = match_data.set2not_predicted_player
    tranformed_data.set2not_predicted_player = match_data.set2predicted_player
    tranformed_data.set3predicted_player = match_data.set3not_predicted_player
    tranformed_data.set3not_predicted_player = match_data.set3predicted_player
    tranformed_data.set4predicted_player = match_data.set4not_predicted_player
    tranformed_data.set4not_predicted_player = match_data.set4predicted_player
    tranformed_data.set5predicted_player = match_data.set5not_predicted_player
    tranformed_data.set5not_predicted_player = match_data.set5predicted_player
    tranformed_data.tournament_name = match_data.tournament_name
    tranformed_data.year = match_data.year
    tranformed_data.odds_predicted_player = match_data.odds_not_predicted_player
    tranformed_data.odds_not_predicted_player = match_data.odds_predicted_player

    return tranformed_data


def transform_home_favorite(matches_data: pd.DataFrame) -> pd.DataFrame:
    transformed_matches = []
    for match_data in matches_data.iterrows():
        if match_data[1].odds_predicted_player <= match_data[1].odds_not_predicted_player:
            transformed_matches.append(list(match_data[1]))
        else:
            transformed_matches.append(list(transform_home_favorite_single(match_data[1])))

    transformed_matches = pd.DataFrame(transformed_matches, columns=COLUMN_NAMES)

    return transformed_matches
