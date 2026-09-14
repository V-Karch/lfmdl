import os
import csv
import json
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.firefox.options import Options


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

    login_button = driver.find_element(
        By.XPATH, "/html/body/div[2]/div/div/section/div[1]/div/div/form/div/input"
    )
    login_button.click()


def scan_page_for_links(driver: WebDriver) -> list[dict]:
    books = driver.find_elements(By.CSS_SELECTOR, "section.account-list-item")

    downloads: list[dict] = []

    for book in books:
        title = book.find_element(By.CSS_SELECTOR, "h3.h4").text.strip()
        author = (
            book.find_element(By.CSS_SELECTOR, "img.book-cover")
            .get_attribute("alt")
            .split(" by ", 1)[1]
        )
        links = book.find_elements(By.CSS_SELECTOR, "a.ga4-download-link")

        for link in links:
            downloads.append(
                {
                    "title": title,
                    "author": author,
                    "isbn": link.get_attribute("data-isbn"),
                    "format": link.get_attribute("data-format"),
                    "download_name": link.get_attribute("title"),
                    "url": link.get_attribute("href"),
                }
            )

    return downloads


def collect_all_download_links(driver: WebDriver) -> list[dict]:
    driver.get("https://libro.fm/user/library")

    all_downloads: list[dict] = []

    page = 1

    while True:
        url = f"https://libro.fm/user/library?page={page}"
        driver.get(url)

        page_downloads = scan_page_for_links(driver)
        all_downloads.extend(page_downloads)

        next_links = driver.find_elements(By.CSS_SELECTOR, 'a[aria-label="Next page"]')
        if not next_links:
            break

        next_url = next_links[0].get_attribute("href")

        if not next_url:
            break

        page += 1

    return all_downloads


def setup_output_directory(
    output_directory_name: str, download_links: list[dict]
) -> set[tuple[str, str]]:
    os.mkdir(output_directory_name)

    print("Making author directories...")

    author_book_pairs: set[tuple[str, str]] = set()
    for download_link in download_links:
        author_book_pairs.add((download_link.get("author"), download_link.get("title")))

    for pair in author_book_pairs:
        os.makedirs(os.path.join(output_directory_name, pair[0], pair[1]))

    print("Output directory set up!")

    return author_book_pairs


def main() -> None:
    print("Attempting login/setup...")
    # Setup / Login
    options = Options()

    options.set_preference("browser.download.folderList", 2)
    options.set_preference("browser.download.dir", os.getcwd())
    options.set_preference(
        "browser.helperApps.neverAsk.saveToDisk",
        "text/csv,application/csv,application/octet-stream",
    )
    options.set_preference("browser.download.manager.showWhenStarting", False)
    options.set_preference("pdfjs.disabled", True)

    driver = webdriver.Firefox(options=options)
    driver.implicitly_wait(10)

    try:
        login_sequence(driver)
        print("Logged in!")

        print("Collecting all download links...")
        download_links = collect_all_download_links(driver)

        print(download_links[0])
        print(download_links[1])
        print(download_links[2])

        download_type = input("Which format would you like to download? (mp3/m4b)\n$ ")

        print("Setting up output directory...")

        output_directory_name = f"library_backup_{int(time.time())}"
        author_book_pairs = setup_output_directory(
            output_directory_name, download_links
        )

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
