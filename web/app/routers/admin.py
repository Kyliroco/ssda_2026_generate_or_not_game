"""Admin endpoints for the /results dashboard."""

import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import get_db

_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "SSDA26")

router = APIRouter(prefix="/api/admin", tags=["admin"])


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
            SELECT correct_category, user_answer, COUNT(*) AS n
            FROM session_questions
            WHERE answered_at IS NOT NULL AND user_answer IS NOT NULL
              AND correct_category IN (1, 2) AND user_answer IN (1, 2)
            GROUP BY correct_category, user_answer
        """).fetchall()

    m: dict[tuple[int, int], int] = {(1, 1): 0, (1, 2): 0, (2, 1): 0, (2, 2): 0}
    for r in rows:
        m[(r[0], r[1])] = r[2]

    tp = m[(1, 1)]   # AI shown   → user said AI    (correct)
    fn = m[(1, 2)]   # AI shown   → user said Human (miss)
    fp = m[(2, 1)]   # Human shown → user said AI   (false alarm)
    tn = m[(2, 2)]   # Human shown → user said Human (correct)
    total = tp + fn + fp + tn

    def pct(num: int, den: int) -> float | None:
        return round(num / den * 100, 1) if den else None

    precision   = pct(tp, tp + fp)
    recall_ai   = pct(tp, tp + fn)
    recall_hum  = pct(tn, tn + fp)
    f1_val      = round(2 * tp / (2 * tp + fp + fn) * 100, 1) if (2 * tp + fp + fn) else None

    return {
        "total": total,
        "matrix": {"ai_ai": tp, "ai_human": fn, "human_ai": fp, "human_human": tn},
        "metrics": {
            "accuracy":       pct(tp + tn, total),
            "precision_ai":   precision,
            "recall_ai":      recall_ai,
            "recall_human":   recall_hum,
            "f1_ai":          f1_val,
        },
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
                sq.correct_category,
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


@router.post("/clear")
def clear_database(data: ClearRequest) -> dict:
    if data.password != _ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Invalid password")
    with get_db() as conn:
        conn.execute(
            "TRUNCATE session_questions, game_sessions, players RESTART IDENTITY CASCADE"
        )
    return {"status": "cleared"}
