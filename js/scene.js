// 3D holographic causal map: nodes, curved directed edges, flow particles,
// staged ripple highlights, camera choreography. Owns nothing about content.

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';
import { edgeKey } from './graph.js';
import { createNodeVisualSystem } from './node-visual-system.js';

const COLOR_POS = new THREE.Color('#2fb9d8');
const COLOR_NEG = new THREE.Color('#ff8a55');
const COLOR_POS_HL = new THREE.Color('#7deeff');
const COLOR_NEG_HL = new THREE.Color('#ffb184');

function hash01(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0;
  return (h % 1000) / 1000;
}

function makeGlowTexture() {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const ctx = c.getContext('2d');
  const g = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
  g.addColorStop(0, 'rgba(255,255,255,0.85)');
  g.addColorStop(0.25, 'rgba(255,255,255,0.28)');
  g.addColorStop(0.6, 'rgba(255,255,255,0.07)');
  g.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 128, 128);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

// Positions are semantic, defined per node in data/nodes.js:
// layer -> height (관념 위 / 실물 아래), radius -> 국내(중심)/글로벌(바깥), angle -> 도메인 섹터.
function computePositions(nodes, layers) {
  const yById = new Map(layers.map((l) => [l.id, l.y]));
  for (const n of nodes) {
    const a = THREE.MathUtils.degToRad(n.angle);
    const y = yById.get(n.layer) ?? 0;
    n.pos = new THREE.Vector3(Math.cos(a) * n.radius, y, Math.sin(a) * n.radius);
  }
}

