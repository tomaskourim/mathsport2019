import json
import logging
import os
import time
from string import punctuation
from typing import Tuple

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys


def load_credentials(credentials_file_path: str) -> Tuple[str, str]:
    credentials = json.load(open(credentials_file_path, "rb"))
    return credentials.get("username"), credentials.get("password")


def write_xpath(driver: webdriver, xpath: str, text: str):
    driver.find_element_by_xpath(xpath).send_keys(text)


def write_id(driver: webdriver, element_id: str, text: str):
    elem = driver.find_element_by_id(element_id)
    elem.click()
    time.sleep(2)
    elem.send_keys(text)


def clear_id(driver: webdriver, element_id: str):
    elem = driver.find_element_by_id(element_id)
    elem.clear()


def send_keys_id(driver: webdriver, element_id: str, key: Keys):
    elem = driver.find_element_by_id(element_id)
    elem.send_keys(key)


def click_id(driver: webdriver, element_id: str):
    driver.find_element_by_id(element_id).click()


def click_xpath(driver: webdriver, xpath: str):
    driver.find_element_by_xpath(xpath).click()


def save_screenshot(driver: webdriver, info_text: str, bookmaker_matchid: str):
    screen_order = 1
    for punct in punctuation:
        info_text = info_text.replace(punct, '_')
    screen_filename = f'screens/{bookmaker_matchid}-{info_text}-{screen_order}.png'
    while os.path.isfile(screen_filename):
        screen_order = screen_order + 1
        screen_filename = f'screens/{bookmaker_matchid}-{info_text}-{screen_order}.png'
    try:
        driver.save_screenshot(screen_filename)
    except TimeoutException:
        logging.error(
            f'Timeout while saving screenshot in match {bookmaker_matchid}. Original error message text: {info_text}')
    except Exception:
        logging.exception(
            f'Error while saving screenshot in match {bookmaker_matchid}. Original error message text: {info_text}')
