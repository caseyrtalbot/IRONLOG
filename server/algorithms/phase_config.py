"""
4x4 periodization matrix — phase-specific programming parameters.

Pure function — no database, no HTTP, no side effects.
Based on NSCA guidelines for goal/phase combinations.
"""


def generate_phase_config(goal, phase, experience, weeks=4):
    """
    Generate phase-specific programming parameters based on NSCA guidelines.
    Returns intensity, volume, and rep ranges for the given phase/goal.
    """
    configs = {
        "strength": {
            "accumulation": {
                "compound_sets": (3, 5), "compound_reps": (5, 8), "compound_rpe": (7, 8),
                "isolation_sets": (2, 4), "isolation_reps": (8, 12), "isolation_rpe": (7, 8.5),
                "rest_compound": 180, "rest_isolation": 90,
                "volume_progression": "linear", "intensity_start_pct": 70, "intensity_end_pct": 80
            },
            "intensification": {
                "compound_sets": (4, 6), "compound_reps": (2, 5), "compound_rpe": (8, 9.5),
                "isolation_sets": (2, 3), "isolation_reps": (6, 10), "isolation_rpe": (8, 9),
                "rest_compound": 240, "rest_isolation": 120,
                "volume_progression": "undulating", "intensity_start_pct": 80, "intensity_end_pct": 92
            },
            "realization": {
                "compound_sets": (3, 5), "compound_reps": (1, 3), "compound_rpe": (9, 10),
                "isolation_sets": (1, 2), "isolation_reps": (6, 8), "isolation_rpe": (7, 8),
                "rest_compound": 300, "rest_isolation": 120,
                "volume_progression": "taper", "intensity_start_pct": 90, "intensity_end_pct": 100
            },
            "deload": {
                "compound_sets": (2, 3), "compound_reps": (3, 5), "compound_rpe": (6, 7),
                "isolation_sets": (1, 2), "isolation_reps": (8, 10), "isolation_rpe": (6, 7),
                "rest_compound": 120, "rest_isolation": 60,
                "volume_progression": "reduced", "intensity_start_pct": 60, "intensity_end_pct": 70
            }
        },
        "hypertrophy": {
            "accumulation": {
                "compound_sets": (3, 4), "compound_reps": (8, 12), "compound_rpe": (7, 8.5),
                "isolation_sets": (3, 4), "isolation_reps": (10, 15), "isolation_rpe": (7, 9),
                "rest_compound": 120, "rest_isolation": 60,
                "volume_progression": "linear", "intensity_start_pct": 62, "intensity_end_pct": 72
            },
            "intensification": {
                "compound_sets": (3, 5), "compound_reps": (6, 10), "compound_rpe": (8, 9),
                "isolation_sets": (2, 4), "isolation_reps": (8, 12), "isolation_rpe": (8, 9.5),
                "rest_compound": 150, "rest_isolation": 75,
                "volume_progression": "step", "intensity_start_pct": 70, "intensity_end_pct": 82
            },
            "realization": {
                "compound_sets": (3, 4), "compound_reps": (4, 8), "compound_rpe": (8.5, 9.5),
                "isolation_sets": (2, 3), "isolation_reps": (6, 10), "isolation_rpe": (8, 9),
                "rest_compound": 180, "rest_isolation": 90,
                "volume_progression": "taper", "intensity_start_pct": 78, "intensity_end_pct": 88
            },
            "deload": {
                "compound_sets": (2, 3), "compound_reps": (8, 10), "compound_rpe": (5, 7),
                "isolation_sets": (1, 2), "isolation_reps": (10, 12), "isolation_rpe": (5, 7),
                "rest_compound": 90, "rest_isolation": 60,
                "volume_progression": "reduced", "intensity_start_pct": 55, "intensity_end_pct": 65
            }
        },
        "power": {
            "accumulation": {
                "compound_sets": (3, 5), "compound_reps": (3, 6), "compound_rpe": (7, 8),
                "isolation_sets": (2, 3), "isolation_reps": (6, 10), "isolation_rpe": (7, 8),
                "rest_compound": 180, "rest_isolation": 90,
                "volume_progression": "linear", "intensity_start_pct": 65, "intensity_end_pct": 78
            },
            "intensification": {
                "compound_sets": (4, 6), "compound_reps": (1, 3), "compound_rpe": (8, 9.5),
                "isolation_sets": (2, 3), "isolation_reps": (3, 6), "isolation_rpe": (8, 9),
                "rest_compound": 300, "rest_isolation": 150,
                "volume_progression": "undulating", "intensity_start_pct": 82, "intensity_end_pct": 95
            },
            "realization": {
                "compound_sets": (3, 5), "compound_reps": (1, 2), "compound_rpe": (9, 10),
                "isolation_sets": (1, 2), "isolation_reps": (3, 5), "isolation_rpe": (7, 8),
                "rest_compound": 360, "rest_isolation": 180,
                "volume_progression": "taper", "intensity_start_pct": 92, "intensity_end_pct": 100
            },
            "deload": {
                "compound_sets": (2, 3), "compound_reps": (2, 3), "compound_rpe": (6, 7),
                "isolation_sets": (1, 2), "isolation_reps": (6, 8), "isolation_rpe": (6, 7),
                "rest_compound": 120, "rest_isolation": 60,
                "volume_progression": "reduced", "intensity_start_pct": 55, "intensity_end_pct": 65
            }
        },
        "endurance": {
            "accumulation": {
                "compound_sets": (2, 3), "compound_reps": (12, 20), "compound_rpe": (6, 8),
                "isolation_sets": (2, 3), "isolation_reps": (15, 25), "isolation_rpe": (6, 8),
                "rest_compound": 60, "rest_isolation": 45,
                "volume_progression": "linear", "intensity_start_pct": 45, "intensity_end_pct": 60
            },
            "intensification": {
                "compound_sets": (3, 4), "compound_reps": (10, 15), "compound_rpe": (7, 9),
                "isolation_sets": (2, 3), "isolation_reps": (12, 20), "isolation_rpe": (7, 9),
                "rest_compound": 45, "rest_isolation": 30,
                "volume_progression": "step", "intensity_start_pct": 55, "intensity_end_pct": 68
            },
            "realization": {
                "compound_sets": (2, 3), "compound_reps": (8, 12), "compound_rpe": (8, 9),
                "isolation_sets": (2, 3), "isolation_reps": (10, 15), "isolation_rpe": (8, 9),
                "rest_compound": 60, "rest_isolation": 45,
                "volume_progression": "taper", "intensity_start_pct": 62, "intensity_end_pct": 72
            },
            "deload": {
                "compound_sets": (1, 2), "compound_reps": (10, 15), "compound_rpe": (5, 6),
                "isolation_sets": (1, 2), "isolation_reps": (12, 15), "isolation_rpe": (5, 6),
                "rest_compound": 60, "rest_isolation": 45,
                "volume_progression": "reduced", "intensity_start_pct": 40, "intensity_end_pct": 50
            }
        }
    }

    goal_key = goal if goal in configs else "strength"
    phase_key = phase if phase in configs[goal_key] else "accumulation"
    return configs[goal_key][phase_key]
