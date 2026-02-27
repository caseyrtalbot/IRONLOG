/**
 * IRONLOG — Elite Strength Training Intelligence
 * app.js — Main application: routing, state, API, all views
 */

'use strict';

// ─────────────────────────────────────────────
// CONSTANTS & CONFIG
// ─────────────────────────────────────────────
const API_BASE = 'cgi-bin/api.py';
const ATHLETE_ID = 1;

const RPE_SCALE = [
  { val: 10,  desc: 'Max effort — could not do more' },
  { val: 9.5, desc: 'Could maybe do 1 more' },
  { val: 9,   desc: '1 RIR — definitely 1 left' },
  { val: 8.5, desc: '1–2 RIR' },
  { val: 8,   desc: '2 RIR — solid working set' },
  { val: 7.5, desc: '2–3 RIR' },
  { val: 7,   desc: '3 RIR — warm/moderate' },
  { val: 6,   desc: '4+ RIR — easy' },
];

const SET_TYPES = ['working','warmup','backoff','amrap','drop','cluster'];

const GOAL_INFO = {
  strength:     { label: 'Strength',    desc: 'Max force production. Low reps (1–5), high intensity (85–100% 1RM), long rest.' },
  hypertrophy:  { label: 'Hypertrophy', desc: 'Muscle growth. Moderate reps (6–15), moderate intensity (65–80% 1RM), pump focus.' },
  power:        { label: 'Power',       desc: 'Speed-strength. Med reps (1–5) explosive, 50–80% 1RM, full recovery.' },
  endurance:    { label: 'Endurance',   desc: 'Muscular endurance. High reps (15–30), lighter loads, short rest.' },
};
const PHASE_INFO = {
  accumulation:    { label: 'Accumulation',    desc: 'High volume, moderate intensity. Build work capacity. Foundation phase.' },
  intensification: { label: 'Intensification', desc: 'Moderate volume, high intensity. Convert volume gains to strength.' },
  realization:     { label: 'Realization',     desc: 'Low volume, maximal intensity. Peak performance — competition prep.' },
  deload:          { label: 'Deload',          desc: 'Reduced volume & intensity. Active recovery to supercompensate.' },
};
const SPLIT_INFO = {
  upper_lower:    { label: 'Upper / Lower',    desc: '2-day frequency split. Horizontal/vertical push+pull each session.' },
  push_pull_legs: { label: 'Push / Pull / Legs', desc: '3-way split. Push muscles, pull muscles, leg day each block.' },
  full_body:      { label: 'Full Body',        desc: 'Full body each session. Max frequency, great for 3-4 days/week.' },
};

// ─────────────────────────────────────────────
// GLOBAL APP STATE  (in-memory only, no storage APIs)
// ─────────────────────────────────────────────
window.APP_STATE = {
  athlete: null,
  dashboard: null,
  exercises: null,        // cached exercise list
  movementPatterns: null,
  muscleGroups: null,
  programs: null,
  e1rms: null,
  currentRoute: 'dashboard',
  charts: {},             // chart instances by id

  // Active workout
  activeWorkout: {
    running: false,
    startTime: null,
    timerInterval: null,
    sessionId: null,
    programId: null,
    exercises: [],        // [{exercise, sets:[{...}], overloadRec, e1rm}]
    sessionRpe: 7,
    notes: '',
    bodyWeight: null,
  },

  // Rest timer
  restTimer: {
    running: false,
    totalSeconds: 120,
    remainingSeconds: 120,
    interval: null,
  },

  // UI ephemeral
  exerciseFilter: { pattern: 'all', equipment: 'all', muscle: 'all', query: '' },
  programGen: { step: 1, goal: null, phase: null, split: null, weeks: 4, days: 4, name: '' },
  analyticsRange: 30,
  selectedProgramId: null,
  generatingProgram: false,
};

const S = window.APP_STATE; // shorthand

