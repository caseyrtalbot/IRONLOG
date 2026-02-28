// dom.js — DOM shorthand utilities

export function $id(id) { return document.getElementById(id); }

export function loadingSpinner(text = 'Loading...') {
    return `<div class="loading-center"><div class="spinner"></div><span>${text}</span></div>`;
}

export function loadingSpinnerSm() {
    return `<div class="loading-center" style="padding:16px"><div class="spinner spinner-sm"></div></div>`;
}

export function emptyState(title, message = '', icon = '') {
    const iconHtml = icon ? `<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">${icon}</svg>` : '';
    const msgHtml = message ? `<p>${message}</p>` : '';
    return `<div class="empty-state">${iconHtml}<h3>${title}</h3>${msgHtml}</div>`;
}

export function errorState(title, retryRoute = '') {
    const retryHtml = retryRoute ? `<button class="btn-primary" onclick="navigate('${retryRoute}')">Retry</button>` : '';
    return `<div class="empty-state"><h3>${title}</h3>${retryHtml}</div>`;
}

// Expose globally for inline event handlers in templates
window.$id = $id;
window.loadingSpinner = loadingSpinner;
window.loadingSpinnerSm = loadingSpinnerSm;
