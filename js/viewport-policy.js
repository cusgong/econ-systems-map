// Pure responsive policy for keeping the selected model visible beside UI.

export const NARROW_VIEWPORT_MAX = 900;

function finiteWidth(width) {
  const value = Number(width);
  return Number.isFinite(value) ? Math.max(0, value) : Infinity;
}

export function focusIdsForViewport(selectedId, contextualIds, viewportWidth) {
  const ids = Array.isArray(contextualIds) ? [...contextualIds] : [];
  if (finiteWidth(viewportWidth) <= NARROW_VIEWPORT_MAX && selectedId) {
    return [selectedId];
  }
  return ids;
}

export function shouldReserveMapViewport(viewportWidth, panelCollapsed) {
  return finiteWidth(viewportWidth) <= NARROW_VIEWPORT_MAX && !panelCollapsed;
}

export function minimumFocusDistance(focusCount) {
  return Number(focusCount) <= 1 ? 28 : 36;
}
