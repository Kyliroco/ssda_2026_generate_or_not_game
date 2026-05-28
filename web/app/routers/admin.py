"""Admin endpoints for the /results dashboard."""

import os
from typing import Final

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import get_db

_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
_HUMAN_CATEGORY: Final[int] = 2
_AI_MODELS: Final[dict[int, str]] = {
    1: "DiffusionPen",
    3: "Higan",
    4: "VATR++",
}

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _pct(num: int, den: int) -> float | None:
    """Compute a percentage value rounded to one decimal place.

    Args:
        num: Numerator.
        den: Denominator.

    Returns:
        Rounded percentage or None when denominator is zero.
    """
    return round(num / den * 100, 1) if den else None


def _build_confusion_payload(tp: int, fn: int, fp: int, tn: int) -> dict:
    """Build confusion matrix payload with derived metrics.

    Args:
        tp: True positives.
        fn: False negatives.
        fp: False positives.
        tn: True negatives.

    Returns:
        Payload containing matrix counts and metrics.
    """
    total = tp + fn + fp + tn
    f1_val = round(2 * tp / (2 * tp + fp + fn) * 100, 1) if (2 * tp + fp + fn) else None

    return {
        "total": total,
        "matrix": {
            "ai_ai": tp,
            "ai_human": fn,
            "human_ai": fp,
            "human_human": tn,
        },
        "metrics": {
            "accuracy": _pct(tp + tn, total),
            "precision_ai": _pct(tp, tp + fp),
            "recall_ai": _pct(tp, tp + fn),
            "recall_human": _pct(tn, tn + fp),
            "f1_ai": f1_val,
        },
    }


@router.get("/stats")
def get_stats() -> dict:
    with get_db() as conn:
        r = conn.execute("""
            SELECT
                (SELECT COUNT(*) FROM players)                                          AS total_players,
                (SELECT COUNT(*) FROM game_sessions)                                    AS total_sessions,
                (SELECT COUNT(*) FROM game_sessions WHERE finished_at IS NOT NULL)      AS finished_sessions,
                (SELECT ROUND(AVG(score::numeric / total_questions * 100), 1)
                   FROM game_sessions WHERE score IS NOT NULL)                          AS avg_pct,
                (SELECT COUNT(*) FROM session_questions WHERE answered_at IS NOT NULL)  AS total_answers,
                (SELECT COUNT(*) FROM session_questions WHERE is_correct = TRUE)        AS correct_answers
        """).fetchone()
    return {
        "total_players":     r[0],
        "total_sessions":    r[1],
        "finished_sessions": r[2],
        "avg_pct":           float(r[3]) if r[3] is not None else None,
        "total_answers":     r[4],
        "correct_answers":   r[5],
    }


@router.get("/players")
def get_players() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                p.id, p.email, p.first_name, p.last_name, p.created_at,
                COUNT(gs.id)  AS session_count,
                MAX(gs.score) AS best_score,
                (SELECT total_questions FROM game_sessions
                   WHERE player_id = p.id AND score IS NOT NULL
                   ORDER BY score DESC LIMIT 1) AS best_total
            FROM players p
            LEFT JOIN game_sessions gs ON gs.player_id = p.id AND gs.finished_at IS NOT NULL
            GROUP BY p.id
            ORDER BY p.created_at DESC
        """).fetchall()
    return [
        {
            "id":            r[0],
            "email":         r[1],
            "first_name":    r[2],
            "last_name":     r[3],
            "created_at":    r[4].isoformat(),
            "session_count": r[5],
            "best_score":    r[6],
            "best_total":    r[7],
        }
        for r in rows
    ]


@router.get("/sessions")
def get_sessions() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                gs.id,
                p.first_name || ' ' || p.last_name AS player_name,
                gs.started_at, gs.finished_at,
                gs.score, gs.total_questions
            FROM game_sessions gs
            JOIN players p ON p.id = gs.player_id
            ORDER BY gs.started_at DESC
        """).fetchall()
    return [
        {
            "id":              r[0],
            "player_name":     r[1],
            "started_at":      r[2].isoformat(),
            "finished_at":     r[3].isoformat() if r[3] else None,
            "score":           r[4],
            "total_questions": r[5],
        }
        for r in rows
    ]


