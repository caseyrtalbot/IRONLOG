// js/views/program-wizard.js — Program generation wizard

import { state } from '../state/store.js';
import { generateProgram as apiGenerateProgram } from '../api/programs.js';
import { GOAL_INFO, PHASE_INFO, SPLIT_INFO } from '../lib/calc.js';
import { formatGoal, formatPhase } from '../lib/format.js';
import { $id } from '../lib/dom.js';
import { showToast } from '../components/toast.js';
import { ATHLETE_ID } from '../config.js';

// ── Entry Point ──────────────────────────────────────

export function showProgramGenerator() {
    state.programGen = { step: 1, goal: null, phase: null, split: null, weeks: 4, days: 4, name: '' };
    renderProgramGeneratorStep();
}

// ── Step Renderer ────────────────────────────────────

function renderProgramGeneratorStep() {
    const vc = $id('view-container');
    const pg = state.programGen;
    const stepTitles = ['Select Goal', 'Select Phase', 'Select Split', 'Configure', 'Name & Generate'];

    const stepIndicator = `
    <div class="step-indicator">
      ${stepTitles.map((_, i) => `<div class="step-dot ${pg.step === i + 1 ? 'active' : pg.step > i + 1 ? 'done' : ''}"></div>`).join('')}
      <span style="font-size:11px;color:var(--gray-mid);margin-left:4px">${stepTitles[pg.step - 1]}</span>
    </div>`;

    let content = '';

    if (pg.step === 1) {
        content = Object.entries(GOAL_INFO).map(([val, info]) => `
      <div class="goal-option ${pg.goal === val ? 'selected' : ''}" onclick="setPgField('goal','${val}');pgNext()">
        <div class="goal-option-name">${info.label}</div>
        <div class="goal-option-desc">${info.desc}</div>
      </div>`).join('');
    } else if (pg.step === 2) {
        content = Object.entries(PHASE_INFO).map(([val, info]) => `
      <div class="goal-option ${pg.phase === val ? 'selected' : ''}" onclick="setPgField('phase','${val}');pgNext()">
        <div class="goal-option-name">${info.label}</div>
        <div class="goal-option-desc">${info.desc}</div>
      </div>`).join('');
    } else if (pg.step === 3) {
        content = Object.entries(SPLIT_INFO).map(([val, info]) => `
      <div class="goal-option ${pg.split === val ? 'selected' : ''}" onclick="setPgField('split','${val}');pgNext()">
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
          ${[2, 3, 4, 5, 6].map(d => `<button class="pill ${pg.days === d ? 'active' : ''}" onclick="setPgField('days',${d});this.closest('.pill-selector').querySelectorAll('.pill').forEach(p=>p.classList.remove('active'));this.classList.add('active')">${d} Days</button>`).join('')}
        </div>
      </div>
      <button class="btn-primary btn-full" onclick="pgNext()" style="margin-top:8px">Continue \u2192</button>`;
    } else if (pg.step === 5) {
        const summary = `${formatGoal(pg.goal)} \u00b7 ${formatPhase(pg.phase)} \u00b7 ${SPLIT_INFO[pg.split]?.label} \u00b7 ${pg.weeks}wks ${pg.days}days/wk`;
        content = `
      <div class="card" style="margin-bottom:16px;background:var(--amber-glow);border-color:rgba(245,166,35,0.3)">
        <div style="font-size:12px;color:var(--amber);margin-bottom:4px;font-family:var(--font-mono)">${summary}</div>
      </div>
      <div class="form-group">
        <label>Program Name</label>
        <input type="text" placeholder="e.g. Strength Block A" id="pg-name-input" value="${pg.name}"
          oninput="state.programGen.name=this.value">
      </div>
      <button class="btn-primary btn-full" id="pg-generate-btn" onclick="generateProgram()">
        Generate Program \u2192
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
        <div class="step-title">${stepTitles[pg.step - 1].toUpperCase()}</div>
        ${content}
      </div>
    </div>`;
}

// ── Navigation Helpers ───────────────────────────────

function setPgField(key, val) { state.programGen[key] = val; }
function pgNext() { state.programGen.step = Math.min(5, state.programGen.step + 1); renderProgramGeneratorStep(); }
function pgBack() { state.programGen.step = Math.max(1, state.programGen.step - 1); renderProgramGeneratorStep(); }

// ── Generate ─────────────────────────────────────────

async function generateProgram() {
    const pg = state.programGen;
    if (!pg.goal || !pg.phase || !pg.split) { showToast('Please complete all steps', 'error'); return; }
    const name = pg.name || `${formatGoal(pg.goal)} ${formatPhase(pg.phase)}`;

    const btn = $id('pg-generate-btn');
    if (btn) { btn.disabled = true; btn.innerHTML = '<div class="spinner spinner-sm"></div> GENERATING...'; }

    try {
        const res = await apiGenerateProgram({
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
        window.navigate('programs');
        setTimeout(() => { if (programId) window.selectProgram(programId); }, 400);
    } catch (e) {
        console.error(e);
        showToast('Error generating program', 'error');
        if (btn) { btn.disabled = false; btn.innerHTML = 'Generate Program \u2192'; }
    }
}

// ── Window globals for inline onclick ────────────────
// state is needed for the inline oninput on step 5 name field
window.state = state;
window.showProgramGenerator = showProgramGenerator;
window.pgNext = pgNext;
window.pgBack = pgBack;
window.setPgField = setPgField;
window.generateProgram = generateProgram;
