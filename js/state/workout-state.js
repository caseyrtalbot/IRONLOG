// js/state/workout-state.js
// Active workout and rest timer state + reset helpers

export const activeWorkout = {
    running: false,
    startTime: null,
    timerInterval: null,
    sessionId: null,
    programId: null,
    exercises: [],        // [{exercise, sets:[{...}], overloadRec, e1rm}]
    sessionRpe: 7,
    notes: '',
    bodyWeight: null,
};

export const restTimer = {
    running: false,
    totalSeconds: 120,
    remainingSeconds: 120,
    interval: null,
};

export function resetWorkout() {
    clearInterval(activeWorkout.timerInterval);
    Object.assign(activeWorkout, {
        running: false,
        startTime: null,
        timerInterval: null,
        sessionId: null,
        programId: null,
        exercises: [],
        sessionRpe: 7,
        notes: '',
        bodyWeight: null,
    });
}

export function resetRestTimer() {
    clearInterval(restTimer.interval);
    Object.assign(restTimer, {
        running: false,
        totalSeconds: 120,
        remainingSeconds: 120,
        interval: null,
    });
}
