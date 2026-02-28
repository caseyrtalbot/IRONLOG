// js/components/timer.js — Workout timer and rest timer

import { activeWorkout, restTimer } from '../state/workout-state.js';
import { fmtSecondsTimer } from '../lib/format.js';
import { $id } from '../lib/dom.js';
import { showToast } from './toast.js';

// ── Workout Timer (header elapsed-time display) ────────────

export function startWorkoutTimer() {
    const display = $id('workout-timer-display');
    const text = $id('workout-timer-text');
    display.classList.remove('hidden');
    activeWorkout.timerInterval = setInterval(() => {
        if (!activeWorkout.startTime) return;
        const elapsed = Math.floor((Date.now() - activeWorkout.startTime) / 1000);
        text.textContent = fmtSecondsTimer(elapsed);
    }, 1000);
}

export function stopWorkoutTimer() {
    clearInterval(activeWorkout.timerInterval);
    $id('workout-timer-display').classList.add('hidden');
    $id('workout-timer-text').textContent = '0:00';
}

// ── Rest Timer (inline countdown) ─────────────────────────

function buildInlineTimerHtml(remaining, total) {
    const pct = ((total - remaining) / total * 100).toFixed(1);
    return `<div class="inline-rest-timer" id="inline-rest-timer">
      <div class="irt-bar"><div class="irt-progress" id="irt-progress" style="width:${pct}%"></div></div>
      <div class="irt-body">
        <div class="irt-time" id="irt-time">${fmtSecondsTimer(remaining)}</div>
        <div class="irt-controls">
          <button class="irt-adjust" onclick="APP.adjustRestTimer(-15)">-15</button>
          <button class="irt-skip" onclick="APP.skipRestTimer()">SKIP</button>
          <button class="irt-adjust" onclick="APP.adjustRestTimer(15)">+15</button>
        </div>
      </div>
    </div>`;
}

export function injectInlineTimer() {
    // Remove any existing inline timer
    document.getElementById('inline-rest-timer')?.remove();
    if (!restTimer.running) return;
    const anchor = document.getElementById(`set-row-${restTimer.anchorExIdx}-${restTimer.anchorSIdx}`);
    if (!anchor) return;
    anchor.insertAdjacentHTML('afterend', buildInlineTimerHtml(restTimer.remainingSeconds, restTimer.totalSeconds));
}

function showRestComplete() {
    const el = document.getElementById('inline-rest-timer');
    if (!el) return;
    el.innerHTML = `<div class="irt-body irt-complete">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6L9 17l-5-5"/></svg>
      <span>Rest complete</span>
    </div>`;
    setTimeout(() => {
        el.classList.add('irt-fade-out');
        el.addEventListener('animationend', () => el.remove());
    }, 2000);
}

export function startRestTimer(seconds = 120, exIdx = null, sIdx = null) {
    clearInterval(restTimer.interval);
    document.getElementById('inline-rest-timer')?.remove();

    restTimer.totalSeconds = seconds;
    restTimer.remainingSeconds = seconds;
    restTimer.running = true;
    restTimer.anchorExIdx = exIdx;
    restTimer.anchorSIdx = sIdx;

    injectInlineTimer();

    restTimer.interval = setInterval(() => {
        restTimer.remainingSeconds--;
        const rem = restTimer.remainingSeconds;
        const timeEl = document.getElementById('irt-time');
        const progressEl = document.getElementById('irt-progress');
        if (timeEl) timeEl.textContent = fmtSecondsTimer(rem);
        if (progressEl) {
            const pct = ((restTimer.totalSeconds - rem) / restTimer.totalSeconds * 100).toFixed(1);
            progressEl.style.width = `${pct}%`;
        }
        if (rem <= 0) {
            clearInterval(restTimer.interval);
            restTimer.running = false;
            showRestComplete();
            if (navigator.vibrate) navigator.vibrate([100, 50, 100]);
        }
    }, 1000);
}

export function adjustRestTimer(delta) {
    restTimer.remainingSeconds = Math.max(5, restTimer.remainingSeconds + delta);
    restTimer.totalSeconds = Math.max(restTimer.totalSeconds, restTimer.remainingSeconds);
    const timeEl = document.getElementById('irt-time');
    if (timeEl) timeEl.textContent = fmtSecondsTimer(restTimer.remainingSeconds);
}

export function skipRestTimer() {
    clearInterval(restTimer.interval);
    restTimer.running = false;
    const el = document.getElementById('inline-rest-timer');
    if (el) {
        el.classList.add('irt-fade-out');
        el.addEventListener('animationend', () => el.remove());
    }
}

// Global — called from inline onclick handlers in the inline timer
window.APP = { adjustRestTimer, skipRestTimer };
