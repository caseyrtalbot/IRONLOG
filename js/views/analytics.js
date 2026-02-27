// js/views/analytics.js — Analytics view with charts

import { state } from '../state/store.js';
import { getAnalytics, getAllE1rms, getVolumeLandmarks, saveVolumeLandmarks as apiSaveVolumeLandmarks } from '../api/analytics.js';
import { getWorkouts } from '../api/workouts.js';
import { $id } from '../lib/dom.js';
import { fmtDate, formatPattern } from '../lib/format.js';
import { showToast } from '../components/toast.js';
import { destroyChart } from '../components/charts.js';
import { ATHLETE_ID } from '../config.js';

// ── Main Render ──────────────────────────────────────

export async function renderAnalytics() {
    const vc = $id('view-container');
    vc.innerHTML = `
    <div class="view">
      <div class="view-header">
        <div class="view-title">Analytics</div>
        <div class="view-sub">Performance intelligence</div>
      </div>
      <div class="time-range-selector">
        ${[7, 30, 90, 'All'].map(d => `<button class="time-btn ${state.analyticsRange === d ? 'active' : ''}" onclick="setAnalyticsRange(${typeof d === 'number' ? d : "'all'"}, this)">${d}${typeof d === 'number' ? 'd' : ''}</button>`).join('')}
      </div>
      <div id="analytics-content">
        <div class="loading-center"><div class="spinner"></div><span>Loading analytics...</span></div>
      </div>
    </div>`;

    loadAnalyticsData();
}

// ── Range Selector ───────────────────────────────────

function setAnalyticsRange(range, btn) {
    state.analyticsRange = range;
    document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    loadAnalyticsData();
}

// ── Data Loader ──────────────────────────────────────

