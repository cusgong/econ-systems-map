// Precision macro-instrument node visuals. Creates a complete PBR fallback
// hierarchy synchronously, then upgrades individually validated GLB roots.

import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';
import { validateModelContract } from './model-contract.js';

const COLOR_UP = new THREE.Color('#ffb36b');
const COLOR_DOWN = new THREE.Color('#6fb5ff');
const COLOR_SELECTION = new THREE.Color('#dbe5ef');
const NEUTRAL_HUB_METRIC = Object.freeze({ hubScore: 0.5, score100: 50, radiusScale: 1 });
const VERTICAL_SLICE_ANCHOR_ID = 'policy_rate';
const VERTICAL_SLICE_MODEL_IDS = new Set([VERTICAL_SLICE_ANCHOR_ID]);
const BASE_VISUAL_RADIUS = 1.82;
const LABEL_GAP = 0.62;
const MAX_MODEL_TRIANGLES = 3000;

const MATERIAL_PARAMS = Object.freeze({
  darkTitanium: Object.freeze({
    color: '#202a35', metalness: 0.9, roughness: 0.25, envMapIntensity: 1.1,
  }),
  satinAlloy: Object.freeze({
    color: '#718091', metalness: 0.82, roughness: 0.34, envMapIntensity: 1.0,
  }),
  technicalCeramic: Object.freeze({
    color: '#c5cbd0', metalness: 0.08, roughness: 0.42, envMapIntensity: 0.8,
  }),
});

function makeBodyTemplate(params, name) {
  const material = new THREE.MeshStandardMaterial({
    ...params,
    emissive: '#05080b',
    emissiveIntensity: 0.03,
    flatShading: false,
  });
  material.name = name;
  return material;
}

function bodyPresetFor(materialName = '') {
  if (materialName.includes('SATIN_ALLOY')) return 'satinAlloy';
  if (materialName.includes('TECHNICAL_CERAMIC')) return 'technicalCeramic';
  return 'darkTitanium';
}

function materialList(material) {
  return Array.isArray(material) ? material : material ? [material] : [];
}

function triangleCount(mesh) {
  const geometry = mesh.geometry;
  if (!geometry) return 0;
  if (geometry.index) return geometry.index.count / 3;
  return (geometry.getAttribute('position')?.count || 0) / 3;
}

function isIdentityRoot(root) {
  const p = root.position;
  const q = root.quaternion;
  const s = root.scale;
  const eps = 1e-6;
  return p.lengthSq() <= eps * eps
    && Math.abs(q.x) <= eps
    && Math.abs(q.y) <= eps
    && Math.abs(q.z) <= eps
    && Math.abs(Math.abs(q.w) - 1) <= eps
    && Math.abs(s.x - 1) <= eps
    && Math.abs(s.y - 1) <= eps
    && Math.abs(s.z - 1) <= eps;
}

function describeRoot(root) {
  const roles = [];
  let triangles = 0;
  root.updateWorldMatrix(true, true);
  root.traverse((object) => {
    if (!object.isMesh) return;
    roles.push(object.userData?.econ_role);
    triangles += triangleCount(object);
  });
  const bounds = new THREE.Box3().setFromObject(root, true);
  const sphere = bounds.getBoundingSphere(new THREE.Sphere());
  return {
    id: root.userData?.econ_id || root.name,
    roles,
    radius: sphere.radius,
    triangles,
    rootIdentity: isIdentityRoot(root),
    root,
  };
}

function findModelRoots(libraryScene) {
  const roots = [];
  libraryScene.traverse((object) => {
    if (typeof object.userData?.econ_id === 'string') roots.push(object);
  });
  return roots;
}

function issueSummary(contract) {
  const issues = [];
  const missing = contract.missing.filter((id) => VERTICAL_SLICE_MODEL_IDS.has(id));
  if (missing.length) issues.push(`missing:${missing.join(',')}`);
  if (contract.extra.length) issues.push(`extra:${contract.extra.join(',')}`);
  if (contract.duplicates.length) issues.push(`duplicates:${contract.duplicates.join(',')}`);
  if (contract.invalid.length) {
    issues.push(`invalid:${contract.invalid.map((record) => record.id).join(',')}`);
  }
  return issues;
}

