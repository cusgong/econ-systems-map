// Deterministic screen-space layout for CSS2D node labels.

function finite(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function clamp(value, minimum, maximum) {
  if (maximum < minimum) return (minimum + maximum) / 2;
  return Math.min(maximum, Math.max(minimum, value));
}

function compareIds(a, b) {
  const left = String(a);
  const right = String(b);
  return left < right ? -1 : left > right ? 1 : 0;
}

function rectAt(x, y, width, height) {
  return {
    left: x - width / 2,
    top: y - height / 2,
    right: x + width / 2,
    bottom: y + height / 2,
  };
}

function rectsOverlap(a, b, gap = 0) {
  return a.left < b.right + gap
    && a.right > b.left - gap
    && a.top < b.bottom + gap
    && a.bottom > b.top - gap;
}

function normalizeObstacle(obstacle) {
  const left = finite(obstacle?.left, 0);
  const top = finite(obstacle?.top, 0);
  const right = finite(obstacle?.right, left);
  const bottom = finite(obstacle?.bottom, top);
  return {
    left: Math.min(left, right),
    top: Math.min(top, bottom),
    right: Math.max(left, right),
    bottom: Math.max(top, bottom),
  };
}

const LOCAL_RING_COUNT = 3;
const LOCAL_PROBE_BUDGET = 1 + LOCAL_RING_COUNT * 8;
const SELECTED_ASSOCIATION_CAP = 160;
const FALLBACK_RING_COUNT = 8;
const FALLBACK_DIRECTION_COUNT = 12;
const FALLBACK_PROBE_BUDGET = FALLBACK_RING_COUNT * FALLBACK_DIRECTION_COUNT;

function* localTargets(candidate, gap) {
  const stepX = Math.max(24, candidate.width * 0.58 + gap);
  const stepY = Math.max(20, candidate.height + gap);
  yield { x: candidate.preferredX, y: candidate.preferredY };
  for (let ring = 1; ring <= LOCAL_RING_COUNT; ring += 1) {
    const dx = stepX * ring;
    const dy = stepY * ring;
    yield { x: candidate.preferredX, y: candidate.preferredY - dy };
    yield { x: candidate.preferredX - dx, y: candidate.preferredY };
    yield { x: candidate.preferredX + dx, y: candidate.preferredY };
    yield { x: candidate.preferredX, y: candidate.preferredY + dy };
    yield { x: candidate.preferredX - dx, y: candidate.preferredY - dy };
    yield { x: candidate.preferredX + dx, y: candidate.preferredY - dy };
    yield { x: candidate.preferredX - dx, y: candidate.preferredY + dy };
    yield { x: candidate.preferredX + dx, y: candidate.preferredY + dy };
  }
}

function* selectedFallbackTargets(candidate) {
  const cap = Math.min(SELECTED_ASSOCIATION_CAP, candidate.maxDisplacement);
  if (!(cap > 0 && Number.isFinite(cap))) return;
  for (let ring = 1; ring <= FALLBACK_RING_COUNT; ring += 1) {
    const radius = cap * ring / FALLBACK_RING_COUNT;
    for (let direction = 0; direction < FALLBACK_DIRECTION_COUNT; direction += 1) {
      const angle = -Math.PI / 2 + direction * Math.PI * 2 / FALLBACK_DIRECTION_COUNT;
      yield {
        x: candidate.preferredX + Math.cos(angle) * radius,
        y: candidate.preferredY + Math.sin(angle) * radius,
      };
    }
  }
}

export function layoutNodeLabels(options = {}) {
  const viewportWidth = Math.max(1, finite(options.viewport?.width, 1));
  const viewportHeight = Math.max(1, finite(options.viewport?.height, 1));
  const padding = Math.max(0, finite(options.viewport?.padding, 8));
  const gap = Math.max(0, finite(options.gap, 4));
  const maxWidth = Math.max(1, viewportWidth - padding * 2);
  const maxHeight = Math.max(1, viewportHeight - padding * 2);
  const obstacles = (options.obstacles || []).map(normalizeObstacle);
  const occupied = [];
  const stats = options.stats && typeof options.stats === 'object' ? options.stats : null;
  if (stats) {
    stats.localProbes = 0;
    stats.fallbackProbes = 0;
    stats.totalProbes = 0;
    stats.localProbeBudget = LOCAL_PROBE_BUDGET;
    stats.fallbackProbeBudget = FALLBACK_PROBE_BUDGET;
  }

  const candidates = (options.candidates || []).map((candidate) => {
    const width = Math.min(maxWidth, Math.max(1, finite(candidate.width, 96)));
    const height = Math.min(maxHeight, Math.max(1, finite(candidate.height, 24)));
    const allowDistantFallback = !!candidate.allowDistantFallback;
    const rawMaxDisplacement = Number(candidate.maxDisplacement);
    return {
      ...candidate,
      id: String(candidate.id),
      width,
      height,
      preferredX: finite(candidate.preferredX, viewportWidth / 2),
      preferredY: finite(candidate.preferredY, viewportHeight / 2),
      priority: finite(candidate.priority, 0),
      critical: !!candidate.critical,
      maxDisplacement: Number.isFinite(rawMaxDisplacement)
        ? Math.max(0, rawMaxDisplacement)
        : allowDistantFallback
          ? SELECTED_ASSOCIATION_CAP
          : Infinity,
      allowDistantFallback,
      leaderThreshold: Number.isFinite(Number(candidate.leaderThreshold))
        ? Math.max(0, Number(candidate.leaderThreshold))
        : Infinity,
    };
  }).sort((a, b) => (
    Number(b.critical) - Number(a.critical)
    || b.priority - a.priority
    || compareIds(a.id, b.id)
  ));

  const placements = [];
  for (const candidate of candidates) {
    const bounds = {
      minX: padding + candidate.width / 2,
      maxX: viewportWidth - padding - candidate.width / 2,
      minY: padding + candidate.height / 2,
      maxY: viewportHeight - padding - candidate.height / 2,
    };
    const canUse = (target) => {
      const x = clamp(target.x, bounds.minX, bounds.maxX);
      const y = clamp(target.y, bounds.minY, bounds.maxY);
      if (Math.hypot(x - candidate.preferredX, y - candidate.preferredY)
        > candidate.maxDisplacement + 0.001) return null;
      const rect = rectAt(x, y, candidate.width, candidate.height);
      if (obstacles.some((obstacle) => rectsOverlap(rect, obstacle))) return null;
      if (occupied.some((placed) => rectsOverlap(rect, placed, gap))) return null;
      return { x, y, rect };
    };

    let placed = null;
    if (candidate.eligible !== false) {
      for (const target of localTargets(candidate, gap)) {
        if (stats) {
          stats.localProbes += 1;
          stats.totalProbes += 1;
        }
        placed = canUse(target);
        if (placed) break;
      }
      if (!placed && candidate.allowDistantFallback) {
        for (const target of selectedFallbackTargets(candidate)) {
          if (stats) {
            stats.fallbackProbes += 1;
            stats.totalProbes += 1;
          }
          placed = canUse(target);
          if (placed) break;
        }
      }
    }

    if (placed) occupied.push(placed.rect);
    const displacement = placed
      ? Math.hypot(placed.x - candidate.preferredX, placed.y - candidate.preferredY)
      : null;
    placements.push({
      id: candidate.id,
      priority: candidate.priority,
      critical: candidate.critical,
      visible: !!placed,
      x: placed?.x ?? null,
      y: placed?.y ?? null,
      displacement,
      showLeader: displacement !== null && displacement > candidate.leaderThreshold + 0.001,
      rect: placed?.rect ?? null,
    });
  }

  return placements.sort((a, b) => compareIds(a.id, b.id));
}
