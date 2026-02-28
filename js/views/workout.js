// js/views/workout.js — Workout tracker view (largest view)

import { state } from '../state/store.js';
import { activeWorkout } from '../state/workout-state.js';
import { getPrograms, getProgram, getSessionPrescriptions } from '../api/programs.js';
import { getAthlete } from '../api/athlete.js';
import { getExercises } from '../api/exercises.js';
import { getOverloadRec } from '../api/analytics.js';
import { saveWorkout } from '../api/workouts.js';
import { calcE1rm, SET_TYPES } from '../lib/calc.js';
import { formatPattern } from '../lib/format.js';
import { $id, loadingSpinner, loadingSpinnerSm, emptyState } from '../lib/dom.js';
import { showToast } from '../components/toast.js';
import { startWorkoutTimer, stopWorkoutTimer, startRestTimer } from '../components/timer.js';
import { buildExerciseBlock, buildSetRow } from '../components/inputs.js';
import { ATHLETE_ID } from '../config.js';

// ── Main Render ──────────────────────────────────────

export async function renderWorkout() {
    const vc = $id('view-container');

    if (activeWorkout.running) {
        renderActiveWorkout();
        return;
    }

    vc.innerHTML = `
    <div class="view">
      <div class="view-header">
        <div class="view-title">Start Workout</div>
        <div class="view-sub">Choose a session or build custom</div>
      </div>
      <div class="workout-setup" id="workout-setup-area">
        ${loadingSpinner('Loading programs...')}
      </div>
    </div>`;

    try {
        const [programsRes, athlete] = await Promise.all([
            getPrograms(),
            Promise.resolve(state.athlete || await getAthlete()),
        ]);
        const programs = programsRes.programs || (Array.isArray(programsRes) ? programsRes : []);
        const activePrograms = programs.filter(p => p.status === 'active');

        let sessionsHtml = '';
        for (const prog of activePrograms) {
            try {
                const detail = await getProgram(prog.id);
                const sessions = detail.sessions || [];
                sessions.forEach(sess => {
                    const exCount = sess.exercises ? sess.exercises.length : 0;
                    sessionsHtml += `
            <div class="session-option" onclick="startProgramSession(${prog.id},${sess.id})">
              <div>
                <div class="session-opt-name">${sess.name}</div>
                <div class="session-opt-meta">${prog.name} \u00b7 ${exCount} exercises</div>
              </div>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#F5A623" stroke-width="2" stroke-linecap="round"><path d="M9 18l6-6-6-6"/></svg>
            </div>`;
                });
            } catch (e) { /* skip failed program loads */ }
        }

        const area = $id('workout-setup-area');
        area.innerHTML = `
      ${sessionsHtml ? `
        <div class="section-title" style="margin-bottom:10px">FROM ACTIVE PROGRAM</div>
        <div class="session-selector-grid">${sessionsHtml}</div>
        <div style="height:16px"></div>
      ` : ''}
      <div class="section-title" style="margin-bottom:10px">CUSTOM WORKOUT</div>
      <div class="session-option" onclick="startCustomWorkout()">
        <div>
          <div class="session-opt-name">+ Build Custom Session</div>
          <div class="session-opt-meta">Pick exercises freely</div>
        </div>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#F5A623" stroke-width="2" stroke-linecap="round"><path d="M9 18l6-6-6-6"/></svg>
      </div>
    `;
    } catch (e) {
        console.error(e);
        $id('workout-setup-area').innerHTML = `
      <div class="session-option" onclick="startCustomWorkout()">
        <div>
          <div class="session-opt-name">+ Start Custom Workout</div>
          <div class="session-opt-meta">Pick exercises freely</div>
        </div>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#F5A623" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
      </div>`;
    }
}

// ── Start Session ────────────────────────────────────

