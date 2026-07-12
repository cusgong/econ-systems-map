import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

function source(relativePath) {
  const url = new URL(relativePath, import.meta.url);
  return existsSync(url) ? readFileSync(url, 'utf8') : '';
}

const visualSource = source('../../js/node-visual-system.js');
const sceneSource = source('../../js/scene.js');
const mainSource = source('../../js/main.js');

test('boot computes hub metrics once and shares the same map with scene and UI', () => {
  assert.match(mainSource, /import\s*{\s*computeHubMetrics\s*}\s*from\s*['"]\.\/hub-metrics\.js['"]/);
  assert.equal(
    (mainSource.match(/\bcomputeHubMetrics\s*\(/g) || []).length,
    1,
    'boot must compute hub metrics exactly once',
  );
  assert.match(mainSource, /const\s+hubMetrics\s*=\s*computeHubMetrics\s*\(\s*graph\s*\)/);
  assert.match(mainSource, /createScene\s*\(\s*{[\s\S]*?\bhubMetrics\s*,[\s\S]*?}\s*\)/);
  assert.match(mainSource, /createUI\s*\(\s*{[\s\S]*?\bhubMetrics\s*,[\s\S]*?}\s*\)/);
  assert.match(sceneSource, /hubMetrics:\s*opts\.hubMetrics/);
});

test('scene exposes pressure as the primary API and keeps setNodeTints as an alias', () => {
  assert.match(sceneSource, /function\s+setPressures\s*\(\s*map\s*\)\s*{\s*visualSystem\.setPressures\s*\(\s*map\s*\)\s*;?\s*}/);
  assert.match(sceneSource, /function\s+setNodeTints\s*\(\s*map\s*\)\s*{\s*setPressures\s*\(\s*map\s*\)\s*;?\s*}/);
  assert.match(sceneSource, /setHighlight,\s*clearHighlight,\s*setPressures,\s*setNodeTints/);
});

test('scene keeps node motion event-driven and lever drag owns nodeRoot Y', () => {
  assert.match(sceneSource, /controls\.autoRotate\s*=\s*false/);
  assert.doesNotMatch(sceneSource, /controls\.autoRotate\s*=\s*!reducedMotion/);
  const nodeRootYWrites = sceneSource.match(/runtime\.nodeRoot\.position\.y\s*=/g) || [];
  assert.equal(nodeRootYWrites.length, 3, 'pointer drag start/end/cancel are the only nodeRoot Y writers');
  assert.match(sceneSource, /visualSystem\.pulseArrival\s*\(\s*p\.toId\s*,\s*p\.sign\s*\)/);
});

test('defines the stable node visual system API and synchronous fallback hierarchy', () => {
  assert.match(visualSource, /export function createNodeVisualSystem\s*\(/);
  assert.match(visualSource, /graph\.nodes/);
  assert.match(visualSource, /new THREE\.SphereGeometry\s*\(/);

  for (const field of [
    'nodeRoot', 'modelRoot', 'fallbackRoot', 'bodyMeshes', 'accentRoot',
    'selectionRing', 'pressureRing', 'arrivalRing', 'leverRing', 'hitProxy', 'labelAnchor',
    'chip', 'categoryColor', 'hubMetric', 'modelStatus', 'motionState',
  ]) {
    assert.match(visualSource, new RegExp(`\\b${field}\\b`), `missing node record field: ${field}`);
  }

  for (const method of [
    'pickTargets', 'loadLibrary', 'setHoveredId', 'setHighlight',
    'clearHighlight', 'setPressures', 'pulseArrival', 'setLang',
    'setLabelTitles', 'setLabelValues', 'update', 'getDiagnostics',
    'getNodeModelStatus', 'dispose',
  ]) {
    assert.match(visualSource, new RegExp(`\\b${method}\\b`), `missing public API member: ${method}`);
  }
});

test('configures the approved PBR color, environment, light, shadow, and DPR policy', () => {
  assert.match(sceneSource, /RoomEnvironment/);
  assert.match(sceneSource, /renderer\.outputColorSpace\s*=\s*THREE\.SRGBColorSpace/);
  assert.match(sceneSource, /renderer\.toneMapping\s*=\s*THREE\.ACESFilmicToneMapping/);
  assert.match(sceneSource, /renderer\.toneMappingExposure\s*=\s*1\.08/);
  assert.match(sceneSource, /new THREE\.PMREMGenerator\s*\(/);
  assert.match(sceneSource, /scene\.environment\s*=/);
  assert.ok(
    (sceneSource.match(/new THREE\.DirectionalLight\s*\(/g) || []).length >= 2,
    'expected a directional key light and a directional rim light',
  );
  assert.match(sceneSource, /new THREE\.HemisphereLight\s*\(\s*0xbfdcff\s*,\s*0x08101f\s*,\s*0\.7\s*\)/);
  assert.match(sceneSource, /new THREE\.DirectionalLight\s*\(\s*0xf2f5ff\s*,\s*1\.45\s*\)/);
  assert.match(sceneSource, /new THREE\.DirectionalLight\s*\(\s*0x7298d8\s*,\s*0\.9\s*\)/);
  assert.match(sceneSource, /position\.set\s*\(\s*24\s*,\s*36\s*,\s*18\s*\)/);
  assert.match(sceneSource, /position\.set\s*\(\s*-24\s*,\s*16\s*,\s*-18\s*\)/);
  assert.match(sceneSource, /shadowMap\.enabled\s*=\s*false/);
  assert.match(sceneSource, /matchMedia\s*\(\s*['"]\(pointer: coarse\)['"]\s*\)/);
  assert.match(sceneSource, /mobile\s*\?\s*1\.5\s*:\s*2/);
});

test('supports the sphere kill switch and exposes the model loading lifecycle', () => {
  const runtimeSource = `${mainSource}\n${sceneSource}\n${visualSource}`;

  assert.match(runtimeSource, /new URLSearchParams\s*\(\s*window\.location\.search\s*\)/);
  assert.match(runtimeSource, /\.get\s*\(\s*['"]nodes['"]\s*\)\s*===\s*['"]sphere['"]/);
  assert.match(runtimeSource, /new URL\s*\(\s*['"]\.\.\/data\/models\/econ-node-library\.glb['"]\s*,\s*import\.meta\.url\s*\)/);
  assert.match(runtimeSource, /nodeLibraryUrl/);
  assert.match(runtimeSource, /dataset\.nodeModels/);
  for (const status of ['loading', 'partial', 'ready', 'fallback']) {
    assert.match(runtimeSource, new RegExp(`['"]${status}['"]`), `missing dataset state: ${status}`);
  }
  assert.match(visualSource, /if\s*\(\s*!url\s*\)/);
});

test('keeps full 30-model GLB loading fail-soft without hiding missing instruments', () => {
  assert.match(visualSource, /async function loadLibrary\s*\(/);
  assert.match(visualSource, /try\s*{/);
  assert.match(visualSource, /catch\s*\(/);
  assert.match(visualSource, /console\.warn\s*\(/);
  assert.match(visualSource, /loadedIds/);
  assert.match(visualSource, /fallbackIds/);
  assert.match(visualSource, /issues/);
  assert.match(visualSource, /const missing\s*=\s*contract\.missing\s*;/);
  assert.doesNotMatch(visualSource, /VERTICAL_SLICE_MODEL_IDS/);
  assert.doesNotMatch(visualSource, /showFatal|unhandledrejection/);
});

test('integrates signature dispatch with a complete resettable accent transform', () => {
  assert.match(visualSource, /from ['"]\.\/node-motion\.js['"]/);
  assert.match(visualSource, /evaluateSignatureTransform\s*\(/);
  assert.match(visualSource, /econ_signature/);
  assert.match(visualSource, /accentBasePosition/);
  assert.match(visualSource, /accentBaseQuaternion/);
  assert.match(visualSource, /accentBaseScale/);
  assert.match(visualSource, /accent\.position\.fromArray\s*\(/);
  assert.match(visualSource, /accent\.quaternion\.fromArray\s*\(/);
  assert.match(visualSource, /accent\.scale\.fromArray\s*\(/);
  assert.match(
    visualSource,
    /record\.accentRoot\.position\.copy\s*\(\s*record\.motionState\.accentBasePosition\s*\)/,
    'reduced motion must restore accent position as well as quaternion and scale',
  );
});

test('integrates projection-aware label layout without changing the public API', () => {
  assert.match(visualSource, /from ['"]\.\/node-label-layout\.js['"]/);
  assert.match(visualSource, /layoutNodeLabels\s*\(/);
  assert.match(visualSource, /getWorldPosition\s*\([^)]*\)\.project\s*\(\s*camera\s*\)/);
  assert.match(visualSource, /querySelector\s*\(\s*['"]\.hud-top['"]\s*\)/);
  assert.match(visualSource, /getElementById\s*\(\s*['"]panel['"]\s*\)/);
  assert.match(visualSource, /classList\.contains\s*\(\s*['"]selected['"]\s*\)/);
  assert.match(visualSource, /classList\.contains\s*\(\s*['"]hl['"]\s*\)/);
  assert.match(visualSource, /querySelector\s*\(\s*['"]\.lval['"]\s*\)/);
  assert.match(visualSource, /style\.visibility\s*=/);
  assert.match(visualSource, /node-label-leader/);
  assert.match(visualSource, /dataset\.nodeScreenX\s*=/);
  assert.match(visualSource, /dataset\.nodeScreenY\s*=/);
  assert.match(visualSource, /chip\.dataset\.nodeId\s*=\s*node\.id/);
  assert.match(visualSource, /anchorOccluded/);
  assert.match(visualSource, /nodeCenterObstacles/);
  assert.match(visualSource, /allowDistantFallback:\s*selected/);
  assert.match(visualSource, /LABEL_SELECTED_ASSOCIATION_CAP\s*=\s*160/);
  assert.match(visualSource, /LABEL_SELECTED_LEADER_THRESHOLD\s*=\s*0\s*;/);
  assert.match(visualSource, /maxDisplacement:\s*selected\s*\?\s*LABEL_SELECTED_ASSOCIATION_CAP/);
  assert.doesNotMatch(visualSource, /maxDisplacement:\s*selected\s*\?\s*Infinity/);
  assert.match(visualSource, /leaderThreshold:\s*selected/);
  assert.match(visualSource, /placement\.showLeader/);
  assert.match(visualSource, /getElementById\s*\(\s*['"]legend['"]\s*\)/);
  assert.match(visualSource, /getElementById\s*\(\s*['"]statusline['"]\s*\)/);
});
