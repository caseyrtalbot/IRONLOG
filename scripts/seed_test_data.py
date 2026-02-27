"""
Seed realistic test data: one completed 4-week strength program with
logged workouts, progressive overload, and e1RM history.

Usage: python3 -m scripts.seed_test_data
"""

import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from server.db.connection import get_connection
from server.db.schema import init_schema
from server.db.seed_exercises import seed_exercises
from server.db.seed_muscles import seed_muscles
from server.algorithms.e1rm import estimate_1rm

ATHLETE_ID = 1

# Core exercises with realistic starting e1RMs for a 175lb intermediate lifter
EXERCISES = {
    "Barbell Bench Press":    {"id": 1,  "e1rm": 255},
    "Back Squat":             {"id": 19, "e1rm": 335},
    "Conventional Deadlift":  {"id": 29, "e1rm": 405},
    "Overhead Press":         {"id": 11, "e1rm": 155},
    "Barbell Row (Bent-Over)":{"id": 40, "e1rm": 225},
    "Pull-Up":                {"id": 51, "e1rm": 215},  # BW+40 ≈ 215
    "Romanian Deadlift":      {"id": 31, "e1rm": 285},
    "Incline Barbell Press":  {"id": 9,  "e1rm": 205},
    "Front Squat":            {"id": 20, "e1rm": 265},
}

# 4-day upper/lower split — 4 weeks of sessions
WEEKLY_SESSIONS = [
    {
        "name": "Upper A — Strength",
        "exercises": [
            ("Barbell Bench Press",    4, 5,  0.82),
            ("Barbell Row (Bent-Over)",4, 5,  0.80),
            ("Overhead Press",         3, 8,  0.72),
            ("Pull-Up",               3, 8,  0.70),
        ],
    },
    {
        "name": "Lower A — Strength",
        "exercises": [
            ("Back Squat",            4, 5,  0.82),
            ("Romanian Deadlift",     3, 8,  0.72),
            ("Front Squat",           3, 8,  0.70),
        ],
    },
    {
        "name": "Upper B — Volume",
        "exercises": [
            ("Incline Barbell Press", 4, 8,  0.72),
            ("Pull-Up",              4, 8,  0.70),
            ("Barbell Bench Press",   3, 8,  0.72),
            ("Barbell Row (Bent-Over)",3, 10, 0.68),
        ],
    },
    {
        "name": "Lower B — Volume",
        "exercises": [
            ("Conventional Deadlift", 3, 5,  0.82),
            ("Back Squat",            3, 8,  0.72),
            ("Romanian Deadlift",     3, 10, 0.68),
        ],
    },
]

# Progressive overload: week-over-week intensity bump
WEEKLY_INTENSITY_BUMP = [0.0, 0.02, 0.03, 0.05]  # Weeks 1-4


def round_weight(w):
    """Round to nearest 5 lbs."""
    return round(w / 5) * 5


