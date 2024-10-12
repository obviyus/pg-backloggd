from datetime import datetime
import sqlite3
import csv
import glob

DB_FILENAME = "pg.db"


def read_and_ingest_csv(filename: str, conn):
    cursor = conn.cursor()
    with open(filename, "r") as f:
        reader = csv.DictReader(f)
        data = [row for row in reader]

    for row in data:
        cursor.execute(
            """
            INSERT INTO games (game_id, game_name)
            VALUES (?, ?)
            ON CONFLICT(game_id) DO NOTHING
            """,
            (row["Game ID"], row["Game"]),
        )
        cursor.execute(
            """
            INSERT INTO user_ratings (username, game_id, rating, status)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(username, game_id) DO UPDATE SET rating = excluded.rating, status = excluded.status
            """,
            (row["Username"], row["Game ID"], row["Rating"], row["Status"]),
        )

    conn.commit()


# Backloggd username to preferred name mapping
backloggd_to_preferred = {
    "edward6d": "Ed",
    "Bowsori": "Bows",
    "PistolPumpkin": "Pie",
    "Repptilian": "Repp",
    "flint182": "Obviyus",
    "CartoonFan": "Arc",
}


def replace_names(names_string):
    if not names_string:
        return ""
    names = names_string.split(",")
    replaced_names = [
        backloggd_to_preferred.get(name.strip(), name.strip()) for name in names
    ]
    # Remove duplicates while preserving order
    seen = set()
    unique_replaced_names = [
        name for name in replaced_names if not (name in seen or seen.add(name))
    ]
    return ", ".join(unique_replaced_names)


def export_game_recommendations_to_csv(conn):
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT g.game_name,
               GROUP_CONCAT(CASE WHEN ur.rating >= 8 THEN ur.username END)         AS recommended_by,
               GROUP_CONCAT(CASE WHEN ur.rating <= 4 THEN ur.username END)         AS disliked_by,
               AVG(ur.rating)                                                      AS avg_score,
               GROUP_CONCAT(CASE WHEN ur.status = 'Wishlist' THEN ur.username END) AS wants_to_play,
               GROUP_CONCAT(CASE WHEN ur.status = 'Played' THEN ur.username END)   AS played_by,
               g.first_release_date,
               g.igdb_url,
               g.steam_url
        FROM games g
                 JOIN user_ratings ur ON g.game_id = ur.game_id
        WHERE ur.rating != ''
        GROUP BY g.game_name;
        """
    )

    with open("game_recommendations.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Title",
                "Recommended By",
                "Disliked By",
                "Avg Score",
                "Wants To Play",
                "Played By",
                "Release Date",
                "IGDB URL",
                "Steam URL",
            ]
        )

        for row in cursor.fetchall():
            (
                game_name,
                recommended_by,
                disliked_by,
                avg_score,
                wants_to_play,
                played_by,
                release_date,
                igdb_url,
                steam_url,
            ) = row

            if not recommended_by:
                continue

            if release_date:
                release_date = datetime.utcfromtimestamp(release_date).strftime(
                    "%Y-%m-%d"
                )

            writer.writerow(
                [
                    game_name,
                    replace_names(recommended_by),
                    replace_names(disliked_by),
                    avg_score,
                    replace_names(wants_to_play),
                    replace_names(played_by),
                    release_date,
                    igdb_url,
                    steam_url,
                ]
            )


def main():
    conn = sqlite3.connect(DB_FILENAME)
    try:
        for filename in glob.glob("backloggd-export/*.csv"):
            read_and_ingest_csv(filename, conn)

        export_game_recommendations_to_csv(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