// ─────────────────────────────────────────────
// API LAYER
// ─────────────────────────────────────────────
async function api(action, params = {}, method = 'GET', body = null) {
  try {
    const qs = new URLSearchParams({ action, ...params }).toString();
    const url = `${API_BASE}?${qs}`;
    const opts = { method };
    if (body) {
      opts.headers = { 'Content-Type': 'application/json' };
      opts.body = JSON.stringify(body);
    }
    const res = await fetch(url, opts);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch(e) {
    console.error('API error:', action, e);
    throw e;
  }
}

const API = {
  getDashboard:       ()         => api('get_dashboard', { athlete_id: ATHLETE_ID }),
  getAthlete:         ()         => api('get_athlete', { id: ATHLETE_ID }),
  saveAthlete:        (data)     => api('save_athlete', {}, 'POST', data),
  getExercises:       (p={})     => api('get_exercises', p),
  searchExercises:    (q)        => api('search_exercises', { q }),
  getMovementPatterns:()         => api('get_movement_patterns'),
  getMuscleGroups:    ()         => api('get_muscle_groups'),
  getPrograms:        ()         => api('get_programs', { athlete_id: ATHLETE_ID }),
  getProgram:         (id)       => api('get_program', { id }),
  generateProgram:    (data)     => api('generate_program', {}, 'POST', data),
  saveWorkout:        (data)     => api('save_workout', {}, 'POST', data),
  getWorkouts:        (limit=20) => api('get_workouts', { athlete_id: ATHLETE_ID, limit }),
  getWorkoutDetail:   (id)       => api('get_workout_detail', { id }),
  deleteWorkout:      (id)       => api('delete_workout', { id }),
  getE1rm:            (exId, days=90) => api('get_e1rm', { athlete_id: ATHLETE_ID, exercise_id: exId, days }),
  getAllE1rms:         ()         => api('get_e1rm', { athlete_id: ATHLETE_ID }),
  getOverloadRec:     (exId)     => api('get_overload_rec', { athlete_id: ATHLETE_ID, exercise_id: exId }),
  getAnalytics:       (days, metric) => api('get_analytics', { athlete_id: ATHLETE_ID, days, metric }),
  getVolumeLandmarks: ()         => api('get_volume_landmarks', { athlete_id: ATHLETE_ID }),
  saveVolumeLandmarks:(data)     => api('save_volume_landmarks', {}, 'POST', data),
  getPhaseConfig:     (goal, phase) => api('get_phase_config', { goal, phase }),
};

// ─────────────────────────────────────────────
// UTILITY
// ─────────────────────────────────────────────
function calcE1rm(weight, reps, rpe) {
  if (!weight || !reps) return null;
  // Epley formula with RPE adjustment
  let effectiveReps = reps;
  if (rpe && rpe < 10) {
    const rir = 10 - rpe;
    effectiveReps = reps + rir;
  }
  if (effectiveReps <= 0) return weight;
  return +(weight * (1 + effectiveReps / 30)).toFixed(1);
}

function rpeColor(rpe) {
  if (!rpe) return '';
  if (rpe <= 7) return 'rpe-green';
  if (rpe <= 8.5) return 'rpe-amber';
  return 'rpe-red';
}

function fmtDate(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr.replace(' ', 'T'));
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function fmtDuration(min) {
  if (!min) return '—';
  const h = Math.floor(min / 60);
  const m = min % 60;
  return h ? `${h}h ${m}m` : `${m}m`;
}

function fmtSecondsTimer(s) {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${sec.toString().padStart(2,'0')}`;
}

function capitalize(str) {
  return str ? str.charAt(0).toUpperCase() + str.slice(1) : '';
}

function formatPattern(p) {
  return p ? p.split('_').map(capitalize).join(' ') : '';
}

function formatGoal(g) { return GOAL_INFO[g]?.label || capitalize(g); }
function formatPhase(p) { return PHASE_INFO[p]?.label || capitalize(p); }

function dotsHtml(filled, total=5) {
  let h = '<div class="dots-rating">';
  for (let i=1;i<=total;i++) h += `<div class="dot ${i<=filled?'filled':'empty'}"></div>`;
  return h + '</div>';
}

function showToast(msg, type='info', duration=3000) {
  const tc = document.getElementById('toast-container');
  if (!tc) return;
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  const icons = { success:'✓', error:'✗', info:'→' };
  t.innerHTML = `<span style="font-weight:800">${icons[type]||'→'}</span> ${msg}`;
  tc.appendChild(t);
  setTimeout(() => { t.style.opacity='0'; t.style.transform='translateY(4px)'; t.style.transition='0.2s ease'; setTimeout(()=>t.remove(),200); }, duration);
}

function $id(id) { return document.getElementById(id); }

function destroyChart(key) {
  if (S.charts[key]) { S.charts[key].destroy(); delete S.charts[key]; }
}

// ─────────────────────────────────────────────
// ROUTING
// ─────────────────────────────────────────────
const routes = {
  dashboard: renderDashboard,
  workout:   renderWorkout,
  exercises: renderExercises,
  programs:  renderPrograms,
  analytics: renderAnalytics,
  profile:   renderProfile,
};

function navigate(route) {
  if (!routes[route]) route = 'dashboard';
  S.currentRoute = route;
  history.replaceState(null, '', '#' + route);

  // Update nav
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.route === route);
  });

  // Transition
  const vc = $id('view-container');
  vc.classList.add('transitioning');
  setTimeout(() => {
    vc.classList.remove('transitioning');
    // Destroy old charts
    Object.keys(S.charts).forEach(destroyChart);
    vc.innerHTML = '';
    routes[route]();
  }, 140);
}

function handleHash() {
  const hash = location.hash.slice(1) || 'dashboard';
  navigate(routes[hash] ? hash : 'dashboard');
}

// ─────────────────────────────────────────────
// APP INIT
// ─────────────────────────────────────────────
async function initApp() {
  try {
    // Load athlete
    const athleteRes = await API.getAthlete().catch(() => null);
    if (athleteRes && athleteRes.id) {
      S.athlete = athleteRes;
      // Update streak badge
      updateStreakBadge();
    } else {
      showOnboarding();
      return;
    }

    // Prefetch exercises in background
    API.getExercises().then(res => { S.exercises = res.exercises || res || []; });
    API.getMovementPatterns().then(res => { S.movementPatterns = res.patterns || res || []; });
    API.getMuscleGroups().then(res => { S.muscleGroups = res.groups || res || []; });

    // Hide loader
    setTimeout(() => {
      $id('page-loader').classList.add('hidden');
    }, 800);

    // Route
    handleHash();
    window.addEventListener('hashchange', handleHash);

  } catch(e) {
    console.error('Init error:', e);
    $id('page-loader').classList.add('hidden');
    showOnboarding();
  }
}

function updateStreakBadge() {
  if (!S.dashboard) return;
  const streak = S.dashboard.streak || 0;
  const badge = $id('streak-badge');
  const count = $id('streak-count');
  if (streak > 0) {
    count.textContent = streak;
    badge.classList.remove('hidden');
  }
}

// ─────────────────────────────────────────────
// ONBOARDING
// ─────────────────────────────────────────────
function showOnboarding() {
  $id('page-loader').classList.add('hidden');
  const modal = $id('onboarding-modal');
  modal.classList.remove('hidden');

  // Pill selectors
  modal.querySelectorAll('.pill-selector').forEach(ps => {
    ps.querySelectorAll('.pill').forEach(p => {
      p.addEventListener('click', () => {
        ps.querySelectorAll('.pill').forEach(x=>x.classList.remove('active'));
        p.classList.add('active');
      });
    });
  });

  $id('ob-submit').addEventListener('click', async () => {
    const name = $id('ob-name').value.trim();
    if (!name) { showToast('Please enter your name', 'error'); return; }

    const data = {
      id: ATHLETE_ID,
      name,
      age: parseInt($id('ob-age').value) || null,
      body_weight: parseFloat($id('ob-weight').value) || null,
      experience_level: modal.querySelector('#ob-experience .pill.active')?.dataset.value || 'intermediate',
      primary_goal: modal.querySelector('#ob-goal .pill.active')?.dataset.value || 'strength',
      training_days_per_week: parseInt($id('ob-days').value) || 4,
      session_duration_min: parseInt($id('ob-duration').value) || 75,
    };

    const btn = $id('ob-submit');
    btn.disabled = true; btn.innerHTML = '<div class="spinner spinner-sm"></div> SAVING...';

    try {
      const res = await API.saveAthlete(data);
      S.athlete = res.athlete || data;
      modal.classList.add('hidden');
      showToast('Profile saved! Welcome to IRONLOG.', 'success');

      // Prefetch
      API.getExercises().then(r => { S.exercises = r.exercises || r || []; });
      API.getMovementPatterns().then(r => { S.movementPatterns = r.patterns || r || []; });
      API.getMuscleGroups().then(r => { S.muscleGroups = r.groups || r || []; });

      window.addEventListener('hashchange', handleHash);
      navigate('dashboard');
    } catch(e) {
      showToast('Error saving profile', 'error');
      btn.disabled = false; btn.innerHTML = 'START TRAINING →';
    }
  });
}

// ─────────────────────────────────────────────
// WORKOUT TIMER (header)
// ─────────────────────────────────────────────
function startWorkoutTimer() {
  const display = $id('workout-timer-display');
  const text = $id('workout-timer-text');
  display.classList.remove('hidden');
  S.activeWorkout.timerInterval = setInterval(() => {
    if (!S.activeWorkout.startTime) return;
    const elapsed = Math.floor((Date.now() - S.activeWorkout.startTime) / 1000);
    text.textContent = fmtSecondsTimer(elapsed);
  }, 1000);
}

function stopWorkoutTimer() {
  clearInterval(S.activeWorkout.timerInterval);
  $id('workout-timer-display').classList.add('hidden');
  $id('workout-timer-text').textContent = '0:00';
}

// ─────────────────────────────────────────────
// REST TIMER
// ─────────────────────────────────────────────
function startRestTimer(seconds=120) {
  const overlay = $id('rest-timer-overlay');
  const display = $id('rest-timer-display');
  const ring = $id('rest-ring-progress');
  const circumference = 276.46;

  clearInterval(S.restTimer.interval);
  S.restTimer.totalSeconds = seconds;
  S.restTimer.remainingSeconds = seconds;
  S.restTimer.running = true;
  overlay.classList.remove('hidden');
  display.textContent = fmtSecondsTimer(seconds);
  ring.style.strokeDashoffset = '0';

  S.restTimer.interval = setInterval(() => {
    S.restTimer.remainingSeconds--;
    const rem = S.restTimer.remainingSeconds;
    display.textContent = fmtSecondsTimer(rem);
    const offset = circumference * (1 - rem / S.restTimer.totalSeconds);
    ring.style.strokeDashoffset = offset.toFixed(2);
    if (rem <= 0) {
      clearInterval(S.restTimer.interval);
      S.restTimer.running = false;
      overlay.classList.add('hidden');
      showToast('Rest complete — next set!', 'success');
      // Vibrate if available
      if (navigator.vibrate) navigator.vibrate([100, 50, 100]);
    }
  }, 1000);
}

window.APP = {
  adjustRestTimer(delta) {
    S.restTimer.remainingSeconds = Math.max(5, S.restTimer.remainingSeconds + delta);
    S.restTimer.totalSeconds = Math.max(S.restTimer.totalSeconds, S.restTimer.remainingSeconds);
    $id('rest-timer-display').textContent = fmtSecondsTimer(S.restTimer.remainingSeconds);
  },
  skipRestTimer() {
    clearInterval(S.restTimer.interval);
    S.restTimer.running = false;
    $id('rest-timer-overlay').classList.add('hidden');
  },
};

// ─────────────────────────────────────────────
// VIEW: DASHBOARD
// ─────────────────────────────────────────────
async function renderDashboard() {
  const vc = $id('view-container');
  vc.innerHTML = `<div class="view"><div class="loading-center"><div class="spinner"></div><span>Loading dashboard...</span></div></div>`;

  try {
    const data = await API.getDashboard();
    S.dashboard = data;
    updateStreakBadge();

    const athlete = S.athlete || {};
    const firstName = (athlete.name || 'Athlete').split(' ')[0];
    const streak = data.streak || 0;
    const totalWorkouts = data.total_workouts || 0;
    const recentPRs = data.recent_prs || [];
    const recentWorkouts = data.recent_workouts || [];
    const activeProgram = data.active_program || null;

    let activeProgramHtml = '';
    if (activeProgram) {
      const pct = Math.round((activeProgram.current_week / activeProgram.mesocycle_weeks) * 100);
      activeProgramHtml = `
        <div class="active-program-card" onclick="navigate('programs'); setTimeout(()=>selectProgram(${activeProgram.id}),200)">
          <div class="prog-card-top">
            <div>
              <div class="prog-card-name">${activeProgram.name}</div>
              <div class="prog-card-sub">${formatGoal(activeProgram.goal)} · ${formatPhase(activeProgram.phase)}</div>
            </div>
            <div class="prog-week-badge">WK ${activeProgram.current_week}/${activeProgram.mesocycle_weeks}</div>
          </div>
          <div class="prog-progress-bar"><div class="prog-progress-fill" style="width:${pct}%"></div></div>
          <div style="display:flex;gap:6px">
            <span class="badge badge-amber">${formatPhase(activeProgram.phase)}</span>
            <span class="badge badge-gray">${activeProgram.mesocycle_weeks} weeks</span>
          </div>
        </div>`;
    }

    let prsHtml = '';
    if (recentPRs.length) {
      prsHtml = recentPRs.slice(0,5).map(pr => `
        <div class="pr-item">
          <div class="pr-item-left">
            <div class="pr-item-name">${pr.exercise_name || '—'}</div>
            <div class="pr-item-date">${fmtDate(pr.date)}</div>
          </div>
          <div class="pr-item-right">
            <div class="pr-item-val">${pr.estimated_1rm ? pr.estimated_1rm.toFixed(0) : '—'}</div>
            <div class="pr-item-unit">lbs e1RM <span class="badge badge-pr ml-2">PR</span></div>
          </div>
        </div>`).join('');
    } else {
      prsHtml = `<div class="text-dim text-sm" style="padding:12px 0">No PRs yet — start training!</div>`;
    }

    let workoutsHtml = '';
    if (recentWorkouts.length) {
      workoutsHtml = recentWorkouts.slice(0,7).map(w => {
        const rpeColor_ = w.session_rpe ? (w.session_rpe >= 9 ? 'rpe-red' : w.session_rpe >= 7.5 ? 'rpe-amber' : 'rpe-green') : '';
        return `
          <div class="workout-history-item" onclick="viewWorkout(${w.id})">
            <div class="wh-date">${fmtDate(w.date)}</div>
            <div class="wh-info">
              <div class="wh-title">${w.notes || (w.session_name || 'Workout')}</div>
              <div class="wh-meta">${fmtDuration(w.duration_min)} · ${w.total_volume ? Math.round(w.total_volume).toLocaleString() + ' lbs' : '—'}</div>
            </div>
            <div class="wh-rpe ${rpeColor_}">${w.session_rpe || '—'}</div>
          </div>`;
      }).join('');
    } else {
      workoutsHtml = `<div class="text-dim text-sm" style="padding:12px 0">No workouts logged yet.</div>`;
    }

    vc.innerHTML = `
      <div class="view">
        <div class="dashboard-hero">
          <div class="hero-greeting">GOOD ${getTimeOfDay()}</div>
          <div class="hero-name">${firstName}</div>
          <div class="hero-stats">
            <div class="hero-stat">
              <div class="hero-stat-val">${streak}</div>
              <div class="hero-stat-label">Day Streak</div>
            </div>
            <div class="hero-stat" style="border-left:1px solid var(--border-dim);padding-left:16px">
              <div class="hero-stat-val">${totalWorkouts}</div>
              <div class="hero-stat-label">Workouts</div>
            </div>
            ${data.weekly_volume ? `<div class="hero-stat" style="border-left:1px solid var(--border-dim);padding-left:16px">
              <div class="hero-stat-val">${Math.round(data.weekly_volume/1000).toFixed(0)}k</div>
              <div class="hero-stat-label">Vol/Week</div>
            </div>` : ''}
          </div>
        </div>

        ${activeProgramHtml}

        <div class="quick-actions">
          <div class="quick-action" onclick="navigate('workout')">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <rect x="1" y="11" width="4" height="3" rx="0.5" stroke="currentColor" stroke-width="1.8"/>
              <rect x="5" y="8.5" width="2" height="7" rx="0.5" stroke="currentColor" stroke-width="1.8"/>
              <rect x="7" y="6" width="10" height="12" rx="1" stroke="currentColor" stroke-width="1.8"/>
              <rect x="17" y="8.5" width="2" height="7" rx="0.5" stroke="currentColor" stroke-width="1.8"/>
              <rect x="19" y="11" width="4" height="3" rx="0.5" stroke="currentColor" stroke-width="1.8"/>
              <line x1="12" y1="9" x2="12" y2="15" stroke="currentColor" stroke-width="1.5"/>
              <line x1="9.5" y1="12" x2="14.5" y2="12" stroke="currentColor" stroke-width="1.5"/>
            </svg>
            <span>Start<br>Workout</span>
          </div>
          <div class="quick-action" onclick="navigate('programs')">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/>
              <line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
            <span>View<br>Program</span>
          </div>
          <div class="quick-action" onclick="navigate('exercises')">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M4 6h16M4 10h16M4 14h10M4 18h7"/>
            </svg>
            <span>Exercise<br>Library</span>
          </div>
        </div>

        <div class="section">
          <div class="section-header">
            <div class="section-title">Recent PRs</div>
            <div class="section-action" onclick="navigate('analytics')">View All →</div>
          </div>
          <div class="card" style="padding:0 16px">${prsHtml}</div>
        </div>

        <div class="section">
          <div class="section-header">
            <div class="section-title">Recent Workouts</div>
            <div class="section-action" onclick="navigate('analytics')">History →</div>
          </div>
          <div class="card" style="padding:0 16px">${workoutsHtml}</div>
        </div>
      </div>`;
  } catch(e) {
    console.error(e);
    vc.innerHTML = `<div class="view"><div class="empty-state">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>
      <h3>Could not load dashboard</h3>
      <p>Check your connection</p>
      <button class="btn-primary" onclick="navigate('dashboard')">Retry</button>
    </div></div>`;
  }
}

function getTimeOfDay() {
  const h = new Date().getHours();
  if (h < 12) return 'MORNING';
  if (h < 17) return 'AFTERNOON';
  return 'EVENING';
}

function viewWorkout(id) {
  // Navigate to analytics or show detail toast
  showToast('Workout detail coming soon', 'info');
}

// ─────────────────────────────────────────────
// VIEW: WORKOUT TRACKER
// ─────────────────────────────────────────────
async function renderWorkout() {
  const vc = $id('view-container');

  if (S.activeWorkout.running) {
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
        <div class="loading-center"><div class="spinner"></div><span>Loading programs...</span></div>
      </div>
    </div>`;

  try {
    const [programsRes, athlete] = await Promise.all([
      API.getPrograms(),
      Promise.resolve(S.athlete || await API.getAthlete()),
    ]);
    const programs = programsRes.programs || [];
    const activePrograms = programs.filter(p => p.status === 'active');

    let sessionsHtml = '';
    for (const prog of activePrograms) {
      try {
        const detail = await API.getProgram(prog.id);
        const sessions = detail.sessions || [];
        sessions.forEach(sess => {
          const exCount = sess.exercises ? sess.exercises.length : 0;
          sessionsHtml += `
            <div class="session-option" onclick="startProgramSession(${prog.id},${sess.id})">
              <div>
                <div class="session-opt-name">${sess.name}</div>
                <div class="session-opt-meta">${prog.name} · ${exCount} exercises</div>
              </div>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#F5A623" stroke-width="2" stroke-linecap="round"><path d="M9 18l6-6-6-6"/></svg>
            </div>`;
        });
      } catch(e) {}
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
  } catch(e) {
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

async function startProgramSession(programId, sessionId) {
  showToast('Loading session...', 'info');
  try {
    const detail = await API.getProgram(programId);
    const session = (detail.sessions || []).find(s => s.id === sessionId);
    if (!session) { showToast('Session not found', 'error'); return; }

    S.activeWorkout = {
      running: true,
      startTime: Date.now(),
      timerInterval: null,
      sessionId: sessionId,
      programId: programId,
      sessionName: session.name,
      exercises: [],
      sessionRpe: 7,
      notes: '',
      bodyWeight: S.athlete?.body_weight || null,
    };

    // Build exercises array from program
    for (const pe of (session.exercises || [])) {
      const sets = [];
      for (let i=1; i<=pe.sets_prescribed; i++) {
        sets.push({
          set_number: i,
          set_type: i === 1 ? 'warmup' : 'working',
          weight: '', reps: pe.reps_prescribed || '', rpe: pe.intensity_value || '',
          rir: '', logged: false,
          prescribed_reps: pe.reps_prescribed,
          prescribed_intensity: pe.intensity_value,
          intensity_type: pe.intensity_type,
          rest_seconds: pe.rest_seconds || 120,
        });
      }
      // Get overload rec in background
      let overloadRec = null;
      API.getOverloadRec(pe.exercise_id).then(r => {
        const exBlock = S.activeWorkout.exercises.find(e => e.exercise.id === pe.exercise_id);
        if (exBlock) exBlock.overloadRec = r;
        if (S.currentRoute === 'workout') renderActiveWorkout();
      }).catch(()=>{});

      S.activeWorkout.exercises.push({
        exercise: pe.exercise || { id: pe.exercise_id, name: pe.exercise_name || 'Exercise', movement_pattern: pe.movement_pattern || '' },
        sets,
        overloadRec: null,
        e1rm: null,
        superset_group: pe.superset_group || null,
      });
    }

    startWorkoutTimer();
    renderActiveWorkout();
  } catch(e) {
    console.error(e);
    showToast('Error loading session', 'error');
  }
}

function startCustomWorkout() {
  S.activeWorkout = {
    running: true,
    startTime: Date.now(),
    timerInterval: null,
    sessionId: null,
    programId: null,
    sessionName: 'Custom Workout',
    exercises: [],
    sessionRpe: 7,
    notes: '',
    bodyWeight: S.athlete?.body_weight || null,
  };
  startWorkoutTimer();
  renderActiveWorkout();
}

function renderActiveWorkout() {
  const vc = $id('view-container');
  const aw = S.activeWorkout;
  const elapsed = aw.startTime ? Math.floor((Date.now() - aw.startTime) / 1000) : 0;

  let exercisesHtml = aw.exercises.map((ex, exIdx) => buildExerciseBlock(ex, exIdx)).join('');

  vc.innerHTML = `
    <div class="view workout-active">
      <div class="workout-top-bar">
        <div class="session-name">${aw.sessionName || 'Workout'}</div>
        <button class="btn-ghost" style="padding:6px 10px;font-size:11px;min-height:36px" onclick="discardWorkout()">✕ Discard</button>
      </div>

      <div id="exercise-blocks-container">
        ${exercisesHtml}
        ${aw.exercises.length === 0 ? `<div class="empty-state" style="padding:32px 24px">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>
          <h3>No exercises yet</h3>
          <p>Add exercises from your program or search the library</p>
        </div>` : ''}
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
          oninput="S.activeWorkout.sessionRpe=parseFloat(this.value);document.getElementById('session-rpe-val').textContent=this.value">
        <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--gray-dim);margin-top:2px">
          <span>6 — Easy</span><span>8 — Hard</span><span>10 — Max</span>
        </div>
        <div style="margin-top:12px">
          <label style="font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:var(--gray-mid);display:block;margin-bottom:6px">NOTES</label>
          <textarea rows="2" placeholder="Session notes..." style="resize:none;background:var(--bg-input);border:1px solid var(--border-normal);color:var(--white);padding:10px 12px;border-radius:8px;font-size:14px;outline:none;width:100%"
            oninput="S.activeWorkout.notes=this.value">${aw.notes}</textarea>
        </div>
        <div style="margin-top:12px">
          <button class="btn-primary btn-full" onclick="finishWorkout()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6L9 17l-5-5"/></svg>
            FINISH WORKOUT
          </button>
        </div>
      </div>
    </div>`;

  // Attach event listeners for set inputs
  attachSetInputListeners();
}

function buildExerciseBlock(ex, exIdx) {
  const ssClass = ex.superset_group ? `superset-${ex.superset_group}` : '';
  const ssHtml = ex.superset_group ? `<span class="superset-label">${ex.superset_group}</span>` : '';

  const overloadHtml = ex.overloadRec ? `
    <div class="overload-rec">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
      ${ex.overloadRec.recommendation || 'Based on last session'}
    </div>` : '';

  const e1rmHtml = ex.e1rm ? `<div class="e1rm-inline">e1RM: <strong>${ex.e1rm}</strong> lbs</div>` : '<div class="e1rm-inline" id="e1rm-ex-'+exIdx+'"></div>';

  const setsHtml = ex.sets.map((set, sIdx) => buildSetRow(set, exIdx, sIdx)).join('');

  const rpeTooltipRows = RPE_SCALE.map(r => `
    <div class="rpe-scale-row">
      <span class="rpe-scale-num">${r.val}</span>
      <span class="rpe-scale-desc">${r.desc}</span>
    </div>`).join('');

  return `
    <div class="exercise-block ${ssClass}" id="ex-block-${exIdx}">
      <div class="exercise-block-header">
        ${ssHtml}
        <div style="flex:1;min-width:0">
          <div class="exercise-block-name">${ex.exercise.name}</div>
          <div class="exercise-block-meta">${formatPattern(ex.exercise.movement_pattern)} · ${ex.exercise.primary_muscles || ''}</div>
        </div>
        <div class="rpe-tooltip-wrapper">
          <button class="btn-icon" onclick="toggleRpeTooltip(this)" title="RPE Scale">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>
          </button>
          <div class="rpe-scale-tooltip" id="rpe-tooltip-${exIdx}">
            <div style="font-size:9px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:var(--gray-dim);margin-bottom:6px">TUCHSCHERER RPE SCALE</div>
            ${rpeTooltipRows}
          </div>
        </div>
        <button class="btn-icon" onclick="removeExercise(${exIdx})" title="Remove">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
        </button>
      </div>

      <div class="set-type-selector">
        ${SET_TYPES.map(t => `<button class="stype-pill ${ex.currentSetType===t?'active':''}" onclick="setCurrentSetType(${exIdx},'${t}')">${t.toUpperCase()}</button>`).join('')}
      </div>

      <div class="set-table-header">
        <div>SET</div><div>WEIGHT</div><div>REPS</div><div style="text-align:center">RPE</div><div style="text-align:center">RIR</div><div></div>
      </div>

      <div id="sets-container-${exIdx}">${setsHtml}</div>

      ${e1rmHtml}
      ${overloadHtml}

      <div class="add-set-row">
        <button class="add-set-btn" onclick="addSet(${exIdx})">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 5v14M5 12h14"/></svg>
          ADD SET
        </button>
      </div>
    </div>`;
}

function buildSetRow(set, exIdx, sIdx) {
  const typePill = `<span class="set-type-pill ${set.set_type}">${set.set_type === 'working' ? 'W' : set.set_type.charAt(0).toUpperCase()}</span>`;
  const doneClass = set.logged ? 'done' : '';
  const rowClass = set.logged ? 'logged' : '';

  return `
    <div class="set-row ${rowClass}" id="set-row-${exIdx}-${sIdx}">
      <div class="set-num">${typePill}</div>
      <div>
        <input type="number" class="set-input" inputmode="decimal" placeholder="${set.weight || '—'}"
          value="${set.weight || ''}" id="set-w-${exIdx}-${sIdx}"
          onchange="onSetInput(${exIdx},${sIdx})" oninput="onSetInput(${exIdx},${sIdx})">
      </div>
      <div>
        <input type="number" class="set-input" inputmode="decimal" placeholder="${set.reps || '—'}"
          value="${set.reps || ''}" id="set-r-${exIdx}-${sIdx}"
          onchange="onSetInput(${exIdx},${sIdx})" oninput="onSetInput(${exIdx},${sIdx})">
      </div>
      <div>
        <input type="number" class="set-input" inputmode="decimal" placeholder="RPE"
          value="${set.rpe || ''}" id="set-rpe-${exIdx}-${sIdx}" min="6" max="10" step="0.5"
          onchange="onSetInput(${exIdx},${sIdx})" oninput="onSetInput(${exIdx},${sIdx})">
      </div>
      <div>
        <input type="number" class="set-input" inputmode="decimal" placeholder="RIR"
          value="${set.rir || ''}" id="set-rir-${exIdx}-${sIdx}" min="0" max="5"
          onchange="onSetInput(${exIdx},${sIdx})" oninput="onSetInput(${exIdx},${sIdx})">
      </div>
      <div>
        <button class="set-log-btn ${doneClass}" id="set-log-${exIdx}-${sIdx}"
          onclick="logSet(${exIdx},${sIdx})" title="${set.logged?'Logged':'Log set'}">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6L9 17l-5-5"/></svg>
        </button>
      </div>
    </div>`;
}

function attachSetInputListeners() {
  // Already handled inline via onchange/oninput attrs
}

function onSetInput(exIdx, sIdx) {
  const w = parseFloat($id(`set-w-${exIdx}-${sIdx}`)?.value) || null;
  const r = parseInt($id(`set-r-${exIdx}-${sIdx}`)?.value) || null;
  const rpe = parseFloat($id(`set-rpe-${exIdx}-${sIdx}`)?.value) || null;
  const rir = parseInt($id(`set-rir-${exIdx}-${sIdx}`)?.value) || null;

  // Save to state
  if (S.activeWorkout.exercises[exIdx]?.sets[sIdx]) {
    const set = S.activeWorkout.exercises[exIdx].sets[sIdx];
    if (w !== null) set.weight = w;
    if (r !== null) set.reps = r;
    if (rpe !== null) set.rpe = rpe;
    if (rir !== null) set.rir = rir;
  }

  // Update e1RM display
  const e1rm = calcE1rm(w, r, rpe);
  const e1rmEl = $id(`e1rm-ex-${exIdx}`);
  if (e1rmEl && e1rm) {
    e1rmEl.innerHTML = `e1RM: <strong>${e1rm}</strong> lbs`;
    S.activeWorkout.exercises[exIdx].e1rm = e1rm;
  }
}

function logSet(exIdx, sIdx) {
  const set = S.activeWorkout.exercises[exIdx]?.sets[sIdx];
  if (!set) return;

  // Read current input values
  const w = parseFloat($id(`set-w-${exIdx}-${sIdx}`)?.value) || set.weight;
  const r = parseInt($id(`set-r-${exIdx}-${sIdx}`)?.value) || set.reps;
  const rpe = parseFloat($id(`set-rpe-${exIdx}-${sIdx}`)?.value) || set.rpe;

  set.weight = w; set.reps = r; set.rpe = rpe;
  set.logged = true;

  // Visual feedback
  const row = $id(`set-row-${exIdx}-${sIdx}`);
  const btn = $id(`set-log-${exIdx}-${sIdx}`);
  if (row) row.classList.add('logged');
  if (btn) btn.classList.add('done');

  // e1RM
  const e1rm = calcE1rm(w, r, rpe);
  if (e1rm) {
    const e1rmEl = $id(`e1rm-ex-${exIdx}`);
    if (e1rmEl) e1rmEl.innerHTML = `e1RM: <strong>${e1rm}</strong> lbs`;
    S.activeWorkout.exercises[exIdx].e1rm = e1rm;
  }

  // Start rest timer
  const restSecs = set.rest_seconds || 120;
  startRestTimer(restSecs);

  showToast(`Set logged${e1rm ? ` · ${e1rm} lbs e1RM` : ''}`, 'success', 2500);
}

function addSet(exIdx) {
  const ex = S.activeWorkout.exercises[exIdx];
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
  S.activeWorkout.exercises.splice(exIdx, 1);
  renderActiveWorkout();
}

function setCurrentSetType(exIdx, type) {
  S.activeWorkout.exercises[exIdx].currentSetType = type;
  // Re-render just that block
  const block = $id(`ex-block-${exIdx}`);
  if (block) {
    block.querySelectorAll('.stype-pill').forEach((p, i) => {
      p.classList.toggle('active', SET_TYPES[i] === type);
    });
  }
}

function toggleRpeTooltip(btn) {
  // Find the tooltip in the same wrapper
  const wrapper = btn.closest('.rpe-tooltip-wrapper');
  if (!wrapper) return;
  const tooltip = wrapper.querySelector('.rpe-scale-tooltip');
  if (!tooltip) return;
  tooltip.classList.toggle('visible');
  // Close on next click outside
  const close = (e) => {
    if (!wrapper.contains(e.target)) {
      tooltip.classList.remove('visible');
      document.removeEventListener('click', close);
    }
  };
  setTimeout(() => document.addEventListener('click', close), 10);
}

function discardWorkout() {
  if (!confirm('Discard this workout? All data will be lost.')) return;
  S.activeWorkout.running = false;
  stopWorkoutTimer();
  navigate('dashboard');
}

async function finishWorkout() {
  const aw = S.activeWorkout;
  const loggedSets = aw.exercises.flatMap((ex, exIdx) =>
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
    await API.saveWorkout(payload);
    S.activeWorkout.running = false;
    stopWorkoutTimer();
    showToast(`Workout saved! ${loggedSets.length} sets logged.`, 'success');
    navigate('dashboard');
  } catch(e) {
    console.error(e);
    showToast('Error saving workout', 'error');
    if (btn) { btn.disabled = false; btn.innerHTML = 'FINISH WORKOUT'; }
  }
}

// Exercise search modal for adding to workout
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
      <div class="loading-center"><div class="spinner"></div></div>
    </div>`;
  document.body.appendChild(modal);
  setTimeout(() => document.getElementById('ex-search-input')?.focus(), 100);
  renderExSearchResults('');
}

async function renderExSearchResults(query) {
  const container = $id('ex-search-results');
  if (!container) return;
  let exercises = S.exercises || [];
  if (!exercises.length) {
    const res = await API.getExercises().catch(() => ({ exercises: [] }));
    S.exercises = exercises = res.exercises || res || [];
  }
  const filtered = query
    ? exercises.filter(e => e.name.toLowerCase().includes(query.toLowerCase()))
    : exercises.slice(0, 50);

  container.innerHTML = filtered.length
    ? filtered.map(ex => `
        <div class="exercise-card" onclick="addExerciseToWorkout(${JSON.stringify(ex).replace(/"/g,'&quot;')})">
          <div class="exercise-card-info">
            <div class="exercise-card-name">${ex.name}</div>
            <div style="display:flex;gap:6px;margin-top:4px;flex-wrap:wrap">
              <span class="badge badge-gray">${formatPattern(ex.movement_pattern)}</span>
              <span style="font-size:11px;color:var(--gray-dim)">${(ex.primary_muscles||'').split(',').slice(0,2).join(', ')}</span>
            </div>
          </div>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#F5A623" stroke-width="2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
        </div>`).join('')
    : `<div class="empty-state"><h3>No exercises found</h3></div>`;
}

function filterExSearchModal(q) {
  clearTimeout(window._exSearchTimeout);
  window._exSearchTimeout = setTimeout(() => renderExSearchResults(q), 250);
}

function addExerciseToWorkout(exData) {
  let ex;
  try { ex = typeof exData === 'string' ? JSON.parse(exData) : exData; } catch(e) { return; }
  S.activeWorkout.exercises.push({
    exercise: ex, sets: [
      { set_number: 1, set_type: 'warmup', weight: '', reps: '', rpe: '', rir: '', logged: false, rest_seconds: 120 },
      { set_number: 2, set_type: 'working', weight: '', reps: '', rpe: '', rir: '', logged: false, rest_seconds: 120 },
      { set_number: 3, set_type: 'working', weight: '', reps: '', rpe: '', rir: '', logged: false, rest_seconds: 120 },
    ],
    overloadRec: null, e1rm: null, superset_group: null,
  });
  // Fetch overload rec
  API.getOverloadRec(ex.id).then(r => {
    const found = S.activeWorkout.exercises.find(e => e.exercise.id === ex.id);
    if (found) found.overloadRec = r;
  }).catch(()=>{});

  $id('ex-search-modal')?.remove();
  renderActiveWorkout();
  showToast(`${ex.name} added`, 'success', 1500);
}

// ─────────────────────────────────────────────
// VIEW: EXERCISE LIBRARY
// ─────────────────────────────────────────────
async function renderExercises() {
  const vc = $id('view-container');
  vc.innerHTML = `
    <div class="view">
      <div class="search-bar-wrap">
        <div class="search-input-wrap">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
          <input type="text" class="search-input" placeholder="Search exercises..." id="ex-lib-search"
            oninput="handleExerciseSearch(this.value)">
        </div>
      </div>
      <div id="ex-filter-bar">
        <div class="loading-center" style="padding:16px"><div class="spinner spinner-sm"></div></div>
      </div>
      <div id="ex-list">
        <div class="loading-center"><div class="spinner"></div><span>Loading exercises...</span></div>
      </div>
    </div>`;

  try {
    const [exRes, patternsRes, musclesRes] = await Promise.all([
      S.exercises ? Promise.resolve({ exercises: S.exercises }) : API.getExercises(),
      S.movementPatterns ? Promise.resolve({ patterns: S.movementPatterns }) : API.getMovementPatterns(),
      S.muscleGroups ? Promise.resolve({ groups: S.muscleGroups }) : API.getMuscleGroups(),
    ]);

    S.exercises = exRes.exercises || exRes || [];
    S.movementPatterns = patternsRes.patterns || patternsRes || [];
    S.muscleGroups = musclesRes.groups || musclesRes || [];

    const equipmentOptions = [...new Set(S.exercises.map(e => e.equipment).filter(Boolean))].sort();

    const filterBar = $id('ex-filter-bar');
    filterBar.innerHTML = `
      <div class="filter-tabs">
        <div class="filter-tab ${S.exerciseFilter.pattern==='all'?'active':''}" onclick="setExFilter('pattern','all',this)">All</div>
        ${S.movementPatterns.map(p => `
          <div class="filter-tab ${S.exerciseFilter.pattern===p?'active':''}" onclick="setExFilter('pattern','${p}',this)">
            ${formatPattern(p)}
          </div>`).join('')}
      </div>
      <div style="padding:0 16px 8px;display:flex;gap:8px">
        <select id="ex-equip-filter" style="flex:1" onchange="setExFilter('equipment',this.value)">
          <option value="all">All Equipment</option>
          ${equipmentOptions.map(e => `<option value="${e}" ${S.exerciseFilter.equipment===e?'selected':''}>${capitalize(e)}</option>`).join('')}
        </select>
        <select id="ex-muscle-filter" style="flex:1" onchange="setExFilter('muscle',this.value)">
          <option value="all">All Muscles</option>
          ${S.muscleGroups.map(m => `<option value="${m}" ${S.exerciseFilter.muscle===m?'selected':''}>${formatPattern(m)}</option>`).join('')}
        </select>
      </div>`;

    renderExerciseList();
  } catch(e) {
    console.error(e);
    $id('ex-filter-bar').innerHTML = '';
    $id('ex-list').innerHTML = `<div class="empty-state"><h3>Error loading exercises</h3><button class="btn-primary" onclick="navigate('exercises')">Retry</button></div>`;
  }
}

function setExFilter(key, val, el) {
  S.exerciseFilter[key] = val;
  if (key === 'pattern' && el) {
    document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
    el.classList.add('active');
  }
  renderExerciseList();
}

function handleExerciseSearch(q) {
  S.exerciseFilter.query = q;
  clearTimeout(window._exLibSearchTimeout);
  window._exLibSearchTimeout = setTimeout(renderExerciseList, 200);
}

function renderExerciseList() {
  const list = $id('ex-list');
  if (!list) return;
  let exercises = S.exercises || [];

  const { pattern, equipment, muscle, query } = S.exerciseFilter;

  if (query) exercises = exercises.filter(e => e.name.toLowerCase().includes(query.toLowerCase()));
  if (pattern !== 'all') exercises = exercises.filter(e => e.movement_pattern === pattern);
  if (equipment !== 'all') exercises = exercises.filter(e => e.equipment === equipment);
  if (muscle !== 'all') exercises = exercises.filter(e =>
    (e.primary_muscles||'').includes(muscle) || (e.secondary_muscles||'').includes(muscle)
  );

  if (!exercises.length) {
    list.innerHTML = `<div class="empty-state"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg><h3>No exercises found</h3><p>Try different filters</p></div>`;
    return;
  }

  list.innerHTML = `<div class="exercise-grid">${exercises.map(ex => {
    const muscles = (ex.primary_muscles||'').split(',').filter(Boolean);
    const muscleTags = muscles.slice(0,3).map(m => `<span class="muscle-tag">${m.trim()}</span>`).join('');
    const equipBadge = ex.equipment ? `<span class="badge badge-gray">${capitalize(ex.equipment)}</span>` : '';
    const catBadge = `<span class="badge ${ex.category==='compound'?'badge-amber':'badge-gray'}">${ex.category||'—'}</span>`;
    return `
      <div class="exercise-card" onclick="viewExerciseDetail(${ex.id})">
        <div class="exercise-card-info">
          <div class="exercise-card-name">${ex.name}</div>
          <div style="display:flex;gap:4px;align-items:center;margin-top:3px;flex-wrap:wrap">
            ${catBadge} ${equipBadge}
            <span style="font-size:10px;color:var(--gray-dim)">${formatPattern(ex.movement_pattern)}</span>
          </div>
          <div class="exercise-card-tags">${muscleTags}</div>
        </div>
        <div class="exercise-card-right">
          <div style="text-align:right">
            <div style="font-size:9px;color:var(--gray-dim);margin-bottom:2px">FATIGUE</div>
            ${dotsHtml(ex.fatigue_rating||3)}
          </div>
          <div style="text-align:right">
            <div style="font-size:9px;color:var(--gray-dim);margin-bottom:2px">COMPLEX</div>
            ${dotsHtml(ex.complexity||2)}
          </div>
        </div>
      </div>`;
  }).join('')}</div>`;
}

async function viewExerciseDetail(exId) {
  const ex = (S.exercises||[]).find(e => e.id === exId);
  if (!ex) return;

  const vc = $id('view-container');
  vc.innerHTML = `
    <div class="view">
      <div class="exercise-detail-header">
        <div class="detail-back-btn" onclick="renderExercises()">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
          Back to Exercises
        </div>
        <div class="detail-name">${ex.name}</div>
        <div class="detail-tags">
          <span class="badge badge-amber">${ex.category||'—'}</span>
          <span class="badge badge-gray">${formatPattern(ex.movement_pattern)}</span>
          <span class="badge badge-gray">${capitalize(ex.equipment||'')}</span>
        </div>
      </div>
      <div class="section" style="margin-top:12px">
        <div class="section-title" style="margin-bottom:8px">MUSCLES</div>
        <div class="card">
          <div style="margin-bottom:8px"><span style="font-size:11px;color:var(--gray-dim);text-transform:uppercase;letter-spacing:0.06em;font-weight:700">Primary</span><br>
            <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:5px">${(ex.primary_muscles||'').split(',').map(m=>`<span class="muscle-tag" style="font-size:11px;padding:3px 8px">${m.trim()}</span>`).join('')}</div>
          </div>
          ${ex.secondary_muscles ? `<div style="margin-top:8px"><span style="font-size:11px;color:var(--gray-dim);text-transform:uppercase;letter-spacing:0.06em;font-weight:700">Secondary</span><br>
            <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:5px">${ex.secondary_muscles.split(',').map(m=>`<span class="muscle-tag" style="font-size:11px;padding:3px 8px;opacity:0.7">${m.trim()}</span>`).join('')}</div>
          </div>` : ''}
        </div>
      </div>
      <div class="section">
        <div class="section-title" style="margin-bottom:8px">RATINGS</div>
        <div class="card">
          <div class="flex-between" style="margin-bottom:10px">
            <span style="font-size:12px;color:var(--gray-mid)">Fatigue Rating</span>
            ${dotsHtml(ex.fatigue_rating||3)}
          </div>
          <div class="flex-between">
            <span style="font-size:12px;color:var(--gray-mid)">Complexity</span>
            ${dotsHtml(ex.complexity||2)}
          </div>
        </div>
      </div>
      <div class="section">
        <div class="section-title" style="margin-bottom:8px">VOLUME LANDMARKS</div>
        <div class="card" id="vlm-detail">
          <div class="loading-center" style="padding:16px"><div class="spinner spinner-sm"></div></div>
        </div>
      </div>
      <div class="section">
        <div class="section-title" style="margin-bottom:8px">e1RM — LAST 90 DAYS</div>
        <div class="chart-card" style="margin:0 0 8px">
          <div class="chart-wrap" style="height:180px">
            <canvas id="e1rm-chart-${exId}"></canvas>
          </div>
        </div>
      </div>
      <div class="section" id="overload-rec-section">
        <div class="section-title" style="margin-bottom:8px">PROGRESSIVE OVERLOAD</div>
        <div class="card" id="overload-detail">
          <div class="loading-center" style="padding:16px"><div class="spinner spinner-sm"></div></div>
        </div>
      </div>
      ${S.activeWorkout.running ? `
        <div style="padding:0 16px 16px">
          <button class="btn-secondary btn-full" onclick='addExerciseToWorkout(${JSON.stringify(ex)})'>
            + Add to Current Workout
          </button>
        </div>` : ''}
    </div>`;

  // Load e1RM trend
  try {
    const e1rmData = await API.getE1rm(exId, 90);
    const history = e1rmData.history || [];
    const vlm = (await API.getVolumeLandmarks().catch(()=>({landmarks:[]}))).landmarks || [];
    const exLandmark = vlm.find(l => {
      const muscles = (ex.primary_muscles||'').split(',').map(m=>m.trim().toLowerCase());
      return muscles.some(m => l.muscle_group && l.muscle_group.toLowerCase().includes(m));
    });

    // Volume landmark display
    const vlmEl = $id('vlm-detail');
    if (vlmEl) {
      const mev = ex.mev_sets_per_week || 6;
      const mrv = ex.mrv_sets_per_week || 20;
      const mav = Math.round((mev + mrv) / 2);
      vlmEl.innerHTML = `
        <div class="volume-landmark-bar">
          <div class="vlb-label">
            <span>MEV: ${mev} sets/wk</span>
            <span>MRV: ${mrv} sets/wk</span>
          </div>
          <div class="vlb-track" style="height:12px;border-radius:6px">
            <div style="position:absolute;left:0;top:0;bottom:0;width:${(mev/mrv*100).toFixed(0)}%;background:rgba(245,166,35,0.2);border-radius:6px"></div>
            <div style="position:absolute;left:${(mev/mrv*100).toFixed(0)}%;top:0;bottom:0;width:${((mav-mev)/mrv*100).toFixed(0)}%;background:rgba(245,166,35,0.5);border-radius:0 6px 6px 0"></div>
          </div>
          <div class="flex-between" style="margin-top:6px;font-size:10px;color:var(--gray-dim)">
            <span>Minimum Effective</span><span style="color:var(--amber)">Maximum Adaptive</span><span style="color:var(--red)">Maximum Recoverable</span>
          </div>
        </div>`;
    }

    // e1RM Chart
    if (history.length > 1) {
      const ctx = document.getElementById(`e1rm-chart-${exId}`);
      if (ctx) {
        destroyChart(`e1rm-${exId}`);
        S.charts[`e1rm-${exId}`] = new Chart(ctx, {
          type: 'line',
          data: {
            labels: history.map(h => fmtDate(h.date)),
            datasets: [{
              label: 'e1RM (lbs)',
              data: history.map(h => h.estimated_1rm),
              borderColor: '#F5A623',
              backgroundColor: 'rgba(245,166,35,0.08)',
              borderWidth: 2,
              pointBackgroundColor: '#F5A623',
              pointRadius: 4,
              tension: 0.3,
              fill: true,
            }]
          },
          options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
              x: { grid: { color: '#1a1a1a' }, ticks: { color: '#555', font: { family: 'JetBrains Mono', size: 10 } } },
              y: { grid: { color: '#1a1a1a' }, ticks: { color: '#555', font: { family: 'JetBrains Mono', size: 10 } } }
            }
          }
        });
      }
    } else {
      const ctx = document.getElementById(`e1rm-chart-${exId}`)?.parentElement;
      if (ctx) ctx.innerHTML = `<div class="empty-state" style="padding:24px"><h3>No data yet</h3><p>Log some sets to see your progress</p></div>`;
    }

    // Current e1RM display
    if (e1rmData.current_e1rm) {
      const section = $id('overload-rec-section');
      if (section) {
        section.insertAdjacentHTML('beforebegin', `
          <div class="section" style="margin-top:0">
            <div class="card flex-between">
              <span style="font-size:12px;color:var(--gray-mid)">Current e1RM</span>
              <span class="mono text-amber" style="font-size:18px;font-weight:700">${e1rmData.current_e1rm?.toFixed(0)} lbs</span>
            </div>
          </div>`);
      }
    }

  } catch(e) { console.error(e); }

  // Overload recommendation
  try {
    const rec = await API.getOverloadRec(exId);
    const overloadEl = $id('overload-detail');
    if (overloadEl) {
      overloadEl.innerHTML = rec.recommendation
        ? `<div style="display:flex;gap:10px;align-items:flex-start">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="#F5A623" flex-shrink:0><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
            <div>
              <div style="font-weight:700;font-size:14px;color:var(--white)">${rec.recommendation}</div>
              ${rec.details ? `<div style="font-size:12px;color:var(--gray-mid);margin-top:4px">${rec.details}</div>` : ''}
            </div>
           </div>`
        : `<div class="text-dim text-sm">No recommendation available yet. Log more data.</div>`;
    }
  } catch(e) {
    const overloadEl = $id('overload-detail');
    if (overloadEl) overloadEl.innerHTML = `<div class="text-dim text-sm">Log workouts to get overload recommendations.</div>`;
  }
}

// ─────────────────────────────────────────────
// VIEW: PROGRAMS
// ─────────────────────────────────────────────
async function renderPrograms() {
  const vc = $id('view-container');
  vc.innerHTML = `
    <div class="view">
      <div class="view-header">
        <div class="view-title">Programs</div>
        <div class="view-sub">Periodized training blocks</div>
      </div>
      <div style="padding:0 16px 16px">
        <button class="btn-primary btn-full" onclick="showProgramGenerator()">+ Generate New Program</button>
      </div>
      <div id="programs-list">
        <div class="loading-center"><div class="spinner"></div><span>Loading programs...</span></div>
      </div>
    </div>`;

  try {
    const res = await API.getPrograms();
    const programs = res.programs || [];
    S.programs = programs;

    const list = $id('programs-list');
    if (!programs.length) {
      list.innerHTML = `<div class="empty-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
        <h3>No programs yet</h3>
        <p>Generate an AI-powered periodized program tailored to your goals</p>
      </div>`;
      return;
    }

    list.innerHTML = programs.map(p => `
      <div class="program-card ${p.status==='active'?'active-prog':''}" onclick="selectProgram(${p.id})">
        <div class="program-card-top">
          <div>
            <div class="program-card-name">${p.name}</div>
            <div class="program-card-meta">${formatGoal(p.goal)} · ${formatPhase(p.phase)} · ${p.mesocycle_weeks} wks</div>
          </div>
          <span class="prog-status ${p.status}">${capitalize(p.status)}</span>
        </div>
        ${p.status === 'active' ? `
          <div class="prog-progress-bar" style="margin-top:10px">
            <div class="prog-progress-fill" style="width:${Math.round((p.current_week/p.mesocycle_weeks)*100)}%"></div>
          </div>
          <div style="font-size:10px;color:var(--gray-dim);margin-top:4px;font-family:var(--font-mono)">Week ${p.current_week} of ${p.mesocycle_weeks}</div>
        ` : ''}
      </div>`).join('');
  } catch(e) {
    $id('programs-list').innerHTML = `<div class="empty-state"><h3>Error loading programs</h3><button class="btn-primary" onclick="navigate('programs')">Retry</button></div>`;
  }
}

async function selectProgram(programId) {
  S.selectedProgramId = programId;
  const vc = $id('view-container');
  vc.innerHTML = `<div class="view"><div class="loading-center"><div class="spinner"></div><span>Loading program...</span></div></div>`;

  try {
    const data = await API.getProgram(programId);
    const prog = data.program || data;
    const sessions = data.sessions || [];

    const sessionsHtml = sessions.map(sess => {
      const exercises = sess.exercises || [];
      const exHtml = exercises.map(pe => {
        const ssHtml = pe.superset_group ? `<span class="superset-label" style="margin-right:6px">${pe.superset_group}</span>` : '';
        return `
          <div class="program-exercise-row">
            <div style="flex:1;min-width:0">
              <div class="pe-row-name">${ssHtml}${pe.exercise_name || pe.name || '—'}</div>
              <div class="pe-row-prescription">${pe.sets_prescribed} × ${pe.reps_prescribed} reps</div>
            </div>
            <div style="text-align:right">
              <div class="pe-row-intensity">${pe.intensity_type?.toUpperCase()}: ${pe.intensity_value}</div>
              <div style="font-size:10px;color:var(--gray-dim)">${pe.rest_seconds ? Math.round(pe.rest_seconds/60)+'min rest' : ''}</div>
            </div>
          </div>`;
      }).join('');

      return `
        <div class="session-day-card">
          <div class="session-day-header" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='none'?'block':'none'">
            <div>
              <div class="session-day-name">${sess.name}</div>
              <div class="session-day-meta">Day ${sess.day_number} · ${exercises.length} exercises</div>
            </div>
            <div style="display:flex;align-items:center;gap:8px">
              <button class="btn-secondary" style="padding:6px 12px;font-size:11px;min-height:36px" onclick="event.stopPropagation();startProgramSession(${programId},${sess.id})">
                Start →
              </button>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 9l6 6 6-6"/></svg>
            </div>
          </div>
          <div style="display:none">${exHtml || '<div style="padding:12px 14px;font-size:12px;color:var(--gray-dim)">No exercises prescribed</div>'}</div>
        </div>`;
    }).join('');

    vc.innerHTML = `
      <div class="view">
        <div style="padding:16px;border-bottom:1px solid var(--border-dim)">
          <div class="detail-back-btn" style="display:flex;align-items:center;gap:6px;color:var(--amber);font-size:13px;font-weight:600;margin-bottom:12px;cursor:pointer" onclick="navigate('programs')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
            All Programs
          </div>
          <div class="flex-between">
            <div>
              <div style="font-size:22px;font-weight:900;letter-spacing:-0.02em">${prog.name || data.name}</div>
              <div style="font-size:12px;color:var(--gray-mid);margin-top:3px;font-family:var(--font-mono)">${formatGoal(prog.goal||data.goal)} · ${formatPhase(prog.phase||data.phase)} · ${prog.mesocycle_weeks||data.mesocycle_weeks} weeks</div>
            </div>
            <span class="prog-status ${prog.status||data.status}">${capitalize(prog.status||data.status||'active')}</span>
          </div>
        </div>
        <div style="padding:14px 16px;display:flex;gap:8px">
          <span class="badge badge-amber">${formatPhase(prog.phase||data.phase)}</span>
          <span class="badge badge-gray">${formatGoal(prog.goal||data.goal)}</span>
          <span class="badge badge-gray">${sessions.length} sessions/week</span>
        </div>
        ${sessionsHtml || '<div class="empty-state"><h3>No sessions</h3></div>'}
      </div>`;
  } catch(e) {
    vc.innerHTML = `<div class="view"><div class="empty-state"><h3>Error loading program</h3><button class="btn-primary" onclick="navigate('programs')">Back</button></div></div>`;
  }
}

function showProgramGenerator() {
  S.programGen = { step: 1, goal: null, phase: null, split: null, weeks: 4, days: 4, name: '' };
  renderProgramGeneratorStep();
}

function renderProgramGeneratorStep() {
  const vc = $id('view-container');
  const pg = S.programGen;
  const stepTitles = ['Select Goal', 'Select Phase', 'Select Split', 'Configure', 'Name & Generate'];

  const stepIndicator = `
    <div class="step-indicator">
      ${stepTitles.map((_,i) => `<div class="step-dot ${pg.step===i+1?'active':pg.step>i+1?'done':''}"></div>`).join('')}
      <span style="font-size:11px;color:var(--gray-mid);margin-left:4px">${stepTitles[pg.step-1]}</span>
    </div>`;

  let content = '';

  if (pg.step === 1) {
    content = Object.entries(GOAL_INFO).map(([val, info]) => `
      <div class="goal-option ${pg.goal===val?'selected':''}" onclick="setPgField('goal','${val}');pgNext()">
        <div class="goal-option-name">${info.label}</div>
        <div class="goal-option-desc">${info.desc}</div>
      </div>`).join('');
  } else if (pg.step === 2) {
    content = Object.entries(PHASE_INFO).map(([val, info]) => `
      <div class="goal-option ${pg.phase===val?'selected':''}" onclick="setPgField('phase','${val}');pgNext()">
        <div class="goal-option-name">${info.label}</div>
        <div class="goal-option-desc">${info.desc}</div>
      </div>`).join('');
  } else if (pg.step === 3) {
    content = Object.entries(SPLIT_INFO).map(([val, info]) => `
      <div class="goal-option ${pg.split===val?'selected':''}" onclick="setPgField('split','${val}');pgNext()">
        <div class="goal-option-name">${info.label}</div>
        <div class="goal-option-desc">${info.desc}</div>
      </div>`).join('');
  } else if (pg.step === 4) {
    content = `
      <div class="form-group">
        <label>Mesocycle Length: <span class="text-amber mono" id="weeks-val">${pg.weeks} weeks</span></label>
        <input type="range" class="range-slider" min="3" max="6" value="${pg.weeks}" 
          oninput="setPgField('weeks',parseInt(this.value));document.getElementById('weeks-val').textContent=this.value+' weeks'">
        <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--gray-dim);margin-top:4px">
          <span>3 wks</span><span>4 wks</span><span>5 wks</span><span>6 wks</span>
        </div>
      </div>
      <div class="form-group">
        <label>Days Per Week</label>
        <div class="pill-selector">
          ${[2,3,4,5,6].map(d => `<button class="pill ${pg.days===d?'active':''}" onclick="setPgField('days',${d});this.closest('.pill-selector').querySelectorAll('.pill').forEach(p=>p.classList.remove('active'));this.classList.add('active')">${d} Days</button>`).join('')}
        </div>
      </div>
      <button class="btn-primary btn-full" onclick="pgNext()" style="margin-top:8px">Continue →</button>`;
  } else if (pg.step === 5) {
    const summary = `${formatGoal(pg.goal)} · ${formatPhase(pg.phase)} · ${SPLIT_INFO[pg.split]?.label} · ${pg.weeks}wks ${pg.days}days/wk`;
    content = `
      <div class="card" style="margin-bottom:16px;background:var(--amber-glow);border-color:rgba(245,166,35,0.3)">
        <div style="font-size:12px;color:var(--amber);margin-bottom:4px;font-family:var(--font-mono)">${summary}</div>
      </div>
      <div class="form-group">
        <label>Program Name</label>
        <input type="text" placeholder="e.g. Strength Block A" id="pg-name-input" value="${pg.name}"
          oninput="S.programGen.name=this.value">
      </div>
      <button class="btn-primary btn-full" id="pg-generate-btn" onclick="generateProgram()">
        Generate Program →
      </button>`;
  }

  vc.innerHTML = `
    <div class="view">
      <div style="padding:16px;border-bottom:1px solid var(--border-dim);display:flex;align-items:center;gap:10px">
        ${pg.step > 1 ? `<button class="btn-icon" onclick="pgBack()"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg></button>` : `<button class="btn-icon" onclick="navigate('programs')"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg></button>`}
        <div style="font-size:17px;font-weight:800">New Program</div>
      </div>
      <div class="generator-step">
        ${stepIndicator}
        <div class="step-title">${stepTitles[pg.step-1].toUpperCase()}</div>
        ${content}
      </div>
    </div>`;
}

function setPgField(key, val) { S.programGen[key] = val; }
function pgNext() { S.programGen.step = Math.min(5, S.programGen.step + 1); renderProgramGeneratorStep(); }
function pgBack() { S.programGen.step = Math.max(1, S.programGen.step - 1); renderProgramGeneratorStep(); }

async function generateProgram() {
  const pg = S.programGen;
  if (!pg.goal || !pg.phase || !pg.split) { showToast('Please complete all steps', 'error'); return; }
  const name = pg.name || `${formatGoal(pg.goal)} ${formatPhase(pg.phase)}`;

  const btn = $id('pg-generate-btn');
  if (btn) { btn.disabled = true; btn.innerHTML = '<div class="spinner spinner-sm"></div> GENERATING...'; }

  try {
    const res = await API.generateProgram({
      athlete_id: ATHLETE_ID,
      goal: pg.goal,
      phase: pg.phase,
      split: pg.split,
      weeks: pg.weeks,
      days_per_week: pg.days,
      name,
    });
    const programId = res.program_id || res.id;
    showToast(`"${name}" generated!`, 'success');
    navigate('programs');
    setTimeout(() => { if (programId) selectProgram(programId); }, 400);
  } catch(e) {
    console.error(e);
    showToast('Error generating program', 'error');
    if (btn) { btn.disabled = false; btn.innerHTML = 'Generate Program →'; }
  }
}

// ─────────────────────────────────────────────
// VIEW: ANALYTICS
// ─────────────────────────────────────────────
async function renderAnalytics() {
  const vc = $id('view-container');
  vc.innerHTML = `
    <div class="view">
      <div class="view-header">
        <div class="view-title">Analytics</div>
        <div class="view-sub">Performance intelligence</div>
      </div>
      <div class="time-range-selector">
        ${[7,30,90,'All'].map(d => `<button class="time-btn ${S.analyticsRange===d?'active':''}" onclick="setAnalyticsRange(${typeof d==='number'?d:"'all'"}, this)">${d}${typeof d==='number'?'d':''}</button>`).join('')}
      </div>
      <div id="analytics-content">
        <div class="loading-center"><div class="spinner"></div><span>Loading analytics...</span></div>
      </div>
    </div>`;

  loadAnalyticsData();
}

function setAnalyticsRange(range, btn) {
  S.analyticsRange = range;
  document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  loadAnalyticsData();
}

async function loadAnalyticsData() {
  const container = $id('analytics-content');
  if (!container) return;
  container.innerHTML = `<div class="loading-center"><div class="spinner"></div><span>Crunching numbers...</span></div>`;

  const days = S.analyticsRange === 'all' ? 365 : S.analyticsRange;

  try {
    const [volumeData, freqData, muscleData, workoutsData, e1rmData] = await Promise.all([
      API.getAnalytics(days, 'volume').catch(() => null),
      API.getAnalytics(days, 'frequency').catch(() => null),
      API.getAnalytics(days, 'muscle_volume').catch(() => null),
      API.getWorkouts(50).catch(() => ({ workouts: [] })),
      API.getAllE1rms().catch(() => ({ exercises: [] })),
    ]);

    const workouts = workoutsData.workouts || [];
    const e1rms = e1rmData.exercises || [];
    const volumePoints = volumeData?.data || [];
    const musclePoints = muscleData?.data || [];
    const freqPoints = freqData?.data || [];

    // Build heat calendar from workout dates
    const workoutDates = new Set(workouts.map(w => w.date?.split('T')[0] || w.date));
    const today = new Date();
    const calDays = [];
    for (let i = 83; i >= 0; i--) {
      const d = new Date(today);
      d.setDate(d.getDate() - i);
      const key = d.toISOString().split('T')[0];
      calDays.push({ date: key, worked: workoutDates.has(key) });
    }

    const heatHtml = calDays.map(d => `<div class="heat-day ${d.worked?'worked':''}" title="${d.date}"></div>`).join('');

    // e1RM top exercises
    const topE1rms = e1rms.slice(0, 6);

    container.innerHTML = `
      <!-- Volume Chart -->
      <div class="chart-card">
        <div class="chart-card-title">Volume Load Per Workout</div>
        <div class="chart-wrap" style="height:180px">
          <canvas id="volume-chart"></canvas>
        </div>
      </div>

      <!-- Frequency Heat Calendar -->
      <div class="chart-card">
        <div class="chart-card-title">Training Calendar (12 Weeks)</div>
        <div class="heat-calendar" id="heat-cal">${heatHtml}</div>
        <div style="display:flex;gap:8px;margin-top:10px;align-items:center;font-size:11px;color:var(--gray-dim)">
          <div class="heat-day" style="width:12px;height:12px;border-radius:2px;flex-shrink:0"></div><span>Rest</span>
          <div class="heat-day worked" style="width:12px;height:12px;border-radius:2px;flex-shrink:0"></div><span>Trained</span>
        </div>
      </div>

      <!-- Muscle Volume -->
      <div class="chart-card">
        <div class="chart-card-title">Muscle Group Volume</div>
        <div class="chart-wrap" style="height:220px">
          <canvas id="muscle-chart"></canvas>
        </div>
      </div>

      <!-- e1RM Trends -->
      <div class="chart-card">
        <div class="chart-card-title">Estimated 1RM — Current</div>
        ${topE1rms.length ? topE1rms.map(e => `
          <div class="flex-between" style="padding:8px 0;border-bottom:1px solid var(--border-dim)">
            <div>
              <div style="font-weight:600;font-size:13px">${e.exercise_name}</div>
              <div style="font-size:10px;color:var(--gray-dim);font-family:var(--font-mono)">${fmtDate(e.date)}</div>
            </div>
            <div class="mono text-amber" style="font-size:18px;font-weight:700">${e.estimated_1rm?.toFixed(0)} lbs</div>
          </div>`).join('') :
          `<div class="text-dim text-sm" style="padding:12px 0">Log workouts to track e1RM</div>`
        }
      </div>

      <!-- Movement Pattern Frequency -->
      <div class="chart-card">
        <div class="chart-card-title">Movement Pattern Frequency</div>
        <div class="chart-wrap" style="height:200px">
          <canvas id="freq-chart"></canvas>
        </div>
      </div>

      <!-- Volume Landmarks -->
      <div class="chart-card">
        <div class="chart-card-title">Volume Landmarks Editor
          <button class="btn-ghost" style="float:right;padding:4px 10px;font-size:10px;min-height:30px" onclick="saveVolumeLandmarks()">Save</button>
        </div>
        <div id="vlm-editor">
          <div class="loading-center" style="padding:16px"><div class="spinner spinner-sm"></div></div>
        </div>
      </div>`;

    // Render charts
    renderVolumeChart(volumePoints, workouts);
    renderMuscleChart(musclePoints);
    renderFreqChart(freqPoints);
    loadVolumeEditor(muscleData);

  } catch(e) {
    console.error(e);
    container.innerHTML = `<div class="empty-state"><h3>Analytics unavailable</h3><p>Log some workouts first</p></div>`;
  }
}

function renderVolumeChart(volumePoints, workouts) {
  const ctx = document.getElementById('volume-chart');
  if (!ctx) return;
  destroyChart('volume');

  const labels = volumePoints.length ? volumePoints.map(p => fmtDate(p.date)) : workouts.slice(0,20).reverse().map(w => fmtDate(w.date));
  const values = volumePoints.length ? volumePoints.map(p => p.volume || p.value || 0) : workouts.slice(0,20).reverse().map(w => w.total_volume || 0);

  if (!labels.length) { ctx.parentElement.innerHTML = `<div class="text-dim text-sm" style="padding:16px">No data yet</div>`; return; }

  S.charts.volume = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{ label: 'Volume (lbs)', data: values, backgroundColor: 'rgba(245,166,35,0.6)', borderColor: '#F5A623', borderWidth: 1, borderRadius: 3 }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#555', font: { family: 'JetBrains Mono', size: 9 }, maxRotation: 45 } },
        y: { grid: { color: '#1a1a1a' }, ticks: { color: '#555', font: { family: 'JetBrains Mono', size: 10 } } }
      }
    }
  });
}

function renderMuscleChart(musclePoints) {
  const ctx = document.getElementById('muscle-chart');
  if (!ctx) return;
  destroyChart('muscle');
  if (!musclePoints.length) { ctx.parentElement.innerHTML = `<div class="text-dim text-sm" style="padding:16px">No data yet</div>`; return; }
  const top = musclePoints.slice(0, 10);
  S.charts.muscle = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: top.map(p => formatPattern(p.muscle_group || p.label || p.name || '')),
      datasets: [{ data: top.map(p => p.volume || p.sets || p.value || 0), backgroundColor: top.map((_,i) => `hsla(${35+i*15},85%,55%,0.7)`), borderRadius: 3 }]
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: '#1a1a1a' }, ticks: { color: '#555', font: { family: 'JetBrains Mono', size: 10 } } },
        y: { grid: { display: false }, ticks: { color: '#8A8A8A', font: { size: 11 } } }
      }
    }
  });
}

function renderFreqChart(freqPoints) {
  const ctx = document.getElementById('freq-chart');
  if (!ctx) return;
  destroyChart('freq');
  if (!freqPoints.length) { ctx.parentElement.innerHTML = `<div class="text-dim text-sm" style="padding:16px">No data yet</div>`; return; }
  const top = freqPoints.slice(0, 8);
  S.charts.freq = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: top.map(p => formatPattern(p.movement_pattern || p.label || '')),
      datasets: [{ data: top.map(p => p.count || p.frequency || p.value || 0), backgroundColor: 'rgba(245,166,35,0.5)', borderColor: '#F5A623', borderWidth: 1, borderRadius: 3 }]
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: '#1a1a1a' }, ticks: { color: '#555', font: { family: 'JetBrains Mono', size: 10 } } },
        y: { grid: { display: false }, ticks: { color: '#8A8A8A', font: { size: 11 } } }
      }
    }
  });
}

async function loadVolumeEditor(muscleData) {
  const editor = $id('vlm-editor');
  if (!editor) return;
  try {
    const res = await API.getVolumeLandmarks();
    const landmarks = res.landmarks || [];
    if (!landmarks.length) { editor.innerHTML = `<div class="text-dim text-sm">No volume landmarks configured. Go to Profile to set them up.</div>`; return; }
    editor.innerHTML = `<div>${landmarks.map(l => `
      <div class="vlm-editor-row">
        <div class="vlm-muscle-name">
          ${formatPattern(l.muscle_group)}
          <span class="vlm-current-sets">Current: ${l.current_sets || '?'} sets/wk</span>
        </div>
        <div class="vlm-inputs">
          <div class="vlm-input-group"><label>MEV</label><input type="number" class="vlm-input" inputmode="decimal" value="${l.mev}" data-muscle="${l.muscle_group}" data-field="mev"></div>
          <div class="vlm-input-group"><label>MAV Low</label><input type="number" class="vlm-input" inputmode="decimal" value="${l.mav_low}" data-muscle="${l.muscle_group}" data-field="mav_low"></div>
          <div class="vlm-input-group"><label>MAV High</label><input type="number" class="vlm-input" inputmode="decimal" value="${l.mav_high}" data-muscle="${l.muscle_group}" data-field="mav_high"></div>
          <div class="vlm-input-group"><label>MRV</label><input type="number" class="vlm-input" inputmode="decimal" value="${l.mrv}" data-muscle="${l.muscle_group}" data-field="mrv"></div>
        </div>
      </div>`).join('')}</div>`;
  } catch(e) {
    editor.innerHTML = `<div class="text-dim text-sm">Could not load landmarks.</div>`;
  }
}

async function saveVolumeLandmarks() {
  const editor = $id('vlm-editor');
  if (!editor) return;
  const inputs = editor.querySelectorAll('input[data-muscle]');
  const data = {};
  inputs.forEach(input => {
    const muscle = input.dataset.muscle;
    const field = input.dataset.field;
    if (!data[muscle]) data[muscle] = { muscle_group: muscle };
    data[muscle][field] = parseInt(input.value) || 0;
  });
  try {
    await API.saveVolumeLandmarks({ athlete_id: ATHLETE_ID, landmarks: Object.values(data) });
    showToast('Volume landmarks saved', 'success');
  } catch(e) { showToast('Error saving landmarks', 'error'); }
}

// ─────────────────────────────────────────────
// VIEW: PROFILE
// ─────────────────────────────────────────────
async function renderProfile() {
  const vc = $id('view-container');
  vc.innerHTML = `
    <div class="view">
      <div class="view-header">
        <div class="view-title">Profile</div>
        <div class="view-sub">Athlete configuration</div>
      </div>
      <div id="profile-content">
        <div class="loading-center"><div class="spinner"></div></div>
      </div>
    </div>`;

  try {
    const athlete = S.athlete || await API.getAthlete();
    S.athlete = athlete;
    const [vlmRes] = await Promise.all([API.getVolumeLandmarks().catch(()=>({landmarks:[]}))]);
    const landmarks = vlmRes.landmarks || [];

    const content = $id('profile-content');
    content.innerHTML = `
      <div class="section">
        <div style="display:flex;align-items:center;gap:14px;margin-bottom:16px">
          <div class="profile-avatar">${(athlete.name||'A').charAt(0).toUpperCase()}</div>
          <div>
            <div style="font-size:18px;font-weight:800">${athlete.name||'Athlete'}</div>
            <div style="font-size:12px;color:var(--gray-dim);font-family:var(--font-mono)">${capitalize(athlete.experience_level||'intermediate')} · ${capitalize(athlete.primary_goal||'strength')}</div>
          </div>
        </div>

        <div class="form-group"><label>Full Name</label>
          <input type="text" id="pf-name" value="${athlete.name||''}" placeholder="Your name">
        </div>
        <div class="form-row">
          <div class="form-group"><label>Age</label>
            <input type="number" id="pf-age" inputmode="decimal" value="${athlete.age||''}" placeholder="25">
          </div>
          <div class="form-group"><label>Body Weight (lbs)</label>
            <input type="number" id="pf-weight" inputmode="decimal" value="${athlete.body_weight||''}" placeholder="185">
          </div>
        </div>
        <div class="form-row">
          <div class="form-group"><label>Body Fat %</label>
            <input type="number" id="pf-bf" inputmode="decimal" value="${athlete.body_fat_pct||''}" placeholder="15">
          </div>
          <div class="form-group"><label>Training Age (yrs)</label>
            <input type="number" id="pf-ta" inputmode="decimal" value="${athlete.training_age||''}" placeholder="3">
          </div>
        </div>
        <div class="form-group"><label>Experience Level</label>
          <div class="pill-selector" id="pf-exp">
            ${['beginner','intermediate','advanced','elite'].map(e => `<button class="pill ${athlete.experience_level===e?'active':''}" data-value="${e}" onclick="this.closest('.pill-selector').querySelectorAll('.pill').forEach(p=>p.classList.remove('active'));this.classList.add('active')">${capitalize(e)}</button>`).join('')}
          </div>
        </div>
        <div class="form-group"><label>Primary Goal</label>
          <div class="pill-selector" id="pf-goal">
            ${['strength','hypertrophy','power','endurance'].map(g => `<button class="pill ${athlete.primary_goal===g?'active':''}" data-value="${g}" onclick="this.closest('.pill-selector').querySelectorAll('.pill').forEach(p=>p.classList.remove('active'));this.classList.add('active')">${capitalize(g)}</button>`).join('')}
          </div>
        </div>
        <div class="form-row">
          <div class="form-group"><label>Training Days/Week</label>
            <input type="number" id="pf-days" inputmode="decimal" value="${athlete.training_days_per_week||4}" min="1" max="7">
          </div>
          <div class="form-group"><label>Session Duration (min)</label>
            <input type="number" id="pf-dur" inputmode="decimal" value="${athlete.session_duration_min||75}">
          </div>
        </div>
        <button class="btn-primary btn-full" id="pf-save-btn" onclick="saveProfile()">Save Profile</button>
      </div>

      <div class="section" style="padding-top:0">
        <div class="section-header">
          <div class="section-title">Volume Landmarks</div>
        </div>
        ${landmarks.length ? `
          <div class="card" id="vlm-profile-editor">
            ${landmarks.map(l => `
              <div class="vlm-editor-row">
                <div class="vlm-muscle-name">${formatPattern(l.muscle_group)}</div>
                <div class="vlm-inputs">
                  <div class="vlm-input-group"><label>MEV</label><input type="number" class="vlm-input" inputmode="decimal" value="${l.mev}" data-muscle="${l.muscle_group}" data-field="mev"></div>
                  <div class="vlm-input-group"><label>MAV-</label><input type="number" class="vlm-input" inputmode="decimal" value="${l.mav_low}" data-muscle="${l.muscle_group}" data-field="mav_low"></div>
                  <div class="vlm-input-group"><label>MAV+</label><input type="number" class="vlm-input" inputmode="decimal" value="${l.mav_high}" data-muscle="${l.muscle_group}" data-field="mav_high"></div>
                  <div class="vlm-input-group"><label>MRV</label><input type="number" class="vlm-input" inputmode="decimal" value="${l.mrv}" data-muscle="${l.muscle_group}" data-field="mrv"></div>
                </div>
              </div>`).join('')}
            <button class="btn-secondary btn-full" style="margin-top:12px" onclick="saveProfileLandmarks()">Save Landmarks</button>
          </div>` :
          `<div class="card text-dim text-sm">No landmarks configured yet.</div>`
        }
      </div>`;
  } catch(e) {
    $id('profile-content').innerHTML = `<div class="empty-state"><h3>Error loading profile</h3><button class="btn-primary" onclick="navigate('profile')">Retry</button></div>`;
  }
}

async function saveProfile() {
  const btn = $id('pf-save-btn');
  if (btn) { btn.disabled = true; btn.innerHTML = '<div class="spinner spinner-sm"></div> SAVING...'; }

  const data = {
    id: ATHLETE_ID,
    name: $id('pf-name')?.value.trim() || S.athlete?.name,
    age: parseInt($id('pf-age')?.value) || null,
    body_weight: parseFloat($id('pf-weight')?.value) || null,
    body_fat_pct: parseFloat($id('pf-bf')?.value) || null,
    training_age: parseInt($id('pf-ta')?.value) || null,
    experience_level: document.querySelector('#pf-exp .pill.active')?.dataset.value || 'intermediate',
    primary_goal: document.querySelector('#pf-goal .pill.active')?.dataset.value || 'strength',
    training_days_per_week: parseInt($id('pf-days')?.value) || 4,
    session_duration_min: parseInt($id('pf-dur')?.value) || 75,
  };

  try {
    const res = await API.saveAthlete(data);
    S.athlete = res.athlete || data;
    showToast('Profile saved!', 'success');
  } catch(e) { showToast('Error saving profile', 'error'); }
  finally {
    if (btn) { btn.disabled = false; btn.innerHTML = 'Save Profile'; }
  }
}

async function saveProfileLandmarks() {
  const editor = document.getElementById('vlm-profile-editor');
  if (!editor) return;
  const inputs = editor.querySelectorAll('input[data-muscle]');
  const data = {};
  inputs.forEach(input => {
    const muscle = input.dataset.muscle;
    const field = input.dataset.field;
    if (!data[muscle]) data[muscle] = { muscle_group: muscle };
    data[muscle][field] = parseInt(input.value) || 0;
  });
  try {
    await API.saveVolumeLandmarks({ athlete_id: ATHLETE_ID, landmarks: Object.values(data) });
    showToast('Volume landmarks saved!', 'success');
  } catch(e) { showToast('Error saving landmarks', 'error'); }
}

// ─────────────────────────────────────────────
// GLOBAL HELPERS FOR ONCLICK ATTRS
// ─────────────────────────────────────────────
window.navigate = navigate;
window.selectProgram = selectProgram;
window.showProgramGenerator = showProgramGenerator;
window.startProgramSession = startProgramSession;
window.startCustomWorkout = startCustomWorkout;
window.viewExerciseDetail = viewExerciseDetail;
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
window.pgNext = pgNext;
window.pgBack = pgBack;
window.setPgField = setPgField;
window.generateProgram = generateProgram;
window.setExFilter = setExFilter;
window.handleExerciseSearch = handleExerciseSearch;
window.setAnalyticsRange = setAnalyticsRange;
window.saveVolumeLandmarks = saveVolumeLandmarks;
window.saveProfile = saveProfile;
window.saveProfileLandmarks = saveProfileLandmarks;
window.onSetInput = onSetInput;
window.renderExercises = renderExercises;
window.S = S;

// ─────────────────────────────────────────────
// BOOT
// ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', initApp);
