"""
Workout service — logging, retrieval, and deletion of workouts.

All functions receive a DB cursor and typed arguments; they never touch HTTP.
Delegates e1RM estimation to server.algorithms.e1rm.
"""

from datetime import datetime

from server.algorithms.e1rm import estimate_1rm
from server.models.workout import WorkoutSave


def save_workout(db, body: WorkoutSave) -> dict:
    """
    Save a complete workout log with all sets.

    Auto-calculates and stores e1RM for every working set that has weight + reps,
    delegating the math to algorithms.e1rm.estimate_1rm.
    """
    date = body.date or datetime.now().strftime("%Y-%m-%d")

    cur = db.execute(
        """
        INSERT INTO workout_logs (athlete_id, program_id, session_id, date,
        duration_min, notes, session_rpe, body_weight)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [body.athlete_id, body.program_id, body.session_id, date,
         body.duration_min, body.notes, body.session_rpe, body.body_weight],
    )
    workout_id = cur.lastrowid

    for s in body.sets:
        db.execute(
            """
            INSERT INTO set_logs (workout_log_id, exercise_id, set_number, set_type,
            weight, reps, rpe, rir, tempo, rest_seconds, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [workout_id, s.exercise_id, s.set_number, s.set_type,
             s.weight, s.reps, s.rpe, s.rir, s.tempo, s.rest_seconds, s.notes],
        )

        # Auto-calculate and store e1RM for working sets
        if s.weight and s.reps and s.set_type == "working":
            rpe = s.rpe if s.rpe is not None else 10
            e1rm = estimate_1rm(s.weight, s.reps, rpe)
            if e1rm > 0:
                db.execute(
                    """
                    INSERT INTO one_rep_maxes (athlete_id, exercise_id, estimated_1rm,
                    method, source_weight, source_reps, source_rpe, date)
                    VALUES (?, ?, ?, 'epley', ?, ?, ?, ?)
                    """,
                    [body.athlete_id, s.exercise_id, e1rm,
                     s.weight, s.reps, rpe, date],
                )

    db.commit()
    return {"id": workout_id, "status": "saved", "sets_logged": len(body.sets)}


def get_workouts(db, athlete_id: int, limit: int = 20, offset: int = 0) -> list[dict]:
    """Return workout summaries for an athlete with set aggregates."""
    rows = db.execute(
        """
        SELECT wl.*, COUNT(sl.id) as total_sets,
               SUM(CASE WHEN sl.set_type = 'working' THEN 1 ELSE 0 END) as working_sets,
               ROUND(SUM(sl.weight * sl.reps), 1) as total_volume
        FROM workout_logs wl
        LEFT JOIN set_logs sl ON sl.workout_log_id = wl.id
        WHERE wl.athlete_id = ?
        GROUP BY wl.id
        ORDER BY wl.date DESC, wl.created_at DESC
        LIMIT ? OFFSET ?
        """,
        [athlete_id, limit, offset],
    ).fetchall()
    return [dict(r) for r in rows]


def get_workout_detail(db, workout_id: int) -> dict | None:
    """Return full workout with sets grouped by exercise, or None."""
    workout = db.execute(
        "SELECT * FROM workout_logs WHERE id = ?", [workout_id]
    ).fetchone()
    if not workout:
        return None

    sets = db.execute(
        """
        SELECT sl.*, e.name as exercise_name, e.movement_pattern, e.category
        FROM set_logs sl
        JOIN exercises e ON sl.exercise_id = e.id
        WHERE sl.workout_log_id = ?
        ORDER BY sl.exercise_id, sl.set_number
        """,
        [workout_id],
    ).fetchall()

    result = dict(workout)
    result["sets"] = [dict(s) for s in sets]

    # Group sets by exercise for display
    grouped: dict = {}
    for s in result["sets"]:
        eid = s["exercise_id"]
        if eid not in grouped:
            grouped[eid] = {
                "exercise_id": eid,
                "exercise_name": s["exercise_name"],
                "movement_pattern": s["movement_pattern"],
                "category": s["category"],
                "sets": [],
            }
        grouped[eid]["sets"].append(s)
    result["exercises"] = list(grouped.values())

    return result


def delete_workout(db, workout_id: int) -> dict:
    """Delete a workout and its sets. Returns status dict."""
    db.execute("DELETE FROM set_logs WHERE workout_log_id = ?", [workout_id])
    db.execute("DELETE FROM workout_logs WHERE id = ?", [workout_id])
    db.commit()
    return {"status": "deleted"}
