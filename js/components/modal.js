// js/components/modal.js — Generic full-screen modal helpers

/**
 * Create a full-screen modal div and append it to document.body.
 * @param {string} id          — DOM id for the modal element
 * @param {string} innerHTML   — HTML content inside the modal
 * @param {string} [className] — optional CSS class (default: 'exercise-search-modal')
 * @returns {HTMLElement} the modal element
 */
export function createModal(id, innerHTML, className = 'exercise-search-modal') {
    const modal = document.createElement('div');
    modal.className = className;
    modal.id = id;
    modal.innerHTML = innerHTML;
    document.body.appendChild(modal);
    return modal;
}

/**
 * Remove a modal from the DOM by its id.
 * @param {string} id — DOM id of the modal to remove
 */
export function closeModal(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}
