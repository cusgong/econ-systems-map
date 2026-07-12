import test from 'node:test';
import assert from 'node:assert/strict';
import { NODES } from '../../data/nodes.js';
import { EDGES } from '../../data/edges.js';
import { buildGraph } from '../../js/graph.js';
import { computeHubMetrics, hubBandFor, radiusScaleFor } from '../../js/hub-metrics.js';

function syntheticGraph(nodeIds, edges) {
  const nodes = nodeIds.map((id) => ({ id }));
  const completeEdges = edges.map((edge) => ({
    strength: 3,
    confidence: 3,
    ...edge,
  }));
  return buildGraph(nodes, completeEdges);
}

function assertClose(actual, expected, epsilon = 1e-12) {
  assert.ok(
    Math.abs(actual - expected) <= epsilon,
    `expected ${actual} to be within ${epsilon} of ${expected}`,
  );
}

test('first-hop influence is not depth-decayed', () => {
  const graph = syntheticGraph(['a', 'b'], [{ from: 'a', to: 'b' }]);
  const metrics = computeHubMetrics(graph, { maxDepth: 1, decay: 0 });

  assert.equal(metrics.get('a').outInfluence, 1);
  assert.equal(metrics.get('b').inExposure, 1);
});

test('second and third hops each receive 0.68 decay', () => {
  const graph = syntheticGraph(
    ['a', 'b', 'c', 'd'],
    [
      { from: 'a', to: 'b' },
      { from: 'b', to: 'c' },
      { from: 'c', to: 'd' },
    ],
  );
  const metrics = computeHubMetrics(graph, { maxDepth: 3, decay: 0.68 });

  assertClose(metrics.get('a').outInfluence, 1 + 0.68 + 0.68 ** 2);
});

test('a later stronger path replaces an earlier weaker path to the same destination', () => {
  const graph = syntheticGraph(
    ['a', 'b', 'c', 'd'],
    [
      { from: 'a', to: 'b' },
      { from: 'a', to: 'c' },
      { from: 'b', to: 'd', strength: 1 },
      { from: 'c', to: 'd' },
    ],
  );
  const metrics = computeHubMetrics(graph, { maxDepth: 2, decay: 0.68 });
  const directReach = 1 + 1;
  const strongerSharedReach = 0.68;

  assertClose(metrics.get('a').outInfluence - directReach, strongerSharedReach);
});

test('causal paths do not revisit a node', () => {
  const graph = syntheticGraph(
    ['a', 'b', 'c'],
    [
      { from: 'a', to: 'b' },
      { from: 'b', to: 'a' },
      { from: 'b', to: 'c' },
    ],
  );
  const metrics = computeHubMetrics(graph, { maxDepth: 3, decay: 0.68 });

  assertClose(metrics.get('a').outInfluence, 1 + 0.68);
});

test('hub raw score weights outgoing influence 60% and incoming exposure 40%', () => {
  const graph = syntheticGraph(
    ['a', 'b', 'c'],
    [
      { from: 'a', to: 'b' },
      { from: 'a', to: 'c' },
    ],
  );
  const metrics = computeHubMetrics(graph, { maxDepth: 1 });

  assert.equal(metrics.get('a').hubRaw, 0.6);
  assert.equal(metrics.get('b').hubRaw, 0.4);
  assert.equal(metrics.get('c').hubRaw, 0.4);
});

test('10th-to-90th percentile clipping keeps hub scores in the 0-to-1 range', () => {
  const sourceIds = Array.from({ length: 10 }, (_, index) => `source_${index + 1}`);
  const graph = syntheticGraph(
    [...sourceIds, 'sink'],
    sourceIds.map((from, index) => ({
      from,
      to: 'sink',
      strength: 3 * ((index + 1) / 10),
    })),
  );
  const metrics = computeHubMetrics(graph, {
    maxDepth: 1,
    outWeight: 1,
    inWeight: 0,
  });
  const scores = [...metrics.values()].map((metric) => metric.hubScore);

  assert.ok(scores.every((score) => score >= 0 && score <= 1));
  assert.equal(metrics.get('sink').hubScore, 0);
  assert.equal(metrics.get('source_1').hubScore, 0);
  assertClose(metrics.get('source_2').hubScore, 0.125);
  assert.equal(metrics.get('source_9').hubScore, 1);
  assert.equal(metrics.get('source_10').hubScore, 1);
});

test('current graph produces deterministic 30-node hub snapshot', () => {
  const metrics = computeHubMetrics(buildGraph(NODES, EDGES));
  const actual = Object.fromEntries([...metrics].map(([id, value]) => [id, value.score100]));

  assert.equal(metrics.size, 30);
  assert.deepEqual(actual, {
    policy_rate: 100,
    market_rate: 77,
    liquidity: 7,
    credit_spread: 4,
    bank_lending: 63,
    cpi: 100,
    inflation_exp: 71,
    wages: 60,
    fx: 59,
    exports: 90,
    current_account: 0,
    capital_flows: 40,
    fed_rate: 8,
    global_growth: 47,
    consumption: 100,
    investment: 56,
    employment: 98,
    earnings: 80,
    defaults: 73,
    gdp: 99,
    stocks: 23,
    housing: 20,
    household_debt: 13,
    oil: 75,
    commodity: 0,
    fiscal: 18,
    geopolitics: 88,
    tech: 50,
    risk_sentiment: 27,
    consumer_conf: 0,
  });
});

test('radius mapping preserves the approved area scale and 0/50/100 ordering', () => {
  const low = radiusScaleFor(0);
  const medium = radiusScaleFor(0.5);
  const high = radiusScaleFor(1);

  assert.equal(low, 0.82);
  assert.equal(medium, 1.074895);
  assert.equal(high, 1.28);
  assert.ok(low < medium);
  assert.ok(medium < high);
});

test('hub band boundaries are low, medium, and high thirds', () => {
  assert.equal(hubBandFor(0), 'low');
  assert.equal(hubBandFor((1 / 3) - Number.EPSILON), 'low');
  assert.equal(hubBandFor(1 / 3), 'medium');
  assert.equal(hubBandFor((2 / 3) - Number.EPSILON), 'medium');
  assert.equal(hubBandFor(2 / 3), 'high');
  assert.equal(hubBandFor(1), 'high');
});
