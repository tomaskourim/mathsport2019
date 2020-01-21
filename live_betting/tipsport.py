import datetime
import json
import logging
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
from live_betting.utils import load_credentials, write_id, click_id, save_screenshot
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
            texts.append(e.text)
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
            # remove tournament brackets
            text = text.replace("\nPAVOUK", "")
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
            elif "čtyřhra" in text or "4hra" in text:
                tournament["type"] = "doubles"
                text = text.replace("čtyřhra", "")
                text = text.replace(", 4hra", "")
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
            elif "tvrdý p." in text:
                tournament["surface"] = "hard"
                text = text.replace(" - tvrdý p.", "")
            else:
                tournament["surface"] = None

            tournament["tournament_name"] = text.strip()
            tournaments = tournaments.append(tournament, ignore_index=True)

        return tournaments

    def get_matches_tournament(self, tournament: pd.DataFrame) -> pd.DataFrame:
        self.driver.get("".join([self.tennis_tournament_base_url, str(tournament.tournament_bookmaker_id)]))
        time.sleep(self.seconds_to_sleep)
        elements = self.driver.find_elements_by_xpath("//div[@data-matchid]")
        home = []
        away = []
        matchid = []
        start_time_utc = []
        for base_info in elements:
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
                base_info.find_elements_by_xpath(".//div[@class='o-matchRow__dateClosed']")[1].text, '%d.%m.%Y %H:%M')
            starting_time = pytz.timezone('Europe/Berlin').localize(starting_time).astimezone(pytz.utc)
            start_time_utc.append(starting_time)

        matches = pd.DataFrame(zip(home, away, matchid, start_time_utc),
                               columns=["home", "away", "bookmaker_matchid", "start_time_utc"])
        return matches

    def handle_match(self, bookmaker_matchid: str, c_lambda: float):
        starting_odds = self.handle_prematch(bookmaker_matchid)
        logging.info(f"Finished prematch handling of match {bookmaker_matchid}. Starting odds is {starting_odds}.")
        if starting_odds[0] is None:
            logging.info(f"Match {bookmaker_matchid} has no starting odds.")
            return
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
            current_odds = self.get_set_odds(1, bookmaker_matchid)
            if current_odds != last_odds:
                save_set_odds(current_odds, self.database_id, bookmaker_matchid, 1)
                last_odds = current_odds
            self.wait_half_to_matchstart()
            self.driver.refresh()
            time.sleep(self.seconds_to_sleep / 2)
            if not self.open_odds_menu(bookmaker_matchid):
                logging.warning(f"Unable to open odds menu in loop, match {bookmaker_matchid}")
                break
        return current_odds

    def match_started(self, bookmaker_matchid) -> bool:
        utc_time = pytz.utc.localize(datetime.datetime.utcnow())
        errors = 0
        while True:
            try:
                elem_base = self.get_base_odds_element(1)
                elem_odds = elem_base.find_elements_by_xpath("../../..//div[@class='tdEventCells']/div")
                starting_time = self.get_starting_time()
                break
            except NoSuchElementException:
                time.sleep(self.seconds_to_sleep)
                errors = errors + 1
                if errors > 3:
                    logging.warning(f"Match {bookmaker_matchid} started by error at UTC {utc_time}")
                    return True

        if starting_time - utc_time < datetime.timedelta(seconds=30):
            if "disabled" in elem_odds[0].get_attribute("class") and "disabled" in elem_odds[1].get_attribute(
                    "class"):
                logging.info(f"Match {bookmaker_matchid} started at UTC: {utc_time}")
                return True
        return False

    def get_set_odds(self, set_number: int, bookmaker_matchid: str) -> tuple:
        elem_base = self.get_base_odds_element(set_number)
        elem_odds = elem_base.find_elements_by_xpath("./../../..//div[@class='tdEventCells']//span")
        try:
            odds = (float(elem_odds[1].text), float(elem_odds[3].text))
        except:
            odds = (float(elem_odds[1].text), float(elem_odds[4].text))
        save_screenshot(self.driver, f"set{set_number}_odds_gathered_{odds[0]}_{odds[1]}", bookmaker_matchid)
        return odds

    def wait_half_to_matchstart(self):
        starting_time = self.get_starting_time()
        utc_time = pytz.utc.localize(datetime.datetime.utcnow())
        seconds_to_sleep = max((starting_time - utc_time).total_seconds() / 2, self.seconds_to_sleep)
        time.sleep(seconds_to_sleep)
        pass

    def open_odds_menu(self, bookmaker_matchid: str) -> bool:
        errors = 0
        while errors < 4:
            try:
                click_id(self.driver, "matchName" + bookmaker_matchid)
                time.sleep(self.short_seconds_to_sleep)
                return True
            except NoSuchElementException:
                errors = errors + 1
                logging.warning(f"Unable to click on odds element in match {bookmaker_matchid}. Trying again.")
                self.driver.refresh()
                time.sleep(self.seconds_to_sleep * errors)
        return False

    def get_base_odds_element(self, set_number: int) -> WebElement:
        if set_number == 5:
            return self.driver.find_element_by_xpath(f"//span[@title='Vítěz zápasu']")
        elif set_number == 3:
            try:
                return self.driver.find_element_by_xpath(f"//span[@title='Vítěz {set_number}. setu']")
            except NoSuchElementException:
                return self.driver.find_element_by_xpath(f"//span[@title='Vítěz zápasu']")
        else:
            return self.driver.find_element_by_xpath(f"//span[@title='Vítěz {set_number}. setu']")

    def get_starting_time(self) -> datetime:
        starting_time = datetime.datetime.strptime(
            self.driver.find_elements_by_xpath("//div[@class='o-matchRow__dateClosed']")[1].text, '%d.%m.%Y %H:%M')
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
                last_set_score = current_set_score
                logging.info(f"Handled set{set_number} in match {bookmaker_matchid}. Home won = {home_won}")
                if self.match_finished(bookmaker_matchid, current_set_score):
                    break
                home_probability = c_lambda * home_probability + 1 / 2 * (1 - c_lambda) * (1 + (1 if home_won else -1))
                set_number = set_number + 1
                self.bet_next_set(bookmaker_matchid, set_number, home_probability)
            except Exception as error:
                logging.exception(f"Error while handling live match {bookmaker_matchid} in set{set_number}: {error}")
                errors_in_match = errors_in_match + 1
                save_screenshot(self.driver, f"set{set_number}_live_{str(error)[:5]}", bookmaker_matchid)
                time.sleep(self.seconds_to_sleep)

    def match_finished(self, bookmaker_matchid: str, current_set_score: tuple) -> bool:
        if max(current_set_score) < 2:  # TODO handle best-of-five matches
            try:
                self.driver.find_element_by_xpath("//span[@class='removalCountdownText']")
            except NoSuchElementException:
                try:
                    self.driver.find_element_by_xpath(
                        "//div[contains(text(),'byl ukončen, vyberte si další z naší nabídky aktuálně probíhajících')]")
                except NoSuchElementException:
                    return False
        logging.info(f"Match {bookmaker_matchid} finished.")  # return True unless given conditions happens
        return True

    def wait_for_set_end(self, set_number: int, last_set_state: tuple, bookmaker_matchid: str) -> tuple:
        game_score = (0, 0)
        point_score = ""
        while True:
            # TODO if no score is returned, assume the match is over and try to guess the result
            set_score, game_score, point_score = self.get_score(set_number, bookmaker_matchid,
                                                                last_set_state, game_score, point_score)
            if last_set_state != set_score:
                return set_score
            elif max(game_score) < 5:
                time.sleep((5 - max(game_score)) * MINUTES_PER_GAME * 60)  # wait minimal number of games to play
            elif game_score[0] == 5 and game_score[1] == 5:
                time.sleep(MINUTES_PER_GAME * 60)  # wait 1 game
            else:
                time.sleep(MINUTES_PER_GAME * 10)  # wait a moment

    def evaluate_last_bet(self, last_set_score: tuple, current_set_score: tuple, bookmaker_matchid: str,
                          set_number: int, home_won: bool):  # TODO to generic Bookmaker class or elsewhere
        if set_number > 1:
            logging.info(f"Betting evaluation: matchid={bookmaker_matchid}, last score: {last_set_score}, \
            current score: {current_set_score}, set number {set_number}. Home won = {home_won}")
            evaluate_bet_on_set(self.database_id, bookmaker_matchid, set_number, home_won)

    def bet_next_set(self, bookmaker_matchid: str, set_number: int, home_probability: float):
        while True:
            try:
                # get odds for next set
                set_odds = self.get_set_odds(set_number, bookmaker_matchid)
                save_set_odds(set_odds, self.database_id, bookmaker_matchid, set_number)
                # bet on next set if possible
                if home_probability > 1 / set_odds[0]:
                    self.bet_set('home', bookmaker_matchid, set_number, set_odds[0], home_probability)
                else:
                    logging.info(
                        f"Not placing bet on home, match {bookmaker_matchid}, set{set_number} with odds {set_odds[0]}"
                        f" and computed prob. {home_probability}")
                if (1 - home_probability) > 1 / set_odds[1]:
                    self.bet_set('away', bookmaker_matchid, set_number, set_odds[1], 1 - home_probability)
                else:
                    logging.info(
                        f"Not placing bet on away, match {bookmaker_matchid}, set{set_number} with odds {set_odds[1]}"
                        f" and computed prob. {1 - home_probability}")
                break
            except Exception as error:
                logging.exception(
                    f"Error while handling bets and odds on match {bookmaker_matchid}, set{set_number}: {error}")
                save_screenshot(self.driver, f"set{set_number}_placing_bet_{str(error)[:5]}", bookmaker_matchid)
                if self.next_set_started(bookmaker_matchid, set_number):
                    logging.info(f"Match {bookmaker_matchid}: Set{set_number} started.")
                    break
                else:
                    time.sleep(self.seconds_to_sleep / 2)  # wait just a moment

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
        save_screenshot(self.driver, f"set{set_number}_bet_prepared_{bet_type}_{odd}_time{datetime.datetime.now()}", bookmaker_matchid)
        # time.sleep(self.short_seconds_to_sleep / 2)
        write_id(self.driver, 'amountPaid',
                 str(max(self.minimal_bet_amount, round(probability * self.base_bet_amount))))
        click_id(self.driver, 'submitButton')
        save_screenshot(self.driver, f"set{set_number}_bet_created_{bet_type}_{odd}_time{datetime.datetime.now()}", bookmaker_matchid)
        logging.info(f"Waiting for {self.seconds_to_sleep} seconds in bet placing in match {bookmaker_matchid}")
        time.sleep(self.seconds_to_sleep)
        try:
            self.driver.find_element_by_xpath("//td[@class='ticketMessage successfullySaved']")
            click_id(self.driver, 'removeAllBets')
            logging.info(
                f"Placed bet {bet_type} in match {bookmaker_matchid} on set{set_number} with odd {odd} and \
                probability {probability}")
            save_bet(self.database_id, bookmaker_matchid, bet_type, "".join(['set', str(set_number)]), odd, probability)
        except NoSuchElementException:
            logging.error(f"Unable to place bet {bet_type} in match {bookmaker_matchid} on set{set_number} with "
                          f"odd {odd} and probability {probability}")

    def next_set_started(self, bookmaker_matchid: str, set_number: int) -> bool:
        _, _, point_score = self.get_score(set_number, bookmaker_matchid, (0, 0), (0, 0), "")
        if point_score == '(00:00)':  # TODO it is eager to start, some corner cases should be handled
            return False
        else:
            return True

    def get_score(self, set_number: int, bookmaker_matchid: str, last_set_score: tuple, last_game_score: tuple,
                  last_point_score: str) -> Tuple[Tuple[int, ...], Tuple[int, ...], str]:
        try:
            # with live video stream
            return self.get_score_with_video(set_number, bookmaker_matchid, last_set_score, last_game_score,
                                             last_point_score)
        except NoSuchElementException:
            # w/out live video stream
            return self.get_score_without_video(set_number, bookmaker_matchid)
        pass

    def get_score_with_video(self, set_number: int, bookmaker_matchid: str, last_set_score: tuple,
                             last_game_score: tuple, last_point_score: str) -> \
            Tuple[Tuple[int, ...], Tuple[int, ...], str]:
        try:
            raw_text = self.driver.find_element_by_xpath("//span[@class='m-scoreOffer__msg']").text
            logging.info(f"Video score raw text for match {bookmaker_matchid}: {raw_text}")
        except NoSuchElementException:
            try:
                elem = self.driver.find_element_by_xpath("//span[@class='m-scoreboardStats__score']")
                raw_text = elem.text + elem.get_attribute("title")
                logging.info(f"Tracker score raw text for match {bookmaker_matchid}: {raw_text}")
            except NoSuchElementException:
                self.driver.find_element_by_xpath(
                    "//div[contains(text(),'byl ukončen, vyberte si další z naší nabídky aktuálně probíhajících')]")
                return self.get_score_after_match(last_set_score, last_game_score, last_point_score)
        if 'Za ' in raw_text or 'Začátek plánován' in raw_text or 'se rozehr' in raw_text or 'ošetřování' in raw_text:
            return last_set_score, last_game_score, last_point_score
        raw_text = raw_text.replace(',', '')
        raw_text = raw_text.replace('*', '')  # supertiebreak doubles has * marking serving pair
        raw_text = re.sub('\(\\d+\)', '', raw_text)
        set_score = raw_text[:3].split(':')
        set_score = [int(x) for x in set_score]
        if '-' in raw_text:
            set_games = raw_text.split(' - ')[1].split(' ')
            point_score = set_games[len(set_games) - 1]
            if sum(set_score) == len(set_games) - 2:
                game_score = set_games[set_number - 1].split(':')
            else:
                set_score, game_score = self.get_score_from_mistake(set_games)
        else:
            game_score = raw_text[-4:-1].split(':')
            point_score = last_point_score  # TODO actually do something
        game_score = [int(x) for x in game_score]
        return tuple(set_score), tuple(game_score), point_score

    def get_score_without_video(self, set_number: int, bookmaker_matchid: str) -> \
            Tuple[Tuple[int, int], Tuple[int, int], str]:
        elems = self.driver.find_elements_by_xpath("//div[@class='flexContainerRow']")
        home_raw = elems[1].text
        away_raw = elems[2].text
        logging.info(f"No video score for match {bookmaker_matchid}: Home raw: {home_raw}, away_raw: {away_raw}")

        home_split = home_raw.split('\n')
        home_sets_raw = home_split[0]
        home_games_raw = home_split[set_number]

        away_split = away_raw.split('\n')
        away_sets_raw = away_split[0]
        away_games_raw = away_split[set_number]

        if "-" in home_sets_raw:
            home_sets = 0
        else:
            home_sets = int(home_sets_raw)

        if "-" in away_sets_raw:
            away_sets = 0
        else:
            away_sets = int(away_sets_raw)

        if "-" in home_games_raw:
            home_games = 0
        else:
            home_games = int(home_games_raw)

        if "-" in away_games_raw:
            away_games = 0
        else:
            away_games = int(away_games_raw)

        logging.info(
            f"Current score for match {bookmaker_matchid}: sets {home_sets}:{away_sets}, games {home_games}:{away_games}")
        point_score = ""  # TODO actually get it
        return (home_sets, away_sets), (home_games, away_games), point_score

    @staticmethod
    def get_score_from_mistake(set_games: List) -> Tuple[List[int], List[int]]:
        home_sets = sum(1 if set_games[i].split(':')[0] > set_games[i].split(':')[1] else 0 for i in
                        range(0, len(set_games) - 2))
        away_sets = sum(1 if set_games[i].split(':')[1] > set_games[i].split(':')[0] else 0 for i in
                        range(0, len(set_games) - 2))
        return [home_sets, away_sets], set_games[len(set_games) - 2].split(':')

    @staticmethod
    def get_score_after_match(set_score, game_score, point_score):
        if max(set_score) == 1:  # match about to end #TODO handle Grand Slam
            if game_score == (6, 6):  # set about to end in tiebreak #TODO what about Wimbledon and infinite sets
                point_score = point_score.replace('(', '').replace(')', '')
                point_home = int(point_score.split(':')[0])
                point_away = int(point_score.split(':')[1])
                game_score = (game_score[0] + 1, game_score[1]) if point_home > point_away else (
                    game_score[0], game_score[1] + 1)
            elif max(game_score) >= 5 and max(game_score) - min(game_score) >= 1:  # set about to end
                game_score = (game_score[0] + 1, game_score[1]) if game_score[0] > game_score[1] else (
                    game_score[0], game_score[1] + 1)
            else:
                logging.error(f"Set score: {set_score}, game score: {game_score}, point score: {point_score}")
                raise Exception(f"Unexpected scores: {set_score}, {game_score}, {point_score}")
            set_score = (set_score[0] + 1, set_score[1]) if game_score[0] > game_score[1] else (
                set_score[0], set_score[1] + 1)
            point_score = '0:0'
            return set_score, game_score, point_score
        else:
            raise Exception(f"Unexpected set score: {set_score}, {game_score}, {point_score}")
