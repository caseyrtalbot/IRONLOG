"""
Program service — program generation and retrieval.

All functions receive a DB cursor and typed arguments; they never touch HTTP.
Delegates phase-config computation to server.algorithms.phase_config.
"""

import json
import logging

from server.algorithms.phase_config import generate_phase_config
from server.algorithms.progression import calculate_weekly_progression, prescribe_weight
from server.algorithms.volume_budget import calculate_projected_volume, audit_volume
from server.models.program import ProgramGenerate
from server.services.analytics_service import get_volume_landmarks

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_programs(db, athlete_id: int) -> list[dict]:
    """Return all programs for an athlete, newest first."""
    rows = db.execute(
        "SELECT * FROM programs WHERE athlete_id = ? ORDER BY created_at DESC",
        [athlete_id],
    ).fetchall()
    return [dict(r) for r in rows]


def get_program_detail(db, program_id: int) -> dict | None:
    """Return full program with sessions and exercises, or None."""
    program = db.execute(
        "SELECT * FROM programs WHERE id = ?", [program_id]
    ).fetchone()
    if not program:
        return None

    sessions = db.execute(
        """
        SELECT * FROM program_sessions WHERE program_id = ?
        ORDER BY day_number, session_order
        """,
        [program_id],
    ).fetchall()

    result = dict(program)
    result["sessions"] = []
    for sess in sessions:
        s = dict(sess)
        exercises = db.execute(
            """
            SELECT pe.*, e.name as exercise_name, e.movement_pattern, e.category,
                   e.primary_muscles, e.equipment
            FROM program_exercises pe
            JOIN exercises e ON pe.exercise_id = e.id
            WHERE pe.session_id = ?
            ORDER BY pe.exercise_order
            """,
            [sess["id"]],
        ).fetchall()
        ex_list = []
        for ex in exercises:
            ex_dict = dict(ex)
            # Attach weekly prescriptions
            weeks = db.execute("""
                SELECT week_number, sets_prescribed, reps_prescribed,
                       intensity_pct, target_weight, target_rpe
                FROM weekly_prescriptions
                WHERE program_exercise_id = ?
                ORDER BY week_number
            """, [ex["id"]]).fetchall()
            ex_dict["weekly"] = [dict(w) for w in weeks]
            ex_list.append(ex_dict)

        s["exercises"] = ex_list
        result["sessions"].append(s)

    # Include volume audit summary
    try:
        result["volume_summary"] = _calculate_program_volume(db, program_id)
    except Exception:
        logger.exception("Failed to calculate volume summary for program %s", program_id)
        result["volume_summary"] = None

    return result


def delete_program(db, program_id: int) -> dict | None:
    """Delete a program and all cascading child records. Returns status or None."""
    program = db.execute("SELECT id, name FROM programs WHERE id = ?", [program_id]).fetchone()
    if not program:
        return None
    # Cascade handles sessions, exercises, prescriptions
    db.execute("DELETE FROM programs WHERE id = ?", [program_id])
    db.commit()
    return {"status": "deleted", "name": program["name"]}