async function startProgramSession(programId, sessionId) {
    showToast('Loading session...', 'info');
    try {
        const detail = await getProgram(programId);
        const session = (detail.sessions || []).find(s => s.id === sessionId);
        if (!session) { showToast('Session not found', 'error'); return; }

        Object.assign(activeWorkout, {
            running: true,
            startTime: Date.now(),
            timerInterval: null,
            sessionId: sessionId,
            programId: programId,
            sessionName: session.name,
            exercises: [],
            sessionRpe: 7,
            notes: '',
            bodyWeight: state.athlete?.body_weight || null,
        });

        // Fetch weekly prescriptions for pre-filling weights
        const prescriptions = await getSessionPrescriptions(programId, sessionId).catch(() => []);
        const prescriptionMap = {};
        for (const p of (Array.isArray(prescriptions) ? prescriptions : prescriptions.prescriptions || [])) {
            prescriptionMap[p.exercise_id] = p;
        }

        // Build exercises array from program
        for (const pe of (session.exercises || [])) {
            const rx = prescriptionMap[pe.exercise_id];
            const sets = [];
            const numSets = (rx && rx.week_sets) || pe.sets_prescribed;
            for (let i = 1; i <= numSets; i++) {
                sets.push({
                    set_number: i,
                    set_type: i === 1 ? 'warmup' : 'working',
                    weight: (rx && rx.target_weight) || '',
                    reps: pe.reps_prescribed || '',
                    rpe: (rx && rx.target_rpe) || pe.intensity_value || '',
                    rir: '', logged: false,
                    prescribed_weight: (rx && rx.target_weight) || null,
                    prescribed_reps: pe.reps_prescribed,
                    prescribed_intensity: pe.intensity_value,
                    intensity_type: pe.intensity_type,
                    rest_seconds: pe.rest_seconds || 120,
                });
            }
            // Get overload rec in background
            getOverloadRec(pe.exercise_id).then(r => {
                const exBlock = activeWorkout.exercises.find(e => e.exercise.id === pe.exercise_id);
                if (exBlock) exBlock.overloadRec = r;
                if (state.currentRoute === 'workout') renderActiveWorkout();
            }).catch(() => {});

            activeWorkout.exercises.push({
                exercise: pe.exercise || { id: pe.exercise_id, name: pe.exercise_name || 'Exercise', movement_pattern: pe.movement_pattern || '' },
                sets,
                overloadRec: null,
                e1rm: null,
                superset_group: pe.superset_group || null,
            });
        }

        startWorkoutTimer();
        renderActiveWorkout();
    } catch (e) {
        console.error(e);
        showToast('Error loading session', 'error');
    }
}

function startCustomWorkout() {
    Object.assign(activeWorkout, {
        running: true,
        startTime: Date.now(),
        timerInterval: null,
        sessionId: null,
        programId: null,
        sessionName: 'Custom Workout',
        exercises: [],
        sessionRpe: 7,
        notes: '',
        bodyWeight: state.athlete?.body_weight || null,
    });
    startWorkoutTimer();
    renderActiveWorkout();
}

// ── Active Workout Render ────────────────────────────

