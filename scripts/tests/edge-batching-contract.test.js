import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import * as THREE from '../../vendor/three.module.min.js';
import { EDGES } from '../../data/edges.js';
import {
  PASSIVE_EDGE_BASE_OPACITY,
  PASSIVE_EDGE_GROUP_KEYS,
  PASSIVE_EDGE_HIGHLIGHT_OPACITY,
  PASSIVE_EDGE_SEGMENTS,
  buildPassiveEdgeBatches,
  disposePassiveEdgeBatches,
  setPassiveEdgeBatchOpacity,
} from '../../js/edge-batching.js';


const sceneSource = fs.readFileSync(new URL('../../js/scene.js', import.meta.url), 'utf8');


function canonicalCurveRecords() {
  return EDGES.map((edge, index) => ({
    edge,
    curve: new THREE.QuadraticBezierCurve3(
      new THREE.Vector3(index, 0, 0),
      new THREE.Vector3(index + 0.45, 0.5, 0.2),
      new THREE.Vector3(index + 1, 0.1, 0.4),
    ),
  }));
}


test('canonical graph has three populated groups inside the four-group capacity', () => {
  const { batches, groupCounts } = buildPassiveEdgeBatches(THREE, canonicalCurveRecords());
  assert.deepEqual(PASSIVE_EDGE_GROUP_KEYS, [
    'positive|certain',
    'positive|contested',
    'negative|certain',
    'negative|contested',
  ]);
  assert.deepEqual(Object.fromEntries(groupCounts), {
    'positive|certain': 74,
    'positive|contested': 2,
    'negative|certain': 31,
    'negative|contested': 0,
  });
  assert.equal(batches.size, 3);
  assert.equal([...groupCounts.values()].reduce((sum, count) => sum + count, 0), 107);
  disposePassiveEdgeBatches(batches);
});


test('each edge contributes 40 disconnected line-segment pairs', () => {
  const { batches, groupCounts } = buildPassiveEdgeBatches(THREE, canonicalCurveRecords());
  for (const [key, line] of batches) {
    const expectedVertices = groupCounts.get(key) * PASSIVE_EDGE_SEGMENTS * 2;
    assert.equal(line.geometry.getAttribute('position').count, expectedVertices, key);
    assert.equal(line.geometry.getAttribute('color').count, expectedVertices, key);
    if (key.endsWith('|contested')) {
      assert.equal(line.geometry.getAttribute('lineDistance').count, expectedVertices, key);
    } else {
      assert.equal(line.geometry.getAttribute('lineDistance'), undefined, key);
    }
  }
  disposePassiveEdgeBatches(batches);
});


test('contested dash distance accumulates across short pairs and resets only between edges', () => {
  const records = [0, 1].map((offset) => ({
    edge: { sign: 1, confidence: 1, strength: 2 },
    curve: new THREE.LineCurve3(
      new THREE.Vector3(0, offset, 0),
      new THREE.Vector3(8, offset, 0),
    ),
  }));
  const { batches } = buildPassiveEdgeBatches(THREE, records);
  const line = batches.get('positive|contested');
  const distances = line.geometry.getAttribute('lineDistance');
  const verticesPerEdge = PASSIVE_EDGE_SEGMENTS * 2;
  const period = line.material.dashSize + line.material.gapSize;

  for (let edgeIndex = 0; edgeIndex < records.length; edgeIndex++) {
    const start = edgeIndex * verticesPerEdge;
    assert.equal(distances.getX(start), 0);
    let previousEnd = 0;
    let reachesGap = false;
    for (let segment = 0; segment < PASSIVE_EDGE_SEGMENTS; segment++) {
      const from = distances.getX(start + segment * 2);
      const to = distances.getX(start + segment * 2 + 1);
      assert.ok(Math.abs(from - previousEnd) < 1e-6);
      assert.ok(to > from);
      assert.ok(to - from < line.material.dashSize);
      reachesGap ||= to % period > line.material.dashSize;
      previousEnd = to;
    }
    assert.ok(previousEnd > period);
    assert.equal(reachesGap, true);
  }
  disposePassiveEdgeBatches(batches);
});


test('strength colors preserve the old effective alpha ladder', () => {
  const records = [1, 2, 3].map((strength, index) => ({
    edge: { sign: 1, confidence: 3, strength },
    curve: new THREE.LineCurve3(
      new THREE.Vector3(index, 0, 0),
      new THREE.Vector3(index + 1, 0, 0),
    ),
  }));
  const { batches } = buildPassiveEdgeBatches(THREE, records);
  const colors = batches.get('positive|certain').geometry.getAttribute('color');
  const stride = PASSIVE_EDGE_SEGMENTS * 2;
  const magnitudes = [0, 1, 2].map((edgeIndex) => {
    const offset = edgeIndex * stride;
    return Math.hypot(colors.getX(offset), colors.getY(offset), colors.getZ(offset));
  });
  assert.ok(magnitudes[0] < magnitudes[1]);
  assert.ok(magnitudes[1] < magnitudes[2]);
  const effectiveAlpha = [1, 2, 3].map((strength) => (
    PASSIVE_EDGE_BASE_OPACITY * (0.3 + strength * 0.2)
  ));
  for (const [index, expected] of [0.17, 0.238, 0.306].entries()) {
    assert.ok(Math.abs(effectiveAlpha[index] - expected) < 1e-12);
  }
  disposePassiveEdgeBatches(batches);
});


test('highlight opacity transitions and disposal apply to every populated batch', () => {
  const { batches } = buildPassiveEdgeBatches(THREE, canonicalCurveRecords());
  setPassiveEdgeBatchOpacity(batches, PASSIVE_EDGE_HIGHLIGHT_OPACITY);
  for (const line of batches.values()) {
    assert.equal(line.material.opacity, PASSIVE_EDGE_HIGHLIGHT_OPACITY);
  }
  setPassiveEdgeBatchOpacity(batches, PASSIVE_EDGE_BASE_OPACITY);
  const disposed = [];
  for (const [key, line] of batches) {
    line.geometry.addEventListener('dispose', () => disposed.push(`${key}:geometry`));
    line.material.addEventListener('dispose', () => disposed.push(`${key}:material`));
  }
  disposePassiveEdgeBatches(batches);
  assert.equal(disposed.length, batches.size * 2);
});


test('scene integrates populated-batch diagnostics and preserves edge highlights', () => {
  assert.match(sceneSource, /buildPassiveEdgeBatches\s*\(/);
  assert.match(sceneSource, /passiveEdgeBatchCapacity:\s*PASSIVE_EDGE_GROUP_KEYS\.length/);
  assert.match(sceneSource, /passiveEdgeBatchCount:\s*passiveEdgeBatches\.size/);
  assert.match(sceneSource, /passiveEdgeCount:\s*edgeVis\.size/);
  assert.match(sceneSource, /setPassiveEdgeBatchOpacity\s*\(/);
  assert.match(sceneSource, /new THREE\.TubeGeometry\s*\(\s*ev\.curve/);
  assert.match(sceneSource, /new THREE\.ConeGeometry/);
  assert.doesNotMatch(sceneSource, /edgeVis\.set[^\n]+\bline\b/);
});
