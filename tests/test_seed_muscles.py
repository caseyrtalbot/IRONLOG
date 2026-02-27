# tests/test_seed_muscles.py
import sqlite3
from server.db.schema import init_schema
from server.db.seed_exercises import seed_exercises
from server.db.seed_muscles import seed_muscles, CANONICAL_GROUPS, IDENTIFIER_MAP, EXERCISE_OVERRIDES


def _setup_db():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    init_schema(db)
    seed_exercises(db)
    return db


def test_canonical_groups_count():
    assert len(CANONICAL_GROUPS) == 16


def test_identifier_map_covers_all():
    """Every identifier in the map resolves to a canonical group."""
    for identifier, canonical in IDENTIFIER_MAP.items():
        assert canonical in CANONICAL_GROUPS, f"{identifier} maps to unknown group {canonical}"


def test_seed_populates_exercise_muscles():
    db = _setup_db()
    seed_muscles(db)
    count = db.execute("SELECT COUNT(*) FROM exercise_muscles").fetchone()[0]
    assert count > 500, f"Expected 500+ rows, got {count}"
    db.close()


def test_every_non_mobility_exercise_has_assignments():
    """Every exercise with a volume-relevant pattern has at least 1 muscle assignment."""
    db = _setup_db()
    seed_muscles(db)
    orphans = db.execute("""
        SELECT e.id, e.name, e.movement_pattern FROM exercises e
        LEFT JOIN exercise_muscles em ON e.id = em.exercise_id
        WHERE em.id IS NULL
        AND e.movement_pattern NOT IN (
            'shoulder_mobility', 'hip_mobility', 'spinal_mobility',
            'thoracic_extension', 'thoracic_rotation'
        )
    """).fetchall()
    orphan_names = [r["name"] for r in orphans]
    assert len(orphans) == 0, f"Exercises without muscle assignments: {orphan_names}"
    db.close()


def test_contribution_range():
    """All contribution values are between 0.25 and 1.0."""
    db = _setup_db()
    seed_muscles(db)
    bad = db.execute(
        "SELECT * FROM exercise_muscles WHERE contribution < 0.25 OR contribution > 1.0"
    ).fetchall()
    assert len(bad) == 0, f"Found {len(bad)} rows with contribution outside [0.25, 1.0]"
    db.close()


def test_bench_press_contributions():
    """Spot-check: Barbell Bench Press should have chest=1.0, front_delts=0.5, triceps=0.5."""
    db = _setup_db()
    seed_muscles(db)
    rows = db.execute("""
        SELECT em.muscle_group, em.contribution, em.is_primary
        FROM exercise_muscles em
        JOIN exercises e ON em.exercise_id = e.id
        WHERE e.name = 'Barbell Bench Press'
        ORDER BY em.contribution DESC
    """).fetchall()
    muscles = {r["muscle_group"]: r["contribution"] for r in rows}
    assert muscles["chest"] == 1.0
    assert muscles["front_delts"] == 0.5
    assert muscles["triceps"] == 0.5
    db.close()


def test_conventional_deadlift_override():
    """Spot-check: Conventional DL should have override values (quads 0.25, erectors 0.75)."""
    db = _setup_db()
    seed_muscles(db)
    rows = db.execute("""
        SELECT em.muscle_group, em.contribution
        FROM exercise_muscles em
        JOIN exercises e ON em.exercise_id = e.id
        WHERE e.name = 'Conventional Deadlift'
    """).fetchall()
    muscles = {r["muscle_group"]: r["contribution"] for r in rows}
    assert muscles.get("quads") == 0.25
    assert muscles.get("erectors") == 0.75
    db.close()


def test_rdl_vs_conventional_deadlift():
    """RDL should have higher hamstring and lower quad/erector than conventional."""
    db = _setup_db()
    seed_muscles(db)
    rdl = dict(db.execute("""
        SELECT em.muscle_group, em.contribution FROM exercise_muscles em
        JOIN exercises e ON em.exercise_id = e.id WHERE e.name = 'Romanian Deadlift'
    """).fetchall())
    conv = dict(db.execute("""
        SELECT em.muscle_group, em.contribution FROM exercise_muscles em
        JOIN exercises e ON em.exercise_id = e.id WHERE e.name = 'Conventional Deadlift'
    """).fetchall())
    # RDL: hamstrings should be >= conventional
    assert rdl.get("hamstrings", 0) >= conv.get("hamstrings", 0)
    # Conventional: quads should be > RDL (RDL has no quad contribution)
    assert conv.get("quads", 0) > rdl.get("quads", 0)
    db.close()


def test_pullup_has_core_pulldown_does_not():
    """Pull-Up should have core contribution; Lat Pulldown should not."""
    db = _setup_db()
    seed_muscles(db)
    pu = db.execute("""
        SELECT em.muscle_group FROM exercise_muscles em
        JOIN exercises e ON em.exercise_id = e.id WHERE e.name = 'Pull-Up'
    """).fetchall()
    pd = db.execute("""
        SELECT em.muscle_group FROM exercise_muscles em
        JOIN exercises e ON em.exercise_id = e.id WHERE e.name = 'Lat Pulldown'
    """).fetchall()
    pu_muscles = [r["muscle_group"] for r in pu]
    pd_muscles = [r["muscle_group"] for r in pd]
    assert "core" in pu_muscles
    assert "core" not in pd_muscles
    db.close()


def test_all_overrides_match_real_exercises():
    """Every key in EXERCISE_OVERRIDES must match an exercise name in the database."""
    db = _setup_db()
    exercise_names = {r["name"] for r in db.execute("SELECT name FROM exercises").fetchall()}
    unmatched = [name for name in EXERCISE_OVERRIDES if name not in exercise_names]
    assert len(unmatched) == 0, f"Override keys with no matching exercise: {unmatched}"
    db.close()


def test_idempotent():
    """Running seed_muscles twice should not duplicate rows."""
    db = _setup_db()
    seed_muscles(db)
    count1 = db.execute("SELECT COUNT(*) FROM exercise_muscles").fetchone()[0]
    seed_muscles(db)
    count2 = db.execute("SELECT COUNT(*) FROM exercise_muscles").fetchone()[0]
    assert count1 == count2
    db.close()
