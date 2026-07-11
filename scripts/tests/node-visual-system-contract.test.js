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

test('defines the stable node visual system API and synchronous fallback hierarchy', () => {
  assert.match(visualSource, /export function createNodeVisualSystem\s*\(/);
  assert.match(visualSource, /graph\.nodes/);
  assert.match(visualSource, /new THREE\.SphereGeometry\s*\(/);

  for (const field of [
    'nodeRoot', 'modelRoot', 'fallbackRoot', 'bodyMeshes', 'accentRoot',
    'selectionRing', 'pressureRing', 'leverRing', 'hitProxy', 'labelAnchor',
    'chip', 'categoryColor', 'hubMetric', 'modelStatus', 'motionState',
  ]) {
    assert.match(visualSource, new RegExp(`\\b${field}\\b`), `missing node record field: ${field}`);
  }

  for (const method of [
    'pickTargets', 'loadLibrary', 'setHoveredId', 'setHighlight',
    'clearHighlight', 'setPressures', 'pulseArrival', 'setLang',
    'setLabelTitles', 'setLabelValues', 'update', 'getDiagnostics', 'dispose',
  ]) {
    assert.match(visualSource, new RegExp(`\\b${method}\\b`), `missing public API member: ${method}`);
  }
});

test('configures the approved PBR color, environment, light, shadow, and DPR policy', () => {
  assert.match(sceneSource, /RoomEnvironment/);
  assert.match(sceneSource, /renderer\.outputColorSpace\s*=\s*THREE\.SRGBColorSpace/);
  assert.match(sceneSource, /renderer\.toneMapping\s*=\s*THREE\.ACESFilmicToneMapping/);
  assert.match(sceneSource, /renderer\.toneMappingExposure\s*=\s*0\.95/);
  assert.match(sceneSource, /new THREE\.PMREMGenerator\s*\(/);
  assert.match(sceneSource, /scene\.environment\s*=/);
  assert.ok(
    (sceneSource.match(/new THREE\.DirectionalLight\s*\(/g) || []).length >= 2,
    'expected a directional key light and a directional rim light',
  );
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

test('keeps GLB loading fail-soft with a policy-rate-only vertical slice', () => {
  assert.match(visualSource, /async function loadLibrary\s*\(/);
  assert.match(visualSource, /try\s*{/);
  assert.match(visualSource, /catch\s*\(/);
  assert.match(visualSource, /console\.warn\s*\(/);
  assert.match(visualSource, /policy_rate/);
  assert.match(visualSource, /loadedIds/);
  assert.match(visualSource, /fallbackIds/);
  assert.match(visualSource, /issues/);
  assert.match(visualSource, /VERTICAL_SLICE_MODEL_IDS/);
  assert.match(
    visualSource,
    /contract\.missing\.filter\s*\(\s*\(id\)\s*=>\s*VERTICAL_SLICE_MODEL_IDS\.has\s*\(id\)\s*\)/,
  );
  assert.doesNotMatch(visualSource, /showFatal|unhandledrejection/);
});
