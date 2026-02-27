// js/views/programs.js — Programs list view

import { state } from '../state/store.js';
import { getPrograms } from '../api/programs.js';
import { $id } from '../lib/dom.js';
import { capitalize, formatGoal, formatPhase } from '../lib/format.js';

// ── Main Render ──────────────────────────────────────

export async function renderPrograms() {
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
        const res = await getPrograms();
        const programs = res.programs || (Array.isArray(res) ? res : []);
        state.programs = programs;

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
      <div class="program-card ${p.status === 'active' ? 'active-prog' : ''}" onclick="selectProgram(${p.id})">
        <div class="program-card-top">
          <div>
            <div class="program-card-name">${p.name}</div>
            <div class="program-card-meta">${formatGoal(p.goal)} \u00b7 ${formatPhase(p.phase)} \u00b7 ${p.mesocycle_weeks} wks</div>
          </div>
          <span class="prog-status ${p.status}">${capitalize(p.status)}</span>
        </div>
        ${p.status === 'active' ? `
          <div class="prog-progress-bar" style="margin-top:10px">
            <div class="prog-progress-fill" style="width:${Math.round((p.current_week / p.mesocycle_weeks) * 100)}%"></div>
          </div>
          <div style="font-size:10px;color:var(--gray-dim);margin-top:4px;font-family:var(--font-mono)">Week ${p.current_week} of ${p.mesocycle_weeks}</div>
        ` : ''}
      </div>`).join('');
    } catch (e) {
        $id('programs-list').innerHTML = `<div class="empty-state"><h3>Error loading programs</h3><button class="btn-primary" onclick="navigate('programs')">Retry</button></div>`;
    }
}
