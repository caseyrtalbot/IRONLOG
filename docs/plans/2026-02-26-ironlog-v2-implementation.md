# IRONLOG v2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restructure IRONLOG from a monolithic CGI app into a deeply modular FastAPI + vanilla ES modules architecture, preserving all existing functionality.

**Architecture:** FastAPI backend (SQLite, raw SQL, pure-function algorithms) served separately from a static vanilla JS frontend split into ES modules. Strict dependency direction enforced across all layers.

**Tech Stack:** Python 3 / FastAPI / SQLite / Vanilla JS (ES modules) / Chart.js / CSS custom properties

**Note:** The `exercise_muscles` relation table and enhanced generator with volume budgeting are Phase 4 work. These will be designed from first principles when we reach that stage — not ported from any external source.

---

## Phase 1: Backend

### Task 1: Project scaffolding

**Files:**
- Create: `server/__init__.py`
- Create: `server/db/__init__.py`
- Create: `server/models/__init__.py`
- Create: `server/routes/__init__.py`
- Create: `server/services/__init__.py`
- Create: `server/algorithms/__init__.py`
- Create: `requirements.txt`
- Create: `run.sh`

**Step 1: Create requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
pydantic==2.9.0
pytest==8.3.0
```

**Step 2: Create directory structure with __init__.py files**

Every `__init__.py` is empty. They exist only to make Python recognize the directories as packages.

**Step 3: Create run.sh**

```bash
#!/bin/bash
cd "$(dirname "$0")"
uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

**Step 4: Install dependencies and verify**

Run: `pip install -r requirements.txt`
Run: `chmod +x run.sh`

**Step 5: Commit**

```bash
git add requirements.txt run.sh server/
git commit -m "scaffold: backend directory structure and dependencies"
```

---

### Task 2: Config and database connection

**Files:**
- Create: `server/config.py`
- Create: `server/dependencies.py`
- Create: `server/db/connection.py`

**Step 1: Create server/config.py**

```python
import os

DB_PATH = os.environ.get("IRONLOG_DB", "ironlog.db")
CORS_ORIGINS = os.environ.get("IRONLOG_CORS", "*").split(",")
```

**Step 2: Create server/db/connection.py**

```python
import sqlite3
from server.config import DB_PATH


def get_connection():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    return db
```

**Step 3: Create server/dependencies.py**

```python
from server.db.connection import get_connection


def get_db():
    db = get_connection()
    try:
        yield db
    finally:
        db.close()
```

**Step 4: Commit**

```bash
git add server/config.py server/dependencies.py server/db/connection.py
git commit -m "feat: config, db connection, and FastAPI dependency injection"
```

---

### Task 3: Database schema

**Files:**
- Create: `server/db/schema.py`

**Step 1: Create server/db/schema.py**

