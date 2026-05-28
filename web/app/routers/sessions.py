"""Game session management endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import get_db
from ..images import pick_questions

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _fmt_question(row: tuple) -> dict:
    # row: (id, session_id, question_order, image_path, correct_category, is_placeholder)
    return {
        "order": row[2],
        "image_path": row[3],
        "is_placeholder": bool(row[5]),
    }


class SessionStart(BaseModel):
    player_id: int


@router.post("")
def start_session(data: SessionStart) -> dict:
    questions = pick_questions()

    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM players WHERE id = %s", (data.player_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Player not found")

        session_id: int = conn.execute(
            "INSERT INTO game_sessions (player_id, total_questions) VALUES (%s, %s) RETURNING id",
            (data.player_id, len(questions)),
        ).fetchone()[0]

        for i, q in enumerate(questions, start=1):
            conn.execute(
                "INSERT INTO session_questions"
                " (session_id, question_order, image_path, correct_category, is_placeholder)"
                " VALUES (%s, %s, %s, %s, %s)",
                (session_id, i, q["path"], q["category"], q["is_placeholder"]),
            )

        first = conn.execute(
            "SELECT id, session_id, question_order, image_path, correct_category, is_placeholder"
            " FROM session_questions WHERE session_id = %s AND question_order = 1",
            (session_id,),
        ).fetchone()

    return {
        "session_id": session_id,
        "total_questions": len(questions),
        "question": _fmt_question(first),
    }


class AnswerSubmit(BaseModel):
    question_order: int
    answer: int        # 1 = synthetic/AI, 2 = human
    image_path: str    # path of the image displayed when the answer was submitted


@router.post("/{session_id}/answer")
def submit_answer(session_id: int, data: AnswerSubmit) -> dict:
    if data.answer not in (1, 2):
        raise HTTPException(status_code=400, detail="Answer must be 1 (AI) or 2 (human)")

    with get_db() as conn:
        session = conn.execute(
            "SELECT id, finished_at, total_questions FROM game_sessions WHERE id = %s",
            (session_id,),
        ).fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session[1] is not None:
            raise HTTPException(status_code=400, detail="Session already finished")

        question = conn.execute(
            "SELECT id, correct_category, answered_at"
            " FROM session_questions WHERE session_id = %s AND question_order = %s",
            (session_id, data.question_order),
        ).fetchone()
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        if question[2] is not None:
            raise HTTPException(status_code=400, detail="Question already answered")

        is_correct = data.answer == question[1]

        conn.execute(
            "UPDATE session_questions"
            " SET user_answer = %s, is_correct = %s, answered_at = NOW(),"
            "     submitted_image_path = %s"
            " WHERE id = %s",
            (data.answer, is_correct, data.image_path, question[0]),
        )

        answered_count: int = conn.execute(
            "SELECT COUNT(*) FROM session_questions WHERE session_id = %s AND answered_at IS NOT NULL",
            (session_id,),
        ).fetchone()[0]

        total: int = session[2]

        if answered_count >= total:
            score: int = conn.execute(
                "SELECT COUNT(*) FROM session_questions WHERE session_id = %s AND is_correct = TRUE",
                (session_id,),
            ).fetchone()[0]

            conn.execute(
                "UPDATE game_sessions SET finished_at = NOW(), score = %s WHERE id = %s",
                (score, session_id),
            )

            return {
                "is_correct": is_correct,
                "correct_answer": question[1],
                "finished": True,
                "score": score,
                "total_questions": total,
                "next_question": None,
            }

        next_q = conn.execute(
            "SELECT id, session_id, question_order, image_path, correct_category, is_placeholder"
            " FROM session_questions WHERE session_id = %s AND question_order = %s",
            (session_id, data.question_order + 1),
        ).fetchone()

    return {
        "is_correct": is_correct,
        "correct_answer": question[1],
        "finished": False,
        "score": None,
        "total_questions": total,
        "next_question": _fmt_question(next_q) if next_q else None,
    }
