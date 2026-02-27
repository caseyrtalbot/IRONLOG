import { get, post } from './client.js';
import { ATHLETE_ID } from '../config.js';

export function getAthlete() {
    return get('athlete', { id: ATHLETE_ID });
}

export function saveAthlete(data) {
    return post('athlete', data);
}
