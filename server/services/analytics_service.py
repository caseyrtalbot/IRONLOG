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
            SELECT em.muscle_group,
                   ROUND(SUM(em.contribution), 1) as effective_sets,
                   ROUND(SUM(sl.weight * sl.reps * em.contribution)) as weighted_volume
            FROM set_logs sl
            JOIN workout_logs wl ON sl.workout_log_id = wl.id
            JOIN exercise_muscles em ON sl.exercise_id = em.exercise_id
            WHERE wl.athlete_id = ? AND wl.date >= date('now', ?)
            AND sl.set_type = 'working'
            GROUP BY em.muscle_group
            ORDER BY effective_sets DESC
            """,
            [athlete_id, f"-{days} days"],
        ).fetchall()
        return [
            {
                "muscle_group": r["muscle_group"],
                "total_sets": r["effective_sets"],
                "total_volume": r["weighted_volume"],
            }
            for r in rows
        ]

    return []


# ---------------------------------------------------------------------------
# Volume landmarks
# ---------------------------------------------------------------------------

_VOLUME_DEFAULTS = [
    ("chest", 8, 12, 18, 22),
    ("front_delts", 6, 8, 14, 20),
    ("side_delts", 8, 14, 22, 28),
    ("rear_delts", 6, 10, 18, 24),
    ("lats", 8, 12, 18, 22),
    ("upper_back", 6, 10, 16, 22),
    ("quads", 6, 10, 16, 20),
    ("hamstrings", 4, 8, 14, 18),
    ("glutes", 4, 8, 14, 18),
    ("biceps", 6, 10, 16, 20),
    ("triceps", 4, 8, 14, 18),
    ("calves", 8, 10, 16, 20),
]


def get_volume_landmarks(db, athlete_id: int) -> list[dict]:
    """Return volume landmarks: stored values merged with defaults for missing groups."""
    stored = {
        r["muscle_group"]: dict(r)
        for r in db.execute(
            "SELECT * FROM volume_landmarks WHERE athlete_id = ?", [athlete_id]
        ).fetchall()
    }

    result = []
    default_groups = set()
    for d in _VOLUME_DEFAULTS:
        group = d[0]
        default_groups.add(group)
        if group in stored:
            result.append(stored[group])
        else:
            result.append({
                "muscle_group": group, "mev": d[1],
                "mav_low": d[2], "mav_high": d[3], "mrv": d[4],
            })

    # Include any user-added groups not in defaults (e.g. core, erectors opt-in)
    for group, data in stored.items():
        if group not in default_groups:
            result.append(data)

    return result


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
# Muscle status
# ---------------------------------------------------------------------------


def get_muscle_status(db, athlete_id: int, days: int = 7) -> list[dict]:
    """
    Compare actual weekly effective sets per muscle against volume landmarks.
    Returns each muscle with actual sets, MEV, MAV range, and MRV.
    """
    # Get actual volume from last N days
    actual_rows = db.execute("""
        SELECT em.muscle_group,
               ROUND(SUM(em.contribution), 1) as actual_sets
        FROM set_logs sl
        JOIN workout_logs wl ON sl.workout_log_id = wl.id
        JOIN exercise_muscles em ON sl.exercise_id = em.exercise_id
        WHERE wl.athlete_id = ? AND wl.date >= date('now', ?)
        AND sl.set_type = 'working'
        GROUP BY em.muscle_group
    """, [athlete_id, f"-{days} days"]).fetchall()
    actual = {r["muscle_group"]: r["actual_sets"] for r in actual_rows}

    # Get landmarks
    landmarks = get_volume_landmarks(db, athlete_id)

    result = []
    for lm in landmarks:
        muscle = lm["muscle_group"]
        actual_sets = actual.get(muscle, 0)
        mev = lm["mev"]
        mav_low = lm["mav_low"]
        mav_high = lm["mav_high"]
        mrv = lm["mrv"]

        if actual_sets < mev:
            zone = "below_mev"
        elif actual_sets < mav_low:
            zone = "below_mav"
        elif actual_sets <= mav_high:
            zone = "optimal"
        elif actual_sets <= mrv:
            zone = "above_mav"
        else:
            zone = "above_mrv"

        result.append({
            "muscle_group": muscle,
            "actual_sets": actual_sets,
            "mev": mev,
            "mav_low": mav_low,
            "mav_high": mav_high,
            "mrv": mrv,
            "zone": zone,
        })

    return result


# ---------------------------------------------------------------------------
# Session compliance
# ---------------------------------------------------------------------------


def get_session_compliance(db, athlete_id: int, program_id: int) -> dict:
    """
    Compare prescribed vs actual for each workout session in a program.
    Returns per-exercise and per-session compliance percentages.
    """
    program = db.execute(
        "SELECT * FROM programs WHERE id = ?", [program_id]
    ).fetchone()
    if not program:
        return {"error": "Program not found"}

    # Get all workout logs for this program
    workout_logs = db.execute("""
        SELECT wl.id, wl.session_id, wl.date
        FROM workout_logs wl
        WHERE wl.program_id = ? AND wl.athlete_id = ?
        ORDER BY wl.date
    """, [program_id, athlete_id]).fetchall()

    sessions_compliance = []

    for wl in workout_logs:
        if not wl["session_id"]:
            continue

        # Get prescribed exercises for this session
        prescribed = db.execute("""
            SELECT pe.exercise_id, pe.sets_prescribed, pe.reps_prescribed,
                   e.name as exercise_name,
                   wp.target_weight, wp.sets_prescribed as week_sets
            FROM program_exercises pe
            JOIN exercises e ON pe.exercise_id = e.id
            LEFT JOIN weekly_prescriptions wp
                ON wp.program_exercise_id = pe.id
                AND wp.week_number = ?
            WHERE pe.session_id = ?
        """, [program["current_week"], wl["session_id"]]).fetchall()

        # Get actual logged sets
        actual = db.execute("""
            SELECT exercise_id, COUNT(*) as sets_done,
                   AVG(weight) as avg_weight, AVG(reps) as avg_reps
            FROM set_logs
            WHERE workout_log_id = ? AND set_type = 'working'
            GROUP BY exercise_id
        """, [wl["id"]]).fetchall()
        actual_map = {r["exercise_id"]: dict(r) for r in actual}

        exercise_compliance = []
        for pe in prescribed:
            ex_id = pe["exercise_id"]
            actual_data = actual_map.get(ex_id, {})
            target_sets = pe["week_sets"] or pe["sets_prescribed"]
            done_sets = actual_data.get("sets_done", 0)

            sets_pct = min(1.0, done_sets / target_sets) if target_sets > 0 else 0

            weight_pct = None
            if pe["target_weight"] and actual_data.get("avg_weight"):
                weight_pct = round(actual_data["avg_weight"] / pe["target_weight"], 2)

            exercise_compliance.append({
                "exercise_name": pe["exercise_name"],
                "exercise_id": ex_id,
                "sets_prescribed": target_sets,
                "sets_completed": done_sets,
                "sets_compliance": round(sets_pct, 2),
                "target_weight": pe["target_weight"],
                "avg_weight_used": actual_data.get("avg_weight"),
                "weight_compliance": weight_pct,
            })

        overall = sum(e["sets_compliance"] for e in exercise_compliance) / max(1, len(exercise_compliance))

        sessions_compliance.append({
            "date": wl["date"],
            "session_id": wl["session_id"],
            "exercises": exercise_compliance,
            "overall_compliance": round(overall, 2),
        })

    return {
        "program_id": program_id,
        "program_name": program["name"],
        "sessions": sessions_compliance,
        "total_sessions_logged": len(sessions_compliance),
    }


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