Extract the schema from `cgi-bin/api.py:29-169` — the 9 existing CREATE TABLE statements plus the 2 new tables (`exercise_muscles` and `program_phases`), plus all indexes. The `exercises` table keeps `primary_muscles` and `secondary_muscles` columns for now (they'll coexist with `exercise_muscles` until Phase 4 migration is complete).

The `programs` table keeps the `config` column for now but adds `program_phases` as the forward-looking structure.

```python
SCHEMA = """
CREATE TABLE IF NOT EXISTS athletes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER,
    body_weight REAL,
    body_fat_pct REAL,
    training_age INTEGER DEFAULT 0,
    experience_level TEXT DEFAULT 'intermediate'
        CHECK(experience_level IN ('beginner','intermediate','advanced','elite')),
    primary_goal TEXT DEFAULT 'strength'
        CHECK(primary_goal IN ('strength','hypertrophy','power','endurance','general')),
    training_days_per_week INTEGER DEFAULT 4,
    session_duration_min INTEGER DEFAULT 75,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    movement_pattern TEXT NOT NULL,
    primary_muscles TEXT NOT NULL,
    secondary_muscles TEXT DEFAULT '',
    equipment TEXT DEFAULT 'barbell',
    bilateral INTEGER DEFAULT 1,
    complexity INTEGER DEFAULT 2 CHECK(complexity BETWEEN 1 AND 5),
    fatigue_rating INTEGER DEFAULT 3 CHECK(fatigue_rating BETWEEN 1 AND 5),
    mev_sets_per_week INTEGER DEFAULT 6,
    mrv_sets_per_week INTEGER DEFAULT 20,
    notes TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS exercise_muscles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise_id INTEGER NOT NULL,
    muscle_group TEXT NOT NULL,
    is_primary INTEGER DEFAULT 1,
    contribution REAL DEFAULT 0.5,
    FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE,
    UNIQUE(exercise_id, muscle_group)
);

CREATE TABLE IF NOT EXISTS programs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    athlete_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    phase TEXT NOT NULL
        CHECK(phase IN ('accumulation','intensification','realization','deload','transition')),
    goal TEXT NOT NULL
        CHECK(goal IN ('strength','hypertrophy','power','endurance','general')),
    mesocycle_weeks INTEGER DEFAULT 4,
    current_week INTEGER DEFAULT 1,
    status TEXT DEFAULT 'active'
        CHECK(status IN ('active','completed','paused')),
    config TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);

CREATE TABLE IF NOT EXISTS program_phases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id INTEGER NOT NULL,
    phase_order INTEGER NOT NULL,
    phase_type TEXT NOT NULL
        CHECK(phase_type IN ('accumulation','intensification','realization','deload')),
    duration_weeks INTEGER DEFAULT 4,
    volume_multiplier REAL DEFAULT 1.0,
    intensity_target REAL,
    rpe_target REAL,
    FOREIGN KEY (program_id) REFERENCES programs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS program_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id INTEGER NOT NULL,
    day_number INTEGER NOT NULL,
    name TEXT NOT NULL,
    focus TEXT DEFAULT '',
    session_order INTEGER DEFAULT 1,
    FOREIGN KEY (program_id) REFERENCES programs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS program_exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL,
    exercise_order INTEGER DEFAULT 1,
    superset_group TEXT DEFAULT NULL,
    sets_prescribed INTEGER NOT NULL,
    reps_prescribed TEXT NOT NULL,
    intensity_type TEXT DEFAULT 'rpe'
        CHECK(intensity_type IN ('rpe','rir','percent_rm','rpe_range')),
    intensity_value TEXT NOT NULL,
    rest_seconds INTEGER DEFAULT 120,
    tempo TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    FOREIGN KEY (session_id) REFERENCES program_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (exercise_id) REFERENCES exercises(id)
);

CREATE TABLE IF NOT EXISTS workout_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    athlete_id INTEGER NOT NULL,
    program_id INTEGER,
    session_id INTEGER,
    date TEXT NOT NULL,
    duration_min INTEGER,
    notes TEXT DEFAULT '',
    session_rpe REAL,
    body_weight REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (athlete_id) REFERENCES athletes(id),
    FOREIGN KEY (program_id) REFERENCES programs(id)
);

CREATE TABLE IF NOT EXISTS set_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_log_id INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL,
    set_number INTEGER NOT NULL,
    set_type TEXT DEFAULT 'working'
        CHECK(set_type IN ('warmup','working','backoff','amrap','drop','cluster')),
    weight REAL,
    reps INTEGER,
    rpe REAL,
    rir INTEGER,
    tempo TEXT DEFAULT '',
    rest_seconds INTEGER,
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workout_log_id) REFERENCES workout_logs(id) ON DELETE CASCADE,
    FOREIGN KEY (exercise_id) REFERENCES exercises(id)
);

CREATE TABLE IF NOT EXISTS one_rep_maxes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    athlete_id INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL,
    estimated_1rm REAL NOT NULL,
    method TEXT DEFAULT 'epley',
    source_weight REAL,
    source_reps INTEGER,
    source_rpe REAL,
    date TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (athlete_id) REFERENCES athletes(id),
    FOREIGN KEY (exercise_id) REFERENCES exercises(id)
);

CREATE TABLE IF NOT EXISTS volume_landmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    athlete_id INTEGER NOT NULL,
    muscle_group TEXT NOT NULL,
    mev INTEGER DEFAULT 6,
    mav_low INTEGER DEFAULT 10,
    mav_high INTEGER DEFAULT 16,
    mrv INTEGER DEFAULT 20,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (athlete_id) REFERENCES athletes(id),
    UNIQUE(athlete_id, muscle_group)
);

CREATE INDEX IF NOT EXISTS idx_exercise_muscles_exercise
    ON exercise_muscles(exercise_id);
CREATE INDEX IF NOT EXISTS idx_program_phases_program
    ON program_phases(program_id);
CREATE INDEX IF NOT EXISTS idx_set_logs_exercise
    ON set_logs(exercise_id);
CREATE INDEX IF NOT EXISTS idx_set_logs_workout
    ON set_logs(workout_log_id);
CREATE INDEX IF NOT EXISTS idx_workout_logs_athlete
    ON workout_logs(athlete_id);
CREATE INDEX IF NOT EXISTS idx_workout_logs_date
    ON workout_logs(date);
CREATE INDEX IF NOT EXISTS idx_one_rep_maxes_athlete_exercise
    ON one_rep_maxes(athlete_id, exercise_id);
"""


def init_schema(db):
    db.executescript(SCHEMA)
    db.commit()
```

**Step 2: Commit**

```bash
git add server/db/schema.py
git commit -m "feat: database schema with 11 tables"
```

---

### Task 4: Algorithm modules

**Files:**
- Create: `server/algorithms/e1rm.py`
- Create: `server/algorithms/overload.py`
- Create: `server/algorithms/phase_config.py`
- Create: `server/algorithms/streak.py`
- Create: `server/algorithms/volume.py`

These are pure functions extracted from `cgi-bin/api.py`. No database imports, no HTTP imports. They take data in and return results.

**Step 1: Create server/algorithms/e1rm.py**

Extract from `cgi-bin/api.py:543-604`:
- `estimate_1rm(weight, reps, rpe)` — Epley formula with RPE adjustment
- `rpe_to_percentage(rpe, reps)` — Tuchscherer RPE chart
- `calculate_training_weight(e1rm, rpe, reps)` — recommended weight from e1RM
- `calculate_volume_load(sets_data)` — total volume from set list

**Step 2: Create server/algorithms/overload.py**

Extract the pure logic from `cgi-bin/api.py:618-699`. Refactor `get_progressive_overload_recommendation` to be a pure function that takes session data (not a db cursor):

```python
def recommend_overload(last_session, prev_session, current_e1rm):
    """
    Pure function: analyze recent sessions, return overload recommendation.
    last_session/prev_session: list of dicts with weight, reps, rpe keys.
    Returns dict with action, suggested_weight, suggested_reps, rationale.
    """
```

**Step 3: Create server/algorithms/phase_config.py**

Extract `generate_phase_config` from `cgi-bin/api.py:702-816`. This is already a pure function — copy directly.

**Step 4: Create server/algorithms/streak.py**

Extract streak calculation logic from `cgi-bin/api.py:1558-1571`:

```python
def calculate_streak(workout_dates, today):
    """
    Pure function: count consecutive training days with 2-day grace window.
    workout_dates: list of date strings (YYYY-MM-DD), descending order.
    today: date object.
    Returns int streak count.
    """
```

**Step 5: Create server/algorithms/volume.py**

```python
def aggregate_muscle_volume(sets_with_muscles):
    """
    Aggregate volume per muscle group from set logs joined with exercise muscle data.
    This is a placeholder that currently works with comma-separated primary_muscles.
    Will be upgraded in Phase 4 to use exercise_muscles contribution factors.
    """
```

**Step 6: Commit**

```bash
git add server/algorithms/
git commit -m "feat: pure algorithm modules (e1rm, overload, phase_config, streak, volume)"
```

---

### Task 5: Test algorithm modules

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_e1rm.py`
- Create: `tests/test_overload.py`
- Create: `tests/test_streak.py`

**Step 1: Write tests for e1rm**

```python
from server.algorithms.e1rm import estimate_1rm, rpe_to_percentage, calculate_volume_load


def test_estimate_1rm_basic():
    # 225 lbs x 5 reps @ RPE 10 -> Epley: 225 * (1 + 5/30) = 262.5
    assert estimate_1rm(225, 5, 10) == 262.5


def test_estimate_1rm_with_rpe_adjustment():
    # 225 lbs x 5 reps @ RPE 8 -> effective reps = 5 + 2 = 7
    # 225 * (1 + 7/30) = 277.5
    assert estimate_1rm(225, 5, 8) == 277.5


def test_estimate_1rm_single_rep():
    # 1 rep @ RPE 10 -> effective_reps = 1, return weight
    assert estimate_1rm(315, 1, 10) == 315


def test_estimate_1rm_zero_weight():
    assert estimate_1rm(0, 5, 8) == 0


def test_estimate_1rm_zero_reps():
    assert estimate_1rm(225, 0, 8) == 0


def test_rpe_to_percentage_known_values():
    assert rpe_to_percentage(10, 1) == 100
    assert rpe_to_percentage(8, 5) == 81.1
    assert rpe_to_percentage(6, 10) == 62.6


def test_calculate_volume_load():
    sets = [
        {"weight": 225, "reps": 5},
        {"weight": 225, "reps": 5},
        {"weight": 225, "reps": 4},
    ]
    assert calculate_volume_load(sets) == 3150.0
```

**Step 2: Write tests for streak**

```python
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
```

**Step 3: Write tests for overload**

```python
from server.algorithms.overload import recommend_overload


def test_overload_low_rpe_increases_load():
    last = [{"weight": 200, "reps": 5, "rpe": 6.5}]
    prev = [{"weight": 195, "reps": 5, "rpe": 7}]
    rec = recommend_overload(last, prev, 260)
    assert rec["action"] == "increase_load"


def test_overload_moderate_rpe_micro_loads():
    last = [{"weight": 200, "reps": 5, "rpe": 8}]
    prev = [{"weight": 195, "reps": 5, "rpe": 7.5}]
    rec = recommend_overload(last, prev, 260)
    assert rec["action"] == "micro_load"


def test_overload_high_rpe_adds_reps():
    last = [{"weight": 200, "reps": 5, "rpe": 9.5}]
    prev = [{"weight": 200, "reps": 5, "rpe": 9}]
    rec = recommend_overload(last, prev, 260)
    assert rec["action"] == "add_reps_or_deload"
```

**Step 4: Run tests**

Run: `pytest tests/ -v`
Expected: All pass.

**Step 5: Commit**

```bash
git add tests/
git commit -m "test: algorithm unit tests (e1rm, streak, overload)"
```

---

### Task 6: Exercise seed data

**Files:**
- Create: `server/db/seed_exercises.py`

**Step 1: Create server/db/seed_exercises.py**

Extract the entire `seed_exercises` function from `cgi-bin/api.py:175-536`. This is the 250+ exercise taxonomy — copy the full tuple list and the `executemany` call. Wrap in a function:

```python
def seed_exercises(db):
    count = db.execute("SELECT COUNT(*) FROM exercises").fetchone()[0]
    if count > 0:
        return

    exercises = [
        # Copy all 250+ tuples from cgi-bin/api.py:182-529
    ]

    db.executemany("""
        INSERT OR IGNORE INTO exercises
        (name, category, movement_pattern, primary_muscles, secondary_muscles,
         equipment, bilateral, complexity, fatigue_rating, mev_sets_per_week, mrv_sets_per_week)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, exercises)
    db.commit()
```

**Step 2: Commit**

```bash
git add server/db/seed_exercises.py
git commit -m "feat: 250+ exercise seed data"
```

---

### Task 7: Pydantic models

**Files:**
- Create: `server/models/common.py`
- Create: `server/models/athlete.py`
- Create: `server/models/exercise.py`
- Create: `server/models/program.py`
- Create: `server/models/workout.py`
- Create: `server/models/analytics.py`

**Step 1: Create server/models/common.py**

```python
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error: str
```

**Step 2: Create domain models**

One Pydantic model per request body used in the existing API. Derive fields from what `cgi-bin/api.py` reads from `body.get(...)`:

- `athlete.py`: `AthleteCreate` (name, age, body_weight, etc.)
- `exercise.py`: no write models needed (read-only seed data)
- `program.py`: `ProgramGenerate` (athlete_id, goal, phase, split, weeks, days_per_week, name)
- `workout.py`: `WorkoutSave` (athlete_id, program_id, session_id, date, duration_min, notes, session_rpe, body_weight, sets: list[SetLog])
- `analytics.py`: `VolumeLandmarksSave` (athlete_id, landmarks: list[LandmarkEntry])

**Step 3: Commit**

```bash
git add server/models/
git commit -m "feat: Pydantic request/response models"
```

---

### Task 8: Service layer

**Files:**
- Create: `server/services/athlete_service.py`
- Create: `server/services/exercise_service.py`
- Create: `server/services/program_service.py`
- Create: `server/services/workout_service.py`
- Create: `server/services/analytics_service.py`
- Create: `server/services/dashboard_service.py`

Each service file contains the SQL queries and business logic extracted from the corresponding handler functions in `cgi-bin/api.py`. Services receive a `db` cursor and return Python dicts/lists — they never touch HTTP.

**Mapping from api.py handlers to services:**

- `athlete_service.py`: `get_athlete` (api.py:958), `save_athlete` (api.py:966)
- `exercise_service.py`: `get_exercises` (api.py:909), `get_exercise` (api.py:936), `search_exercises` (api.py:946), `get_movement_patterns` (api.py:1609), `get_muscle_groups` (api.py:1617)
- `program_service.py`: `get_programs` (api.py:998), `get_program_detail` (api.py:1006), `generate_program` (api.py:1037) + all helper functions `_generate_upper_lower`, `_generate_ppl`, `_generate_full_body`, `_populate_session`, `_add_exercise_by_pattern` (api.py:1070-1295)
- `workout_service.py`: `save_workout` (api.py:1298), `get_workouts` (api.py:1340), `get_workout_detail` (api.py:1359), `delete_workout` (api.py:1397)
- `analytics_service.py`: `get_e1rm` (api.py:1407), `get_overload_rec` (api.py:1440), `get_analytics` (api.py:1449), `get_volume_landmarks` (api.py:1499), `save_volume_landmarks` (api.py:1522), `get_phase_config` (api.py:1534)
- `dashboard_service.py`: `get_dashboard` (api.py:1542)

**Key refactoring for services:**
- Remove `params.get(...)` parsing — services receive typed Python arguments
- Import algorithms from `server.algorithms` instead of calling inline functions
- The `overload_rec` service queries DB for recent sets, then delegates to `algorithms.overload.recommend_overload()`
- The `dashboard_service` streak calculation queries dates, then delegates to `algorithms.streak.calculate_streak()`

**Step 1: Write all 6 service files**

Extract each handler's SQL + logic, removing HTTP concerns (params parsing, json_response calls). Each function signature takes `db` + typed arguments, returns a dict or list.

**Step 2: Commit**

```bash
git add server/services/
git commit -m "feat: service layer (all business logic extracted from api.py)"
```

---

### Task 9: Route layer

**Files:**
- Create: `server/routes/athlete.py`
- Create: `server/routes/exercises.py`
- Create: `server/routes/programs.py`
- Create: `server/routes/workouts.py`
- Create: `server/routes/analytics.py`
- Create: `server/routes/dashboard.py`

Each route file defines a FastAPI `APIRouter`, declares endpoints, parses query params or request body, calls the corresponding service, and returns the result. Routes are thin — validate input, delegate, respond.

**URL mapping from old CGI actions to REST endpoints:**

| Old: `?action=` | New: REST endpoint | Method |
|---|---|---|
| `get_athlete` | `/athlete` | GET |
| `save_athlete` | `/athlete` | POST |
| `get_exercises` | `/exercises` | GET |
| `get_exercise` | `/exercises/{id}` | GET |
| `search_exercises` | `/exercises/search` | GET |
| `get_movement_patterns` | `/exercises/patterns` | GET |
| `get_muscle_groups` | `/exercises/muscles` | GET |
| `get_programs` | `/programs` | GET |
| `get_program` | `/programs/{id}` | GET |
| `generate_program` | `/programs/generate` | POST |
| `save_workout` | `/workouts` | POST |
| `get_workouts` | `/workouts` | GET |
| `get_workout_detail` | `/workouts/{id}` | GET |
| `delete_workout` | `/workouts/{id}` | DELETE |
| `get_e1rm` | `/analytics/e1rm` | GET |
| `get_overload_rec` | `/analytics/overload` | GET |
| `get_analytics` | `/analytics/{metric}` | GET |
| `get_volume_landmarks` | `/analytics/volume-landmarks` | GET |
| `save_volume_landmarks` | `/analytics/volume-landmarks` | POST |
| `get_phase_config` | `/analytics/phase-config` | GET |
| `get_dashboard` | `/dashboard` | GET |

**Example route file (server/routes/athlete.py):**

```python
from fastapi import APIRouter, Depends
from server.dependencies import get_db
from server.models.athlete import AthleteCreate
from server.services import athlete_service

router = APIRouter()


@router.get("/athlete")
def get_athlete(id: int = 1, db=Depends(get_db)):
    return athlete_service.get_athlete(db, id)


@router.post("/athlete")
def save_athlete(body: AthleteCreate, db=Depends(get_db)):
    return athlete_service.save_athlete(db, body)
```

**Step 1: Write all 6 route files following this pattern**

**Step 2: Commit**

```bash
git add server/routes/
git commit -m "feat: REST route layer (all 21 endpoints)"
```

---

### Task 10: FastAPI app entry point

**Files:**
- Create: `server/main.py`

**Step 1: Create server/main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.config import CORS_ORIGINS
from server.db.connection import get_connection
from server.db.schema import init_schema
from server.db.seed_exercises import seed_exercises
from server.routes import athlete, exercises, programs, workouts, analytics, dashboard


def create_app():
    app = FastAPI(title="IRONLOG", version="2.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(athlete.router, tags=["athlete"])
    app.include_router(exercises.router, tags=["exercises"])
    app.include_router(programs.router, tags=["programs"])
    app.include_router(workouts.router, tags=["workouts"])
    app.include_router(analytics.router, tags=["analytics"])
    app.include_router(dashboard.router, tags=["dashboard"])

    @app.on_event("startup")
    def startup():
        db = get_connection()
        init_schema(db)
        seed_exercises(db)
        db.close()

    return app


app = create_app()
```

**Step 2: Verify server starts**

Run: `./run.sh`
Expected: Uvicorn starts, `http://localhost:8000/docs` shows all 21 endpoints.

**Step 3: Smoke test key endpoints**

Run: `curl http://localhost:8000/athlete`
Expected: `{"id": null}` (no athlete yet)

Run: `curl http://localhost:8000/exercises | python -m json.tool | head -20`
Expected: JSON array of 250+ exercises

Run: `curl http://localhost:8000/dashboard`
Expected: JSON with recent_workouts, streak, totals, recent_prs, active_program

**Step 4: Commit**

```bash
git add server/main.py
git commit -m "feat: FastAPI app entry point — all endpoints live"
```

---

## Phase 2: Frontend Split

### Task 11: Frontend config and API client

**Files:**
- Create: `js/config.js`
- Create: `js/api/client.js`
- Create: `js/api/athlete.js`
- Create: `js/api/exercises.js`
- Create: `js/api/programs.js`
- Create: `js/api/workouts.js`
- Create: `js/api/analytics.js`
- Create: `js/api/dashboard.js`

**Step 1: Create js/config.js**

```javascript
export const API_BASE = window.IRONLOG_API || 'http://localhost:8000';
export const ATHLETE_ID = 1;
```

**Step 2: Create js/api/client.js**

Extract from `app.js:93-114`. Refactor to use the new REST URL pattern:

```javascript
import { API_BASE } from '../config.js';

export async function get(path, params = {}) {
    const qs = new URLSearchParams(params).toString();
    const url = qs ? `${API_BASE}/${path}?${qs}` : `${API_BASE}/${path}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}

export async function post(path, body) {
    const res = await fetch(`${API_BASE}/${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}

export async function del(path, params = {}) {
    const qs = new URLSearchParams(params).toString();
    const url = qs ? `${API_BASE}/${path}?${qs}` : `${API_BASE}/${path}`;
    const res = await fetch(url, { method: 'DELETE' });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}
```

**Step 3: Create domain API modules**

Each wraps client.js calls with domain-specific function names. Example `js/api/dashboard.js`:

```javascript
import { get } from './client.js';
import { ATHLETE_ID } from '../config.js';

export function getDashboard() {
    return get('dashboard', { athlete_id: ATHLETE_ID });
}
```

**Step 4: Commit**

```bash
git add js/config.js js/api/
git commit -m "feat: frontend API client with domain modules"
```

---

### Task 12: State and router modules

**Files:**
- Create: `js/state/store.js`
- Create: `js/state/router.js`
- Create: `js/state/workout-state.js`

**Step 1: Create js/state/store.js**

Extract `APP_STATE` from `app.js:48-86`:

```javascript
export const state = {
    athlete: null,
    dashboard: null,
    exercises: null,
    movementPatterns: null,
    muscleGroups: null,
    programs: null,
    e1rms: null,
    currentRoute: 'dashboard',
    charts: {},
    exerciseFilter: { pattern: 'all', equipment: 'all', muscle: 'all', query: '' },
    programGen: { step: 1, goal: null, phase: null, split: null, weeks: 4, days: 4, name: '' },
    analyticsRange: 30,
    selectedProgramId: null,
    generatingProgram: false,
};
```

**Step 2: Create js/state/router.js**

Extract hash-routing logic from app.js. Register view renderers by route name:

```javascript
const routes = {};

export function registerRoute(name, renderer) {
    routes[name] = renderer;
}

export function navigate(hash) {
    // ... extracted from app.js routing logic
}

export function initRouter() {
    window.addEventListener('hashchange', () => navigate(location.hash.slice(1)));
    navigate(location.hash.slice(1) || 'dashboard');
}
```

**Step 3: Create js/state/workout-state.js**

Extract `activeWorkout` and `restTimer` state + related mutation functions from app.js.

**Step 4: Commit**

```bash
git add js/state/
git commit -m "feat: state management and hash router modules"
```

---

### Task 13: Lib modules (pure utilities)

**Files:**
- Create: `js/lib/calc.js`
- Create: `js/lib/format.js`
- Create: `js/lib/dom.js`

**Step 1: Create js/lib/calc.js**

Extract `calcE1rm` and the RPE_SCALE constant from app.js. Pure math, no DOM.

**Step 2: Create js/lib/format.js**

Extract all formatting helpers scattered in app.js: date formatting, duration formatting (MM:SS), number formatting (volume with K suffix), weight display.

**Step 3: Create js/lib/dom.js**

Extract any DOM utility patterns used repeatedly: class toggling, element selection shortcuts, event delegation helpers.

**Step 4: Commit**

```bash
git add js/lib/
git commit -m "feat: pure utility modules (calc, format, dom)"
```

---

### Task 14: Component modules

**Files:**
- Create: `js/components/toast.js`
- Create: `js/components/modal.js`
- Create: `js/components/timer.js`
- Create: `js/components/loader.js`
- Create: `js/components/badges.js`
- Create: `js/components/charts.js`
- Create: `js/components/pills.js`
- Create: `js/components/inputs.js`

Each component is a set of pure functions that take data and return HTML strings, plus optional event-binding setup functions.

**Step 1: Extract toast, modal, and loader**

From app.js: `showToast()`, modal show/hide logic, loader animation control.

**Step 2: Extract timer component**

From app.js: rest timer rendering, countdown logic, ring SVG updates, skip/adjust handlers.

**Step 3: Extract badges, pills, inputs, charts**

- `badges.js`: PR badge, set type badge, status badge HTML generators
- `pills.js`: pill selector rendering + click handler binding
- `inputs.js`: numeric input with inputmode, RPE slider, reps stepper
- `charts.js`: Chart.js wrapper (create chart, destroy chart, track instances for cleanup)

**Step 4: Commit**

```bash
git add js/components/
git commit -m "feat: reusable UI component modules"
```

---

### Task 15: View modules

**Files:**
- Create: `js/views/dashboard.js`
- Create: `js/views/workout.js`
- Create: `js/views/exercises.js`
- Create: `js/views/exercise-detail.js`
- Create: `js/views/programs.js`
- Create: `js/views/program-detail.js`
- Create: `js/views/program-wizard.js`
- Create: `js/views/analytics.js`
- Create: `js/views/profile.js`

Each view exports a single `render()` function. Views import from `api/*`, `state/*`, `lib/*`, and `components/*`. They never call `fetch()` directly or access global state without going through the store.

**Step 1: Extract each render___View() function from app.js**

This is the largest extraction. Each view function in `app.js` becomes its own module. The HTML string construction, event binding, and data fetching all move together.

The key refactoring for each view:
- Replace `api('get_dashboard', {...})` calls with `import { getDashboard } from '../api/dashboard.js'`
- Replace `S.xxx` references with `import { state } from '../state/store.js'`
- Replace inline toast/modal/badge calls with component imports
- Replace inline chart creation with `import { createChart, destroyChart } from '../components/charts.js'`

**Step 2: Commit**

```bash
git add js/views/
git commit -m "feat: view modules (all 9 views extracted from app.js)"
```

---

### Task 16: Entry point and index.html update

**Files:**
- Create: `js/app.js` (new modular entry point)
- Modify: `index.html:194` (script tag change)
- Delete: old `app.js` (root level)

**Step 1: Create js/app.js**

```javascript
import { state } from './state/store.js';
import { registerRoute, initRouter } from './state/router.js';
import { renderDashboardView } from './views/dashboard.js';
import { renderWorkoutView } from './views/workout.js';
import { renderExercisesView } from './views/exercises.js';
import { renderExerciseDetailView } from './views/exercise-detail.js';
import { renderProgramsView } from './views/programs.js';
import { renderProgramDetailView } from './views/program-detail.js';
import { renderProgramWizardView } from './views/program-wizard.js';
import { renderAnalyticsView } from './views/analytics.js';
import { renderProfileView } from './views/profile.js';
import { getAthlete } from './api/athlete.js';

// Register all routes
registerRoute('dashboard', renderDashboardView);
registerRoute('workout', renderWorkoutView);
registerRoute('exercises', renderExercisesView);
registerRoute('exercise', renderExerciseDetailView);
registerRoute('programs', renderProgramsView);
registerRoute('program', renderProgramDetailView);
registerRoute('program-wizard', renderProgramWizardView);
registerRoute('analytics', renderAnalyticsView);
registerRoute('profile', renderProfileView);

// Initialize
async function init() {
    const athlete = await getAthlete();
    if (!athlete.id) {
        document.getElementById('onboarding-modal').classList.remove('hidden');
    } else {
        state.athlete = athlete;
    }
    document.getElementById('page-loader').classList.add('done');
    initRouter();
}

init();
```

**Step 2: Update index.html**

Change line 194:
```html
<!-- before -->
<script src="./app.js"></script>
<!-- after -->
<script type="module" src="./js/app.js"></script>
```

**Step 3: Delete old app.js from root**

```bash
rm app.js
```

**Step 4: Verify the app loads and all views render**

Open `index.html` in browser. Navigate to each route via bottom nav. Verify:
- Dashboard renders with greeting, stats, recent workouts
- Exercise library renders with search and filters
- Programs list renders
- Analytics renders with charts
- Profile renders with form

**Step 5: Commit**

```bash
git add js/app.js index.html
git rm app.js
git commit -m "feat: modular entry point — frontend split complete"
```

---

## Phase 3: Connect

### Task 17: Wire frontend to FastAPI backend

**Files:**
- Modify: `js/config.js` (verify API_BASE points to localhost:8000)
- Modify: `js/api/client.js` (if any URL patterns need adjustment)

**Step 1: Start the FastAPI server**

Run: `./run.sh`

**Step 2: Serve the frontend**

Run: `python -m http.server 3000` (from project root, separate terminal)

**Step 3: Test every feature end-to-end**

Open `http://localhost:3000` in browser. Test sequence:

1. Onboarding flow — fill in profile, submit → athlete saved
2. Dashboard — verify greeting, stats load
3. Workout — start from program or custom, log sets, finish
4. Exercises — search, filter, view detail with e1RM chart
5. Programs — generate via wizard, view detail, start session
6. Analytics — toggle time ranges, verify charts render
7. Profile — edit and save

**Step 4: Fix any integration issues**

URL mismatches, response shape differences, CORS errors.

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: frontend connected to FastAPI backend — full integration"
```

---

### Task 18: Clean up old CGI backend

**Files:**
- Delete: `cgi-bin/api.py`
- Delete: `cgi-bin/` directory

**Step 1: Verify the app works fully without cgi-bin**

The frontend should be hitting FastAPI on port 8000, not cgi-bin. Verify nothing references `cgi-bin`.

**Step 2: Remove cgi-bin**

```bash
rm -rf cgi-bin/
```

**Step 3: Commit**

```bash
git rm -r cgi-bin/
git commit -m "chore: remove legacy CGI backend"
```

---

## Phase 4: Enhance (Future — Design Fresh When Ready)

> **Note:** These tasks are deliberately left as stubs. When we reach this phase, we will design the `exercise_muscles` seed data, contribution factors, and volume analytics queries from first principles. The enhanced generator with phase-aware volume budgeting will also be designed fresh at that time.

### Task 19: Author exercise_muscles seed data

Design and author contribution factors for all 250+ exercises. This is domain work — each exercise needs accurate primary/secondary muscle assignments with contribution weights (0.0-1.0).

### Task 20: Per-muscle volume analytics

Upgrade `analytics_service.py` and `algorithms/volume.py` to query via `exercise_muscles` relation with contribution factors instead of comma-separated strings.

### Task 21: Enhanced generator with volume budgeting

Add MEV/MRV-aware volume budgeting to the program generator. Design the logic fresh based on the volume landmarks table and exercise_muscles data.
