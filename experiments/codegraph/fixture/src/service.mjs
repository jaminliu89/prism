import { normalizeIntent } from './core.mjs';
export function planIdea(value) {
  return { intent: normalizeIntent(value), stage: 0 };
}
