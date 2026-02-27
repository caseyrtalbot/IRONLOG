import { get, post, del } from './client.js';
import { ATHLETE_ID } from '../config.js';

export function getPrograms() {
    return get('programs', { athlete_id: ATHLETE_ID });
}

export function deleteProgram(id) {
    return del(`programs/${id}`);
}

export function getProgram(id) {
    return get(`programs/${id}`);
}

export function generateProgram(data) {
    return post('programs/generate', data);
}

export function getSessionPrescriptions(programId, sessionId) {
    return get(`programs/${programId}/sessions/${sessionId}/prescriptions`);
}

export function getProgramRetrospective(programId) {
    return get(`programs/${programId}/retrospective`);
}
