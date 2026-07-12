import test from 'node:test';
import assert from 'node:assert/strict';
import { registerHooks } from 'node:module';

const threeUrl = new URL('../../vendor/three.module.min.js', import.meta.url).href;
const addonsUrl = new URL('../../vendor/addons/', import.meta.url);

registerHooks({
  resolve(specifier, context, nextResolve) {
    if (specifier === 'three') return { url: threeUrl, shortCircuit: true };
    if (specifier.startsWith('three/addons/')) {
      return {
        url: new URL(specifier.slice('three/addons/'.length), addonsUrl).href,
        shortCircuit: true,
      };
    }
    return nextResolve(specifier, context);
  },
});

class FakeClassList {
  constructor() {
    this.values = new Set();
  }

  setFromString(value) {
    this.values = new Set(String(value).split(/\s+/).filter(Boolean));
  }

  add(...tokens) {
    for (const token of tokens) this.values.add(token);
  }

  remove(...tokens) {
    for (const token of tokens) this.values.delete(token);
  }

  contains(token) {
    return this.values.has(token);
  }

  toggle(token, force) {
    const next = force === undefined ? !this.contains(token) : !!force;
    if (next) this.add(token);
    else this.remove(token);
    return next;
  }
}

class FakeElement {
  constructor(ownerDocument, tagName = 'div') {
    this.ownerDocument = ownerDocument;
    this.tagName = tagName.toUpperCase();
    this.style = {};
    this.dataset = {};
    this.classList = new FakeClassList();
    this.children = [];
    this.parentNode = null;
    this.hidden = false;
    this.offsetWidth = 96;
    this.offsetHeight = 24;
    this.textContent = '';
    this.attributes = new Map();
  }

  set className(value) {
    this.classList.setFromString(value);
  }

  get className() {
    return [...this.classList.values].join(' ');
  }

  set innerHTML(value) {
    this.children = [];
    for (const match of String(value).matchAll(/class="([^"]+)"/g)) {
      const child = new FakeElement(this.ownerDocument, 'span');
      child.className = match[1];
      this.append(child);
    }
  }

  append(...children) {
    for (const child of children) {
      child.parentNode = this;
      this.children.push(child);
    }
  }

  appendChild(child) {
    this.append(child);
    return child;
  }

  querySelector(selector) {
    if (!selector.startsWith('.')) return null;
    const className = selector.slice(1);
    for (const child of this.children) {
      if (child.classList.contains(className)) return child;
      const nested = child.querySelector(selector);
      if (nested) return nested;
    }
    return null;
  }

  setAttribute(name, value) {
    this.attributes.set(name, String(value));
  }

  addEventListener() {}

  removeEventListener() {}

  getBoundingClientRect() {
    return {
      left: 0,
      top: 0,
      right: this.offsetWidth,
      bottom: this.offsetHeight,
      width: this.offsetWidth,
      height: this.offsetHeight,
    };
  }

  remove() {
    if (!this.parentNode) return;
    this.parentNode.children = this.parentNode.children.filter((child) => child !== this);
    this.parentNode = null;
  }
}

function installFakeDom() {
  const document = {
    documentElement: null,
    createElement(tagName) {
      return new FakeElement(document, tagName);
    },
    querySelector() {
      return null;
    },
    getElementById() {
      return null;
    },
  };
  document.defaultView = { Element: FakeElement };
  document.documentElement = document.createElement('html');
  globalThis.document = document;
  globalThis.window = {
    innerHeight: 844,
    getComputedStyle(element) {
      return {
        display: element.style.display || 'block',
        visibility: element.style.visibility || 'visible',
      };
    },
  };
}

