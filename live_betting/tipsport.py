import datetime
import json
import logging
import time
from typing import List

import pandas as pd
import pytz

from live_betting.bookmaker import Bookmaker
from live_betting.config_betting import CREDENTIALS_PATH
from live_betting.inplay_operations import save_first_set_odds
from live_betting.utils import load_fb_credentials, write_id, click_id


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

    def handle_match(self, bookmaker_matchid: str):
        self.handle_prematch(self, bookmaker_matchid)

    def handle_prematch(self, self1, bookmaker_matchid):
        self.driver.get("".join([self.tennis_match_base_url, bookmaker_matchid]))
        time.sleep(self.seconds_to_sleep)
        click_id(self.driver, "matchName" + bookmaker_matchid)
        time.sleep(self.short_seconds_to_sleep)

        last_odds = (None, None)
        while ~self.match_started():
            current_odds = self.get_first_set_odds()
            if current_odds != last_odds:
                save_first_set_odds(current_odds, self.database_id, bookmaker_matchid)
                last_odds = current_odds
            self.wait_half_to_matchstart()
            self.driver.refresh()
            time.sleep(self.short_seconds_to_sleep)
            click_id(self.driver, "matchName" + bookmaker_matchid)
            time.sleep(self.short_seconds_to_sleep)
        pass

    def get_first_set_odds(self) -> tuple:
        elem_base = self.driver.find_element_by_xpath("//span[@title='Vítěz 1. setu']")
        elem_kurzy = elem_base.find_elements_by_xpath("./../../..//div[@class='tdEventCells']//span")
        kurzy = (elem_kurzy[1].text, elem_kurzy[3].text)
        return kurzy

    def match_started(self) -> bool:
        elem_base = self.driver.find_element_by_xpath("//span[@title='Vítěz 1. setu']")
        elem_kurzy = elem_base.find_elements_by_xpath("../../..//div[@class='tdEventCells']/div")
        if "disabled" in elem_kurzy[0].get_attribute("class") and "disabled" in elem_kurzy[1].get_attribute("class"):
            logging.error(f"Match started at: {datetime.datetime.now()}")
            return True
        return False

    def wait_half_to_matchstart(self):
        starting_time = datetime.datetime.strptime(
            self.driver.find_elements_by_xpath("//div[@class='actualState']")[1].text, '%d.%m.%Y %H:%M')
        starting_time = pytz.timezone('Europe/Berlin').localize(starting_time).astimezone(pytz.utc)
        utc_time = pytz.utc.localize(datetime.datetime.utcnow())
        seconds_to_sleep = (starting_time - utc_time).total_seconds() / 2
        time.sleep(seconds_to_sleep)
        pass
