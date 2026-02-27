"""
Volume budget calculation and auditing.

Pure functions — no database, no HTTP, no side effects.
"""


def calculate_projected_volume(program_exercises):
    """
    Calculate projected weekly volume per muscle from a program's exercises.

    Args:
        program_exercises: list of dicts with:
            - sets_prescribed (int): number of sets
            - muscles (list): [{muscle_group, contribution}, ...]

    Returns:
        dict mapping muscle_group -> projected effective sets/week (float).
    """
    volume = {}
    for ex in program_exercises:
        sets = ex.get("sets_prescribed", 0)
        for m in ex.get("muscles", []):
            group = m["muscle_group"]
            contribution = m["contribution"]
            volume[group] = volume.get(group, 0) + (sets * contribution)
    return volume


def audit_volume(projected, landmarks):
    """
    Compare projected volume against landmarks, flag issues at two severity levels.

    Severity tiers:
        - below_mev / above_mrv: red — outside productive training range
        - below_mav / above_mav: yellow — suboptimal but not harmful

    Args:
        projected: dict from calculate_projected_volume
        landmarks: dict mapping muscle_group -> {mev, mav_low, mav_high, mrv}

    Returns:
        list of dicts: {muscle, issue, severity, projected, target, delta}
    """
    issues = []
    for muscle, targets in landmarks.items():
        vol = projected.get(muscle, 0)
        if vol < targets["mev"]:
            issues.append({
                "muscle": muscle,
                "issue": "below_mev",
                "severity": "red",
                "projected": round(vol, 1),
                "target": targets["mev"],
                "delta": round(targets["mev"] - vol, 1),
            })
        elif vol < targets["mav_low"]:
            issues.append({
                "muscle": muscle,
                "issue": "below_mav",
                "severity": "yellow",
                "projected": round(vol, 1),
                "target": targets["mav_low"],
                "delta": round(targets["mav_low"] - vol, 1),
            })
        elif vol > targets["mrv"]:
            issues.append({
                "muscle": muscle,
                "issue": "above_mrv",
                "severity": "red",
                "projected": round(vol, 1),
                "target": targets["mrv"],
                "delta": round(vol - targets["mrv"], 1),
            })
        elif vol > targets["mav_high"]:
            issues.append({
                "muscle": muscle,
                "issue": "above_mav",
                "severity": "yellow",
                "projected": round(vol, 1),
                "target": targets["mav_high"],
                "delta": round(vol - targets["mav_high"], 1),
            })
    return issues
