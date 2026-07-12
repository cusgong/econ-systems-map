// Passive causal-edge batching. This module receives the active Three.js
// namespace so the same implementation can run through the browser import map
// and the vendored r170 Node regression tests.

export const PASSIVE_EDGE_GROUP_KEYS = Object.freeze([
  'positive|certain',
  'positive|contested',
  'negative|certain',
  'negative|contested',
]);
export const PASSIVE_EDGE_SEGMENTS = 40;
export const PASSIVE_EDGE_BASE_OPACITY = 0.34;
export const PASSIVE_EDGE_HIGHLIGHT_OPACITY = 0.055;


function groupKeyFor(edge) {
  const sign = edge.sign > 0 ? 'positive' : 'negative';
  const confidence = edge.confidence === 1 ? 'contested' : 'certain';
  return `${sign}|${confidence}`;
}


export function buildPassiveEdgeBatches(THREE, records) {
  const buffers = new Map(PASSIVE_EDGE_GROUP_KEYS.map((key) => [key, {
    positions: [],
    colors: [],
    lineDistances: [],
  }]));
  const groupCounts = new Map(PASSIVE_EDGE_GROUP_KEYS.map((key) => [key, 0]));
  const positive = new THREE.Color('#2fb9d8');
  const negative = new THREE.Color('#ff8a55');

  for (const { edge, curve } of records) {
    const key = groupKeyFor(edge);
    const group = buffers.get(key);
    const points = curve.getPoints(PASSIVE_EDGE_SEGMENTS);
    const contested = key.endsWith('|contested');
    let lineDistance = 0;
    const strength = Math.max(1, Math.min(3, Number(edge.strength) || 1));
    const strengthColor = (edge.sign > 0 ? positive : negative)
      .clone()
      .multiplyScalar(0.3 + strength * 0.2);
    groupCounts.set(key, groupCounts.get(key) + 1);
    for (let index = 0; index < PASSIVE_EDGE_SEGMENTS; index++) {
      group.positions.push(points[index].x, points[index].y, points[index].z);
      group.positions.push(points[index + 1].x, points[index + 1].y, points[index + 1].z);
      group.colors.push(strengthColor.r, strengthColor.g, strengthColor.b);
      group.colors.push(strengthColor.r, strengthColor.g, strengthColor.b);
      if (contested) {
        const nextDistance = lineDistance + points[index].distanceTo(points[index + 1]);
        group.lineDistances.push(lineDistance, nextDistance);
        lineDistance = nextDistance;
      }
    }
  }

  const batches = new Map();
  for (const key of PASSIVE_EDGE_GROUP_KEYS) {
    const group = buffers.get(key);
    if (!group.positions.length) continue;
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(group.positions, 3));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(group.colors, 3));
    const contested = key.endsWith('|contested');
    if (contested) {
      geometry.setAttribute(
        'lineDistance',
        new THREE.Float32BufferAttribute(group.lineDistances, 1),
      );
    }
    const common = {
      vertexColors: true,
      transparent: true,
      opacity: PASSIVE_EDGE_BASE_OPACITY,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    };
    const material = contested
      ? new THREE.LineDashedMaterial({ ...common, dashSize: 1.7, gapSize: 1.2 })
      : new THREE.LineBasicMaterial(common);
    const line = new THREE.LineSegments(geometry, material);
    line.name = `passive_edges__${key.replace('|', '__')}`;
    line.userData.edgeCount = groupCounts.get(key);
    batches.set(key, line);
  }
  return { batches, groupCounts };
}


export function setPassiveEdgeBatchOpacity(batches, opacity) {
  for (const line of batches.values()) line.material.opacity = opacity;
}


export function disposePassiveEdgeBatches(batches) {
  for (const line of batches.values()) {
    line.geometry.dispose();
    line.material.dispose();
  }
}
