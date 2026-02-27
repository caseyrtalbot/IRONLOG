"""
Exercise-muscle contribution seed data.

Two-layer assignment system:
  1. PATTERN_TEMPLATES: default contributions by (movement_pattern, category)
  2. EXERCISE_OVERRIDES: specific exercises that deviate from their pattern default

See docs/MUSCLE_ASSIGNMENTS_NOTE.md for design rationale.
"""

CANONICAL_GROUPS = [
    "chest", "front_delts", "side_delts", "rear_delts",
    "lats", "upper_back", "quads", "hamstrings", "glutes",
    "biceps", "triceps", "forearms", "calves",
    "core", "erectors", "adductors",
]

# Map exercise taxonomy identifiers → canonical groups
IDENTIFIER_MAP = {
    "chest": "chest", "upper_chest": "chest", "lower_chest": "chest",
    "anterior_deltoid": "front_delts",
    "lateral_deltoid": "side_delts",
    "rear_deltoid": "rear_delts",
    "lats": "lats",
    "rhomboids": "upper_back", "traps": "upper_back", "upper_traps": "upper_back",
    "lower_traps": "upper_back", "upper_back": "upper_back",
    "quads": "quads",
    "hamstrings": "hamstrings",
    "glutes": "glutes", "glute_medius": "glutes", "glute_minimus": "glutes",
    "biceps": "biceps", "brachialis": "biceps",
    "biceps_long_head": "biceps", "biceps_short_head": "biceps",
    "triceps": "triceps", "triceps_long_head": "triceps",
    "forearms": "forearms", "brachioradialis": "forearms",
    "forearm_flexors": "forearms", "forearm_extensors": "forearms",
    "calves": "calves", "gastrocnemius": "calves", "soleus": "calves",
    "core": "core", "rectus_abdominis": "core", "obliques": "core",
    "hip_flexors": "core", "serratus_anterior": "core",
    "erectors": "erectors",
    "adductors": "adductors",
    "shoulders": "side_delts",  # generic fallback
}

# Patterns that produce zero volume (mobility/prehab)
_SKIP_PATTERNS = {
    "shoulder_mobility", "hip_mobility", "spinal_mobility",
    "thoracic_extension", "thoracic_rotation",
}

