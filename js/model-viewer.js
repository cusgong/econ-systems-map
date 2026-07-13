// Panel instrument inspector: a small turntable that shows the selected node's
// model large, lit, and auto-rotating so it can be read from every angle — the
// map view only ever shows one side. Loads the GLB once and clones the chosen
// root; falls back silently to nothing if the library or WebGL is unavailable.

import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const BODY_PARAMS = { color: '#3a4654', metalness: 0.76, roughness: 0.32 };
const AUTO_ROTATE_SPEED = 2.2; // deg-equivalent OrbitControls units
const RESUME_AUTOROTATE_MS = 2600;

export function createModelViewer({ libraryUrl, categories }) {
  const categoryColor = new Map((categories || []).map((c) => [c.id, c.color]));
  let renderer = null;
  let scene = null;
  let camera = null;
  let controls = null;
  let pivot = null;
  let envTexture = null;
  let libraryPromise = null;
  let currentId = null;
  let currentColor = null;
  let reducedMotion = false;
  let container = null;
  let frame = 0;
  let interactedAt = -Infinity;
  let resizeObserver = null;
  let disposed = false;
  let ownedMaterials = [];

  function ensureRenderer() {
    if (renderer) return true;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'low-power' });
    } catch {
      return false; // no WebGL context available (second context, headless, etc.)
    }
    renderer.setClearColor(0x000000, 0);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.12;
    renderer.domElement.className = 'model-viewer-canvas';
    renderer.domElement.setAttribute('aria-hidden', 'true');

    scene = new THREE.Scene();
    const pmrem = new THREE.PMREMGenerator(renderer);
    const room = new RoomEnvironment();
    envTexture = pmrem.fromScene(room, 0.04).texture;
    scene.environment = envTexture;
    room.dispose();
    pmrem.dispose();

    const hemi = new THREE.HemisphereLight(0xbfdcff, 0x0a1424, 0.75);
    scene.add(hemi);
    const key = new THREE.DirectionalLight(0xf2f5ff, 1.5);
    key.position.set(6, 9, 7);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0x74a0e0, 0.85);
    rim.position.set(-7, 4, -6);
    scene.add(rim);

    camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
    camera.position.set(0, 1.1, 5.2);

    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.09;
    controls.enablePan = false;
    controls.minDistance = 3.2;
    controls.maxDistance = 8;
    controls.autoRotate = !reducedMotion;
    controls.autoRotateSpeed = AUTO_ROTATE_SPEED;
    controls.addEventListener('start', () => { interactedAt = performance.now(); controls.autoRotate = false; });

    pivot = new THREE.Group();
    scene.add(pivot);

    renderer.setAnimationLoop(tick);
    return true;
  }

  function tick() {
    if (disposed || !renderer) return;
    const el = renderer.domElement;
    if (!el.isConnected) return; // not shown: skip work
    if (!reducedMotion && !controls.autoRotate
      && performance.now() - interactedAt > RESUME_AUTOROTATE_MS) {
      controls.autoRotate = true; // resume turntable after the user lets go
    }
    controls.update();
    if (frame % 20 === 0) syncSize();
    frame++;
    renderer.render(scene, camera);
  }

  function syncSize() {
    if (!renderer || !container) return;
    const w = container.clientWidth || 320;
    const h = container.clientHeight || 240;
    if (w <= 0 || h <= 0) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const cur = renderer.getSize(new THREE.Vector2());
    if (Math.abs(cur.x - w) > 1 || Math.abs(cur.y - h) > 1 || renderer.getPixelRatio() !== dpr) {
      renderer.setPixelRatio(dpr);
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    }
  }

  function loadLibrary() {
    if (libraryPromise) return libraryPromise;
    const loader = new GLTFLoader();
    libraryPromise = loader.loadAsync(libraryUrl).then((gltf) => gltf.scene);
    return libraryPromise;
  }

  function disposeCurrent() {
    for (const m of ownedMaterials) m.dispose();
    ownedMaterials = [];
    while (pivot.children.length) {
      const c = pivot.children.pop();
      c.traverse((o) => { if (o.isMesh) o.geometry?.dispose(); });
      pivot.remove(c);
    }
  }

  function styleModel(root, color) {
    const accent = new THREE.Color(color);
    root.traverse((o) => {
      if (!o.isMesh) return;
      const role = o.userData?.econ_role;
      let mat;
      if (role === 'accent') {
        mat = new THREE.MeshStandardMaterial({
          color: accent, metalness: 0.5, roughness: 0.28,
          emissive: accent, emissiveIntensity: 0.5, envMapIntensity: 1.1,
        });
      } else {
        mat = new THREE.MeshStandardMaterial({
          ...BODY_PARAMS, emissive: '#101820', emissiveIntensity: 0.08, envMapIntensity: 1.25,
        });
      }
      o.material = mat;
      ownedMaterials.push(mat);
    });
  }

  function frameModel(root) {
    const box = new THREE.Box3().setFromObject(root);
    const sphere = box.getBoundingSphere(new THREE.Sphere());
    if (!(sphere.radius > 0)) return;
    root.position.sub(sphere.center);
    const wrap = new THREE.Group();
    // normalize to a stable on-screen size; the square viewport is the tighter
    // constraint (equal H/W), so leave a little margin around the instrument
    wrap.scale.setScalar(1.42 / sphere.radius);
    wrap.add(root);
    pivot.add(wrap);
    controls.target.set(0, 0, 0);
    camera.position.set(0, 1.15, 5.2);
    controls.update();
  }

  async function swapModel(nodeId, color) {
    disposeCurrent();
    let libraryScene;
    try {
      libraryScene = await loadLibrary();
    } catch {
      container?.classList.add('mv-failed');
      return;
    }
    if (disposed || currentId !== nodeId) return; // selection changed while loading
    let source = null;
    libraryScene.traverse((o) => {
      if (source) return;
      if (o.name === nodeId || o.userData?.econ_id === nodeId) source = o;
    });
    if (!source) { container?.classList.add('mv-failed'); return; }
    const clone = source.clone(true);
    clone.position.set(0, 0, 0);
    clone.rotation.set(0, 0, 0);
    clone.quaternion.identity();
    clone.scale.set(1, 1, 1);
    styleModel(clone, color);
    frameModel(clone);
    container?.classList.remove('mv-failed');
    container?.classList.add('mv-ready');
  }

  // Public: attach the turntable into `host` for `nodeId`. Re-parents the shared
  // canvas; only rebuilds the model when the id actually changes (panel re-renders
  // on every direction/depth toggle must not reset the spin).
  function attach(host, nodeId, opts = {}) {
    if (!host || !nodeId) return;
    reducedMotion = !!opts.reducedMotion;
    if (!ensureRenderer()) { host.classList.add('mv-failed'); return; }
    container = host;
    host.appendChild(renderer.domElement);
    controls.autoRotate = !reducedMotion;
    interactedAt = -Infinity;
    syncSize();
    resizeObserver?.disconnect();
    resizeObserver = new ResizeObserver(() => syncSize());
    resizeObserver.observe(host);
    const color = opts.color || categoryColor.get(opts.cat) || '#54e0ff';
    if (nodeId !== currentId || color !== currentColor) {
      currentId = nodeId;
      currentColor = color;
      swapModel(nodeId, color);
    }
  }

  function dispose() {
    disposed = true;
    resizeObserver?.disconnect();
    renderer?.setAnimationLoop(null);
    disposeCurrent();
    envTexture?.dispose();
    controls?.dispose();
    renderer?.dispose();
    renderer?.domElement.remove();
  }

  return { attach, dispose };
}
