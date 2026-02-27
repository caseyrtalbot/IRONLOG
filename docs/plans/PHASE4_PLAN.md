# Phase 4: Exercise-Muscle Foundation & Volume Intelligence

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable evidence-based per-muscle volume tracking by populating exercise-muscle contribution data, upgrading volume analytics to use contribution-weighted sets, and adding volume-aware budgeting to the program generator.

**Architecture:** Two-layer assignment system — movement pattern templates provide default contributions for all 292 exercises, with exercise-specific overrides for biomechanical edge cases. 16 canonical muscle groups mapped from ~30 exercise taxonomy identifiers. Contribution-weighted sets (`sets × contribution_factor`) as the volume unit.

**Tech Stack:** Python 3 / FastAPI / SQLite / Vanilla JS (ES modules) / Chart.js

---

## Design Foundations

### A. 16 Canonical Muscle Groups

These map cleanly to volume landmarks (MEV/MAV/MRV) based on literature (Israetel/RP, Helms et al, Schoenfeld).

| # | Canonical Name | Mapped From (exercise taxonomy identifiers) | Rationale |
|---|---|---|---|
| 1 | `chest` | chest, upper_chest, lower_chest | Single group per literature; regional variation is minor for volume tracking |
| 2 | `front_delts` | anterior_deltoid | Split from "shoulders" — heavily loaded by pressing, different recovery profile |
| 3 | `side_delts` | lateral_deltoid | Highest volume tolerance of any muscle; primarily isolation-trained |
| 4 | `rear_delts` | rear_deltoid | High volume tolerance; trained by pulling + isolation |
| 5 | `lats` | lats | Primary back width; vertical pull dominant |
| 6 | `upper_back` | rhomboids, traps, upper_traps, lower_traps, upper_back | Combined postural muscles; rows and retraction dominant |
| 7 | `quads` | quads | Squat pattern |
| 8 | `hamstrings` | hamstrings | Curl and hinge pattern |
| 9 | `glutes` | glutes, glute_medius, glute_minimus | Hip extension complex |
| 10 | `biceps` | biceps, brachialis, biceps_long_head, biceps_short_head | Elbow flexion complex |
| 11 | `triceps` | triceps, triceps_long_head | Elbow extension complex |
| 12 | `forearms` | forearms, brachioradialis, forearm_flexors, forearm_extensors | Grip/wrist complex |
| 13 | `calves` | calves, gastrocnemius, soleus | Plantar flexion complex |
| 14 | `core` | core, rectus_abdominis, obliques, hip_flexors, serratus_anterior | Ab/oblique/stabilizer group |
| 15 | `erectors` | erectors | Spinal erectors — separate because high fatigue cost in heavy compound lifts |
| 16 | `adductors` | adductors | Hip adduction — relevant for squat-heavy programs in elite athletes |

**Unmapped identifiers** (mobility/prehab, negligible volume contribution):
- `external_rotators`, `internal_rotators`, `rotator_cuff` → Rotator cuff prehab, not tracked for volume
- `shoulders` (generic, appears in 2 exercises) → mapped to `side_delts` as default

### B. Contribution Value Scale

| Factor | Meaning | Example |
|---|---|---|
| **1.0** | Primary target — the muscle this exercise is designed to train | Bench press → chest |
| **0.75** | Major synergist — heavily involved, nearly co-primary | Conventional deadlift → glutes |
| **0.5** | Significant synergist — meaningfully trained but not the focus | Bench press → triceps |
| **0.25** | Minor synergist — some involvement, not a meaningful stimulus alone | Back squat → core |

**Floor: 0.25.** Below this, contribution is negligible for volume tracking.

**The 0.25 tier caveat:** At 0.25 contribution, 4 compound sets = 1 effective set. Over a full training week with 15-20 compound sets, stabilizer muscles (core, erectors) accumulate 4-5 effective sets from spillover alone. This is tracked accurately in analytics. However, the **generator audit must not chase MEV for stabilizer-dominant muscles** — see Section F for the architectural fix.

### B2. Assignment System Rules

**Override semantics: FULL REPLACE.** When an exercise has an override, it completely replaces the pattern template. The override dict IS the complete muscle assignment for that exercise. No merging, no inheritance. This means overrides are slightly duplicative (~30 entries) but trivially simple to reason about — what you see is what you get.

**Resolution order:** Every exercise has exactly one `movement_pattern` tag in the database, chosen by primary force vector. The template system is a flat lookup `(pattern, category) → muscles`, not a multi-inheritance merge. If the single-pattern assignment gives wrong muscles for a specific exercise, that's what overrides are for (e.g., Landmine Press is tagged `vertical_push` but gets an override because it's angled between vertical and horizontal).

