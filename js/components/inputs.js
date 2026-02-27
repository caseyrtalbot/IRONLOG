// js/components/inputs.js — Workout set input components

import { formatPattern } from '../lib/format.js';
import { RPE_SCALE, SET_TYPES } from '../lib/calc.js';
import { setTypePill } from './badges.js';

/**
 * Build a single set row within an exercise block.
 * Inline onclick handlers (onSetInput, logSet) are set on `window` by the workout view.
 */
export function buildSetRow(set, exIdx, sIdx) {
    const typePill = setTypePill(set.set_type);
    const doneClass = set.logged ? 'done' : '';
    const rowClass = set.logged ? 'logged' : '';

    return `
    <div class="set-row ${rowClass}" id="set-row-${exIdx}-${sIdx}">
      <div class="set-num">${typePill}</div>
      <div>
        <input type="number" class="set-input" inputmode="decimal" placeholder="${set.weight || '\u2014'}"
          value="${set.weight || ''}" id="set-w-${exIdx}-${sIdx}"
          onchange="onSetInput(${exIdx},${sIdx})" oninput="onSetInput(${exIdx},${sIdx})">
      </div>
      <div>
        <input type="number" class="set-input" inputmode="decimal" placeholder="${set.reps || '\u2014'}"
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
          onclick="logSet(${exIdx},${sIdx})" title="${set.logged ? 'Logged' : 'Log set'}">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6L9 17l-5-5"/></svg>
        </button>
      </div>
    </div>`;
}

/**
 * Build a full exercise block (header, set-type selector, set rows, add-set button).
 * Inline onclick handlers (toggleRpeTooltip, removeExercise, setCurrentSetType, addSet)
 * are set on `window` by the workout view.
 */
export function buildExerciseBlock(ex, exIdx) {
    const ssClass = ex.superset_group ? `superset-${ex.superset_group}` : '';
    const ssHtml = ex.superset_group ? `<span class="superset-label">${ex.superset_group}</span>` : '';

    const overloadHtml = ex.overloadRec ? `
    <div class="overload-rec">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
      ${ex.overloadRec.recommendation || 'Based on last session'}
    </div>` : '';

    const e1rmHtml = ex.e1rm
        ? `<div class="e1rm-inline">e1RM: <strong>${ex.e1rm}</strong> lbs</div>`
        : `<div class="e1rm-inline" id="e1rm-ex-${exIdx}"></div>`;

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
          <div class="exercise-block-meta">${formatPattern(ex.exercise.movement_pattern)} \u00b7 ${ex.exercise.primary_muscles || ''}</div>
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
        ${SET_TYPES.map(t => `<button class="stype-pill ${ex.currentSetType === t ? 'active' : ''}" onclick="setCurrentSetType(${exIdx},'${t}')">${t.toUpperCase()}</button>`).join('')}
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