function renderActiveWorkout() {
    const vc = $id('view-container');
    const aw = activeWorkout;

    let exercisesHtml = aw.exercises.map((ex, exIdx) => buildExerciseBlock(ex, exIdx)).join('');

    vc.innerHTML = `
    <div class="view workout-active">
      <div class="workout-top-bar">
        <div class="session-name">${aw.sessionName || 'Workout'}</div>
        <button class="btn-ghost" style="padding:6px 10px;font-size:11px;min-height:36px" onclick="discardWorkout()">✕ Discard</button>
      </div>

      <div id="exercise-blocks-container">
        ${exercisesHtml}
        ${aw.exercises.length === 0 ? emptyState('No exercises yet', 'Add exercises from your program or search the library', '<circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>') : ''}
      </div>

      <div style="padding:0 16px 12px;display:flex;gap:8px">
        <button class="btn-secondary" style="flex:1" onclick="openExerciseSearch()">+ Add Exercise</button>
      </div>

      <div class="session-footer">
        <div class="session-rpe-label">
          <span>SESSION RPE</span>
          <span class="mono text-amber" id="session-rpe-val">${aw.sessionRpe}</span>
        </div>
        <input type="range" class="rpe-slider" min="6" max="10" step="0.5" value="${aw.sessionRpe}" id="session-rpe-slider"
          oninput="activeWorkout.sessionRpe=parseFloat(this.value);document.getElementById('session-rpe-val').textContent=this.value">
        <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--gray-dim);margin-top:2px">
          <span>6 \u2014 Easy</span><span>8 \u2014 Hard</span><span>10 \u2014 Max</span>
        </div>
        <div style="margin-top:12px">
          <label style="font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:var(--gray-mid);display:block;margin-bottom:6px">NOTES</label>
          <textarea rows="2" placeholder="Session notes..." style="resize:none;background:var(--bg-input);border:1px solid var(--border-normal);color:var(--white);padding:10px 12px;border-radius:8px;font-size:14px;outline:none;width:100%"
            oninput="activeWorkout.notes=this.value">${aw.notes}</textarea>
        </div>
        <div style="margin-top:12px">
          <button class="btn-primary btn-full" onclick="finishWorkout()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6L9 17l-5-5"/></svg>
            FINISH WORKOUT
          </button>
        </div>
      </div>
    </div>`;
}

// ── Set Input / Logging ──────────────────────────────

function onSetInput(exIdx, sIdx) {
    const w = parseFloat($id(`set-w-${exIdx}-${sIdx}`)?.value) || null;
    const r = parseInt($id(`set-r-${exIdx}-${sIdx}`)?.value) || null;
    const rpe = parseFloat($id(`set-rpe-${exIdx}-${sIdx}`)?.value) || null;
    const rir = parseInt($id(`set-rir-${exIdx}-${sIdx}`)?.value) || null;

    if (activeWorkout.exercises[exIdx]?.sets[sIdx]) {
        const set = activeWorkout.exercises[exIdx].sets[sIdx];
        if (w !== null) set.weight = w;
        if (r !== null) set.reps = r;
        if (rpe !== null) set.rpe = rpe;
        if (rir !== null) set.rir = rir;
    }

    const e1rm = calcE1rm(w, r, rpe);
    const e1rmEl = $id(`e1rm-ex-${exIdx}`);
    if (e1rmEl && e1rm) {
        e1rmEl.innerHTML = `e1RM: <strong>${e1rm}</strong> lbs`;
        activeWorkout.exercises[exIdx].e1rm = e1rm;
    }
}

function logSet(exIdx, sIdx) {
    const set = activeWorkout.exercises[exIdx]?.sets[sIdx];
    if (!set) return;

    const w = parseFloat($id(`set-w-${exIdx}-${sIdx}`)?.value) || set.weight;
    const r = parseInt($id(`set-r-${exIdx}-${sIdx}`)?.value) || set.reps;
    const rpe = parseFloat($id(`set-rpe-${exIdx}-${sIdx}`)?.value) || set.rpe;

    set.weight = w; set.reps = r; set.rpe = rpe;
    set.logged = true;

    const row = $id(`set-row-${exIdx}-${sIdx}`);
    const btn = $id(`set-log-${exIdx}-${sIdx}`);
    if (row) row.classList.add('logged');
    if (btn) btn.classList.add('done');

    const e1rm = calcE1rm(w, r, rpe);
    if (e1rm) {
        const e1rmEl = $id(`e1rm-ex-${exIdx}`);
        if (e1rmEl) e1rmEl.innerHTML = `e1RM: <strong>${e1rm}</strong> lbs`;
        activeWorkout.exercises[exIdx].e1rm = e1rm;
    }

    const restSecs = set.rest_seconds || 120;
    startRestTimer(restSecs);
    showToast(`Set logged${e1rm ? ` \u00b7 ${e1rm} lbs e1RM` : ''}`, 'success', 2500);
}