**Miscellaneous exercises:** Exercises that resist clean pattern categorization (farmer's walks, sled pushes, carries, medicine ball work) MUST be explicit overrides rather than forced into ill-fitting patterns. During implementation, the agent should flag any exercise that can't cleanly map to a single pattern template — those become mandatory overrides.

### C. Volume Formula

```
weekly_sets_per_muscle[m] = SUM(em.contribution)
  FOR ALL set_logs sl
  JOIN exercise_muscles em ON sl.exercise_id = em.exercise_id
  WHERE em.muscle_group = m
    AND sl.set_type = 'working'
    AND sl.workout_log_id IN (workouts from past 7 days)
```

A set of Bench Press (4 working sets) contributes:
- chest: 4 × 1.0 = **4.0 effective sets**
- front_delts: 4 × 0.5 = **2.0 effective sets**
- triceps: 4 × 0.5 = **2.0 effective sets**

### D. Movement Pattern Templates

The core design: **each (movement_pattern, category) pair defines a default muscle contribution map.** Exercises inherit from their template. Only meaningfully different exercises get overrides.

#### Compound Push

| Pattern | Primary | Synergists |
|---|---|---|
| `horizontal_push` / `compound` | chest: 1.0 | front_delts: 0.5, triceps: 0.5 |
| `vertical_push` / `compound` | front_delts: 1.0 | side_delts: 0.5, triceps: 0.5 |

#### Compound Pull

| Pattern | Primary | Synergists |
|---|---|---|
| `horizontal_pull` / `compound` | upper_back: 1.0 | lats: 0.75, rear_delts: 0.5, biceps: 0.5, forearms: 0.25 |
| `vertical_pull` / `compound` | lats: 1.0 | biceps: 0.5, rear_delts: 0.25, forearms: 0.25 |

#### Compound Lower

| Pattern | Primary | Synergists |
|---|---|---|
| `squat` / `compound` | quads: 1.0 | glutes: 0.5, core: 0.25, erectors: 0.25 |
| `hip_hinge` / `compound` | glutes: 1.0, hamstrings: 0.75 | erectors: 0.5 |
| `lunge` / `compound` | quads: 0.75, glutes: 0.75 | hamstrings: 0.25 |
| `hip_extension` / `compound` | glutes: 1.0 | hamstrings: 0.5 |

#### Isolation

| Pattern | Muscles |
|---|---|
| `knee_extension` / `isolation` | quads: 1.0 |
| `knee_flexion` / `isolation` | hamstrings: 1.0 |
| `ankle_plantar_flexion` / `isolation` | calves: 1.0 |
| `elbow_flexion` / `isolation` | biceps: 1.0, forearms: 0.25 |
| `elbow_extension` / `isolation` | triceps: 1.0 |
| `lateral_raise` / `isolation` | side_delts: 1.0 |
| `lateral_raise` / `compound` | side_delts: 1.0, upper_back: 0.5 | *(upright rows)*
| `horizontal_push` / `isolation` | chest: 1.0 | *(flies, pec deck)*
| `horizontal_pull` / `isolation` | rear_delts: 1.0 | *(reverse fly, face pull)*
| `vertical_pull` / `isolation` | lats: 1.0 | *(pullover)*
| `hip_extension` / `isolation` | glutes: 1.0 |
| `hip_abduction` / `isolation` | glutes: 1.0 |
| `hip_adduction` / `isolation` | adductors: 1.0 |
| `shoulder_flexion` / `isolation` | front_delts: 1.0 |

#### Core Patterns

| Pattern | Muscles |
|---|---|
| `spinal_flexion` / `isolation` | core: 1.0 |
| `anti_extension` / `isolation` | core: 1.0 |
| `anti_rotation` / `isolation` | core: 1.0 |
| `anti_lateral_flexion` / `isolation` | core: 1.0 |
| `lateral_flexion` / `isolation` | core: 1.0 |
| `rotation` / `isolation` | core: 1.0 |

#### Specialty

| Pattern | Muscles |
|---|---|
| `scapular_elevation` / `isolation` | upper_back: 1.0 |
| `scapular_elevation` / `compound` | upper_back: 1.0, rear_delts: 0.25 |
| `scapular_retraction` / `isolation` | upper_back: 1.0, rear_delts: 0.5 |
| `wrist_flexion` / `isolation` | forearms: 1.0 |
| `wrist_extension` / `isolation` | forearms: 1.0 |
| `grip` / `isolation` | forearms: 1.0 |
| `olympic` / `compound` | quads: 0.5, glutes: 0.5, hamstrings: 0.5, upper_back: 0.5, erectors: 0.5 |
| `plyometric` / `compound` | quads: 0.5, glutes: 0.5 |
| `loaded_carry` / `compound` | forearms: 0.75, core: 0.5, upper_back: 0.5 |

#### Mobility / Prehab (zero volume contribution)

Patterns: `shoulder_mobility`, `hip_mobility`, `spinal_mobility`, `thoracic_extension`, `thoracic_rotation`
→ No exercise_muscles rows inserted. These don't contribute to volume tracking.

### E. Exercise-Specific Overrides

These exercises deviate meaningfully from their pattern default.

| Exercise Name | Override | Rationale |
|---|---|---|
| **Close-Grip Bench Press** | triceps: 1.0, chest: 0.5, front_delts: 0.25 | Narrow grip shifts primary target to triceps |
| **Incline Barbell Press** | chest: 0.75, front_delts: 0.75, triceps: 0.5 | Incline angle increases front delt contribution |
| **Incline Dumbbell Press** | chest: 0.75, front_delts: 0.75, triceps: 0.25 | Same as incline barbell, less triceps (DB stabilization) |
| **Decline Barbell Press** | chest: 1.0, triceps: 0.5, front_delts: 0.25 | Decline reduces front delt, emphasizes chest |
| **Dip / Weighted Dip** | chest: 0.75, triceps: 0.75, front_delts: 0.5 | Co-primary push; more balanced than bench |
| **Behind-the-Neck Press** | side_delts: 0.75, front_delts: 0.75, triceps: 0.5 | Wider abduction plane shifts to side delts |
| **Pull-Up / Weighted Pull-Up** | lats: 1.0, biceps: 0.5, core: 0.25, forearms: 0.25, rear_delts: 0.25 | Hanging adds core engagement vs pulldown |
| **Chin-Up / Weighted Chin-Up** | lats: 1.0, biceps: 0.75, forearms: 0.25, rear_delts: 0.25 | Supination increases biceps contribution |
| **Conventional Deadlift** | glutes: 1.0, hamstrings: 0.75, erectors: 0.75, quads: 0.25, lats: 0.25, forearms: 0.25 | Significant erector + quad involvement from floor |
| **Sumo Deadlift** | glutes: 1.0, quads: 0.75, hamstrings: 0.5, adductors: 0.5, erectors: 0.5 | Wide stance shifts to quads + adductors |
| **Romanian Deadlift** | hamstrings: 1.0, glutes: 0.5, erectors: 0.5 | Limited knee bend = hamstring dominant |
| **Good Morning** | hamstrings: 1.0, erectors: 0.75, glutes: 0.5 | Forward lean = heavy erector demand |
| **Front Squat** | quads: 1.0, glutes: 0.5, core: 0.5, upper_back: 0.25 | Front rack = high core + upper back demand |
| **Box Squat** | quads: 0.75, glutes: 0.75, hamstrings: 0.5, erectors: 0.25 | Pause at bottom recruits more posterior chain |
| **Sumo Squat** | quads: 0.75, glutes: 0.75, adductors: 0.5 | Wide stance loads adductors |
| **Hammer Curl** | biceps: 0.75, forearms: 0.75 | Neutral grip = brachioradialis emphasis |
| **Reverse Curl** | forearms: 1.0, biceps: 0.25 | Pronated grip = forearm dominant |
| **Copenhagen Plank / Dip** | core: 0.75, adductors: 0.75 | Significant adductor loading |
| **Floor Press** | triceps: 0.75, chest: 0.75, front_delts: 0.25 | Reduced ROM shifts toward triceps |
| **45-Degree Back Extension** | erectors: 1.0, glutes: 0.5, hamstrings: 0.5 | Primary erector exercise |
| **Reverse Hyperextension** | glutes: 0.75, hamstrings: 0.5, erectors: 0.75 | Balanced posterior chain |
| **Glute-Ham Raise** | hamstrings: 1.0, glutes: 0.5, erectors: 0.25 | Compound knee flexion + hip extension |
| **Cable Pull-Through** | glutes: 1.0, hamstrings: 0.5, erectors: 0.25 | Hip extension focus |
| **Push Press / Barbell Thruster** | front_delts: 0.75, triceps: 0.5, side_delts: 0.25, quads: 0.25, glutes: 0.25 | Lower body drive component |
| **Landmine Press** | front_delts: 0.75, chest: 0.5, triceps: 0.5, core: 0.25 | Angled pressing + anti-rotation |
| **Muscle-Up** | lats: 0.75, chest: 0.5, triceps: 0.5, biceps: 0.5, core: 0.25 | Compound pull + push transition |
| **Diamond Push-Up** | triceps: 1.0, chest: 0.5, front_delts: 0.25 | Narrow hand position = triceps dominant |
| **Pendlay Row** | upper_back: 1.0, lats: 0.75, rear_delts: 0.5, biceps: 0.5, erectors: 0.25 | Dead-stop adds erector demand |
| **Trap Bar Deadlift** | quads: 0.75, glutes: 0.75, hamstrings: 0.5, erectors: 0.5 | Higher handles = more quad, less hamstring |
| **Block Pull / Rack Pull** | erectors: 1.0, glutes: 0.75, upper_back: 0.5, hamstrings: 0.25, forearms: 0.25 | Partial ROM = erector/lockout focused |
| **Snatch-Grip Deadlift** | upper_back: 0.75, hamstrings: 0.75, glutes: 0.75, erectors: 0.5 | Wide grip = upper back emphasis |
| **Y-Raise** | upper_back: 0.75, rear_delts: 0.75 | Tagged `vertical_push/isolation` but targets lower traps/rear delts — would get wrong template without override |

### F. Volume Landmark Defaults & Stabilizer Budgeting

**The stabilizer budgeting problem:** If core gets 0.25 contribution from squats, rows, presses, and deadlifts, it accumulates ~4-5 effective sets from compound spillover alone. If the audit checks core against MEV (8 sets), it would flag a deficit and suggest 12+ sets of direct ab work — absurd. The compound stimulus IS adequate for most lifters.

**The fix:** Default volume landmarks only include **12 primary muscles** — the muscles that are meaningfully programmed with direct work. Stabilizer-dominant muscles (core, erectors, forearms, adductors) are **tracked in analytics** (their effective volume is displayed) but **excluded from default generator auditing** because they're not in the athlete's landmarks table.

Athletes who want to target these muscles can manually add them to their volume landmarks via the Profile editor. The contribution weights still track reality (squats DO train core a little), but the generator doesn't chase MEV for muscles that most lifters train adequately through compound spillover.

**Default volume landmarks (12 primary muscles):**

| Muscle Group | MEV | MAV-Low | MAV-High | MRV | Notes |
|---|---|---|---|---|---|
| chest | 8 | 12 | 18 | 22 | |
| front_delts | 6 | 8 | 14 | 20 | Gets heavy indirect from pressing |
| side_delts | 8 | 14 | 22 | 28 | Highest volume tolerance |
| rear_delts | 6 | 10 | 18 | 24 | High volume tolerance |
| lats | 8 | 12 | 18 | 22 | |
| upper_back | 6 | 10 | 16 | 22 | Gets indirect from pulling |
| quads | 6 | 10 | 16 | 20 | High systemic fatigue cost |
| hamstrings | 4 | 8 | 14 | 18 | |
| glutes | 4 | 8 | 14 | 18 | |
| biceps | 6 | 10 | 16 | 20 | |
| triceps | 4 | 8 | 14 | 18 | Gets heavy indirect from pressing |
| calves | 8 | 10 | 16 | 20 | |

**Excluded from defaults (tracked in analytics, not audited by generator):**

| Muscle Group | Why excluded | Can opt-in? |
|---|---|---|
| core | Adequately trained through compound spillover for most lifters | Yes — add to landmarks in Profile |
| erectors | High fatigue cost, mostly indirect, rarely needs direct targeting | Yes |
| forearms | Mostly indirect from pulling/gripping | Yes |
| adductors | Mostly indirect from squats/lunges | Yes |

**Audit function behavior:** `audit_volume()` only compares projected volume against muscles that appear in the athlete's landmarks table. If a muscle isn't in landmarks, it's not audited — no MEV/MRV warnings. The analytics view still shows all 16 muscles' effective volume regardless.

---

## Task 19: Author exercise_muscles Seed Data

**Files:**
- Create: `server/db/seed_muscles.py`
- Create: `docs/MUSCLE_ASSIGNMENTS_NOTE.md`
- Create: `tests/test_seed_muscles.py`
- Modify: `server/main.py` (add seed_muscles to startup)
- Modify: `server/services/analytics_service.py:173-184` (replace legacy `_VOLUME_DEFAULTS` with 12 canonical groups, rewrite `get_volume_landmarks` to merge stored+defaults)
- Modify: `server/main.py` (add `_migrate_legacy_landmarks` for `back`/`shoulders` → canonical names)

**Step 1: Write failing test**

```python
# tests/test_seed_muscles.py
import sqlite3
from server.db.schema import init_schema
from server.db.seed_exercises import seed_exercises
from server.db.seed_muscles import seed_muscles, CANONICAL_GROUPS, IDENTIFIER_MAP, EXERCISE_OVERRIDES


def _setup_db():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    init_schema(db)
    seed_exercises(db)
    return db


def test_canonical_groups_count():
    assert len(CANONICAL_GROUPS) == 16


def test_identifier_map_covers_all():
    """Every identifier in the map resolves to a canonical group."""
    for identifier, canonical in IDENTIFIER_MAP.items():
        assert canonical in CANONICAL_GROUPS, f"{identifier} maps to unknown group {canonical}"


def test_seed_populates_exercise_muscles():
    db = _setup_db()
    seed_muscles(db)
    count = db.execute("SELECT COUNT(*) FROM exercise_muscles").fetchone()[0]
    assert count > 500, f"Expected 500+ rows, got {count}"
    db.close()


def test_every_non_mobility_exercise_has_assignments():
    """Every exercise with a volume-relevant pattern has at least 1 muscle assignment."""
    db = _setup_db()
    seed_muscles(db)
    orphans = db.execute("""
        SELECT e.id, e.name, e.movement_pattern FROM exercises e
        LEFT JOIN exercise_muscles em ON e.id = em.exercise_id
        WHERE em.id IS NULL
        AND e.movement_pattern NOT IN (
            'shoulder_mobility', 'hip_mobility', 'spinal_mobility',
            'thoracic_extension', 'thoracic_rotation'
        )
    """).fetchall()
    orphan_names = [r["name"] for r in orphans]
    assert len(orphans) == 0, f"Exercises without muscle assignments: {orphan_names}"
    db.close()


def test_contribution_range():
    """All contribution values are between 0.25 and 1.0."""
    db = _setup_db()
    seed_muscles(db)
    bad = db.execute(
        "SELECT * FROM exercise_muscles WHERE contribution < 0.25 OR contribution > 1.0"
    ).fetchall()
    assert len(bad) == 0, f"Found {len(bad)} rows with contribution outside [0.25, 1.0]"
    db.close()


def test_bench_press_contributions():
    """Spot-check: Barbell Bench Press should have chest=1.0, front_delts=0.5, triceps=0.5."""
    db = _setup_db()
    seed_muscles(db)
    rows = db.execute("""
        SELECT em.muscle_group, em.contribution, em.is_primary
        FROM exercise_muscles em
        JOIN exercises e ON em.exercise_id = e.id
        WHERE e.name = 'Barbell Bench Press'
        ORDER BY em.contribution DESC
    """).fetchall()
    muscles = {r["muscle_group"]: r["contribution"] for r in rows}
    assert muscles["chest"] == 1.0
    assert muscles["front_delts"] == 0.5
    assert muscles["triceps"] == 0.5
    db.close()


def test_conventional_deadlift_override():
    """Spot-check: Conventional DL should have override values (quads 0.25, erectors 0.75)."""
    db = _setup_db()
    seed_muscles(db)
    rows = db.execute("""
        SELECT em.muscle_group, em.contribution
        FROM exercise_muscles em
        JOIN exercises e ON em.exercise_id = e.id
        WHERE e.name = 'Conventional Deadlift'
    """).fetchall()
    muscles = {r["muscle_group"]: r["contribution"] for r in rows}
    assert muscles.get("quads") == 0.25
    assert muscles.get("erectors") == 0.75
    db.close()


def test_rdl_vs_conventional_deadlift():
    """RDL should have higher hamstring and lower quad/erector than conventional."""
    db = _setup_db()
    seed_muscles(db)
    rdl = dict(db.execute("""
        SELECT em.muscle_group, em.contribution FROM exercise_muscles em
        JOIN exercises e ON em.exercise_id = e.id WHERE e.name = 'Romanian Deadlift'
    """).fetchall())
    conv = dict(db.execute("""
        SELECT em.muscle_group, em.contribution FROM exercise_muscles em
        JOIN exercises e ON em.exercise_id = e.id WHERE e.name = 'Conventional Deadlift'
    """).fetchall())
    # RDL: hamstrings should be >= conventional
    assert rdl.get("hamstrings", 0) >= conv.get("hamstrings", 0)
    # Conventional: quads should be > RDL (RDL has no quad contribution)
    assert conv.get("quads", 0) > rdl.get("quads", 0)
    db.close()


def test_pullup_has_core_pulldown_does_not():
    """Pull-Up should have core contribution; Lat Pulldown should not."""
    db = _setup_db()
    seed_muscles(db)
    pu = db.execute("""
        SELECT em.muscle_group FROM exercise_muscles em
        JOIN exercises e ON em.exercise_id = e.id WHERE e.name = 'Pull-Up'
    """).fetchall()
    pd = db.execute("""
        SELECT em.muscle_group FROM exercise_muscles em
        JOIN exercises e ON em.exercise_id = e.id WHERE e.name = 'Lat Pulldown'
    """).fetchall()
    pu_muscles = [r["muscle_group"] for r in pu]
    pd_muscles = [r["muscle_group"] for r in pd]
    assert "core" in pu_muscles
    assert "core" not in pd_muscles
    db.close()


def test_all_overrides_match_real_exercises():
    """Every key in EXERCISE_OVERRIDES must match an exercise name in the database."""
    db = _setup_db()
    exercise_names = {r["name"] for r in db.execute("SELECT name FROM exercises").fetchall()}
    unmatched = [name for name in EXERCISE_OVERRIDES if name not in exercise_names]
    assert len(unmatched) == 0, f"Override keys with no matching exercise: {unmatched}"
    db.close()


def test_idempotent():
    """Running seed_muscles twice should not duplicate rows."""
    db = _setup_db()
    seed_muscles(db)
    count1 = db.execute("SELECT COUNT(*) FROM exercise_muscles").fetchone()[0]
    seed_muscles(db)
    count2 = db.execute("SELECT COUNT(*) FROM exercise_muscles").fetchone()[0]
    assert count1 == count2
    db.close()
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/caseytalbot/Desktop/IRONLOG && python -m pytest tests/test_seed_muscles.py -v`
Expected: ImportError (seed_muscles doesn't exist yet)

**Step 3: Create `server/db/seed_muscles.py`**

The seed function uses the pattern templates and exercise overrides defined in Design Foundations sections D and E above. Full implementation:

```python
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
    # These exercises have (pattern, category) combos that would resolve to wrong muscles
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
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/caseytalbot/Desktop/IRONLOG && python -m pytest tests/test_seed_muscles.py -v`
Expected: All 11 tests PASS

**Step 5: Update `server/main.py` startup**

Add `seed_muscles` import and call after `seed_exercises`:

```python
# server/main.py — add to imports
from server.db.seed_muscles import seed_muscles

# In startup():
    seed_exercises(db)
    seed_muscles(db)  # <-- add this line
```

**Step 6: Update `server/services/analytics_service.py` — defaults, merge logic, migration**

Three changes in this file:

**6a. Replace `_VOLUME_DEFAULTS` (line 173-184) with 12 primary muscle defaults:**

```python
_VOLUME_DEFAULTS = [
    ("chest", 8, 12, 18, 22),
    ("front_delts", 6, 8, 14, 20),
    ("side_delts", 8, 14, 22, 28),
    ("rear_delts", 6, 10, 18, 24),
    ("lats", 8, 12, 18, 22),
    ("upper_back", 6, 10, 16, 22),
    ("quads", 6, 10, 16, 20),
    ("hamstrings", 4, 8, 14, 18),
    ("glutes", 4, 8, 14, 18),
    ("biceps", 6, 10, 16, 20),
    ("triceps", 4, 8, 14, 18),
    ("calves", 8, 10, 16, 20),
]
```

**6b. Rewrite `get_volume_landmarks` to merge stored with defaults (not all-or-nothing):**

The current implementation returns ALL stored landmarks OR ALL defaults. This breaks when defaults expand from 10 → 12 groups — any athlete with saved landmarks loses the new groups. Fix: merge stored landmarks with defaults, preserving user customizations while adding new default groups.

```python
def get_volume_landmarks(db, athlete_id: int) -> list[dict]:
    """Return volume landmarks: stored values merged with defaults for missing groups."""
    stored = {
        r["muscle_group"]: dict(r)
        for r in db.execute(
            "SELECT * FROM volume_landmarks WHERE athlete_id = ?", [athlete_id]
        ).fetchall()
    }

    result = []
    default_groups = set()
    for d in _VOLUME_DEFAULTS:
        group = d[0]
        default_groups.add(group)
        if group in stored:
            result.append(stored[group])
        else:
            result.append({
                "muscle_group": group, "mev": d[1],
                "mav_low": d[2], "mav_high": d[3], "mrv": d[4],
            })

    # Include any user-added groups not in defaults (e.g. core, erectors opt-in)
    for group, data in stored.items():
        if group not in default_groups:
            result.append(data)

    return result
```

**6c. Add legacy landmark migration to startup (in `server/main.py`, after seed_muscles):**

The old `_VOLUME_DEFAULTS` used `back` and `shoulders`. Any athlete who saved landmarks with those names needs them renamed. Add a one-time migration:

```python
def _migrate_legacy_landmarks(db):
    """Rename legacy muscle group names in volume_landmarks."""
    # back → split into lats + upper_back
    legacy_back = db.execute(
        "SELECT * FROM volume_landmarks WHERE muscle_group = 'back'"
    ).fetchall()
    for row in legacy_back:
        # Create lats and upper_back entries with the same values
        for new_group in ("lats", "upper_back"):
            db.execute(
                """INSERT OR IGNORE INTO volume_landmarks
                   (athlete_id, muscle_group, mev, mav_low, mav_high, mrv)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                [row["athlete_id"], new_group, row["mev"],
                 row["mav_low"], row["mav_high"], row["mrv"]],
            )
        db.execute(
            "DELETE FROM volume_landmarks WHERE id = ?", [row["id"]]
        )

    # shoulders → split into front_delts + side_delts + rear_delts
    legacy_shoulders = db.execute(
        "SELECT * FROM volume_landmarks WHERE muscle_group = 'shoulders'"
    ).fetchall()
    for row in legacy_shoulders:
        for new_group in ("front_delts", "side_delts", "rear_delts"):
            db.execute(
                """INSERT OR IGNORE INTO volume_landmarks
                   (athlete_id, muscle_group, mev, mav_low, mav_high, mrv)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                [row["athlete_id"], new_group, row["mev"],
                 row["mav_low"], row["mav_high"], row["mrv"]],
            )
        db.execute(
            "DELETE FROM volume_landmarks WHERE id = ?", [row["id"]]
        )

    db.commit()
```

Add to `server/main.py` startup after `seed_muscles(db)`:

```python
    _migrate_legacy_landmarks(db)
```

**Step 7: Create `docs/MUSCLE_ASSIGNMENTS_NOTE.md`**

Document: the 16 canonical groups, identifier mapping, contribution scale, pattern template methodology, override rationale, and how to extend for new exercises. Reference this plan's Design Foundations sections A-E.

**Step 8: Commit**

```bash
git add server/db/seed_muscles.py tests/test_seed_muscles.py docs/MUSCLE_ASSIGNMENTS_NOTE.md
git add server/main.py server/services/analytics_service.py
git commit -m "feat: exercise_muscles seed data with contribution factors, canonical volume landmarks"
```

---

## Task 20: Per-Muscle Volume Analytics

**Files:**
- Delete: `server/algorithms/volume.py` (dead code — zero callers before or after this change)
- Modify: `server/services/analytics_service.py:149-164` (rewrite muscle_volume query)
- Modify: `js/views/analytics.js` (update muscle chart for 16 groups)
- Modify: `js/views/profile.js` (update volume landmarks section for 16 groups)

**Why delete `volume.py`:** The current `aggregate_muscle_volume` function has zero callers — the analytics service does its own inline SQL for `muscle_volume`. Rewriting it would create differently-shaped dead code. The analytics service SQL aggregation is correct: the database should do the grouping, not Python. Volume budgeting for the generator (Task 21) has its own purpose-built module `volume_budget.py`. There is no need for a middle-layer algorithm file.

**Step 1: Delete `server/algorithms/volume.py`**

```bash
rm server/algorithms/volume.py
```

**Step 2: Rewrite `analytics_service.py` muscle_volume query**

Replace the `elif metric == "muscle_volume":` block (lines 149-164) with a query that joins through `exercise_muscles`:

```python
    elif metric == "muscle_volume":
        rows = db.execute(
            """
            SELECT em.muscle_group,
                   ROUND(SUM(em.contribution), 1) as effective_sets,
                   ROUND(SUM(sl.weight * sl.reps * em.contribution)) as weighted_volume
            FROM set_logs sl
            JOIN workout_logs wl ON sl.workout_log_id = wl.id
            JOIN exercise_muscles em ON sl.exercise_id = em.exercise_id
            WHERE wl.athlete_id = ? AND wl.date >= date('now', ?)
            AND sl.set_type = 'working'
            GROUP BY em.muscle_group
            ORDER BY effective_sets DESC
            """,
            [athlete_id, f"-{days} days"],
        ).fetchall()
        return [
            {
                "muscle_group": r["muscle_group"],
                "total_sets": r["effective_sets"],
                "total_volume": r["weighted_volume"],
            }
            for r in rows
        ]
```

**Step 3: Frontend — update analytics.js muscle chart**

The `renderMuscleChart` function already reads `musclePoints[].muscle_group` and `sets`/`volume`. The data shape hasn't changed — just the values are now accurate. The chart will automatically display all 16 muscle groups instead of CSV-concatenated strings.

Verify: Labels should now show "Chest", "Front Delts", "Lats", etc. instead of "chest,anterior_deltoid,triceps".

The `formatPattern` function in `js/lib/format.js` already converts underscores to spaces and capitalizes each word — this works correctly for canonical names like `front_delts` → "Front Delts". No changes needed.

**Step 4: Run all tests**

Run: `cd /Users/caseytalbot/Desktop/IRONLOG && python -m pytest tests/ -v`
Expected: All pass (14 existing + 11 seed_muscles tests)

**Step 5: Manual verification**

1. Start backend: `./run.sh`
2. Serve frontend: `python3 -m http.server 3000`
3. Open `http://localhost:3000#analytics`
4. Verify muscle volume chart shows 16 individual groups (not CSV strings)
5. Verify volume landmarks editor shows 12 default groups (plus any user-added)
6. Test time range selector (7d, 30d, 90d, All)

**Step 6: Commit**

```bash
git rm server/algorithms/volume.py
git add server/services/analytics_service.py
git add js/views/analytics.js
git commit -m "feat: per-muscle volume analytics with contribution-weighted sets"
```

---

## Task 21: Enhanced Generator with Volume Budgeting

**Files:**
- Create: `server/algorithms/volume_budget.py` (pure function: calculate + audit projected volume)
- Modify: `server/services/program_service.py` (add volume audit after generation, return volume_summary in dict)
- Test: `tests/test_volume_budget.py`
- Modify: `js/views/program-wizard.js` or `js/views/program-detail.js` (display volume projections)

**Note:** `server/models/program.py` defines `ProgramGenerate` (input model). The generation response is a plain dict returned from `program_service.py` — no response model exists or is needed. We modify the return dict directly.

**Step 1: Write failing test for volume budget algorithm**

```python
# tests/test_volume_budget.py
from server.algorithms.volume_budget import calculate_projected_volume, audit_volume


def test_calculate_projected_volume():
    """Project weekly volume from program exercises and muscle contributions."""
    # Simulates 2 sessions/week, each with exercises and their muscle data
    program_exercises = [
        # Session 1: Bench 4 sets, Row 4 sets
        {"sets_prescribed": 4, "muscles": [
            {"muscle_group": "chest", "contribution": 1.0},
            {"muscle_group": "front_delts", "contribution": 0.5},
            {"muscle_group": "triceps", "contribution": 0.5},
        ]},
        {"sets_prescribed": 4, "muscles": [
            {"muscle_group": "upper_back", "contribution": 1.0},
            {"muscle_group": "lats", "contribution": 0.75},
            {"muscle_group": "rear_delts", "contribution": 0.5},
            {"muscle_group": "biceps", "contribution": 0.5},
        ]},
    ]
    result = calculate_projected_volume(program_exercises)
    assert result["chest"] == 4.0
    assert result["front_delts"] == 2.0
    assert result["triceps"] == 2.0
    assert result["upper_back"] == 4.0
    assert result["lats"] == 3.0
    assert result["biceps"] == 2.0


def test_audit_volume_flags_red_issues():
    """Audit should flag muscles below MEV (red) or above MRV (red)."""
    projected = {"chest": 4.0, "side_delts": 0.0, "quads": 25.0}
    landmarks = {
        "chest": {"mev": 8, "mav_low": 12, "mav_high": 18, "mrv": 22},
        "side_delts": {"mev": 8, "mav_low": 14, "mav_high": 22, "mrv": 28},
        "quads": {"mev": 6, "mav_low": 10, "mav_high": 16, "mrv": 20},
    }
    audit = audit_volume(projected, landmarks)
    assert any(a["muscle"] == "chest" and a["issue"] == "below_mev" for a in audit)
    assert any(a["muscle"] == "side_delts" and a["issue"] == "below_mev" for a in audit)
    assert any(a["muscle"] == "quads" and a["issue"] == "above_mrv" for a in audit)


def test_audit_volume_flags_yellow_issues():
    """Audit should flag muscles below MAV-low (yellow) or above MAV-high (yellow)."""
    projected = {"chest": 9.0, "quads": 19.0}  # between MEV-MAV_low, between MAV_high-MRV
    landmarks = {
        "chest": {"mev": 8, "mav_low": 12, "mav_high": 18, "mrv": 22},
        "quads": {"mev": 6, "mav_low": 10, "mav_high": 16, "mrv": 20},
    }
    audit = audit_volume(projected, landmarks)
    assert any(a["muscle"] == "chest" and a["issue"] == "below_mav" for a in audit)
    assert any(a["muscle"] == "quads" and a["issue"] == "above_mav" for a in audit)


def test_audit_volume_within_range():
    """Muscles within MAV range should have no issues."""
    projected = {"chest": 14.0}
    landmarks = {"chest": {"mev": 8, "mav_low": 12, "mav_high": 18, "mrv": 22}}
    audit = audit_volume(projected, landmarks)
    assert len(audit) == 0
```

**Step 2: Create `server/algorithms/volume_budget.py`**

```python
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
```

**Step 3: Wire into `program_service.py`**

After generating sessions in `generate_program()`, add a volume audit step:

```python
# After the split-specific builder (_generate_upper_lower, etc.) and before db.commit():

# --- Volume audit ---
volume_summary = _calculate_program_volume(db, program_id)
# Store summary in the program's config JSON
config["volume_summary"] = volume_summary
db.execute(
    "UPDATE programs SET config = ? WHERE id = ?",
    [json.dumps(config), program_id],
)
db.commit()
return {"id": program_id, "name": program_name, "status": "generated",
        "volume_summary": volume_summary}
```

Add the private helper:

```python
def _calculate_program_volume(db, program_id):
    """Calculate projected weekly volume for a generated program."""
    from server.algorithms.volume_budget import calculate_projected_volume, audit_volume

    exercises = db.execute("""
        SELECT pe.sets_prescribed, pe.exercise_id
        FROM program_exercises pe
        JOIN program_sessions ps ON pe.session_id = ps.id
        WHERE ps.program_id = ?
    """, [program_id]).fetchall()

    program_exercises = []
    for ex in exercises:
        muscles = db.execute("""
            SELECT muscle_group, contribution FROM exercise_muscles
            WHERE exercise_id = ?
        """, [ex["exercise_id"]]).fetchall()
        program_exercises.append({
            "sets_prescribed": ex["sets_prescribed"],
            "muscles": [dict(m) for m in muscles],
        })

    projected = calculate_projected_volume(program_exercises)

    # Get athlete landmarks (use defaults if not set)
    athlete_id = db.execute(
        "SELECT athlete_id FROM programs WHERE id = ?", [program_id]
    ).fetchone()["athlete_id"]

    from server.services.analytics_service import get_volume_landmarks
    landmarks_list = get_volume_landmarks(db, athlete_id)
    landmarks = {l["muscle_group"]: l for l in landmarks_list}

    audit = audit_volume(projected, landmarks)

    return {
        "projected": {k: round(v, 1) for k, v in sorted(projected.items())},
        "audit": audit,
    }
```

**Step 4: Run tests**

Run: `cd /Users/caseytalbot/Desktop/IRONLOG && python -m pytest tests/ -v`
Expected: All pass

**Step 5: Frontend — display volume projections**

In the program detail view or the program wizard completion step, display the volume summary returned by the generator:

- Show a table of muscle groups with projected weekly sets
- Color-code: green (within MAV), yellow (below MAV-low or above MAV-high), red (below MEV or above MRV)
- Show audit warnings for muscles outside healthy ranges

This is a frontend display change in `js/views/program-detail.js` and/or `js/views/program-wizard.js`.

**Step 6: Manual verification**

1. Generate a new program via the wizard
2. Verify the API response includes `volume_summary` with `projected` and `audit`
3. Verify the program detail view shows volume projections
4. Verify audit flags make sense (e.g., if no lateral raises in program, side_delts below MEV)

**Step 7: Commit**

```bash
git add server/algorithms/volume_budget.py tests/test_volume_budget.py
git add server/services/program_service.py
git add js/views/program-detail.js js/views/program-wizard.js
git commit -m "feat: volume-budgeted generator with MEV/MRV auditing"
```

---

## Verification Checklist

### Backend
- [ ] `python -m pytest tests/ -v` — all tests pass (14 existing + 11 seed_muscles + 4 volume_budget = 29)
- [ ] `./run.sh` starts cleanly, no import errors
- [ ] `server/algorithms/volume.py` does NOT exist (deleted — was dead code)
- [ ] `curl http://localhost:8000/exercises/1` — exercise still loads
- [ ] `curl http://localhost:8000/analytics/muscle_volume?athlete_id=1&days=30` — returns canonical muscle groups (not CSV strings)
- [ ] `curl http://localhost:8000/analytics/volume-landmarks?athlete_id=1` — returns 12 default groups with correct canonical names
- [ ] `curl -X POST http://localhost:8000/programs/generate -H 'Content-Type: application/json' -d '{"athlete_id":1,"goal":"hypertrophy","phase":"accumulation","split":"upper_lower","weeks":4,"days_per_week":4}'` — returns volume_summary with projected + audit (audit includes severity field)

### Frontend
- [ ] Analytics → muscle volume chart shows individual muscle groups (not CSV concatenated strings)
- [ ] Analytics → volume landmarks editor shows 12 default groups (not 10 legacy groups)
- [ ] Profile → volume landmarks section shows 12 default groups
- [ ] Program wizard → after generation, shows volume projections
- [ ] Program detail → shows volume audit warnings with red/yellow color coding

### Database
- [ ] `SELECT COUNT(*) FROM exercise_muscles` → 500+ rows
- [ ] `SELECT COUNT(DISTINCT muscle_group) FROM exercise_muscles` → 16 (all canonical groups represented)
- [ ] `SELECT * FROM exercise_muscles WHERE exercise_id = (SELECT id FROM exercises WHERE name = 'Barbell Bench Press')` → 3 rows (chest 1.0, front_delts 0.5, triceps 0.5)
- [ ] `SELECT * FROM volume_landmarks WHERE muscle_group IN ('back', 'shoulders')` → 0 rows (legacy names migrated)

### Data Integrity
- [ ] Every key in EXERCISE_OVERRIDES matches an exercise name in `exercises` table (test enforces this)
- [ ] Every non-mobility exercise has at least 1 muscle assignment (test enforces this)
- [ ] Y-Raise gets upper_back + rear_delts (not front_delts from wrong template fallback)
- [ ] No `compound_kettlebell` category exists in templates (removed — dead code)

### Documentation
- [ ] `docs/MUSCLE_ASSIGNMENTS_NOTE.md` exists and documents all design decisions


If you need specific details from before exiting plan mode (like exact code snippets, error messages, or content you generated), read the full transcript at: /Users/caseytalbot/.claude/projects/-Users-caseytalbot/caf35ac9-bceb-4b53-8883-bb363d036c5c.jsonl