@router.get("/confusion")
def get_confusion() -> dict:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                sq.session_id,
                CASE
                    WHEN split_part(sq.image_path, '/', 1) IN ('1', '2', '3', '4')
                        THEN split_part(sq.image_path, '/', 1)::int
                    ELSE sq.correct_category
                END AS effective_category,
                sq.user_answer
            FROM session_questions sq
            JOIN game_sessions gs ON gs.id = sq.session_id
            WHERE sq.answered_at IS NOT NULL
              AND sq.user_answer IN (1, 2)
              AND gs.finished_at IS NOT NULL
        """).fetchall()

    overall_counts: dict[tuple[int, int], int] = {
        (1, 1): 0,
        (1, 2): 0,
        (2, 1): 0,
        (2, 2): 0,
        (3, 1): 0,
        (3, 2): 0,
        (4, 1): 0,
        (4, 2): 0,
    }
    model_sessions: dict[int, set[int]] = {model_id: set() for model_id in _AI_MODELS}

    for session_id, effective_category, user_answer in rows:
        key = (effective_category, user_answer)
        if key in overall_counts:
            overall_counts[key] += 1
        if effective_category in model_sessions:
            model_sessions[effective_category].add(session_id)

    ai_tp = sum(overall_counts[(model_id, 1)] for model_id in _AI_MODELS)
    ai_fn = sum(overall_counts[(model_id, 2)] for model_id in _AI_MODELS)
    overall_payload = _build_confusion_payload(
        tp=ai_tp,
        fn=ai_fn,
        fp=overall_counts[(_HUMAN_CATEGORY, 1)],
        tn=overall_counts[(_HUMAN_CATEGORY, 2)],
    )

    per_model: list[dict] = []
    for model_id, model_name in _AI_MODELS.items():
        model_counts: dict[tuple[int, int], int] = {
            (model_id, 1): 0,
            (model_id, 2): 0,
            (_HUMAN_CATEGORY, 1): 0,
            (_HUMAN_CATEGORY, 2): 0,
        }
        relevant_sessions = model_sessions[model_id]

        for session_id, effective_category, user_answer in rows:
            if session_id not in relevant_sessions:
                continue
            key = (effective_category, user_answer)
            if key in model_counts:
                model_counts[key] += 1

        model_payload = _build_confusion_payload(
            tp=model_counts[(model_id, 1)],
            fn=model_counts[(model_id, 2)],
            fp=model_counts[(_HUMAN_CATEGORY, 1)],
            tn=model_counts[(_HUMAN_CATEGORY, 2)],
        )
        model_payload["model_id"] = model_id
        model_payload["model_name"] = model_name
        per_model.append(model_payload)

    return {
        "total": overall_payload["total"],
        "matrix": overall_payload["matrix"],
        "metrics": overall_payload["metrics"],
        "overall": overall_payload,
        "by_model": per_model,
    }


@router.get("/questions")
def get_questions() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                sq.id, sq.session_id,
                p.first_name || ' ' || p.last_name AS player_name,
                sq.question_order,
                sq.image_path,
                sq.submitted_image_path,
                CASE
                    WHEN split_part(sq.image_path, '/', 1) IN ('1', '2', '3', '4')
                        THEN split_part(sq.image_path, '/', 1)::int
                    ELSE sq.correct_category
                END AS effective_category,
                sq.user_answer,
                sq.is_correct,
                sq.answered_at
            FROM session_questions sq
            JOIN game_sessions gs ON gs.id = sq.session_id
            JOIN players p ON p.id = gs.player_id
            ORDER BY sq.session_id DESC, sq.question_order ASC
        """).fetchall()
    return [
        {
            "id":                   r[0],
            "session_id":           r[1],
            "player_name":          r[2],
            "question_order":       r[3],
            "image_path":           r[4],
            "submitted_image_path": r[5],
            "correct_category":     r[6],
            "user_answer":          r[7],
            "is_correct":           r[8],
            "answered_at":          r[9].isoformat() if r[9] else None,
        }
        for r in rows
    ]


class ClearRequest(BaseModel):
    password: str


@router.post(
    "/clear",
    responses={
        403: {"description": "Invalid password"},
    },
)
def clear_database(data: ClearRequest) -> dict:
    if not _ADMIN_PASSWORD or data.password != _ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Invalid password")
    with get_db() as conn:
        conn.execute(
            "TRUNCATE session_questions, game_sessions, players RESTART IDENTITY CASCADE"
        )
    return {"status": "cleared"}
