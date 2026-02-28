// normalize.js — Defensive data normalization for API responses

export function normalizeArray(data, key) {
    if (Array.isArray(data)) return data;
    return (data && data[key]) || [];
}

export function normalizeName(obj) {
    return obj.exercise_name || obj.name || '\u2014';
}

export function normalizeE1rm(obj) {
    return obj.estimated_1rm ?? obj.e1rm ?? obj.best_e1rm ?? null;
}
