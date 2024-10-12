A simple collection of scripts that read the Backloggd profiles of users and display their stats with a custom scoring formula.

There's 3 major scripts in this collection:
- `spider-scraper.py`: Scrapes the Backloggd profiles of users and saves their game data to a CSV file.
- `igdb-fetcher.py`: Fetches the IGDB data of the games in the CSV file and saves it into SQLite.
- `sqliter.py`: Combines all scraped CSVs into a single SQLite database and outputs a single CSV file with the final stats.

To run `igdb-fetcher.py`, you need to have your `TWITCH_CLIENT_ID` and `TWITCH_CLIENT_SECRET` set inside a `.env` file in the same directory as the script. You can generate those here: https://api-docs.igdb.com/#getting-started