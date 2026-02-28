// js/views/programs.js — Programs list view

import { state } from '../state/store.js';
import { getPrograms, deleteProgram } from '../api/programs.js';
import { $id, loadingSpinner, emptyState, errorState } from '../lib/dom.js';
import { capitalize, formatGoal, formatPhase } from '../lib/format.js';
import { showToast } from '../components/toast.js';

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
        ${loadingSpinner('Loading programs...')}
      </div>
    </div>`;

    try {
        const res = await getPrograms();
        const programs = res.programs || (Array.isArray(res) ? res : []);
        state.programs = programs;

        const list = $id('programs-list');
        if (!programs.length) {
            list.innerHTML = emptyState('No programs yet', 'Generate an AI-powered periodized program tailored to your goals', '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>');
            return;
        }

        list.innerHTML = programs.map(p => `
      <div class="program-card ${p.status === 'active' ? 'active-prog' : ''}" onclick="selectProgram(${p.id})">
        <div class="program-card-top">
          <div style="flex:1;min-width:0">
            <div class="program-card-name">${p.name}</div>
            <div class="program-card-meta">${formatGoal(p.goal)} \u00b7 ${formatPhase(p.phase)} \u00b7 ${p.mesocycle_weeks} wks</div>
          </div>
          <span class="prog-status ${p.status}">${capitalize(p.status)}</span>
          <button class="btn-icon" style="margin-left:4px;color:var(--gray-dim)" onclick="event.stopPropagation();confirmDeleteProgram(${p.id},'${p.name.replace(/'/g, "\\'")}')" title="Delete program">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/></svg>
          </button>
        </div>
        ${p.status === 'active' ? `
          <div class="prog-progress-bar" style="margin-top:10px">
            <div class="prog-progress-fill" style="width:${Math.round((p.current_week / p.mesocycle_weeks) * 100)}%"></div>
          </div>
          <div style="font-size:10px;color:var(--gray-dim);margin-top:4px;font-family:var(--font-mono)">Week ${p.current_week} of ${p.mesocycle_weeks}</div>
        ` : ''}
      </div>`).join('');
    } catch (e) {
        $id('programs-list').innerHTML = errorState('Error loading programs', 'programs');
    }
}

async function confirmDeleteProgram(id, name) {
    if (!confirm(`Delete "${name}"? This will remove all sessions, prescriptions, and associated data.`)) return;
    try {
        await deleteProgram(id);
        showToast(`"${name}" deleted`, 'success');
        renderPrograms();
    } catch (e) {
        showToast('Error deleting program', 'error');
    }
}

window.confirmDeleteProgram = confirmDeleteProgram;
