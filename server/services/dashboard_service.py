"""
Dashboard service — aggregated athlete dashboard data.

All functions receive a DB cursor and typed arguments; they never touch HTTP.
Delegates streak calculation to server.algorithms.streak.
"""

from datetime import datetime

from server.algorithms.streak import calculate_streak


def get_dashboard(db, athlete_id: int) -> dict:
    """
    Build the full dashboard payload: recent workouts, streak, totals, PRs,
    and active program.
    """
    # Recent workouts (last 7)
    recent = db.execute(
        """
        SELECT wl.id, wl.date, wl.duration_min, wl.session_rpe,
               COUNT(sl.id) as total_sets,
               ROUND(SUM(sl.weight * sl.reps), 0) as volume_load
        FROM workout_logs wl
        LEFT JOIN set_logs sl ON sl.workout_log_id = wl.id AND sl.set_type = 'working'
        WHERE wl.athlete_id = ?
        GROUP BY wl.id
        ORDER BY wl.date DESC
        LIMIT 7
        """,
        [athlete_id],
    ).fetchall()

    # Streak — query dates then delegate to pure algorithm
    dates_rows = db.execute(
        """
        SELECT DISTINCT date FROM workout_logs
        WHERE athlete_id = ? ORDER BY date DESC LIMIT 60
        """,
        [athlete_id],
    ).fetchall()
    workout_dates = [r["date"] for r in dates_rows]
    streak = calculate_streak(workout_dates, datetime.now().date())

    # Total stats
    totals = db.execute(
        """
        SELECT COUNT(DISTINCT wl.id) as total_workouts,
               COUNT(sl.id) as total_sets,
               ROUND(SUM(sl.weight * sl.reps), 0) as total_volume
        FROM workout_logs wl
        LEFT JOIN set_logs sl ON sl.workout_log_id = wl.id AND sl.set_type = 'working'
        WHERE wl.athlete_id = ?
        """,
        [athlete_id],
    ).fetchone()

    # PRs (top e1RM per exercise, last 30 days)
    prs = db.execute(
        """
        SELECT e.name, MAX(orm.estimated_1rm) as best_e1rm, orm.date
        FROM one_rep_maxes orm
        JOIN exercises e ON orm.exercise_id = e.id
        WHERE orm.athlete_id = ? AND orm.date >= date('now', '-30 days')
        GROUP BY orm.exercise_id
        ORDER BY orm.estimated_1rm DESC
        LIMIT 5
        """,
        [athlete_id],
    ).fetchall()

    # Active program
    program = db.execute(
        """
        SELECT * FROM programs WHERE athlete_id = ? AND status = 'active'
        ORDER BY created_at DESC LIMIT 1
        """,
        [athlete_id],
    ).fetchone()

    return {
        "recent_workouts": [dict(r) for r in recent],
        "streak": streak,
        "totals": dict(totals) if totals else {},
        "recent_prs": [dict(r) for r in prs],
        "active_program": dict(program) if program else None,
    }
