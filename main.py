import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver


def login_sequence(driver: WebDriver):
    driver.get("https://libro.fm/login")

    with open("config.txt", "r") as f:
        config_data: list[str] = [i.strip() for i in f.readlines()]
        email: str = config_data[0].split("=")[1]
        password: str = config_data[1].split("=")[1]

    enter_email_button = driver.find_element(By.XPATH, '//*[@id="email"]')
    enter_email_button.send_keys(email)

    enter_password_button = driver.find_element(By.XPATH, '//*[@id="password"]')
    enter_password_button.send_keys(password)

    del enter_email_button
    del enter_password_button

    login_button = driver.find_element(
        By.XPATH, "/html/body/div[2]/div/div/section/div[1]/div/div/form/div/input"
    )
    login_button.click()

    del login_button


def main() -> None:
    driver: WebDriver = webdriver.Firefox()
    driver.implicitly_wait = 5

    login_sequence(driver)

    time.sleep(5)


if __name__ == "__main__":
    main()
