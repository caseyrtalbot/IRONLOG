// js/views/program-detail.js — Single program detail view

import { state } from '../state/store.js';
import { getProgram, getProgramRetrospective } from '../api/programs.js';
import { $id, loadingSpinner } from '../lib/dom.js';
import { capitalize, formatGoal, formatPhase } from '../lib/format.js';

let detailWeek = 1;

// ── Week Tabs ────────────────────────────────────────

function renderWeekTabs(program, currentWeek) {
    const weeks = program.mesocycle_weeks || 4;
    return `
    <div style="padding:0 16px 14px;display:flex;gap:6px;overflow-x:auto">
      ${Array.from({length: weeks}, (_, i) => i + 1).map(w => `
        <button class="pill ${w === currentWeek ? 'active' : ''}"
          onclick="setDetailWeek(${w})"
          style="min-width:60px">
          Week ${w}${w === (program.current_week || 1) ? ' ●' : ''}
        </button>
      `).join('')}
    </div>`;
}

// ── Exercise Row with Weekly Prescription ────────────

function renderExerciseRow(pe, selectedWeek) {
    const weekData = (pe.weekly || []).find(w => w.week_number === selectedWeek);
    const sets = weekData?.sets_prescribed || pe.sets_prescribed;
    const reps = weekData?.reps_prescribed || pe.reps_prescribed;
    const weight = weekData?.target_weight;
    const rpe = weekData?.target_rpe || pe.intensity_value;
    const intensity = weekData?.intensity_pct;

    const weightDisplay = weight
        ? `<div class="mono text-amber" style="font-size:14px;font-weight:700">${weight} lbs</div>`
        : '';
    const intensityDisplay = intensity
        ? `<div style="font-size:10px;color:var(--gray-dim)">${intensity}% 1RM</div>`
        : '';

    return `
    <div class="program-exercise-row">
      <div style="flex:1;min-width:0">
        <div class="pe-row-name">${pe.superset_group ? `<span class="superset-label">${pe.superset_group}</span>` : ''}${pe.exercise_name || pe.name || '\u2014'}</div>
        <div class="pe-row-prescription">${sets} \u00d7 ${reps} @ RPE ${rpe}</div>
      </div>
      <div style="text-align:right">
        ${weightDisplay}
        ${intensityDisplay}
        <div style="font-size:10px;color:var(--gray-dim)">${pe.rest_seconds ? Math.round(pe.rest_seconds / 60) + 'min rest' : ''}</div>
      </div>
    </div>`;
}

// ── Next Phase Button ────────────────────────────────

function renderNextPhaseButton(program) {
    if (program.status !== 'completed' || !program.suggested_next_phase) return '';
    const phase = program.suggested_next_phase;
    const phaseLabel = phase.charAt(0).toUpperCase() + phase.slice(1);
    return `
    <div style="padding:16px;border-top:2px solid var(--amber)">
      <button class="btn-primary btn-full" onclick="startNextPhase('${program.goal}','${phase}','${program.name}')">
        Start Next Phase \u2192 ${phaseLabel}
      </button>
    </div>`;
}

// ── Global helpers for inline onclick ────────────────

function setDetailWeek(w) {
    detailWeek = w;
    // Re-render the current program view
    if (typeof window._currentProgramId !== 'undefined') {
        selectProgram(window._currentProgramId);
    }
}
window.setDetailWeek = setDetailWeek;

function startNextPhase(goal, phase, prevName) {
    // Navigate to wizard with pre-filled values
    window.location.hash = '#program-wizard';
}
window.startNextPhase = startNextPhase;

// ── Volume Summary Renderer ─────────────────────────

