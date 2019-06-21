import json
import time
from typing import List

import pandas as pd

from live_betting.bookmaker import Bookmaker
from live_betting.config_betting import CREDENTIALS_PATH
from live_betting.utils import load_fb_credentials, write_id, click_id


class Tipsport(Bookmaker):
    def __init__(self):
        Bookmaker.__init__(self, "https://www.tipsport.cz/")

    def login(self):
        username, password = load_fb_credentials(CREDENTIALS_PATH)
        write_id(self._driver, "userNameId", username)
        write_id(self._driver, "passwordId", password)
        click_id(self._driver, "btnLogin")
        time.sleep(30)  # some time in seconds for the website to load

    def get_tournaments(self) -> pd.DataFrame():
        self._driver.get("https://www.tipsport.cz/kurzy/tenis-43#superSportId=43")
        time.sleep(30)  # some time in seconds for the website to load
        elements = self._driver.find_elements_by_xpath("//div[@class='colCompetition']")
        texts = []
        tournament_year_ids = []
        tournament_ids = []
        for e in elements:
            texts.append(e.find_element_by_xpath(".//h2").text)
            tournament_year_ids.append(e.get_attribute("data-competition-annual-id"))
            tournament_ids.append(json.loads(e.get_attribute("data-model"))['id'])

        tournaments = self.obtain_tournaments_from_texts(texts)
        tournaments["tournament_year_ids"] = tournament_year_ids
        tournaments["tournament_ids"] = tournament_ids
        return tournaments

    def get_inplay_tournaments(self) -> pd.DataFrame():
        self._driver.get("https://www.tipsport.cz/live")
        time.sleep(30)  # some time in seconds for the website to load
        elements = self._driver.find_elements_by_xpath("//span[contains(text(),'Tenis')]")
        texts = []
        for e in elements:
            texts.append(e.text)
        return self.obtain_tournaments_from_texts(texts)

    @staticmethod
    def obtain_tournaments_from_texts(texts: List[str]) -> pd.DataFrame():
        tournaments = pd.DataFrame(columns=["sex", "type", "surface", "tournament_name"])
        for text in texts:  # the page is constantly reloading and the original elements are then no longer attached
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
