# IRONLOG v2 Implementation Handoff

## Status: 34 of 34 tasks complete (Phases 1-6 COMPLETE)

## Branch

- **All work on `main`** at `2f45a04` (47 commits)
- No active worktrees or feature branches

## Execution Method

Using **Subagent-Driven Development** (`superpowers:subagent-driven-development`):
- Fresh subagent per task (or parallel agents for independent tasks)
- Phases 5-6: Tasks 22+23, 28+29, 30+31, 32+33+34 were executed in parallel batches

## Plan Files

- **Design doc:** `docs/plans/2026-02-26-ironlog-v2-design.md`
- **Phases 1-3 implementation plan:** `docs/plans/2026-02-26-ironlog-v2-implementation.md`
- **Phase 4 plan:** `docs/plans/PHASE4_PLAN.md`
- **Phase 5-6 plan:** `docs/plans/2026-02-27-phase5-6-plan.md`
- **Muscle assignments reference:** `docs/MUSCLE_ASSIGNMENTS_NOTE.md`

## Commit History

```
2f45a04 feat: e1RM progression bar chart in analytics view
6375a39 feat: program retrospective view with e1RM changes and volume totals
f33c607 feat: muscle status zone chart and compliance API client
603e8e2 feat: program retrospective endpoint with e1RM changes and volume totals
cd6c1d7 feat: muscle status and session compliance analytics endpoints
20c122a feat: program detail with weekly prescription view and next phase button
0aab4d2 feat: workout view pre-fills prescribed weights from weekly prescriptions
82ca1e2 feat: include weekly prescriptions in program detail response
3a432da feat: week advancement, program completion, and weekly prescriptions endpoint
b529543 feat: volume-constrained generator with iterative adjustment
befeb1f feat: weekly prescription generation with e1RM-based weights
2c24260 feat: progression algorithm — weekly curves + weight prescription
074eb79 feat: weekly_prescriptions table + suggested_next_phase column
034dd26 docs: Phase 5-6 plan — smart prescriptions & performance feedback
cd68c00 feat: serve frontend static files from FastAPI
6022662 chore: move Phase 4 plan to docs/plans/
b616fdf feat: Phase 4 — exercise-muscle foundation & volume intelligence
c639180 docs: update handoff for Phase 4 — Phases 1-3 complete
a9f4abf chore: remove legacy CGI backend and old monolithic app.js
4763d0c fix: add missing e1rm field normalization in analytics view
70c5ce6 feat: wire frontend to FastAPI backend — fix response shape mismatches
9cab266 fix: remove unused navigate and capitalize imports from entry point
46aeae0 feat: modular entry point — frontend split complete
a1fa6b3 fix: remove unused vlm fetch and import, add sessionName to workout state
c32bb3d feat: view modules — all 9 views extracted from app.js
ad6114d fix: use setTypePill from badges.js instead of duplicating logic
6c0efb7 feat: reusable UI component modules
875af78 fix: match original getTimeOfDay casing and move dotsHtml to format.js
04cbcae feat: pure utility modules (calc, format, dom)
5ed4ece fix: clear workout timer interval before reset to prevent leaks
7709138 feat: state management and hash router modules
f9ea21c fix: strip undefined/null params from API client query strings
2b5ce3b feat: frontend API client with domain modules
e50f7a6 feat: FastAPI app entry point — all endpoints live
8af7f58 fix: remove unused HTTPException import from analytics routes
1eadb49 feat: REST route layer — 21 endpoints mapping old CGI actions to FastAPI
cfcd746 fix: address code review findings in service layer
ae2f63f feat: service layer — extract SQL + business logic from monolith
afdcec2 fix: tighten AthleteCreate.id type and ProgramGenerate.split validation
20a70ec feat: Pydantic request/response models
28e6fc9 feat: 250+ exercise seed data
48af9ed test: algorithm unit tests (e1rm, streak, overload)
5250e56 feat: pure algorithm modules (e1rm, overload, phase_config, streak, volume)
5887599 feat: database schema with 11 tables
a4a57cf feat: config, db connection, and FastAPI dependency injection
16eecc4 scaffold: backend directory structure and dependencies
```

## Task Status

### Phase 1: Backend — COMPLETE (10/10)

