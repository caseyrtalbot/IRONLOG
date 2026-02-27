import { get, post, del } from './client.js';
import { ATHLETE_ID } from '../config.js';

export function saveWorkout(data) {
    return post('workouts', data);
}

export function getWorkouts(limit = 20) {
    return get('workouts', { athlete_id: ATHLETE_ID, limit });
}

export function getWorkoutDetail(id) {
    return get(`workouts/${id}`);
}

export function deleteWorkout(id) {
    return del(`workouts/${id}`);
}
