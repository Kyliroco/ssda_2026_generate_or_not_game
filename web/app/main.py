"""Generate or Not — game web application."""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Final

import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .routers import leaderboard, players, sessions

APP_TITLE: Final[str] = "Generate or Not"
DATABASE_URL_KEY: Final[str] = "DATABASE_URL"
STATIC_DIR: Path = Path(__file__).parent / "static"
DATA_DIR: Final[str] = "/data"

_SAFE_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._- ()"
)


@asynccontextmanager
async def lifespan(application: FastAPI):  # noqa: ARG001
    init_db()
    yield


app = FastAPI(title=APP_TITLE, lifespan=lifespan)

app.include_router(players.router)
app.include_router(sessions.router)
app.include_router(leaderboard.router)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _get_database_url() -> str:
    return os.getenv(DATABASE_URL_KEY, "")


def _is_database_reachable(url: str) -> bool:
    if not url:
        return False
    try:
        with psycopg.connect(url, connect_timeout=2) as conn:
            conn.execute("SELECT 1")
        return True
    except psycopg.Error:
        return False


@app.get("/health")
def health() -> dict[str, str]:
    db_status = "up" if _is_database_reachable(_get_database_url()) else "down"
    return {"app": "up", "db": db_status}


@app.get("/api/images/{category}/{filename}")
def serve_image(category: int, filename: str) -> FileResponse:
    if category not in (1, 2):
        raise HTTPException(status_code=404, detail="Category not found")
    if not all(c in _SAFE_CHARS for c in filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = os.path.join(DATA_DIR, str(category), filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")
