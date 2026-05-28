"""Image scanning and random question selection."""

import logging
import random
from pathlib import Path
from typing import Final

DATA_DIR: Final[Path] = Path("/data/data")
IMAGE_EXTENSIONS: Final[set[str]] = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"}
QUESTIONS_PER_SESSION: Final[int] = 20
logger = logging.getLogger(__name__)


def _scan_category_files(category: int) -> list[str]:
    """Return category image paths relative to the category folder.

    Args:
        category: Category folder number (1 or 2).

    Returns:
        A sorted list of POSIX relative paths for image files.
    """
    category_dir = DATA_DIR / str(category)
    if not category_dir.is_dir():
        logger.warning("Image directory missing: %s", category_dir)
        return []

    rel_paths: list[str] = []
    for file_path in sorted(category_dir.rglob("*")):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        rel_paths.append(file_path.relative_to(category_dir).as_posix())

    logger.info(
        "Scanned category %s in %s, found %s eligible image files",
        category,
        category_dir,
        len(rel_paths),
    )
    return rel_paths


def _filter_category_one_against_two(category_one_paths: list[str], category_two_paths: list[str]) -> list[str]:
    """Keep category 1 images only when the filename also exists in category 2.

    Args:
        category_one_paths: Relative image paths from category 1.
        category_two_paths: Relative image paths from category 2.

    Returns:
        Filtered category 1 paths with existing filename matches in category 2.
    """
    category_two_names = {Path(path).name for path in category_two_paths}
    return [path for path in category_one_paths if Path(path).name in category_two_names]


def scan_images() -> list[dict]:
    """Scan available images and apply category matching constraints.

    Args:
        None.

    Returns:
        A list of image descriptors with API-ready paths and categories.
    """
    images: list[dict] = []

    category_one_paths = _scan_category_files(1)
    category_two_paths = _scan_category_files(2)

    filtered_category_one = _filter_category_one_against_two(category_one_paths, category_two_paths)

    dropped_category_one = len(category_one_paths) - len(filtered_category_one)
    if dropped_category_one > 0:
        logger.warning(
            "Dropped %s category-1 images because matching filenames were not found in /data/data/2",
            dropped_category_one,
        )

    for rel_path in filtered_category_one:
        images.append({"path": f"1/{rel_path}", "category": 1})

    for rel_path in category_two_paths:
        images.append({"path": f"2/{rel_path}", "category": 2})

    logger.info(
        "Prepared image pool: category1=%s (matched), category2=%s, total=%s",
        len(filtered_category_one),
        len(category_two_paths),
        len(images),
    )

    return images


def pick_questions(count: int = QUESTIONS_PER_SESSION) -> list[dict]:
    """Pick random questions from scanned images.

    Args:
        count: Number of questions to include in the session.

    Returns:
        A list of selected question dictionaries.
    """
    images = scan_images()
    if not images:
        logger.error(
            "No selectable images were found in /data/data. Falling back to blue placeholder questions. "
            "Check /data/data/1 and /data/data/2 contents and matching filenames."
        )
        return [
            {"path": f"placeholder/{i}", "category": random.randint(1, 2), "is_placeholder": True}
            for i in range(count)
        ]
    selected = random.choices(images, k=count) if len(images) < count else random.sample(images, count)
    return [{"path": img["path"], "category": img["category"], "is_placeholder": False} for img in selected]