export function createScene(opts) {
  const {
    container, labelContainer, graph, categories, layers,
    onSelect, lang: initialLang,
  } = opts;
  let reducedMotion = !!opts.reducedMotion;
  let lang = initialLang || 'ko';

  // --- renderer / scene / camera ---
  // container may report 0x0 when initialized in a hidden/backgrounded pane;
  // fall back to the window size and self-heal in the render loop.
  function viewSize() {
    const w = container.clientWidth || window.innerWidth || 1;
    const h = container.clientHeight || window.innerHeight || 1;
    return [w, h];
  }
  let [vw, vh] = viewSize();

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.95;
  renderer.shadowMap.enabled = false;
  function syncPixelRatio() {
    const mobile = window.matchMedia('(pointer: coarse)').matches;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, mobile ? 1.5 : 2));
  }
  syncPixelRatio();
  renderer.setSize(vw, vh);
  container.appendChild(renderer.domElement);

  const labelRenderer = new CSS2DRenderer();
  labelRenderer.setSize(vw, vh);
  labelRenderer.domElement.style.position = 'absolute';
  labelRenderer.domElement.style.inset = '0';
  labelRenderer.domElement.style.pointerEvents = 'none';
  labelContainer.appendChild(labelRenderer.domElement);

  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(new THREE.Color('#050a16'), 110, 320);
  const pmrem = new THREE.PMREMGenerator(renderer);
  const room = new RoomEnvironment();
  const envTarget = pmrem.fromScene(room, 0.04);
  scene.environment = envTarget.texture;

  const keyLight = new THREE.DirectionalLight(0xf2f5ff, 1.35);
  keyLight.position.set(24, 36, 18);
  keyLight.castShadow = false;
  scene.add(keyLight);
  const rimLight = new THREE.DirectionalLight(0x7298d8, 0.42);
  rimLight.position.set(-24, 16, -18);
  rimLight.castShadow = false;
  scene.add(rimLight);

  const camera = new THREE.PerspectiveCamera(55, vw / vh, 0.1, 600);
  camera.position.set(0, 34, 128); // side-on enough that the layer strata read

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.minDistance = 26;
  controls.maxDistance = 240;
  controls.maxPolarAngle = 1.48;
  controls.autoRotate = !reducedMotion;
  controls.autoRotateSpeed = 0.35;
  function onControlsStart() {
    controls.autoRotate = false;
    camTween = null; // user input takes the camera back immediately
  }
  controls.addEventListener('start', onControlsStart);

  // --- ambience: stars + floor rings ---
  {
    const starCount = 650;
    const pos = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount; i++) {
      const r = 190 + hashN(i) * 90;
      const th = hashN(i + 1000) * Math.PI * 2;
      const ph = Math.acos(2 * hashN(i + 2000) - 1);
      pos[i * 3] = r * Math.sin(ph) * Math.cos(th);
      pos[i * 3 + 1] = r * Math.cos(ph) * 0.6;
      pos[i * 3 + 2] = r * Math.sin(ph) * Math.sin(th);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const m = new THREE.PointsMaterial({
      color: 0x9fc9ff, size: 1.0, sizeAttenuation: true,
      transparent: true, opacity: 0.45, depthWrite: false,
    });
    scene.add(new THREE.Points(g, m));
    function hashN(i) { return hash01('star' + i); }
  }
  {
    for (let k = 0; k < 5; k++) {
      const radius = 28 + k * 15;
      const pts = [];
      for (let i = 0; i <= 96; i++) {
        const a = (i / 96) * Math.PI * 2;
        pts.push(new THREE.Vector3(Math.cos(a) * radius, -32, Math.sin(a) * radius));
      }
      const g = new THREE.BufferGeometry().setFromPoints(pts);
      const m = new THREE.LineBasicMaterial({
        color: 0x3a6ea8, transparent: true, opacity: k === 2 ? 0.14 : 0.06, depthWrite: false,
      });
      scene.add(new THREE.Line(g, m));
    }
  }

  // --- layer guides: a faint ring + name tag at each semantic altitude ---
  const layerTags = [];
  {
    const tagAngle = THREE.MathUtils.degToRad(292); // quiet sector between geopolitics and exports
    for (const l of layers) {
      const pts = [];
      for (let i = 0; i <= 96; i++) {
        const a = (i / 96) * Math.PI * 2;
        pts.push(new THREE.Vector3(Math.cos(a) * 60, l.y, Math.sin(a) * 60));
      }
      const g = new THREE.BufferGeometry().setFromPoints(pts);
      const m = new THREE.LineBasicMaterial({
        color: 0x4a7cb8, transparent: true, opacity: 0.055, depthWrite: false,
      });
      scene.add(new THREE.Line(g, m));

      const wrap = document.createElement('div');
      wrap.style.pointerEvents = 'none';
      const tag = document.createElement('div');
      tag.className = 'layer-tag';
      tag.textContent = l.name[lang] || l.name.ko;
      wrap.appendChild(tag);
      const tagObj = new CSS2DObject(wrap);
      tagObj.position.set(Math.cos(tagAngle) * 65, l.y, Math.sin(tagAngle) * 65);
      scene.add(tagObj);
      layerTags.push({ el: tag, l });
    }
  }

  // --- nodes ---
  computePositions(graph.nodes, layers);
  const glowTex = makeGlowTexture();
  const visualSystem = createNodeVisualSystem({
    scene,
    camera,
    renderer,
    graph,
    categories,
    hubMetrics: opts.hubMetrics,
    reducedMotion,
    lang,
    onSelect,
  });
  const nodeRuntime = new Map(visualSystem.pickTargets.map((target) => {
    const id = target.userData.nodeId;
    const nodeRoot = target.parent;
    const labelAnchor = nodeRoot.getObjectByName(`${id}__label_anchor`);
    const chip = labelAnchor?.children[0]?.element?.querySelector('.node-label') || null;
    return [id, { nodeRoot, chip }];
  }));
  // Fallbacks, labels, and hit proxies already exist. Model loading never gates
  // the first frame or lets a rejected request escape into the boot fatal path.
  void visualSystem.loadLibrary(opts.nodeLibraryUrl);

  // --- edges ---
  const edgeVis = new Map(); // key -> vis
  const up = new THREE.Vector3(0, 1, 0);
  for (const e of graph.edges) {
    const a = graph.nodeById.get(e.from).pos;
    const b = graph.nodeById.get(e.to).pos;
    const dir = new THREE.Vector3().subVectors(b, a);
    const dist = dir.length();
    const side = new THREE.Vector3().crossVectors(dir, up).normalize();
    if (!isFinite(side.x)) side.set(1, 0, 0);
    const f = hash01(e.from + e.to) * 2 - 1;
    const mid = new THREE.Vector3().addVectors(a, b).multiplyScalar(0.5)
      .addScaledVector(side, dist * 0.16 * f)
      .addScaledVector(up, dist * 0.1 + 2.5);
    const curve = new THREE.QuadraticBezierCurve3(a.clone(), mid, b.clone());

    const pts = curve.getPoints(40);
    const geo = new THREE.BufferGeometry().setFromPoints(pts);
    const color = e.sign > 0 ? COLOR_POS : COLOR_NEG;
    const baseOpacity = 0.1 + 0.07 * e.strength;
    const mat = e.confidence === 1
      ? new THREE.LineDashedMaterial({
          color, transparent: true, opacity: baseOpacity, dashSize: 1.7, gapSize: 1.2,
          blending: THREE.AdditiveBlending, depthWrite: false,
        })
      : new THREE.LineBasicMaterial({
          color, transparent: true, opacity: baseOpacity,
          blending: THREE.AdditiveBlending, depthWrite: false,
        });
    const line = new THREE.Line(geo, mat);
    if (e.confidence === 1) line.computeLineDistances();
    scene.add(line);
    edgeVis.set(edgeKey(e), { e, curve, line, baseOpacity, dimmed: false });
  }

  // --- flow particles (direction + strength made visible) ---
  const particles = [];
  for (const [key, ev] of edgeVis) {
    const count = ev.e.strength + 1;
    for (let i = 0; i < count; i++) {
      particles.push({
        key, curve: ev.curve,
        offset: hash01(key + i),
        speed: 0.05 + 0.035 * ev.e.strength,
        sign: ev.e.sign,
      });
    }
  }
  const pGeo = new THREE.BufferGeometry();
  const pPos = new Float32Array(particles.length * 3);
  const pCol = new Float32Array(particles.length * 3);
  pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));
  pGeo.setAttribute('color', new THREE.BufferAttribute(pCol, 3));
  const pMat = new THREE.PointsMaterial({
    size: 2.1, vertexColors: true, transparent: true, opacity: 0.9,
    map: glowTex, // round soft sprite; bare points render as squares up close
    blending: THREE.AdditiveBlending, depthWrite: false, sizeAttenuation: true,
  });
  const pCloud = new THREE.Points(pGeo, pMat);
  pCloud.frustumCulled = false;
  scene.add(pCloud);
  const tmpV = new THREE.Vector3();

  function particleColors() {
    for (let i = 0; i < particles.length; i++) {
      const p = particles[i];
      const ev = edgeVis.get(p.key);
      const c = p.sign > 0 ? COLOR_POS_HL : COLOR_NEG_HL;
      const mul = ev.dimmed ? 0.05 : (ev.highlighted ? 1.3 : 0.55);
      pCol[i * 3] = Math.min(1, c.r * mul);
      pCol[i * 3 + 1] = Math.min(1, c.g * mul);
      pCol[i * 3 + 2] = Math.min(1, c.b * mul);
    }
    pGeo.attributes.color.needsUpdate = true;
  }

  function particlePositions(elapsed) {
    for (let i = 0; i < particles.length; i++) {
      const p = particles[i];
      const t = reducedMotion ? p.offset : (p.offset + elapsed * p.speed) % 1;
      p.curve.getPoint(t, tmpV);
      pPos[i * 3] = tmpV.x;
      pPos[i * 3 + 1] = tmpV.y;
      pPos[i * 3 + 2] = tmpV.z;
    }
    pGeo.attributes.position.needsUpdate = true;
  }
  particleColors();
  particlePositions(0);

  // --- highlight machinery ---
  const hlGroup = new THREE.Group();
  scene.add(hlGroup);
  let staged = []; // {materials:[], showAt, shown}
  let hlActive = false;
  // traveling pulses along highlighted edges (per-edge duration grows with lag)
  let pulseEdges = [];
  let pulsePeriod = 0;
  let pulseT0 = 0;
  function updatePulses(elapsed) {
    if (!pulseEdges.length || reducedMotion) return;
    const phase = (elapsed - pulseT0) % pulsePeriod;
    for (const p of pulseEdges) {
      const local = (phase - p.start) / p.dur;
      if (local >= 0 && local <= 1) {
        p.curve.getPoint(local, tmpV);
        p.sprite.position.copy(tmpV);
        p.sprite.visible = true;
      } else {
        p.sprite.visible = false;
      }
      // arrival: the target node gets pushed up (+) or pulled down (−)
      if (p.lastLocal !== null && p.lastLocal >= 0 && p.lastLocal <= 1 && local > 1) {
        visualSystem.pulseArrival(p.toId, p.sign);
      }
      p.lastLocal = local;
    }
  }

  function clearHighlight() {
    hlActive = false;
    staged = [];
    pulseEdges = [];
    visualSystem.clearHighlight();
    while (hlGroup.children.length) {
      const c = hlGroup.children.pop();
      c.geometry?.dispose();
      c.material?.dispose();
      hlGroup.remove(c);
    }
    for (const ev of edgeVis.values()) {
      ev.line.material.opacity = ev.baseOpacity;
      ev.dimmed = false;
      ev.highlighted = false;
    }
    particleColors();
  }

  /**
   * spec: { nodeOrders: Map(id->order), edgeOrders: Map(key->order), selectedId }
   * Staged wave: order n appears n*0.45s later (instant when reduced motion).
   */
  function setHighlight(spec) {
    clearHighlight();
    hlActive = true;
    visualSystem.setHighlight(spec);
    const { edgeOrders } = spec;
    const now = clock.getElapsedTime();
    for (const [key, ev] of edgeVis) {
      if (edgeOrders.has(key)) {
        ev.highlighted = true;
        ev.line.material.opacity = 0.05; // replaced visually by tube
      } else {
        ev.dimmed = true;
        ev.line.material.opacity = 0.018;
      }
    }
    particleColors();

    for (const [key, order] of edgeOrders) {
      const ev = edgeVis.get(key);
      if (!ev) continue;
      // regime-flip edges glow gold: the sign can invert depending on the macro regime
      const bright = ev.e.flip
        ? new THREE.Color('#ffdf8e')
        : (ev.e.sign > 0 ? COLOR_POS_HL : COLOR_NEG_HL);
      const tubeGeo = new THREE.TubeGeometry(ev.curve, 40, 0.1 + 0.055 * ev.e.strength, 6, false);
      const tubeMat = new THREE.MeshBasicMaterial({
        color: bright, transparent: true, opacity: 0,
        blending: THREE.AdditiveBlending, depthWrite: false,
      });
      const tube = new THREE.Mesh(tubeGeo, tubeMat);
      hlGroup.add(tube);

      const coneGeo = new THREE.ConeGeometry(0.55, 1.7, 10);
      const coneMat = tubeMat.clone();
      const cone = new THREE.Mesh(coneGeo, coneMat);
      const pt = ev.curve.getPoint(0.88);
      const tangent = ev.curve.getTangent(0.88);
      cone.position.copy(pt);
      cone.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), tangent);
      hlGroup.add(cone);

      const showAt = reducedMotion ? now : now + (order - 1) * 0.45;
      staged.push({ materials: [tubeMat, coneMat], target: 0.85, showAt });

      // traveling pulse for this edge: departs on its ripple order, and its
      // travel TIME is proportional to the edge's lag — 시차가 눈에 보인다
      if (!reducedMotion) {
        const spr = new THREE.Sprite(new THREE.SpriteMaterial({
          map: glowTex, color: bright, transparent: true, opacity: 0.95,
          blending: THREE.AdditiveBlending, depthWrite: false,
        }));
        spr.scale.setScalar(3.4);
        spr.visible = false;
        hlGroup.add(spr);
        pulseEdges.push({
          curve: ev.curve,
          start: (order - 1) * 0.45,
          dur: 0.4 + ev.e.lag * 0.4,
          sprite: spr, sign: ev.e.sign, toId: ev.e.to, lastLocal: null,
        });
      }
    }
    if (pulseEdges.length) {
      pulsePeriod = Math.max(...pulseEdges.map((p) => p.start + p.dur)) + 1.6;
      pulseT0 = now;
    }
  }

  function updateStaged(elapsed) {
    for (const s of staged) {
      if (elapsed < s.showAt) continue;
      const k = Math.min(1, (elapsed - s.showAt) / 0.3);
      for (const m of s.materials) m.opacity = s.target * k;
    }
  }

  // --- node tints (simulator) ---
  function setNodeTints(map) {
    visualSystem.setPressures(map);
  }

  // --- camera choreography ---
  let camTween = null;
  function tweenCameraTo(targetPos, camPos, ms = 950) {
    if (reducedMotion) {
      controls.target.copy(targetPos);
      camera.position.copy(camPos);
      controls.update();
      camTween = null;
      return;
    }
    camTween = {
      t0: clock.getElapsedTime(),
      dur: ms / 1000,
      fromT: controls.target.clone(), toT: targetPos.clone(),
      fromC: camera.position.clone(), toC: camPos.clone(),
    };
  }
  function updateCamTween(elapsed) {
    if (!camTween) return;
    let k = (elapsed - camTween.t0) / camTween.dur;
    if (k >= 1) { k = 1; }
    const e = k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
    controls.target.lerpVectors(camTween.fromT, camTween.toT, e);
    camera.position.lerpVectors(camTween.fromC, camTween.toC, e);
    if (k === 1) camTween = null;
  }

  function focusNodes(ids, pad = 1) {
    const pts = ids.map((id) => graph.nodeById.get(id)?.pos).filter(Boolean);
    if (!pts.length) return;
    const center = pts.reduce((s, p) => s.add(p), new THREE.Vector3()).multiplyScalar(1 / pts.length);
    let radius = 6;
    for (const p of pts) radius = Math.max(radius, center.distanceTo(p));
    const dist = THREE.MathUtils.clamp(radius * 2.4 * pad + 20, 36, 165);
    const dirV = new THREE.Vector3().subVectors(camera.position, controls.target);
    if (dirV.lengthSq() < 1) dirV.set(0, 0.5, 1);
    dirV.normalize();
    if (dirV.y < 0.25) { dirV.y = 0.25; dirV.normalize(); }
    const camPos = center.clone().addScaledVector(dirV, dist);
    tweenCameraTo(center, camPos);
  }

  function resetView() {
    tweenCameraTo(new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 34, 128));
  }

  // --- picking + lever drag-to-shock ---
  const ray = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  let downXY = null;
  let dragState = null; // {id, startY, moved} — vertical drag on a lever node = live shock

  function raycastNode(ev) {
    const r = renderer.domElement.getBoundingClientRect();
    ndc.x = ((ev.clientX - r.left) / r.width) * 2 - 1;
    ndc.y = -((ev.clientY - r.top) / r.height) * 2 + 1;
    ray.setFromCamera(ndc, camera);
    const hits = ray.intersectObjects(visualSystem.pickTargets, false);
    return hits.length ? hits[0].object.userData.nodeId : null;
  }
  function dragValue(ev) {
    return THREE.MathUtils.clamp((dragState.startY - ev.clientY) / 110, -1, 1);
  }

  function onPointerDown(ev) {
    downXY = [ev.clientX, ev.clientY];
    const id = raycastNode(ev);
    const n = id ? graph.nodeById.get(id) : null;
    if (n && n.lever && typeof opts.onLeverDrag === 'function') {
      dragState = { id, startY: ev.clientY, moved: false };
      controls.enabled = false;
      try { renderer.domElement.setPointerCapture(ev.pointerId); } catch { /* ok */ }
    }
  }

  function onPointerUp(ev) {
    if (dragState) {
      const { id, moved } = dragState;
      const v = dragValue(ev);
      const runtime = nodeRuntime.get(id);
      const node = graph.nodeById.get(id);
      if (runtime && node) runtime.nodeRoot.position.y = node.pos.y;
      dragState = null;
      controls.enabled = true;
      if (moved) {
        downXY = null;
        // quantize to the simulator slider's 25% steps so UI stays consistent
        opts.onLeverDragEnd?.(id, Math.round(v * 4) / 4);
        return;
      }
      // tiny movement: fall through and treat as a click-select
    }
    if (!downXY) return;
    const movedPx = Math.hypot(ev.clientX - downXY[0], ev.clientY - downXY[1]);
    downXY = null;
    if (movedPx > 7) return;
    onSelect(raycastNode(ev));
  }

  function onPointerMove(ev) {
    if (dragState) {
      const v = dragValue(ev);
      if (Math.abs(dragState.startY - ev.clientY) > 5) dragState.moved = true;
      const runtime = nodeRuntime.get(dragState.id);
      const node = graph.nodeById.get(dragState.id);
      if (runtime && node) runtime.nodeRoot.position.y = node.pos.y + v * 4;
      if (dragState.moved) opts.onLeverDrag(dragState.id, v);
      return;
    }
    if (downXY) return;
    const id = raycastNode(ev);
    visualSystem.setHoveredId(id);
    const n = id ? graph.nodeById.get(id) : null;
    renderer.domElement.style.cursor = n ? (n.lever ? 'ns-resize' : 'pointer') : '';
  }

  function onPointerCancel(ev) {
    // interrupted drag (notification, browser gesture takeover, tab switch):
    // undo the drag without committing a shock
    downXY = null;
    if (!dragState) return;
    const { id, moved } = dragState;
    const runtime = nodeRuntime.get(id);
    const node = graph.nodeById.get(id);
    if (runtime && node) runtime.nodeRoot.position.y = node.pos.y;
    dragState = null;
    controls.enabled = true;
    try { renderer.domElement.releasePointerCapture(ev.pointerId); } catch { /* ok */ }
    // pointermove only tints after `moved`; re-render with the preview zeroed (no onLeverDragEnd)
    if (moved) opts.onLeverDrag(id, 0);
  }

  function onPointerLeave() {
    if (dragState) return;
    visualSystem.setHoveredId(null);
    renderer.domElement.style.cursor = '';
  }

  renderer.domElement.addEventListener('pointerdown', onPointerDown);
  renderer.domElement.addEventListener('pointerup', onPointerUp);
  renderer.domElement.addEventListener('pointermove', onPointerMove, { passive: true });
  renderer.domElement.addEventListener('pointercancel', onPointerCancel);
  renderer.domElement.addEventListener('pointerleave', onPointerLeave);

  // --- label distance fade ---
  const camWorld = new THREE.Vector3();
  function updateLabelFade() {
    camera.getWorldPosition(camWorld);
    for (const { nodeRoot, chip } of nodeRuntime.values()) {
      if (!chip) continue;
      const d = camWorld.distanceTo(nodeRoot.position);
      let o = 1;
      if (d > 95) o = Math.max(0.25, 1 - (d - 95) / 130);
      if (chip.classList.contains('dimmed')) o = Math.min(o, 0.14);
      chip.style.opacity = String(o);
    }
  }

  // --- loop ---
  const clock = new THREE.Clock();
  let disposed = false;
  let frame = 0;
  let animationFrame = 0;
  function animate() {
    if (disposed) return;
    animationFrame = requestAnimationFrame(animate);
    // Note: no document.hidden gate. Browsers already throttle rAF in hidden
    // tabs, and skipping renders entirely breaks first paint, CSS2D label
    // attachment, and screenshot-based verification of background windows.
    if (frame % 30 === 0) {
      const [w, h] = viewSize();
      if (Math.abs(w - vw) > 1 || Math.abs(h - vh) > 1) resize();
    }
    const elapsed = clock.getElapsedTime();
    controls.update();
    updateCamTween(elapsed);
    if (!reducedMotion || frame === 0) particlePositions(elapsed);
    if (hlActive) {
      updateStaged(elapsed);
      updatePulses(elapsed);
    }
    visualSystem.update(elapsed);
    if (frame % 3 === 0) updateLabelFade();
    renderer.render(scene, camera);
    labelRenderer.render(scene, camera);
    frame++;
    if (frame === 1 && typeof opts.onFirstFrame === 'function') opts.onFirstFrame();
  }
  animate();

  function resize() {
    [vw, vh] = viewSize();
    camera.aspect = vw / vh;
    camera.updateProjectionMatrix();
    syncPixelRatio(); // monitor, zoom, or coarse-pointer changes
    renderer.setSize(vw, vh);
    labelRenderer.setSize(vw, vh);
  }
  window.addEventListener('resize', resize);
  function onVisibilityChange() {
    if (!document.hidden && !disposed) {
      resize();
      renderer.render(scene, camera);
      labelRenderer.render(scene, camera);
    }
  }
  document.addEventListener('visibilitychange', onVisibilityChange);

  return {
    setHighlight, clearHighlight, setNodeTints, focusNodes, resetView,
    setLang(l) {
      lang = l;
      visualSystem.setLang(l);
      for (const tg of layerTags) {
        tg.el.textContent = tg.l.name[lang] || tg.l.name.ko;
      }
    },
    setReducedMotion(v) {
      reducedMotion = v;
      if (v) controls.autoRotate = false;
      visualSystem.setReducedMotion(v);
      particlePositions(0);
    },
    setLabelTitles(map) {
      visualSystem.setLabelTitles(map);
    },
    setLabelValues(map) {
      visualSystem.setLabelValues(map);
    },
    dispose() {
      if (disposed) return;
      disposed = true;
      cancelAnimationFrame(animationFrame);
      clearHighlight();
      window.removeEventListener('resize', resize);
      document.removeEventListener('visibilitychange', onVisibilityChange);
      controls.removeEventListener('start', onControlsStart);
      renderer.domElement.removeEventListener('pointerdown', onPointerDown);
      renderer.domElement.removeEventListener('pointerup', onPointerUp);
      renderer.domElement.removeEventListener('pointermove', onPointerMove);
      renderer.domElement.removeEventListener('pointercancel', onPointerCancel);
      renderer.domElement.removeEventListener('pointerleave', onPointerLeave);
      controls.dispose();
      visualSystem.dispose();
      const geometries = new Set();
      const materials = new Set();
      scene.traverse((object) => {
        if (object.geometry) geometries.add(object.geometry);
        if (Array.isArray(object.material)) {
          for (const material of object.material) materials.add(material);
        } else if (object.material) {
          materials.add(object.material);
        }
      });
      for (const geometry of geometries) geometry.dispose();
      for (const material of materials) material.dispose();
      glowTex.dispose();
      envTarget.dispose();
      room.dispose();
      pmrem.dispose();
      renderer.dispose();
      renderer.domElement.remove();
      labelRenderer.domElement.remove();
    },
  };
}
