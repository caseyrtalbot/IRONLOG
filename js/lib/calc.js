// calc.js — Domain constants and pure calculation helpers (no DOM)

export const RPE_SCALE = [
  { val: 10,  desc: 'Max effort — could not do more' },
  { val: 9.5, desc: 'Could maybe do 1 more' },
  { val: 9,   desc: '1 RIR — definitely 1 left' },
  { val: 8.5, desc: '1–2 RIR' },
  { val: 8,   desc: '2 RIR — solid working set' },
  { val: 7.5, desc: '2–3 RIR' },
  { val: 7,   desc: '3 RIR — warm/moderate' },
  { val: 6,   desc: '4+ RIR — easy' },
];

export const SET_TYPES = ['working','warmup','backoff','amrap','drop','cluster'];

export const GOAL_INFO = {
  strength:     { label: 'Strength',    desc: 'Max force production. Low reps (1–5), high intensity (85–100% 1RM), long rest.' },
  hypertrophy:  { label: 'Hypertrophy', desc: 'Muscle growth. Moderate reps (6–15), moderate intensity (65–80% 1RM), pump focus.' },
  power:        { label: 'Power',       desc: 'Speed-strength. Med reps (1–5) explosive, 50–80% 1RM, full recovery.' },
  endurance:    { label: 'Endurance',   desc: 'Muscular endurance. High reps (15–30), lighter loads, short rest.' },
};

export const PHASE_INFO = {
  accumulation:    { label: 'Accumulation',    desc: 'High volume, moderate intensity. Build work capacity. Foundation phase.' },
  intensification: { label: 'Intensification', desc: 'Moderate volume, high intensity. Convert volume gains to strength.' },
  realization:     { label: 'Realization',     desc: 'Low volume, maximal intensity. Peak performance — competition prep.' },
  deload:          { label: 'Deload',          desc: 'Reduced volume & intensity. Active recovery to supercompensate.' },
};

export const SPLIT_INFO = {
  upper_lower:    { label: 'Upper / Lower',    desc: '2-day frequency split. Horizontal/vertical push+pull each session.' },
  push_pull_legs: { label: 'Push / Pull / Legs', desc: '3-way split. Push muscles, pull muscles, leg day each block.' },
  full_body:      { label: 'Full Body',        desc: 'Full body each session. Max frequency, great for 3-4 days/week.' },
};

export function calcE1rm(weight, reps, rpe) {
  if (!weight || !reps) return null;
  // Epley formula with RPE adjustment
  let effectiveReps = reps;
  if (rpe && rpe < 10) {
    const rir = 10 - rpe;
    effectiveReps = reps + rir;
  }
  if (effectiveReps <= 0) return weight;
  return +(weight * (1 + effectiveReps / 30)).toFixed(1);
}
