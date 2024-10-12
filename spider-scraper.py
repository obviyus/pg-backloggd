import scrapy
import csv
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import re


class AllCategoriesSpider(scrapy.Spider):
    name = "all_categories"
    allowed_domains = ["backloggd.com"]

    def __init__(self, username=None, *args, **kwargs):
        super(AllCategoriesSpider, self).__init__(*args, **kwargs)
        self.username = username
        if username:
            self.start_urls = [
                f"https://www.backloggd.com/u/{username}/games/added/type:played/",
                f"https://www.backloggd.com/u/{username}/games/added/type:playing/",
                f"https://www.backloggd.com/u/{username}/games/added/type:backlog/",
                f"https://www.backloggd.com/u/{username}/games/added/type:wishlist/",
            ]
        else:
            raise ValueError("Please enter a username when prompted")

        self.custom_settings = {
            "ROBOTSTXT_OBEY": False,
        }

        self.results = []

    # Generates initial requests to send to server
    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse, errback=self.handle_error)

    def parse(self, response):
        self.log(f"Received response for {response.url}")

        url_type = response.url.split(":")[-1]
        if "played" in url_type:
            status = "Played"
        elif "playing" in url_type:
            status = "Playing"
        elif "backlog" in url_type:
            status = "Backlog"
        elif "wishlist" in url_type:
            status = "Wishlist"
        else:
            status = "Unknown"

        for card in response.css("div.card.mx-auto.game-cover"):
            game = card.css("div.game-text-centered::text").get().strip()
            rating = card.css("div.card.mx-auto.game-cover::attr(data-rating)").get()
            game_id = card.css("div.card.mx-auto.game-cover::attr(game_id)").get()

            data = {
                "Game": game,
                "Status": status,
                "Rating": rating,
                "Game ID": game_id,
            }
            self.results.append(data)
            self.log(
                f"Scraped: Game: {game}, Status: {status}, Rating: {rating}, Game ID: {game_id}"
            )

        next_page = response.css('a[rel="next"]::attr(href)').get()
        if next_page:
            self.log(f"Following next page: {urljoin(response.url, next_page)}")
            yield scrapy.Request(
                url=urljoin(response.url, next_page),
                callback=self.parse,
                errback=self.handle_error,
            )

    def scrape_journal_data(self, url):
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        entries = soup.find_all("div", class_="journal_entry")

        data = []
        # Keep track of seen games
        seen_games = set()

        for entry in entries:
            game_name_elem = entry.find("div", class_="col col-md-4 my-auto game-name")
            game_name = (
                game_name_elem.find("a").text.strip() if game_name_elem else None
            )

            # Clean the game title
            cleaned_game_name = self.clean_game_title(game_name)

            # Check if the game name has been seen before
            if cleaned_game_name not in seen_games:
                seen_games.add(cleaned_game_name)

                # Extract URL of game's log page
                formatted_game_name = re.sub(
                    r"[^a-zA-Z0-9]", "-", cleaned_game_name.lower()
                )
                game_url = f"https://www.backloggd.com/u/{username}/logs/{formatted_game_name}/"

                # Scrape the game's log page for the dates
                first_played_date, last_played_date = self.scrape_played_dates(game_url)
                data.append(
                    {
                        "Game Name": game_name,
                        "Started on": first_played_date,
                        "Finished on": last_played_date,
                    }
                )

        return data

    def scrape_played_dates(self, game_url):
        response = requests.get(game_url)
        soup = BeautifulSoup(response.text, "html.parser")

        # HTML structures labeling the "First Played" and "Last Played" dates
        date_elem_candidates = soup.find_all("div", class_="col mt-2 mt-lg-0")
        first_played_date = None
        last_played_date_elem = None

        # Check for both "Started" and "Finished" bits
        started_found = False
        finished_found = False

        for candidate in date_elem_candidates:
            date_elem = candidate.find("p", class_="date-tooltip right-tooltip")
            if date_elem:
                status_elem = candidate.find_next(
                    "div", class_="col-auto col-md-2 my-auto ml-auto order-md-last"
                )
                status_text = status_elem.text.strip().lower() if status_elem else None

                # Check if it's the "First Played" or "Last Played" date
                if not first_played_date:
                    if "started" in status_text:
                        first_played_date = date_elem.text.strip()
                        started_found = True
                    elif "finished" in status_text:
                        first_played_date = date_elem.text.strip()
                        finished_found = True
                else:
                    last_played_date_elem = date_elem

        if last_played_date_elem:
            last_played_date = last_played_date_elem.text.strip()
        else:
            # Failsafe to alternate structure if "Last Played" date not found
            last_played_elem = soup.find("div", class_="col mt-2 mt-sm-0")
            if last_played_elem:
                last_played_elem = last_played_elem.find(
                    "p", class_="date-tooltip right-tooltip"
                )

            last_played_date = (
                last_played_elem.text.strip() if last_played_elem else None
            )

        # If both "Started" and "Finished" found, insert into both columns
        if started_found and finished_found:
            last_played_date = first_played_date

        return first_played_date, last_played_date

    def combine_and_export_to_csv(self):
        csv_filename = f"backloggd-export/{self.username}.csv"
        fieldnames = [
            "Username",
            "Game",
            "Status",
            "Rating",
            "Game ID",
            "Start date",
            "Finish date",
        ]

        journal_data = self.scrape_journal_data(
            f"https://www.backloggd.com/u/{self.username}/journal/"
        )

        combined_data = []
        for category_entry in self.results:
            journal_entry = next(
                (
                    entry
                    for entry in journal_data
                    if entry["Game Name"] == category_entry["Game"]
                ),
                None,
            )

            if journal_entry:
                combined_entry = {
                    "Username": self.username,
                    "Game": category_entry["Game"],
                    "Status": category_entry["Status"],
                    "Rating": category_entry["Rating"],
                    "Game ID": category_entry["Game ID"],
                    "Start date": journal_entry["Started on"],
                    "Finish date": journal_entry["Finished on"],
                }
            else:
                combined_entry = {
                    "Username": self.username,
                    "Game": category_entry["Game"],
                    "Status": category_entry["Status"],
                    "Rating": category_entry["Rating"],
                    "Game ID": category_entry["Game ID"],
                    "Start date": None,
                    "Finish date": None,
                }

            combined_data.append(combined_entry)

        with open(csv_filename, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()

            for entry in combined_data:
                writer.writerow(entry)

        self.log(f"Data has been successfully combined and saved to {csv_filename}.")

    def clean_game_title(self, game_title):
        return game_title.replace(":", "")

    # Handles request processing errors
    def handle_error(self, failure):
        self.log(f"An error occurred: {repr(failure)}")

    # Handles the spider closing event
    def closed(self, reason):
        self.log("Spider closed: sorting results by category order...")
        self.results.sort(key=lambda x: (x["Status"], x["Game"]))
        self.combine_and_export_to_csv()


# Run the spider
if __name__ == "__main__":
    username = input("Enter your Backloggd profile username: ")
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings

    process = CrawlerProcess(get_project_settings())
    process.crawl(AllCategoriesSpider, username=username)
    process.start()