# Default contributions by (movement_pattern, category)
# Format: {muscle_group: (is_primary, contribution)}
PATTERN_TEMPLATES = {
    # === COMPOUND PUSH ===
    ("horizontal_push", "compound"): {
        "chest": (True, 1.0), "front_delts": (False, 0.5), "triceps": (False, 0.5),
    },
    ("vertical_push", "compound"): {
        "front_delts": (True, 1.0), "side_delts": (False, 0.5), "triceps": (False, 0.5),
    },
    # === COMPOUND PULL ===
    ("horizontal_pull", "compound"): {
        "upper_back": (True, 1.0), "lats": (True, 0.75),
        "rear_delts": (False, 0.5), "biceps": (False, 0.5), "forearms": (False, 0.25),
    },
    ("vertical_pull", "compound"): {
        "lats": (True, 1.0), "biceps": (False, 0.5),
        "rear_delts": (False, 0.25), "forearms": (False, 0.25),
    },
    # === COMPOUND LOWER ===
    ("squat", "compound"): {
        "quads": (True, 1.0), "glutes": (False, 0.5),
        "core": (False, 0.25), "erectors": (False, 0.25),
    },
    ("hip_hinge", "compound"): {
        "glutes": (True, 1.0), "hamstrings": (True, 0.75), "erectors": (False, 0.5),
    },
    ("lunge", "compound"): {
        "quads": (True, 0.75), "glutes": (True, 0.75), "hamstrings": (False, 0.25),
    },
    ("hip_extension", "compound"): {
        "glutes": (True, 1.0), "hamstrings": (False, 0.5),
    },
    ("hip_extension", "isolation"): {"glutes": (True, 1.0)},
    ("hip_abduction", "isolation"): {"glutes": (True, 1.0)},
    ("hip_adduction", "isolation"): {"adductors": (True, 1.0)},
    # === ISOLATION LIMBS ===
    ("knee_extension", "isolation"): {"quads": (True, 1.0)},
    ("knee_flexion", "isolation"): {"hamstrings": (True, 1.0)},
    ("knee_flexion", "compound"): {"hamstrings": (True, 1.0), "glutes": (False, 0.5)},
    ("ankle_plantar_flexion", "isolation"): {"calves": (True, 1.0)},
    ("elbow_flexion", "isolation"): {"biceps": (True, 1.0), "forearms": (False, 0.25)},
    ("elbow_extension", "isolation"): {"triceps": (True, 1.0)},
    ("lateral_raise", "isolation"): {"side_delts": (True, 1.0)},
    ("lateral_raise", "compound"): {"side_delts": (True, 1.0), "upper_back": (False, 0.5)},
    ("horizontal_push", "isolation"): {"chest": (True, 1.0)},
    ("horizontal_pull", "isolation"): {"rear_delts": (True, 1.0)},
    ("vertical_pull", "isolation"): {"lats": (True, 1.0)},
    ("shoulder_flexion", "isolation"): {"front_delts": (True, 1.0)},
    # === CORE ===
    ("spinal_flexion", "isolation"): {"core": (True, 1.0)},
    ("anti_extension", "isolation"): {"core": (True, 1.0)},
    ("anti_rotation", "isolation"): {"core": (True, 1.0)},
    ("anti_lateral_flexion", "isolation"): {"core": (True, 1.0)},
    ("lateral_flexion", "isolation"): {"core": (True, 1.0)},
    ("rotation", "isolation"): {"core": (True, 1.0)},
    # === TRAPS / UPPER BACK ===
    ("scapular_elevation", "isolation"): {"upper_back": (True, 1.0)},
    ("scapular_elevation", "compound"): {"upper_back": (True, 1.0), "rear_delts": (False, 0.25)},
    ("scapular_retraction", "isolation"): {"upper_back": (True, 1.0), "rear_delts": (False, 0.5)},
    # === FOREARMS ===
    ("wrist_flexion", "isolation"): {"forearms": (True, 1.0)},
    ("wrist_extension", "isolation"): {"forearms": (True, 1.0)},
    ("grip", "isolation"): {"forearms": (True, 1.0)},
    # === OLYMPIC / POWER ===
    ("olympic", "compound"): {
        "quads": (True, 0.5), "glutes": (True, 0.5), "hamstrings": (False, 0.5),
        "upper_back": (False, 0.5), "erectors": (False, 0.5),
    },
    ("plyometric", "compound"): {"quads": (True, 0.5), "glutes": (True, 0.5)},
    # === CARRIES ===
    ("loaded_carry", "compound"): {
        "forearms": (True, 0.75), "core": (False, 0.5), "upper_back": (False, 0.5),
    },
    ("anti_lateral_flexion", "compound"): {
        "core": (True, 0.75), "forearms": (False, 0.5), "upper_back": (False, 0.25),
    },
}