| # | Task | Commit |
|---|------|--------|
| 1 | Project scaffolding | `16eecc4` |
| 2 | Config and database connection | `a4a57cf` |
| 3 | Database schema (11 tables) | `5887599` |
| 4 | Algorithm modules (e1rm, overload, phase_config, streak, volume) | `5250e56` |
| 5 | Test algorithm modules (14 tests, all passing) | `48af9ed` |
| 6 | Exercise seed data (292 exercises) | `28e6fc9` |
| 7 | Pydantic models (6 files) | `20a70ec` + `afdcec2` |
| 8 | Service layer (6 services, all business logic) | `ae2f63f` + `cfcd746` |
| 9 | Route layer (21 REST endpoints) | `1eadb49` + `8af7f58` |
| 10 | FastAPI app entry point (server starts cleanly) | `e50f7a6` |

### Phase 2: Frontend Split — COMPLETE (6/6)

| # | Task | Commit |
|---|------|--------|
| 11 | Frontend config and API client (8 files) | `2b5ce3b` + `f9ea21c` |
| 12 | State and router modules (3 files) | `7709138` + `5ed4ece` |
| 13 | Lib modules — calc, format, dom (3 files) | `04cbcae` + `875af78` |
| 14 | Component modules — toast, modal, timer, charts, etc. (8 files) | `6c0efb7` + `ad6114d` |
| 15 | View modules — all 9 views extracted (9 files, 1705 lines) | `c32bb3d` + `a1fa6b3` |
| 16 | Entry point and index.html update | `46aeae0` + `9cab266` |

### Phase 3: Connect — COMPLETE (2/2)

| # | Task | Commit |
|---|------|--------|
| 17 | Wire frontend to FastAPI backend (12 response shape fixes) | `70c5ce6` + `4763d0c` |
| 18 | Clean up old CGI backend + monolith (3764 lines removed) | `a9f4abf` |

### Phase 4: Exercise-Muscle Foundation & Volume Intelligence — COMPLETE (3/3)

| # | Task | Commit |
|---|------|--------|
| 19 | Exercise-muscle seed data (16 muscles, 50 templates, 150+ overrides) | `b616fdf` |
| 20 | Per-muscle volume analytics (contribution-weighted queries) | `b616fdf` |
| 21 | Volume budget + audit in generator + frontend display | `b616fdf` |

### Phase 5: Smart Prescriptions — COMPLETE (8/8)

| # | Task | Commit |
|---|------|--------|
| 22 | Schema: `weekly_prescriptions` table + `suggested_next_phase` column | `074eb79` |
| 23 | Algorithm: `progression.py` — weekly intensity ramp + volume wave curves | `2c24260` |
| 24 | Service: Weekly prescription generation with e1RM-based weights | `befeb1f` |
| 25 | Service: Volume-constrained generator (generate-adjust loop, 3-pass cap) | `b529543` |
| 26 | Service: Week advancement + program completion + next phase suggestion | `3a432da` |
| 27 | API: Enhanced program detail with weekly prescriptions | `82ca1e2` |
| 28 | Frontend: Program detail weekly view with prescribed weights | `20c122a` |
| 29 | Frontend: Workout view pre-fills weights from current week prescriptions | `0aab4d2` |

### Phase 6: Performance Feedback — COMPLETE (5/5)

| # | Task | Commit |
|---|------|--------|
| 30 | Backend: Muscle status + session compliance analytics endpoints | `cd6c1d7` |
| 31 | Backend: Program retrospective endpoint | `603e8e2` |
| 32 | Frontend: Volume vs landmarks zone chart + compliance API client | `f33c607` |
| 33 | Frontend: e1RM progression bar chart | `2f45a04` |
| 34 | Frontend: Program retrospective view | `6375a39` |

## Architecture Summary

### Backend (`server/`)

```
server/
├── main.py              — FastAPI app factory + startup + static serving
├── config.py            — DB_PATH, CORS_ORIGINS from env
├── dependencies.py      — get_db() generator for DI
├── algorithms/          — Pure functions (no DB, no HTTP)
│   ├── e1rm.py          — Epley formula, RPE chart, volume load
│   ├── overload.py      — Progressive overload recommendations
│   ├── phase_config.py  — 4×4 periodization matrix (goal × phase)
│   ├── progression.py   — Weekly progression curves + weight prescription
│   ├── streak.py        — Consecutive training day counter
│   └── volume_budget.py — Projected volume + MEV/MRV audit
├── db/
│   ├── connection.py    — SQLite connection with WAL + FK
│   ├── schema.py        — 12 tables + 8 indexes (incl. weekly_prescriptions)
│   ├── seed_exercises.py — 292 exercise taxonomy entries
│   └── seed_muscles.py  — Exercise-muscle contributions (16 groups, 50 templates, 150+ overrides)
├── models/              — Pydantic v2 request models
├── services/            — Business logic + SQL (no HTTP)
│   ├── athlete_service.py
│   ├── exercise_service.py
│   ├── program_service.py  — Generator + volume budget + weekly prescriptions + retrospective
│   ├── workout_service.py  — Workout logging + auto week advancement
│   ├── analytics_service.py — e1RM, overload, volume, landmarks, muscle status, compliance
│   └── dashboard_service.py
└── routes/              — Thin FastAPI routers (25 endpoints)
```

