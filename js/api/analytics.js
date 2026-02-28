import { get, post } from './client.js';
import { ATHLETE_ID } from '../config.js';

export function getE1rm(exerciseId, days = 90) {
    return get('analytics/e1rm', { athlete_id: ATHLETE_ID, exercise_id: exerciseId, days });
}

export function getAllE1rms() {
    return get('analytics/e1rm', { athlete_id: ATHLETE_ID });
}

export function getOverloadRec(exerciseId) {
    return get('analytics/overload', { athlete_id: ATHLETE_ID, exercise_id: exerciseId });
}

export function getAnalytics(days, metric) {
    return get(`analytics/${metric}`, { athlete_id: ATHLETE_ID, days });
}

export function getVolumeLandmarks() {
    return get('analytics/volume-landmarks', { athlete_id: ATHLETE_ID });
}

export function saveVolumeLandmarks(data) {
    return post('analytics/volume-landmarks', data);
}

export function getMuscleStatus(days = 7) {
    return get('analytics/muscle-status', { athlete_id: ATHLETE_ID, days });
}

