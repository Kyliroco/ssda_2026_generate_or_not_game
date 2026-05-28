"""Image scanning and random question selection."""

import logging
import random
from pathlib import Path
from typing import Final, TypedDict

DATA_DIR: Final[Path] = Path("/data/data")
IMAGE_EXTENSIONS: Final[set[str]] = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"}
QUESTIONS_PER_SESSION: Final[int] = 20
HUMAN_DATASET: Final[int] = 2
ALTERED_DATASETS: Final[tuple[int, ...]] = (1, 3, 4)
MATCHED_ALTERED_DATASET: Final[int] = 1
logger = logging.getLogger(__name__)


class ImagePools(TypedDict):
    """Image pools used to build gameplay questions.

    Attributes:
        human_paths: API paths for human images from dataset 2.
        altered_by_dataset: Altered API paths grouped by dataset id.
    """

    human_paths: list[str]
    altered_by_dataset: dict[int, list[str]]


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


def _filter_matched_altered_paths(
    altered_dataset: int,
    altered_paths: list[str],
    human_names: set[str],
) -> list[str]:
    """Filter altered paths by filename presence in human dataset.

    Args:
        altered_dataset: Altered dataset number.
        altered_paths: Relative paths found in altered dataset.
        human_names: Filenames present in human dataset.

    Returns:
        API-ready paths that match filenames from human dataset.
    """
    eligible_api_paths: list[str] = []
    dropped_count = 0

    for rel_path in altered_paths:
        filename = Path(rel_path).name
        if filename not in human_names:
            dropped_count += 1
            continue
        eligible_api_paths.append(f"{altered_dataset}/{rel_path}")

    if dropped_count > 0:
        logger.warning(
            "Dropped %s altered images from /data/data/%s because matching filenames were not found in /data/data/2",
            dropped_count,
            altered_dataset,
        )

    logger.info(
        "Prepared altered dataset %s with matching enabled: eligible=%s dropped=%s",
        altered_dataset,
        len(eligible_api_paths),
        dropped_count,
    )
    return eligible_api_paths


def _build_unfiltered_altered_paths(altered_dataset: int, altered_paths: list[str]) -> list[str]:
    """Build API-ready paths without filename matching.

    Args:
        altered_dataset: Altered dataset number.
        altered_paths: Relative paths found in altered dataset.

    Returns:
        API-ready paths for every altered image file.
    """
    eligible_api_paths = [f"{altered_dataset}/{rel_path}" for rel_path in altered_paths]
    logger.info(
        "Prepared altered dataset %s with no matching filter: eligible=%s",
        altered_dataset,
        len(eligible_api_paths),
    )
    return eligible_api_paths


def _build_altered_paths_by_dataset(human_paths: list[str]) -> dict[int, list[str]]:
    """Build altered image pools per dataset.

    Args:
        human_paths: Relative image paths from human dataset 2.

    Returns:
        A mapping from altered dataset id to API-ready image paths.
        Matching against dataset 2 is applied only for dataset 1.
    """
    human_names = {Path(path).name for path in human_paths}
    altered_paths_by_dataset: dict[int, list[str]] = {}

    for altered_dataset in ALTERED_DATASETS:
        altered_paths = _scan_category_files(altered_dataset)
        if altered_dataset == MATCHED_ALTERED_DATASET:
            altered_paths_by_dataset[altered_dataset] = _filter_matched_altered_paths(
                altered_dataset,
                altered_paths,
                human_names,
            )
        else:
            altered_paths_by_dataset[altered_dataset] = _build_unfiltered_altered_paths(
                altered_dataset,
                altered_paths,
            )

    return altered_paths_by_dataset


def scan_images() -> ImagePools:
    """Build image pools for human and altered question selection.

    Args:
        None.

    Returns:
        A dictionary with two pools:
        - "human_paths": list of API paths in dataset 2.
        - "altered_by_dataset": mapping from altered dataset to API paths.
    """
    human_rel_paths = _scan_category_files(HUMAN_DATASET)
    human_api_paths = [f"{HUMAN_DATASET}/{path}" for path in human_rel_paths]
    altered_by_dataset = _build_altered_paths_by_dataset(human_rel_paths)
    altered_total = sum(len(paths) for paths in altered_by_dataset.values())

    logger.info(
        "Prepared pools: human=%s altered_total=%s",
        len(human_api_paths),
        altered_total,
    )

    return {
        "human_paths": human_api_paths,
        "altered_by_dataset": altered_by_dataset,
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
    altered_by_dataset: dict[int, list[str]] = pools["altered_by_dataset"]
    available_altered_datasets = [dataset for dataset, paths in altered_by_dataset.items() if paths]

    if not human_paths and not available_altered_datasets:
        logger.error(
            "No selectable images were found in /data/data. Falling back to blue placeholder questions. "
            "Check /data/data/1, /data/data/3, /data/data/4 and /data/data/2 contents. "
            "Filename matching against /data/data/2 is required only for /data/data/1."
        )
        return [
            {"path": f"placeholder/{i}", "category": random.randint(1, 2), "is_placeholder": True}
            for i in range(count)
        ]

    questions: list[dict] = []
    for _ in range(count):
        pick_altered = False
        if available_altered_datasets and human_paths:
            pick_altered = random.choice([True, False])
        elif available_altered_datasets:
            pick_altered = True

        if pick_altered:
            selected_dataset = random.choice(available_altered_datasets)
            selected_path = random.choice(altered_by_dataset[selected_dataset])
            questions.append({"path": selected_path, "category": selected_dataset, "is_placeholder": False})
        else:
            selected_path = random.choice(human_paths)
            questions.append({"path": selected_path, "category": 2, "is_placeholder": False})

    return questions