function addSet(exIdx) {
    const ex = activeWorkout.exercises[exIdx];
    if (!ex) return;
    const lastSet = ex.sets[ex.sets.length - 1] || {};
    const newSet = {
        set_number: ex.sets.length + 1,
        set_type: 'working',
        weight: lastSet.weight || '',
        reps: lastSet.reps || '',
        rpe: lastSet.rpe || '',
        rir: lastSet.rir || '',
        logged: false,
        rest_seconds: lastSet.rest_seconds || 120,
    };
    ex.sets.push(newSet);
    const sIdx = ex.sets.length - 1;
    const container = $id(`sets-container-${exIdx}`);
    if (container) {
        container.insertAdjacentHTML('beforeend', buildSetRow(newSet, exIdx, sIdx));
    }
}

function removeExercise(exIdx) {
    activeWorkout.exercises.splice(exIdx, 1);
    renderActiveWorkout();
}

function setCurrentSetType(exIdx, type) {
    activeWorkout.exercises[exIdx].currentSetType = type;
    const block = $id(`ex-block-${exIdx}`);
    if (block) {
        block.querySelectorAll('.stype-pill').forEach((p, i) => {
            p.classList.toggle('active', SET_TYPES[i] === type);
        });
    }
}

function toggleRpeTooltip(btn) {
    const wrapper = btn.closest('.rpe-tooltip-wrapper');
    if (!wrapper) return;
    const tooltip = wrapper.querySelector('.rpe-scale-tooltip');
    if (!tooltip) return;
    tooltip.classList.toggle('visible');
    const close = (e) => {
        if (!wrapper.contains(e.target)) {
            tooltip.classList.remove('visible');
            document.removeEventListener('click', close);
        }
    };
    setTimeout(() => document.addEventListener('click', close), 10);
}

// ── Finish / Discard ─────────────────────────────────

function discardWorkout() {
    if (!confirm('Discard this workout? All data will be lost.')) return;
    activeWorkout.running = false;
    stopWorkoutTimer();
    window.navigate('dashboard');
}

async function finishWorkout() {
    const aw = activeWorkout;
    const loggedSets = aw.exercises.flatMap((ex) =>
        ex.sets.filter(s => s.logged).map(s => ({
            exercise_id: ex.exercise.id,
            set_number: s.set_number,
            set_type: s.set_type || 'working',
            weight: s.weight || 0,
            reps: s.reps || 0,
            rpe: s.rpe || null,
            rir: s.rir || null,
            tempo: s.tempo || '',
            rest_seconds: s.rest_seconds || 120,
            notes: s.notes || '',
        }))
    );

    if (loggedSets.length === 0) {
        showToast('Log at least one set before finishing', 'error');
        return;
    }

    const duration = aw.startTime ? Math.round((Date.now() - aw.startTime) / 60000) : null;

    const payload = {
        athlete_id: ATHLETE_ID,
        program_id: aw.programId || null,
        session_id: aw.sessionId || null,
        date: new Date().toISOString().split('T')[0],
        duration_min: duration,
        notes: aw.notes || '',
        session_rpe: aw.sessionRpe || null,
        body_weight: aw.bodyWeight || null,
        sets: loggedSets,
    };

    const btn = document.querySelector('.session-footer .btn-primary');
    if (btn) { btn.disabled = true; btn.innerHTML = '<div class="spinner spinner-sm"></div> SAVING...'; }

    try {
        await saveWorkout(payload);
        activeWorkout.running = false;
        stopWorkoutTimer();
        showToast(`Workout saved! ${loggedSets.length} sets logged.`, 'success');
        window.navigate('dashboard');
    } catch (e) {
        console.error(e);
        showToast('Error saving workout', 'error');
        if (btn) { btn.disabled = false; btn.innerHTML = 'FINISH WORKOUT'; }
    }
}

// ── Exercise Search Modal ────────────────────────────

