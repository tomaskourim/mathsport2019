import json
import time
from typing import List

import pandas as pd

from live_betting.bookmaker import Bookmaker
from live_betting.config_betting import CREDENTIALS_PATH
from live_betting.utils import load_fb_credentials, write_id, click_id


class Tipsport(Bookmaker):
    def __init__(self):
        Bookmaker.__init__(self, "https://www.tipsport.cz", "Tipsport")
        self.tennis_id = 43
        self.tennis_tournament_base_url = "https://www.tipsport.cz/kurzy/a/a/a-"

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

    def get_matches_tournament(self, tournament):
        self.driver.get("".join([self.tennis_tournament_base_url, str(tournament.tournament_bookmaker_id)]))
        time.sleep(self.seconds_to_sleep)
        elements = self.driver.find_elements_by_xpath("//div[@class='rowMatchWrapper']")
        home = []
        away = []
        matchid = []
        expected_start_date = []
        expected_start_time = []
        for e in elements:
            base_info = e.find_element_by_xpath("./div")
            players = base_info.get_attribute("data-matchname")
            if "celkově" in players:
                continue
            players_splitted = players.split(" - ")
            if len(players_splitted) != 2:
                players_splitted = players.split("-")
            if len(players_splitted) != 2:
                print(
                    f"Impossible to find two players in tournament {tournament.tournament_name}. Found text: {players}")
                continue
            home.append(players_splitted[0])
            away.append(players_splitted[1])
            matchid.append(base_info.get_attribute("data-matchid"))
            start_date, start_time = e.find_elements_by_xpath(".//div[@class='actualState']")[1].text.split(" ")
            expected_start_date.append(start_date)
            expected_start_time.append(start_time)
        matches = pd.DataFrame(zip(home, away, matchid, expected_start_date, expected_start_time),
                               columns=["home", "away", "bookmaker_matchid", "start_date", "start_time"])
        return matches
