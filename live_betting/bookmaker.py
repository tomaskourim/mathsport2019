from selenium import webdriver

from live_betting.config_betting import WEBDRIVER_PATH


class Bookmaker:
    def __init__(self, home_url):
        self._home_url = home_url
        self._driver = webdriver.Chrome(executable_path=WEBDRIVER_PATH)
        self._driver.maximize_window()
        self._driver.get(self._home_url)

    def close(self):
        self._driver.quit()

    def login(self):
        pass