function makeModelRoot(THREE, id, signature) {
  const root = new THREE.Group();
  root.name = id;
  root.userData = {
    econ_id: id,
    econ_ready: true,
    econ_signature: signature,
    econ_axis: 'x',
    econ_amount: 0.4,
    econ_duration: 0.4,
  };

  const bodyMaterial = new THREE.MeshStandardMaterial({ color: '#ffffff' });
  bodyMaterial.name = 'MAT__DARK_TITANIUM';
  const body = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.8, 0.7), bodyMaterial);
  body.name = `${id}__body`;
  body.userData.econ_role = 'body';

  const accentMaterial = new THREE.MeshStandardMaterial({ color: '#ffffff' });
  accentMaterial.name = 'MAT__CATEGORY_ACCENT';
  const accent = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.3, 0.3), accentMaterial);
  accent.name = `${id}__accent`;
  accent.position.set(0.16, 0.12, 0.2);
  accent.userData.econ_role = 'accent';

  root.add(body, accent);
  return root;
}

function assertClose(actual, expected, epsilon = 1e-6) {
  assert.ok(
    Math.abs(actual - expected) <= epsilon,
    `expected ${actual} to be within ${epsilon} of ${expected}`,
  );
}

function nodeChip(scene, id) {
  return scene
    .getObjectByName(`${id}__label_anchor`)
    ?.children[0]
    ?.element
    ?.querySelector('.node-label');
}

test('hub sizing clamps to the approved range and drives fallback, labels, and hit proxies', async (t) => {
  installFakeDom();
  const THREE = await import('three');
  const { createNodeVisualSystem } = await import('../../js/node-visual-system.js');
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(55, 390 / 844, 0.1, 600);
  camera.position.set(0, 0, 200);
  const canvas = document.createElement('canvas');
  canvas.clientWidth = 390;
  canvas.clientHeight = 844;
  canvas.offsetWidth = 390;
  canvas.offsetHeight = 844;
  const renderer = { domElement: canvas, info: { render: { calls: 7, triangles: 321 } } };
  const nodes = [
    { id: 'low', cat: 'policy', name: { ko: '낮음', en: 'Low' }, pos: new THREE.Vector3(-4, 2, 0) },
    { id: 'mid', cat: 'policy', name: { ko: '중간', en: 'Medium' }, pos: new THREE.Vector3(0, 2, 0) },
    { id: 'high', cat: 'policy', name: { ko: '높음', en: 'High' }, pos: new THREE.Vector3(4, 2, 0) },
  ];
  const hubMetrics = new Map([
    ['low', { score100: 0, radiusScale: 0.2 }],
    ['mid', { score100: 50, radiusScale: 1.074895 }],
    ['high', { score100: 100, radiusScale: 2 }],
  ]);
  const visual = createNodeVisualSystem({
    scene,
    camera,
    renderer,
    graph: { nodes },
    categories: [{ id: 'policy', color: '#66aaff' }],
    hubMetrics,
  });
  t.after(() => visual.dispose());

  visual.update(1);
  for (const node of nodes) {
    const root = scene.getObjectByName(`${node.id}__node_root`);
    const distance = camera.position.distanceTo(root.position);
    const worldPerPixel = (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2) * distance) / 844;
    const hubScale = Math.max(0.82, Math.min(1.28, hubMetrics.get(node.id).radiusScale));
    const semanticRadius = 1.82 * hubScale;
    const radius = Math.max(1.82, worldPerPixel * 17) * hubScale;
    assert.deepEqual(root.position.toArray(), node.pos.toArray(), 'semantic position must not move');
    assertClose(scene.getObjectByName(`${node.id}__model_root`).scale.x, radius);
    assertClose(scene.getObjectByName(`${node.id}__fallback_root`).scale.x, radius);
    assertClose(scene.getObjectByName(`${node.id}__selection_ring`).scale.x, radius);
    assertClose(scene.getObjectByName(`${node.id}__label_anchor`).position.y, radius + 0.62);

    const hitRadius = scene.getObjectByName(`${node.id}__hit_proxy`).scale.x;
    assert.ok((hitRadius / worldPerPixel) * 2 >= 44 - 1e-6);
    const chip = nodeChip(scene, node.id);
    assert.equal(chip.dataset.hubScore, String(hubMetrics.get(node.id).score100));
    assert.equal(chip.dataset.radiusScale, String(hubScale));
    assert.ok(Number(chip.dataset.hitRadiusPx) >= 22);
    assertClose(Number(chip.dataset.visualRadiusPx), radius / worldPerPixel, 0.02);
    assertClose(Number(chip.dataset.semanticRadiusPx), semanticRadius / worldPerPixel, 0.02);
    assert.ok(Number(chip.dataset.visualRadiusPx) >= 17 * hubScale - 0.02);
  }
  const displayed = nodes.map((node) => scene.getObjectByName(`${node.id}__model_root`).scale.x);
  assert.ok(displayed[0] < displayed[1]);
  assert.ok(displayed[1] < displayed[2]);

  camera.position.set(0, 2, 10);
  visual.setHighlight({ selectedId: 'high', nodeOrders: new Map([['high', 0]]) });
  visual.update(2);
  for (const node of nodes) {
    const hubScale = Math.max(0.82, Math.min(1.28, hubMetrics.get(node.id).radiusScale));
    const maxBaseRadiusPx = node.id === 'high' ? 44 : 26;
    const chip = nodeChip(scene, node.id);
    assert.ok(
      Number(chip.dataset.visualRadiusPx) <= maxBaseRadiusPx * hubScale + 0.02,
      `${node.id} must not overwhelm the selected inspection view`,
    );
  }
});

