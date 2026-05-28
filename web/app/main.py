"""Generate or Not — game web application."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path, PurePosixPath
from typing import Final

import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .routers import admin, leaderboard, players, sessions

APP_TITLE: Final[str] = "Generate or Not"
DATABASE_URL_KEY: Final[str] = "DATABASE_URL"
STATIC_DIR: Path = Path(__file__).parent / "static"
DATA_DIR: Final[str] = "/data"
logger = logging.getLogger(__name__)

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
app.include_router(admin.router)

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


def _is_safe_relative_path(path_value: str) -> bool:
    """Validate an image relative path.

    Args:
        path_value: Relative path provided by the client.

    Returns:
        True when the path is safe to use, otherwise False.
    """
    posix_path = PurePosixPath(path_value)
    if path_value.startswith("/"):
        return False
    if not posix_path.parts:
        return False

    for part in posix_path.parts:
        if part in {".", ".."}:
            return False
        if not all(char in _SAFE_CHARS for char in part):
            return False
    return True


@app.get(
    "/api/images/{category}/{file_path:path}",
    responses={
        400: {"description": "Invalid filename"},
        404: {"description": "Category not found or image not found"},
    },
)
def serve_image(category: int, file_path: str) -> FileResponse:
    """Serve one image file from a category folder.

    Args:
        category: Image category (1 or 2).
        file_path: Relative file path under the category folder.

    Returns:
        The requested image file response.
    """
    if category not in (1, 2):
        logger.warning("Image request rejected: unknown category=%s path=%s", category, file_path)
        raise HTTPException(status_code=404, detail="Category not found")
    if not _is_safe_relative_path(file_path):
        logger.warning("Image request rejected: invalid relative path category=%s path=%s", category, file_path)
        raise HTTPException(status_code=400, detail="Invalid filename")

    category_dir = Path(DATA_DIR) / str(category)
    path = (category_dir / file_path).resolve()
    try:
        path.relative_to(category_dir.resolve())
    except ValueError as error:
        logger.warning(
            "Image request rejected: path traversal attempt category=%s path=%s",
            category,
            file_path,
        )
        raise HTTPException(status_code=400, detail="Invalid filename") from error

    if not path.is_file():
        logger.error(
            "Image file not found. category=%s requested=%s resolved=%s",
            category,
            file_path,
            path,
        )
        raise HTTPException(status_code=404, detail="Image not found")

    logger.info("Serving image. category=%s path=%s", category, file_path)
    return FileResponse(str(path))


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/results", response_class=HTMLResponse)
def results() -> str:
    return (STATIC_DIR / "results.html").read_text(encoding="utf-8")
