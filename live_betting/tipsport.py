import time
from typing import Tuple, List

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

    def get_inplay_tournaments(self) -> List[Tuple[str, str]]:
        self._driver.get("https://www.tipsport.cz/live")
        time.sleep(30)  # some time in seconds for the website to load
        elements = self._driver.find_elements_by_xpath("//span[contains(text(),'Tenis')]")
        texts = []
        for e in elements:
            texts.append(e.text)
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
                continue

            if "dvouhra" in text:
                tournament["type"] = "singles"
                text = text.replace("dvouhra", "")
            elif "čtyřhra" in text:
                tournament["type"] = "doubles"
                text = text.replace("čtyřhra", "")
            else:
                continue

            if "tráva" in text:
                tournament["surface"] = "grass"
                text = text.replace(" - tráva ", "")
            elif "antuka" in text:
                tournament["surface"] = "clay"
                text = text.replace(" - antuka ", "")
            elif "tvrdý povrch" in text:
                tournament["surface"] = "hard"
                text = text.replace(" - tvrdý povrch ", "")
            else:
                continue

            tournament["tournament_name"] = text
            tournaments = tournaments.append(tournament, ignore_index=True)

        return tournaments
