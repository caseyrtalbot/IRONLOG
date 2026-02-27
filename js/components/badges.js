// js/components/badges.js — Badge and pill HTML generators

import { capitalize, formatPhase } from '../lib/format.js';

/**
 * Program status badge.
 * Maps status string to a coloured badge.
 */
export function statusBadge(status) {
    const colorMap = {
        active:    'amber',
        completed: 'green',
        paused:    'gray',
    };
    const color = colorMap[status] || 'gray';
    const text = capitalize(status);
    return `<span class="badge badge-${color}">${text}</span>`;
}

/**
 * Training phase badge (accumulation / intensification / realization / deload).
 */
export function phaseBadge(phase) {
    return `<span class="badge badge-amber">${formatPhase(phase)}</span>`;
}

/**
 * Set-type pill shown next to each set row (W, B, A, D, C, etc.)
 */
export function setTypePill(setType) {
    const label = setType === 'working'
        ? 'W'
        : setType.charAt(0).toUpperCase();
    return `<span class="set-type-pill ${setType}">${label}</span>`;
}
