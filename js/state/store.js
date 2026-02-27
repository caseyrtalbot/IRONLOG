// js/state/store.js
// Central application state (excludes activeWorkout & restTimer — see workout-state.js)

export const state = {
    athlete: null,
    dashboard: null,
    exercises: null,        // cached exercise list
    movementPatterns: null,
    muscleGroups: null,
    programs: null,
    e1rms: null,
    currentRoute: 'dashboard',
    charts: {},             // chart instances by id

    // UI ephemeral
    exerciseFilter: { pattern: 'all', equipment: 'all', muscle: 'all', query: '' },
    programGen: { step: 1, goal: null, phase: null, split: null, weeks: 4, days: 4, name: '' },
    analyticsRange: 30,
    selectedProgramId: null,
    generatingProgram: false,
};
