import datetime
import json
import logging
import time
from typing import List, Tuple

import numpy as np
import pandas as pd
import pytz
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement

from config import FAIR_ODDS_PARAMETER
from live_betting.bookmaker import Bookmaker
from live_betting.config_betting import CREDENTIALS_PATH, MINUTES_PER_GAME
from live_betting.inplay_operations import save_set_odds, evaluate_bet_on_set, home_won_set, save_bet
from live_betting.utils import load_fb_credentials, write_id, click_id
from odds_to_probabilities import probabilities_from_odds


class Tipsport(Bookmaker):
    def __init__(self):
        Bookmaker.__init__(self, "https://www.tipsport.cz", "Tipsport")
        self.tennis_id = 43
        self.tennis_tournament_base_url = "https://www.tipsport.cz/kurzy/a/a/a-"
        self.tennis_match_base_url = "https://www.tipsport.cz/tenis-"
        self.tennis_match_live_base_url = "https://www.tipsport.cz/live/tenis/"

    def login(self):
        username, password = load_fb_credentials(CREDENTIALS_PATH)
        write_id(self.driver, "userNameId", username)
        write_id(self.driver, "passwordId", password)
        click_id(self.driver, "btnLogin")
        time.sleep(self.seconds_to_sleep)  # some time in seconds for the website to load

    def get_tournaments(self) -> pd.DataFrame():
        self.driver.get("https://www.tipsport.cz/kurzy/tenis-43#superSportId=43")
        time.sleep(self.seconds_to_sleep)  # some time in seconds for the website to load
        self.scroll_to_botton()
        elements = self.driver.find_elements_by_xpath("//div[@class='colCompetition']")
        texts = []
        tournament_year_ids = []
        tournament_ids = []
        for e in elements:
            texts.append(e.find_element_by_xpath(".//h2").text)
            tournament_year_ids.append(e.get_attribute("data-competition-annual-id"))
            tournament_ids.append(str(json.loads(e.get_attribute("data-model"))['id']))

        tournaments = self.obtain_tournaments_from_texts(texts)
        tournaments["tournament_bookmaker_year_id"] = tournament_year_ids
        tournaments["tournament_bookmaker_id"] = tournament_ids
        return tournaments

    def get_inplay_tournaments(self) -> pd.DataFrame():
        self.driver.get("https://www.tipsport.cz/live")
        time.sleep(self.seconds_to_sleep)  # some time in seconds for the website to load
        elements = self.driver.find_elements_by_xpath(
            f"//div[@data-id='{self.tennis_id}']//span[@class='nameMatchesGroup']")
        texts = []
        for e in elements:
            texts.append(e.text)
        return self.obtain_tournaments_from_texts(texts)

    @staticmethod
    def obtain_tournaments_from_texts(texts: List[str]) -> pd.DataFrame():
        tournaments = pd.DataFrame(columns=["sex", "type", "surface", "name"])
        for text in texts:  # the page is constantly reloading and the original elements are then no longer attached
            if len(text) == 0:
                continue
            tournament = {}
            if "muži" in text:
                tournament["sex"] = "men"
                text = text.replace(", Tenis muži - ", "")
            elif "ženy" in text:
                tournament["sex"] = "women"
                text = text.replace(", Tenis ženy - ", "")
            else:
                tournament["sex"] = None

            if "dvouhra" in text:
                tournament["type"] = "singles"
                text = text.replace("dvouhra", "")
            elif "čtyřhra" in text:
                tournament["type"] = "doubles"
                text = text.replace("čtyřhra", "")
            elif "družstva" in text:
                tournament["type"] = "teams"
                text = text.replace("družstva", "")
            else:
                tournament["type"] = None

            if "tráva" in text:
                tournament["surface"] = "grass"
                text = text.replace(" - tráva", "")
            elif "antuka" in text:
                tournament["surface"] = "clay"
                text = text.replace(" - antuka", "")
            elif "tvrdý povrch" in text:
                tournament["surface"] = "hard"
                text = text.replace(" - tvrdý povrch", "")
            else:
                tournament["surface"] = None

            tournament["tournament_name"] = text.strip()
            tournaments = tournaments.append(tournament, ignore_index=True)

        return tournaments

    def get_matches_tournament(self, tournament: pd.DataFrame) -> pd.DataFrame:
        self.driver.get("".join([self.tennis_tournament_base_url, str(tournament.tournament_bookmaker_id)]))
        time.sleep(self.seconds_to_sleep)
        elements = self.driver.find_elements_by_xpath("//div[@class='rowMatchWrapper']")
        home = []
        away = []
        matchid = []
        start_time_utc = []
        for e in elements:
            base_info = e.find_element_by_xpath("./div")
            players = base_info.get_attribute("data-matchname")
            if "celkově" in players:
                continue
            players_splitted = players.split(" - ")
            if len(players_splitted) != 2:
                players_splitted = players.split("-")
            if len(players_splitted) != 2:
                logging.warning(
                    f"Impossible to find two players in tournament {tournament.tournament_name}. Found text: {players}")
                continue
            home.append(players_splitted[0])
            away.append(players_splitted[1])
            matchid.append(base_info.get_attribute("data-matchid"))
            starting_time = datetime.datetime.strptime(
                e.find_elements_by_xpath(".//div[@class='actualState']")[1].text, '%d.%m.%Y %H:%M')
            starting_time = pytz.timezone('Europe/Berlin').localize(starting_time).astimezone(pytz.utc)
            start_time_utc.append(starting_time)

        matches = pd.DataFrame(zip(home, away, matchid, start_time_utc),
                               columns=["home", "away", "bookmaker_matchid", "start_time_utc"])
        return matches

    def handle_match(self, bookmaker_matchid: str, c_lambda: float):
        starting_odds = self.handle_prematch(bookmaker_matchid)
        home_probability = probabilities_from_odds(np.asarray(starting_odds), "1.set", FAIR_ODDS_PARAMETER)[0]
        self.handle_inplay(bookmaker_matchid, home_probability, c_lambda)

    def handle_inplay(self, bookmaker_matchid: str, home_probability: float, c_lambda: float):
        self.driver.get("".join([self.tennis_match_live_base_url, bookmaker_matchid]))
        time.sleep(self.seconds_to_sleep)

        set_number = 1
        last_set_score = (0, 0)
        # while match not finished
        while ~self.match_finished():
            # wait for the set to finish
            current_set_score = self.wait_for_set_end(set_number, last_set_score)
            home_probability = self.evaluate_and_bet(last_set_score, current_set_score, c_lambda, bookmaker_matchid,
                                                     set_number, home_probability)
            last_set_score = current_set_score
            set_number = set_number + 1

        pass

    def handle_prematch(self, bookmaker_matchid) -> tuple:
        self.driver.get("".join([self.tennis_match_base_url, bookmaker_matchid]))
        time.sleep(self.seconds_to_sleep)
        click_id(self.driver, "matchName" + bookmaker_matchid)
        time.sleep(self.short_seconds_to_sleep)

        last_odds = (None, None)
        current_odds = (None, None)
        while ~self.match_started():
            current_odds = self.get_set_odds(1)
            if current_odds != last_odds:
                save_set_odds(current_odds, self.database_id, bookmaker_matchid, 1)
                last_odds = current_odds
            self.wait_half_to_matchstart()
            self.driver.refresh()
            time.sleep(self.short_seconds_to_sleep)
            click_id(self.driver, "matchName" + bookmaker_matchid)
            time.sleep(self.short_seconds_to_sleep)
        return current_odds

    def get_base_odds_element(self, set_number: int) -> WebElement:
        return self.driver.find_element_by_xpath(f"//span[@title='Vítěz {set_number}. setu']")

    def get_set_odds(self, set_number: int) -> tuple:
        elem_base = self.get_base_odds_element(set_number)
        elem_odds = elem_base.find_elements_by_xpath("./../../..//div[@class='tdEventCells']//span")
        odds = (elem_odds[1].text, elem_odds[3].text)
        return odds

    def match_started(self) -> bool:
        elem_base = self.get_base_odds_element(1)
        elem_odds = elem_base.find_elements_by_xpath("../../..//div[@class='tdEventCells']/div")
        starting_time = self.get_starting_time()
        utc_time = pytz.utc.localize(datetime.datetime.utcnow())
        if starting_time - utc_time < datetime.timedelta(seconds=30):
            if "disabled" in elem_odds[0].get_attribute("class") and "disabled" in elem_odds[1].get_attribute(
                    "class"):
                logging.error(f"Match started at: {datetime.datetime.now()}")
                return True
        return False

    def wait_half_to_matchstart(self):
        starting_time = self.get_starting_time()
        utc_time = pytz.utc.localize(datetime.datetime.utcnow())
        seconds_to_sleep = max((starting_time - utc_time).total_seconds() / 2, self.seconds_to_sleep)
        time.sleep(seconds_to_sleep)
        pass

    def get_starting_time(self) -> datetime:
        starting_time = datetime.datetime.strptime(
            self.driver.find_elements_by_xpath("//div[@class='actualState']")[1].text, '%d.%m.%Y %H:%M')
        starting_time = pytz.timezone('Europe/Berlin').localize(starting_time).astimezone(pytz.utc)
        return starting_time

    def evaluate_and_bet(self, last_set_score: tuple, current_set_score: tuple, c_lambda: float, bookmaker_matchid: str,
                         set_number: int, home_probability: float) -> float:
        # evaluate last bet
        if set_number > 1:
            evaluate_bet_on_set(last_set_score, current_set_score, self.database_id, bookmaker_matchid, set_number)
        # save odds for next set
        set_odds = self.get_set_odds(set_number + 1)
        save_set_odds(set_odds, self.database_id, bookmaker_matchid, set_number + 1)

        # bet on next set
        home_probability = self.bet_set(home_probability, set_odds, last_set_score, current_set_score, c_lambda,
                                        bookmaker_matchid, set_number)
        return home_probability

    def match_finished(self):
        try:
            self.driver.find_element_by_xpath("//span[@class='removalCountdownText']")
            return True
        except NoSuchElementException:
            return False

    def bet_set(self, home_probability: float, set_odds: tuple, last_set_score: tuple, current_set_score: tuple,
                c_lambda: float, bookmaker_matchid: str, set_number: int):

        home_probability = c_lambda * home_probability + 1 / 2 * (1 - c_lambda) * (
                1 + (1 if home_won_set(current_set_score, last_set_score) else -1))
        # bet if possible
        if home_probability > 1 / set_odds[0]:
            self.bet('home', bookmaker_matchid, set_number, set_odds[0], home_probability)
        if (1 - home_probability) > 1 / set_odds[1]:
            self.bet('away', bookmaker_matchid, set_number, set_odds[1], 1 - home_probability)

        return home_probability

    def wait_for_set_end(self, set_number: int, last_set_state: tuple) -> tuple:

        while True:
            try:
                # with live video stream
                set_score, game_score = self.get_score_with_video(set_number)
            except NoSuchElementException:
                # w/out live video stream
                set_score, game_score = self.get_score_without_video(set_number)
            if last_set_state != set_score:
                return set_score
            elif max(game_score) < 5:
                time.sleep((5 - max(game_score)) * MINUTES_PER_GAME * 60)  # wait minimal number of games to play
            elif game_score[0] == 5 and game_score[1] == 5:
                time.sleep(MINUTES_PER_GAME * 60)  # wait 1 game
            else:
                time.sleep(MINUTES_PER_GAME * 15)  # wait quarter of game

    def get_score_with_video(self, set_number: int) -> Tuple[Tuple[int, ...], Tuple[int, ...]]:
        raw_text = self.driver.find_element_by_xpath("//span[@class='m-scoreOffer__msg']").text
        set_score = raw_text[:3].split(':')
        set_score = [int(x) for x in set_score]
        game_score = raw_text.split(' - ')[1].split(' ')[set_number - 1].split(':')
        game_score = [int(x) for x in game_score]
        return tuple(set_score), tuple(game_score)

    def get_score_without_video(self, set_number: int) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        elems = self.driver.find_elements_by_xpath("//div[@class='flexContainerRow']")
        home_raw = elems[1].text
        away_raw = elems[2].text
        home_sets = int(home_raw.split('\n')[0])
        away_sets = int(away_raw.split('\n')[0])
        home_games = int(home_raw.split('\n')[set_number])
        away_games = int(away_raw.split('\n')[set_number])
        return (home_sets, away_sets), (home_games, away_games)

    def bet(self, bet_type: str, bookmaker_matchid: str, set_number: int, odd: float, probability: float):
        if bet_type == 'home':
            odd_index = 0
        elif bet_type == 'away':
            odd_index = 1
        else:
            raise Exception(f"Unexpected bet type: {bet_type}")
        elem_base = self.get_base_odds_element(set_number)
        elem_odds = elem_base.find_elements_by_xpath("../..//div[@class='tdEventCells']/div")[odd_index]
        elem_odds.click()
        time.sleep(self.short_seconds_to_sleep)
        click_id(self.driver, 'submitButton')
        time.sleep(self.seconds_to_sleep)
        save_bet(self.database_id, bookmaker_matchid, bet_type, "".join(['set', str(set_number)]), odd, probability)
        pass
