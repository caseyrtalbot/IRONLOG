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

// ── Rest Timer (overlay countdown) ─────────────────────────

export function startRestTimer(seconds = 120) {
    const overlay = $id('rest-timer-overlay');
    const display = $id('rest-timer-display');
    const ring = $id('rest-ring-progress');
    const circumference = 276.46;

    clearInterval(restTimer.interval);
    restTimer.totalSeconds = seconds;
    restTimer.remainingSeconds = seconds;
    restTimer.running = true;
    overlay.classList.remove('hidden');
    display.textContent = fmtSecondsTimer(seconds);
    ring.style.strokeDashoffset = '0';

    restTimer.interval = setInterval(() => {
        restTimer.remainingSeconds--;
        const rem = restTimer.remainingSeconds;
        display.textContent = fmtSecondsTimer(rem);
        const offset = circumference * (1 - rem / restTimer.totalSeconds);
        ring.style.strokeDashoffset = offset.toFixed(2);
        if (rem <= 0) {
            clearInterval(restTimer.interval);
            restTimer.running = false;
            overlay.classList.add('hidden');
            showToast('Rest complete \u2014 next set!', 'success');
            // Vibrate if available
            if (navigator.vibrate) navigator.vibrate([100, 50, 100]);
        }
    }, 1000);
}

export function adjustRestTimer(delta) {
    restTimer.remainingSeconds = Math.max(5, restTimer.remainingSeconds + delta);
    restTimer.totalSeconds = Math.max(restTimer.totalSeconds, restTimer.remainingSeconds);
    $id('rest-timer-display').textContent = fmtSecondsTimer(restTimer.remainingSeconds);
}

export function skipRestTimer() {
    clearInterval(restTimer.interval);
    restTimer.running = false;
    $id('rest-timer-overlay').classList.add('hidden');
}

// Global — called from inline onclick handlers in the rest-timer overlay
window.APP = { adjustRestTimer, skipRestTimer };