# Exercise-specific overrides: exercise name → {muscle: (is_primary, contribution)}
EXERCISE_OVERRIDES = {
    # --- Push overrides ---
    "Close-Grip Bench Press": {
        "triceps": (True, 1.0), "chest": (False, 0.5), "front_delts": (False, 0.25),
    },
    "Incline Barbell Press": {
        "chest": (True, 0.75), "front_delts": (True, 0.75), "triceps": (False, 0.5),
    },
    "Incline Dumbbell Press": {
        "chest": (True, 0.75), "front_delts": (True, 0.75), "triceps": (False, 0.25),
    },
    "Decline Barbell Press": {
        "chest": (True, 1.0), "triceps": (False, 0.5), "front_delts": (False, 0.25),
    },
    "Floor Press": {
        "triceps": (True, 0.75), "chest": (True, 0.75), "front_delts": (False, 0.25),
    },
    "Dip": {
        "chest": (True, 0.75), "triceps": (True, 0.75), "front_delts": (False, 0.5),
    },
    "Weighted Dip": {
        "chest": (True, 0.75), "triceps": (True, 0.75), "front_delts": (False, 0.5),
    },
    "Behind-the-Neck Press": {
        "side_delts": (True, 0.75), "front_delts": (True, 0.75), "triceps": (False, 0.5),
    },
    "Push Press": {
        "front_delts": (True, 0.75), "triceps": (False, 0.5),
        "side_delts": (False, 0.25), "quads": (False, 0.25), "glutes": (False, 0.25),
    },
    "Barbell Thruster": {
        "quads": (True, 0.5), "front_delts": (True, 0.75), "triceps": (False, 0.5),
        "glutes": (False, 0.25), "core": (False, 0.25),
    },
    "Diamond Push-Up": {
        "triceps": (True, 1.0), "chest": (False, 0.5), "front_delts": (False, 0.25),
    },
    "JM Press": {
        "triceps": (True, 1.0), "chest": (False, 0.5), "front_delts": (False, 0.25),
    },
    "Board Press": {
        "triceps": (True, 0.75), "chest": (True, 0.75), "front_delts": (False, 0.25),
    },
    "Spoto Press": {
        "chest": (True, 1.0), "triceps": (False, 0.5), "front_delts": (False, 0.5),
    },
    "Landmine Press": {
        "front_delts": (True, 0.75), "chest": (False, 0.5),
        "triceps": (False, 0.5), "core": (False, 0.25),
    },
    "Ring Dip": {
        "chest": (True, 0.75), "triceps": (True, 0.75),
        "front_delts": (False, 0.5), "core": (False, 0.25),
    },
    "Bench Dip": {
        "triceps": (True, 1.0), "chest": (False, 0.25), "front_delts": (False, 0.25),
    },
    # --- Pull overrides ---
    "Pull-Up": {
        "lats": (True, 1.0), "biceps": (False, 0.5),
        "core": (False, 0.25), "forearms": (False, 0.25), "rear_delts": (False, 0.25),
    },
    "Weighted Pull-Up": {
        "lats": (True, 1.0), "biceps": (False, 0.5),
        "core": (False, 0.25), "forearms": (False, 0.25), "rear_delts": (False, 0.25),
    },
    "Chin-Up": {
        "lats": (True, 1.0), "biceps": (True, 0.75),
        "forearms": (False, 0.25), "rear_delts": (False, 0.25),
    },
    "Weighted Chin-Up": {
        "lats": (True, 1.0), "biceps": (True, 0.75),
        "forearms": (False, 0.25), "rear_delts": (False, 0.25),
    },
    "Pendlay Row": {
        "upper_back": (True, 1.0), "lats": (True, 0.75),
        "rear_delts": (False, 0.5), "biceps": (False, 0.5), "erectors": (False, 0.25),
    },
    "Muscle-Up": {
        "lats": (True, 0.75), "chest": (False, 0.5), "triceps": (False, 0.5),
        "biceps": (False, 0.5), "core": (False, 0.25),
    },
    "Supinated Barbell Row": {
        "upper_back": (True, 1.0), "lats": (True, 0.75),
        "biceps": (True, 0.75), "rear_delts": (False, 0.5),
    },
    # --- Lower body overrides ---
    "Conventional Deadlift": {
        "glutes": (True, 1.0), "hamstrings": (True, 0.75), "erectors": (True, 0.75),
        "quads": (False, 0.25), "lats": (False, 0.25), "forearms": (False, 0.25),
    },
    "Sumo Deadlift": {
        "glutes": (True, 1.0), "quads": (True, 0.75), "hamstrings": (False, 0.5),
        "adductors": (False, 0.5), "erectors": (False, 0.5),
    },
    "Romanian Deadlift": {
        "hamstrings": (True, 1.0), "glutes": (False, 0.5), "erectors": (False, 0.5),
    },
    "Dumbbell Romanian Deadlift": {
        "hamstrings": (True, 1.0), "glutes": (False, 0.5), "erectors": (False, 0.25),
    },
    "Good Morning": {
        "hamstrings": (True, 1.0), "erectors": (True, 0.75), "glutes": (False, 0.5),
    },
    "Front Squat": {
        "quads": (True, 1.0), "glutes": (False, 0.5),
        "core": (False, 0.5), "upper_back": (False, 0.25),
    },
    "Box Squat": {
        "quads": (True, 0.75), "glutes": (True, 0.75),
        "hamstrings": (False, 0.5), "erectors": (False, 0.25),
    },
    "Sumo Squat": {
        "quads": (True, 0.75), "glutes": (True, 0.75), "adductors": (False, 0.5),
    },
    "Zercher Squat": {
        "quads": (True, 1.0), "glutes": (False, 0.5),
        "core": (False, 0.5), "biceps": (False, 0.25), "upper_back": (False, 0.25),
    },
    "Trap Bar Deadlift": {
        "quads": (True, 0.75), "glutes": (True, 0.75),
        "hamstrings": (False, 0.5), "erectors": (False, 0.5),
    },
    "Block Pull / Rack Pull": {
        "erectors": (True, 1.0), "glutes": (True, 0.75),
        "upper_back": (False, 0.5), "hamstrings": (False, 0.25), "forearms": (False, 0.25),
    },
    "Snatch-Grip Deadlift": {
        "upper_back": (True, 0.75), "hamstrings": (True, 0.75), "glutes": (True, 0.75),
        "erectors": (False, 0.5),
    },
    "Deficit Deadlift": {
        "hamstrings": (True, 1.0), "glutes": (True, 0.75),
        "quads": (False, 0.5), "erectors": (False, 0.5),
    },
    "Curtsy Lunge": {
        "quads": (True, 0.75), "glutes": (True, 0.75), "adductors": (False, 0.5),
    },
    "45-Degree Back Extension": {
        "erectors": (True, 1.0), "glutes": (False, 0.5), "hamstrings": (False, 0.5),
    },
    "Reverse Hyperextension": {
        "glutes": (True, 0.75), "hamstrings": (False, 0.5), "erectors": (True, 0.75),
    },
    "Glute-Ham Raise": {
        "hamstrings": (True, 1.0), "glutes": (False, 0.5), "erectors": (False, 0.25),
    },
    "Cable Pull-Through": {
        "glutes": (True, 1.0), "hamstrings": (False, 0.5), "erectors": (False, 0.25),
    },
    # --- Arm overrides ---
    "Hammer Curl": {
        "biceps": (True, 0.75), "forearms": (True, 0.75),
    },
    "Reverse Curl": {
        "forearms": (True, 1.0), "biceps": (False, 0.25),
    },
    "Fat Grip Curl": {
        "biceps": (True, 0.75), "forearms": (True, 0.75),
    },
    "Zottman Curl": {
        "biceps": (True, 0.75), "forearms": (True, 0.75),
    },
    # --- Core overrides ---
    "Copenhagen Plank": {
        "core": (True, 0.75), "adductors": (True, 0.75),
    },
    "Copenhagen Dip": {
        "adductors": (True, 0.75), "core": (True, 0.75),
    },
    # --- Plyometric overrides ---
    "Plyo Push-Up": {
        "chest": (True, 0.5), "triceps": (False, 0.5), "front_delts": (False, 0.25),
    },
    "Medicine Ball Slam": {
        "lats": (True, 0.5), "core": (True, 0.5), "front_delts": (False, 0.25),
    },
    # --- Miscellaneous / loaded carry overrides ---
    "Sled Push": {
        "quads": (True, 0.75), "glutes": (True, 0.75), "calves": (False, 0.25), "core": (False, 0.25),
    },
    "Sled Pull": {
        "hamstrings": (True, 0.5), "glutes": (True, 0.5), "calves": (False, 0.25),
        "core": (False, 0.25), "lats": (False, 0.25),
    },
    "Kettlebell Swing": {
        "glutes": (True, 1.0), "hamstrings": (False, 0.5), "core": (False, 0.25),
    },
    # --- Template mismatch overrides ---
    "Y-Raise": {
        "upper_back": (True, 0.75), "rear_delts": (True, 0.75),
    },
}


