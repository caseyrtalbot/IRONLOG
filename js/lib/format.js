// format.js — Display formatting helpers (no DOM mutation)

import { GOAL_INFO, PHASE_INFO } from './calc.js';

export function fmtDate(dateStr) {
  if (!dateStr) return '\u2014';
  const d = new Date(dateStr.replace(' ', 'T'));
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function fmtDuration(min) {
  if (!min) return '\u2014';
  const h = Math.floor(min / 60);
  const m = min % 60;
  return h ? `${h}h ${m}m` : `${m}m`;
}

export function fmtSecondsTimer(s) {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${sec.toString().padStart(2,'0')}`;
}

export function capitalize(str) {
  return str ? str.charAt(0).toUpperCase() + str.slice(1) : '';
}

export function formatPattern(p) {
  return p ? p.split('_').map(capitalize).join(' ') : '';
}

export function formatGoal(g) { return GOAL_INFO[g]?.label || capitalize(g); }
export function formatPhase(p) { return PHASE_INFO[p]?.label || capitalize(p); }

export function dotsHtml(filled, total=5) {
  let h = '<div class="dots-rating">';
  for (let i=1;i<=total;i++) h += `<div class="dot ${i<=filled?'filled':'empty'}"></div>`;
  return h + '</div>';
}

export function getTimeOfDay() {
  const h = new Date().getHours();
  if (h < 12) return 'MORNING';
  if (h < 17) return 'AFTERNOON';
  return 'EVENING';
}
