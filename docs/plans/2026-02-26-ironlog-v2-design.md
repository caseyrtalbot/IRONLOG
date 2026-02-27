# IRONLOG v2 — Design Document

## Context

IRONLOG is a 5,000-line strength training app (vanilla JS + Python CGI + SQLite) that delivers ~80% of the functionality of Iron Protocol, a 25,000-line Next.js app. This redesign preserves IRONLOG's zero-dependency simplicity while upgrading the architecture for clean modularity, accurate per-muscle volume tracking, and deployment as a static frontend + API backend.

## Decisions

- **Platform:** Responsive — both mobile and desktop
- **Deployment:** Static frontend (Vercel/GitHub Pages) + FastAPI backend (Railway/Fly.io)
- **Backend:** FastAPI replacing Python CGI. Same SQLite, same raw SQL, proper HTTP server with CORS and Pydantic validation.
- **Frontend:** Vanilla JS with browser-native ES modules. Zero build step. Split from 1 file into ~25 modules.
- **Generator:** Enhance IRONLOG's existing generator (not a full port of Iron Protocol's 10-phase pipeline)
- **Key new feature:** Accurate per-muscle volume tracking via `exercise_muscles` relation table with contribution factors
- **Auth:** Single-user, no auth. `athlete_id = 1` throughout.
- **Structure:** Deep modules with strict dependency direction. Every file under 200 lines.

## Architecture

```
Browser (any device)          Static Host (Vercel / GitHub Pages)
  |-- index.html              |-- index.html
  |-- js/ (ES modules)        |-- js/*.js
  |-- style.css               |-- style.css
        |
        |  fetch("https://api.ironlog.dev/...")
        v
  FastAPI Server              Railway / Fly.io
  |-- main.py                 (single process, uvicorn)
  |-- routes/*.py
  |-- algorithms/*.py
  |-- ironlog.db              (SQLite, WAL mode, on persistent volume)
```

- Frontend is fully static. No server rendering, no build step.
- API is a single FastAPI process with SQLite. No Postgres, no Redis.
- Communication is JSON over HTTPS with CORS.
- Frontend's `api/client.js` points at a configurable `API_BASE_URL`.

## Database Schema (11 tables)

### Kept from IRONLOG (refined)

**athletes** — single user profile, experience level, goal, training days, session duration.

**exercises** — 250+ seeded taxonomy. All columns retained except `primary_muscles` and `secondary_muscles` text columns (moved to `exercise_muscles` relation).

**programs** — mesocycle blocks. `config` JSON blob removed (replaced by `program_phases` table).

**program_sessions** — training days within a program.

**program_exercises** — prescribed exercises per session (sets, reps, intensity, rest, tempo, superset group).

**workout_logs** — completed training sessions with date, duration, session RPE, body weight, notes.

**set_logs** — individual sets: weight, reps, RPE, RIR, set type (warmup/working/backoff/amrap/drop/cluster), tempo, rest.

**one_rep_maxes** — append-only e1RM history per exercise. Stores source weight/reps/RPE and Epley estimate. Used for trend charts.

**volume_landmarks** — per-muscle MEV/MAV-low/MAV-high/MRV thresholds. Editable by user.

### Added

**exercise_muscles** — the key structural upgrade:
- `exercise_id` FK to exercises
- `muscle_group` TEXT (chest, front_delts, triceps, etc.)
- `is_primary` INTEGER (0 or 1)
- `contribution` REAL (0.0-1.0)

Enables: `SELECT muscle_group, SUM(sets * contribution) FROM ...` for accurate per-muscle volume tracking in one query.

**program_phases** — replaces JSON config blob:
- `program_id` FK to programs (CASCADE DELETE)
- `phase_order` INTEGER
- `phase_type` TEXT (accumulation/intensification/realization/deload)
- `duration_weeks` INTEGER
- `volume_multiplier` REAL
- `intensity_target` REAL
- `rpe_target` REAL

## Backend Structure

