"""
Program service — program generation and retrieval.

All functions receive a DB cursor and typed arguments; they never touch HTTP.
Delegates phase-config computation to server.algorithms.phase_config.
"""

import json

from server.algorithms.phase_config import generate_phase_config
from server.models.program import ProgramGenerate


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
        s["exercises"] = [dict(ex) for ex in exercises]
        result["sessions"].append(s)

    # Include volume audit summary
    try:
        result["volume_summary"] = _calculate_program_volume(db, program_id)
    except Exception:
        result["volume_summary"] = None

    return result


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

    # Volume audit
    try:
        volume_summary = _calculate_program_volume(db, program_id)
    except Exception:
        volume_summary = None

    return {"id": program_id, "name": program_name, "status": "generated",
            "volume_summary": volume_summary}


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
    from server.algorithms.volume_budget import calculate_projected_volume, audit_volume

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

    from server.services.analytics_service import get_volume_landmarks
    landmarks_list = get_volume_landmarks(db, athlete_id)
    landmarks = {l["muscle_group"]: l for l in landmarks_list}

    audit = audit_volume(projected, landmarks)

    return {
        "projected": {k: round(v, 1) for k, v in sorted(projected.items())},
        "audit": audit,
    }