function renderVolumeSummary(volumeSummary) {
    if (!volumeSummary || !volumeSummary.projected) return '';

    const projected = volumeSummary.projected;
    const audit = volumeSummary.audit || [];

    // Build a lookup for quick issue checking per muscle
    const issueMap = {};
    for (const a of audit) {
        issueMap[a.muscle] = a;
    }

    // Build table rows for each projected muscle group
    const muscleRows = Object.keys(projected).sort().map(muscle => {
        const vol = projected[muscle];
        const issue = issueMap[muscle];

        let colorClass = 'vol-green';
        let statusLabel = 'OK';
        if (issue) {
            if (issue.severity === 'red') {
                colorClass = 'vol-red';
                statusLabel = issue.issue === 'below_mev' ? 'Below MEV' : 'Above MRV';
            } else {
                colorClass = 'vol-yellow';
                statusLabel = issue.issue === 'below_mav' ? 'Below MAV' : 'Above MAV';
            }
        }

        const muscleName = muscle.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');

        return `
        <tr class="${colorClass}">
          <td style="padding:6px 10px;font-size:12px;font-weight:600">${muscleName}</td>
          <td style="padding:6px 10px;font-size:12px;text-align:center;font-family:var(--font-mono)">${vol}</td>
          <td style="padding:6px 10px;font-size:11px;text-align:right">${statusLabel}</td>
        </tr>`;
    }).join('');

    // Build audit warnings
    const warningsHtml = audit.length > 0
        ? audit.map(a => {
            const icon = a.severity === 'red' ? '!!' : '!';
            const muscleName = a.muscle.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
            const direction = a.issue.startsWith('below') ? 'needs' : 'exceeds';
            const targetLabel = a.issue.replace('below_', '').replace('above_', '').toUpperCase();
            return `
            <div class="vol-warning vol-warning-${a.severity}" style="display:flex;align-items:center;gap:8px;padding:8px 12px;margin-bottom:4px;border-radius:var(--radius-sm);font-size:12px">
              <span style="font-weight:800;min-width:18px;text-align:center">${icon}</span>
              <span><strong>${muscleName}</strong> ${direction} ${targetLabel} target &mdash; projected ${a.projected} sets, target ${a.target} (${a.delta} sets ${a.issue.startsWith('below') ? 'short' : 'over'})</span>
            </div>`;
        }).join('')
        : '<div style="padding:8px 12px;font-size:12px;color:var(--green)">All muscle groups within optimal volume range.</div>';

    return `
    <div style="padding:0 16px 14px">
      <div style="background:var(--bg-card);border:1px solid var(--border-dim);border-radius:var(--radius-md);overflow:hidden">
        <div style="padding:12px 14px;border-bottom:1px solid var(--border-dim);display:flex;align-items:center;justify-content:space-between">
          <div style="font-size:13px;font-weight:700;letter-spacing:0.03em;text-transform:uppercase;color:var(--gray-bright)">Volume Budget</div>
          <span class="badge badge-gray" style="font-size:10px">sets/week</span>
        </div>
        <table style="width:100%;border-collapse:collapse">
          <thead>
            <tr style="border-bottom:1px solid var(--border-dim)">
              <th style="padding:6px 10px;font-size:10px;text-align:left;color:var(--gray-dim);text-transform:uppercase;letter-spacing:0.05em">Muscle</th>
              <th style="padding:6px 10px;font-size:10px;text-align:center;color:var(--gray-dim);text-transform:uppercase;letter-spacing:0.05em">Sets</th>
              <th style="padding:6px 10px;font-size:10px;text-align:right;color:var(--gray-dim);text-transform:uppercase;letter-spacing:0.05em">Status</th>
            </tr>
          </thead>
          <tbody>${muscleRows}</tbody>
        </table>
        ${audit.length > 0 ? `
        <div style="padding:10px 12px;border-top:1px solid var(--border-dim)">
          <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:var(--gray-dim);margin-bottom:6px">Audit Warnings</div>
          ${warningsHtml}
        </div>` : `
        <div style="padding:10px 12px;border-top:1px solid var(--border-dim)">
          ${warningsHtml}
        </div>`}
      </div>
    </div>`;
}

// ── Program Retrospective ────────────────────────────