test('selection and context materials retain readable body and accent contrast', async (t) => {
  installFakeDom();
  const THREE = await import('three');
  const { createNodeVisualSystem } = await import('../../js/node-visual-system.js');
  const scene = new THREE.Scene();
  const nodes = [
    { id: 'policy_rate', cat: 'policy', name: { ko: '기준금리', en: 'Policy rate' } },
    { id: 'fx', cat: 'policy', name: { ko: '환율', en: 'FX' } },
  ];
  const visual = createNodeVisualSystem({
    scene,
    graph: { nodes },
    categories: [{ id: 'policy', color: '#66aaff' }],
  });
  t.after(() => visual.dispose());

  const dimmedBody = scene.getObjectByName('policy_rate__fallback_body').material;
  const dimmedAccent = scene.getObjectByName('policy_rate__fallback_accent').material;
  const selectedBody = scene.getObjectByName('fx__fallback_body').material;
  const selectionRing = scene.getObjectByName('fx__selection_ring');
  const bodyBefore = dimmedBody.color.clone();
  const accentBefore = dimmedAccent.color.clone();

  visual.setHighlight({ selectedId: 'fx', nodeOrders: new Map([['fx', 0]]) });

  assert.ok(dimmedBody.color.r >= bodyBefore.r * 0.55);
  assert.ok(dimmedAccent.color.b >= accentBefore.b * 0.5);
  assert.ok(dimmedAccent.emissiveIntensity >= 0.025);
  assert.ok(selectedBody.emissiveIntensity >= 0.1);
  assert.ok(selectionRing.geometry.parameters.tube >= 0.04);
});

test('loaded models normalize source bounds to radius one before applying hub scale', async (t) => {
  installFakeDom();
  const THREE = await import('three');
  const { createNodeVisualSystem } = await import('../../js/node-visual-system.js');
  const sourceRoot = makeModelRoot(THREE, 'policy_rate', 'rotate');
  sourceRoot.updateWorldMatrix(true, true);
  const sourceRadius = new THREE.Box3()
    .setFromObject(sourceRoot, true)
    .getBoundingSphere(new THREE.Sphere()).radius;
  const library = new THREE.Group();
  library.add(sourceRoot);
  const scene = new THREE.Scene();
  const visual = createNodeVisualSystem({
    scene,
    graph: { nodes: [{ id: 'policy_rate', cat: 'policy', name: { ko: '기준금리', en: 'Policy rate' } }] },
    categories: [{ id: 'policy', color: '#66aaff' }],
    hubMetrics: new Map([['policy_rate', { score100: 100, radiusScale: 1.28 }]]),
    loader: { async loadAsync() { return { scene: library }; } },
  });
  t.after(() => visual.dispose());

  const result = await visual.loadLibrary('/models.glb');
  assert.equal(result.status, 'ready');
  const normalized = scene.getObjectByName('policy_rate__normalized_model');
  const modelRoot = scene.getObjectByName('policy_rate__model_root');
  assertClose(normalized.scale.x, 1 / sourceRadius);
  assertClose(sourceRadius * normalized.scale.x, 1);
  assertClose(sourceRadius * normalized.scale.x * modelRoot.scale.x, 1.82 * 1.28);
});