async function loadAnalyticsData() {
    const container = $id('analytics-content');
    if (!container) return;
    container.innerHTML = `<div class="loading-center"><div class="spinner"></div><span>Crunching numbers...</span></div>`;

    const days = state.analyticsRange === 'all' ? 365 : state.analyticsRange;

    try {
        const [volumeData, freqData, muscleData, workoutsData, e1rmData] = await Promise.all([
            getAnalytics(days, 'volume').catch(() => null),
            getAnalytics(days, 'frequency').catch(() => null),
            getAnalytics(days, 'muscle_volume').catch(() => null),
            getWorkouts(50).catch(() => []),
            getAllE1rms().catch(() => []),
        ]);

        const workouts = Array.isArray(workoutsData) ? workoutsData : (workoutsData.workouts || []);
        const e1rms = (Array.isArray(e1rmData) ? e1rmData : (e1rmData.exercises || [])).map(e => ({
            ...e,
            exercise_name: e.exercise_name || e.name,
        }));
        const volumePoints = Array.isArray(volumeData) ? volumeData : (volumeData?.data || []);
        const musclePoints = (Array.isArray(muscleData) ? muscleData : (muscleData?.data || [])).map(p => ({
            ...p,
            muscle_group: p.muscle_group || p.primary_muscles,
            sets: p.sets ?? p.total_sets,
            volume: p.volume ?? p.total_volume,
        }));
        const freqPoints = (Array.isArray(freqData) ? freqData : (freqData?.data || [])).map(p => ({
            ...p,
            count: p.count ?? p.session_count ?? p.total_sets,
        }));

        // Build heat calendar from workout dates
        const workoutDates = new Set(workouts.map(w => w.date?.split('T')[0] || w.date));
        const today = new Date();
        const calDays = [];
        for (let i = 83; i >= 0; i--) {
            const d = new Date(today);
            d.setDate(d.getDate() - i);
            const key = d.toISOString().split('T')[0];
            calDays.push({ date: key, worked: workoutDates.has(key) });
        }

        const heatHtml = calDays.map(d => `<div class="heat-day ${d.worked ? 'worked' : ''}" title="${d.date}"></div>`).join('');

        // e1RM top exercises
        const topE1rms = e1rms.slice(0, 6);

        container.innerHTML = `
      <!-- Volume Chart -->
      <div class="chart-card">
        <div class="chart-card-title">Volume Load Per Workout</div>
        <div class="chart-wrap" style="height:180px">
          <canvas id="volume-chart"></canvas>
        </div>
      </div>

      <!-- Frequency Heat Calendar -->
      <div class="chart-card">
        <div class="chart-card-title">Training Calendar (12 Weeks)</div>
        <div class="heat-calendar" id="heat-cal">${heatHtml}</div>
        <div style="display:flex;gap:8px;margin-top:10px;align-items:center;font-size:11px;color:var(--gray-dim)">
          <div class="heat-day" style="width:12px;height:12px;border-radius:2px;flex-shrink:0"></div><span>Rest</span>
          <div class="heat-day worked" style="width:12px;height:12px;border-radius:2px;flex-shrink:0"></div><span>Trained</span>
        </div>
      </div>

      <!-- Muscle Volume -->
      <div class="chart-card">
        <div class="chart-card-title">Muscle Group Volume</div>
        <div class="chart-wrap" style="height:220px">
          <canvas id="muscle-chart"></canvas>
        </div>
      </div>

      <!-- e1RM Trends -->
      <div class="chart-card">
        <div class="chart-card-title">Estimated 1RM \u2014 Current</div>
        ${topE1rms.length ? topE1rms.map(e => `
          <div class="flex-between" style="padding:8px 0;border-bottom:1px solid var(--border-dim)">
            <div>
              <div style="font-weight:600;font-size:13px">${e.exercise_name}</div>
              <div style="font-size:10px;color:var(--gray-dim);font-family:var(--font-mono)">${fmtDate(e.date)}</div>
            </div>
            <div class="mono text-amber" style="font-size:18px;font-weight:700">${e.estimated_1rm?.toFixed(0)} lbs</div>
          </div>`).join('') :
            `<div class="text-dim text-sm" style="padding:12px 0">Log workouts to track e1RM</div>`
        }
      </div>

      <!-- Movement Pattern Frequency -->
      <div class="chart-card">
        <div class="chart-card-title">Movement Pattern Frequency</div>
        <div class="chart-wrap" style="height:200px">
          <canvas id="freq-chart"></canvas>
        </div>
      </div>

      <!-- Volume Landmarks -->
      <div class="chart-card">
        <div class="chart-card-title">Volume Landmarks Editor
          <button class="btn-ghost" style="float:right;padding:4px 10px;font-size:10px;min-height:30px" onclick="saveVolumeLandmarks()">Save</button>
        </div>
        <div id="vlm-editor">
          <div class="loading-center" style="padding:16px"><div class="spinner spinner-sm"></div></div>
        </div>
      </div>`;

        // Render charts
        renderVolumeChart(volumePoints, workouts);
        renderMuscleChart(musclePoints);
        renderFreqChart(freqPoints);
        loadVolumeEditor();

    } catch (e) {
        console.error(e);
        container.innerHTML = `<div class="empty-state"><h3>Analytics unavailable</h3><p>Log some workouts first</p></div>`;
    }
}

// ── Chart Renderers (view-specific, not generic) ─────

function renderVolumeChart(volumePoints, workouts) {
    const ctx = document.getElementById('volume-chart');
    if (!ctx) return;
    destroyChart('volume');

    const labels = volumePoints.length ? volumePoints.map(p => fmtDate(p.date)) : workouts.slice(0, 20).reverse().map(w => fmtDate(w.date));
    const values = volumePoints.length ? volumePoints.map(p => p.volume || p.value || 0) : workouts.slice(0, 20).reverse().map(w => w.total_volume || 0);

    if (!labels.length) { ctx.parentElement.innerHTML = `<div class="text-dim text-sm" style="padding:16px">No data yet</div>`; return; }

    state.charts.volume = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{ label: 'Volume (lbs)', data: values, backgroundColor: 'rgba(245,166,35,0.6)', borderColor: '#F5A623', borderWidth: 1, borderRadius: 3 }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#555', font: { family: 'JetBrains Mono', size: 9 }, maxRotation: 45 } },
                y: { grid: { color: '#1a1a1a' }, ticks: { color: '#555', font: { family: 'JetBrains Mono', size: 10 } } }
            }
        }
    });
}

