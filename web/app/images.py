"""Image scanning and random question selection."""

import os
import random

DATA_DIR = "/data"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"}
QUESTIONS_PER_SESSION = 20


def scan_images() -> list[dict]:
    images: list[dict] = []
    for category in (1, 2):
        dir_path = os.path.join(DATA_DIR, str(category))
        if not os.path.isdir(dir_path):
            continue
        for fname in sorted(os.listdir(dir_path)):
            if os.path.splitext(fname)[1].lower() in IMAGE_EXTENSIONS:
                images.append({"path": f"{category}/{fname}", "category": category})
    return images


def pick_questions(count: int = QUESTIONS_PER_SESSION) -> list[dict]:
    images = scan_images()
    if not images:
        return [
            {"path": f"placeholder/{i}", "category": random.randint(1, 2), "is_placeholder": True}
            for i in range(count)
        ]
    selected = random.choices(images, k=count) if len(images) < count else random.sample(images, count)
    return [{"path": img["path"], "category": img["category"], "is_placeholder": False} for img in selected]
