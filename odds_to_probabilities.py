# functions to transfer bookmaker's odds into probabilities

EVEN_ODDS_PROBABILITY = 0.5
SETS_TO_WIN = 3


def get_first_set_odds_from_fulltime(odds, fair_odds_parameter):
    # TODO
    pass


def get_fair_odds(odds, fair_odds_parameter):
    odds_probability_norm = sum(1 / odds)
    normalized_odds_probabilities = 1 / (odds * odds_probability_norm)
    odds_weights = (1 - normalized_odds_probabilities) + (
            normalized_odds_probabilities - EVEN_ODDS_PROBABILITY) * fair_odds_parameter * 1 / EVEN_ODDS_PROBABILITY
    probabilities = 1 / odds - odds_weights * (odds_probability_norm - 1)

    return probabilities


def probabilities_from_odds(odds, odds_probability_type, fair_odds_parameter):
    if odds_probability_type == '1.set':
        return get_fair_odds(odds, fair_odds_parameter)
    elif odds_probability_type == 'fulltime':
        return get_first_set_odds_from_fulltime(odds, fair_odds_parameter)
    else:
        raise Exception(f'odds_probability_type should be 1.set or fulltime, but {odds_probability_type} was provided')
