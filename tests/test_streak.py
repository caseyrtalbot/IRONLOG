from datetime import date
from server.algorithms.streak import calculate_streak


def test_streak_consecutive_days():
    today = date(2026, 2, 26)
    dates = ["2026-02-26", "2026-02-25", "2026-02-24"]
    assert calculate_streak(dates, today) == 3


def test_streak_with_grace_window():
    today = date(2026, 2, 26)
    # Skipped one day but within 2-day grace
    dates = ["2026-02-26", "2026-02-24"]
    assert calculate_streak(dates, today) == 2


def test_streak_broken():
    today = date(2026, 2, 26)
    # 4-day gap breaks the streak
    dates = ["2026-02-26", "2026-02-21"]
    assert calculate_streak(dates, today) == 1


def test_streak_no_workouts():
    today = date(2026, 2, 26)
    assert calculate_streak([], today) == 0
