// js/views/program-detail.js — Single program detail view

import { state } from '../state/store.js';
import { getProgram } from '../api/programs.js';
import { $id } from '../lib/dom.js';
import { capitalize, formatGoal, formatPhase } from '../lib/format.js';

// ── Main Render ──────────────────────────────────────

export async function selectProgram(programId) {
    state.selectedProgramId = programId;
    const vc = $id('view-container');
    vc.innerHTML = `<div class="view"><div class="loading-center"><div class="spinner"></div><span>Loading program...</span></div></div>`;

    try {
        const data = await getProgram(programId);
        const prog = data.program || data;
        const sessions = data.sessions || [];

        const sessionsHtml = sessions.map(sess => {
            const exercises = sess.exercises || [];
            const exHtml = exercises.map(pe => {
                const ssHtml = pe.superset_group ? `<span class="superset-label" style="margin-right:6px">${pe.superset_group}</span>` : '';
                return `
          <div class="program-exercise-row">
            <div style="flex:1;min-width:0">
              <div class="pe-row-name">${ssHtml}${pe.exercise_name || pe.name || '\u2014'}</div>
              <div class="pe-row-prescription">${pe.sets_prescribed} \u00d7 ${pe.reps_prescribed} reps</div>
            </div>
            <div style="text-align:right">
              <div class="pe-row-intensity">${pe.intensity_type?.toUpperCase()}: ${pe.intensity_value}</div>
              <div style="font-size:10px;color:var(--gray-dim)">${pe.rest_seconds ? Math.round(pe.rest_seconds / 60) + 'min rest' : ''}</div>
            </div>
          </div>`;
            }).join('');

            return `
        <div class="session-day-card">
          <div class="session-day-header" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='none'?'block':'none'">
            <div>
              <div class="session-day-name">${sess.name}</div>
              <div class="session-day-meta">Day ${sess.day_number} \u00b7 ${exercises.length} exercises</div>
            </div>
            <div style="display:flex;align-items:center;gap:8px">
              <button class="btn-secondary" style="padding:6px 12px;font-size:11px;min-height:36px" onclick="event.stopPropagation();startProgramSession(${programId},${sess.id})">
                Start \u2192
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
              <div style="font-size:12px;color:var(--gray-mid);margin-top:3px;font-family:var(--font-mono)">${formatGoal(prog.goal || data.goal)} \u00b7 ${formatPhase(prog.phase || data.phase)} \u00b7 ${prog.mesocycle_weeks || data.mesocycle_weeks} weeks</div>
            </div>
            <span class="prog-status ${prog.status || data.status}">${capitalize(prog.status || data.status || 'active')}</span>
          </div>
        </div>
        <div style="padding:14px 16px;display:flex;gap:8px">
          <span class="badge badge-amber">${formatPhase(prog.phase || data.phase)}</span>
          <span class="badge badge-gray">${formatGoal(prog.goal || data.goal)}</span>
          <span class="badge badge-gray">${sessions.length} sessions/week</span>
        </div>
        ${sessionsHtml || '<div class="empty-state"><h3>No sessions</h3></div>'}
      </div>`;
    } catch (e) {
        vc.innerHTML = `<div class="view"><div class="empty-state"><h3>Error loading program</h3><button class="btn-primary" onclick="navigate('programs')">Back</button></div></div>`;
    }
}

// ── Window globals for inline onclick ────────────────
window.selectProgram = selectProgram;
