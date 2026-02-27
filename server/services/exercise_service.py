"""
Exercise service — read-only exercise taxonomy queries.

All functions receive a DB cursor and typed arguments; they never touch HTTP.
"""

from typing import Optional


def get_exercises(
    db,
    pattern: str = "",
    category: str = "",
    equipment: str = "",
    muscle: str = "",
) -> list[dict]:
    """Return exercises matching optional filter criteria."""
    query = "SELECT * FROM exercises WHERE 1=1"
    args: list = []

    if pattern:
        query += " AND movement_pattern = ?"
        args.append(pattern)
    if category:
        query += " AND category = ?"
        args.append(category)
    if equipment:
        query += " AND equipment = ?"
        args.append(equipment)
    if muscle:
        query += " AND (primary_muscles LIKE ? OR secondary_muscles LIKE ?)"
        args.extend([f"%{muscle}%", f"%{muscle}%"])

    query += " ORDER BY name"
    rows = db.execute(query, args).fetchall()
    return [dict(r) for r in rows]


def get_exercise(db, exercise_id: int) -> Optional[dict]:
    """Return a single exercise by ID, or None if not found."""
    row = db.execute("SELECT * FROM exercises WHERE id = ?", [exercise_id]).fetchone()
    if not row:
        return None
    return dict(row)


def search_exercises(db, q: str) -> list[dict]:
    """Full-text-ish search across name, muscles, pattern, equipment."""
    if not q:
        return []
    rows = db.execute(
        """
        SELECT * FROM exercises
        WHERE name LIKE ? OR primary_muscles LIKE ?
           OR movement_pattern LIKE ? OR equipment LIKE ?
        ORDER BY name LIMIT 50
        """,
        [f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"],
    ).fetchall()
    return [dict(r) for r in rows]


def get_movement_patterns(db) -> list[dict]:
    """Return distinct movement patterns with exercise counts."""
    rows = db.execute(
        """
        SELECT DISTINCT movement_pattern, COUNT(*) as count
        FROM exercises GROUP BY movement_pattern ORDER BY movement_pattern
        """
    ).fetchall()
    return [dict(r) for r in rows]


def get_muscle_groups(db) -> list[str]:
    """Return a sorted, deduplicated list of primary muscle groups."""
    rows = db.execute(
        "SELECT DISTINCT primary_muscles FROM exercises ORDER BY primary_muscles"
    ).fetchall()
    muscles: set[str] = set()
    for r in rows:
        for m in r["primary_muscles"].split(","):
            muscles.add(m.strip())
    return sorted(muscles)
