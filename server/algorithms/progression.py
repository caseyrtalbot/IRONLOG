# server/algorithms/progression.py
"""
Weekly progression curves and weight prescription.

Pure functions — no database, no HTTP, no side effects.
"""


def calculate_weekly_progression(
    base_sets, weeks, progression_type,
    intensity_start, intensity_end,
    rpe_start, rpe_end,
):
    """
    Generate per-week progression for a mesocycle.

    Args:
        base_sets: int — base number of sets from phase_config (e.g., 3)
        weeks: int — mesocycle length (e.g., 4)
        progression_type: str — "linear", "undulating", "step", "taper", "reduced"
        intensity_start: float — starting %1RM (e.g., 70)
        intensity_end: float — ending %1RM (e.g., 80)
        rpe_start: float — starting RPE target (e.g., 7.0)
        rpe_end: float — ending RPE target (e.g., 8.0)

    Returns:
        list of dicts: [{week, sets, intensity_pct, rpe}, ...]
    """
    result = []
    for w in range(1, weeks + 1):
        # Intensity always ramps linearly
        t = (w - 1) / max(1, weeks - 1)
        intensity = round(intensity_start + (intensity_end - intensity_start) * t, 1)
        rpe = round(rpe_start + (rpe_end - rpe_start) * t, 1)

        # Volume follows the progression curve
        sets = _volume_for_week(base_sets, w, weeks, progression_type)

        result.append({
            "week": w,
            "sets": sets,
            "intensity_pct": intensity,
            "rpe": rpe,
        })
    return result


_UNDULATING_OFFSETS = [0, 1, 0, 1]  # Wave: base, up, base, up


def _volume_for_week(base, week, total_weeks, progression_type):
    """Calculate sets for a given week based on progression curve."""
    t = (week - 1) / max(1, total_weeks - 1)  # 0.0 to 1.0

    if progression_type == "linear":
        # Ramp from base to base+1 over the mesocycle
        return base + round(t)

    elif progression_type == "undulating":
        # Wave: up, down, up, higher
        offsets = _UNDULATING_OFFSETS
        if total_weeks <= len(offsets):
            idx = week - 1
            return base + offsets[idx] if idx < len(offsets) else base
        else:
            # For longer mesocycles, alternate 0/+1
            return base + (week % 2)

    elif progression_type == "step":
        # Flat for first half, jump for second half
        if t < 0.5:
            return base
        return base + 1

    elif progression_type == "taper":
        # Start high, decrease toward end
        return base + 1 - round(t)

    elif progression_type == "reduced":
        # Deload: drop 1 set from base
        return max(1, base - 1)

    return base


def prescribe_weight(e1rm, intensity_pct):
    """
    Calculate prescribed training weight from e1RM and target intensity.

    Returns weight rounded to nearest 2.5 lbs, or None if e1RM unavailable.
    """
    if not e1rm or not intensity_pct:
        return None
    raw = e1rm * (intensity_pct / 100.0)
    return round(raw / 2.5) * 2.5