function renderMuscleChart(musclePoints) {
    const ctx = document.getElementById('muscle-chart');
    if (!ctx) return;
    destroyChart('muscle');
    if (!musclePoints.length) { ctx.parentElement.innerHTML = `<div class="text-dim text-sm" style="padding:16px">No data yet</div>`; return; }
    const top = musclePoints.slice(0, 10);
    state.charts.muscle = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: top.map(p => formatPattern(p.muscle_group || p.label || p.name || '')),
            datasets: [{ data: top.map(p => p.volume || p.sets || p.value || 0), backgroundColor: top.map((_, i) => `hsla(${35 + i * 15},85%,55%,0.7)`), borderRadius: 3 }]
        },
        options: {
            indexAxis: 'y', responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: '#1a1a1a' }, ticks: { color: '#555', font: { family: 'JetBrains Mono', size: 10 } } },
                y: { grid: { display: false }, ticks: { color: '#8A8A8A', font: { size: 11 } } }
            }
        }
    });
}

function renderFreqChart(freqPoints) {
    const ctx = document.getElementById('freq-chart');
    if (!ctx) return;
    destroyChart('freq');
    if (!freqPoints.length) { ctx.parentElement.innerHTML = `<div class="text-dim text-sm" style="padding:16px">No data yet</div>`; return; }
    const top = freqPoints.slice(0, 8);
    state.charts.freq = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: top.map(p => formatPattern(p.movement_pattern || p.label || '')),
            datasets: [{ data: top.map(p => p.count || p.frequency || p.value || 0), backgroundColor: 'rgba(245,166,35,0.5)', borderColor: '#F5A623', borderWidth: 1, borderRadius: 3 }]
        },
        options: {
            indexAxis: 'y', responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: '#1a1a1a' }, ticks: { color: '#555', font: { family: 'JetBrains Mono', size: 10 } } },
                y: { grid: { display: false }, ticks: { color: '#8A8A8A', font: { size: 11 } } }
            }
        }
    });
}

// ── Volume Landmarks Editor ──────────────────────────

async function loadVolumeEditor() {
    const editor = $id('vlm-editor');
    if (!editor) return;
    try {
        const res = await getVolumeLandmarks();
        const landmarks = Array.isArray(res) ? res : (res.landmarks || []);
        if (!landmarks.length) { editor.innerHTML = `<div class="text-dim text-sm">No volume landmarks configured. Go to Profile to set them up.</div>`; return; }
        editor.innerHTML = `<div>${landmarks.map(l => `
      <div class="vlm-editor-row">
        <div class="vlm-muscle-name">
          ${formatPattern(l.muscle_group)}
          <span class="vlm-current-sets">Current: ${l.current_sets || '?'} sets/wk</span>
        </div>
        <div class="vlm-inputs">
          <div class="vlm-input-group"><label>MEV</label><input type="number" class="vlm-input" inputmode="decimal" value="${l.mev}" data-muscle="${l.muscle_group}" data-field="mev"></div>
          <div class="vlm-input-group"><label>MAV Low</label><input type="number" class="vlm-input" inputmode="decimal" value="${l.mav_low}" data-muscle="${l.muscle_group}" data-field="mav_low"></div>
          <div class="vlm-input-group"><label>MAV High</label><input type="number" class="vlm-input" inputmode="decimal" value="${l.mav_high}" data-muscle="${l.muscle_group}" data-field="mav_high"></div>
          <div class="vlm-input-group"><label>MRV</label><input type="number" class="vlm-input" inputmode="decimal" value="${l.mrv}" data-muscle="${l.muscle_group}" data-field="mrv"></div>
        </div>
      </div>`).join('')}</div>`;
    } catch (e) {
        editor.innerHTML = `<div class="text-dim text-sm">Could not load landmarks.</div>`;
    }
}

async function saveVolumeLandmarks() {
    const editor = $id('vlm-editor');
    if (!editor) return;
    const inputs = editor.querySelectorAll('input[data-muscle]');
    const data = {};
    inputs.forEach(input => {
        const muscle = input.dataset.muscle;
        const field = input.dataset.field;
        if (!data[muscle]) data[muscle] = { muscle_group: muscle };
        data[muscle][field] = parseInt(input.value) || 0;
    });
    try {
        await apiSaveVolumeLandmarks({ athlete_id: ATHLETE_ID, landmarks: Object.values(data) });
        showToast('Volume landmarks saved', 'success');
    } catch (e) { showToast('Error saving landmarks', 'error'); }
}

// ── Window globals for inline onclick ────────────────
window.setAnalyticsRange = setAnalyticsRange;
window.saveVolumeLandmarks = saveVolumeLandmarks;