```
server/
|-- main.py                     <- app factory, CORS, mount routers
|-- config.py                   <- API_BASE, DB_PATH, CORS_ORIGINS
|-- dependencies.py             <- FastAPI dependency injection (get_db)
|
|-- db/
|   |-- connection.py           <- SQLite connection, WAL mode, pragmas
|   |-- schema.py               <- CREATE TABLE statements (11 tables)
|   |-- seed_exercises.py       <- 250+ exercise inserts
|   |-- seed_muscles.py         <- exercise_muscles relation data
|
|-- models/                     <- Pydantic request/response schemas
|   |-- athlete.py
|   |-- exercise.py
|   |-- program.py
|   |-- workout.py
|   |-- analytics.py
|   |-- common.py               <- PaginatedResponse, ErrorResponse
|
|-- routes/                     <- thin HTTP layer: validate, delegate, respond
|   |-- athlete.py
|   |-- exercises.py
|   |-- programs.py
|   |-- workouts.py
|   |-- analytics.py
|   |-- dashboard.py
|
|-- services/                   <- business logic (SQL queries + transforms)
|   |-- athlete_service.py
|   |-- exercise_service.py
|   |-- program_service.py
|   |-- workout_service.py
|   |-- analytics_service.py
|   |-- dashboard_service.py
|
|-- algorithms/                 <- pure functions: no DB, no HTTP
    |-- e1rm.py                 <- Epley formula, RPE-to-percentage table
    |-- overload.py             <- progressive overload recommendations
    |-- phase_config.py         <- 4x4 periodization matrix
    |-- generator.py            <- program generation logic
    |-- streak.py               <- consecutive training day calculation
    |-- volume.py               <- per-muscle volume aggregation
```

### Dependency direction (strictly enforced)

```
routes -> services -> db/connection
routes -> models
services -> algorithms
algorithms -> (nothing)
```

Routes never touch SQL. Services never touch HTTP. Algorithms never import from server.

## Frontend Structure

```
js/
|-- app.js                      <- entry: init, router registration
|-- config.js                   <- API_BASE_URL, feature flags
|
|-- api/                        <- one module per domain
|   |-- client.js               <- base fetch wrapper, error handling
|   |-- athlete.js
|   |-- exercises.js
|   |-- programs.js
|   |-- workouts.js
|   |-- analytics.js
|   |-- dashboard.js
|
|-- state/
|   |-- store.js                <- APP_STATE init, getState(), setState()
|   |-- workout-state.js        <- active workout: sets, timer, current exercise
|   |-- router.js               <- hash router, navigate(), onRoute()
|
|-- lib/                        <- pure utility functions
|   |-- calc.js                 <- e1RM, RPE table, unit conversion
|   |-- format.js               <- dates, durations, weights, numbers
|   |-- dom.js                  <- createElement helpers, class toggles
|
|-- components/                 <- reusable UI pieces (return HTML strings)
|   |-- toast.js
|   |-- modal.js
|   |-- timer.js
|   |-- loader.js
|   |-- badges.js
|   |-- charts.js
|   |-- pills.js
|   |-- inputs.js
|
|-- views/                      <- one file per route
    |-- dashboard.js
    |-- workout.js
    |-- exercises.js
    |-- exercise-detail.js
    |-- programs.js
    |-- program-detail.js
    |-- program-wizard.js
    |-- analytics.js
    |-- profile.js
```

### Dependency direction (strictly enforced)

```
views -> components, api/*, state/*, lib/*
components -> lib/*
api/* -> api/client.js -> config.js
state/* -> (nothing)
lib/* -> (nothing)
```

Views never call fetch() directly. Components never access APP_STATE directly. API modules never touch the DOM.

### Component pattern

Every component is a pure function: takes data, returns HTML string. No side effects, no state access, no fetching.

## Migration Strategy

### Phase 1 — Backend

Stand up FastAPI server with new 11-table schema. Port every handler from `api.py` into routes/services/algorithms. Author `exercise_muscles` seed data with contribution factors. Old `cgi-bin/api.py` stays untouched until new backend matches all existing behavior.

### Phase 2 — Frontend split

Extract `app.js` into the module tree. Purely structural — no new features. Every view renders identically. Done when `index.html` loads `js/app.js` as type="module" and the app works exactly as before.

### Phase 3 — Connect

Point frontend `api/client.js` at FastAPI backend. Replace `cgi-bin/api.py?action=X` with clean REST paths. Verify every feature end-to-end.

### Phase 4 — Enhance

Add per-muscle volume tracking analytics powered by `exercise_muscles`. Enhance generator with phase-aware volume budgeting.

### What gets deleted

`cgi-bin/` directory. The old monolithic `app.js`.

### What survives unchanged

`style.css` (identical). `index.html` (one script tag change). 250+ exercise taxonomy. All algorithms. The dark industrial aesthetic.

## Dependencies

### Backend (pip)
- fastapi
- uvicorn
- pydantic

### Frontend
- Chart.js (CDN)
- Google Fonts: Inter + JetBrains Mono (CDN)

Total installable dependencies: 3.

## Out of Scope for v1

- Authentication / multi-user
- Iron Protocol's 10-phase generator pipeline (enhance existing instead)
- Double-progression engine (exercise progress state tracking)
- ACWR / detraining detection
- Equipment profiles
- Joint limitations
- Volume responsiveness scoring
- Metric/imperial toggle
- PR celebration screen
- Capacitor / native app
- Frontend test suite (backend algorithm tests only)
