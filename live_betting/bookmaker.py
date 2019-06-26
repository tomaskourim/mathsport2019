import time

from selenium import webdriver

from database_operations import execute_sql_postgres
from live_betting.config_betting import WEBDRIVER_PATH


class Bookmaker:
    def __init__(self, url, name):
        self._home_url = url
        self.name = name
        self.driver = webdriver.Chrome(executable_path=WEBDRIVER_PATH)
        self.driver.maximize_window()
        self.driver.get(self._home_url)
        self.SCROLL_PAUSE_TIME = 0.5
        self.seconds_to_sleep = 15  # seconds to wait after page loading
        self.database_id = self.get_book_id()

    def close(self):
        self.driver.quit()

    def get_book_id(self):
        return execute_sql_postgres("SELECT id FROM bookmaker WHERE home_url=%s AND name=%s",
                                    [self._home_url, self.name])[0]

    def scroll_to_botton(self):

        # Get scroll height
        last_height = self.driver.execute_script("return document.body.scrollHeight")

        while True:
            # Scroll down to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            # Wait to load page
            time.sleep(self.SCROLL_PAUSE_TIME)

            # Calculate new scroll height and compare with last scroll height
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        time.sleep(self.seconds_to_sleep)  # some time in seconds for the website to load


def scroll_pixels(self, pixels: int):
    self.driver.execute_script(f"window.scrollTo(0, {pixels})")
