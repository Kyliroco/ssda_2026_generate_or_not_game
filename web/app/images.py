"""Image scanning and random question selection."""

import logging
import random
from pathlib import Path
from typing import Final

DATA_DIR: Final[Path] = Path("/data/data")
IMAGE_EXTENSIONS: Final[set[str]] = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"}
QUESTIONS_PER_SESSION: Final[int] = 20
HUMAN_DATASET: Final[int] = 2
ALTERED_DATASETS: Final[tuple[int, ...]] = (1, 3, 4)
logger = logging.getLogger(__name__)


def _scan_category_files(category: int) -> list[str]:
    """Return category image paths relative to the category folder.

    Args:
        category: Dataset folder number.

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


def _build_altered_options_by_filename(human_paths: list[str]) -> dict[str, list[str]]:
    """Build altered image options grouped by filename.

    Args:
        human_paths: Relative image paths from human dataset 2.

    Returns:
        A mapping from filename to altered image API paths from datasets 1/3/4.
        Only filenames that exist in dataset 2 are included.
    """
    human_names = {Path(path).name for path in human_paths}
    altered_options_by_filename: dict[str, list[str]] = {}

    for altered_dataset in ALTERED_DATASETS:
        altered_paths = _scan_category_files(altered_dataset)
        matched_count = 0
        dropped_count = 0

        for rel_path in altered_paths:
            filename = Path(rel_path).name
            if filename not in human_names:
                dropped_count += 1
                continue

            altered_options_by_filename.setdefault(filename, []).append(f"{altered_dataset}/{rel_path}")
            matched_count += 1

        if dropped_count > 0:
            logger.warning(
                "Dropped %s altered images from /data/data/%s because matching filenames were not found in /data/data/2",
                dropped_count,
                altered_dataset,
            )

        logger.info(
            "Prepared altered dataset %s: matched=%s dropped=%s",
            altered_dataset,
            matched_count,
            dropped_count,
        )

    return altered_options_by_filename


def scan_images() -> dict[str, list]:
    """Build image pools for human and altered question selection.

    Args:
        None.

    Returns:
        A dictionary with two pools:
        - "human_paths": list of API paths in dataset 2.
        - "altered_options": list of altered path option lists (from datasets 1/3/4) per filename.
    """
    human_rel_paths = _scan_category_files(HUMAN_DATASET)
    human_api_paths = [f"{HUMAN_DATASET}/{path}" for path in human_rel_paths]
    altered_by_filename = _build_altered_options_by_filename(human_rel_paths)
    altered_options = list(altered_by_filename.values())

    logger.info(
        "Prepared pools: human=%s altered_filenames=%s",
        len(human_api_paths),
        len(altered_options),
    )

    return {
        "human_paths": human_api_paths,
        "altered_options": altered_options,
    }


def pick_questions(count: int = QUESTIONS_PER_SESSION) -> list[dict]:
    """Pick random questions from scanned images.

    Args:
        count: Number of questions to include in the session.

    Returns:
        A list of selected question dictionaries.
    """
    pools = scan_images()
    human_paths: list[str] = pools["human_paths"]
    altered_options: list[list[str]] = pools["altered_options"]

    if not human_paths and not altered_options:
        logger.error(
            "No selectable images were found in /data/data. Falling back to blue placeholder questions. "
            "Check /data/data/1, /data/data/3, /data/data/4 and /data/data/2 contents and matching filenames."
        )
        return [
            {"path": f"placeholder/{i}", "category": random.randint(1, 2), "is_placeholder": True}
            for i in range(count)
        ]

    questions: list[dict] = []
    for _ in range(count):
        pick_altered = False
        if altered_options and human_paths:
            pick_altered = random.choice([True, False])
        elif altered_options:
            pick_altered = True

        if pick_altered:
            altered_paths_for_filename = random.choice(altered_options)
            selected_path = random.choice(altered_paths_for_filename)
            questions.append({"path": selected_path, "category": 1, "is_placeholder": False})
        else:
            selected_path = random.choice(human_paths)
            questions.append({"path": selected_path, "category": 2, "is_placeholder": False})

    return questions
