// js/views/exercises.js — Exercise library view

import { state } from '../state/store.js';
import { getExercises, getMovementPatterns, getMuscleGroups } from '../api/exercises.js';
import { $id, loadingSpinner, loadingSpinnerSm, emptyState, errorState } from '../lib/dom.js';
import { capitalize, formatPattern, dotsHtml } from '../lib/format.js';

// ── Main Render ──────────────────────────────────────

export async function renderExercises() {
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
        ${loadingSpinnerSm()}
      </div>
      <div id="ex-list">
        ${loadingSpinner('Loading exercises...')}
      </div>
    </div>`;

    try {
        const [exRes, patternsRes, musclesRes] = await Promise.all([
            state.exercises ? Promise.resolve({ exercises: state.exercises }) : getExercises(),
            state.movementPatterns ? Promise.resolve({ patterns: state.movementPatterns }) : getMovementPatterns(),
            state.muscleGroups ? Promise.resolve({ groups: state.muscleGroups }) : getMuscleGroups(),
        ]);

        state.exercises = exRes.exercises || exRes || [];
        const rawPatterns = patternsRes.patterns || patternsRes || [];
        state.movementPatterns = rawPatterns.map(p => typeof p === 'string' ? p : p.movement_pattern).filter(Boolean);
        state.muscleGroups = musclesRes.groups || musclesRes || [];

        const equipmentOptions = [...new Set(state.exercises.map(e => e.equipment).filter(Boolean))].sort();

        const filterBar = $id('ex-filter-bar');
        filterBar.innerHTML = `
      <div class="filter-tabs">
        <div class="filter-tab ${state.exerciseFilter.pattern === 'all' ? 'active' : ''}" onclick="setExFilter('pattern','all',this)">All</div>
        ${state.movementPatterns.map(p => `
          <div class="filter-tab ${state.exerciseFilter.pattern === p ? 'active' : ''}" onclick="setExFilter('pattern','${p}',this)">
            ${formatPattern(p)}
          </div>`).join('')}
      </div>
      <div style="padding:0 16px 8px;display:flex;gap:8px">
        <select id="ex-equip-filter" style="flex:1" onchange="setExFilter('equipment',this.value)">
          <option value="all">All Equipment</option>
          ${equipmentOptions.map(e => `<option value="${e}" ${state.exerciseFilter.equipment === e ? 'selected' : ''}>${capitalize(e)}</option>`).join('')}
        </select>
        <select id="ex-muscle-filter" style="flex:1" onchange="setExFilter('muscle',this.value)">
          <option value="all">All Muscles</option>
          ${state.muscleGroups.map(m => `<option value="${m}" ${state.exerciseFilter.muscle === m ? 'selected' : ''}>${formatPattern(m)}</option>`).join('')}
        </select>
      </div>`;

        renderExerciseList();
    } catch (e) {
        console.error(e);
        $id('ex-filter-bar').innerHTML = '';
        $id('ex-list').innerHTML = errorState('Error loading exercises', 'exercises');
    }
}

// ── Filter / Search ──────────────────────────────────

function setExFilter(key, val, el) {
    state.exerciseFilter[key] = val;
    if (key === 'pattern' && el) {
        document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
        el.classList.add('active');
    }
    renderExerciseList();
}

function handleExerciseSearch(q) {
    state.exerciseFilter.query = q;
    clearTimeout(window._exLibSearchTimeout);
    window._exLibSearchTimeout = setTimeout(renderExerciseList, 200);
}

// ── Exercise List Render ─────────────────────────────

function renderExerciseList() {
    const list = $id('ex-list');
    if (!list) return;
    let exercises = state.exercises || [];

    const { pattern, equipment, muscle, query } = state.exerciseFilter;

    if (query) exercises = exercises.filter(e => e.name.toLowerCase().includes(query.toLowerCase()));
    if (pattern !== 'all') exercises = exercises.filter(e => e.movement_pattern === pattern);
    if (equipment !== 'all') exercises = exercises.filter(e => e.equipment === equipment);
    if (muscle !== 'all') exercises = exercises.filter(e =>
        (e.primary_muscles || '').includes(muscle) || (e.secondary_muscles || '').includes(muscle)
    );

    if (!exercises.length) {
        list.innerHTML = emptyState('No exercises found', 'Try different filters', '<circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>');
        return;
    }

    list.innerHTML = `<div class="exercise-grid">${exercises.map(ex => {
        const muscles = (ex.primary_muscles || '').split(',').filter(Boolean);
        const muscleTags = muscles.slice(0, 3).map(m => `<span class="muscle-tag">${m.trim()}</span>`).join('');
        const equipBadge = ex.equipment ? `<span class="badge badge-gray">${capitalize(ex.equipment)}</span>` : '';
        const catBadge = `<span class="badge ${ex.category === 'compound' ? 'badge-amber' : 'badge-gray'}">${ex.category || '\u2014'}</span>`;
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
            ${dotsHtml(ex.fatigue_rating || 3)}
          </div>
          <div style="text-align:right">
            <div style="font-size:9px;color:var(--gray-dim);margin-bottom:2px">COMPLEX</div>
            ${dotsHtml(ex.complexity || 2)}
          </div>
        </div>
      </div>`;
    }).join('')}</div>`;
}

// ── Window globals for inline onclick ────────────────
window.setExFilter = setExFilter;
window.handleExerciseSearch = handleExerciseSearch;
window.renderExercises = renderExercises;
