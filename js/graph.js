// Graph engine: indexing, ripple (n-th order paths), shock propagation, loop checks.
// Pure logic, no DOM / three.js.

export const LAG_MONTHS = [0.5, 3, 12, 24]; // representative months per lag category

function pushMap(map, key, item) {
  let arr = map.get(key);
  if (!arr) { arr = []; map.set(key, arr); }
  arr.push(item);
}

export function edgeKey(e) { return e.from + '>' + e.to; }

export function buildGraph(nodes, edges) {
  const nodeById = new Map(nodes.map((n) => [n.id, n]));
  const valid = [];
  const out = new Map();
  const inn = new Map();
  const byKey = new Map();
  for (const e of edges) {
    if (!nodeById.has(e.from) || !nodeById.has(e.to) || e.from === e.to) continue;
    if (byKey.has(edgeKey(e))) continue; // dedupe
    valid.push(e);
    byKey.set(edgeKey(e), e);
    pushMap(out, e.from, e);
    pushMap(inn, e.to, e);
  }
  const degree = new Map();
  for (const e of valid) {
    degree.set(e.from, (degree.get(e.from) || 0) + 1);
    degree.set(e.to, (degree.get(e.to) || 0) + 1);
  }
  return { nodes, nodeById, edges: valid, out, inn, byKey, degree };
}

/**
 * Ripple exploration from one node: first-visit BFS tree up to maxDepth.
 * dir 'down' = effects (follow from->to), 'up' = drivers (follow to->from).
 * Expansion is strongest-first so each node's recorded path is a strong one.
 * Returns { nodes: Map(id -> {order, path, edges}), edgeOrders: Map(edgeKey -> order) }
 * path is in traversal order from the start node outward; edges[i] connects path[i], path[i+1]
 * (for dir 'up' the causal arrow of edges[i] points path[i+1] -> path[i]).
 */
export function ripple(graph, startId, dir = 'down', maxDepth = 3) {
  const visited = new Map([[startId, { order: 0, path: [startId], edges: [] }]]);
  const edgeOrders = new Map();
  let frontier = [startId];
  for (let depth = 1; depth <= maxDepth && frontier.length; depth++) {
    const next = [];
    for (const id of frontier) {
      const adj = (dir === 'down' ? graph.out.get(id) : graph.inn.get(id)) || [];
      const sorted = [...adj].sort((a, b) => b.strength - a.strength);
      for (const e of sorted) {
        const nb = dir === 'down' ? e.to : e.from;
        if (visited.has(nb)) continue;
        const prev = visited.get(id);
        visited.set(nb, { order: depth, path: [...prev.path, nb], edges: [...prev.edges, e] });
        edgeOrders.set(edgeKey(e), depth);
        next.push(nb);
      }
    }
    frontier = next;
  }
  visited.delete(startId);
  return { nodes: visited, edgeOrders };
}

/**
 * Shock propagation for the simulator.
 * shocks: { nodeId: value in [-1, 1] }
 * Effects accumulate over all simple paths (no node revisits within a path),
 * damped per hop; final value squashed with tanh.
 * Returns array sorted by |value|:
 *   { id, value, dominant: {v, path, edges, lagM}, conflict, posSum, negSum }
 */
export function propagate(graph, shocks, opts = {}) {
  // First hop carries full edge weight (direct textbook effects should dominate);
  // deeper hops decay by `damping` per hop so indirect ripples stay subordinate.
  const { damping = 0.5, maxDepth = 4, minAbs = 0.02, maxWave = 4000 } = opts;
  const contribs = new Map();
  let wave = [];
  for (const [id, v] of Object.entries(shocks)) {
    if (!v || !graph.nodeById.has(id)) continue;
    wave.push({ id, v, path: [id], edges: [], lagM: 0 });
  }
  for (let depth = 1; depth <= maxDepth && wave.length; depth++) {
    const next = [];
    for (const w of wave) {
      const adj = graph.out.get(w.id) || [];
      for (const e of adj) {
        if (w.path.includes(e.to)) continue;
        const v = w.v * e.sign * (e.strength / 3) * (depth === 1 ? 1 : damping);
        if (Math.abs(v) < minAbs) continue;
        const item = {
          id: e.to, v,
          path: [...w.path, e.to],
          edges: [...w.edges, e],
          lagM: w.lagM + LAG_MONTHS[e.lag],
        };
        pushMap(contribs, e.to, item);
        next.push(item);
      }
    }
    next.sort((a, b) => Math.abs(b.v) - Math.abs(a.v));
    wave = next.length > maxWave ? next.slice(0, maxWave) : next;
  }

  const results = [];
  for (const [id, list] of contribs) {
    if (id in shocks && shocks[id]) continue; // shocked nodes are inputs, not outputs
    let sum = 0, posSum = 0, negSum = 0;
    let dominant = list[0];
    for (const c of list) {
      sum += c.v;
      if (c.v > 0) posSum += c.v; else negSum += c.v;
      if (Math.abs(c.v) > Math.abs(dominant.v)) dominant = c;
    }
    const value = Math.tanh(sum * 1.2);
    const big = Math.max(posSum, -negSum);
    const small = Math.min(posSum, -negSum);
    const conflict = big > 0.05 && small > 0.05 && small / big > 0.33;
    results.push({ id, value, dominant, conflict, posSum, negSum });
  }
  results.sort((a, b) => Math.abs(b.value) - Math.abs(a.value));
  return results;
}

/** Direction glyphs along a path: dirs[i] applies to path node i. */
export function pathDirections(initialSign, edges) {
  const dirs = [initialSign >= 0 ? 1 : -1];
  for (const e of edges) dirs.push(dirs[dirs.length - 1] * e.sign);
  return dirs;
}

/** Lag bucket for a cumulative lag in months. 0: ~3mo, 1: 3-12mo, 2: 1yr+ */
export function lagBucket(months) {
  if (months <= 3.5) return 0;
  if (months <= 13) return 1;
  return 2;
}

/** Resolve a loop's node cycle into its edges (consecutive + closing pair). Null if broken. */
export function loopEdges(graph, nodeIds) {
  const edges = [];
  for (let i = 0; i < nodeIds.length; i++) {
    const from = nodeIds[i];
    const to = nodeIds[(i + 1) % nodeIds.length];
    const e = graph.byKey.get(from + '>' + to);
    if (!e) return null;
    edges.push(e);
  }
  return edges;
}

export function loopNetSign(edges) {
  return edges.reduce((s, e) => s * e.sign, 1);
}
