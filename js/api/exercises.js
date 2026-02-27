import { get } from './client.js';

export function getExercises(params = {}) {
    return get('exercises', params);
}

export function searchExercises(q) {
    return get('exercises/search', { q });
}

export function getMovementPatterns() {
    return get('exercises/patterns');
}

export function getMuscleGroups() {
    return get('exercises/muscles');
}