async function renderRetrospective(programId) {
    try {
        const retro = await getProgramRetrospective(programId);
        if (!retro || retro.status === 'no_data') return '';

        const e1rmRows = (retro.e1rm_changes || []).slice(0, 8).map(e => `
            <div class="flex-between" style="padding:6px 0;border-bottom:1px solid var(--border-dim)">
                <div style="font-size:12px;font-weight:600">${e.name}</div>
                <div style="display:flex;gap:8px;align-items:center">
                    <span style="font-size:11px;color:var(--gray-dim)">${e.starting_e1rm?.toFixed(0) || '—'} →</span>
                    <span class="mono ${e.change > 0 ? 'text-green' : e.change < 0 ? 'text-red' : 'text-dim'}" style="font-size:14px;font-weight:700">
                        ${e.ending_e1rm?.toFixed(0) || '—'} lbs
                    </span>
                    <span style="font-size:10px;color:${e.change > 0 ? 'var(--green)' : 'var(--red)'}">${e.change > 0 ? '+' : ''}${e.change?.toFixed(1) || '0'}</span>
                </div>
            </div>`).join('');

        const formatPattern = (str) => str.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

        const volumeRows = (retro.volume_per_muscle || []).slice(0, 10).map(v => `
            <div class="flex-between" style="padding:4px 0">
                <span style="font-size:12px">${formatPattern(v.muscle_group)}</span>
                <span class="mono text-amber" style="font-size:12px">${v.total_effective_sets} sets</span>
            </div>`).join('');

        const bw = retro.body_weight;
        const bwHtml = bw && bw.start && bw.end
            ? `<div style="font-size:12px;color:var(--gray-mid)">Body weight: ${bw.start} → ${bw.end} lbs (${bw.change > 0 ? '+' : ''}${bw.change})</div>`
            : '';

        return `
        <div style="padding:0 16px 14px">
            <div style="background:var(--bg-card);border:1px solid var(--border-dim);border-radius:var(--radius-md);overflow:hidden">
                <div style="padding:12px 14px;border-bottom:1px solid var(--border-dim)">
                    <div style="font-size:13px;font-weight:700;letter-spacing:0.03em;text-transform:uppercase;color:var(--gray-bright)">Program Retrospective</div>
                    <div style="font-size:11px;color:var(--gray-dim);margin-top:2px">${retro.date_range.total_sessions} sessions · ${retro.date_range.start} to ${retro.date_range.end}</div>
                    ${bwHtml}
                </div>
                ${e1rmRows ? `
                <div style="padding:12px 14px;border-bottom:1px solid var(--border-dim)">
                    <div style="font-size:11px;font-weight:700;text-transform:uppercase;color:var(--gray-dim);margin-bottom:8px">Strength Changes</div>
                    ${e1rmRows}
                </div>` : ''}
                ${volumeRows ? `
                <div style="padding:12px 14px">
                    <div style="font-size:11px;font-weight:700;text-transform:uppercase;color:var(--gray-dim);margin-bottom:8px">Total Volume Per Muscle</div>
                    ${volumeRows}
                </div>` : ''}
            </div>
        </div>`;
    } catch (e) {
        return '';
    }
}

// ── Main Render ──────────────────────────────────────

export async function selectProgram(programId) {
    state.selectedProgramId = programId;
    window._currentProgramId = programId;
    const vc = $id('view-container');
    vc.innerHTML = `<div class="view">${loadingSpinner('Loading program...')}</div>`;

    try {
        const data = await getProgram(programId);
        const prog = data.program || data;
        const sessions = data.sessions || [];
        const volumeSummary = data.volume_summary || prog.volume_summary || null;

        const sessionsHtml = sessions.map(sess => {
            const exercises = sess.exercises || [];
            const exHtml = exercises.map(pe => renderExerciseRow(pe, detailWeek)).join('');

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

        const volumeHtml = renderVolumeSummary(volumeSummary);
        const weekTabsHtml = renderWeekTabs(prog, detailWeek);
        const nextPhaseHtml = renderNextPhaseButton(prog);
        const retroHtml = prog.status === 'completed'
            ? await renderRetrospective(programId)
            : '';

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
        ${weekTabsHtml}
        ${volumeHtml}
        ${nextPhaseHtml}
        ${retroHtml}
        ${sessionsHtml || '<div class="empty-state"><h3>No sessions</h3></div>'}
      </div>`;
    } catch (e) {
        vc.innerHTML = `<div class="view"><div class="empty-state"><h3>Error loading program</h3><button class="btn-primary" onclick="navigate('programs')">Back</button></div></div>`;
    }
}

// ── Window globals for inline onclick ────────────────
window.selectProgram = selectProgram;