test('pressure uses a separate ring and never recolors body, accent, or lever category channels', async (t) => {
  installFakeDom();
  const THREE = await import('three');
  const { createNodeVisualSystem } = await import('../../js/node-visual-system.js');
  const scene = new THREE.Scene();
  const visual = createNodeVisualSystem({
    scene,
    graph: {
      nodes: [{ id: 'policy_rate', cat: 'policy', lever: true, name: { ko: '기준금리', en: 'Policy rate' } }],
    },
    categories: [{ id: 'policy', color: '#66aaff' }],
  });
  t.after(() => visual.dispose());
  const body = scene.getObjectByName('policy_rate__fallback_body');
  const accent = scene.getObjectByName('policy_rate__fallback_accent');
  const lever = scene.getObjectByName('policy_rate__lever_ring');
  const pressure = scene.getObjectByName('policy_rate__pressure_ring');
  const categoryHex = accent.material.color.getHexString();
  const bodyHex = body.material.color.getHexString();
  const leverHex = lever.material.color.getHexString();

  visual.setPressures(new Map([['policy_rate', 0.35]]));
  const weakScale = pressure.scale.x;
  assert.equal(pressure.material.color.getHexString(), 'ffb36b');
  assert.equal(nodeChip(scene, 'policy_rate').querySelector('.tint').textContent, '▲');

  visual.setPressures(new Map([['policy_rate', -0.9]]));
  assert.equal(pressure.material.color.getHexString(), '6fb5ff');
  assert.ok(pressure.scale.x > weakScale, 'pressure magnitude must increase ring scale/thickness');
  assert.equal(nodeChip(scene, 'policy_rate').querySelector('.tint').textContent, '▼');
  assert.equal(nodeChip(scene, 'policy_rate').dataset.pressure, '-0.900');
  assert.equal(body.material.color.getHexString(), bodyHex);
  assert.equal(accent.material.color.getHexString(), categoryHex);
  assert.equal(lever.material.color.getHexString(), leverHex);
  assert.equal(body.material.transparent, false);
  assert.equal(accent.material.transparent, false);
});

test('diagnostics expose only settled public states and per-node fallback status', async (t) => {
  installFakeDom();
  const THREE = await import('three');
  const { createNodeVisualSystem } = await import('../../js/node-visual-system.js');
  let resolveLoad;
  const statuses = [];
  const scene = new THREE.Scene();
  const visual = createNodeVisualSystem({
    scene,
    renderer: { info: { render: { calls: 5, triangles: 144 } } },
    graph: { nodes: [{ id: 'policy_rate', cat: 'policy', name: { ko: '기준금리', en: 'Policy rate' } }] },
    categories: [{ id: 'policy', color: '#66aaff' }],
    loader: {
      loadAsync() {
        return new Promise((resolve) => { resolveLoad = resolve; });
      },
    },
    onModelStatusChange(status) { statuses.push(status); },
  });
  t.after(() => visual.dispose());

  const loading = visual.loadLibrary('/delayed-model.glb');
  assert.equal(visual.getDiagnostics().modelStatus, 'fallback');
  assert.equal(visual.getNodeModelStatus('policy_rate'), null);
  const library = new THREE.Group();
  library.add(makeModelRoot(THREE, 'policy_rate', 'rotate'));
  resolveLoad({ scene: library });
  await loading;

  assert.deepEqual(statuses, ['ready']);
  assert.equal(visual.getNodeModelStatus('policy_rate'), 'ready');
  assert.equal(nodeChip(scene, 'policy_rate').dataset.modelStatus, 'ready');
  assert.deepEqual(
    Object.fromEntries(Object.entries(visual.getDiagnostics()).filter(([key]) => (
      ['modelStatus', 'loadedModelCount', 'fallbackCount', 'calls', 'triangles'].includes(key)
    ))),
    { modelStatus: 'ready', loadedModelCount: 1, fallbackCount: 0, calls: 5, triangles: 144 },
  );
});

