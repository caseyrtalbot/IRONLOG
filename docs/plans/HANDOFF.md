# IRONLOG v2 Implementation Handoff

## Status: 21 of 21 tasks complete (Phases 1-4 COMPLETE) — Phase 5-6 planned

## Branch

- **All work on `main`** at `cd68c00` (34 commits)
- **Pushed to `origin/main`**
- No active worktrees or feature branches

## Execution Method

Using **Subagent-Driven Development** (`superpowers:subagent-driven-development`):
- Fresh subagent per task (or parallel agents for independent tasks)
- Two-stage review after each: spec compliance, then code quality
- Tasks 20+21 were executed in parallel

## Plan Files

- **Design doc:** `docs/plans/2026-02-26-ironlog-v2-design.md`
- **Phases 1-3 implementation plan:** `docs/plans/2026-02-26-ironlog-v2-implementation.md`
- **Phase 4 plan:** `docs/plans/PHASE4_PLAN.md`
- **Phase 5-6 plan:** `docs/plans/2026-02-27-phase5-6-plan.md`
- **Muscle assignments reference:** `docs/MUSCLE_ASSIGNMENTS_NOTE.md`

## Commit History

```
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

Phase 4 also added:
- Static file serving from FastAPI (`cd68c00`)
- Legacy muscle group migration (back→lats+upper_back, shoulders→front/side/rear_delts)
- Volume landmarks editor with 12 canonical muscle groups
- Volume budget table with color-coded audit warnings

### Phase 5: Smart Prescriptions — PLANNED (0/8)

| # | Task | Status |
|---|------|--------|
| 22 | Schema: `weekly_prescriptions` table + `suggested_next_phase` column | Pending |
| 23 | Algorithm: `progression.py` — weekly intensity ramp + volume wave curves | Pending |
| 24 | Service: Weekly prescription generation with e1RM-based weights | Blocked by 22, 23 |
| 25 | Service: Volume-constrained generator (generate-adjust loop, 3-pass cap) | Blocked by 24 |
| 26 | Service: Week advancement + program completion + next phase suggestion | Blocked by 22 |
| 27 | API: Enhanced program detail with weekly prescriptions | Blocked by 24 |
| 28 | Frontend: Program detail weekly view with prescribed weights | Blocked by 27 |
| 29 | Frontend: Workout view pre-fills weights from current week prescriptions | Blocked by 26, 27 |

### Phase 6: Performance Feedback — PLANNED (0/5)

| # | Task | Status |
|---|------|--------|
| 30 | Backend: Muscle status + session compliance analytics endpoints | Blocked by Phase 5 |
| 31 | Backend: Program retrospective endpoint | Blocked by Phase 5 |
| 32 | Frontend: Volume vs landmarks zone chart + compliance view | Blocked by 30 |
| 33 | Frontend: e1RM progression bar chart | Pending |
| 34 | Frontend: Program retrospective view | Blocked by 31 |

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
│   ├── streak.py        — Consecutive training day counter
│   └── volume_budget.py — Projected volume + MEV/MRV audit
├── db/
│   ├── connection.py    — SQLite connection with WAL + FK
│   ├── schema.py        — 11 tables + 7 indexes
│   ├── seed_exercises.py — 292 exercise taxonomy entries
│   └── seed_muscles.py  — Exercise-muscle contributions (16 groups, 50 templates, 150+ overrides)
├── models/              — Pydantic v2 request models
├── services/            — Business logic + SQL (no HTTP)
│   ├── athlete_service.py
│   ├── exercise_service.py
│   ├── program_service.py  — Generator + volume budget + weekly prescriptions
│   ├── workout_service.py
│   ├── analytics_service.py — e1RM, overload, volume, landmarks
│   └── dashboard_service.py
└── routes/              — Thin FastAPI routers (21 endpoints)
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
    ├── analytics.js     — Volume charts, heat calendar, e1RM, landmarks editor
    ├── program-detail.js — Volume budget table + audit warnings
    ├── program-wizard.js — 5-step generator wizard
    └── workout.js       — Set logging with overload recommendations
```

### Database (11 tables)

Core: `athletes`, `exercises`, `programs`, `program_sessions`, `program_exercises`, `workout_logs`, `set_logs`, `one_rep_maxes`, `volume_landmarks`

Phase 4: `exercise_muscles` (contribution-weighted exercise-to-muscle mapping), `program_phases` (exists but not yet populated)

Phase 5 will add: `weekly_prescriptions` (per-week per-exercise targets)

### Key Systems

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

## Key Design Decisions for Phase 5-6

| Decision | Choice |
|----------|--------|
| Weight prescriptions | e1RM × (intensity_pct / 100), rounded to 2.5 lbs. Falls back to RPE-only. |
| Periodization | Hybrid — single phase per program, suggest next phase on completion |
| Week progression | Intensity ramps linearly; volume follows curve (linear/undulating/step/taper/reduced) |
| Prescription storage | New `weekly_prescriptions` table — clean separation from template |
| Volume adjustment | Generate → audit → add isolation to fix below_mev → re-audit (max 3 passes) |
| Compliance | Per-exercise: match logged sets to prescribed by exercise_id + session_id |
| Analytics | Volume vs landmarks chart, session compliance, e1RM progression, program retrospective |

## Running Locally

```bash
cd /Users/caseytalbot/Desktop/IRONLOG
./run.sh   # Starts FastAPI on port 8000 (serves frontend + API)
```

Open `http://localhost:8000` — frontend served via FastAPI static file mount.

## Tests

```bash
python -m pytest tests/ -v
```

Current: 29 tests passing
- `test_e1rm.py` (7 tests)
- `test_overload.py` (3 tests)
- `test_streak.py` (4 tests)
- `test_seed_muscles.py` (11 tests)
- `test_volume_budget.py` (4 tests)

## Resume Instructions for Phase 5

1. Read the plan: `docs/plans/2026-02-27-phase5-6-plan.md`
2. Start with Task 22 (schema) — it unblocks everything else
3. Tasks 22-23 are independent and can run in parallel
4. Task 24 depends on both 22 and 23
5. Continue the pattern: implement → test → commit → next task
6. Use `superpowers:executing-plans` for implementation
