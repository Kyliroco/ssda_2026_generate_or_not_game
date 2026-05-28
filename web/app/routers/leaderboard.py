"""Leaderboard endpoint — best score per player."""

from fastapi import APIRouter

from ..database import get_db

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])

_QUERY = """
WITH best AS (
    SELECT DISTINCT ON (player_id)
        player_id, score, total_questions, finished_at
    FROM game_sessions
    WHERE finished_at IS NOT NULL AND score IS NOT NULL
    ORDER BY player_id, score DESC, finished_at DESC
)
SELECT
    p.id, p.first_name, p.last_name,
    b.score, b.total_questions, b.finished_at
FROM best b
JOIN players p ON p.id = b.player_id
ORDER BY b.score DESC, b.finished_at ASC
LIMIT %s
"""


@router.get("")
def get_leaderboard(limit: int = 10) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(_QUERY, (min(limit, 100),)).fetchall()

    return [
        {
            "rank": i + 1,
            "player_id": row[0],
            "name": f"{row[1]} {row[2]}",
            "best_score": row[3],
            "total_questions": row[4],
            "last_played": row[5].isoformat() if row[5] else None,
        }
        for i, row in enumerate(rows)
    ]
