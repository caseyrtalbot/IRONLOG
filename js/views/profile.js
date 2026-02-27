// js/views/profile.js — Profile / athlete configuration view

import { state } from '../state/store.js';
import { getAthlete, saveAthlete } from '../api/athlete.js';
import { getVolumeLandmarks, saveVolumeLandmarks as apiSaveVolumeLandmarks } from '../api/analytics.js';
import { $id } from '../lib/dom.js';
import { capitalize, formatPattern } from '../lib/format.js';
import { showToast } from '../components/toast.js';
import { ATHLETE_ID } from '../config.js';

// ── Main Render ──────────────────────────────────────

export async function renderProfile() {
    const vc = $id('view-container');
    vc.innerHTML = `
    <div class="view">
      <div class="view-header">
        <div class="view-title">Profile</div>
        <div class="view-sub">Athlete configuration</div>
      </div>
      <div id="profile-content">
        <div class="loading-center"><div class="spinner"></div></div>
      </div>
    </div>`;

    try {
        const athlete = state.athlete || await getAthlete();
        state.athlete = athlete;
        const [vlmRes] = await Promise.all([getVolumeLandmarks().catch(() => [])]);
        const landmarks = Array.isArray(vlmRes) ? vlmRes : (vlmRes.landmarks || []);

        const content = $id('profile-content');
        content.innerHTML = `
      <div class="section">
        <div style="display:flex;align-items:center;gap:14px;margin-bottom:16px">
          <div class="profile-avatar">${(athlete.name || 'A').charAt(0).toUpperCase()}</div>
          <div>
            <div style="font-size:18px;font-weight:800">${athlete.name || 'Athlete'}</div>
            <div style="font-size:12px;color:var(--gray-dim);font-family:var(--font-mono)">${capitalize(athlete.experience_level || 'intermediate')} \u00b7 ${capitalize(athlete.primary_goal || 'strength')}</div>
          </div>
        </div>

        <div class="form-group"><label>Full Name</label>
          <input type="text" id="pf-name" value="${athlete.name || ''}" placeholder="Your name">
        </div>
        <div class="form-row">
          <div class="form-group"><label>Age</label>
            <input type="number" id="pf-age" inputmode="decimal" value="${athlete.age || ''}" placeholder="25">
          </div>
          <div class="form-group"><label>Body Weight (lbs)</label>
            <input type="number" id="pf-weight" inputmode="decimal" value="${athlete.body_weight || ''}" placeholder="185">
          </div>
        </div>
        <div class="form-row">
          <div class="form-group"><label>Body Fat %</label>
            <input type="number" id="pf-bf" inputmode="decimal" value="${athlete.body_fat_pct || ''}" placeholder="15">
          </div>
          <div class="form-group"><label>Training Age (yrs)</label>
            <input type="number" id="pf-ta" inputmode="decimal" value="${athlete.training_age || ''}" placeholder="3">
          </div>
        </div>
        <div class="form-group"><label>Experience Level</label>
          <div class="pill-selector" id="pf-exp">
            ${['beginner', 'intermediate', 'advanced', 'elite'].map(e => `<button class="pill ${athlete.experience_level === e ? 'active' : ''}" data-value="${e}" onclick="this.closest('.pill-selector').querySelectorAll('.pill').forEach(p=>p.classList.remove('active'));this.classList.add('active')">${capitalize(e)}</button>`).join('')}
          </div>
        </div>
        <div class="form-group"><label>Primary Goal</label>
          <div class="pill-selector" id="pf-goal">
            ${['strength', 'hypertrophy', 'power', 'endurance'].map(g => `<button class="pill ${athlete.primary_goal === g ? 'active' : ''}" data-value="${g}" onclick="this.closest('.pill-selector').querySelectorAll('.pill').forEach(p=>p.classList.remove('active'));this.classList.add('active')">${capitalize(g)}</button>`).join('')}
          </div>
        </div>
        <div class="form-row">
          <div class="form-group"><label>Training Days/Week</label>
            <input type="number" id="pf-days" inputmode="decimal" value="${athlete.training_days_per_week || 4}" min="1" max="7">
          </div>
          <div class="form-group"><label>Session Duration (min)</label>
            <input type="number" id="pf-dur" inputmode="decimal" value="${athlete.session_duration_min || 75}">
          </div>
        </div>
        <button class="btn-primary btn-full" id="pf-save-btn" onclick="saveProfile()">Save Profile</button>
      </div>

      <div class="section" style="padding-top:0">
        <div class="section-header">
          <div class="section-title">Volume Landmarks</div>
        </div>
        ${landmarks.length ? `
          <div class="card" id="vlm-profile-editor">
            ${landmarks.map(l => `
              <div class="vlm-editor-row">
                <div class="vlm-muscle-name">${formatPattern(l.muscle_group)}</div>
                <div class="vlm-inputs">
                  <div class="vlm-input-group"><label>MEV</label><input type="number" class="vlm-input" inputmode="decimal" value="${l.mev}" data-muscle="${l.muscle_group}" data-field="mev"></div>
                  <div class="vlm-input-group"><label>MAV-</label><input type="number" class="vlm-input" inputmode="decimal" value="${l.mav_low}" data-muscle="${l.muscle_group}" data-field="mav_low"></div>
                  <div class="vlm-input-group"><label>MAV+</label><input type="number" class="vlm-input" inputmode="decimal" value="${l.mav_high}" data-muscle="${l.muscle_group}" data-field="mav_high"></div>
                  <div class="vlm-input-group"><label>MRV</label><input type="number" class="vlm-input" inputmode="decimal" value="${l.mrv}" data-muscle="${l.muscle_group}" data-field="mrv"></div>
                </div>
              </div>`).join('')}
            <button class="btn-secondary btn-full" style="margin-top:12px" onclick="saveProfileLandmarks()">Save Landmarks</button>
          </div>` :
            `<div class="card text-dim text-sm">No landmarks configured yet.</div>`
        }
      </div>`;
    } catch (e) {
        $id('profile-content').innerHTML = `<div class="empty-state"><h3>Error loading profile</h3><button class="btn-primary" onclick="navigate('profile')">Retry</button></div>`;
    }
}

