"""Minimal web application for the Docker MVP."""

import os
from typing import Final

import psycopg
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

APP_TITLE: Final[str] = "Generate or Not MVP"
DATABASE_URL_KEY: Final[str] = "DATABASE_URL"

app = FastAPI(title=APP_TITLE)


def get_database_url() -> str:
    """Return the PostgreSQL connection URL from environment.

    Args:
        None.

    Returns:
        The database connection URL.
    """
    return os.getenv(DATABASE_URL_KEY, "")


def is_database_reachable(database_url: str) -> bool:
    """Check if PostgreSQL is reachable with a simple query.

    Args:
        database_url: PostgreSQL connection URL.

    Returns:
        True when the query succeeds, otherwise False.
    """
    if not database_url:
        return False

    try:
        with psycopg.connect(database_url, connect_timeout=2) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                cursor.fetchone()
        return True
    except psycopg.Error:
        return False


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """Render the landing page.

    Args:
        None.

    Returns:
        A static HTML response.
    """
    return """<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Generate or Not MVP</title>
    <style>
      :root {
        color-scheme: light;
        --bg-start: #edf6f9;
        --bg-end: #ffddd2;
        --card: #ffffff;
        --text: #14213d;
        --accent: #e76f51;
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        min-height: 100vh;
        font-family: "Trebuchet MS", "Segoe UI", sans-serif;
        background: linear-gradient(160deg, var(--bg-start), var(--bg-end));
        display: grid;
        place-items: center;
        color: var(--text);
      }

      .card {
        width: min(720px, 92vw);
        background: var(--card);
        border-radius: 16px;
        box-shadow: 0 20px 40px rgba(20, 33, 61, 0.16);
        padding: clamp(1.5rem, 2.5vw, 2rem);
      }

      h1 {
        margin-top: 0;
        margin-bottom: 0.6rem;
        font-size: clamp(1.6rem, 3vw, 2.2rem);
      }

      p {
        margin: 0.5rem 0;
        line-height: 1.5;
      }

      .tag {
        display: inline-block;
        margin-top: 0.8rem;
        padding: 0.35rem 0.65rem;
        border-radius: 999px;
        background: var(--accent);
        color: #ffffff;
        font-size: 0.9rem;
      }
    </style>
  </head>
  <body>
    <main class=\"card\">
      <h1>Generate or Not</h1>
      <p>The MVP stack is running with Docker Compose.</p>
      <p>This page is served by the web app on port 6767.</p>
      <p class=\"tag\">Database starts empty and is internal-only</p>
    </main>
  </body>
</html>
"""


@app.get("/health")
def health() -> dict[str, str]:
    """Return app and database health status.

    Args:
        None.

    Returns:
        A dictionary with app and database status values.
    """
    db_status = "up" if is_database_reachable(get_database_url()) else "down"
    return {"app": "up", "db": db_status}
