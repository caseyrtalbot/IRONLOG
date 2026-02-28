// js/views/dashboard.js — Dashboard view

import { state } from '../state/store.js';
import { getDashboard } from '../api/dashboard.js';
import { $id, loadingSpinner, errorState } from '../lib/dom.js';
import { fmtDate, fmtDuration, formatGoal, formatPhase, getTimeOfDay } from '../lib/format.js';
import { showToast } from '../components/toast.js';

// ── Helpers ──────────────────────────────────────────

export function updateStreakBadge() {
    if (!state.dashboard) return;
    const streak = state.dashboard.streak || 0;
    const badge = $id('streak-badge');
    const count = $id('streak-count');
    if (streak > 0) {
        count.textContent = streak;
        badge.classList.remove('hidden');
    }
}

function viewWorkout(id) {
    showToast('Workout detail coming soon', 'info');
}

// ── Main Render ──────────────────────────────────────

export async function renderDashboard() {
    const vc = $id('view-container');
    vc.innerHTML = `<div class="view">${loadingSpinner('Loading dashboard...')}</div>`;

    try {
        const data = await getDashboard();
        state.dashboard = data;
        updateStreakBadge();

        const athlete = state.athlete || {};
        const firstName = (athlete.name || 'Athlete').split(' ')[0];
        const streak = data.streak || 0;
        const totalWorkouts = data.totals?.total_workouts || data.total_workouts || 0;
        const recentPRs = (data.recent_prs || []).map(pr => ({
            ...pr,
            exercise_name: pr.exercise_name || pr.name,
            estimated_1rm: pr.estimated_1rm ?? pr.best_e1rm,
        }));
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
              <div class="prog-card-sub">${formatGoal(activeProgram.goal)} \u00b7 ${formatPhase(activeProgram.phase)}</div>
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
            prsHtml = recentPRs.slice(0, 5).map(pr => `
        <div class="pr-item">
          <div class="pr-item-left">
            <div class="pr-item-name">${pr.exercise_name || '\u2014'}</div>
            <div class="pr-item-date">${fmtDate(pr.date)}</div>
          </div>
          <div class="pr-item-right">
            <div class="pr-item-val">${pr.estimated_1rm ? pr.estimated_1rm.toFixed(0) : '\u2014'}</div>
            <div class="pr-item-unit">lbs e1RM <span class="badge badge-pr ml-2">PR</span></div>
          </div>
        </div>`).join('');
        } else {
            prsHtml = `<div class="text-dim text-sm" style="padding:12px 0">No PRs yet \u2014 start training!</div>`;
        }

        let workoutsHtml = '';
        if (recentWorkouts.length) {
            workoutsHtml = recentWorkouts.slice(0, 7).map(w => {
                const rpeColor_ = w.session_rpe ? (w.session_rpe >= 9 ? 'rpe-red' : w.session_rpe >= 7.5 ? 'rpe-amber' : 'rpe-green') : '';
                const vol = w.total_volume ?? w.volume_load;
                return `
          <div class="workout-history-item" onclick="viewWorkout(${w.id})">
            <div class="wh-date">${fmtDate(w.date)}</div>
            <div class="wh-info">
              <div class="wh-title">${w.notes || (w.session_name || 'Workout')}</div>
              <div class="wh-meta">${fmtDuration(w.duration_min)} \u00b7 ${vol ? Math.round(vol).toLocaleString() + ' lbs' : '\u2014'}</div>
            </div>
            <div class="wh-rpe ${rpeColor_}">${w.session_rpe || '\u2014'}</div>
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
              <div class="hero-stat-val">${Math.round(data.weekly_volume / 1000).toFixed(0)}k</div>
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
            <div class="section-action" onclick="navigate('analytics')">View All \u2192</div>
          </div>
          <div class="card" style="padding:0 16px">${prsHtml}</div>
        </div>

        <div class="section">
          <div class="section-header">
            <div class="section-title">Recent Workouts</div>
            <div class="section-action" onclick="navigate('analytics')">History \u2192</div>
          </div>
          <div class="card" style="padding:0 16px">${workoutsHtml}</div>
        </div>
      </div>`;
    } catch (e) {
        console.error(e);
        vc.innerHTML = `<div class="view">${errorState('Could not load dashboard', 'dashboard')}</div>`;
    }
}

// ── Window globals for inline onclick ────────────────
window.viewWorkout = viewWorkout;
