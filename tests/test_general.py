import unittest

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from live_betting.config_betting import WEBDRIVER_PATH
from live_betting.utils import save_screenshot


class GeneralTest(unittest.TestCase):
    @staticmethod
    def test_screenshot():
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("start-maximized")
        options.add_argument("disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("window-size=1920,1080")
        driver = webdriver.Chrome(options=options, executable_path=WEBDRIVER_PATH)
        driver.get("https://www.google.com")
        info_text = 'Message: no such element: Unable to locate element: {"method":"xpath","selector":"//span[@class=\'m-scoreOffer__msg\']"}'
        save_screenshot(driver, info_text, bookmaker_matchid='1')


if __name__ == '__main__':
    unittest.main()