function setDocumentStatus(status) {
  if (typeof document !== 'undefined' && document.documentElement) {
    document.documentElement.dataset.nodeModels = status;
  }
}

function disposeTree(root, keepMaterials = new Set()) {
  const geometries = new Set();
  const materials = new Set();
  root.traverse((object) => {
    if (!object.isMesh) return;
    if (object.geometry) geometries.add(object.geometry);
    for (const material of materialList(object.material)) {
      if (!keepMaterials.has(material)) materials.add(material);
    }
  });
  for (const geometry of geometries) geometry.dispose();
  for (const material of materials) material.dispose();
  root.removeFromParent();
}

function cloneMetric(metric) {
  if (!metric) return { ...NEUTRAL_HUB_METRIC };
  return {
    ...NEUTRAL_HUB_METRIC,
    ...metric,
    radiusScale: Number.isFinite(metric.radiusScale) ? metric.radiusScale : 1,
  };
}

export function createNodeVisualSystem(options) {
  const {
    scene,
    camera,
    renderer,
    graph,
    categories,
    hubMetrics,
    onSelect,
  } = options;
  if (!scene || !graph?.nodes || !Array.isArray(categories)) {
    throw new TypeError('createNodeVisualSystem requires scene, graph.nodes, and categories');
  }

  let lang = options.lang || 'ko';
  let reducedMotion = !!options.reducedMotion;
  let modelStatus = 'fallback';
  let modelIssues = [];
  let warned = false;
  let disposed = false;
  let generation = 0;
  let lastElapsed = 0;
  let previousElapsed = 0;
  let selectedId = null;

  const expectedIds = graph.nodes.map((node) => node.id);
  const categoryById = new Map(categories.map((category) => [category.id, category]));
  const records = new Map();
  const pickTargets = [];
  const ownedMaterials = new Set();
  const loadedGeometries = new Set();
  const sourceMaterialsDisposed = new Set();
  const sharedGeometries = new Set();

  const bodyTemplates = {
    darkTitanium: makeBodyTemplate(MATERIAL_PARAMS.darkTitanium, 'RUNTIME__DARK_TITANIUM'),
    satinAlloy: makeBodyTemplate(MATERIAL_PARAMS.satinAlloy, 'RUNTIME__SATIN_ALLOY'),
    technicalCeramic: makeBodyTemplate(MATERIAL_PARAMS.technicalCeramic, 'RUNTIME__TECHNICAL_CERAMIC'),
  };
  const fallbackSphereGeometry = new THREE.SphereGeometry(1, 28, 20);
  const fallbackAccentGeometry = new THREE.TorusGeometry(0.76, 0.065, 10, 40);
  const selectionGeometry = new THREE.TorusGeometry(1.22, 0.022, 8, 48);
  const pressureGeometry = new THREE.TorusGeometry(1.32, 0.05, 8, 48);
  const leverGeometry = new THREE.TorusGeometry(1.43, 0.035, 8, 48);
  const hitGeometry = new THREE.SphereGeometry(1, 12, 8);
  sharedGeometries.add(fallbackSphereGeometry);
  sharedGeometries.add(fallbackAccentGeometry);
  sharedGeometries.add(selectionGeometry);
  sharedGeometries.add(pressureGeometry);
  sharedGeometries.add(leverGeometry);
  sharedGeometries.add(hitGeometry);

  for (const template of Object.values(bodyTemplates)) ownedMaterials.add(template);

  function own(material) {
    ownedMaterials.add(material);
    return material;
  }

  function cloneBodyMaterial(nodeId) {
    const material = own(bodyTemplates.darkTitanium.clone());
    material.name = `${nodeId}__runtime_body`;
    return material;
  }

  function cloneAccentMaterial(nodeId, categoryColor) {
    const material = own(new THREE.MeshStandardMaterial({
      color: categoryColor,
      metalness: 0.52,
      roughness: 0.28,
      emissive: categoryColor,
      emissiveIntensity: 0.07,
      envMapIntensity: 1.05,
    }));
    material.name = `${nodeId}__runtime_accent`;
    return material;
  }

  function makeOverlayMaterial(color, opacity) {
    return own(new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity,
      depthWrite: false,
      toneMapped: false,
    }));
  }

  function updateLabelOffset(record, normalizedTop = 1) {
    const top = Math.max(0.72, normalizedTop) * record.visualRadius;
    record.labelAnchor.position.set(0, top + LABEL_GAP, 0);
  }

  for (const node of graph.nodes) {
    const category = categoryById.get(node.cat);
    if (!category) throw new Error(`Unknown category for node ${node.id}: ${node.cat}`);
    const categoryColor = new THREE.Color(category.color);
    const hubMetric = cloneMetric(hubMetrics?.get?.(node.id));
    const visualRadius = BASE_VISUAL_RADIUS * hubMetric.radiusScale;

    const nodeRoot = new THREE.Group();
    nodeRoot.name = `${node.id}__node_root`;
    if (node.pos?.isVector3) nodeRoot.position.copy(node.pos);

    const modelRoot = new THREE.Group();
    modelRoot.name = `${node.id}__model_root`;
    modelRoot.scale.setScalar(visualRadius);
    nodeRoot.add(modelRoot);

    const fallbackRoot = new THREE.Group();
    fallbackRoot.name = `${node.id}__fallback_root`;
    fallbackRoot.scale.setScalar(visualRadius);
    nodeRoot.add(fallbackRoot);

    const bodyMaterial = cloneBodyMaterial(node.id);
    const accentMaterial = cloneAccentMaterial(node.id, categoryColor);
    const fallbackBody = new THREE.Mesh(fallbackSphereGeometry, bodyMaterial);
    fallbackBody.name = `${node.id}__fallback_body`;
    const fallbackAccent = new THREE.Mesh(fallbackAccentGeometry, accentMaterial);
    fallbackAccent.name = `${node.id}__fallback_accent`;
    fallbackAccent.position.z = 0.78;
    fallbackRoot.add(fallbackBody, fallbackAccent);

    const selectionRing = new THREE.Mesh(
      selectionGeometry,
      makeOverlayMaterial(COLOR_SELECTION, 0.78),
    );
    selectionRing.name = `${node.id}__selection_ring`;
    selectionRing.scale.setScalar(visualRadius);
    selectionRing.visible = false;
    nodeRoot.add(selectionRing);

    const pressureRing = new THREE.Mesh(
      pressureGeometry,
      makeOverlayMaterial(COLOR_UP, 0.7),
    );
    pressureRing.name = `${node.id}__pressure_ring`;
    pressureRing.scale.setScalar(visualRadius);
    pressureRing.visible = false;
    nodeRoot.add(pressureRing);

    const leverRing = node.lever
      ? new THREE.Mesh(leverGeometry, makeOverlayMaterial(categoryColor, 0.48))
      : null;
    if (leverRing) {
      leverRing.name = `${node.id}__lever_ring`;
      leverRing.scale.setScalar(visualRadius);
      nodeRoot.add(leverRing);
    }

    const hitMaterial = own(new THREE.MeshBasicMaterial({
      transparent: true,
      opacity: 0,
      depthWrite: false,
      colorWrite: false,
    }));
    const hitProxy = new THREE.Mesh(hitGeometry, hitMaterial);
    hitProxy.name = `${node.id}__hit_proxy`;
    hitProxy.scale.setScalar(visualRadius * 1.18);
    hitProxy.userData.nodeId = node.id;
    nodeRoot.add(hitProxy);
    pickTargets.push(hitProxy);

    const wrap = document.createElement('div');
    wrap.style.pointerEvents = 'none';
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'node-label';
    chip.style.position = 'absolute';
    chip.style.left = '0';
    chip.style.top = '0';
    chip.tabIndex = -1;
    chip.innerHTML = '<span class="dot"></span><span class="nm"></span><span class="lval"></span>'
      + (node.lever ? '<span class="lever-mark">LEVER</span>' : '')
      + '<span class="tint" aria-hidden="true"></span>';
    chip.querySelector('.dot').style.background = category.color;
    chip.querySelector('.nm').textContent = node.name[lang] || node.name.ko;
    const labelClick = (event) => {
      event.stopPropagation();
      onSelect?.(node.id);
    };
    chip.addEventListener('click', labelClick);
    wrap.appendChild(chip);
    const labelObject = new CSS2DObject(wrap);
    const labelAnchor = new THREE.Group();
    labelAnchor.name = `${node.id}__label_anchor`;
    labelAnchor.add(labelObject);
    nodeRoot.add(labelAnchor);

    const motionState = {
      hovered: false,
      selectedAt: null,
      arrivalAt: null,
      arrivalSign: 0,
      accentBaseQuaternion: fallbackAccent.quaternion.clone(),
      accentBaseScale: fallbackAccent.scale.clone(),
    };

    const record = {
      id: node.id,
      node,
      nodeRoot,
      modelRoot,
      fallbackRoot,
      bodyMeshes: [fallbackBody],
      accentRoot: fallbackAccent,
      selectionRing,
      pressureRing,
      leverRing,
      hitProxy,
      labelAnchor,
      chip,
      categoryColor,
      hubMetric,
      modelStatus: 'fallback',
      motionState,
      visualRadius,
      bodyMaterial,
      bodyPreset: 'darkTitanium',
      accentMaterial,
      fallbackBody,
      fallbackAccent,
      labelObject,
      labelClick,
      loadedRoot: null,
      pressure: 0,
    };
    updateLabelOffset(record);
    scene.add(nodeRoot);
    records.set(node.id, record);
  }

  setDocumentStatus('fallback');

  function configureBodyMaterial(record, sourceName) {
    const preset = bodyPresetFor(sourceName);
    const template = bodyTemplates[preset];
    record.bodyMaterial.copy(template);
    record.bodyMaterial.name = `${record.id}__runtime_${preset}`;
    record.bodyPreset = preset;
  }

  function disposeSourceMaterial(material) {
    for (const item of materialList(material)) {
      if (ownedMaterials.has(item) || sourceMaterialsDisposed.has(item)) continue;
      sourceMaterialsDisposed.add(item);
      item.dispose();
    }
  }

  function resetAccentBaseline(record) {
    record.motionState.accentBaseQuaternion.copy(record.accentRoot.quaternion);
    record.motionState.accentBaseScale.copy(record.accentRoot.scale);
    record.motionState.selectedAt = null;
    record.motionState.arrivalAt = null;
  }

  function restoreFallback(record) {
    if (record.loadedRoot) {
      record.loadedRoot.traverse((object) => {
        if (object.isMesh && object.geometry) loadedGeometries.delete(object.geometry);
      });
      disposeTree(record.loadedRoot, ownedMaterials);
      record.loadedRoot = null;
    }
    record.modelRoot.clear();
    record.fallbackRoot.visible = true;
    record.bodyMeshes = [record.fallbackBody];
    record.accentRoot = record.fallbackAccent;
    record.modelStatus = 'fallback';
    configureBodyMaterial(record, 'MAT__DARK_TITANIUM');
    updateLabelOffset(record);
    resetAccentBaseline(record);
  }

  function installModel(record, sourceRoot) {
    sourceRoot.removeFromParent();
    sourceRoot.updateWorldMatrix(true, true);
    const bounds = new THREE.Box3().setFromObject(sourceRoot, true);
    const sphere = bounds.getBoundingSphere(new THREE.Sphere());
    if (!Number.isFinite(sphere.radius) || sphere.radius <= 0) {
      throw new Error(`${record.id}: invalid model radius`);
    }

    const bodyMeshes = [];
    let accentRoot = null;
    sourceRoot.traverse((object) => {
      if (!object.isMesh) return;
      const role = object.userData?.econ_role;
      const sourceName = materialList(object.material)[0]?.name || '';
      disposeSourceMaterial(object.material);
      if (role === 'body') {
        configureBodyMaterial(record, sourceName);
        object.material = record.bodyMaterial;
        bodyMeshes.push(object);
      } else if (role === 'accent') {
        object.material = record.accentMaterial;
        accentRoot = object;
      }
      loadedGeometries.add(object.geometry);
    });
    if (!bodyMeshes.length || !accentRoot) throw new Error(`${record.id}: missing body or accent role`);

    const normalizedRoot = new THREE.Group();
    normalizedRoot.name = `${record.id}__normalized_model`;
    sourceRoot.position.addScaledVector(sphere.center, -1);
    normalizedRoot.scale.setScalar(1 / sphere.radius);
    normalizedRoot.add(sourceRoot);
    record.modelRoot.add(normalizedRoot);
    record.fallbackRoot.visible = false;
    record.loadedRoot = normalizedRoot;
    record.bodyMeshes = bodyMeshes;
    record.accentRoot = accentRoot;
    record.modelStatus = 'ready';
    const normalizedTop = (bounds.max.y - sphere.center.y) / sphere.radius;
    updateLabelOffset(record, normalizedTop);
    resetAccentBaseline(record);
  }

  function resetModels() {
    for (const record of records.values()) restoreFallback(record);
  }

  function warnIssues(issues) {
    if (!issues.length || warned) return;
    warned = true;
    console.warn(`[macroscope] Node model library used fallbacks: ${issues.join(' | ')}`);
  }

  async function loadLibrary(url) {
    const currentGeneration = ++generation;
    resetModels();
    modelIssues = [];
    if (!url) {
      modelStatus = 'fallback';
      setDocumentStatus('fallback');
      return {
        status: 'fallback',
        loadedIds: [],
        fallbackIds: [...expectedIds],
        issues: [],
      };
    }

    modelStatus = 'loading';
    setDocumentStatus('loading');
    try {
      const loader = options.loader || new GLTFLoader(options.loadingManager);
      const gltf = await loader.loadAsync(url);
      if (disposed || currentGeneration !== generation) {
        disposeTree(gltf.scene, ownedMaterials);
        return {
          status: 'fallback',
          loadedIds: [],
          fallbackIds: [...expectedIds],
          issues: ['stale-load'],
        };
      }

      const described = findModelRoots(gltf.scene).map(describeRoot);
      const contract = validateModelContract(expectedIds, described.map((record) => ({
        id: record.id,
        roles: record.roles,
        radius: record.radius,
        triangles: record.triangles,
        rootIdentity: record.rootIdentity,
      })));
      const validIds = contract.validIds.filter((id) => {
        const record = described.find((item) => item.id === id);
        return record && record.triangles <= MAX_MODEL_TRIANGLES;
      });
      const loadedIds = [];
      for (const id of validIds) {
        const description = described.find((record) => record.id === id);
        const record = records.get(id);
        if (!description || !record) continue;
        try {
          installModel(record, description.root);
          loadedIds.push(id);
        } catch (error) {
          modelIssues.push(`${id}:${error instanceof Error ? error.message : String(error)}`);
          disposeTree(description.root, ownedMaterials);
          restoreFallback(record);
        }
      }

      // The current GLB contains only policy_rate. The generic path intentionally
      // accepts later proof/full libraries without another runtime rewrite.
      disposeTree(gltf.scene, ownedMaterials);
      const fallbackIds = expectedIds.filter((id) => !loadedIds.includes(id));
      modelIssues = [...issueSummary(contract), ...modelIssues];
      modelStatus = loadedIds.length === expectedIds.length
        ? 'ready'
        : loadedIds.length
          ? 'partial'
          : 'fallback';
      setDocumentStatus(modelStatus);
      warnIssues(modelIssues);
      return {
        status: modelStatus,
        loadedIds,
        fallbackIds,
        issues: [...modelIssues],
      };
    } catch (error) {
      resetModels();
      const issue = error instanceof Error ? error.message : String(error);
      modelIssues = [issue];
      modelStatus = 'fallback';
      setDocumentStatus('fallback');
      warnIssues(modelIssues);
      return {
        status: 'fallback',
        loadedIds: [],
        fallbackIds: [...expectedIds],
        issues: [...modelIssues],
      };
    }
  }

  function setHoveredId(id) {
    for (const record of records.values()) record.motionState.hovered = record.id === id;
  }

  function applyMaterialState(record, dimmed, selected) {
    const bodyBase = bodyTemplates[record.bodyPreset].color;
    record.bodyMaterial.color.copy(bodyBase);
    record.accentMaterial.color.copy(record.categoryColor);
    if (dimmed) {
      record.bodyMaterial.color.multiplyScalar(0.28);
      record.accentMaterial.color.multiplyScalar(0.24);
      record.accentMaterial.emissiveIntensity = 0.01;
    } else {
      record.accentMaterial.emissiveIntensity = selected ? 0.18 : 0.07;
    }
  }

  function clearHighlight() {
    selectedId = null;
    for (const record of records.values()) {
      applyMaterialState(record, false, false);
      record.selectionRing.visible = false;
      record.chip.classList.remove('dimmed', 'hl', 'selected');
      record.motionState.selectedAt = null;
    }
  }

  function setHighlight(spec = {}) {
    const nodeOrders = spec.nodeOrders || new Map();
    const nextSelectedId = spec.selectedId || null;
    const selectionChanged = nextSelectedId !== selectedId;
    selectedId = nextSelectedId;
    for (const record of records.values()) {
      const included = nodeOrders.has(record.id) || record.id === selectedId;
      const dimmed = !included;
      const selected = record.id === selectedId;
      applyMaterialState(record, dimmed, selected);
      record.selectionRing.visible = selected;
      record.chip.classList.toggle('dimmed', dimmed);
      record.chip.classList.toggle('hl', included);
      record.chip.classList.toggle('selected', selected);
      if (selected && selectionChanged && !reducedMotion) {
        record.motionState.selectedAt = lastElapsed;
      }
    }
  }

  function setPressures(map) {
    for (const record of records.values()) {
      const value = map ? (map.get(record.id) ?? 0) : 0;
      record.pressure = value;
      const active = Math.abs(value) > 0.06;
      record.pressureRing.visible = active;
      record.pressureRing.material.color.copy(value >= 0 ? COLOR_UP : COLOR_DOWN);
      record.pressureRing.material.opacity = 0.42 + Math.min(1, Math.abs(value)) * 0.42;
      record.pressureRing.scale.setScalar(record.visualRadius * (1 + Math.min(1, Math.abs(value)) * 0.08));
      const tint = record.chip.querySelector('.tint');
      record.chip.classList.toggle('tint-up', active && value > 0);
      record.chip.classList.toggle('tint-down', active && value < 0);
      if (tint) tint.textContent = active ? (value > 0 ? '▲' : '▼') : '';
    }
  }

  function pulseArrival(id, sign) {
    const record = records.get(id);
    if (!record || reducedMotion) return;
    record.motionState.arrivalAt = lastElapsed;
    record.motionState.arrivalSign = sign >= 0 ? 1 : -1;
  }

  function setLang(nextLang) {
    lang = nextLang || 'ko';
    for (const record of records.values()) {
      record.chip.querySelector('.nm').textContent = record.node.name[lang] || record.node.name.ko;
    }
  }

  function setLabelTitles(map) {
    if (!map) return;
    for (const [id, title] of map) {
      const record = records.get(id);
      if (record) record.chip.title = title;
    }
  }

  function setLabelValues(map) {
    for (const record of records.values()) {
      const value = record.chip.querySelector('.lval');
      if (value) value.textContent = map?.get(record.id) || '';
    }
  }

  const worldPosition = new THREE.Vector3();
  const axis = new THREE.Vector3();
  const signatureRotation = new THREE.Quaternion();
  function updateHitProxy(record) {
    if (!camera || !renderer?.domElement) return;
    const height = renderer.domElement.clientHeight || window.innerHeight || 1;
    record.nodeRoot.getWorldPosition(worldPosition);
    const distance = camera.position.distanceTo(worldPosition);
    const worldPerPixel = (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2) * distance) / height;
    const minimumRadius = worldPerPixel * 22;
    record.hitProxy.scale.setScalar(Math.max(record.visualRadius * 1.18, minimumRadius));
  }

  function updateAccentMotion(record, elapsed) {
    const state = record.motionState;
    const accent = record.accentRoot;
    accent.quaternion.copy(state.accentBaseQuaternion);
    accent.scale.copy(state.accentBaseScale);
    if (reducedMotion) return;

    if (state.selectedAt !== null) {
      const duration = Number(record.loadedRoot?.children[0]?.userData?.econ_duration) || 0.28;
      const t = (elapsed - state.selectedAt) / duration;
      if (t >= 1) {
        state.selectedAt = null;
      } else if (t >= 0) {
        const rootData = record.loadedRoot?.children[0]?.userData || {};
        const amount = Number(rootData.econ_amount) || 0.16;
        const axisName = rootData.econ_axis || 'z';
        axis.set(axisName === 'x' ? 1 : 0, axisName === 'y' ? 1 : 0, axisName === 'z' ? 1 : 0);
        signatureRotation.setFromAxisAngle(axis, Math.sin(Math.PI * t) * amount);
        accent.quaternion.multiply(signatureRotation);
      }
    }
    if (state.arrivalAt !== null) {
      const t = (elapsed - state.arrivalAt) / 0.2;
      if (t >= 1) {
        state.arrivalAt = null;
      } else if (t >= 0) {
        accent.scale.multiplyScalar(1 + Math.sin(Math.PI * t) * 0.08);
      }
    }
  }

  function update(elapsed) {
    lastElapsed = Number.isFinite(elapsed) ? elapsed : lastElapsed;
    const delta = Math.max(0, Math.min(0.05, lastElapsed - previousElapsed));
    previousElapsed = lastElapsed;
    const smoothing = reducedMotion ? 1 : 1 - Math.exp(-delta * 18);
    for (const record of records.values()) {
      const hover = record.motionState.hovered && !reducedMotion;
      record.modelRoot.rotation.x += ((hover ? -0.018 : 0) - record.modelRoot.rotation.x) * smoothing;
      record.modelRoot.rotation.y += ((hover ? 0.03 : 0) - record.modelRoot.rotation.y) * smoothing;
      updateAccentMotion(record, lastElapsed);
      updateHitProxy(record);
    }
  }

  function setReducedMotion(value) {
    reducedMotion = !!value;
    if (!reducedMotion) return;
    for (const record of records.values()) {
      record.modelRoot.rotation.set(0, 0, 0);
      record.motionState.selectedAt = null;
      record.motionState.arrivalAt = null;
      record.accentRoot.quaternion.copy(record.motionState.accentBaseQuaternion);
      record.accentRoot.scale.copy(record.motionState.accentBaseScale);
    }
  }

  function getDiagnostics() {
    const loadedModelCount = [...records.values()].filter((record) => record.modelStatus === 'ready').length;
    return {
      modelStatus,
      loadedModelCount,
      fallbackCount: records.size - loadedModelCount,
      calls: renderer?.info?.render?.calls ?? 0,
      triangles: renderer?.info?.render?.triangles ?? 0,
      issues: [...modelIssues],
      anchorReady: records.get(VERTICAL_SLICE_ANCHOR_ID)?.modelStatus === 'ready',
    };
  }

  function dispose() {
    if (disposed) return;
    disposed = true;
    generation++;
    for (const record of records.values()) {
      record.chip.removeEventListener('click', record.labelClick);
      record.labelObject.element.remove();
      if (record.loadedRoot) disposeTree(record.loadedRoot, ownedMaterials);
      record.nodeRoot.removeFromParent();
    }
    for (const geometry of loadedGeometries) geometry.dispose();
    for (const geometry of sharedGeometries) geometry.dispose();
    for (const material of ownedMaterials) material.dispose();
    records.clear();
    pickTargets.length = 0;
  }

  return {
    pickTargets,
    loadLibrary,
    setHoveredId,
    setHighlight,
    clearHighlight,
    setPressures,
    pulseArrival,
    setLang,
    setLabelTitles,
    setLabelValues,
    update,
    getDiagnostics,
    dispose,
    setReducedMotion,
  };
}
