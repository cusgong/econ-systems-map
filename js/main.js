// Boot: data -> graph -> scene -> ui -> i18n. Global error surface + loading gate.

import { CATEGORIES, LAYERS, NODES, SIM_LEVERS, SIM_PRESETS } from '../data/nodes.js';
import { EDGES } from '../data/edges.js';
import { CASES } from '../data/cases.js';
import { LOOPS } from '../data/loops.js';
import { DESCS } from '../data/descs.js';
import { SITUATION } from '../data/situation.js';
import { UI_DICT_EN, UI_META } from '../data/strings.js';
import { buildGraph } from './graph.js';
import { createScene } from './scene.js';
import { createUI } from './ui.js';

const APP_VERSION = 'v2.0.0';

let fatalShown = false;
function showFatal() {
  if (fatalShown) return;
  fatalShown = true;
  const f = document.getElementById('fatal');
  f?.classList.add('show');
  document.getElementById('loading')?.classList.add('gone');
  f?.querySelector('.btn')?.focus();
}
// Only a failure during boot bricks the UI; a stray post-boot error is logged,
// not escalated over a working screen.
window.addEventListener('error', (e) => {
  console.error('[macroscope]', e.error || e.message);
  if (!window.__msBooted) showFatal();
});
window.addEventListener('unhandledrejection', (e) => {
  console.error('[macroscope]', e.reason);
  if (!window.__msBooted) showFatal();
});

function initialReducedMotion() {
  try {
    const p = JSON.parse(localStorage.getItem('macroscope.prefs') || 'null');
    if (p && p.v === 1) {
      if (p.motion === 'off') return true;
      if (p.motion === 'on') return false;
    }
  } catch { /* fall through */ }
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function hideLoading() {
  document.getElementById('loading')?.classList.add('gone');
}

function boot() {
  document.getElementById('app-version').textContent = APP_VERSION;

  const graph = buildGraph(NODES, EDGES);

  let uiRef = null;
  let scene = null;
  try {
    scene = createScene({
      container: document.getElementById('stage'),
      labelContainer: document.getElementById('labels'),
      graph,
      categories: CATEGORIES,
      layers: LAYERS,
      onSelect: (id) => uiRef && uiRef.selectNode(id),
      onLeverDrag: (id, v) => uiRef && uiRef.onLeverDrag(id, v),
      onLeverDragEnd: (id, v) => uiRef && uiRef.onLeverDragEnd(id, v),
      reducedMotion: initialReducedMotion(),
      lang: 'ko',
      onFirstFrame: hideLoading,
    });
  } catch (err) {
    console.error('[macroscope] WebGL unavailable, falling back to list mode.', err);
    scene = null;
  }

  const ui = createUI({
    graph, scene,
    categories: CATEGORIES,
    cases: CASES, loops: LOOPS, descs: DESCS, situation: SITUATION,
    simLevers: SIM_LEVERS, simPresets: SIM_PRESETS,
    version: APP_VERSION,
  });
  uiRef = ui;

  ui.wire();
  ui.renderLegend();
  ui.integrityReport();

  window.I18n.init({
    langs: ['ko', 'en'],
    default: 'ko',
    storageKey: 'macroscope.lang',
    dict: { en: UI_DICT_EN },
    meta: UI_META,
    onApply: () => {
      const m = UI_META[window.I18n.lang];
      if (m && m.title) document.title = m.title;
      ui.onLangChange();
    },
  });

  if (!scene) {
    hideLoading();
    ui.enableListMode();
  } else {
    // safety net: if first frame somehow never fires
    setTimeout(hideLoading, 4000);
  }

  ui.initFromHash(); // deep link: #/v/<id>, #/case/<id>/<phase>, #/loop/<id>, #/sim/...
  ui.maybeShowOnboarding();
  window.__msBooted = true;
}

try {
  boot();
} catch (err) {
  console.error('[macroscope] boot failed', err);
  showFatal();
}
