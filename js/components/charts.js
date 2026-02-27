// js/components/charts.js — Chart.js lifecycle management
//
// Only handles creating, storing, and destroying Chart instances.
// Specific chart renderers (volume, muscle, freq) live in the analytics view.

import { state } from '../state/store.js';

/**
 * Destroy a single chart instance by key and remove it from state.charts.
 */
export function destroyChart(key) {
    if (state.charts[key]) {
        state.charts[key].destroy();
        delete state.charts[key];
    }
}

/**
 * Destroy every chart instance tracked in state.charts.
 * Called by the router on navigation to prevent canvas leaks.
 */
export function destroyAllCharts() {
    Object.keys(state.charts).forEach(destroyChart);
}

/**
 * Create a Chart.js instance, store it in state.charts under `key`, and return it.
 * @param {string} key        — lookup key in state.charts
 * @param {string} canvasId   — DOM id of the <canvas> element
 * @param {object} config     — Chart.js configuration object ({ type, data, options })
 * @returns {Chart|null} the Chart instance, or null if canvas not found
 */
export function createChart(key, canvasId, config) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    destroyChart(key);
    const chart = new Chart(ctx, config);
    state.charts[key] = chart;
    return chart;
}
