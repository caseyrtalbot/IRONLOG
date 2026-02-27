// js/components/pills.js — Pill selector component

/**
 * Generate HTML for a pill-selector row.
 * @param {Array<{value:string, label:string}>} options — pill choices
 * @param {string} activeValue — which pill is currently selected
 * @param {string} name        — identifier for the selector (used as id)
 * @returns {string} HTML string
 */
export function pillSelectorHtml(options, activeValue, name) {
    const pills = options.map(opt => {
        const active = opt.value === activeValue ? ' active' : '';
        return `<button class="pill${active}" data-value="${opt.value}">${opt.label}</button>`;
    }).join('');
    return `<div class="pill-selector" id="${name}">${pills}</div>`;
}

/**
 * Attach click handlers to pill selectors within a container.
 * Toggles the `active` class so only one pill is selected at a time per group.
 * @param {HTMLElement} container — parent element containing `.pill-selector` groups
 */
export function bindPillSelector(container) {
    container.querySelectorAll('.pill-selector').forEach(ps => {
        ps.querySelectorAll('.pill').forEach(p => {
            p.addEventListener('click', () => {
                ps.querySelectorAll('.pill').forEach(x => x.classList.remove('active'));
                p.classList.add('active');
            });
        });
    });
}