def seed_muscles(db):
    """Populate exercise_muscles from pattern templates + exercise overrides."""
    count = db.execute("SELECT COUNT(*) FROM exercise_muscles").fetchone()[0]
    if count > 0:
        return

    exercises = db.execute(
        "SELECT id, name, movement_pattern, category FROM exercises"
    ).fetchall()

    rows = []
    for ex in exercises:
        pattern = ex["movement_pattern"]
        category = ex["category"]
        name = ex["name"]

        # Skip mobility patterns
        if pattern in _SKIP_PATTERNS:
            continue

        # Check for exercise-specific override first
        if name in EXERCISE_OVERRIDES:
            muscles = EXERCISE_OVERRIDES[name]
        else:
            # Look up pattern template
            key = (pattern, category)
            muscles = PATTERN_TEMPLATES.get(key)
            if not muscles:
                # Fallback: try just pattern with either category
                for cat in ("compound", "isolation"):
                    muscles = PATTERN_TEMPLATES.get((pattern, cat))
                    if muscles:
                        break

        if not muscles:
            continue  # Unrecognized pattern, skip

        for muscle_group, (is_primary, contribution) in muscles.items():
            rows.append((ex["id"], muscle_group, int(is_primary), contribution))

    db.executemany(
        """INSERT OR IGNORE INTO exercise_muscles
           (exercise_id, muscle_group, is_primary, contribution)
           VALUES (?, ?, ?, ?)""",
        rows,
    )
    db.commit()
