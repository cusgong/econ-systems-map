// Precision macro-instrument node visuals. Creates a complete PBR fallback
// hierarchy synchronously, then upgrades individually validated GLB roots.

import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';
import { validateModelContract } from './model-contract.js';
import { layoutNodeLabels } from './node-label-layout.js';
import { evaluateSignatureTransform } from './node-motion.js';
import {
  createLatestLoadCoordinator,
  normalizePublicLoadStatus,
  validateNodeModelIdentity,
} from './node-model-loader-contract.js';

const COLOR_UP = new THREE.Color('#ffb36b');
const COLOR_DOWN = new THREE.Color('#6fb5ff');
const COLOR_SELECTION = new THREE.Color('#dbe5ef');
const NEUTRAL_HUB_METRIC = Object.freeze({ hubScore: 0.5, score100: 50, radiusScale: 1 });
const MODEL_LOAD_ANCHOR_ID = 'policy_rate';
const BASE_VISUAL_RADIUS = 1.82;
const MIN_HUB_RADIUS_SCALE = 0.82;
const MAX_HUB_RADIUS_SCALE = 1.28;
const HOVER_TILT_X = THREE.MathUtils.degToRad(-1);
const HOVER_TILT_Y = THREE.MathUtils.degToRad(1.7);
const HOVER_RESPONSE_RATE = 18;
const MIN_SIGNATURE_DURATION = 0.22;
const MAX_SIGNATURE_DURATION = 0.32;
const ARRIVAL_DURATION = 0.2;
const LABEL_GAP = 0.62;
const LABEL_SCREEN_GAP = 4;
const LABEL_SCREEN_MARGIN = 8;
const LABEL_VERTICAL_OFFSET = 12;
const LABEL_LAYOUT_INTERVAL = 0.06;
const LABEL_LOCAL_DISPLACEMENT = 32;
const LABEL_CRITICAL_DISPLACEMENT = 64;
const LABEL_SELECTED_ASSOCIATION_CAP = 160;
const LABEL_SELECTED_LEADER_THRESHOLD = 0;
const NODE_CENTER_CLEARANCE = 3;
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
  const meshChildren = [];
  let triangles = 0;
  root.updateWorldMatrix(true, true);
  root.traverse((object) => {
    if (!object.isMesh) return;
    const role = object.userData?.econ_role;
    roles.push(role);
    meshChildren.push({ name: object.name, role });
    triangles += triangleCount(object);
  });
  const bounds = new THREE.Box3().setFromObject(root, true);
  const sphere = bounds.getBoundingSphere(new THREE.Sphere());
  const id = typeof root.userData?.econ_id === 'string' ? root.userData.econ_id : root.name;
  const identity = validateNodeModelIdentity(id, {
    name: root.name,
    econId: root.userData?.econ_id,
    ready: root.userData?.econ_ready,
    meshChildren,
  });
  return {
    id,
    roles,
    radius: sphere.radius,
    triangles,
    rootIdentity: isIdentityRoot(root) && identity.valid,
    identityIssues: identity.issues,
    root,
  };
}

function findModelRoots(libraryScene, expectedIds) {
  const roots = [];
  const expected = new Set(expectedIds);
  libraryScene.traverse((object) => {
    if (typeof object.userData?.econ_id === 'string' || expected.has(object.name)) roots.push(object);
  });
  return roots;
}