test('hover reaches its instrument tilt in about 120ms without exceeding two degrees', async (t) => {
  installFakeDom();
  const THREE = await import('three');
  const { createNodeVisualSystem } = await import('../../js/node-visual-system.js');
  const scene = new THREE.Scene();
  const visual = createNodeVisualSystem({
    scene,
    graph: { nodes: [{ id: 'policy_rate', cat: 'policy', name: { ko: '기준금리', en: 'Policy rate' } }] },
    categories: [{ id: 'policy', color: '#66aaff' }],
  });
  t.after(() => visual.dispose());
  const modelRoot = scene.getObjectByName('policy_rate__model_root');
  const fallbackRoot = scene.getObjectByName('policy_rate__fallback_root');

  visual.update(0);
  visual.setHoveredId('policy_rate');
  for (const elapsed of [0.04, 0.08, 0.12]) visual.update(elapsed);
  const tiltAt120 = THREE.MathUtils.radToDeg(Math.hypot(modelRoot.rotation.x, modelRoot.rotation.y));
  assert.ok(tiltAt120 >= 1.5, `expected a legible tilt by 120ms, received ${tiltAt120} degrees`);
  for (let elapsed = 0.16; elapsed <= 1; elapsed += 0.04) visual.update(elapsed);
  const settledTilt = THREE.MathUtils.radToDeg(Math.hypot(modelRoot.rotation.x, modelRoot.rotation.y));
  assert.ok(settledTilt <= 2, `hover tilt exceeded two degrees: ${settledTilt}`);
  assertClose(fallbackRoot.rotation.x, modelRoot.rotation.x);
  assertClose(fallbackRoot.rotation.y, modelRoot.rotation.y);
});

test('selection signature honors exported transform and clamps duration to 220-320ms', async (t) => {
  installFakeDom();
  const THREE = await import('three');
  const { createNodeVisualSystem } = await import('../../js/node-visual-system.js');
  const sourceRoot = makeModelRoot(THREE, 'policy_rate', 'rotate');
  sourceRoot.userData.econ_axis = 'x';
  sourceRoot.userData.econ_amount = 0.4;
  sourceRoot.userData.econ_duration = 0.8;
  const library = new THREE.Group();
  library.add(sourceRoot);
  const scene = new THREE.Scene();
  const visual = createNodeVisualSystem({
    scene,
    graph: { nodes: [{ id: 'policy_rate', cat: 'policy', name: { ko: '기준금리', en: 'Policy rate' } }] },
    categories: [{ id: 'policy', color: '#66aaff' }],
    loader: { async loadAsync() { return { scene: library }; } },
  });
  t.after(() => visual.dispose());
  await visual.loadLibrary('/models.glb');
  const accent = scene.getObjectByName('policy_rate__accent');
  const baseQuaternion = accent.quaternion.clone();

  visual.update(1);
  visual.setHighlight({ selectedId: 'policy_rate', nodeOrders: new Map([['policy_rate', 0]]) });
  visual.update(1.16);
  assert.ok(baseQuaternion.angleTo(accent.quaternion) > 0.1, 'exported rotate signature must run');
  visual.update(1.321);
  assert.ok(baseQuaternion.angleTo(accent.quaternion) <= 1e-6, 'signature must end by 320ms');
});