// ── Save Functions ───────────────────────────────────

async function saveProfile() {
    const btn = $id('pf-save-btn');
    if (btn) { btn.disabled = true; btn.innerHTML = '<div class="spinner spinner-sm"></div> SAVING...'; }

    const data = {
        id: ATHLETE_ID,
        name: $id('pf-name')?.value.trim() || state.athlete?.name,
        age: parseInt($id('pf-age')?.value) || null,
        body_weight: parseFloat($id('pf-weight')?.value) || null,
        body_fat_pct: parseFloat($id('pf-bf')?.value) || null,
        training_age: parseInt($id('pf-ta')?.value) || null,
        experience_level: document.querySelector('#pf-exp .pill.active')?.dataset.value || 'intermediate',
        primary_goal: document.querySelector('#pf-goal .pill.active')?.dataset.value || 'strength',
        training_days_per_week: parseInt($id('pf-days')?.value) || 4,
        session_duration_min: parseInt($id('pf-dur')?.value) || 75,
    };

    try {
        const res = await saveAthlete(data);
        state.athlete = res.athlete || data;
        showToast('Profile saved!', 'success');
    } catch (e) { showToast('Error saving profile', 'error'); }
    finally {
        if (btn) { btn.disabled = false; btn.innerHTML = 'Save Profile'; }
    }
}

async function saveProfileLandmarks() {
    const editor = document.getElementById('vlm-profile-editor');
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
        showToast('Volume landmarks saved!', 'success');
    } catch (e) { showToast('Error saving landmarks', 'error'); }
}

// ── Window globals for inline onclick ────────────────
window.saveProfile = saveProfile;
window.saveProfileLandmarks = saveProfileLandmarks;
