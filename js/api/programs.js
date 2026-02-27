import { get, post } from './client.js';
import { ATHLETE_ID } from '../config.js';

export function getPrograms() {
    return get('programs', { athlete_id: ATHLETE_ID });
}

export function getProgram(id) {
    return get(`programs/${id}`);
}

export function generateProgram(data) {
    return post('programs/generate', data);
}
