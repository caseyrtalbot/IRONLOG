"""
Training streak calculation.

Pure function — no database, no HTTP, no side effects.
"""

from datetime import datetime, timedelta


def calculate_streak(workout_dates, today):
    """
    Pure function: count consecutive training days with 2-day grace window.

    Args:
        workout_dates: list of date strings (YYYY-MM-DD), descending order.
        today: date object.

    Returns:
        int streak count.
    """
    streak = 0
    for i, date_str in enumerate(workout_dates):
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        expected = today - timedelta(days=i)
        if d == expected or (today - d).days <= 2:
            streak += 1
        else:
            break
    return streak
