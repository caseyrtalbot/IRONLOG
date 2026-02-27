import { get } from './client.js';
import { ATHLETE_ID } from '../config.js';

export function getDashboard() {
    return get('dashboard', { athlete_id: ATHLETE_ID });
}
