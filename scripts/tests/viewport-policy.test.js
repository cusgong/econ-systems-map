import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const moduleUrl = new URL('../../js/viewport-policy.js', import.meta.url);

async function loadPolicy() {
  assert.ok(existsSync(fileURLToPath(moduleUrl)), 'viewport-policy.js must exist');
  return import(moduleUrl.href);
}

function source(relativePath) {
  return readFileSync(new URL(relativePath, import.meta.url), 'utf8');
}

test('every variable selection frames the selected instrument for inspection', async () => {
  const { focusIdsForViewport, minimumFocusDistance } = await loadPolicy();
  const rippleIds = ['policy_rate', 'market_rate', 'liquidity'];

  assert.deepEqual(focusIdsForViewport('policy_rate', rippleIds, 390), ['policy_rate']);
  assert.deepEqual(focusIdsForViewport('policy_rate', rippleIds, 900), ['policy_rate']);
  assert.deepEqual(focusIdsForViewport('policy_rate', rippleIds, 1365), ['policy_rate']);
  assert.equal(minimumFocusDistance(1), 40);
  assert.equal(minimumFocusDistance(2), 36);
});

test('label opacity keeps selected and causal context readable at distance', async () => {
  const { labelOpacityForState } = await loadPolicy();
  assert.equal(typeof labelOpacityForState, 'function');
  assert.equal(labelOpacityForState(180, { selected: true }), 1);
  assert.ok(labelOpacityForState(180, { highlighted: true }) >= 0.92);
  assert.ok(labelOpacityForState(180, { dimmed: true }) >= 0.35);
  assert.ok(labelOpacityForState(260, {}) >= 0.35);
});

test('map viewport is reserved only for an expanded narrow-screen panel', async () => {
  const { shouldReserveMapViewport } = await loadPolicy();

  assert.equal(shouldReserveMapViewport(824, false), true);
  assert.equal(shouldReserveMapViewport(390, true), false);
  assert.equal(shouldReserveMapViewport(901, false), false);
});

test('UI, CSS, and scene integrate the safe viewport policy', () => {
  const ui = source('../../js/ui.js');
  const scene = source('../../js/scene.js');
  const css = source('../../css/main.css');

  assert.match(ui, /from ['"]\.\/viewport-policy\.js['"]/);
  assert.match(ui, /classList\.toggle\(\s*['"]map-viewport-reserved['"]/);
  assert.match(ui, /focusIdsForViewport\s*\(/);
  assert.match(scene, /new ResizeObserver\s*\(/);
  assert.match(scene, /minimumFocusDistance\s*\(/);
  assert.match(scene, /observe\s*\(\s*container\s*\)/);
  assert.match(scene, /disconnect\s*\(\s*\)/);
  assert.match(css, /:root\.map-viewport-reserved\s+#stage/);
  assert.match(css, /:root\.map-viewport-reserved\s+#labels/);
  assert.match(css, /--mobile-panel-reserve/);
  assert.match(css, /\.node-label\.selected\s*{[^}]*border-width:\s*2px/s);
});