function openExerciseSearch() {
    const modal = document.createElement('div');
    modal.className = 'exercise-search-modal';
    modal.id = 'ex-search-modal';
    modal.innerHTML = `
    <div class="exercise-search-header">
      <button class="btn-icon" onclick="document.getElementById('ex-search-modal').remove()">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
      </button>
      <div style="flex:1;position:relative">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="position:absolute;left:10px;top:50%;transform:translateY(-50%);color:var(--gray-dim)">
          <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
        </svg>
        <input type="text" class="search-input" style="padding-left:36px" placeholder="Search exercises..." id="ex-search-input" oninput="filterExSearchModal(this.value)">
      </div>
    </div>
    <div class="exercise-search-results" id="ex-search-results">
      ${loadingSpinnerSm()}
    </div>`;
    document.body.appendChild(modal);
    setTimeout(() => document.getElementById('ex-search-input')?.focus(), 100);
    renderExSearchResults('');
}

async function renderExSearchResults(query) {
    const container = $id('ex-search-results');
    if (!container) return;
    let exercises = state.exercises || [];
    if (!exercises.length) {
        const res = await getExercises().catch(() => ({ exercises: [] }));
        state.exercises = exercises = res.exercises || res || [];
    }
    const filtered = query
        ? exercises.filter(e => e.name.toLowerCase().includes(query.toLowerCase()))
        : exercises.slice(0, 50);

    container.innerHTML = filtered.length
        ? filtered.map(ex => `
        <div class="exercise-card" onclick="addExerciseToWorkout(${JSON.stringify(ex).replace(/"/g, '&quot;')})">
          <div class="exercise-card-info">
            <div class="exercise-card-name">${ex.name}</div>
            <div style="display:flex;gap:6px;margin-top:4px;flex-wrap:wrap">
              <span class="badge badge-gray">${formatPattern(ex.movement_pattern)}</span>
              <span style="font-size:11px;color:var(--gray-dim)">${(ex.primary_muscles || '').split(',').slice(0, 2).join(', ')}</span>
            </div>
          </div>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#F5A623" stroke-width="2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
        </div>`).join('')
        : emptyState('No exercises found');
}

function filterExSearchModal(q) {
    clearTimeout(window._exSearchTimeout);
    window._exSearchTimeout = setTimeout(() => renderExSearchResults(q), 250);
}

function addExerciseToWorkout(exData) {
    let ex;
    try { ex = typeof exData === 'string' ? JSON.parse(exData) : exData; } catch (e) { return; }
    activeWorkout.exercises.push({
        exercise: ex,
        sets: [
            { set_number: 1, set_type: 'warmup', weight: '', reps: '', rpe: '', rir: '', logged: false, rest_seconds: 120 },
            { set_number: 2, set_type: 'working', weight: '', reps: '', rpe: '', rir: '', logged: false, rest_seconds: 120 },
            { set_number: 3, set_type: 'working', weight: '', reps: '', rpe: '', rir: '', logged: false, rest_seconds: 120 },
        ],
        overloadRec: null, e1rm: null, superset_group: null,
    });
    // Fetch overload rec
    getOverloadRec(ex.id).then(r => {
        const found = activeWorkout.exercises.find(e => e.exercise.id === ex.id);
        if (found) found.overloadRec = r;
    }).catch(() => {});

    $id('ex-search-modal')?.remove();
    renderActiveWorkout();
    showToast(`${ex.name} added`, 'success', 1500);
}

// ── Window globals for inline onclick ────────────────
// activeWorkout must be on window for the inline RPE slider and notes textarea
window.activeWorkout = activeWorkout;
window.startProgramSession = startProgramSession;
window.startCustomWorkout = startCustomWorkout;
window.addSet = addSet;
window.logSet = logSet;
window.removeExercise = removeExercise;
window.setCurrentSetType = setCurrentSetType;
window.toggleRpeTooltip = toggleRpeTooltip;
window.finishWorkout = finishWorkout;
window.discardWorkout = discardWorkout;
window.openExerciseSearch = openExerciseSearch;
window.addExerciseToWorkout = addExerciseToWorkout;
window.filterExSearchModal = filterExSearchModal;
window.onSetInput = onSetInput;
