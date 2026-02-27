# Exercise-Muscle Assignment System

Reference implementation: `server/db/seed_muscles.py`

This document describes the data model behind IRONLOG's per-muscle volume tracking. The system maps every exercise to one or more of 16 canonical muscle groups with weighted contribution factors, enabling accurate weekly volume aggregation per muscle.

---

## 1. Canonical Muscle Groups

IRONLOG tracks 16 muscle groups. Each group has a canonical identifier (used in code and the `exercise_muscles.muscle_group` column) and zero or more taxonomy aliases that map onto it. Aliases appear in exercise science literature and third-party datasets; the seed script normalises all of them to the canonical name before inserting.

| # | Canonical ID | Taxonomy Aliases |
|---|---|---|
| 1 | `chest` | `chest`, `upper_chest`, `lower_chest` |
| 2 | `front_delts` | `anterior_deltoid` |
| 3 | `side_delts` | `lateral_deltoid` |
| 4 | `rear_delts` | `rear_deltoid` |
| 5 | `lats` | (none) |
| 6 | `upper_back` | `rhomboids`, `traps`, `upper_traps`, `lower_traps`, `upper_back` |
| 7 | `quads` | (none) |
| 8 | `hamstrings` | (none) |
| 9 | `glutes` | `glutes`, `glute_medius`, `glute_minimus` |
| 10 | `biceps` | `biceps`, `brachialis`, `biceps_long_head`, `biceps_short_head` |
| 11 | `triceps` | `triceps`, `triceps_long_head` |
| 12 | `forearms` | `forearms`, `brachioradialis`, `forearm_flexors`, `forearm_extensors` |
| 13 | `calves` | `calves`, `gastrocnemius`, `soleus` |
| 14 | `core` | `core`, `rectus_abdominis`, `obliques`, `hip_flexors`, `serratus_anterior` |
| 15 | `erectors` | (none) |
| 16 | `adductors` | (none) |

The `volume_landmarks` table uses these same 16 identifiers.

---

## 2. Contribution Scale

Every `exercise_muscles` row carries a `contribution` value between 0.25 and 1.0. This represents how much a single working set of that exercise "counts" toward volume for a given muscle.

| Value | Label | Meaning |
|---|---|---|
| **1.0** | Primary mover | The muscle is the main target. Example: chest on bench press. |
| **0.75** | Major synergist | A significant secondary driver of force. Example: triceps on bench press. |
| **0.5** | Significant synergist | Meaningful contribution but not the focus. Example: front delts on bench press. |
| **0.25** | Minor synergist | Stabiliser or weak contributor. This is the floor -- contributions below 0.25 are not recorded. |

The floor of 0.25 exists to keep the data clean: muscles with negligible involvement (e.g., forearms during a squat) get no row rather than a near-zero contribution that clutters queries.

---

## 3. Two-Layer Assignment System

Muscle assignments use a two-layer strategy: **pattern templates** provide sensible defaults; **exercise-specific overrides** handle biomechanical exceptions.

### Layer 1: Pattern Templates

Each `(movement_pattern, category)` pair has a default set of muscle-group contributions. For example, every exercise tagged `horizontal_push / compound` inherits the same chest/triceps/front-delt profile unless overridden. This covers the majority of the 292 exercises in the taxonomy without per-exercise authoring.

Pattern templates live in a `PATTERN_TEMPLATES` dict in `server/db/seed_muscles.py`.

### Layer 2: Exercise-Specific Overrides

When an exercise's biomechanics differ meaningfully from its pattern template, it gets an entry in `EXERCISE_OVERRIDES`. Overrides use **full replace semantics**: if an exercise appears in the overrides dict, its entire muscle assignment comes from the override. The pattern template is ignored completely. There is no merging of template and override.

This prevents subtle bugs. You never need to reason about "which muscles came from the template and which from the override." Either the template applies in full, or the override applies in full.

Exercise overrides live in an `EXERCISE_OVERRIDES` dict in `server/db/seed_muscles.py`, keyed by exercise name.

### Resolution Order

```
1. Check EXERCISE_OVERRIDES[exercise.name]
   → If found, use those assignments (full replace). Done.
2. Fall back to PATTERN_TEMPLATES[(exercise.movement_pattern, exercise.category)]
   → If found, use those assignments. Done.
3. No match → exercise gets zero exercise_muscles rows (logged as warning during seed).
```

---

## 4. Volume Formula

The per-muscle weekly volume calculation is:

```
weekly_sets_per_muscle[m] = SUM(contribution)
    for each working set logged in the past 7 days
    where the set's exercise has an exercise_muscles row for muscle_group = m
```

In SQL form (via `analytics_service.py`):

