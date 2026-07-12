import test from 'node:test';
import assert from 'node:assert/strict';
import { NODES } from '../../data/nodes.js';
import { EDGES } from '../../data/edges.js';
import { buildGraph, propagate, ripple } from '../../js/graph.js';

const graph = buildGraph(NODES, EDGES);

test('canonical graph shape stays stable', () => {
  assert.equal(graph.nodes.length, 30);
  assert.equal(graph.edges.length, 107);
});

test('policy-rate ripple keeps direct market channels', () => {
  const result = ripple(graph, 'policy_rate', 'down', 3);

  assert.equal(result.nodes.get('market_rate').order, 1);
  assert.equal(result.nodes.get('liquidity').order, 1);
});

test('policy-rate shock preserves representative signs', () => {
  const result = new Map(
    propagate(graph, { policy_rate: 1 }).map((row) => [row.id, row.value]),
  );

  assert.ok(result.get('market_rate') > 0);
  assert.ok(result.get('liquidity') < 0);
});