function issueSummary(contract) {
  const issues = [];
  const missing = contract.missing;
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
  const radiusScale = Number.isFinite(metric.radiusScale) ? metric.radiusScale : 1;
  return {
    ...NEUTRAL_HUB_METRIC,
    ...metric,
    radiusScale: Math.max(MIN_HUB_RADIUS_SCALE, Math.min(MAX_HUB_RADIUS_SCALE, radiusScale)),
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
  let lastElapsed = 0;
  let previousElapsed = 0;
  let lastLabelLayoutAt = -Infinity;
  let labelLayoutDirty = true;
  let selectedId = null;

  const expectedIds = graph.nodes.map((node) => node.id);
  const categoryById = new Map(categories.map((category) => [category.id, category]));
  const records = new Map();
  const pickTargets = [];
  const ownedMaterials = new Set();
  const sourceMaterialsDisposed = new Set();
  const sharedGeometries = new Set();
  const loadCoordinator = createLatestLoadCoordinator();

  const bodyTemplates = {
    darkTitanium: makeBodyTemplate(MATERIAL_PARAMS.darkTitanium, 'RUNTIME__DARK_TITANIUM'),
    satinAlloy: makeBodyTemplate(MATERIAL_PARAMS.satinAlloy, 'RUNTIME__SATIN_ALLOY'),
    technicalCeramic: makeBodyTemplate(MATERIAL_PARAMS.technicalCeramic, 'RUNTIME__TECHNICAL_CERAMIC'),
  };
  const fallbackSphereGeometry = new THREE.SphereGeometry(1, 28, 20);
  const fallbackAccentGeometry = new THREE.TorusGeometry(0.76, 0.065, 10, 40);
  const selectionGeometry = new THREE.TorusGeometry(1.22, 0.022, 8, 48);
  const pressureGeometry = new THREE.TorusGeometry(1.32, 0.05, 8, 48);
  const arrivalGeometry = new THREE.TorusGeometry(1.5, 0.025, 8, 48);
  const leverGeometry = new THREE.TorusGeometry(1.43, 0.035, 8, 48);
  const hitGeometry = new THREE.SphereGeometry(1, 12, 8);
  sharedGeometries.add(fallbackSphereGeometry);
  sharedGeometries.add(fallbackAccentGeometry);
  sharedGeometries.add(selectionGeometry);
  sharedGeometries.add(pressureGeometry);
  sharedGeometries.add(arrivalGeometry);
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

    const arrivalRing = new THREE.Mesh(
      arrivalGeometry,
      makeOverlayMaterial(COLOR_UP, 0),
    );
    arrivalRing.name = `${node.id}__arrival_ring`;
    arrivalRing.scale.setScalar(visualRadius);
    arrivalRing.visible = false;
    nodeRoot.add(arrivalRing);

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
    const leader = document.createElement('span');
    leader.className = 'node-label-leader';
    leader.setAttribute('aria-hidden', 'true');
    Object.assign(leader.style, {
      position: 'absolute',
      display: 'none',
      height: '1px',
      opacity: '0.42',
      background: category.color,
      pointerEvents: 'none',
      transformOrigin: '0 50%',
    });
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'node-label';
    chip.dataset.nodeId = node.id;
    chip.dataset.hubScore = String(hubMetric.score100);
    chip.dataset.radiusScale = String(hubMetric.radiusScale);
    chip.dataset.modelStatus = 'fallback';
    chip.dataset.pressure = '0.000';
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
    wrap.append(leader, chip);
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
      accentBasePosition: fallbackAccent.position.clone(),
      accentBaseQuaternion: fallbackAccent.quaternion.clone(),
      accentBaseScale: fallbackAccent.scale.clone(),
    };
    const fallbackAccentBaseline = {
      position: fallbackAccent.position.clone(),
      quaternion: fallbackAccent.quaternion.clone(),
      scale: fallbackAccent.scale.clone(),
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
      arrivalRing,
      leverRing,
      hitProxy,
      labelAnchor,
      chip,
      leader,
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
      fallbackAccentBaseline,
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
    applyMaterialState(
      record,
      record.chip.classList.contains('dimmed'),
      record.chip.classList.contains('selected'),
    );
  }

  function disposeSourceMaterial(material) {
    for (const item of materialList(material)) {
      if (ownedMaterials.has(item) || sourceMaterialsDisposed.has(item)) continue;
      sourceMaterialsDisposed.add(item);
      item.dispose();
    }
  }

  function resetAccentBaseline(record) {
    record.motionState.accentBasePosition.copy(record.accentRoot.position);
    record.motionState.accentBaseQuaternion.copy(record.accentRoot.quaternion);
    record.motionState.accentBaseScale.copy(record.accentRoot.scale);
  }

  function restoreFallback(record) {
    if (record.loadedRoot) {
      disposeTree(record.loadedRoot, ownedMaterials);
      record.loadedRoot = null;
    }
    record.modelRoot.clear();
    record.fallbackRoot.visible = true;
    record.bodyMeshes = [record.fallbackBody];
    record.accentRoot = record.fallbackAccent;
    record.fallbackAccent.position.copy(record.fallbackAccentBaseline.position);
    record.fallbackAccent.quaternion.copy(record.fallbackAccentBaseline.quaternion);
    record.fallbackAccent.scale.copy(record.fallbackAccentBaseline.scale);
    record.modelStatus = 'fallback';
    record.chip.dataset.modelStatus = 'fallback';
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
    record.chip.dataset.modelStatus = 'ready';
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
    const ticket = loadCoordinator.begin();
    if (ticket === null) {
      return {
        status: normalizePublicLoadStatus('disposed'),
        loadedIds: [],
        fallbackIds: [...expectedIds],
        issues: ['disposed'],
      };
    }
    resetModels();
    modelIssues = [];
    if (!url) {
      loadCoordinator.succeed(ticket, () => {
        modelStatus = 'fallback';
        setDocumentStatus('fallback');
      });
      options.onModelStatusChange?.('fallback');
      return {
        status: 'fallback',
        loadedIds: [],
        fallbackIds: [...expectedIds],
        issues: [],
      };
    }

    modelStatus = 'loading';
    setDocumentStatus('loading');
    for (const record of records.values()) record.chip.dataset.modelStatus = 'pending';
    try {
      const loader = options.loader || new GLTFLoader(options.loadingManager);
      const gltf = await loader.loadAsync(url);
      if (!loadCoordinator.succeed(ticket)) {
        disposeTree(gltf.scene, ownedMaterials);
        const loadedIds = [...records.values()]
          .filter((record) => record.modelStatus === 'ready')
          .map((record) => record.id);
        return {
          status: normalizePublicLoadStatus(modelStatus),
          loadedIds,
          fallbackIds: expectedIds.filter((id) => !loadedIds.includes(id)),
          issues: ['stale-load'],
        };
      }

      const described = findModelRoots(gltf.scene, expectedIds).map(describeRoot);
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

      // Every canonical ID is expected in the production library. Invalid or absent
      // instruments still fail soft to their individual sphere fallback.
      disposeTree(gltf.scene, ownedMaterials);
      const fallbackIds = expectedIds.filter((id) => !loadedIds.includes(id));
      modelIssues = [...issueSummary(contract), ...modelIssues];
      modelStatus = loadedIds.length === expectedIds.length
        ? 'ready'
        : loadedIds.length
          ? 'partial'
          : 'fallback';
      setDocumentStatus(modelStatus);
      for (const record of records.values()) record.chip.dataset.modelStatus = record.modelStatus;
      warnIssues(modelIssues);
      options.onModelStatusChange?.(modelStatus);
      return {
        status: modelStatus,
        loadedIds,
        fallbackIds,
        issues: [...modelIssues],
      };
    } catch (error) {
      if (!loadCoordinator.fail(ticket)) {
        const loadedIds = [...records.values()]
          .filter((record) => record.modelStatus === 'ready')
          .map((record) => record.id);
        return {
          status: normalizePublicLoadStatus(modelStatus),
          loadedIds,
          fallbackIds: expectedIds.filter((id) => !loadedIds.includes(id)),
          issues: ['stale-load'],
        };
      }
      resetModels();
      const issue = error instanceof Error ? error.message : String(error);
      modelIssues = [issue];
      modelStatus = 'fallback';
      setDocumentStatus('fallback');
      warnIssues(modelIssues);
      options.onModelStatusChange?.('fallback');
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
    labelLayoutDirty = true;
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
    labelLayoutDirty = true;
  }

  function setPressures(map) {
    for (const record of records.values()) {
      const value = map ? (map.get(record.id) ?? 0) : 0;
      record.pressure = value;
      record.chip.dataset.pressure = Number(value).toFixed(3);
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
    labelLayoutDirty = true;
  }

  function pulseArrival(id, sign) {
    const record = records.get(id);
    if (!record || reducedMotion) return;
    record.motionState.arrivalAt = lastElapsed;
    record.motionState.arrivalSign = sign >= 0 ? 1 : -1;
    record.arrivalRing.material.color.copy(record.motionState.arrivalSign > 0 ? COLOR_UP : COLOR_DOWN);
    record.arrivalRing.material.opacity = 0.72;
    record.arrivalRing.scale.setScalar(record.visualRadius);
    record.arrivalRing.visible = true;
  }

  function setLang(nextLang) {
    lang = nextLang || 'ko';
    for (const record of records.values()) {
      record.chip.querySelector('.nm').textContent = record.node.name[lang] || record.node.name.ko;
    }
    labelLayoutDirty = true;
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
    labelLayoutDirty = true;
  }

  const worldPosition = new THREE.Vector3();
  const labelProjection = new THREE.Vector3();
  const nodeProjection = new THREE.Vector3();
  function updateHitProxy(record) {
    if (!camera || !renderer?.domElement) return;
    const height = renderer.domElement.clientHeight || window.innerHeight || 1;
    record.nodeRoot.getWorldPosition(worldPosition);
    const distance = camera.position.distanceTo(worldPosition);
    const worldPerPixel = (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2) * distance) / height;
    const minimumRadius = worldPerPixel * 22;
    const hitRadius = Math.max(record.visualRadius * 1.18, minimumRadius);
    record.hitProxy.scale.setScalar(hitRadius);
    record.chip.dataset.hitRadiusPx = (hitRadius / worldPerPixel).toFixed(2);
    record.chip.dataset.visualRadiusPx = (record.visualRadius / worldPerPixel).toFixed(2);
  }

  function updateAccentMotion(record, elapsed) {
    const state = record.motionState;
    const accent = record.accentRoot;
    accent.position.copy(state.accentBasePosition);
    accent.quaternion.copy(state.accentBaseQuaternion);
    accent.scale.copy(state.accentBaseScale);
    record.arrivalRing.visible = false;
    record.arrivalRing.material.opacity = 0;
    record.arrivalRing.scale.setScalar(record.visualRadius);
    if (reducedMotion) return;

    let signature = null;
    let signatureAxis = 'z';
    let signatureAmount = 0;
    let signatureWave = 0;
    if (state.selectedAt !== null) {
      const requestedDuration = Number(record.loadedRoot?.children[0]?.userData?.econ_duration) || 0.28;
      const duration = Math.max(MIN_SIGNATURE_DURATION, Math.min(MAX_SIGNATURE_DURATION, requestedDuration));
      const t = (elapsed - state.selectedAt) / duration;
      if (t >= 1) {
        state.selectedAt = null;
      } else if (t >= 0) {
        const rootData = record.loadedRoot?.children[0]?.userData || {};
        signature = rootData.econ_signature || 'rotate';
        signatureAxis = rootData.econ_axis || 'z';
        signatureAmount = Number(rootData.econ_amount) || 0.16;
        signatureWave = Math.sin(Math.PI * t);
      }
    }
    let arrivalScale = 1;
    if (state.arrivalAt !== null) {
      const t = (elapsed - state.arrivalAt) / ARRIVAL_DURATION;
      if (t >= 1) {
        state.arrivalAt = null;
      } else if (t >= 0) {
        arrivalScale = 1 + Math.sin(Math.PI * t) * 0.08;
        record.arrivalRing.visible = true;
        record.arrivalRing.material.color.copy(state.arrivalSign > 0 ? COLOR_UP : COLOR_DOWN);
        record.arrivalRing.material.opacity = 0.72 * (1 - t);
        record.arrivalRing.scale.setScalar(record.visualRadius * (1 + 0.22 * t));
      }
    }
    if (!signature && arrivalScale === 1) return;

    const transform = evaluateSignatureTransform({
      position: state.accentBasePosition.toArray(),
      quaternion: state.accentBaseQuaternion.toArray(),
      scale: state.accentBaseScale.toArray(),
    }, {
      signature,
      axis: signatureAxis,
      amount: signatureAmount,
      wave: signatureWave,
      arrivalScale,
    });
    accent.position.fromArray(transform.position);
    accent.quaternion.fromArray(transform.quaternion);
    accent.scale.fromArray(transform.scale);
  }

  function elementObstacle(element, viewportRect, width, height) {
    if (!element || element.hidden) return null;
    const style = window.getComputedStyle(element);
    if (style.display === 'none' || style.visibility === 'hidden') return null;
    const rect = element.getBoundingClientRect();
    const obstacle = {
      left: Math.max(0, rect.left - viewportRect.left),
      top: Math.max(0, rect.top - viewportRect.top),
      right: Math.min(width, rect.right - viewportRect.left),
      bottom: Math.min(height, rect.bottom - viewportRect.top),
    };
    if (obstacle.right <= obstacle.left || obstacle.bottom <= obstacle.top) return null;
    return obstacle;
  }

  function labelPriority(record, hasValue) {
    if (record.chip.classList.contains('selected')) return 500;
    if (record.chip.classList.contains('hl')) return 400;
    if (hasValue) return 300;
    if (record.node.lever) return 200;
    return Number(record.hubMetric.score100) || 0;
  }

  function updateLabelLayout() {
    if (!camera || !renderer?.domElement || typeof document === 'undefined') return;
    const viewportRect = renderer.domElement.getBoundingClientRect();
    const width = renderer.domElement.clientWidth || viewportRect.width;
    const height = renderer.domElement.clientHeight || viewportRect.height;
    if (!(width > 0 && height > 0)) return;

    const obstacles = [
      elementObstacle(document.querySelector('.hud-top'), viewportRect, width, height),
      elementObstacle(document.getElementById('panel'), viewportRect, width, height),
      elementObstacle(document.getElementById('legend'), viewportRect, width, height),
      elementObstacle(document.getElementById('statusline'), viewportRect, width, height),
    ].filter(Boolean);
    const projections = new Map();
    const candidates = [];
    for (const record of records.values()) {
      record.labelAnchor.getWorldPosition(labelProjection).project(camera);
      const anchorX = (labelProjection.x * 0.5 + 0.5) * width;
      const anchorY = (-labelProjection.y * 0.5 + 0.5) * height;
      record.nodeRoot.getWorldPosition(nodeProjection).project(camera);
      const nodeX = (nodeProjection.x * 0.5 + 0.5) * width;
      const nodeY = (-nodeProjection.y * 0.5 + 0.5) * height;
      const nodeProjectable = nodeProjection.x >= -1 && nodeProjection.x <= 1
        && nodeProjection.y >= -1 && nodeProjection.y <= 1
        && nodeProjection.z >= -1 && nodeProjection.z <= 1;
      const bounds = record.chip.getBoundingClientRect();
      const labelWidth = record.chip.offsetWidth || bounds.width || 96;
      const labelHeight = record.chip.offsetHeight || bounds.height || 24;
      const hasValue = !!record.chip.querySelector('.lval')?.textContent?.trim();
      const priority = labelPriority(record, hasValue);
      const critical = priority >= 200;
      const selected = record.chip.classList.contains('selected');
      const preferredY = anchorY - labelHeight / 2 - LABEL_VERTICAL_OFFSET;
      const anchorOccluded = obstacles.some((obstacle) => (
        anchorX >= obstacle.left && anchorX <= obstacle.right
        && anchorY >= obstacle.top && anchorY <= obstacle.bottom
      ));
      record.chip.dataset.nodeScreenX = nodeX.toFixed(2);
      record.chip.dataset.nodeScreenY = nodeY.toFixed(2);
      record.chip.dataset.nodeAnchorOccluded = String(anchorOccluded);
      projections.set(record.id, {
        anchorX,
        anchorY,
        nodeX,
        nodeY,
        nodeProjectable,
        labelHeight,
        preferredX: anchorX,
        preferredY,
      });
      candidates.push({
        id: record.id,
        preferredX: anchorX,
        preferredY,
        width: labelWidth,
        height: labelHeight,
        priority,
        critical,
        maxDisplacement: selected
          ? LABEL_SELECTED_ASSOCIATION_CAP
          : critical
            ? LABEL_CRITICAL_DISPLACEMENT
            : LABEL_LOCAL_DISPLACEMENT,
        allowDistantFallback: selected,
        leaderThreshold: selected
          ? LABEL_SELECTED_LEADER_THRESHOLD
          : critical
            ? LABEL_LOCAL_DISPLACEMENT
            : Infinity,
        eligible: (!anchorOccluded || selected)
          && labelProjection.x >= -1 && labelProjection.x <= 1
          && labelProjection.y >= -1 && labelProjection.y <= 1
          && labelProjection.z >= -1 && labelProjection.z <= 1,
      });
    }

    const nodeCenterObstacles = [...projections.values()]
      .filter((projection) => projection.nodeProjectable)
      .map((projection) => ({
        left: projection.nodeX - NODE_CENTER_CLEARANCE,
        top: projection.nodeY - NODE_CENTER_CLEARANCE,
        right: projection.nodeX + NODE_CENTER_CLEARANCE,
        bottom: projection.nodeY + NODE_CENTER_CLEARANCE,
      }));
    const layout = layoutNodeLabels({
      viewport: { width, height, padding: LABEL_SCREEN_MARGIN },
      obstacles: [...obstacles, ...nodeCenterObstacles],
      candidates,
      gap: LABEL_SCREEN_GAP,
    });
    for (const placement of layout) {
      const record = records.get(placement.id);
      const projection = projections.get(placement.id);
      if (!record || !projection) continue;
      record.chip.style.visibility = placement.visible ? 'visible' : 'hidden';
      record.leader.style.display = 'none';
      record.chip.dataset.labelDisplacement = placement.visible
        ? placement.displacement.toFixed(2)
        : '';
      if (!placement.visible) continue;
      const dx = placement.x - projection.anchorX;
      const initialCenterY = projection.anchorY - projection.labelHeight / 2 - LABEL_VERTICAL_OFFSET;
      const dy = placement.y - initialCenterY;
      record.chip.style.transform = `translate(calc(-50% + ${dx.toFixed(2)}px), `
        + `calc(-100% - ${LABEL_VERTICAL_OFFSET}px + ${dy.toFixed(2)}px))`;
      if (placement.showLeader) {
        const startX = projection.nodeX - projection.anchorX;
        const startY = projection.nodeY - projection.anchorY;
        const endX = placement.x - projection.anchorX;
        const endY = placement.y - projection.anchorY;
        const lineX = endX - startX;
        const lineY = endY - startY;
        record.leader.style.display = 'block';
        record.leader.style.left = `${startX.toFixed(2)}px`;
        record.leader.style.top = `${startY.toFixed(2)}px`;
        record.leader.style.width = `${Math.hypot(lineX, lineY).toFixed(2)}px`;
        record.leader.style.transform = `rotate(${Math.atan2(lineY, lineX).toFixed(5)}rad)`;
      }
    }
  }

  function update(elapsed) {
    lastElapsed = Number.isFinite(elapsed) ? elapsed : lastElapsed;
    const delta = Math.max(0, Math.min(0.05, lastElapsed - previousElapsed));
    previousElapsed = lastElapsed;
    const smoothing = reducedMotion ? 1 : 1 - Math.exp(-delta * HOVER_RESPONSE_RATE);
    for (const record of records.values()) {
      const hover = record.motionState.hovered && !reducedMotion;
      record.modelRoot.rotation.x += ((hover ? HOVER_TILT_X : 0) - record.modelRoot.rotation.x) * smoothing;
      record.modelRoot.rotation.y += ((hover ? HOVER_TILT_Y : 0) - record.modelRoot.rotation.y) * smoothing;
      record.fallbackRoot.rotation.x += ((hover ? HOVER_TILT_X : 0) - record.fallbackRoot.rotation.x) * smoothing;
      record.fallbackRoot.rotation.y += ((hover ? HOVER_TILT_Y : 0) - record.fallbackRoot.rotation.y) * smoothing;
      updateAccentMotion(record, lastElapsed);
      updateHitProxy(record);
    }
    if (labelLayoutDirty || lastElapsed - lastLabelLayoutAt >= LABEL_LAYOUT_INTERVAL) {
      updateLabelLayout();
      lastLabelLayoutAt = lastElapsed;
      labelLayoutDirty = false;
    }
  }

  function setReducedMotion(value) {
    reducedMotion = !!value;
    if (!reducedMotion) return;
    for (const record of records.values()) {
      record.modelRoot.rotation.set(0, 0, 0);
      record.fallbackRoot.rotation.set(0, 0, 0);
      record.motionState.selectedAt = null;
      record.motionState.arrivalAt = null;
      record.accentRoot.position.copy(record.motionState.accentBasePosition);
      record.accentRoot.quaternion.copy(record.motionState.accentBaseQuaternion);
      record.accentRoot.scale.copy(record.motionState.accentBaseScale);
      record.arrivalRing.visible = false;
      record.arrivalRing.material.opacity = 0;
      record.arrivalRing.scale.setScalar(record.visualRadius);
    }
  }

  function getDiagnostics() {
    const loadedModelCount = [...records.values()].filter((record) => record.modelStatus === 'ready').length;
    return {
      modelStatus: normalizePublicLoadStatus(modelStatus),
      loadedModelCount,
      fallbackCount: records.size - loadedModelCount,
      calls: renderer?.info?.render?.calls ?? 0,
      triangles: renderer?.info?.render?.triangles ?? 0,
      issues: [...modelIssues],
      anchorReady: records.get(MODEL_LOAD_ANCHOR_ID)?.modelStatus === 'ready',
    };
  }

  function getNodeModelStatus(id) {
    if (modelStatus === 'loading') return null;
    const record = records.get(id);
    return record ? record.modelStatus : null;
  }

  function dispose() {
    if (disposed) return;
    disposed = true;
    loadCoordinator.dispose();
    for (const record of records.values()) {
      record.chip.removeEventListener('click', record.labelClick);
      record.labelObject.element.remove();
      if (record.loadedRoot) disposeTree(record.loadedRoot, ownedMaterials);
      record.nodeRoot.removeFromParent();
    }
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
    getNodeModelStatus,
    dispose,
    setReducedMotion,
  };
}
