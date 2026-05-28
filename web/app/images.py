"""Image scanning and random question selection."""

import random
from pathlib import Path
from typing import Final

DATA_DIR: Final[Path] = Path("/data")
IMAGE_EXTENSIONS: Final[set[str]] = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"}
QUESTIONS_PER_SESSION: Final[int] = 20


def _scan_category_files(category: int) -> list[str]:
    """Return category image paths relative to the category folder.

    Args:
        category: Category folder number (1 or 2).

    Returns:
        A sorted list of POSIX relative paths for image files.
    """
    category_dir = DATA_DIR / str(category)
    if not category_dir.is_dir():
        return []

    rel_paths: list[str] = []
    for file_path in sorted(category_dir.rglob("*")):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        rel_paths.append(file_path.relative_to(category_dir).as_posix())
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

    for rel_path in filtered_category_one:
        images.append({"path": f"1/{rel_path}", "category": 1})

    for rel_path in category_two_paths:
        images.append({"path": f"2/{rel_path}", "category": 2})

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
        return [
            {"path": f"placeholder/{i}", "category": random.randint(1, 2), "is_placeholder": True}
            for i in range(count)
        ]
    selected = random.choices(images, k=count) if len(images) < count else random.sample(images, count)
    return [{"path": img["path"], "category": img["category"], "is_placeholder": False} for img in selected]
