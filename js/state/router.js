// js/state/router.js
// Hash-based router with route registry and view transitions

import { state } from './store.js';

const routes = {};

export function registerRoute(name, renderer) {
    routes[name] = renderer;
}

export function navigate(route) {
    if (!routes[route]) route = 'dashboard';
    state.currentRoute = route;
    history.replaceState(null, '', '#' + route);

    // Update nav active state
    document.querySelectorAll('.nav-item').forEach(el => {
        el.classList.toggle('active', el.dataset.route === route);
    });

    // Transition
    const vc = document.getElementById('view-container');
    vc.classList.add('transitioning');
    setTimeout(() => {
        vc.classList.remove('transitioning');
        // Destroy old charts
        Object.keys(state.charts).forEach(key => {
            if (state.charts[key]) { state.charts[key].destroy(); delete state.charts[key]; }
        });
        vc.innerHTML = '';
        routes[route]();
    }, 140);
}

function handleHash() {
    const hash = location.hash.slice(1) || 'dashboard';
    navigate(routes[hash] ? hash : 'dashboard');
}

export function initRouter() {
    window.addEventListener('hashchange', handleHash);
    handleHash();
}

// Global access for inline onclick handlers in HTML templates
window.navigate = navigate;