### Frontend (`js/`)

```
js/
├── app.js               — Entry point: route registration, init, onboarding
├── config.js            — API_BASE, ATHLETE_ID
├── api/                 — HTTP client + 7 domain modules
├── state/               — store.js, router.js, workout-state.js
├── lib/                 — calc.js, format.js, dom.js
├── components/          — 8 reusable UI components
└── views/               — 9 page renderers
    ├── analytics.js     — Volume charts, muscle status zones, e1RM bars, heat calendar, landmarks editor
    ├── program-detail.js — Weekly prescription view, volume budget, next phase button, retrospective
    ├── program-wizard.js — 5-step generator wizard
    └── workout.js       — Set logging with prescribed weight pre-fill + overload recommendations
```

### Database (12 tables)

Core: `athletes`, `exercises`, `programs`, `program_sessions`, `program_exercises`, `workout_logs`, `set_logs`, `one_rep_maxes`, `volume_landmarks`

Phase 4: `exercise_muscles` (contribution-weighted exercise-to-muscle mapping), `program_phases` (exists but not yet populated)

Phase 5: `weekly_prescriptions` (per-week per-exercise targets with e1RM-derived weights)

### Key Systems

**Weekly Prescriptions** (Phase 5):
- `weekly_prescriptions` table with FK to `program_exercises`
- `progression.py` — 5 volume curves (linear/undulating/step/taper/reduced) + linear intensity ramp
- `prescribe_weight()` — e1RM × intensity_pct / 100, rounded to 2.5 lbs
- Generator creates prescriptions for every exercise × every week on program generation
- Idempotent: skips exercises that already have prescriptions (safe for re-runs after volume adjustment)

**Volume-Constrained Generator** (Phase 5):
- Generate → audit → add isolation exercises → re-audit (max 3 passes)
- 12 primary muscles audited; only fixes `below_mev` deficits
- `_MUSCLE_FIX_PATTERNS` maps each muscle to its best isolation movement pattern
- Exercises added to least-loaded session; max 2 deficits fixed per pass

**Week Advancement** (Phase 5):
- Auto-advances `current_week` based on `completed_sessions // sessions_per_week + 1`
- Marks program `completed` when all weeks done
- Populates `suggested_next_phase` on completion (accumulation → intensification → realization → deload → accumulation)

**Performance Feedback** (Phase 6):
- Muscle status: actual effective sets vs MEV/MAV/MRV landmarks, zone classification
- Session compliance: per-exercise sets/weight compliance vs weekly prescriptions
- Program retrospective: e1RM changes, volume per muscle, RPE trend, body weight change
- Analytics charts: muscle status zone chart (color-coded bars + landmark lines), e1RM horizontal bar chart

**Exercise-Muscle Contributions** (Phase 4):
- 16 canonical muscle groups with 0.25-1.0 contribution factors
- Two-layer: pattern templates → exercise-specific overrides (full replace)
- `SUM(em.contribution)` = effective sets per muscle per week
- 12 primary muscles audited by generator; 4 stabilizers tracked only

**Volume Budget** (Phase 4):
- `calculate_projected_volume()` + `audit_volume()` pure functions
- Red: below MEV / above MRV. Yellow: below MAV / above MAV
- Generator runs audit post-generation and includes in response

**Phase Config** (Phase 1):
- 4×4 matrix: {strength, hypertrophy, power, endurance} × {accumulation, intensification, realization, deload}
- Each cell: compound/isolation sets, reps, RPE, rest, volume_progression, intensity_start/end_pct

## Running Locally

```bash
cd /Users/caseytalbot/Desktop/IRONLOG
./run.sh   # Starts FastAPI on port 8000 (serves frontend + API)
```

Open `http://localhost:8000` — frontend served via FastAPI static file mount.

## Tests

```bash
python3 -m pytest tests/ -v
```

Current: 37 tests passing
- `test_e1rm.py` (7 tests)
- `test_overload.py` (3 tests)
- `test_streak.py` (4 tests)
- `test_seed_muscles.py` (11 tests)
- `test_volume_budget.py` (4 tests)
- `test_progression.py` (7 tests)
- `test_volume_adjust.py` (1 test)
