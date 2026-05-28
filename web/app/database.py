"""Database connection and schema initialisation."""

import os
from contextlib import contextmanager
from typing import Generator

import psycopg

_DATABASE_URL_KEY = "DATABASE_URL"

_DDL_PLAYERS = """
CREATE TABLE IF NOT EXISTS players (
    id         SERIAL PRIMARY KEY,
    email      VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100)        NOT NULL,
    last_name  VARCHAR(100)        NOT NULL,
    created_at TIMESTAMPTZ         NOT NULL DEFAULT NOW()
)
"""

_DDL_SESSIONS = """
CREATE TABLE IF NOT EXISTS game_sessions (
    id              SERIAL PRIMARY KEY,
    player_id       INTEGER     NOT NULL REFERENCES players(id),
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    score           INTEGER,
    total_questions INTEGER     NOT NULL DEFAULT 20
)
"""

_DDL_QUESTIONS = """
CREATE TABLE IF NOT EXISTS session_questions (
    id                   SERIAL PRIMARY KEY,
    session_id           INTEGER      NOT NULL REFERENCES game_sessions(id),
    question_order       INTEGER      NOT NULL,
    image_path           VARCHAR(500) NOT NULL,
    correct_category     INTEGER      NOT NULL,
    is_placeholder       BOOLEAN      NOT NULL DEFAULT FALSE,
    user_answer          INTEGER,
    is_correct           BOOLEAN,
    answered_at          TIMESTAMPTZ,
    submitted_image_path VARCHAR(500),
    UNIQUE (session_id, question_order)
)
"""

# Migration for existing installs — safe to run repeatedly
_MIGRATE_SUBMITTED_PATH = """
ALTER TABLE session_questions
    ADD COLUMN IF NOT EXISTS submitted_image_path VARCHAR(500)
"""


def _get_url() -> str:
    return os.getenv(_DATABASE_URL_KEY, "")


@contextmanager
def get_db() -> Generator[psycopg.Connection, None, None]:
    conn = psycopg.connect(_get_url())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as conn:
        conn.execute(_DDL_PLAYERS)
        conn.execute(_DDL_SESSIONS)
        conn.execute(_DDL_QUESTIONS)
        conn.execute(_MIGRATE_SUBMITTED_PATH)
