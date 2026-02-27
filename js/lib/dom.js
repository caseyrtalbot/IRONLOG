// dom.js — DOM shorthand utilities

export function $id(id) { return document.getElementById(id); }

// Expose globally for inline event handlers in templates
window.$id = $id;
