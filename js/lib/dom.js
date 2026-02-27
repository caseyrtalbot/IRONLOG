// dom.js — DOM shorthand utilities

export function $id(id) { return document.getElementById(id); }

export function dotsHtml(filled, total=5) {
  let h = '<div class="dots-rating">';
  for (let i=1;i<=total;i++) h += `<div class="dot ${i<=filled?'filled':'empty'}"></div>`;
  return h + '</div>';
}

// Expose globally for inline event handlers in templates
window.$id = $id;
