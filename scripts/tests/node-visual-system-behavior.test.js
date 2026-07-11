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
  assert.equal(fxAccent.material.emissiveIntensity, 0.18, 'selected material emphasis must survive install');
  const policyBaseScale = policyAccent.scale.x;
  const fxBaseX = fxAccent.position.x;
  visual.update(1.1);

  assert.ok(policyAccent.scale.x > policyBaseScale * 1.07, 'pending arrival pulse must survive install');
  assert.ok(fxAccent.position.x > fxBaseX + 0.1, 'pending selected signature must survive install');
});
