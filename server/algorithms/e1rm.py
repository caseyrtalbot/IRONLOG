"""
Estimated 1-Rep Max calculations and RPE-based training weight prescriptions.

Pure functions — no database, no HTTP, no side effects.
"""


def estimate_1rm(weight, reps, rpe=10):
    """Estimate 1RM using Epley formula with RPE adjustment."""
    if reps <= 0 or weight <= 0:
        return 0
    rir = 10 - rpe if rpe else 0
    effective_reps = reps + rir
    if effective_reps <= 1:
        return weight
    e1rm = weight * (1 + effective_reps / 30.0)
    return round(e1rm, 1)


def rpe_to_percentage(rpe, reps):
    """Tuchscherer RPE chart - maps RPE and rep count to %1RM."""
    chart = {
        10:  {1: 100, 2: 95.5, 3: 92.2, 4: 89.2, 5: 86.3, 6: 83.7, 7: 81.1, 8: 78.6, 9: 76.2, 10: 73.9, 12: 69.4},
        9.5: {1: 97.8, 2: 93.9, 3: 90.7, 4: 87.8, 5: 85.0, 6: 82.4, 7: 79.9, 8: 77.4, 9: 75.1, 10: 72.3, 12: 68.0},
        9:   {1: 95.5, 2: 92.2, 3: 89.2, 4: 86.3, 5: 83.7, 6: 81.1, 7: 78.6, 8: 76.2, 9: 73.9, 10: 71.0, 12: 66.7},
        8.5: {1: 93.9, 2: 90.7, 3: 87.8, 4: 85.0, 5: 82.4, 6: 79.9, 7: 77.4, 8: 75.1, 9: 72.3, 10: 69.4, 12: 65.3},
        8:   {1: 92.2, 2: 89.2, 3: 86.3, 4: 83.7, 5: 81.1, 6: 78.6, 7: 76.2, 8: 73.9, 9: 71.0, 10: 68.0, 12: 64.0},
        7.5: {1: 90.7, 2: 87.8, 3: 85.0, 4: 82.4, 5: 79.9, 6: 77.4, 7: 75.1, 8: 72.3, 9: 69.4, 10: 66.7, 12: 62.6},
        7:   {1: 89.2, 2: 86.3, 3: 83.7, 4: 81.1, 5: 78.6, 6: 76.2, 7: 73.9, 8: 71.0, 9: 68.0, 10: 65.3, 12: 61.3},
        6.5: {1: 87.8, 2: 85.0, 3: 82.4, 4: 79.9, 5: 77.4, 6: 75.1, 7: 72.3, 8: 69.4, 9: 66.7, 10: 64.0, 12: 60.0},
        6:   {1: 86.3, 2: 83.7, 3: 81.1, 4: 78.6, 5: 76.2, 6: 73.9, 7: 71.0, 8: 68.0, 9: 65.3, 10: 62.6, 12: 58.8},
    }
    rpe_key = max(6, min(10, round(rpe * 2) / 2))
    rep_key = min(12, max(1, reps))
    if rpe_key in chart and rep_key in chart[rpe_key]:
        return chart[rpe_key][rep_key]
    return 75.0


def calculate_training_weight(e1rm, rpe, reps):
    """Calculate recommended training weight from e1RM, target RPE, and rep count."""
    pct = rpe_to_percentage(rpe, reps) / 100.0
    return round(e1rm * pct, 1)


def calculate_volume_load(sets_data):
    """Calculate total volume load (sets x reps x weight) from set logs."""
    total = 0
    for s in sets_data:
        w = s.get('weight', 0) or 0
        r = s.get('reps', 0) or 0
        total += w * r
    return round(total, 1)
