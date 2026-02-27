"""
Muscle group volume aggregation.

Pure function — no database, no HTTP, no side effects.
Placeholder implementation for Phase 4 upgrade with contribution factors.
"""


def aggregate_muscle_volume(sets_with_muscles):
    """
    Aggregate volume per muscle group from set logs joined with exercise muscle data.
    This is a placeholder that currently works with comma-separated primary_muscles.
    Will be upgraded in Phase 4 to use exercise_muscles contribution factors.

    Args:
        sets_with_muscles: list of dicts with 'primary_muscles' (comma-separated str)
                           and 'sets' (int, defaults to 1) keys.

    Returns:
        dict mapping muscle name -> total sets count.
    """
    volume = {}
    for s in sets_with_muscles:
        muscles = s.get("primary_muscles", "").split(",")
        sets_count = s.get("sets", 1)
        for m in muscles:
            m = m.strip()
            if m:
                volume[m] = volume.get(m, 0) + sets_count
    return volume
