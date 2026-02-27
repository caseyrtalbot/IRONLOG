// js/components/toast.js — Toast notification component

export function showToast(msg, type = 'info', duration = 3000) {
    const tc = document.getElementById('toast-container');
    if (!tc) return;
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    const icons = { success: '\u2713', error: '\u2717', info: '\u2192' };
    t.innerHTML = `<span style="font-weight:800">${icons[type] || '\u2192'}</span> ${msg}`;
    tc.appendChild(t);
    setTimeout(() => {
        t.style.opacity = '0';
        t.style.transform = 'translateY(4px)';
        t.style.transition = '0.2s ease';
        setTimeout(() => t.remove(), 200);
    }, duration);
}

// Global — called from inline onclick handlers
window.showToast = showToast;
