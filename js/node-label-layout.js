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

function localTargets(candidate, gap) {
  const stepX = Math.max(24, candidate.width * 0.58 + gap);
  const stepY = Math.max(20, candidate.height + gap);
  const targets = [{ x: candidate.preferredX, y: candidate.preferredY }];
  for (let ring = 1; ring <= 3; ring += 1) {
    const dx = stepX * ring;
    const dy = stepY * ring;
    targets.push(
      { x: candidate.preferredX, y: candidate.preferredY - dy },
      { x: candidate.preferredX - dx, y: candidate.preferredY },
      { x: candidate.preferredX + dx, y: candidate.preferredY },
      { x: candidate.preferredX, y: candidate.preferredY + dy },
      { x: candidate.preferredX - dx, y: candidate.preferredY - dy },
      { x: candidate.preferredX + dx, y: candidate.preferredY - dy },
      { x: candidate.preferredX - dx, y: candidate.preferredY + dy },
      { x: candidate.preferredX + dx, y: candidate.preferredY + dy },
    );
  }
  return targets;
}

function fallbackTargets(candidate, bounds) {
  const step = Math.max(8, Math.min(20, Math.floor(candidate.height / 2)));
  const targets = [];
  for (let y = bounds.minY; y <= bounds.maxY + 0.001; y += step) {
    for (let x = bounds.minX; x <= bounds.maxX + 0.001; x += step) {
      targets.push({ x, y });
    }
  }
  if (!targets.some(({ x }) => Math.abs(x - bounds.maxX) < 0.001)) {
    for (let y = bounds.minY; y <= bounds.maxY + 0.001; y += step) {
      targets.push({ x: bounds.maxX, y });
    }
  }
  if (!targets.some(({ y }) => Math.abs(y - bounds.maxY) < 0.001)) {
    for (let x = bounds.minX; x <= bounds.maxX + 0.001; x += step) {
      targets.push({ x, y: bounds.maxY });
    }
  }
  targets.sort((a, b) => {
    const aDistance = (a.x - candidate.preferredX) ** 2 + (a.y - candidate.preferredY) ** 2;
    const bDistance = (b.x - candidate.preferredX) ** 2 + (b.y - candidate.preferredY) ** 2;
    return aDistance - bDistance || a.y - b.y || a.x - b.x;
  });
  return targets;
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

  const candidates = (options.candidates || []).map((candidate) => {
    const width = Math.min(maxWidth, Math.max(1, finite(candidate.width, 96)));
    const height = Math.min(maxHeight, Math.max(1, finite(candidate.height, 24)));
    return {
      ...candidate,
      id: String(candidate.id),
      width,
      height,
      preferredX: finite(candidate.preferredX, viewportWidth / 2),
      preferredY: finite(candidate.preferredY, viewportHeight / 2),
      priority: finite(candidate.priority, 0),
      critical: !!candidate.critical,
      maxDisplacement: Number.isFinite(Number(candidate.maxDisplacement))
        ? Math.max(0, Number(candidate.maxDisplacement))
        : Infinity,
      allowDistantFallback: !!candidate.allowDistantFallback,
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
      if (!candidate.allowDistantFallback
        && Math.hypot(x - candidate.preferredX, y - candidate.preferredY)
          > candidate.maxDisplacement + 0.001) return null;
      const rect = rectAt(x, y, candidate.width, candidate.height);
      if (obstacles.some((obstacle) => rectsOverlap(rect, obstacle))) return null;
      if (occupied.some((placed) => rectsOverlap(rect, placed, gap))) return null;
      return { x, y, rect };
    };

    let placed = null;
    if (candidate.eligible !== false) {
      const targets = localTargets(candidate, gap).filter((target) => (
        Math.hypot(
          target.x - candidate.preferredX,
          target.y - candidate.preferredY,
        ) <= candidate.maxDisplacement + 0.001
      ));
      if (candidate.critical) {
        targets.push(...fallbackTargets(candidate, bounds).filter((target) => (
          candidate.allowDistantFallback
          || Math.hypot(
            target.x - candidate.preferredX,
            target.y - candidate.preferredY,
          ) <= candidate.maxDisplacement + 0.001
        )));
      }
      for (const target of targets) {
        placed = canUse(target);
        if (placed) break;
      }
    }

    if (placed) occupied.push(placed.rect);
    placements.push({
      id: candidate.id,
      priority: candidate.priority,
      critical: candidate.critical,
      visible: !!placed,
      x: placed?.x ?? null,
      y: placed?.y ?? null,
      displacement: placed
        ? Math.hypot(placed.x - candidate.preferredX, placed.y - candidate.preferredY)
        : null,
      rect: placed?.rect ?? null,
    });
  }

  return placements.sort((a, b) => compareIds(a.id, b.id));
}
