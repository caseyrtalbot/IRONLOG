"""
Analytics service — e1RM trends, overload recommendations, volume analytics,
volume landmarks, and phase-config lookups.

All functions receive a DB cursor and typed arguments; they never touch HTTP.
Delegates computation to server.algorithms where applicable.
"""

from server.algorithms.overload import recommend_overload
from server.algorithms.phase_config import generate_phase_config as _generate_phase_config
from server.models.analytics import VolumeLandmarksSave


# ---------------------------------------------------------------------------
# e1RM trend
# ---------------------------------------------------------------------------


def get_e1rm(db, athlete_id: int, exercise_id: int | None = None, days: int = 90) -> dict | list[dict]:
    """
    If exercise_id is given, return current e1RM + trend for that exercise.
    Otherwise return the latest e1RM for every exercise the athlete has logged.
    """
    if exercise_id is not None:
        trend = _calculate_e1rm_trend(db, athlete_id, exercise_id, days)
        current = db.execute(
            """
            SELECT estimated_1rm FROM one_rep_maxes
            WHERE athlete_id = ? AND exercise_id = ?
            ORDER BY date DESC LIMIT 1
            """,
            [athlete_id, exercise_id],
        ).fetchone()
        return {
            "current_e1rm": current["estimated_1rm"] if current else None,
            "trend": trend,
        }
    else:
        rows = db.execute(
            """
            SELECT orm.exercise_id, e.name, orm.estimated_1rm, orm.date
            FROM one_rep_maxes orm
            JOIN exercises e ON orm.exercise_id = e.id
            WHERE orm.athlete_id = ?
            AND orm.id = (
                SELECT id FROM one_rep_maxes
                WHERE athlete_id = orm.athlete_id AND exercise_id = orm.exercise_id
                ORDER BY date DESC LIMIT 1
            )
            ORDER BY e.name
            """,
            [athlete_id],
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Overload recommendation — delegates to algorithms.overload
# ---------------------------------------------------------------------------


def get_overload_rec(db, athlete_id: int, exercise_id: int) -> dict:
    """
    Query recent working sets from the DB, group by session, then delegate
    to algorithms.overload.recommend_overload for the pure recommendation.
    """
    recent = db.execute(
        """
        SELECT sl.weight, sl.reps, sl.rpe, sl.set_type, wl.date
        FROM set_logs sl
        JOIN workout_logs wl ON sl.workout_log_id = wl.id
        WHERE wl.athlete_id = ? AND sl.exercise_id = ? AND sl.set_type = 'working'
        ORDER BY wl.date DESC, sl.set_number DESC
        LIMIT 20
        """,
        [athlete_id, exercise_id],
    ).fetchall()

    if len(recent) < 2:
        return {"status": "insufficient_data", "message": "Need at least 2 logged sessions"}

    # Group by date
    sessions: dict[str, list[dict]] = {}
    for r in recent:
        d = r["date"]
        if d not in sessions:
            sessions[d] = []
        sessions[d].append(dict(r))

    dates = sorted(sessions.keys(), reverse=True)
    last_session = sessions[dates[0]]
    prev_session = sessions[dates[1]] if len(dates) > 1 else []

    # Fetch current stored e1RM
    e1rm_row = db.execute(
        """
        SELECT estimated_1rm FROM one_rep_maxes
        WHERE athlete_id = ? AND exercise_id = ?
        ORDER BY date DESC LIMIT 1
        """,
        [athlete_id, exercise_id],
    ).fetchone()
    current_e1rm = e1rm_row["estimated_1rm"] if e1rm_row else None

    return recommend_overload(last_session, prev_session, current_e1rm)


# ---------------------------------------------------------------------------
# General analytics — volume / frequency / muscle volume
# ---------------------------------------------------------------------------


def get_analytics(db, athlete_id: int, days: int = 30, metric: str = "volume") -> list[dict]:
    """Return time-series analytics for the given metric."""
    if metric == "volume":
        rows = db.execute(
            """
            SELECT wl.date, SUM(sl.weight * sl.reps) as volume,
                   COUNT(DISTINCT sl.exercise_id) as exercises_performed,
                   COUNT(sl.id) as total_sets
            FROM workout_logs wl
            JOIN set_logs sl ON sl.workout_log_id = wl.id
            WHERE wl.athlete_id = ? AND wl.date >= date('now', ?)
            AND sl.set_type = 'working'
            GROUP BY wl.date
            ORDER BY wl.date
            """,
            [athlete_id, f"-{days} days"],
        ).fetchall()
        return [dict(r) for r in rows]

    elif metric == "frequency":
        rows = db.execute(
            """
            SELECT e.movement_pattern, COUNT(DISTINCT wl.date) as session_count,
                   COUNT(sl.id) as total_sets
            FROM set_logs sl
            JOIN workout_logs wl ON sl.workout_log_id = wl.id
            JOIN exercises e ON sl.exercise_id = e.id
            WHERE wl.athlete_id = ? AND wl.date >= date('now', ?)
            AND sl.set_type = 'working'
            GROUP BY e.movement_pattern
            ORDER BY total_sets DESC
            """,
            [athlete_id, f"-{days} days"],
        ).fetchall()
        return [dict(r) for r in rows]

    elif metric == "muscle_volume":
        rows = db.execute(
            """
            SELECT e.primary_muscles, COUNT(sl.id) as total_sets,
                   SUM(sl.weight * sl.reps) as total_volume
            FROM set_logs sl
            JOIN workout_logs wl ON sl.workout_log_id = wl.id
            JOIN exercises e ON sl.exercise_id = e.id
            WHERE wl.athlete_id = ? AND wl.date >= date('now', ?)
            AND sl.set_type = 'working'
            GROUP BY e.primary_muscles
            ORDER BY total_sets DESC
            """,
            [athlete_id, f"-{days} days"],
        ).fetchall()
        return [dict(r) for r in rows]

    return []


# ---------------------------------------------------------------------------
# Volume landmarks
# ---------------------------------------------------------------------------

_VOLUME_DEFAULTS = [
    ("chest", 8, 12, 18, 22),
    ("back", 8, 12, 18, 22),
    ("quads", 6, 10, 16, 20),
    ("hamstrings", 6, 10, 14, 18),
    ("glutes", 4, 8, 14, 18),
    ("shoulders", 8, 12, 18, 22),
    ("biceps", 6, 10, 16, 20),
    ("triceps", 6, 8, 14, 18),
    ("calves", 8, 10, 16, 20),
    ("core", 4, 8, 12, 16),
]


def get_volume_landmarks(db, athlete_id: int) -> list[dict]:
    """Return stored volume landmarks or sensible defaults."""
    rows = db.execute(
        "SELECT * FROM volume_landmarks WHERE athlete_id = ? ORDER BY muscle_group",
        [athlete_id],
    ).fetchall()

    if not rows:
        return [
            {"muscle_group": d[0], "mev": d[1], "mav_low": d[2], "mav_high": d[3], "mrv": d[4]}
            for d in _VOLUME_DEFAULTS
        ]

    return [dict(r) for r in rows]


def save_volume_landmarks(db, body: VolumeLandmarksSave) -> dict:
    """Upsert volume landmarks for an athlete."""
    for lm in body.landmarks:
        db.execute(
            """
            INSERT OR REPLACE INTO volume_landmarks
            (athlete_id, muscle_group, mev, mav_low, mav_high, mrv, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            [body.athlete_id, lm.muscle_group, lm.mev, lm.mav_low, lm.mav_high, lm.mrv],
        )
    db.commit()
    return {"status": "saved", "count": len(body.landmarks)}


# ---------------------------------------------------------------------------
# Phase config (pure delegation)
# ---------------------------------------------------------------------------


def get_phase_config(goal: str, phase: str, experience: str) -> dict:
    """
    Delegate entirely to algorithms.phase_config.generate_phase_config.
    No DB needed — this is a pure lookup, but lives in the analytics service
    for API grouping consistency.
    """
    return _generate_phase_config(goal, phase, experience)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _calculate_e1rm_trend(db, athlete_id, exercise_id, days):
    """Get e1RM trend data points over time for an exercise."""
    rows = db.execute(
        """
        SELECT estimated_1rm, date FROM one_rep_maxes
        WHERE athlete_id = ? AND exercise_id = ?
        AND date >= date('now', ?)
        ORDER BY date ASC
        """,
        [athlete_id, exercise_id, f"-{days} days"],
    ).fetchall()
    return [{"e1rm": r["estimated_1rm"], "date": r["date"]} for r in rows]
