import time

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
