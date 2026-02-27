# IRONLOG v2 Implementation Handoff

## Status: 18 of 21 tasks complete (Phases 1-3 COMPLETE)

## Branch

- **All work merged to `main`** at `a9f4abf` (31 commits)
- **Pushed to `origin/main`**
- No active worktrees or feature branches

## Execution Method

Using **Subagent-Driven Development** (`superpowers:subagent-driven-development`):
- Fresh subagent per task
- Two-stage review after each: spec compliance, then code quality
- Sequential task execution (no parallel implementers)

## Plan Files

- **Design doc:** `docs/plans/2026-02-26-ironlog-v2-design.md`
- **Implementation plan:** `docs/plans/2026-02-26-ironlog-v2-implementation.md`

## Commit History

```
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

### Phase 4: Enhance — NOT STARTED (0/3)

> **Note:** These tasks are deliberately left as stubs in the plan. They require fresh design work, not mechanical extraction. When we reach this phase, we will design from first principles.

| # | Task | Status | Notes |
|---|------|--------|-------|
| 19 | Author `exercise_muscles` seed data | Pending | Domain work: accurate primary/secondary muscle assignments with contribution weights (0.0-1.0) for all 292 exercises. Requires exercise science knowledge. |
| 20 | Per-muscle volume analytics | Blocked by 19 | Upgrade `analytics_service.py` and `algorithms/volume.py` to query via `exercise_muscles` relation with contribution factors instead of comma-separated strings. |
| 21 | Enhanced generator with volume budgeting | Blocked by 19, 20 | Add MEV/MRV-aware volume budgeting to the program generator. Design logic fresh based on volume landmarks table and `exercise_muscles` data. |

## Architecture Summary

### Backend (`server/`)

```
server/
├── main.py              — FastAPI app factory + startup
├── config.py            — DB_PATH, CORS_ORIGINS from env
├── dependencies.py      — get_db() generator for DI
├── algorithms/          — Pure functions (no DB, no HTTP)
│   ├── e1rm.py          — Epley formula, RPE chart, volume load
│   ├── overload.py      — Progressive overload recommendations
│   ├── phase_config.py  — Periodization config generator
│   ├── streak.py        — Consecutive training day counter
│   └── volume.py        — Muscle volume aggregation (placeholder)
├── db/
│   ├── connection.py    — SQLite connection with WAL + FK
│   ├── schema.py        — 11 tables + indexes
│   └── seed_exercises.py — 292 exercise taxonomy entries
├── models/              — Pydantic v2 request models
├── services/            — Business logic + SQL (no HTTP)
│   ├── athlete_service.py
│   ├── exercise_service.py
│   ├── program_service.py
│   ├── workout_service.py
│   ├── analytics_service.py
│   └── dashboard_service.py
└── routes/              — Thin FastAPI routers (21 endpoints)
```

### Frontend (`js/`)

```
js/
├── app.js               — Entry point (127 lines): route registration, init, onboarding
├── config.js            — API_BASE, ATHLETE_ID
├── api/                 — HTTP client + domain API modules
│   ├── client.js        — get(), post(), del() with cleanParams
│   ├── athlete.js       — getAthlete, saveAthlete
│   ├── exercises.js     — getExercises, searchExercises, getMovementPatterns, getMuscleGroups
│   ├── programs.js      — getPrograms, getProgram, generateProgram
│   ├── workouts.js      — saveWorkout, getWorkouts, getWorkoutDetail, deleteWorkout
│   ├── analytics.js     — getE1rm, getAllE1rms, getOverloadRec, getAnalytics, etc.
│   └── dashboard.js     — getDashboard
├── state/               — Shared mutable state + routing
│   ├── store.js         — Global state object (14 properties)
│   ├── router.js        — Hash router with registerRoute/navigate/initRouter
│   └── workout-state.js — activeWorkout, restTimer + reset helpers
├── lib/                 — Pure utilities (no DOM mutation except dom.js)
│   ├── calc.js          — RPE_SCALE, SET_TYPES, GOAL_INFO, PHASE_INFO, calcE1rm
│   ├── format.js        — 10 formatting functions (fmtDate, dotsHtml, etc.)
│   └── dom.js           — $id() shorthand
├── components/          — Reusable UI components
│   ├── toast.js         — showToast
│   ├── modal.js         — createModal, closeModal
│   ├── timer.js         — Workout timer + rest timer controls
│   ├── loader.js        — loaderHtml
│   ├── badges.js        — statusBadge, phaseBadge, setTypePill
│   ├── charts.js        — Chart.js lifecycle (create/destroy)
│   ├── pills.js         — pillSelectorHtml, bindPillSelector
│   └── inputs.js        — buildSetRow, buildExerciseBlock
└── views/               — Page renderers (set window globals for onclick)
    ├── dashboard.js     — renderDashboard, updateStreakBadge, viewWorkout
    ├── workout.js       — renderWorkout + 15 workout functions (487 lines)
    ├── exercises.js     — renderExercises, search, filters
    ├── exercise-detail.js — viewExerciseDetail with e1RM chart + overload rec
    ├── programs.js      — renderPrograms
    ├── program-detail.js — selectProgram
    ├── program-wizard.js — showProgramGenerator (multi-step wizard)
    ├── analytics.js     — renderAnalytics + 3 chart renderers + volume editor
    └── profile.js       — renderProfile, saveProfile, saveProfileLandmarks
```

**Dependency direction:** `views → components → lib → (nothing)`, `views → api → (nothing)`, `views → state → (nothing)`

## Key Integration Notes

- **12 response shape normalizations** were added in Phase 3 to bridge FastAPI backend field names to frontend expectations. All normalizations live in the frontend views using defensive fallback chains (`||`, `??`, `Array.isArray()`).
- **CORS:** Permissive (`*`) for dev. Should be tightened for production.
- **Config:** `js/config.js` reads `window.IRONLOG_API` or defaults to `http://localhost:8000`.
- **Running locally:** `./run.sh` starts FastAPI on port 8000. Serve frontend with `python3 -m http.server 3000` from project root.

## Known Deviations from Plan

1. **pydantic version:** `>=2.9.0` instead of `==2.9.0` (Python 3.14 compatibility)
2. **View function names:** Plan spec'd `renderDashboardView` etc., actual exports are `renderDashboard` etc.
3. **Route registration:** Plan spec'd 9 routes, actual is 6 (exercise-detail, program-detail, program-wizard are imperative sub-views, not hash routes)
4. **Old app.js deletion:** Plan said Task 16, actually done in Task 18 cleanup
5. **Review-driven fixes:** Multiple code quality improvements beyond plan scope (clearInterval leaks, URLSearchParams undefined bug, casing mismatches, unused imports)

## Resume Instructions for Phase 4

1. Create a worktree: `git worktree add .worktrees/v4-enhance -b feature/v4-enhance`
2. Task 19 (exercise_muscles seed data) is the unblocking task — design this first
3. The `exercise_muscles` table already exists in `server/db/schema.py` — it needs seed data
4. Tasks 20 and 21 depend on Task 19's data being available
5. These tasks need fresh design, not mechanical extraction. Use `superpowers:brainstorming` before implementation.
6. Continue the pattern: implement → spec review → quality review → mark complete → next task