test('arrival animates the accent and a sign-colored ring, then reduced motion restores baselines', async (t) => {
  installFakeDom();
  const THREE = await import('three');
  const { createNodeVisualSystem } = await import('../../js/node-visual-system.js');
  const scene = new THREE.Scene();
  const visual = createNodeVisualSystem({
    scene,
    graph: { nodes: [{ id: 'policy_rate', cat: 'policy', name: { ko: '기준금리', en: 'Policy rate' } }] },
    categories: [{ id: 'policy', color: '#66aaff' }],
  });
  t.after(() => visual.dispose());
  const accent = scene.getObjectByName('policy_rate__fallback_accent');
  const ring = scene.getObjectByName('policy_rate__arrival_ring');
  const baseScale = accent.scale.clone();

  visual.update(2);
  visual.pulseArrival('policy_rate', -1);
  visual.update(2.1);
  assert.equal(ring.visible, true);
  assert.equal(ring.material.color.getHexString(), '6fb5ff');
  assert.ok(ring.scale.x > 1.82);
  assert.ok(accent.scale.x > baseScale.x * 1.07);

  visual.setHoveredId('policy_rate');
  visual.setHighlight({ selectedId: 'policy_rate', nodeOrders: new Map([['policy_rate', 0]]) });
  visual.update(2.12);
  visual.setReducedMotion(true);
  assert.deepEqual(scene.getObjectByName('policy_rate__model_root').rotation.toArray(), [0, 0, 0, 'XYZ']);
  assert.deepEqual(scene.getObjectByName('policy_rate__fallback_root').rotation.toArray(), [0, 0, 0, 'XYZ']);
  assert.deepEqual(accent.position.toArray(), [0, 0, 0.78]);
  assertClose(accent.quaternion.angleTo(new THREE.Quaternion()), 0);
  assert.deepEqual(accent.scale.toArray(), baseScale.toArray());
  assert.equal(ring.visible, false);

  visual.pulseArrival('policy_rate', 1);
  visual.update(2.2);
  assert.equal(ring.visible, false, 'reduced motion must suppress new arrival motion');
});

test('delayed GLB install preserves material, selection, pressure, and pending motion state', async (t) => {
  installFakeDom();
  const THREE = await import('three');
  const { createNodeVisualSystem } = await import('../../js/node-visual-system.js');

  let resolveLoad;
  const loader = {
    loadAsync() {
      return new Promise((resolve) => {
        resolveLoad = resolve;
      });
    },
  };
  const scene = new THREE.Scene();
  const visual = createNodeVisualSystem({
    scene,
    graph: {
      nodes: [
        { id: 'policy_rate', cat: 'policy', name: { ko: '기준금리', en: 'Policy rate' } },
        { id: 'fx', cat: 'policy', name: { ko: '환율', en: 'FX' } },
      ],
    },
    categories: [{ id: 'policy', color: '#66aaff' }],
    loader,
  });
  t.after(() => visual.dispose());

  visual.update(1);
  const loading = visual.loadLibrary('/delayed-models.glb');
  visual.setHighlight({ selectedId: 'fx', nodeOrders: new Map([['fx', 0]]) });
  visual.setPressures(new Map([['policy_rate', 0.8]]));
  visual.pulseArrival('policy_rate', 1);

  const fallbackBody = scene.getObjectByName('policy_rate__fallback_body');
  const dimmedBodyHex = fallbackBody.material.color.getHexString();
  assert.equal(scene.getObjectByName('fx__selection_ring').visible, true);
  assert.equal(scene.getObjectByName('policy_rate__pressure_ring').visible, true);

  const library = new THREE.Group();
  library.add(
    makeModelRoot(THREE, 'policy_rate', 'rotate'),
    makeModelRoot(THREE, 'fx', 'translate'),
  );
  resolveLoad({ scene: library });
  const result = await loading;

  assert.equal(result.status, 'ready');
  assert.deepEqual(result.loadedIds, ['policy_rate', 'fx']);
  assert.equal(
    scene.getObjectByName('policy_rate__body').material.color.getHexString(),
    dimmedBodyHex,
    'install must reapply the existing dimmed material state after changing the body preset',
  );
  assert.equal(scene.getObjectByName('fx__selection_ring').visible, true);
  assert.equal(scene.getObjectByName('policy_rate__pressure_ring').visible, true);
  assert.equal(
    scene.getObjectByName('policy_rate__pressure_ring').material.color.getHexString(),
    'ffb36b',
  );

  const policyAccent = scene.getObjectByName('policy_rate__accent');
  const fxAccent = scene.getObjectByName('fx__accent');
  assert.equal(fxAccent.material.emissiveIntensity, 0.9, 'selected material emphasis must survive install');
  const policyBaseScale = policyAccent.scale.x;
  const fxBaseX = fxAccent.position.x;
  visual.update(1.1);

  assert.ok(policyAccent.scale.x > policyBaseScale * 1.07, 'pending arrival pulse must survive install');
  assert.ok(fxAccent.position.x > fxBaseX + 0.1, 'pending selected signature must survive install');
});
