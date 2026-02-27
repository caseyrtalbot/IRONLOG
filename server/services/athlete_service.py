"""
Athlete service — profile CRUD.

All functions receive a DB cursor and typed arguments; they never touch HTTP.
"""

from server.models.athlete import AthleteCreate


def get_athlete(db, athlete_id: int) -> dict:
    """Return athlete profile or an empty stub."""
    row = db.execute("SELECT * FROM athletes WHERE id = ?", [athlete_id]).fetchone()
    if not row:
        return {"id": None}
    return dict(row)


def save_athlete(db, body: AthleteCreate) -> dict:
    """Insert or update an athlete profile. Returns status dict."""
    existing = db.execute(
        "SELECT id FROM athletes WHERE id = ?", [body.id]
    ).fetchone()

    if existing:
        db.execute(
            """
            UPDATE athletes SET name=?, age=?, body_weight=?, body_fat_pct=?,
            training_age=?, experience_level=?, primary_goal=?,
            training_days_per_week=?, session_duration_min=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            [
                body.name,
                body.age,
                body.body_weight,
                body.body_fat_pct,
                body.training_age,
                body.experience_level,
                body.primary_goal,
                body.training_days_per_week,
                body.session_duration_min,
                existing["id"],
            ],
        )
        db.commit()
        return {"id": existing["id"], "status": "updated"}
    else:
        cur = db.execute(
            """
            INSERT INTO athletes (name, age, body_weight, body_fat_pct, training_age,
            experience_level, primary_goal, training_days_per_week, session_duration_min)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                body.name,
                body.age,
                body.body_weight,
                body.body_fat_pct,
                body.training_age,
                body.experience_level,
                body.primary_goal,
                body.training_days_per_week,
                body.session_duration_min,
            ],
        )
        db.commit()
        return {"id": cur.lastrowid, "status": "created"}
