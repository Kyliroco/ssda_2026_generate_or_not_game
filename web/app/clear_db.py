"""Admin script: truncate all game tables and reset primary key sequences.

Usage (inside the web container):
    python app/clear_db.py          # interactive confirmation
    python app/clear_db.py --yes    # skip confirmation
"""

import os
import sys

import psycopg

_DATABASE_URL = os.getenv("DATABASE_URL", "")

_TABLES = ["session_questions", "game_sessions", "players"]


def _count(conn: psycopg.Connection, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: S608


def main() -> None:
    if not _DATABASE_URL:
        print("ERROR: DATABASE_URL environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    skip_confirm = "--yes" in sys.argv

    with psycopg.connect(_DATABASE_URL) as conn:
        print("Current row counts:")
        for table in _TABLES:
            print(f"  {table}: {_count(conn, table)} rows")

        if not skip_confirm:
            answer = input("\nThis will delete ALL data. Type 'yes' to confirm: ").strip()
            if answer.lower() != "yes":
                print("Aborted.")
                sys.exit(0)

        conn.execute(
            "TRUNCATE session_questions, game_sessions, players RESTART IDENTITY CASCADE"
        )
        conn.commit()

        print("\nTables cleared. Row counts after:")
        for table in _TABLES:
            print(f"  {table}: {_count(conn, table)} rows")

    print("\nDone.")


if __name__ == "__main__":
    main()
