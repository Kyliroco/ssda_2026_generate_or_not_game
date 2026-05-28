"""Player registration endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel

from ..database import get_db

router = APIRouter(prefix="/api/players", tags=["players"])


class PlayerCreate(BaseModel):
    email: str
    first_name: str
    last_name: str


@router.post("")
def create_or_get_player(data: PlayerCreate) -> dict:
    email = data.email.lower().strip()
    first_name = data.first_name.strip()
    last_name = data.last_name.strip()

    with get_db() as conn:
        row = conn.execute(
            "SELECT id, email, first_name, last_name, created_at FROM players WHERE email = %s",
            (email,),
        ).fetchone()

        if not row:
            row = conn.execute(
                "INSERT INTO players (email, first_name, last_name) VALUES (%s, %s, %s)"
                " RETURNING id, email, first_name, last_name, created_at",
                (email, first_name, last_name),
            ).fetchone()

    return {
        "id": row[0],
        "email": row[1],
        "first_name": row[2],
        "last_name": row[3],
        "created_at": row[4].isoformat(),
    }
