import json
from typing import Tuple

from selenium import webdriver


def load_fb_credentials(credentials_file_path: str) -> Tuple[str, str]:
    credentials = json.load(open(credentials_file_path, "rb"))
    return credentials.get("username"), credentials.get("password")


def write_xpath(driver: webdriver, xpath: str, text: str):
    driver.find_element_by_xpath(xpath).send_keys(text)


def write_id(driver: webdriver, element_id: str, text: str):
    driver.find_element_by_id(element_id).send_keys(text)


def click_id(driver: webdriver, element_id: str):
    driver.find_element_by_id(element_id).click()
