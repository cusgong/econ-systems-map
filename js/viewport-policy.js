// Pure responsive policy for keeping the selected model visible beside UI.

export const NARROW_VIEWPORT_MAX = 900;

function finiteWidth(width) {
  const value = Number(width);
  return Number.isFinite(value) ? Math.max(0, value) : Infinity;
}

export function focusIdsForViewport(selectedId, contextualIds, viewportWidth) {
  const ids = Array.isArray(contextualIds) ? [...contextualIds] : [];
  finiteWidth(viewportWidth);
  if (selectedId) return [selectedId];
  return ids;
}

export function shouldReserveMapViewport(viewportWidth, panelCollapsed) {
  return finiteWidth(viewportWidth) <= NARROW_VIEWPORT_MAX && !panelCollapsed;
}

export function minimumFocusDistance(focusCount) {
  return Number(focusCount) <= 1 ? 40 : 36;
}

export function labelOpacityForState(distance, state = {}) {
  const d = Number.isFinite(Number(distance)) ? Math.max(0, Number(distance)) : 0;
  let opacity = d > 95 ? Math.max(0.35, 1 - (d - 95) / 130) : 1;
  if (state.selected) return 1;
  if (state.highlighted) return Math.max(0.92, opacity);
  if (state.dimmed) return Math.max(0.38, Math.min(0.42, opacity));
  return opacity;
}
