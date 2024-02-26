## Overview
This is a simple web scraper spider which scrapes game log data from your Backloggd profile.(https://backloggd.com/)

The scraped data is organized by status (played, playing, backlog, wishlist) and export to a CSV file `all_entries.csv`.
  
## Installation

1. **Clone the repository**

2. **Install Python dependencies:**

    ```bash
    pip install -r requirements.txt
    ```
### Optional
 - A python virtual environment would help manage packages more clearly
## Usage

1. **Run the spider:**

    ```bash
    python spider-scraper.py
    ```

2. **Enter your Backloggd profile username when prompted.**

3. **Wait for the spider to scrape data from your profile.**

4. **Find the scraped data in the file `all_entries.csv`.**

## Notes

- This spider scrapes data directly from Backloggd's website since there is no official API available.
- Use responsibly and respect the website's terms of service.