def generate_program(db, body: ProgramGenerate) -> dict:
    """
    Generate a periodized program.

    Delegates phase-config creation to algorithms.phase_config.generate_phase_config.
    Returns status dict with new program id and name.
    """
    program_name = body.name or f"{body.goal.title()} - {body.phase.title()} Block"

    athlete = db.execute(
        "SELECT * FROM athletes WHERE id = ?", [body.athlete_id]
    ).fetchone()
    experience = athlete["experience_level"] if athlete else "intermediate"

    config = generate_phase_config(body.goal, body.phase, experience, body.weeks)

    cur = db.execute(
        """
        INSERT INTO programs (athlete_id, name, phase, goal, mesocycle_weeks, config)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [body.athlete_id, program_name, body.phase, body.goal, body.weeks, json.dumps(config)],
    )
    program_id = cur.lastrowid

    if body.split == "upper_lower":
        _generate_upper_lower(db, program_id, config, body.goal, body.days_per_week)
    elif body.split == "push_pull_legs":
        _generate_ppl(db, program_id, config, body.goal, body.days_per_week)
    elif body.split == "full_body":
        _generate_full_body(db, program_id, config, body.goal, body.days_per_week)

    db.commit()

    # Generate weekly prescriptions
    e1rms = _get_athlete_e1rms(db, body.athlete_id)
    _generate_weekly_prescriptions(db, program_id, config, body.weeks, e1rms)
    db.commit()

    # Volume-constrained adjustment
    try:
        volume_summary = _adjust_for_volume(db, program_id, body.athlete_id, config)
        # Re-generate weekly prescriptions for any newly added exercises
        _generate_weekly_prescriptions(db, program_id, config, body.weeks, e1rms)
        db.commit()
    except Exception:
        logger.exception("Volume adjustment failed for program %s", program_id)
        volume_summary = _calculate_program_volume(db, program_id)

    return {"id": program_id, "name": program_name, "status": "generated",
            "volume_summary": volume_summary}


def get_current_week_prescriptions(db, program_id, session_id):
    """
    Get prescriptions for the current week of a program session.
    Returns exercises with per-week targets (sets, reps, weight, RPE).
    """
    program = db.execute(
        "SELECT current_week FROM programs WHERE id = ?", [program_id]
    ).fetchone()
    if not program:
        return []

    week = program["current_week"]

    rows = db.execute("""
        SELECT pe.*, e.name as exercise_name, e.movement_pattern, e.category,
               e.equipment,
               wp.sets_prescribed as week_sets,
               wp.reps_prescribed as week_reps,
               wp.intensity_pct, wp.target_weight, wp.target_rpe
        FROM program_exercises pe
        JOIN exercises e ON pe.exercise_id = e.id
        LEFT JOIN weekly_prescriptions wp
            ON wp.program_exercise_id = pe.id AND wp.week_number = ?
        WHERE pe.session_id = ?
        ORDER BY pe.exercise_order
    """, [week, session_id]).fetchall()

    return [dict(r) for r in rows]


def get_program_retrospective(db, program_id: int) -> dict | None:
    """
    Generate end-of-program summary: volume per muscle, e1RM changes,
    compliance rate, RPE trend, body weight change.
    """
    program = db.execute(
        "SELECT * FROM programs WHERE id = ?", [program_id]
    ).fetchone()
    if not program:
        return None

    athlete_id = program["athlete_id"]

    # Date range of this program's workouts
    date_range = db.execute("""
        SELECT MIN(date) as start_date, MAX(date) as end_date, COUNT(*) as total_sessions
        FROM workout_logs WHERE program_id = ?
    """, [program_id]).fetchone()

    if not date_range or not date_range["start_date"]:
        return {"program": dict(program), "status": "no_data"}

    # 1. Volume per muscle accumulated during this program
    volume_per_muscle = db.execute("""
        SELECT em.muscle_group,
               ROUND(SUM(em.contribution), 1) as total_effective_sets,
               ROUND(SUM(sl.weight * sl.reps * em.contribution)) as total_volume_load
        FROM set_logs sl
        JOIN workout_logs wl ON sl.workout_log_id = wl.id
        JOIN exercise_muscles em ON sl.exercise_id = em.exercise_id
        WHERE wl.program_id = ? AND sl.set_type = 'working'
        GROUP BY em.muscle_group
        ORDER BY total_effective_sets DESC
    """, [program_id]).fetchall()

    # 2. e1RM changes: compare first vs last for each exercise in the program
    e1rm_changes = db.execute("""
        SELECT e.name,
               first_orm.estimated_1rm as starting_e1rm,
               last_orm.estimated_1rm as ending_e1rm,
               ROUND(last_orm.estimated_1rm - first_orm.estimated_1rm, 1) as change
        FROM (
            SELECT DISTINCT sl.exercise_id
            FROM set_logs sl
            JOIN workout_logs wl ON sl.workout_log_id = wl.id
            WHERE wl.program_id = ? AND sl.set_type = 'working'
        ) used_exercises
        JOIN exercises e ON e.id = used_exercises.exercise_id
        LEFT JOIN one_rep_maxes first_orm ON first_orm.exercise_id = e.id
            AND first_orm.athlete_id = ?
            AND first_orm.date = (
                SELECT MIN(date) FROM one_rep_maxes
                WHERE exercise_id = e.id AND athlete_id = ? AND date >= ?
            )
        LEFT JOIN one_rep_maxes last_orm ON last_orm.exercise_id = e.id
            AND last_orm.athlete_id = ?
            AND last_orm.date = (
                SELECT MAX(date) FROM one_rep_maxes
                WHERE exercise_id = e.id AND athlete_id = ? AND date <= ?
            )
        WHERE first_orm.estimated_1rm IS NOT NULL AND last_orm.estimated_1rm IS NOT NULL
        ORDER BY change DESC
    """, [
        program_id, athlete_id, athlete_id, date_range["start_date"],
        athlete_id, athlete_id, date_range["end_date"],
    ]).fetchall()

    # 3. RPE trend across sessions
    rpe_trend = db.execute("""
        SELECT date, session_rpe
        FROM workout_logs
        WHERE program_id = ? AND session_rpe IS NOT NULL
        ORDER BY date
    """, [program_id]).fetchall()

    # 4. Body weight change
    bw_start = db.execute("""
        SELECT body_weight FROM workout_logs
        WHERE program_id = ? AND body_weight IS NOT NULL
        ORDER BY date ASC LIMIT 1
    """, [program_id]).fetchone()
    bw_end = db.execute("""
        SELECT body_weight FROM workout_logs
        WHERE program_id = ? AND body_weight IS NOT NULL
        ORDER BY date DESC LIMIT 1
    """, [program_id]).fetchone()

    return {
        "program": dict(program),
        "date_range": {
            "start": date_range["start_date"],
            "end": date_range["end_date"],
            "total_sessions": date_range["total_sessions"],
        },
        "volume_per_muscle": [dict(r) for r in volume_per_muscle],
        "e1rm_changes": [dict(r) for r in e1rm_changes],
        "rpe_trend": [{"date": r["date"], "rpe": r["session_rpe"]} for r in rpe_trend],
        "body_weight": {
            "start": bw_start["body_weight"] if bw_start else None,
            "end": bw_end["body_weight"] if bw_end else None,
            "change": round(bw_end["body_weight"] - bw_start["body_weight"], 1)
                if bw_start and bw_end and bw_start["body_weight"] and bw_end["body_weight"]
                else None,
        },
    }


# ---------------------------------------------------------------------------
# Private helpers — session generation
# ---------------------------------------------------------------------------


def _generate_upper_lower(db, program_id, config, goal, days):
    """Generate upper/lower split program."""
    if days >= 4:
        sessions = [
            (1, "Upper A - Strength Focus", "upper_strength"),
            (2, "Lower A - Strength Focus", "lower_strength"),
            (3, "Upper B - Volume Focus", "upper_volume"),
            (4, "Lower B - Volume Focus", "lower_volume"),
        ]
    elif days == 3:
        sessions = [
            (1, "Upper A", "upper_strength"),
            (2, "Lower A", "lower_strength"),
            (3, "Full Body B", "full_body"),
        ]
    else:
        sessions = [
            (1, "Upper", "upper_strength"),
            (2, "Lower", "lower_strength"),
        ]

    for day_num, name, focus in sessions:
        cur = db.execute(
            """
            INSERT INTO program_sessions (program_id, day_number, name, focus)
            VALUES (?, ?, ?, ?)
            """,
            [program_id, day_num, name, focus],
        )
        session_id = cur.lastrowid
        _populate_session(db, session_id, focus, config, goal)


def _generate_ppl(db, program_id, config, goal, days):
    """Generate push/pull/legs split."""
    sessions = [
        (1, "Push", "push"),
        (2, "Pull", "pull"),
        (3, "Legs", "legs"),
    ]
    if days >= 6:
        sessions.extend([
            (4, "Push B", "push_volume"),
            (5, "Pull B", "pull_volume"),
            (6, "Legs B", "legs_volume"),
        ])

    for day_num, name, focus in sessions:
        cur = db.execute(
            """
            INSERT INTO program_sessions (program_id, day_number, name, focus)
            VALUES (?, ?, ?, ?)
            """,
            [program_id, day_num, name, focus],
        )
        session_id = cur.lastrowid
        _populate_session(db, session_id, focus, config, goal)


def _generate_full_body(db, program_id, config, goal, days):
    """Generate full body split."""
    for d in range(1, min(days + 1, 5)):
        focus = "full_body" if d % 2 == 1 else "full_body_b"
        cur = db.execute(
            """
            INSERT INTO program_sessions (program_id, day_number, name, focus)
            VALUES (?, ?, ?, ?)
            """,
            [program_id, d, f"Full Body Day {d}", focus],
        )
        session_id = cur.lastrowid
        _populate_session(db, session_id, focus, config, goal)


def _populate_session(db, session_id, focus, config, goal):
    """Populate a session with exercises from the taxonomy based on focus."""
    c_sets = config["compound_sets"]
    c_reps = config["compound_reps"]
    c_rpe = config["compound_rpe"]
    i_sets = config["isolation_sets"]
    i_reps = config["isolation_reps"]
    i_rpe = config["isolation_rpe"]

    order = 1

    if focus in ("upper_strength", "push"):
        # Main compound push
        _add_exercise_by_pattern(
            db, session_id, "horizontal_push", "compound", "barbell",
            c_sets[1], f"{c_reps[0]}-{c_reps[1]}", "rpe", str(c_rpe[1]),
            config["rest_compound"], order, "A"); order += 1
        # Secondary push
        _add_exercise_by_pattern(
            db, session_id, "vertical_push", "compound", None,
            c_sets[0], f"{c_reps[0]}-{c_reps[1]}", "rpe", str(c_rpe[0]),
            config["rest_compound"], order, "B"); order += 1
        # Horizontal pull (superset)
        _add_exercise_by_pattern(
            db, session_id, "horizontal_pull", "compound", None,
            c_sets[0], f"{c_reps[0]+1}-{c_reps[1]+2}", "rpe", str(c_rpe[0]),
            config["rest_compound"], order, "B"); order += 1
        # Triceps isolation
        _add_exercise_by_pattern(
            db, session_id, "elbow_extension", "isolation", None,
            i_sets[1], f"{i_reps[0]}-{i_reps[1]}", "rir", "2",
            config["rest_isolation"], order, "C"); order += 1
        # Lateral raise (superset)
        _add_exercise_by_pattern(
            db, session_id, "lateral_raise", "isolation", None,
            i_sets[1], f"{i_reps[0]}-{i_reps[1]}", "rir", "1",
            config["rest_isolation"], order, "C"); order += 1

    elif focus in ("lower_strength", "legs"):
        # Main squat
        _add_exercise_by_pattern(
            db, session_id, "squat", "compound", "barbell",
            c_sets[1], f"{c_reps[0]}-{c_reps[1]}", "rpe", str(c_rpe[1]),
            config["rest_compound"], order, "A"); order += 1
        # Hip hinge
        _add_exercise_by_pattern(
            db, session_id, "hip_hinge", "compound", "barbell",
            c_sets[0], f"{c_reps[0]}-{c_reps[1]}", "rpe", str(c_rpe[0]),
            config["rest_compound"], order, "B"); order += 1
        # Unilateral
        _add_exercise_by_pattern(
            db, session_id, "lunge", "compound", None,
            c_sets[0], f"{c_reps[0]+1}-{c_reps[1]+2}", "rpe", str(c_rpe[0]),
            config["rest_compound"], order, "C"); order += 1
        # Leg curl
        _add_exercise_by_pattern(
            db, session_id, "knee_flexion", "isolation", None,
            i_sets[1], f"{i_reps[0]}-{i_reps[1]}", "rir", "2",
            config["rest_isolation"], order, "D"); order += 1
        # Calf raise
        _add_exercise_by_pattern(
            db, session_id, "ankle_plantar_flexion", "isolation", None,
            i_sets[0], f"{i_reps[0]}-{i_reps[1]+3}", "rir", "1",
            config["rest_isolation"], order, "D"); order += 1

    elif focus in ("upper_volume", "push_volume"):
        # Incline press
        _add_exercise_by_pattern(
            db, session_id, "horizontal_push", "compound", "dumbbell",
            c_sets[0], f"{c_reps[0]+2}-{c_reps[1]+2}", "rpe", str(c_rpe[0]),
            config["rest_compound"], order, "A"); order += 1
        # Vertical pull
        _add_exercise_by_pattern(
            db, session_id, "vertical_pull", "compound", None,
            c_sets[0], f"{c_reps[0]}-{c_reps[1]}", "rpe", str(c_rpe[0]),
            config["rest_compound"], order, "B"); order += 1
        # Cable fly (superset)
        _add_exercise_by_pattern(
            db, session_id, "horizontal_push", "isolation", "cable",
            i_sets[1], f"{i_reps[0]}-{i_reps[1]}", "rir", "1",
            config["rest_isolation"], order, "C"); order += 1
        # Biceps
        _add_exercise_by_pattern(
            db, session_id, "elbow_flexion", "isolation", None,
            i_sets[1], f"{i_reps[0]}-{i_reps[1]}", "rir", "2",
            config["rest_isolation"], order, "C"); order += 1
        # Rear delt
        _add_exercise_by_pattern(
            db, session_id, "horizontal_pull", "isolation", None,
            i_sets[0], f"{i_reps[0]}-{i_reps[1]}", "rir", "1",
            config["rest_isolation"], order, "D"); order += 1

    elif focus in ("lower_volume", "legs_volume"):
        # Front squat or hack squat
        _add_exercise_by_pattern(
            db, session_id, "squat", "compound", "machine",
            c_sets[0], f"{c_reps[0]+2}-{c_reps[1]+2}", "rpe", str(c_rpe[0]),
            config["rest_compound"], order, "A"); order += 1
        # RDL
        _add_exercise_by_pattern(
            db, session_id, "hip_hinge", "compound", "dumbbell",
            c_sets[0], f"{c_reps[0]+1}-{c_reps[1]+2}", "rpe", str(c_rpe[0]),
            config["rest_compound"], order, "B"); order += 1
        # Hip extension
        _add_exercise_by_pattern(
            db, session_id, "hip_extension", "compound", None,
            c_sets[0], f"{c_reps[0]+2}-{c_reps[1]+2}", "rpe", str(c_rpe[0]),
            config["rest_compound"], order, "C"); order += 1
        # Leg extension
        _add_exercise_by_pattern(
            db, session_id, "knee_extension", "isolation", None,
            i_sets[1], f"{i_reps[0]}-{i_reps[1]}", "rir", "2",
            config["rest_isolation"], order, "D"); order += 1
        # Calf
        _add_exercise_by_pattern(
            db, session_id, "ankle_plantar_flexion", "isolation", None,
            i_sets[0], f"{i_reps[0]}-{i_reps[1]+3}", "rir", "1",
            config["rest_isolation"], order, "D"); order += 1

    elif focus in ("pull", "pull_volume"):
        # Heavy row
        _add_exercise_by_pattern(
            db, session_id, "horizontal_pull", "compound", "barbell",
            c_sets[1], f"{c_reps[0]}-{c_reps[1]}", "rpe", str(c_rpe[1]),
            config["rest_compound"], order, "A"); order += 1
        # Vertical pull
        _add_exercise_by_pattern(
            db, session_id, "vertical_pull", "compound", None,
            c_sets[0], f"{c_reps[0]}-{c_reps[1]}", "rpe", str(c_rpe[0]),
            config["rest_compound"], order, "B"); order += 1
        # Cable row
        _add_exercise_by_pattern(
            db, session_id, "horizontal_pull", "compound", "cable",
            c_sets[0], f"{c_reps[0]+2}-{c_reps[1]+2}", "rpe", str(c_rpe[0]),
            config["rest_compound"], order, "C"); order += 1
        # Biceps
        _add_exercise_by_pattern(
            db, session_id, "elbow_flexion", "isolation", None,
            i_sets[1], f"{i_reps[0]}-{i_reps[1]}", "rir", "2",
            config["rest_isolation"], order, "D"); order += 1
        # Rear delt
        _add_exercise_by_pattern(
            db, session_id, "horizontal_pull", "isolation", None,
            i_sets[0], f"{i_reps[0]}-{i_reps[1]}", "rir", "1",
            config["rest_isolation"], order, "D"); order += 1

    elif focus in ("full_body", "full_body_b"):
        # Squat
        _add_exercise_by_pattern(
            db, session_id, "squat", "compound", "barbell",
            c_sets[0], f"{c_reps[0]}-{c_reps[1]}", "rpe", str(c_rpe[1]),
            config["rest_compound"], order, "A"); order += 1
        # Press
        _add_exercise_by_pattern(
            db, session_id, "horizontal_push", "compound", None,
            c_sets[0], f"{c_reps[0]}-{c_reps[1]}", "rpe", str(c_rpe[0]),
            config["rest_compound"], order, "B"); order += 1
        # Pull
        _add_exercise_by_pattern(
            db, session_id, "vertical_pull", "compound", None,
            c_sets[0], f"{c_reps[0]}-{c_reps[1]}", "rpe", str(c_rpe[0]),
            config["rest_compound"], order, "B"); order += 1
        # Hinge
        _add_exercise_by_pattern(
            db, session_id, "hip_hinge", "compound", None,
            c_sets[0], f"{c_reps[0]}-{c_reps[1]}", "rpe", str(c_rpe[0]),
            config["rest_compound"], order, "C"); order += 1


def _add_exercise_by_pattern(
    db, session_id, pattern, category, equipment,
    sets, reps, intensity_type, intensity_value, rest, order, superset_group,
):
    """Find a matching exercise and add it to the session."""
    query = "SELECT id FROM exercises WHERE movement_pattern = ? AND category = ?"
    args: list = [pattern, category]
    if equipment:
        query += " AND equipment = ?"
        args.append(equipment)
    query += " ORDER BY RANDOM() LIMIT 1"

    row = db.execute(query, args).fetchone()
    if not row:
        # Fallback without equipment filter
        row = db.execute(
            "SELECT id FROM exercises WHERE movement_pattern = ? ORDER BY RANDOM() LIMIT 1",
            [pattern],
        ).fetchone()

    if row:
        db.execute(
            """
            INSERT INTO program_exercises (session_id, exercise_id, exercise_order,
            superset_group, sets_prescribed, reps_prescribed, intensity_type,
            intensity_value, rest_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [session_id, row["id"], order, superset_group, sets, reps,
             intensity_type, intensity_value, rest],
        )


def _calculate_program_volume(db, program_id):
    """Calculate projected weekly volume for a generated program."""
    exercises = db.execute("""
        SELECT pe.sets_prescribed, pe.exercise_id
        FROM program_exercises pe
        JOIN program_sessions ps ON pe.session_id = ps.id
        WHERE ps.program_id = ?
    """, [program_id]).fetchall()

    program_exercises = []
    for ex in exercises:
        muscles = db.execute("""
            SELECT muscle_group, contribution FROM exercise_muscles
            WHERE exercise_id = ?
        """, [ex["exercise_id"]]).fetchall()
        program_exercises.append({
            "sets_prescribed": ex["sets_prescribed"],
            "muscles": [dict(m) for m in muscles],
        })

    projected = calculate_projected_volume(program_exercises)

    # Get athlete landmarks (use defaults if not set)
    athlete_id = db.execute(
        "SELECT athlete_id FROM programs WHERE id = ?", [program_id]
    ).fetchone()["athlete_id"]

    landmarks_list = get_volume_landmarks(db, athlete_id)
    landmarks = {l["muscle_group"]: l for l in landmarks_list}

    audit = audit_volume(projected, landmarks)

    return {
        "projected": {k: round(v, 1) for k, v in sorted(projected.items())},
        "audit": audit,
    }


def _get_athlete_e1rms(db, athlete_id):
    """Return dict mapping exercise_id -> latest e1RM."""
    rows = db.execute("""
        SELECT exercise_id, estimated_1rm
        FROM one_rep_maxes
        WHERE athlete_id = ?
        AND id IN (
            SELECT MAX(id) FROM one_rep_maxes
            WHERE athlete_id = ?
            GROUP BY exercise_id
        )
    """, [athlete_id, athlete_id]).fetchall()
    return {r["exercise_id"]: r["estimated_1rm"] for r in rows}


def _generate_weekly_prescriptions(db, program_id, config, weeks, e1rms):
    """Generate per-week prescriptions for every exercise in the program."""
    exercises = db.execute("""
        SELECT pe.id as pe_id, pe.exercise_id, pe.sets_prescribed,
               pe.reps_prescribed, pe.intensity_type, pe.intensity_value,
               e.category
        FROM program_exercises pe
        JOIN program_sessions ps ON pe.session_id = ps.id
        JOIN exercises e ON pe.exercise_id = e.id
        WHERE ps.program_id = ?
    """, [program_id]).fetchall()

    for ex in exercises:
        # Skip if already has prescriptions (idempotency for re-runs)
        existing = db.execute(
            "SELECT COUNT(*) FROM weekly_prescriptions WHERE program_exercise_id = ?",
            [ex["pe_id"]]
        ).fetchone()[0]
        if existing > 0:
            continue

        is_compound = ex["category"] == "compound"
        key_prefix = "compound" if is_compound else "isolation"

        base_sets = ex["sets_prescribed"]
        rpe_range = config.get(f"{key_prefix}_rpe", (7, 8))

        progression = calculate_weekly_progression(
            base_sets=base_sets,
            weeks=weeks,
            progression_type=config.get("volume_progression", "linear"),
            intensity_start=config.get("intensity_start_pct", 70),
            intensity_end=config.get("intensity_end_pct", 80),
            rpe_start=rpe_range[0],
            rpe_end=rpe_range[1],
        )

        e1rm = e1rms.get(ex["exercise_id"])

        for wp in progression:
            target_weight = prescribe_weight(e1rm, wp["intensity_pct"]) if e1rm else None

            db.execute("""
                INSERT INTO weekly_prescriptions
                (program_exercise_id, week_number, sets_prescribed, reps_prescribed,
                 intensity_pct, target_weight, target_rpe)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [
                ex["pe_id"], wp["week"], wp["sets"],
                ex["reps_prescribed"], wp["intensity_pct"],
                target_weight, wp["rpe"],
            ])


# 12 primary muscles the generator should audit and fix
_PRIMARY_MUSCLES = {
    "chest", "front_delts", "side_delts", "rear_delts", "lats", "upper_back",
    "quads", "hamstrings", "glutes", "biceps", "triceps", "calves",
}

# Mapping: muscle -> best isolation movement pattern to add
_MUSCLE_FIX_PATTERNS = {
    "chest": ("horizontal_push", "isolation"),
    "front_delts": ("vertical_push", "isolation"),
    "side_delts": ("lateral_raise", "isolation"),
    "rear_delts": ("horizontal_pull", "isolation"),
    "lats": ("vertical_pull", "compound"),
    "upper_back": ("horizontal_pull", "compound"),
    "quads": ("knee_extension", "isolation"),
    "hamstrings": ("knee_flexion", "isolation"),
    "glutes": ("hip_extension", "compound"),
    "biceps": ("elbow_flexion", "isolation"),
    "triceps": ("elbow_extension", "isolation"),
    "calves": ("ankle_plantar_flexion", "isolation"),
}


def _adjust_for_volume(db, program_id, athlete_id, config, max_passes=3):
    """
    Iteratively add exercises to fix volume deficits.

    1. Calculate projected volume
    2. Audit against landmarks (primary muscles only)
    3. For each below_mev: add an isolation exercise to the least-loaded session
    4. Re-audit. Repeat up to max_passes.

    Returns final volume_summary.
    """
    for _pass in range(max_passes):
        volume_summary = _calculate_program_volume(db, program_id)
        audit = volume_summary.get("audit", [])

        # Filter to below_mev on primary muscles only
        deficits = [
            a for a in audit
            if a["issue"] == "below_mev" and a["muscle"] in _PRIMARY_MUSCLES
        ]
        if not deficits:
            return volume_summary  # All good

        # Find least-loaded session (fewest exercises)
        sessions = db.execute("""
            SELECT ps.id, ps.name, COUNT(pe.id) as ex_count
            FROM program_sessions ps
            LEFT JOIN program_exercises pe ON pe.session_id = ps.id
            WHERE ps.program_id = ?
            GROUP BY ps.id
            ORDER BY ex_count ASC
        """, [program_id]).fetchall()

        if not sessions:
            return volume_summary

        for deficit in deficits[:2]:  # Fix at most 2 deficits per pass
            muscle = deficit["muscle"]
            fix = _MUSCLE_FIX_PATTERNS.get(muscle)
            if not fix:
                continue

            pattern, category = fix
            target_session = sessions[0]  # least loaded

            # Get current max exercise order in that session
            max_order = db.execute("""
                SELECT COALESCE(MAX(exercise_order), 0) FROM program_exercises
                WHERE session_id = ?
            """, [target_session["id"]]).fetchone()[0]

            i_sets = config.get("isolation_sets", (2, 3))
            i_reps = config.get("isolation_reps", (8, 12))

            _add_exercise_by_pattern(
                db, target_session["id"], pattern, category, None,
                i_sets[0], f"{i_reps[0]}-{i_reps[1]}", "rir", "2",
                config.get("rest_isolation", 60), max_order + 1, None,
            )

        db.commit()

    return _calculate_program_volume(db, program_id)