```sql
SELECT em.muscle_group,
       SUM(em.contribution) AS weekly_sets
FROM set_logs sl
JOIN workout_logs wl ON sl.workout_log_id = wl.id
JOIN exercise_muscles em ON sl.exercise_id = em.exercise_id
WHERE sl.set_type = 'working'
  AND wl.date >= date('now', '-7 days')
GROUP BY em.muscle_group
```

Only **working sets** count. Warmup, backoff, drop, and cluster sets are excluded. This matches the convention in hypertrophy research where "hard sets" (sets taken within a few reps of failure) drive adaptation.

A bench press set with `contribution = 1.0` for chest, `0.75` for triceps, and `0.5` for front delts contributes 1.0 set toward chest volume, 0.75 set toward triceps volume, and 0.5 set toward front delt volume.

---

## 5. Mobility Patterns Excluded

Exercises with the following movement patterns produce **no `exercise_muscles` rows**:

- `shoulder_mobility`
- `hip_mobility`
- `spinal_mobility`
- `thoracic_extension`
- `thoracic_rotation`

These are warm-up and corrective drills. They do not load muscles in a way that accumulates meaningful hypertrophic or strength volume. Including them would inflate volume counts and distort the generator's volume budgeting. They exist in the exercise taxonomy for logging purposes but are invisible to the muscle-tracking system.

---

## 6. How to Add a New Exercise

### Standard case (template covers it)

1. Add the exercise tuple to `server/db/seed_exercises.py` with accurate `movement_pattern` and `category` values.
2. Run the seed. The muscle assignment system will look up `PATTERN_TEMPLATES[(movement_pattern, category)]` and auto-generate the `exercise_muscles` rows.
3. Verify the inherited assignments make sense for the exercise's biomechanics.

### Exception case (biomechanics differ from template)

1. Add the exercise to `seed_exercises.py` as above.
2. Add an entry to `EXERCISE_OVERRIDES` in `server/db/seed_muscles.py`, keyed by the exercise name. Specify every muscle group and its contribution. The template will be skipped entirely.
3. Run the seed.

### Example

A close-grip bench press is tagged `horizontal_push / compound`, which by default assigns chest=1.0, triceps=0.75, front_delts=0.5. But the close grip shifts emphasis to triceps, so an override might be:

```python
EXERCISE_OVERRIDES = {
    "Close-Grip Bench Press": {
        "triceps": (True, 1.0),
        "chest": (False, 0.75),
        "front_delts": (False, 0.5),
    },
    # ...
}
```

Full replace: the entry above is the complete muscle assignment. Nothing from the horizontal_push template leaks in.

---

## 7. Volume Landmarks

The `volume_landmarks` table stores per-muscle thresholds that the generator and analytics views use to assess whether weekly volume is adequate, optimal, or excessive.

| Landmark | Column | Meaning |
|---|---|---|
| MEV | `mev` | Minimum Effective Volume -- fewest weekly sets to maintain muscle. |
| MAV Low | `mav_low` | Low end of the Maximum Adaptive Volume range. |
| MAV High | `mav_high` | High end of the Maximum Adaptive Volume range. |
| MRV | `mrv` | Maximum Recoverable Volume -- ceiling before recovery breaks down. |

### Primary vs. Stabiliser Muscles

The 16 canonical muscles are split into two tiers for generator auditing:

**12 primary muscles** (default volume landmarks, audited by the generator):
- chest, front_delts, side_delts, rear_delts, lats, upper_back, quads, hamstrings, glutes, biceps, triceps, calves

**4 stabiliser muscles** (tracked but excluded from generator auditing by default):
- core, erectors, forearms, adductors

The stabiliser muscles accumulate meaningful volume as synergists across many compound movements. They are tracked in the analytics view so users can see their weekly volume, and they have landmarks in `volume_landmarks` that the user can edit. However, the program generator does not audit them by default -- it will not add or remove exercises to hit MEV/MRV targets for these four groups. This prevents the generator from bloating programs with isolation work for muscles that already get sufficient indirect stimulation.

Users who specifically want to bring up a stabiliser group (e.g., adding dedicated core work) can do so manually or adjust generator settings when that feature is implemented.

---

## Data Integrity Notes

- The `exercise_muscles` table has a `UNIQUE(exercise_id, muscle_group)` constraint. An exercise cannot have two contribution entries for the same muscle.
- The `is_primary` column (INTEGER 0 or 1) marks whether the muscle is a primary mover for that exercise. This is informational and used in UI display. The `contribution` value is what drives volume math.
- Deleting an exercise cascades to its `exercise_muscles` rows (FK with `ON DELETE CASCADE`).
- The seed script is idempotent: it checks for existing rows before inserting and can be re-run safely.
