"""
Progressive overload recommendation engine.

Pure function — no database, no HTTP, no side effects.
Takes session data as arguments and returns recommendations.
"""

from .e1rm import estimate_1rm


def recommend_overload(last_session, prev_session, current_e1rm):
    """
    Pure function: analyze recent sessions, return overload recommendation.

    Args:
        last_session: list of dicts with weight, reps, rpe keys (most recent session).
        prev_session: list of dicts with weight, reps, rpe keys (previous session).
        current_e1rm: float, current estimated 1RM for the exercise.

    Returns:
        dict with action, suggested_weight, suggested_reps, rationale.
    """
    if not last_session or len(last_session) < 1:
        return {"status": "insufficient_data", "message": "Need at least 1 logged session"}

    # Calculate averages from last session
    last_avg_weight = sum(s.get("weight", 0) or 0 for s in last_session) / max(1, len(last_session))
    last_avg_reps = sum(s.get("reps", 0) or 0 for s in last_session) / max(1, len(last_session))
    rpe_entries = [s for s in last_session if s.get("rpe")]
    last_avg_rpe = sum(s["rpe"] for s in rpe_entries) / max(1, len(rpe_entries)) if rpe_entries else 8.0

    # Fallback e1rm if not provided
    if not current_e1rm:
        current_e1rm = estimate_1rm(last_avg_weight, last_avg_reps, last_avg_rpe)

    recommendation = {
        "current_e1rm": current_e1rm,
        "last_session": {
            "avg_weight": round(last_avg_weight, 1),
            "avg_reps": round(last_avg_reps, 1),
            "avg_rpe": round(last_avg_rpe, 1),
        },
    }

    if last_avg_rpe < 7:
        # Too light — bump weight 5%
        new_weight = round(last_avg_weight * 1.05, 1)
        recommendation["action"] = "increase_load"
        recommendation["suggested_weight"] = new_weight
        recommendation["suggested_reps"] = round(last_avg_reps)
        recommendation["rationale"] = (
            f"RPE {last_avg_rpe} indicates capacity for heavier loading. Increase by ~5%."
        )
    elif last_avg_rpe < 8.5:
        # Productive range — micro-load 2.5%
        new_weight = round(last_avg_weight * 1.025, 1)
        recommendation["action"] = "micro_load"
        recommendation["suggested_weight"] = new_weight
        recommendation["suggested_reps"] = round(last_avg_reps)
        recommendation["rationale"] = (
            f"RPE {last_avg_rpe} is in productive range. Micro-load 2.5% for sustained progression."
        )
    elif last_avg_rpe >= 9.5:
        # Near maximal — add reps or deload
        recommendation["action"] = "add_reps_or_deload"
        recommendation["suggested_weight"] = round(last_avg_weight, 1)
        recommendation["suggested_reps"] = round(last_avg_reps) + 1
        recommendation["rationale"] = (
            f"RPE {last_avg_rpe} is near-maximal. Add 1 rep at same weight or consider deload."
        )
    else:
        # RPE 8.5–9.5 — standard linear progression
        new_weight = round(last_avg_weight + 2.5, 1)
        recommendation["action"] = "standard_progression"
        recommendation["suggested_weight"] = new_weight
        recommendation["suggested_reps"] = round(last_avg_reps)
        recommendation["rationale"] = (
            f"RPE {last_avg_rpe} supports linear load increase. Add 2.5 lbs/1.25 kg."
        )

    return recommendation
