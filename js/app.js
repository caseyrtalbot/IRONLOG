// js/app.js — Modular entry point for IRONLOG
// Imports all modules and boots the application

import { state } from './state/store.js';
import { registerRoute, initRouter } from './state/router.js';
import { ATHLETE_ID } from './config.js';

// API
import { getAthlete, saveAthlete } from './api/athlete.js';
import { getExercises, getMovementPatterns, getMuscleGroups } from './api/exercises.js';

// Lib
import { $id } from './lib/dom.js';

import { showToast } from './components/toast.js';

// Views
import { renderDashboard, updateStreakBadge } from './views/dashboard.js';
import { renderWorkout } from './views/workout.js';
import { renderExercises } from './views/exercises.js';
import { viewExerciseDetail } from './views/exercise-detail.js';
import { renderPrograms } from './views/programs.js';
import { selectProgram } from './views/program-detail.js';
import { showProgramGenerator } from './views/program-wizard.js';
import { renderAnalytics } from './views/analytics.js';
import { renderProfile } from './views/profile.js';

// ─────────────────────────────────────────────
// ROUTE REGISTRATION
// ─────────────────────────────────────────────
registerRoute('dashboard', renderDashboard);
registerRoute('workout', renderWorkout);
registerRoute('exercises', renderExercises);
registerRoute('programs', renderPrograms);
registerRoute('analytics', renderAnalytics);
registerRoute('profile', renderProfile);

// ─────────────────────────────────────────────
// APP INIT
// ─────────────────────────────────────────────
async function initApp() {
  try {
    const athleteRes = await getAthlete().catch(() => null);
    if (athleteRes && athleteRes.id) {
      state.athlete = athleteRes;
      updateStreakBadge();
    } else {
      showOnboarding();
      return;
    }

    // Prefetch exercises in background
    getExercises().then(res => { state.exercises = res.exercises || res || []; });
    getMovementPatterns().then(res => { state.movementPatterns = res.patterns || res || []; });
    getMuscleGroups().then(res => { state.muscleGroups = res.groups || res || []; });

    // Hide loader
    setTimeout(() => {
      $id('page-loader').classList.add('hidden');
    }, 800);

    // Initialize router (handles initial route + hashchange)
    initRouter();

  } catch(e) {
    console.error('Init error:', e);
    $id('page-loader').classList.add('hidden');
    showOnboarding();
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
        ps.querySelectorAll('.pill').forEach(x => x.classList.remove('active'));
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
      const res = await saveAthlete(data);
      state.athlete = res.athlete || data;
      modal.classList.add('hidden');
      showToast('Profile saved! Welcome to IRONLOG.', 'success');

      // Prefetch
      getExercises().then(r => { state.exercises = r.exercises || r || []; });
      getMovementPatterns().then(r => { state.movementPatterns = r.patterns || r || []; });
      getMuscleGroups().then(r => { state.muscleGroups = r.groups || r || []; });

      initRouter();
    } catch(e) {
      showToast('Error saving profile', 'error');
      btn.disabled = false; btn.innerHTML = 'START TRAINING \u2192';
    }
  });
}

// Boot
document.addEventListener('DOMContentLoaded', initApp);
