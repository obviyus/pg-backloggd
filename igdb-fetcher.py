import sqlite3
import requests
from time import sleep
from sqliter import DB_FILENAME
from dotenv import dotenv_values

config = dotenv_values(".env")


def fetch_access_token():
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": config["TWITCH_CLIENT_ID"],
        "client_secret": config["TWITCH_CLIENT_SECRET"],
        "grant_type": "client_credentials",
    }
    response = requests.post(url, params=params)

    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        print(
            f"Failed to fetch access token. Status code: {response.status_code}\nResponse: {response.text}"
        )
        return None


def fetch_game_info(game_id, access_token, retries=3):
    url = "https://api.igdb.com/v4/games"
    headers = {
        "Client-ID": config["TWITCH_CLIENT_ID"],
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    data = f"fields url,first_release_date,websites.url; where id = {game_id};"

    for _ in range(retries):
        response = requests.post(url, headers=headers, data=data)

        if response.status_code == 200:
            try:
                json_response = response.json()
                if json_response:
                    game = json_response[0]
                    igdb_url = game.get("url")
                    first_release_date = game.get("first_release_date")
                    steam_url = next(
                        (
                            x["url"]
                            for x in game.get("websites", [])
                            if "store.steampowered.com" in x["url"]
                        ),
                        None,
                    )
                    return igdb_url, first_release_date, steam_url
                else:
                    print(f"Empty response for game_id: {game_id}")
                    return None, None, None
            except ValueError:
                print(f"Failed to parse JSON for game_id: {game_id}")
                return None, None, None
        elif response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 5))
            print(f"Rate limited. Retrying after {retry_after} seconds...")
            sleep(retry_after)
        else:
            print(
                f"Failed to fetch game info for game_id: {game_id}. Status code: {response.status_code}\nResponse: {response.text}"
            )
            return None, None, None

    print(f"Max retries reached for game_id: {game_id}")
    return None, None, None


def runner():
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()

    cursor.execute("SELECT game_id FROM games WHERE igdb_url IS NULL;")
    game_ids = cursor.fetchall()

    access_token = fetch_access_token()
    if not access_token:
        return

    for (game_id,) in game_ids:
        igdb_url, first_release_date, steam_url = fetch_game_info(game_id, access_token)

        if igdb_url is not None:
            cursor.execute(
                """
                UPDATE games
                SET igdb_url = ?, first_release_date = ?, steam_url = ?
                WHERE game_id = ?;
                """,
                (igdb_url, first_release_date, steam_url, game_id),
            )
            cursor.connection.commit()

        sleep(1)


if __name__ == "__main__":
    runner()
