// js/views/exercise-detail.js — Single exercise detail view

import { state } from '../state/store.js';
import { activeWorkout } from '../state/workout-state.js';
import { getE1rm, getOverloadRec, getVolumeLandmarks } from '../api/analytics.js';
import { $id } from '../lib/dom.js';
import { fmtDate, capitalize, formatPattern, dotsHtml } from '../lib/format.js';
import { destroyChart, createChart } from '../components/charts.js';
import { renderExercises } from './exercises.js';

// ── Main Render ──────────────────────────────────────

export async function viewExerciseDetail(exId) {
    const ex = (state.exercises || []).find(e => e.id === exId);
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
          <span class="badge badge-amber">${ex.category || '\u2014'}</span>
          <span class="badge badge-gray">${formatPattern(ex.movement_pattern)}</span>
          <span class="badge badge-gray">${capitalize(ex.equipment || '')}</span>
        </div>
      </div>
      <div class="section" style="margin-top:12px">
        <div class="section-title" style="margin-bottom:8px">MUSCLES</div>
        <div class="card">
          <div style="margin-bottom:8px"><span style="font-size:11px;color:var(--gray-dim);text-transform:uppercase;letter-spacing:0.06em;font-weight:700">Primary</span><br>
            <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:5px">${(ex.primary_muscles || '').split(',').map(m => `<span class="muscle-tag" style="font-size:11px;padding:3px 8px">${m.trim()}</span>`).join('')}</div>
          </div>
          ${ex.secondary_muscles ? `<div style="margin-top:8px"><span style="font-size:11px;color:var(--gray-dim);text-transform:uppercase;letter-spacing:0.06em;font-weight:700">Secondary</span><br>
            <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:5px">${ex.secondary_muscles.split(',').map(m => `<span class="muscle-tag" style="font-size:11px;padding:3px 8px;opacity:0.7">${m.trim()}</span>`).join('')}</div>
          </div>` : ''}
        </div>
      </div>
      <div class="section">
        <div class="section-title" style="margin-bottom:8px">RATINGS</div>
        <div class="card">
          <div class="flex-between" style="margin-bottom:10px">
            <span style="font-size:12px;color:var(--gray-mid)">Fatigue Rating</span>
            ${dotsHtml(ex.fatigue_rating || 3)}
          </div>
          <div class="flex-between">
            <span style="font-size:12px;color:var(--gray-mid)">Complexity</span>
            ${dotsHtml(ex.complexity || 2)}
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
        <div class="section-title" style="margin-bottom:8px">e1RM \u2014 LAST 90 DAYS</div>
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
      ${activeWorkout.running ? `
        <div style="padding:0 16px 16px">
          <button class="btn-secondary btn-full" onclick='addExerciseToWorkout(${JSON.stringify(ex)})'>
            + Add to Current Workout
          </button>
        </div>` : ''}
    </div>`;

    // Load e1RM trend
    try {
        const e1rmData = await getE1rm(exId, 90);
        const history = e1rmData.history || [];
        const vlm = (await getVolumeLandmarks().catch(() => ({ landmarks: [] }))).landmarks || [];

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
            <div style="position:absolute;left:0;top:0;bottom:0;width:${(mev / mrv * 100).toFixed(0)}%;background:rgba(245,166,35,0.2);border-radius:6px"></div>
            <div style="position:absolute;left:${(mev / mrv * 100).toFixed(0)}%;top:0;bottom:0;width:${((mav - mev) / mrv * 100).toFixed(0)}%;background:rgba(245,166,35,0.5);border-radius:0 6px 6px 0"></div>
          </div>
          <div class="flex-between" style="margin-top:6px;font-size:10px;color:var(--gray-dim)">
            <span>Minimum Effective</span><span style="color:var(--amber)">Maximum Adaptive</span><span style="color:var(--red)">Maximum Recoverable</span>
          </div>
        </div>`;
        }

        // e1RM Chart
        if (history.length > 1) {
            createChart(`e1rm-${exId}`, `e1rm-chart-${exId}`, {
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

    } catch (e) { console.error(e); }

    // Overload recommendation
    try {
        const rec = await getOverloadRec(exId);
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
    } catch (e) {
        const overloadEl = $id('overload-detail');
        if (overloadEl) overloadEl.innerHTML = `<div class="text-dim text-sm">Log workouts to get overload recommendations.</div>`;
    }
}

// ── Window globals for inline onclick ────────────────
window.viewExerciseDetail = viewExerciseDetail;