def seed_test_data():
    db = get_connection()
    init_schema(db)
    seed_exercises(db)
    seed_muscles(db)

    # Ensure athlete exists
    athlete = db.execute("SELECT id FROM athletes WHERE id = ?", [ATHLETE_ID]).fetchone()
    if not athlete:
        db.execute(
            "INSERT INTO athletes (id, name, body_weight, experience_level, primary_goal) "
            "VALUES (?, 'Casey Talbot', 175.0, 'advanced', 'strength')",
            [ATHLETE_ID],
        )
        db.commit()

    # Start date: 6 weeks ago (completed program + 2 weeks rest)
    start_date = datetime.now() - timedelta(weeks=6)

    # Create a completed program
    cur = db.execute("""
        INSERT INTO programs (athlete_id, name, phase, goal, mesocycle_weeks,
                              current_week, status, suggested_next_phase, config)
        VALUES (?, 'Strength — Accumulation Block', 'accumulation', 'strength', 4, 4,
                'completed', 'intensification', '{}')
    """, [ATHLETE_ID])
    completed_program_id = cur.lastrowid

    # Create sessions for the completed program
    session_ids = []
    for i, sess in enumerate(WEEKLY_SESSIONS):
        cur = db.execute("""
            INSERT INTO program_sessions (program_id, day_number, name, focus)
            VALUES (?, ?, ?, ?)
        """, [completed_program_id, i + 1, sess["name"], "strength"])
        session_ids.append(cur.lastrowid)

        for j, (ex_name, sets, reps, _) in enumerate(sess["exercises"]):
            ex = EXERCISES[ex_name]
            db.execute("""
                INSERT INTO program_exercises (session_id, exercise_id, exercise_order,
                    sets_prescribed, reps_prescribed, intensity_type, intensity_value, rest_seconds)
                VALUES (?, ?, ?, ?, ?, 'rpe', '8', 180)
            """, [cur.lastrowid, ex["id"], j + 1, sets, str(reps)])

    db.commit()

    # Log 4 weeks of workouts (16 sessions total)
    body_weights = [175.0, 175.5, 176.0, 176.5]  # Slight gain over block
    session_rpes = [7.0, 7.5, 8.0, 8.5]  # Increasing difficulty

    total_workouts = 0
    for week in range(4):
        week_start = start_date + timedelta(weeks=week)
        bump = WEEKLY_INTENSITY_BUMP[week]

        for day_idx, sess in enumerate(WEEKLY_SESSIONS):
            workout_date = (week_start + timedelta(days=[0, 1, 3, 4][day_idx])).strftime("%Y-%m-%d")
            bw = body_weights[week] + random.uniform(-0.5, 0.5)

            cur = db.execute("""
                INSERT INTO workout_logs (athlete_id, program_id, session_id,
                    date, duration_min, session_rpe, body_weight, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                ATHLETE_ID, completed_program_id, session_ids[day_idx],
                workout_date, random.randint(55, 80),
                session_rpes[week] + random.uniform(-0.5, 0.5),
                round(bw, 1),
                f"Week {week + 1} — feeling {'strong' if week < 3 else 'fatigued'}",
            ])
            workout_id = cur.lastrowid
            total_workouts += 1

            for ex_name, num_sets, target_reps, base_pct in sess["exercises"]:
                ex = EXERCISES[ex_name]
                e1rm = ex["e1rm"]
                working_pct = base_pct + bump
                working_weight = round_weight(e1rm * working_pct)

                for s in range(1, num_sets + 1):
                    if s == 1:
                        # Warmup set
                        w = round_weight(working_weight * 0.6)
                        r = target_reps + 3
                        rpe = 5.0
                        set_type = "warmup"
                    else:
                        # Working sets with small variance
                        w = working_weight + random.choice([-5, 0, 0, 0, 5])
                        r = target_reps + random.choice([-1, 0, 0, 0, 1])
                        rpe = 7.5 + week * 0.3 + random.uniform(-0.5, 0.5)
                        rpe = round(min(10, max(6, rpe)), 1)
                        set_type = "working"

                    db.execute("""
                        INSERT INTO set_logs (workout_log_id, exercise_id, set_number,
                            set_type, weight, reps, rpe, rest_seconds)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, [workout_id, ex["id"], s, set_type, w, r, rpe,
                          180 if set_type == "working" else 90])

                    # Store e1RM for working sets
                    if set_type == "working" and w and r:
                        est = estimate_1rm(w, r, rpe)
                        if est > 0:
                            db.execute("""
                                INSERT INTO one_rep_maxes (athlete_id, exercise_id,
                                    estimated_1rm, method, source_weight, source_reps,
                                    source_rpe, date)
                                VALUES (?, ?, ?, 'epley', ?, ?, ?, ?)
                            """, [ATHLETE_ID, ex["id"], est, w, r, rpe, workout_date])

    db.commit()

    # Now generate an active program (intensification — next phase)
    from server.services.program_service import generate_program
    from server.models.program import ProgramGenerate

    active_body = ProgramGenerate(
        athlete_id=ATHLETE_ID,
        name="Strength — Intensification Block",
        goal="strength",
        phase="intensification",
        split="upper_lower",
        days_per_week=4,
        weeks=4,
    )
    result = generate_program(db, active_body)
    active_program_id = result["id"]

    # Log 1 week of the active program to show partial progress
    active_sessions = db.execute(
        "SELECT id, day_number FROM program_sessions WHERE program_id = ? ORDER BY day_number",
        [active_program_id],
    ).fetchall()

    recent_start = datetime.now() - timedelta(days=5)
    for i, sess in enumerate(active_sessions[:3]):  # 3 of 4 sessions done
        workout_date = (recent_start + timedelta(days=[0, 1, 3][i])).strftime("%Y-%m-%d")
        exercises = db.execute("""
            SELECT pe.*, e.name FROM program_exercises pe
            JOIN exercises e ON pe.exercise_id = e.id
            WHERE pe.session_id = ? ORDER BY exercise_order
        """, [sess["id"]]).fetchall()

        cur = db.execute("""
            INSERT INTO workout_logs (athlete_id, program_id, session_id,
                date, duration_min, session_rpe, body_weight)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [ATHLETE_ID, active_program_id, sess["id"],
              workout_date, random.randint(60, 75), 7.5, 176.0])
        workout_id = cur.lastrowid
        total_workouts += 1

        for ex in exercises:
            # Try to use a realistic weight based on known e1RMs
            ex_info = EXERCISES.get(ex["name"])
            base_weight = round_weight((ex_info["e1rm"] if ex_info else 135) * 0.78)

            for s in range(1, (ex["sets_prescribed"] or 3) + 1):
                if s == 1:
                    w, r, rpe, stype = round_weight(base_weight * 0.6), 8, 5.0, "warmup"
                else:
                    w = base_weight + random.choice([-5, 0, 0, 5])
                    r = 5 + random.choice([-1, 0, 0, 1])
                    rpe = 7.5 + random.uniform(-0.5, 0.5)
                    stype = "working"

                db.execute("""
                    INSERT INTO set_logs (workout_log_id, exercise_id, set_number,
                        set_type, weight, reps, rpe, rest_seconds)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, [workout_id, ex["exercise_id"], s, stype, w, r, round(rpe, 1), 180])

                if stype == "working" and w and r:
                    est = estimate_1rm(w, r, round(rpe, 1))
                    if est > 0:
                        db.execute("""
                            INSERT INTO one_rep_maxes (athlete_id, exercise_id,
                                estimated_1rm, method, source_weight, source_reps,
                                source_rpe, date)
                            VALUES (?, ?, ?, 'epley', ?, ?, ?, ?)
                        """, [ATHLETE_ID, ex["exercise_id"], est, w, r, round(rpe, 1), workout_date])

    db.commit()
    db.close()

    print(f"Seeded test data:")
    print(f"  1 completed program (4 weeks, 16 sessions)")
    print(f"  1 active program (intensification, week 1, 3/4 sessions logged)")
    print(f"  {total_workouts} total workouts logged")
    print(f"  e1RM history for {len(EXERCISES)} exercises")
    print(f"  Body weight: 175 → 176.5 lbs")


if __name__ == "__main__":
    seed_test_data()
