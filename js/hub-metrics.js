const DEFAULTS = Object.freeze({
  maxDepth: 3,
  decay: 0.68,
  outWeight: 0.60,
  inWeight: 0.40,
});

const MIN_RADIUS = 0.82;
const MAX_RADIUS = 1.28;

function normalize(values) {
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  return values.map((value) => (hi === lo ? 0.5 : (value - lo) / (hi - lo)));
}

function quantile(sorted, percentile) {
  const position = (sorted.length - 1) * percentile;
  const lower = Math.floor(position);
  const upper = Math.ceil(position);
  return sorted[lower] + (sorted[upper] - sorted[lower]) * (position - lower);
}

function strongestReach(graph, origin, { maxDepth, decay }) {
  const best = new Map();

  function walk(id, depth, score, seen) {
    if (depth >= maxDepth) return;

    for (const edge of graph.out.get(id) || []) {
      if (seen.has(edge.to)) continue;

      const quality = (edge.strength / 3) * (edge.confidence / 3);
      const nextScore = score * quality * (depth === 0 ? 1 : decay);
      if (nextScore > (best.get(edge.to) || 0)) best.set(edge.to, nextScore);
      walk(edge.to, depth + 1, nextScore, new Set([...seen, edge.to]));
    }
  }

  walk(origin, 0, 1, new Set([origin]));
  return best;
}

export function radiusScaleFor(score) {
  const clampedScore = Math.max(0, Math.min(1, score));
  const value = Math.sqrt(
    MIN_RADIUS ** 2 + (MAX_RADIUS ** 2 - MIN_RADIUS ** 2) * clampedScore,
  );
  return Number(value.toFixed(6));
}

export function hubBandFor(score) {
  return score < 1 / 3 ? 'low' : score < 2 / 3 ? 'medium' : 'high';
}

export function computeHubMetrics(graph, options = {}) {
  const opts = { ...DEFAULTS, ...options };
  const ids = graph.nodes.map((node) => node.id);
  const reaches = new Map(
    ids.map((id) => [id, strongestReach(graph, id, opts)]),
  );
  const outgoing = ids.map((id) => (
    [...reaches.get(id).values()].reduce((sum, value) => sum + value, 0)
  ));
  const incoming = ids.map((target) => (
    ids.reduce(
      (sum, origin) => sum + (reaches.get(origin).get(target) || 0),
      0,
    )
  ));
  const outNorm = normalize(outgoing);
  const inNorm = normalize(incoming);
  const raw = ids.map((id, index) => (
    opts.outWeight * outNorm[index] + opts.inWeight * inNorm[index]
  ));
  const sorted = [...raw].sort((a, b) => a - b);
  const lo = quantile(sorted, 0.10);
  const hi = quantile(sorted, 0.90);

  return new Map(ids.map((id, index) => {
    const score = hi === lo
      ? 0.5
      : Math.max(0, Math.min(1, (raw[index] - lo) / (hi - lo)));

    return [id, Object.freeze({
      outInfluence: outgoing[index],
      inExposure: incoming[index],
      hubRaw: raw[index],
      hubScore: score,
      score100: Math.round(score * 100),
      radiusScale: radiusScaleFor(score),
      band: hubBandFor(score),
    })];
  }));
}
