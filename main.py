import os
import csv
import json
import time
import shutil
import zipfile
from urllib.parse import urlparse, parse_qs, unquote

import requests

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
    driver.implicitly_wait(10)
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

    driver.implicitly_wait(120)

    return all_downloads


def setup_output_directory(output_directory_name: str, download_links: list[dict]):
    os.mkdir(output_directory_name)

    print("Making author directories...")

    for download_link in download_links:
        os.makedirs(
            os.path.join(
                output_directory_name,
                download_link.get("author"),
                download_link.get("title"),
            ),
            exist_ok=True,
        )

    print("Output directory set up!")


def create_requests_session(driver: WebDriver) -> requests.Session:
    session = requests.Session()

    for cookie in driver.get_cookies():
        session.cookies.set(
            cookie["name"],
            cookie["value"],
            domain=cookie.get("domain"),
            path=cookie.get("path", "/"),
        )

    return session


def get_filename_from_url(url: str) -> str:
    parsed_url = urlparse(url)
    query = parse_qs(parsed_url.query)

    filename = query.get("file", ["download.m4b"])[0]

    return unquote(filename)


def download_m4b_files(
    driver: WebDriver,
    download_links: list[dict],
    output_directory_name: str,
):
    session = create_requests_session(driver)

    m4b_links = [
        download_link
        for download_link in download_links
        if "m4b" in download_link.get("download_name", "").lower()
    ]

    print(f"Found {len(m4b_links)} m4b files to download.")

    for index, download_link in enumerate(m4b_links, start=1):
        title = download_link.get("title")
        author = download_link.get("author")
        url = download_link.get("url")

        filename = get_filename_from_url(url)

        output_directory = os.path.join(
            output_directory_name,
            author,
            title,
        )

        output_path = os.path.join(
            output_directory,
            filename,
        )

        print(f"[{index}/{len(m4b_links)}] Downloading {title}...")

        response = session.get(
            url,
            stream=True,
            timeout=120,
        )

        response.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

        print(f"Saved: {output_path}")


def download_mp3_files(
    driver: WebDriver,
    download_links: list[dict],
    output_directory_name: str,
):
    session = create_requests_session(driver)

    mp3_links = [
        download_link
        for download_link in download_links
        if "m4b" not in download_link.get("download_name", "").lower()
    ]

    print(f"Found {len(mp3_links)} MP3 zip files to download.")

    for index, download_link in enumerate(mp3_links, start=1):
        title = download_link.get("title")
        author = download_link.get("author")
        url = download_link.get("url")

        output_directory = os.path.join(
            output_directory_name,
            author,
            title,
        )

        filename = get_filename_from_url(url)

        if not filename.lower().endswith(".zip"):
            filename += ".zip"

        zip_path = os.path.join(
            output_directory,
            filename,
        )

        print(f"[{index}/{len(mp3_links)}] " f"Downloading {title} ({filename})...")

        response = session.get(
            url,
            stream=True,
            timeout=120,
        )

        response.raise_for_status()

        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

        print(f"Downloaded: {zip_path}")
        print(f"Extracting {filename}...")

        with zipfile.ZipFile(zip_path, "r") as zip_file:
            for zip_info in zip_file.infolist():
                if zip_info.is_dir():
                    continue

                original_filename = os.path.basename(zip_info.filename)

                prefix = f"{title} - "

                if original_filename.startswith(prefix):
                    new_filename = original_filename[len(prefix) :]
                else:
                    new_filename = original_filename

                output_path = os.path.join(
                    output_directory,
                    new_filename,
                )

                with zip_file.open(zip_info) as source:
                    with open(output_path, "wb") as destination:
                        shutil.copyfileobj(source, destination)

        os.remove(zip_path)

        print(f"Extracted and cleaned up: {title}")


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
    options.add_argument("--headless")

    driver = webdriver.Firefox(options=options)
    driver.implicitly_wait(120)

    try:
        login_sequence(driver)
        print("Logged in!")

        print("Collecting all download links...")
        download_links = collect_all_download_links(driver)

        download_type = input("Which format would you like to download? (mp3/m4b)\n$ ")

        print("Setting up output directory...")

        output_directory_name = f"library_backup_{int(time.time())}"

        setup_output_directory(
            output_directory_name,
            download_links,
        )

        print("Attempting full library download...")

        if download_type == "mp3":
            download_mp3_files(
                driver,
                download_links,
                output_directory_name,
            )

        if download_type == "m4b":
            download_m4b_files(
                driver,
                download_links,
                output_directory_name,
            )

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
