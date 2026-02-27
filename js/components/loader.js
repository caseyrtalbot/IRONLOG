// js/components/loader.js — Loading spinner HTML

export function loaderHtml(text = 'Loading...') {
    return `<div class="loading-center"><div class="spinner"></div><span>${text}</span></div>`;
}
