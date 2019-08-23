import datetime
import json
import logging
import os
import re
import time
from typing import List, Tuple

import numpy as np
import pandas as pd
import pytz
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement

from config import FAIR_ODDS_PARAMETER
from live_betting.bookmaker import Bookmaker
from live_betting.config_betting import CREDENTIALS_PATH
from live_betting.config_betting import MINUTES_PER_GAME
from live_betting.inplay_operations import save_set_odds, evaluate_bet_on_set, home_won_set, save_bet
from live_betting.prematch_operations import get_matchid
from live_betting.utils import load_credentials, write_id, click_id
from odds_to_probabilities import probabilities_from_odds


class Tipsport(Bookmaker):
    def __init__(self):
        Bookmaker.__init__(self, "https://www.tipsport.cz", "Tipsport")
        self.tennis_id = 43
        self.tennis_tournament_base_url = "https://www.tipsport.cz/kurzy/a/a/a-"
        self.tennis_match_base_url = "https://www.tipsport.cz/tenis-"
        self.tennis_match_live_base_url = "https://www.tipsport.cz/live/tenis/"
        self.base_bet_amount = 50
        self.minimal_bet_amount = 5

    def login(self):
        username, password = load_credentials(CREDENTIALS_PATH)
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
        tournaments = pd.DataFrame(columns=["sex", "type", "surface", "tournament_name"])
        for text in texts:  # the page is constantly reloading and the original elements are then no longer attached
            if len(text) == 0:
                continue
            tournament = {}
            # to remove TV stations streaming a tournament
            tv_location = text.find("    ")
            if tv_location > 0:
                text = text[0:tv_location]
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
        logging.info(f"Finished prematch handling of match {bookmaker_matchid}. Starting odds is {starting_odds}.")
        home_probability = probabilities_from_odds(np.asarray(starting_odds), "1.set", FAIR_ODDS_PARAMETER)[0]
        logging.info(f"Finished probability calculation of match {bookmaker_matchid}. \
                        Starting home probability is {home_probability}.")
        self.handle_inplay(bookmaker_matchid, home_probability, c_lambda)

    def handle_prematch(self, bookmaker_matchid) -> tuple:
        last_odds = (None, None)
        current_odds = (None, None)
        self.driver.get("".join([self.tennis_match_base_url, bookmaker_matchid]))
        time.sleep(self.seconds_to_sleep)
        if not self.open_odds_menu(bookmaker_matchid):
            logging.error(f"Unable to open odds menu at beginning, match {bookmaker_matchid}")
            return current_odds

        while not self.match_started(bookmaker_matchid):
            current_odds = self.get_set_odds(1)
            if current_odds != last_odds:
                save_set_odds(current_odds, self.database_id, bookmaker_matchid, 1)
                last_odds = current_odds
            self.wait_half_to_matchstart()
            self.driver.refresh()
            time.sleep(self.seconds_to_sleep / 2)
            if not self.open_odds_menu(bookmaker_matchid):
                logging.error(f"Unable to open odds menu in loop, match {bookmaker_matchid}")
                break
        return current_odds

    def match_started(self, bookmaker_matchid) -> bool:
        utc_time = pytz.utc.localize(datetime.datetime.utcnow())
        try:
            elem_base = self.get_base_odds_element(1)
            elem_odds = elem_base.find_elements_by_xpath("../../..//div[@class='tdEventCells']/div")
            starting_time = self.get_starting_time()
        except NoSuchElementException:
            logging.error(f"Match {bookmaker_matchid} started by error at UTC {utc_time}")
            self.driver.save_screenshot(f"screens/{bookmaker_matchid}.png")
            return True

        if starting_time - utc_time < datetime.timedelta(seconds=30):
            if "disabled" in elem_odds[0].get_attribute("class") and "disabled" in elem_odds[1].get_attribute(
                    "class"):
                logging.info(f"Match started at UTC: {utc_time}")
                return True
        return False

    def get_set_odds(self, set_number: int) -> tuple:
        elem_base = self.get_base_odds_element(set_number)
        elem_odds = elem_base.find_elements_by_xpath("./../../..//div[@class='tdEventCells']//span")
        try:
            odds = (float(elem_odds[1].text), float(elem_odds[3].text))
        except:
            odds = (float(elem_odds[1].text), float(elem_odds[4].text))
        return odds

    def wait_half_to_matchstart(self):
        starting_time = self.get_starting_time()
        utc_time = pytz.utc.localize(datetime.datetime.utcnow())
        seconds_to_sleep = max((starting_time - utc_time).total_seconds() / 2, self.seconds_to_sleep)
        time.sleep(seconds_to_sleep)
        pass

    def open_odds_menu(self, bookmaker_matchid: str) -> bool:
        errors = 0
        while errors < 5:
            try:
                click_id(self.driver, "matchName" + bookmaker_matchid)
                time.sleep(self.short_seconds_to_sleep / 2)
                return True
            except NoSuchElementException:
                errors = errors + 1
                logging.warning(f"Unable to click on odds element in match {bookmaker_matchid}. Trying again.")
                self.driver.refresh()
                time.sleep(self.seconds_to_sleep * errors)
        return False

    def get_base_odds_element(self, set_number: int) -> WebElement:
        if set_number == 5:  # TODO handle also best-of-three matches
            return self.driver.find_element_by_xpath(f"//span[@title='Vítěz zápasu']")  # TODO verify
        else:
            return self.driver.find_element_by_xpath(f"//span[@title='Vítěz {set_number}. setu']")

    def get_starting_time(self) -> datetime:
        starting_time = datetime.datetime.strptime(
            self.driver.find_elements_by_xpath("//div[@class='actualState']")[1].text, '%d.%m.%Y %H:%M')
        starting_time = pytz.timezone('Europe/Berlin').localize(starting_time).astimezone(pytz.utc)
        return starting_time

    # inplay operations
    def handle_inplay(self, bookmaker_matchid: str, home_probability: float, c_lambda: float):
        self.driver.get("".join([self.tennis_match_live_base_url, bookmaker_matchid]))
        time.sleep(self.seconds_to_sleep)

        matchid = get_matchid(bookmaker_matchid, self.database_id)
        set_number = 1
        last_set_score = (0, 0)
        errors_in_match = 0
        # while match not finished or error rate reached
        while errors_in_match < 5:
            try:
                # wait for the set to finish
                current_set_score = self.wait_for_set_end(set_number, last_set_score, bookmaker_matchid)
                home_won = home_won_set(current_set_score, last_set_score, set_number, matchid)
                self.evaluate_last_bet(last_set_score, current_set_score, bookmaker_matchid, set_number, home_won)
                logging.info(f"Handled set{set_number} in match {bookmaker_matchid}.")
                if self.match_finished(bookmaker_matchid):
                    break
                home_probability = c_lambda * home_probability + 1 / 2 * (1 - c_lambda) * (1 + (1 if home_won else -1))
                set_number = set_number + 1
                self.bet_next_set(bookmaker_matchid, set_number, home_probability)
                last_set_score = current_set_score
            except Exception as error:
                logging.exception(f"Error while handling live match {bookmaker_matchid} in set{set_number}: {error}")
                errors_in_match = errors_in_match + 1
                screen_order = 1
                screen_filename = f"screens/live_set{set_number}-{bookmaker_matchid}-{screen_order}.png"
                while os.path.isfile(screen_filename):
                    screen_order = screen_order + 1
                    screen_filename = f"screens/live_set{set_number}-{bookmaker_matchid}-{screen_order}.png"
                self.driver.save_screenshot(screen_filename)

    pass

    def match_finished(self, bookmaker_matchid: str) -> bool:
        try:
            self.driver.find_element_by_xpath("//span[@class='removalCountdownText']")
            logging.info(f"Match {bookmaker_matchid} finished.")
            return True
        except NoSuchElementException:
            return False

    def wait_for_set_end(self, set_number: int, last_set_state: tuple, bookmaker_matchid: str) -> tuple:
        while True:
            try:
                # with live video stream
                set_score, game_score = self.get_score_with_video(set_number, bookmaker_matchid)
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

    def evaluate_last_bet(self, last_set_score: tuple, current_set_score: tuple, bookmaker_matchid: str,
                          set_number: int, home_won: bool):
        if set_number > 1:
            evaluate_bet_on_set(self.database_id, bookmaker_matchid, set_number, home_won)
            logging.info(f"Betting evaluation: matchid={bookmaker_matchid}, last score: {last_set_score}, \
            current score: {current_set_score}, set number {set_number}. Home won = {home_won}")
            self.driver.save_screenshot(
                f"screens/set_bet_evaluation_{bookmaker_matchid}-set{set_number}_currentscore_{current_set_score}.png")
        pass

    def bet_next_set(self, bookmaker_matchid: str, set_number: int, home_probability: float):
        errors = 0
        while errors < 5:
            try:
                # get odds for next set
                set_odds = self.get_set_odds(set_number)
                save_set_odds(set_odds, self.database_id, bookmaker_matchid, set_number)
                # bet on next set if possible
                if home_probability > 1 / set_odds[0]:
                    self.bet_set('home', bookmaker_matchid, set_number, set_odds[0], home_probability)
                if (1 - home_probability) > 1 / set_odds[1]:
                    self.bet_set('away', bookmaker_matchid, set_number, set_odds[1], 1 - home_probability)
                break
            except:
                errors = errors + 1
                time.sleep(self.seconds_to_sleep)
        pass

    def bet_set(self, bet_type: str, bookmaker_matchid: str, set_number: int, odd: float, probability: float):
        if bet_type == 'home':
            odd_index = 0
        elif bet_type == 'away':
            odd_index = 1
        else:
            raise Exception(f"Unexpected bet type: {bet_type}")
        elem_base = self.get_base_odds_element(set_number)
        elems_odds = elem_base.find_elements_by_xpath("../../..//div[@class='tdEventCells']/div")
        elem_odds = elems_odds[odd_index]
        elem_odds.click()
        time.sleep(self.short_seconds_to_sleep)
        write_id(self.driver, 'amountPaid',
                 str(max(self.minimal_bet_amount, round(probability * self.base_bet_amount))))
        click_id(self.driver, 'submitButton')
        time.sleep(self.seconds_to_sleep)
        try:
            self.driver.find_element_by_xpath("//td[@class='ticketMessage successfullySaved']")
            click_id(self.driver, 'removeAllBets')
            logging.info(
                f"Placed bet {bet_type} in match {bookmaker_matchid} on set{set_number} with odd {odd} and \
                probability {probability}")
            save_bet(self.database_id, bookmaker_matchid, bet_type, "".join(['set', str(set_number)]), odd, probability)
        except NoSuchElementException:
            logging.error(f"Unable to place bet \
                {self.database_id, bookmaker_matchid, bet_type, ''.join(['set', str(set_number)]), odd, probability}")
        pass

    def get_score_with_video(self, set_number: int, bookmaker_matchid: str) -> Tuple[Tuple[int, ...], Tuple[int, ...]]:
        try:
            raw_text = self.driver.find_element_by_xpath("//span[@class='m-scoreOffer__msg']").text
        except NoSuchElementException:
            logging.info(f"No video for match {bookmaker_matchid}.")
            elem = self.driver.find_element_by_xpath("//span[@class='m-scoreboardStats__score']")
            raw_text = elem.text + elem.get_attribute("title")
        logging.info(f"Video score raw text for match {bookmaker_matchid}: {raw_text}")
        # TODO co kdyz se odlozi zacatek? Naparsovat cas a ulozit? Ale teoreticky by to melo vyskocit i v prematch
        if 'Za ' in raw_text or 'Začátek plánován na' in raw_text:
            return (0, 0), (0, 0)
        raw_text = raw_text.replace(',', '')
        raw_text = raw_text.replace('*', '')  # supertiebreak doubles has * marking serving pair
        raw_text = re.sub('\(\\d+\)', '', raw_text)
        set_score = raw_text[:3].split(':')
        set_score = [int(x) for x in set_score]
        if '-' in raw_text:
            game_score = raw_text.split(' - ')[1].split(' ')[set_number - 1].split(':')
        else:
            game_score = raw_text[-4:-1].split(':')
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
