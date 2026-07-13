// UI controller: panel rendering per mode, simulator, case playback, loops,
// legend, onboarding, sources, prefs. Talks to scene via a narrow API.

import { ripple, propagate, pathDirections, lagBucket, loopEdges, loopNetSign, edgeKey } from './graph.js';
import { hubBandFor, radiusScaleFor } from './hub-metrics.js';
import { focusIdsForViewport, shouldReserveMapViewport } from './viewport-policy.js';

const $ = (sel) => document.querySelector(sel);
const t = (s) => window.I18n.t(s);
const L = (obj) => (obj ? (obj[window.I18n.lang] ?? obj.ko ?? '') : '');

const PHASE_SHORT = {
  cause: { ko: '원인', en: 'Cause' },
  spread: { ko: '확산', en: 'Spread' },
  policy: { ko: '정책 대응', en: 'Policy' },
  psychology: { ko: '시장 심리', en: 'Psychology' },
  outcome: { ko: '결과', en: 'Outcome' },
};
const LAG_LABELS = [
  { ko: '즉시~1개월', en: 'within a month' },
  { ko: '1~6개월', en: '1-6 months' },
  { ko: '6~18개월', en: '6-18 months' },
  { ko: '18개월+', en: '18+ months' },
];
const LAG_BUCKET_LABELS = [
  { ko: '단기 (~3개월)', en: 'short run (~3mo)' },
  { ko: '중기 (3~12개월)', en: 'medium run (3-12mo)' },
  { ko: '장기 (1년+)', en: 'long run (1yr+)' },
];
const CONF_LABELS = [null,
  { ko: '논쟁적', en: 'contested' },
  { ko: '일반적 견해', en: 'widely held' },
  { ko: '교과서 합의', en: 'textbook' },
];
const SOURCE_NAMES = {
  BOK: '한국은행 통화정책 파급경로', Mishkin: 'Mishkin, 화폐와 금융', Mankiw: 'Mankiw, 거시경제학',
  IMF: 'IMF', BIS: 'BIS', Dalio: 'Dalio, How the Economic Machine Works',
  Shiller: 'Shiller, 내러티브 경제학', Minsky: 'Minsky, 금융불안정성 가설', Empirical: '정형화된 실증 사실',
};

const PREFS_KEY = 'macroscope.prefs';
const HUB_BAND_KEYS = Object.freeze({ low: '낮음', medium: '중간', high: '높음' });

export function hubMetricPresentation(metric, modelStatus) {
  const hubScore = Number.isFinite(metric?.hubScore)
    ? Math.max(0, Math.min(1, metric.hubScore))
    : 0.5;
  const score100 = Number.isFinite(metric?.score100)
    ? Math.max(0, Math.min(100, Math.round(metric.score100)))
    : Math.round(hubScore * 100);
  const band = Object.hasOwn(HUB_BAND_KEYS, metric?.band)
    ? metric.band
    : hubBandFor(hubScore);
  return {
    score100,
    band,
    bandKey: HUB_BAND_KEYS[band],
    showFallback: modelStatus === 'fallback',
  };
}

export function hubLegendSamples() {
  return [0, 50, 100].map((score100) => ({
    score100,
    radiusScale: radiusScaleFor(score100 / 100),
  }));
}

export function createUI(deps) {
  const { graph, hubMetrics, scene, modelViewer, categories, cases, loops, descs, version, situation } = deps;
  const catById = new Map(categories.map((c) => [c.id, c]));
  const descById = new Map(descs.map((d) => [d.id, d.desc]));
  const simLevers = deps.simLevers;
  const simPresets = deps.simPresets;

  // ---------- prefs (versioned, defensive) ----------
  function loadPrefs() {
    try {
      const raw = localStorage.getItem(PREFS_KEY);
      if (!raw) return { v: 1 };
      const p = JSON.parse(raw);
      return (p && p.v === 1) ? p : { v: 1 };
    } catch { return { v: 1 }; }
  }
  function savePrefs() {
    try { localStorage.setItem(PREFS_KEY, JSON.stringify(prefs)); } catch { /* in-memory only */ }
  }
  const prefs = loadPrefs();

  const mediaReduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  function reducedMotion() {
    if (prefs.motion === 'off') return true;
    if (prefs.motion === 'on') return false;
    return mediaReduced.matches;
  }

  // ---------- state ----------
  const state = {
    mode: 'explore',
    selectedId: null,
    dir: 'down',          // 'down' effects | 'up' drivers
    assumeSign: 1,        // explore assumption: selected variable rises(+1)/falls(-1)
    depth: 2,
    simShocks: Object.fromEntries(simLevers.map((l) => [l.id, 0])),
    caseId: null,
    phaseIdx: 0,
    autoplay: false,
    autoplayTimer: null,
    loopId: null,
    nowThemeId: null,
    nowProjected: true,
    listMode: false,
  };

  const els = {
    panel: $('#panel'), body: $('#panel-body'), title: $('#panel-title'),
    toggle: $('#panel-toggle'), toast: $('#toast'), live: $('#sr-live'),
    legendBody: $('#legend-body'), legend: $('#legend'),
    status: $('#status-msg'),
  };

  // ---------- tiny helpers ----------
  function h(tag, attrs = {}, ...children) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === 'class') el.className = v;
      else if (k === 'html') el.innerHTML = v;
      else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
      else if (v !== null && v !== undefined) el.setAttribute(k, v);
    }
    for (const c of children) {
      if (c == null) continue;
      el.append(c.nodeType ? c : document.createTextNode(c));
    }
    return el;
  }
  let toastTimer = null;
  function toast(msg) {
    els.toast.textContent = msg;
    els.toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => els.toast.classList.remove('show'), 2600);
  }
  function announce(msg) { els.live.textContent = msg; }
  function nodeName(id) { const n = graph.nodeById.get(id); return n ? L(n.name) : id; }
  function strengthDots(s) { return '●'.repeat(s) + '○'.repeat(3 - s); }

  function chainEl(ids, dirs, navigable = false) {
    const wrap = h('div', { class: 'chain' });
    ids.forEach((id, i) => {
      if (i > 0) wrap.append(h('span', { class: 'arr', 'aria-hidden': 'true' }, '→'));
      if (navigable) {
        wrap.append(h('button', {
          class: 'chain-node',
          title: t('이 변수로 이동'),
          onclick: (ev) => { ev.stopPropagation(); selectNode(id); },
        }, nodeName(id)));
      } else {
        wrap.append(h('span', {}, nodeName(id)));
      }
      wrap.append(h('span', { class: dirs[i] > 0 ? 'd-up' : 'd-dn' }, dirs[i] > 0 ? '↑' : '↓'));
    });
    return wrap;
  }

  function edgeBadges(e, extra = []) {
    const meta = h('div', { class: 'meta' });
    meta.append(h('span', { class: 'badge ' + (e.sign > 0 ? 'sign-pos' : 'sign-neg') },
      e.sign > 0 ? t('같은 방향') : t('반대 방향')));
    meta.append(h('span', { class: 'badge', title: t('영향 강도') }, strengthDots(e.strength)));
    meta.append(h('span', { class: 'badge' }, '⏱︎ ' + L(LAG_LABELS[e.lag])));
    meta.append(h('span', { class: 'badge conf-' + e.confidence }, t('확실성') + ': ' + L(CONF_LABELS[e.confidence])));
    if (e.flip) meta.append(h('span', { class: 'badge flip' }, '⇄ ' + t('국면 반전')));
    meta.append(h('span', { class: 'badge' }, SOURCE_NAMES[e.source] ? (window.I18n.lang === 'ko' ? SOURCE_NAMES[e.source] : e.source) : e.source));
    for (const x of extra) meta.append(x);
    return meta;
  }

  // ---------- mode switching ----------
  // sim/cases/loops are contained views of Explore; their titles say so
  const PANEL_TITLES = { explore: 'EXPLORE', now: 'NOW', sim: 'EXPLORE · SIM', cases: 'EXPLORE · CASE', loops: 'EXPLORE · LOOP', ai: 'ASK AI' };

  function setMode(mode, opts = {}) {
    if (state.mode === mode && !opts.force) return;
    stopAutoplay();
    state.mode = mode;
    state.loopId = null;
    state.caseId = null;
    state.phaseIdx = 0;
    state.nowThemeId = null;
    // sim/cases/loops are sub-views OF explore now — they light the 탐색 tab.
    const tabMode = (mode === 'now' || mode === 'ai') ? mode : 'explore';
    document.querySelectorAll('.mode-tab').forEach((b) => {
      if (b.dataset.mode === tabMode) b.setAttribute('aria-current', 'true');
      else b.removeAttribute('aria-current');
    });
    els.title.textContent = PANEL_TITLES[mode];
    scene?.clearHighlight();
    scene?.setPressures(null);
    if (mode === 'sim') {
      applySimTints();
    } else if (mode === 'now') {
      state.nowProjected = true;
      applyNowTints();
      scene?.resetView();
    } else if (mode === 'explore' && state.selectedId) {
      applyExploreHighlight();
    } else {
      scene?.resetView();
    }
    renderPanel();
    expandPanelIfMobile(mode !== 'explore' || !!state.selectedId);
    // opts.quiet: caller immediately opens content (case/loop/theme/variable)
    // which pushes its own hash — skip this push so back-button history stays clean
    if (!opts.quiet) syncHash(true);
  }

  function renderPanel() {
    // preserve keyboard focus across the re-render (buttons carry data-fkey)
    const active = document.activeElement;
    const wasInBody = !!(active && active !== document.body && els.body.contains(active));
    const fkey = wasInBody ? active.getAttribute('data-fkey') : null;
    // AI chat keeps its scroll position (the conversation lives at the bottom)
    if (!(state.mode === 'ai' && chatLog.length)) els.body.scrollTop = 0;
    els.body.replaceChildren();
    if (state.listMode) {
      els.body.append(h('div', { class: 'card' }, h('p', {},
        t('이 기기에서는 3D를 사용할 수 없어 목록 모드로 표시합니다. 모든 설명은 아래 패널에서 그대로 볼 수 있습니다.'))));
    }
    if (state.mode === 'explore') renderExplore();
    else if (state.mode === 'now') renderNow();
    else if (state.mode === 'sim') renderSim();
    else if (state.mode === 'cases') renderCases();
    else if (state.mode === 'ai') renderAI();
    else renderLoops();
    if (fkey) {
      const back = els.body.querySelector('[data-fkey="' + fkey + '"]');
      if (back) back.focus();
      else els.body.focus({ preventScroll: true });
    } else if (wasInBody) {
      // keyboard user's focus would silently drop to <body>; anchor it on the panel
      els.body.focus({ preventScroll: true });
    }
  }

  // ---------- browsable card builders (shared by Explore home + sub-views) ----------
  function caseCardEl(c) {
    return h('button', { class: 'case-card', onclick: () => { setMode('cases', { quiet: true }); openCase(c.id); } },
      h('div', { class: 'cs-period' }, c.period),
      h('div', { class: 'cs-title' }, L(c.title)),
      h('div', { class: 'cs-sub' }, L(c.phases[0].title)),
    );
  }
  function loopCardEl(lp) {
    const cyc = lp.nodes.map(nodeName).join(' → ') + ' → ' + nodeName(lp.nodes[0]);
    return h('button', { class: 'case-card', onclick: () => { setMode('loops', { quiet: true }); openLoop(lp.id); } },
      h('div', { class: 'h-node' },
        h('span', { class: 'cs-title' }, L(lp.name)),
        h('span', { class: 'loop-type ' + lp.type }, lp.type === 'reinforcing' ? t('강화 루프') + ' ⟳' : t('균형 루프') + ' ⇄'),
      ),
      h('div', { class: 'loop-cycle' }, cyc),
    );
  }

  // ---------- explore ----------
  function selectNode(id) {
    if (state.mode === 'sim') {
      if (id) highlightSimNode(id);
      return;
    }
    if (state.mode !== 'explore') return;
    if (!id && !state.selectedId) return; // nothing to deselect; keep viewpoint
    state.selectedId = id;
    if (!id) {
      scene?.clearHighlight();
      scene?.resetView();
      renderPanel();
      syncHash(true);
      return;
    }
    applyExploreHighlight();
    renderPanel();
    expandPanelIfMobile(true);
    const r = ripple(graph, id, state.dir, 3);
    const counts = [0, 0, 0];
    for (const info of r.nodes.values()) counts[info.order - 1]++;
    announce(nodeName(id) + ' — ' + t('1차') + ' ' + counts[0] + ', ' + t('2차') + ' ' + counts[1] + ', ' + t('3차') + ' ' + counts[2]);
    syncHash(true);
  }

  function applyExploreHighlight() {
    if (!state.selectedId || !scene) return;
    const r = ripple(graph, state.selectedId, state.dir, state.depth);
    const nodeOrders = new Map([...r.nodes].map(([id, info]) => [id, info.order]));
    scene.setHighlight({ nodeOrders, edgeOrders: r.edgeOrders, selectedId: state.selectedId });
    const contextualIds = [state.selectedId, ...[...r.nodes]
      .filter(([, i]) => i.order <= Math.min(2, state.depth))
      .map(([id]) => id)];
    scene.focusNodes(focusIdsForViewport(state.selectedId, contextualIds, window.innerWidth));
  }

  function renderExplore() {
    const b = els.body;
    if (!state.selectedId) {
      b.append(h('div', { class: 'card' },
        h('h3', {}, t('변수를 선택하세요')),
        h('p', {}, t('지도의 점 하나가 변수 하나입니다. 변수를 클릭하면 그 변화가 어디로 번져가는지 1차 → 2차 → 3차 파급 경로가 켜집니다.')),
      ));

      // section quick-nav: the home stacks ~3 screens of content — let people jump
      const jump = (sel) => els.body.querySelector(sel)?.scrollIntoView({
        behavior: reducedMotion() ? 'auto' : 'smooth', block: 'start',
      });
      b.append(h('div', { class: 'quick-nav', role: 'navigation', 'aria-label': t('섹션 이동') },
        h('button', { class: 'preset-btn', onclick: () => jump('#sec-sim') }, t('시뮬레이터')),
        h('button', { class: 'preset-btn', onclick: () => jump('#sec-cases') }, t('역사 사례')),
        h('button', { class: 'preset-btn', onclick: () => jump('#sec-loops') }, t('피드백 루프')),
        h('button', { class: 'preset-btn', onclick: () => jump('#sec-cats') }, t('변수 분류')),
        h('button', { class: 'preset-btn', onclick: openSearch }, '⌕ ' + t('검색')),
      ));

      const quick = h('div', { class: 'card' }, h('h3', {}, t('추천 시작점')));
      const row = h('div', { class: 'presets' });
      for (const id of ['policy_rate', 'oil', 'fx', 'risk_sentiment']) {
        const nd = graph.nodeById.get(id);
        row.append(h('button', { class: 'preset-btn', onclick: () => selectNode(id) },
          h('span', { class: 'si-dot', style: 'background:' + catById.get(nd.cat).color }), nodeName(id)));
      }
      quick.append(row);
      quick.append(h('p', {}, t('드래그로 회전, 휠이나 두 손가락으로 확대·축소할 수 있습니다.')));
      b.append(quick);

      // scenario simulator — a view within Explore, not a separate tab
      b.append(h('div', { class: 'card', id: 'sec-sim' },
        h('h3', {}, t('시나리오 시뮬레이터')),
        h('p', {}, t('금리·유가·환율 레버를 움직여 파급을 실험합니다. 지도에서 고리 달린 레버 노드를 위아래로 잡아끌어도 됩니다.')),
        h('div', { class: 'presets', style: 'margin-top:8px' },
          h('button', { class: 'btn primary sm', 'data-fkey': 'open-sim', onclick: () => setMode('sim') }, t('시뮬레이터 열기'))),
      ));

      // history cases — browse and play on the map, in place
      b.append(h('div', { class: 'order-h', id: 'sec-cases' }, h('span', { class: 'n' }, '▶︎'), t('역사 사례')));
      for (const c of cases) b.append(caseCardEl(c));

      // feedback loops — the heart of systems thinking, browsable here
      b.append(h('div', { class: 'order-h', id: 'sec-loops' }, h('span', { class: 'n' }, '⟳'), t('피드백 루프')));
      for (const lp of loops) b.append(loopCardEl(lp));

      const catCard = h('div', { class: 'card', id: 'sec-cats' }, h('h3', {}, t('변수 분류')));
      for (const c of categories) {
        const ids = graph.nodes.filter((n) => n.cat === c.id);
        const rowEl = h('div', { class: 'presets' });
        rowEl.append(h('span', { class: 'badge', style: 'color:' + c.color + ';border-color:' + c.color + '55' }, L(c.name)));
        for (const n of ids) rowEl.append(h('button', { class: 'preset-btn', onclick: () => selectNode(n.id) }, L(n.name)));
        catCard.append(rowEl);
      }
      b.append(catCard);
      return;
    }

    const n = graph.nodeById.get(state.selectedId);
    const cat = catById.get(n.cat);
    const nodeModelStatus = scene?.getNodeModelStatus?.(n.id) ?? null;
    const hub = hubMetricPresentation(hubMetrics?.get?.(n.id), nodeModelStatus);
    b.append(h('button', { class: 'btn sm', 'data-fkey': 'back-hub', onclick: () => selectNode(null) }, '← ' + t('탐색')));
    const head = h('div', { class: 'h-node', style: 'margin-top:10px' },
      h('span', { class: 'nm' }, L(n.name)),
      h('span', { class: 'cat-chip', style: 'color:' + cat.color }, L(cat.name)),
    );
    if (n.lever) head.append(h('span', { class: 'badge', style: 'color:var(--cy)' }, t('시뮬레이터 레버')));
    head.append(h('div', {
      class: 'hub-summary',
      'data-hub-score': String(hub.score100),
      'data-hub-band': hub.band,
      'data-model-status': nodeModelStatus || 'pending',
    },
    h('span', { class: 'hub-score' }, `${t('인과 허브')} ${hub.score100}/100`),
    h('span', { class: `hub-band hub-band-${hub.band}` }, t(hub.bandKey))));
    b.append(head);
    // turntable inspector: the map only shows one side, so let the panel show the
    // whole instrument, auto-rotating. Attached after the panel lands in the DOM;
    // only rebuilds the model when the selected id changes (spin survives re-renders).
    if (modelViewer && !state.listMode) {
      const mv = h('div', { class: 'model-viewer', role: 'img',
        style: '--mv-accent:' + cat.color,
        'aria-label': L(n.name) + ' ' + t('3D 계기 모형') });
      b.append(mv);
      requestAnimationFrame(() => {
        if (mv.isConnected) {
          modelViewer.attach(mv, n.id, { color: cat.color, cat: n.cat, reducedMotion: reducedMotion() });
        }
      });
    }
    const d = descById.get(n.id);
    if (d) b.append(h('p', { class: 'desc' }, L(d)));
    if (hub.showFallback) {
      b.append(h('p', { class: 'model-fallback-note' },
        t('모델을 불러오지 못해 기본 형상으로 표시합니다')));
    }
    // the signature interaction, hinted at the moment it is relevant
    if (n.lever && !state.listMode) {
      b.append(h('p', { class: 'rd-src' }, '⇅ ' + t('지도에서 이 노드를 위아래로 잡아끌면 즉석 충격을 줄 수 있습니다.')));
    }

    // NOW instrument strip: what this variable reads today (tap -> NOW board)
    const rd = situation.readings.find((r) => r.node === n.id);
    if (rd) {
      b.append(h('button', { class: 'now-strip', onclick: () => setMode('now'), title: t('지금 탭에서 전체 상황 보기') },
        h('span', { class: 'asof-chip' }, t('지금') + ' ' + L(rd.value) + ' ' + trendGlyph(rd.trend)),
        h('span', { class: 'ns-note' }, L(rd.note)),
      ));
    }

    // this variable's history & loops: cross-links so exploring flows into cases
    const relLoops = loops.filter((lp) => lp.nodes.includes(n.id));
    const relCases = cases.filter((c) => c.phases.some((p) =>
      p.focusNodes.includes(n.id) || p.activeEdges.some(([f, tt]) => f === n.id || tt === n.id)));
    if (relLoops.length || relCases.length) {
      const row = h('div', { class: 'presets rel-row' });
      for (const lp of relLoops) {
        row.append(h('button', { class: 'preset-btn', onclick: () => { setMode('loops', { quiet: true }); openLoop(lp.id); } }, '⟳ ' + L(lp.name)));
      }
      for (const c of relCases) {
        row.append(h('button', { class: 'preset-btn', onclick: () => { setMode('cases', { quiet: true }); openCase(c.id); } }, '▶︎ ' + L(c.title)));
      }
      b.append(row);
    }

    // direction + assumption + depth controls
    const segDir = h('div', { class: 'seg', role: 'group', 'aria-label': t('탐색 방향') },
      h('button', { 'data-fkey': 'dir-down', 'aria-pressed': String(state.dir === 'down'), onclick: () => { state.dir = 'down'; applyExploreHighlight(); renderPanel(); } }, t('영향 보기') + ' →'),
      h('button', { 'data-fkey': 'dir-up', 'aria-pressed': String(state.dir === 'up'), onclick: () => { state.dir = 'up'; applyExploreHighlight(); renderPanel(); } }, '← ' + t('원인 보기')),
    );
    const segSign = h('div', { class: 'seg', role: 'group', 'aria-label': t('가정') },
      h('button', { 'data-fkey': 'sign-up', 'aria-pressed': String(state.assumeSign === 1), onclick: () => { state.assumeSign = 1; renderPanel(); } }, t('올랐을 때') + ' ↑'),
      h('button', { 'data-fkey': 'sign-down', 'aria-pressed': String(state.assumeSign === -1), onclick: () => { state.assumeSign = -1; renderPanel(); } }, t('내렸을 때') + ' ↓'),
    );
    const segDepth = h('div', { class: 'seg', role: 'group', 'aria-label': t('파급 깊이') });
    [1, 2, 3].forEach((dd) => {
      segDepth.append(h('button', {
        'data-fkey': 'depth-' + dd,
        'aria-pressed': String(state.depth === dd),
        onclick: () => { state.depth = dd; applyExploreHighlight(); renderPanel(); },
      }, t(dd + '차까지')));
    });
    b.append(h('div', {}, segDir, ' ', segSign, ' ', segDepth));

    const r = ripple(graph, n.id, state.dir, state.depth);
    const byOrder = [[], [], []];
    for (const [id, info] of r.nodes) byOrder[info.order - 1].push({ id, info });

    const orderTitleDown = [t('1차 · 직접 효과'), t('2차 · 한 다리 건너'), t('3차 · 두 다리 건너')];
    const orderTitleUp = [t('1차 · 직접 원인'), t('2차 · 상류 원인'), t('3차 · 더 먼 원인')];

    byOrder.forEach((list, oi) => {
      if (!list.length) return;
      b.append(h('div', { class: 'order-h' }, h('span', { class: 'n' }, String(oi + 1)), (state.dir === 'down' ? orderTitleDown : orderTitleUp)[oi]));
      for (const { id, info } of list) {
        b.append(effectRow(n.id, id, info));
      }
    });
    if (![...r.nodes.keys()].length) {
      b.append(h('div', { class: 'card' }, h('p', {}, t('이 방향으로 연결된 경로가 없습니다.'))));
    }
  }

  function effectRow(startId, id, info) {
    // display path always oriented cause -> effect
    let ids = info.path, edges = info.edges;
    if (state.dir === 'up') {
      ids = [...info.path].reverse();
      edges = [...info.edges].reverse();
    }
    // The rise/fall toggle always refers to the SELECTED variable. In effects
    // mode it is the chain's first node; in drivers mode it is the last, so
    // anchor the initial sign such that the chain ends at assumeSign.
    let initial = state.assumeSign;
    if (state.dir === 'up') {
      const prod = edges.reduce((s, e) => s * e.sign, 1);
      initial = state.assumeSign * prod;
    }
    const dirs = pathDirections(initial, edges);
    const lastEdge = edges[edges.length - 1];
    // a plain container (the chain inside holds real buttons, so no role=button);
    // keyboard expand/collapse lives on a dedicated toggle button
    const row = h('div', { class: 'fx-row' });
    const tog = h('button', {
      class: 'fx-toggle', 'aria-expanded': 'false',
      'aria-label': nodeName(id) + ' — ' + t('경로 상세'),
    }, '▾');
    row.append(tog);
    row.append(chainEl(ids, dirs, true));
    row.append(h('div', { class: 'mech' }, L(lastEdge.mech)));
    const noteEl = lastEdge.note ? h('div', { class: 'mech', style: 'color:var(--warn)' }, '※ ' + L(lastEdge.note)) : null;
    if (noteEl) noteEl.style.display = 'none';
    const flipEl = lastEdge.flip
      ? h('div', { class: 'mech', style: 'color:#ffdf8e' }, '⇄ ' + t('국면 반전') + ': ' + L(lastEdge.flip))
      : null;
    if (flipEl) flipEl.style.display = 'none';
    row.append(edgeBadges(lastEdge));
    if (noteEl) row.append(noteEl);
    if (flipEl) row.append(flipEl);
    row.addEventListener('click', () => {
      const expanded = row.classList.contains('open');
      document.querySelectorAll('.fx-row.open').forEach((x) => {
        x.classList.remove('open');
        x.querySelector('.fx-toggle')?.setAttribute('aria-expanded', 'false');
      });
      row.classList.toggle('open', !expanded);
      tog.setAttribute('aria-expanded', String(!expanded));
      if (noteEl) noteEl.style.display = expanded ? 'none' : '';
      if (flipEl) flipEl.style.display = expanded ? 'none' : '';
      // highlight just this path
      const nodeOrders = new Map(info.path.map((pid, i) => [pid, Math.max(1, i)]));
      const edgeOrders = new Map(info.edges.map((e, i) => [edgeKey(e), i + 1]));
      scene?.setHighlight({ nodeOrders, edgeOrders, selectedId: startId });
      scene?.focusNodes(info.path);
    });
    return row;
  }

  // ---------- simulator ----------
  let simResults = [];

  function applySimTints() {
    const shocksActive = Object.values(state.simShocks).some((v) => v !== 0);
    if (!shocksActive) { scene?.setPressures(null); scene?.clearHighlight(); simResults = []; return; }
    simResults = propagate(graph, state.simShocks);
    if (!scene) return;
    scene.clearHighlight(); // a shock change invalidates any dominant-path highlight
    const tint = new Map();
    for (const [id, v] of Object.entries(state.simShocks)) if (v) tint.set(id, v);
    for (const r of simResults) tint.set(r.id, r.value);
    scene.setPressures(tint);
  }

  function highlightSimNode(id) {
    const r = simResults.find((x) => x.id === id);
    if (!r || !scene) return;
    const nodeOrders = new Map(r.dominant.path.map((pid, i) => [pid, Math.max(1, i)]));
    const edgeOrders = new Map(r.dominant.edges.map((e, i) => [edgeKey(e), i + 1]));
    scene.setHighlight({ nodeOrders, edgeOrders, selectedId: r.dominant.path[0] });
    scene.focusNodes(r.dominant.path);
  }

  function renderSim() {
    const b = els.body;
    b.append(h('button', { class: 'btn sm', onclick: () => setMode('explore') }, '← ' + t('탐색')));
    b.append(h('div', { class: 'card', style: 'margin-top:10px' },
      h('h3', {}, t('시나리오 시뮬레이터')),
      h('p', {}, t('레버를 움직이면 충격이 연쇄 경로를 타고 번지는 모습을 봅니다. 숫자는 예측이 아니라 방향과 상대적 세기입니다.')),
    ));

    const presetRow = h('div', { class: 'presets' });
    for (const p of simPresets) {
      presetRow.append(h('button', { class: 'preset-btn', 'data-fkey': 'preset-' + p.id, onclick: () => {
        for (const k of Object.keys(state.simShocks)) state.simShocks[k] = 0;
        for (const [k, v] of Object.entries(p.shocks)) state.simShocks[k] = v;
        applySimTints(); renderPanel();
        announce(L(p.name) + ' ' + t('프리셋 적용'));
        syncHash(false);
      } }, L(p.name)));
    }
    presetRow.append(h('button', { class: 'preset-btn', 'data-fkey': 'preset-reset', onclick: () => {
      for (const k of Object.keys(state.simShocks)) state.simShocks[k] = 0;
      applySimTints(); renderPanel();
      syncHash(false);
    } }, t('초기화')));
    b.append(presetRow);

    for (const lever of simLevers) {
      const val = state.simShocks[lever.id];
      const out = h('output', { for: 'lv-' + lever.id }, fmtShock(val));
      const input = h('input', {
        type: 'range', id: 'lv-' + lever.id, min: '-100', max: '100', step: '25',
        value: String(Math.round(val * 100)),
        'aria-label': nodeName(lever.id),
      });
      input.addEventListener('input', () => {
        state.simShocks[lever.id] = Number(input.value) / 100;
        out.textContent = fmtShock(state.simShocks[lever.id]);
        applySimTints();
        renderSimResults();
        syncHash(false);
      });
      b.append(h('div', { class: 'lever' },
        h('div', { class: 'lv-h' }, h('label', { for: 'lv-' + lever.id }, nodeName(lever.id)), out),
        input,
        h('div', { class: 'imp-sub' }, L(lever.hint)),
      ));
    }

    b.append(h('div', { id: 'sim-results' }));
    renderSimResults();
  }

  function fmtShock(v) {
    if (!v) return '0';
    return (v > 0 ? '+' : '−') + Math.round(Math.abs(v) * 100) + '%';
  }

  function renderSimResults() {
    const host = $('#sim-results');
    if (!host) return;
    host.replaceChildren();
    const shocksActive = Object.values(state.simShocks).some((v) => v !== 0);
    if (!shocksActive) {
      host.append(h('div', { class: 'card' }, h('p', {}, t('아직 충격이 없습니다. 레버를 움직이거나 프리셋을 눌러 보세요.'))));
      return;
    }
    // applySimTints already recomputed simResults for this shock set; reuse it
    host.append(h('div', { class: 'order-h' }, h('span', { class: 'n' }, '»'), t('예상 파급 (세기 순)')));
    const top = simResults.slice(0, 14);
    if (!top.length) {
      host.append(h('div', { class: 'card' }, h('p', {}, t('충격이 너무 약해 뚜렷한 파급이 없습니다.'))));
      return;
    }
    for (const r of top) {
      const pct = Math.round(Math.abs(r.value) * 100);
      const upDown = r.value > 0;
      const row = h('button', { class: 'imp-row', onclick: () => highlightSimNode(r.id) });
      row.append(h('div', { class: 'imp-top' },
        h('span', { class: 'nm' }, nodeName(r.id)),
        h('span', { class: 'val ' + (upDown ? 'up' : 'down') }, (upDown ? '▲ ' : '▼ ') + pct),
      ));
      const bar = h('div', { class: 'imp-bar' });
      const fill = h('i', { class: upDown ? 'up' : 'down' });
      fill.style.width = Math.min(50, pct / 2) + '%';
      bar.append(fill);
      row.append(bar);
      const sub = h('div', { class: 'imp-sub' });
      sub.append(h('span', {}, '⏱︎ ' + L(LAG_BUCKET_LABELS[lagBucket(r.dominant.lagM)])));
      if (r.conflict) sub.append(h('span', { class: 'badge conflict' }, t('경로 상충')));
      const dirs = pathDirections(state.simShocks[r.dominant.path[0]] ?? 1, r.dominant.edges);
      sub.append(h('span', {}, r.dominant.path.map((pid, i) => nodeName(pid) + (dirs[i] > 0 ? '↑' : '↓')).join(' → ')));
      row.append(sub);
      if (r.conflict) {
        row.append(h('div', { class: 'mech' }, t('올리는 경로와 내리는 경로가 동시에 작동합니다. 순효과는 조건에 따라 달라질 수 있습니다.')));
      }
      host.append(row);
    }
    host.append(h('div', { class: 'card' }, h('p', {},
      t('이 모형은 교과서 메커니즘을 단순화한 것입니다. 실제 경제는 초기 조건과 정책 대응에 따라 다르게 움직입니다.'),
      ' ', h('button', { class: 'btn sm', onclick: openSources }, t('출처와 한계')),
    )));
  }

  // ---------- cases ----------
  function renderCases() {
    const b = els.body;
    if (!state.caseId) {
      // reachable only via a #/cases deep link now; the browsable list lives on the Explore home
      b.append(h('button', { class: 'btn sm', onclick: () => setMode('explore') }, '← ' + t('탐색')));
      b.append(h('div', { class: 'card', style: 'margin-top:10px' },
        h('h3', {}, t('역사 사례 재생')),
        h('p', {}, t('과거의 큰 사건을 원인 → 확산 → 정책 대응 → 시장 심리 → 결과의 5단계로 지도 위에 재생합니다.')),
      ));
      for (const c of cases) b.append(caseCardEl(c));
      return;
    }
    const c = cases.find((x) => x.id === state.caseId);
    if (!c) { state.caseId = null; renderCases(); return; }
    const phase = c.phases[state.phaseIdx];

    b.append(h('button', { class: 'btn sm', onclick: () => { closeCase(); } }, '← ' + t('탐색')));
    b.append(h('div', { class: 'h-node', style: 'margin-top:10px' },
      h('span', { class: 'nm' }, L(c.title)),
      h('span', { class: 'badge' }, c.period),
    ));

    const stepper = h('div', { class: 'phase-stepper', role: 'group', 'aria-label': t('단계') });
    c.phases.forEach((p, i) => {
      const btn = h('button', { class: 'ps' + (i < state.phaseIdx ? ' done' : ''), 'data-fkey': 'phase-' + i, onclick: () => gotoPhase(i) }, L(PHASE_SHORT[p.key]));
      if (i === state.phaseIdx) btn.setAttribute('aria-current', 'step');
      stepper.append(btn);
    });
    b.append(stepper);

    b.append(h('div', { class: 'card' },
      h('h3', {}, (state.phaseIdx + 1) + '. ' + L(phase.title)),
      h('p', {}, L(phase.narration)),
    ));

    const nav = h('div', { class: 'case-nav' });
    nav.append(h('button', { class: 'btn', 'data-fkey': 'case-prev', disabled: state.phaseIdx === 0 ? '' : null, onclick: () => gotoPhase(state.phaseIdx - 1) }, '← ' + t('이전')));
    nav.append(h('button', { class: 'btn primary', 'data-fkey': 'case-next', onclick: () => {
      if (state.phaseIdx < c.phases.length - 1) gotoPhase(state.phaseIdx + 1);
      else { stopAutoplay(); }
    }, disabled: state.phaseIdx >= c.phases.length - 1 ? '' : null }, t('다음') + ' →'));
    const play = h('button', { class: 'btn', 'data-fkey': 'case-play', 'aria-pressed': String(state.autoplay), onclick: toggleAutoplay },
      state.autoplay ? '⏸︎ ' + t('일시정지') : '▶︎ ' + t('자동 재생'));
    nav.append(play);
    b.append(nav);

    const cmp = h('details', { class: 'acc', style: 'margin-top:12px' },
      h('summary', {}, t('지금과 비교하면?')),
      h('div', { class: 'acc-body' },
        h('p', {}, h('strong', {}, t('공통점') + ' · ')),
        h('p', {}, L(c.comparison.common)),
        h('p', { style: 'margin-top:8px' }, h('strong', {}, t('다른 점') + ' · ')),
        h('p', {}, L(c.comparison.differences)),
      ));
    b.append(cmp);

    const src = h('details', { class: 'acc' },
      h('summary', {}, t('출처')),
      h('div', { class: 'acc-body' }, h('ul', {}, ...c.sources.map((s) => h('li', {}, s)))));
    b.append(src);
  }

  function openCase(id) {
    state.caseId = id;
    state.phaseIdx = 0;
    renderPanel();
    applyPhase();
    expandPanelIfMobile(true);
    syncHash(true);
  }
  function closeCase() {
    stopAutoplay();
    state.caseId = null;
    // return to the Explore lens: to the variable you came from, or the home hub
    setMode('explore');
  }
  function gotoPhase(i) {
    const c = cases.find((x) => x.id === state.caseId);
    if (!c) return;
    state.phaseIdx = Math.max(0, Math.min(c.phases.length - 1, i));
    renderPanel();
    applyPhase();
    syncHash(false);
  }
  function applyPhase() {
    const c = cases.find((x) => x.id === state.caseId);
    if (!c || !scene) return;
    const phase = c.phases[state.phaseIdx];
    const nodeOrders = new Map(phase.focusNodes.map((id) => [id, 1]));
    const edgeOrders = new Map();
    phase.activeEdges.forEach(([f, tt], i) => {
      const key = f + '>' + tt;
      if (graph.byKey.has(key)) edgeOrders.set(key, Math.min(4, i + 1));
      const e = graph.byKey.get(key);
      if (e) { nodeOrders.set(f, nodeOrders.get(f) || 1); nodeOrders.set(tt, nodeOrders.get(tt) || 1); }
    });
    scene.setHighlight({ nodeOrders, edgeOrders, selectedId: null });
    scene.setPressures(new Map(Object.entries(phase.shocks || {})));
    scene.focusNodes(phase.focusNodes.length ? phase.focusNodes : [...nodeOrders.keys()]);
    announce(L(c.title) + ' — ' + L(PHASE_SHORT[phase.key]) + ': ' + L(phase.title));
  }
  function toggleAutoplay() {
    if (state.autoplay) { stopAutoplay(); renderPanel(); return; }
    state.autoplay = true;
    state.autoplayTimer = setInterval(() => {
      const c = cases.find((x) => x.id === state.caseId);
      if (!c) { stopAutoplay(); return; }
      if (state.phaseIdx >= c.phases.length - 1) { stopAutoplay(); renderPanel(); return; }
      gotoPhase(state.phaseIdx + 1);
    }, 7000);
    renderPanel();
  }
  function stopAutoplay() {
    state.autoplay = false;
    if (state.autoplayTimer) { clearInterval(state.autoplayTimer); state.autoplayTimer = null; }
  }

  // ---------- loops ----------
  function renderLoops() {
    const b = els.body;
    if (!state.loopId) {
      // reachable only via a #/loops deep link now; the browsable list lives on the Explore home
      b.append(h('button', { class: 'btn sm', onclick: () => setMode('explore') }, '← ' + t('탐색')));
      b.append(h('div', { class: 'card', style: 'margin-top:10px' },
        h('h3', {}, t('피드백 루프')),
        h('p', {}, t('시스템 사고의 핵심은 한 방향 화살표가 아니라 되먹임 고리입니다. 강화 루프는 눈덩이처럼 스스로 커지고, 균형 루프는 온도조절기처럼 되돌립니다.')),
      ));
      for (const lp of loops) b.append(loopCardEl(lp));
      return;
    }
    const lp = loops.find((x) => x.id === state.loopId);
    if (!lp) { state.loopId = null; renderLoops(); return; }
    b.append(h('button', { class: 'btn sm', onclick: closeLoop }, '← ' + t('탐색')));
    b.append(h('div', { class: 'h-node', style: 'margin-top:10px' },
      h('span', { class: 'nm' }, L(lp.name)),
      h('span', { class: 'loop-type ' + lp.type }, lp.type === 'reinforcing' ? t('강화 루프') + ' ⟳' : t('균형 루프') + ' ⇄'),
    ));
    b.append(h('div', { class: 'loop-cycle' }, lp.nodes.map(nodeName).join(' → ') + ' → ' + nodeName(lp.nodes[0])));
    b.append(h('div', { class: 'card', style: 'margin-top:10px' }, h('p', {}, L(lp.story))));
    b.append(h('div', { class: 'card' }, h('h3', {}, t('실제 사례')), h('p', {}, L(lp.example))));
    b.append(h('div', { class: 'card' }, h('p', {},
      lp.type === 'reinforcing'
        ? t('강화 루프: 한 바퀴 돌 때마다 같은 방향으로 커집니다. 부호를 곱하면 (+)가 됩니다.')
        : t('균형 루프: 한 바퀴 돌면 원래 방향을 되돌립니다. 부호를 곱하면 (−)가 됩니다.'))));
  }

  function closeLoop() {
    state.loopId = null;
    // return to the Explore lens (variable you came from, or home hub)
    setMode('explore');
  }

  function openLoop(id) {
    state.loopId = id;
    const lp = loops.find((x) => x.id === id);
    renderPanel();
    if (lp) announce(L(lp.name) + ' — ' + (lp.type === 'reinforcing' ? t('강화 루프') : t('균형 루프')));
    if (!lp || !scene) return;
    const edges = loopEdges(graph, lp.nodes);
    if (!edges) return;
    const nodeOrders = new Map(lp.nodes.map((nid) => [nid, 1]));
    const edgeOrders = new Map(edges.map((e, i) => [edgeKey(e), i + 1]));
    scene.setHighlight({ nodeOrders, edgeOrders, selectedId: null });
    scene.focusNodes(lp.nodes);
    expandPanelIfMobile(true);
    syncHash(true);
  }

  // ---------- legend ----------
  function renderLegend() {
    const lb = els.legendBody;
    lb.replaceChildren();
    const row = (el, txt) => h('div', { class: 'lg-row' }, el, h('span', {}, txt));
    // Category colors lead: node color is the first thing the map now says.
    lb.append(h('div', { class: 'lg-h' }, t('변수 분류')));
    const cats = h('div', { class: 'lg-cats' });
    for (const c of categories) {
      cats.append(h('div', { class: 'lg-row' }, h('span', { class: 'lg-dot', style: 'background:' + c.color }), h('span', {}, L(c.name))));
    }
    lb.append(cats);
    lb.append(h('div', { class: 'lg-h' }, t('선과 연결')));
    lb.append(row(h('span', { class: 'lg-line' }), t('같은 방향으로 민다 (+)')));
    lb.append(row(h('span', { class: 'lg-line neg' }), t('반대 방향으로 민다 (−)')));
    lb.append(row(h('span', { class: 'lg-line dashed' }), t('점선 = 확실성 낮음')));
    lb.append(row(h('span', {}, '✦'), t('흐르는 점 = 인과 방향, 점 개수 = 강도')));
    lb.append(row(h('span', { class: 'lg-line', style: 'border-color:#ffdf8e' }), t('금색 강조 = 국면 따라 방향 반전 가능')));
    lb.append(h('div', { class: 'lg-h' }, t('인과 허브')));
    const hubSamples = h('div', { class: 'hub-legend-samples', 'aria-label': t('인과 허브') });
    for (const sample of hubLegendSamples()) {
      hubSamples.append(h('div', {
        class: 'hub-legend-sample',
        'data-score': String(sample.score100),
      },
      h('span', {
        class: 'hub-legend-dot',
        style: `--hub-scale:${sample.radiusScale}`,
        'aria-hidden': 'true',
      }),
      h('span', {}, String(sample.score100))));
    }
    lb.append(hubSamples);
    lb.append(h('p', { class: 'hub-legend-help' }, t('강한 직·간접 경로, 최대 3단계')));
    lb.append(h('div', { class: 'lg-h' }, t('노드와 압력')));
    lb.append(row(h('span', {}, '◎'), t('고리 달린 노드 = 시뮬레이터 레버')));
    lb.append(row(h('span', { class: 'lg-dot', style: 'background:var(--up)' }), t('상승 압력')));
    lb.append(row(h('span', { class: 'lg-dot', style: 'background:var(--down)' }), t('하락 압력')));
    lb.append(h('div', { class: 'lg-h' }, t('공간과 조작')));
    lb.append(row(h('span', {}, '⇅'), t('레버 노드 위아래 드래그 = 즉석 충격')));
    lb.append(row(h('span', {}, '↕'), t('높이 = 심리·기대(위) ↔ 실물·원자재(아래)')));
    lb.append(row(h('span', {}, '⊙'), t('중심에서 멀수록 해외·글로벌 변수')));
  }

  // ---------- onboarding ----------
  const obSteps = () => [
    {
      title: t('연결로 경제 읽기'),
      body: t('점 하나가 변수(금리, 물가, 환율…)이고, 선은 인과관계입니다. 청록 선은 같은 방향, 주황 선은 반대 방향으로 밉니다. 위치에도 의미가 있습니다. 위층일수록 사람들의 마음(심리·기대)과 정책, 아래층일수록 실물과 원자재이고, 중심에서 멀수록 해외 변수입니다.'),
      svg: '<svg width="220" height="90" viewBox="0 0 220 90"><circle cx="30" cy="45" r="9" fill="#4fd8ff"/><circle cx="110" cy="25" r="9" fill="#ff7666"/><circle cx="190" cy="55" r="9" fill="#62d97e"/><path d="M39 42 Q75 20 101 25" stroke="#3bd6f0" stroke-width="2" fill="none"/><path d="M119 28 Q155 45 181 52" stroke="#ff9257" stroke-width="2" fill="none" stroke-dasharray="5 4"/></svg>',
    },
    {
      title: t('2차·3차 파급을 따라가기'),
      body: t('변수를 클릭하면 직접 효과(1차)만이 아니라 한 다리, 두 다리 건너의 파급(2차·3차)까지 경로가 차례로 켜집니다. 화살표 방향과 시차, 확실성을 함께 확인하세요.'),
      svg: `<svg width="220" height="90" viewBox="0 0 220 90"><circle cx="25" cy="45" r="10" fill="#4fd8ff"/><circle cx="95" cy="30" r="8" fill="#9d8cff" opacity=".9"/><circle cx="165" cy="55" r="7" fill="#62d97e" opacity=".8"/><path d="M35 42 L85 32" stroke="#7deeff" stroke-width="2.5"/><path d="M103 33 L156 52" stroke="#7deeff" stroke-width="1.8" opacity=".7"/><text x="52" y="22" fill="#aabfdd" font-size="10">${t('1차')}</text><text x="125" y="60" fill="#aabfdd" font-size="10">${t('2차')}</text></svg>`,
    },
    {
      title: t('한 곳에서: 탐색 · 지금 · AI'),
      rows: [
        { k: t('탐색'), v: t('변수를 고르면 관련 역사 사례·피드백 루프가 그 자리에서 열리고, 시뮬레이터도 지도를 벗어나지 않고 열립니다.') },
        { k: t('지금'), v: t('오늘의 경제 지표를 지도 위 색으로 비춥니다.') },
        { k: 'AI', v: t('지도를 아는 AI와 대화하면 답변의 근거 경로가 지도에 켜집니다.') },
        { k: t('레버'), v: t('고리 달린 레버 노드를 위아래로 잡아끌면 즉석 충격을 줍니다.') },
      ],
      svg: `<svg width="220" height="90" viewBox="0 0 220 90"><rect x="20" y="38" width="180" height="6" rx="3" fill="#1b2b4d"/><rect x="20" y="38" width="120" height="6" rx="3" fill="#54e0ff"/><circle cx="140" cy="41" r="9" fill="#eaf3ff"/><text x="20" y="70" fill="#aabfdd" font-size="10">${nodeName('policy_rate')} +75%</text></svg>`,
    },
    {
      title: t('읽는 법 요약'),
      body: t('선의 색 = 방향, 흐르는 점 = 인과의 흐름과 강도, 점선 = 확실성 낮음. 금색 선은 국면에 따라 방향이 뒤집힐 수 있는 관계입니다. 이 지도는 교과서 메커니즘의 단순화 모형이며 예측 도구가 아닙니다.')
        + ' ' + t('검색은 상단의 검색 버튼으로 열고, 경로 속 변수 이름을 클릭하면 그 변수로 바로 이동합니다.')
        + (window.matchMedia('(pointer: fine)').matches
          ? ' ' + t('단축키: Ctrl+K 또는 / 검색, Esc 닫기·선택 해제, ← → 사례 단계 이동.') : ''),
      svg: '<svg width="220" height="90" viewBox="0 0 220 90"><path d="M20 60 Q110 10 200 55" stroke="#3bd6f0" stroke-width="2" fill="none"/><circle cx="80" cy="38" r="3" fill="#7deeff"/><circle cx="120" cy="30" r="3" fill="#7deeff"/><circle cx="160" cy="38" r="3" fill="#7deeff"/><path d="M40 75 L180 75" stroke="#ffdf8e" stroke-width="2"/></svg>',
    },
  ];

  let obIdx = 0;
  function renderOnboarding() {
    const dlg = $('#dlg-onboarding');
    const body = $('#ob-body');
    const steps = obSteps();
    const s = steps[obIdx];
    body.replaceChildren(
      h('h2', { id: 'ob-title' }, s.title),
      h('div', { class: 'ob-steps' }, ...steps.map((_, i) => h('button', {
        class: 'ob-dot' + (i === obIdx ? ' on' : ''),
        'aria-label': t('단계') + ' ' + (i + 1),
        'aria-current': i === obIdx ? 'step' : null,
        onclick: () => { obIdx = i; renderOnboarding(); },
      }))),
      h('div', { class: 'ob-visual', html: s.svg }),
      s.rows
        ? h('div', { class: 'ob-rows' }, ...s.rows.map((r) => h('div', { class: 'obr' }, h('b', {}, r.k), h('span', {}, r.v))))
        : h('p', {}, s.body),
      h('div', { class: 'dlg-actions' },
        obIdx < steps.length - 1 ? h('button', { class: 'btn left', onclick: () => dlg.close() }, t('건너뛰기')) : null,
        obIdx > 0 ? h('button', { class: 'btn', onclick: () => { obIdx--; renderOnboarding(); } }, '← ' + t('이전')) : null,
        obIdx < steps.length - 1
          ? h('button', { class: 'btn primary', onclick: () => { obIdx++; renderOnboarding(); } }, t('다음') + ' →')
          : h('button', { class: 'btn primary', onclick: () => { dlg.close(); } }, t('시작하기')),
      ),
    );
    body.querySelector('.dlg-actions .btn.primary')?.focus();
  }
  function openOnboarding() {
    obIdx = 0;
    renderOnboarding();
    $('#dlg-onboarding').showModal();
  }

  // ---------- sources ----------
  function openSources() {
    const body = $('#sources-body');
    body.replaceChildren(
      h('h2', { id: 'src-title' }, t('출처와 한계')),
      h('h3', {}, t('메커니즘 출처')),
      h('ul', {},
        h('li', {}, t('한국은행, 통화정책 파급경로 (금리·자산가격·환율·기대 경로)')),
        h('li', {}, 'F. Mishkin, The Economics of Money, Banking and Financial Markets'),
        h('li', {}, 'N. G. Mankiw, Macroeconomics'),
        h('li', {}, 'R. Dalio, How the Economic Machine Works (2013)'),
        h('li', {}, 'R. Shiller, Narrative Economics (2019)'),
        h('li', {}, 'H. Minsky, The Financial Instability Hypothesis (1992)'),
        h('li', {}, t('IMF·BIS 공개 보고서 (자본이동, 신용 사이클)')),
      ),
      h('h3', {}, t('역사 사례 출처')),
      h('ul', {}, ...cases.flatMap((c) => c.sources.map((s) => h('li', {}, L(c.title) + ' — ' + s)))),
      h('h3', {}, t('이 지도의 한계')),
      h('ul', {},
        h('li', {}, t('교과서 메커니즘의 단순화 모형입니다. 강도·시차·확실성은 정성적 구간이지 측정치가 아닙니다.')),
        h('li', {}, t('실제 경제는 초기 조건, 기대, 정책 대응에 따라 같은 충격에도 다르게 반응합니다.')),
        h('li', {}, t('예측이나 투자 판단의 근거가 아니라, 연결을 보는 훈련 도구입니다.')),
      ),
      h('div', { class: 'dlg-actions' }, h('button', { class: 'btn primary', onclick: () => $('#dlg-sources').close() }, t('닫기'))),
    );
    $('#dlg-sources').showModal();
  }

  // ---------- NOW: situation board ----------
  function monthsSince(iso) {
    const then = new Date(iso + 'T00:00:00');
    if (Number.isNaN(then.getTime())) return 0;
    return (Date.now() - then.getTime()) / (1000 * 60 * 60 * 24 * 30.4);
  }
  function trendGlyph(tr) { return tr > 0 ? '▲' : tr < 0 ? '▼' : '→'; }
  function applyNowTints() {
    if (!scene) return;
    if (!state.nowProjected) { scene.setPressures(null); return; }
    const map = new Map();
    for (const r of situation.readings) {
      if (graph.nodeById.has(r.node) && r.trend) map.set(r.node, r.trend * 0.45);
    }
    scene.setPressures(map);
  }
  function openTheme(id) {
    const th = situation.themes.find((x) => x.id === id);
    if (!th) return;
    state.nowThemeId = id;
    renderPanel();
    announce(L(th.title));
    if (scene) {
      const nodeOrders = new Map(th.nodes.map((nid) => [nid, 1]));
      const edgeOrders = new Map();
      (th.edges || []).forEach(([f, tt], i) => {
        if (graph.byKey.has(f + '>' + tt)) edgeOrders.set(f + '>' + tt, Math.min(4, i + 1));
      });
      scene.setHighlight({ nodeOrders, edgeOrders, selectedId: null });
      scene.focusNodes(th.nodes);
    }
    expandPanelIfMobile(true);
    syncHash(true);
  }
  function closeTheme() {
    state.nowThemeId = null;
    scene?.clearHighlight();
    scene?.resetView();
    applyNowTints();
    renderPanel();
    syncHash(true);
  }
  function renderNow() {
    const b = els.body;
    if (state.nowThemeId) {
      const th = situation.themes.find((x) => x.id === state.nowThemeId);
      if (th) {
        b.append(h('button', { class: 'btn sm', onclick: closeTheme }, '← ' + t('지금 목록')));
        b.append(h('div', { class: 'h-node', style: 'margin-top:10px' }, h('span', { class: 'nm' }, L(th.title))));
        b.append(h('div', { class: 'card' }, h('p', {}, L(th.body))));
        const relRow = h('div', { class: 'presets' });
        if (th.relatedCase) {
          const c = cases.find((x) => x.id === th.relatedCase);
          if (c) relRow.append(h('button', { class: 'preset-btn', onclick: () => { setMode('cases', { quiet: true }); openCase(c.id); } }, t('닮은꼴 사례') + ': ' + L(c.title) + ' →'));
        }
        if (th.relatedLoop) {
          const lp = loops.find((x) => x.id === th.relatedLoop);
          if (lp) relRow.append(h('button', { class: 'preset-btn', onclick: () => { setMode('loops', { quiet: true }); openLoop(lp.id); } }, t('관련 루프') + ': ' + L(lp.name) + ' →'));
        }
        if (relRow.children.length) b.append(relRow);
        if (th.sources && th.sources.length) {
          b.append(h('details', { class: 'acc' }, h('summary', {}, t('출처')),
            h('div', { class: 'acc-body' }, h('ul', {}, ...th.sources.map((s) => h('li', {}, s))))));
        }
        return;
      }
      state.nowThemeId = null;
    }

    b.append(h('div', { class: 'card' },
      h('h3', {}, t('지금의 경제, 한눈에')),
      h('p', {}, t('아래 지표의 최근 방향(약 6개월)을 지도 위 색으로 비춥니다. 예측이 아니라, 오늘의 배치도입니다.')),
      h('div', { class: 'presets', style: 'margin-top:10px' },
        h('span', { class: 'asof-chip' },
          t('수치') + ' ' + (situation.readingsAsOf || situation.asOf) + ' · ' + t('해설') + ' ' + (situation.themesAsOf || situation.asOf) + (t('기준') ? ' ' + t('기준') : '')),
        h('button', {
          class: 'preset-btn', 'data-fkey': 'now-project', 'aria-pressed': String(state.nowProjected),
          onclick: () => { state.nowProjected = !state.nowProjected; applyNowTints(); renderPanel(); },
        }, state.nowProjected ? t('지도 비추기 끄기') : t('지도에 비추기')),
      ),
    ));

    const themeAge = monthsSince(situation.themesAsOf || situation.asOf);
    if (themeAge > 4) {
      b.append(h('div', { class: 'card stale-warn' },
        h('p', {}, t('흐름 해설이') + ' ' + Math.round(themeAge) + t('개월 전 것입니다. 그 사이의 사건은 반영되지 않았을 수 있습니다.'))));
    }
    const readingAge = monthsSince(situation.readingsAsOf || situation.asOf);
    if (readingAge > 1) {
      b.append(h('div', { class: 'card stale-warn' },
        h('p', {}, t('지표 수치의 자동 갱신이') + ' ' + Math.round(readingAge) + t('개월째 멈춰 있습니다. 각 출처에서 직접 확인하세요.'))));
    }

    b.append(h('div', { class: 'order-h' }, h('span', { class: 'n' }, '◉'), t('주요 지표')));
    for (const r of situation.readings) {
      const row = h('button', {
        class: 'reading-row',
        title: t('이 변수로 이동'),
        onclick: () => { setMode('explore', { quiet: true }); selectNode(r.node); },
      });
      row.append(h('span', { class: 'rd-name' }, nodeName(r.node)));
      row.append(h('span', { class: 'rd-value' }, L(r.value)));
      row.append(h('span', {
        class: 'rd-trend ' + (r.trend > 0 ? 'up' : r.trend < 0 ? 'down' : 'flat'),
        'aria-label': r.trend > 0 ? t('상승') : r.trend < 0 ? t('하락') : t('보합'),
      }, trendGlyph(r.trend)));
      if (r.note) row.append(h('span', { class: 'rd-note' }, L(r.note)));
      row.append(h('span', { class: 'rd-src' }, r.source + ' · ' + r.date));
      b.append(row);
    }

    b.append(h('div', { class: 'order-h' }, h('span', { class: 'n' }, '≋'), t('지금 주요 흐름')));
    for (const th of situation.themes) {
      const bodyStr = L(th.body);
      const preview = bodyStr.length > 84 ? bodyStr.slice(0, 84).replace(/\s+\S*$/, '') + '…' : bodyStr;
      b.append(h('button', { class: 'case-card', onclick: () => openTheme(th.id) },
        h('div', { class: 'cs-title' }, L(th.title)),
        h('div', { class: 'cs-sub' }, preview),
      ));
    }

    b.append(h('div', { class: 'card' }, h('p', {},
      t('지표 수치는 공식 통계에서 자동 갱신되고, 흐름 해설은 주간 검증 파이프라인이 갱신합니다. 각 항목에 출처와 기준일을 표기했습니다.'),
      ' ', h('button', { class: 'btn sm', onclick: openSources }, t('출처와 한계')))));
  }

  // ---------- lever drag-to-shock (grab a lever node, pull up/down) ----------
  function onLeverDrag(id, v) {
    if (!scene) return;
    const preview = { ...state.simShocks, [id]: v };
    const res = propagate(graph, preview);
    const tint = new Map();
    for (const [k, val] of Object.entries(preview)) if (val) tint.set(k, val);
    for (const r of res) tint.set(r.id, r.value);
    scene.setPressures(tint);
  }
  function onLeverDragEnd(id, v) {
    state.simShocks[id] = v;
    announce(nodeName(id) + ' ' + fmtShock(v));
    if (state.mode !== 'sim') setMode('sim', { force: true });
    else { applySimTints(); renderPanel(); syncHash(false); }
  }

  // ---------- key-variable instrument values on 3D labels ----------
  const INSTRUMENT_NODES = ['policy_rate', 'fed_rate', 'fx', 'oil', 'cpi', 'stocks'];
  function applyLabelValues() {
    if (!scene) return;
    const map = new Map();
    for (const r of situation.readings) {
      if (INSTRUMENT_NODES.includes(r.node)) map.set(r.node, L(r.value));
    }
    scene.setLabelValues(map);
  }

  // ---------- AI chat (BYO API key, direct browser calls) ----------
  // Only providers whose API allows direct browser CORS are offered (verified
  // 260711). OpenAI's own API blocks browser CORS, so GPT is reachable only via
  // an OpenAI-compatible gateway (OpenRouter). Each adapter builds the request
  // and extracts {text, stop} from SSE `data:` JSON lines.
  const AI_PROVIDERS = {
    anthropic: {
      label: { ko: 'Anthropic (Claude)', en: 'Anthropic (Claude)' },
      keyHint: 'sk-ant-...',
      keyUrl: 'console.anthropic.com',
      models: [
        { id: 'claude-opus-4-8', label: 'Claude Opus 4.8' },
        { id: 'claude-sonnet-5', label: 'Claude Sonnet 5' },
        { id: 'claude-haiku-4-5', label: 'Claude Haiku 4.5' },
      ],
      validate: (k) => k.startsWith('sk-ant-'),
      build(sys, msgs, model, key) {
        return {
          url: 'https://api.anthropic.com/v1/messages',
          headers: {
            'content-type': 'application/json', 'x-api-key': key,
            'anthropic-version': '2023-06-01', 'anthropic-dangerous-direct-browser-access': 'true',
          },
          body: {
            model, max_tokens: 2048, stream: true, thinking: { type: 'adaptive' },
            system: [{ type: 'text', text: sys, cache_control: { type: 'ephemeral' } }],
            messages: msgs.map((m) => ({ role: m.role, content: m.content })),
          },
        };
      },
      extract(o) {
        if (o.type === 'content_block_delta' && o.delta && o.delta.type === 'text_delta') return { text: o.delta.text };
        if (o.type === 'message_delta' && o.delta && o.delta.stop_reason) return { stop: o.delta.stop_reason };
        return {};
      },
    },
    google: {
      label: { ko: 'Google (Gemini)', en: 'Google (Gemini)' },
      keyHint: 'AIza...',
      keyUrl: 'aistudio.google.com/apikey',
      models: [
        { id: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash' },
        { id: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro' },
        { id: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash' },
      ],
      validate: (k) => k.length > 10,
      build(sys, msgs, model, key) {
        return {
          url: 'https://generativelanguage.googleapis.com/v1beta/models/' + encodeURIComponent(model)
            + ':streamGenerateContent?alt=sse&key=' + encodeURIComponent(key),
          headers: { 'content-type': 'application/json' },
          body: {
            systemInstruction: { parts: [{ text: sys }] },
            contents: msgs.map((m) => ({ role: m.role === 'assistant' ? 'model' : 'user', parts: [{ text: m.content }] })),
            generationConfig: { maxOutputTokens: 2048 },
          },
        };
      },
      extract(o) {
        const cand = o.candidates && o.candidates[0];
        if (!cand) return {};
        let text = '';
        if (cand.content && cand.content.parts) for (const p of cand.content.parts) if (p.text) text += p.text;
        const out = {};
        if (text) out.text = text;
        if (cand.finishReason) out.stop = cand.finishReason;
        return out;
      },
    },
    openai_compat: {
      label: { ko: 'OpenAI 호환 (OpenRouter · Grok · Groq …)', en: 'OpenAI-compatible (OpenRouter · Grok · Groq …)' },
      keyHint: 'sk-... / gsk_...',
      custom: true,
      presets: [
        { id: 'openrouter', label: { ko: 'OpenRouter (GPT·Claude·Gemini 등)', en: 'OpenRouter (GPT, Claude, Gemini …)' }, base: 'https://openrouter.ai/api/v1', model: 'openai/gpt-4o-mini', keyUrl: 'openrouter.ai/keys' },
        { id: 'xai', label: { ko: 'xAI (Grok)', en: 'xAI (Grok)' }, base: 'https://api.x.ai/v1', model: 'grok-3', keyUrl: 'console.x.ai' },
        { id: 'groq', label: { ko: 'Groq', en: 'Groq' }, base: 'https://api.groq.com/openai/v1', model: 'llama-3.3-70b-versatile', keyUrl: 'console.groq.com/keys' },
        { id: 'deepseek', label: { ko: 'DeepSeek', en: 'DeepSeek' }, base: 'https://api.deepseek.com', model: 'deepseek-chat', keyUrl: 'platform.deepseek.com' },
        { id: 'mistral', label: { ko: 'Mistral', en: 'Mistral' }, base: 'https://api.mistral.ai/v1', model: 'mistral-large-latest', keyUrl: 'console.mistral.ai/api-keys' },
        { id: 'custom', label: { ko: '직접 입력 (Base URL)', en: 'Custom (Base URL)' }, base: '', model: '', keyUrl: '' },
      ],
      models: [],
      validate: (k) => k.length > 8,
      build(sys, msgs, model, key, baseUrl) {
        const base = (baseUrl || 'https://openrouter.ai/api/v1').replace(/\/+$/, '');
        return {
          url: base + '/chat/completions',
          headers: {
            'content-type': 'application/json', authorization: 'Bearer ' + key,
            'HTTP-Referer': location.origin, 'X-Title': 'MacroScope',
          },
          body: {
            model: model || 'openai/gpt-4o-mini', stream: true, max_tokens: 2048,
            messages: [{ role: 'system', content: sys }, ...msgs.map((m) => ({ role: m.role, content: m.content }))],
          },
        };
      },
      extract(o) {
        const ch = o.choices && o.choices[0];
        if (!ch) return {};
        const out = {};
        if (ch.delta && ch.delta.content) out.text = ch.delta.content;
        if (ch.finish_reason) out.stop = ch.finish_reason;
        return out;
      },
    },
  };
  const chatLog = []; // {role, text, streaming?, action?}
  let chatBusy = false;
  let chatAbort = null;
  let aiSystemCache = null;

  function curProviderId() { return AI_PROVIDERS[prefs.aiProvider] ? prefs.aiProvider : 'anthropic'; }
  function keyStoreId(p) { return 'macroscope.key.' + p; }
  function getKey(p) {
    try {
      let k = localStorage.getItem(keyStoreId(p)) || '';
      if (!k && p === 'anthropic') k = localStorage.getItem('macroscope.apikey') || ''; // migrate legacy single-key store
      return k;
    } catch { return ''; }
  }
  function setKey(p, k) {
    try {
      if (k) localStorage.setItem(keyStoreId(p), k); else localStorage.removeItem(keyStoreId(p));
      if (p === 'anthropic') localStorage.removeItem('macroscope.apikey');
    } catch { /* in-memory only */ }
  }
  function curModel(p) {
    const stored = prefs.aiModelBy && prefs.aiModelBy[p];
    if (stored) return stored;
    const prov = AI_PROVIDERS[p];
    if (prov.custom) {
      const preset = prov.presets.find((x) => x.id === (prefs.aiCompatPreset || 'openrouter'));
      return (preset && preset.model) || '';
    }
    return (prov.models[0] && prov.models[0].id) || '';
  }

  function buildAiSystem() {
    if (aiSystemCache) return aiSystemCache;
    const s = [];
    s.push('당신은 "매크로스코프(MacroScope)"라는 인터랙티브 3D 경제 인과관계 지도 웹앱에 내장된 경제 교육 조수입니다.');
    s.push('역할: 사용자의 투자·비즈니스·사회과학 질문을 이 지도의 변수와 인과 경로로 풀어 설명합니다. 쉬운 언어(중학생 이해 가능), 메커니즘과 조건 중심. 예측·투자 조언·매수매도 판단은 절대 하지 않고, 대신 "어떤 경로가 어느 방향으로 작동하는지"를 설명합니다.');
    s.push('답변 언어: 아래 앱 상태의 lang을 따릅니다 (ko=한국어 합니다체, en=영어). 길이: 보통 4~8문장, 필요시 짧은 목록. 지도에 없는 연결을 쓸 때는 "지도 밖의 요인"이라고 명시합니다.');
    s.push('부호가 국면에 따라 뒤집히는 엣지(반전 표시)는 항상 양쪽 국면을 함께 설명합니다.');
    s.push('');
    s.push('## 지도 지식');
    s.push('### 변수 (id: 이름 - 설명)');
    for (const n of graph.nodes) {
      const d = descById.get(n.id);
      s.push(n.id + ': ' + n.name.ko + (d ? ' - ' + d.ko : ''));
    }
    s.push('### 인과 엣지 (from->to [부호 강도s1-3 시차l0-3 확실성c1-3] 메커니즘 / ⇄반전조건)');
    for (const e of graph.edges) {
      s.push(e.from + '->' + e.to + ' [' + (e.sign > 0 ? '+' : '-') + ' s' + e.strength + ' l' + e.lag + ' c' + e.confidence + '] '
        + e.mech.ko + (e.flip ? ' / ⇄ ' + e.flip.ko : ''));
    }
    s.push('### 피드백 루프');
    for (const lp of loops) s.push(lp.id + ' (' + (lp.type === 'reinforcing' ? '강화' : '균형') + '): ' + lp.nodes.join('->') + ' - ' + lp.name.ko);
    s.push('### 역사 사례');
    for (const c of cases) s.push(c.id + ': ' + c.title.ko + ' (' + c.period + ')');
    s.push('### 지금 상황판 (수치 기준 ' + (situation.readingsAsOf || situation.asOf) + ' · 해설 기준 ' + (situation.themesAsOf || situation.asOf) + ' - 이후는 알 수 없음을 밝히세요)');
    for (const r of situation.readings) {
      s.push(r.node + ': ' + r.value.ko + ' ' + (r.trend > 0 ? '↑' : r.trend < 0 ? '↓' : '→') + ' - ' + r.note.ko + ' (' + r.source + ', ' + r.date + ')');
    }
    for (const th of situation.themes) s.push('테마 ' + th.id + ': ' + th.title.ko);
    s.push('');
    s.push('## 지도 조작 프로토콜 (필수)');
    s.push('모든 답변의 맨 마지막 줄에 정확히 하나의 코드블록을 출력합니다. 형식:');
    s.push('```map');
    s.push('{"focus": ["노드id"], "edges": [["from","to"]], "shocks": {"노드id": 0.5}, "open": {"case": "사례id"}}');
    s.push('```');
    s.push('- focus/edges: 답변의 핵심 인과 경로 (위 목록에 실제로 존재하는 엣지만, 3~8개).');
    s.push('- shocks: 시나리오형 질문일 때만, -1~1 (예: 금리 인상 질문 -> {"policy_rate": 0.75}). 아니면 생략.');
    s.push('- open: 가장 관련 있는 사례({"case": id}) 또는 루프({"loop": id}) 하나. 없으면 생략.');
    s.push('- 지도와 무관한 질문이면 {"focus": []} 만 출력.');
    aiSystemCache = s.join('\n');
    return aiSystemCache;
  }

  function appStateContext() {
    const parts = ['lang=' + window.I18n.lang, 'mode=' + state.mode];
    if (state.selectedId) parts.push('selected=' + state.selectedId);
    const sh = Object.entries(state.simShocks).filter(([, v]) => v).map(([k, v]) => k + ':' + v);
    if (sh.length) parts.push('shocks=' + sh.join(','));
    return '[앱 상태: ' + parts.join(' ') + ']';
  }

  function setBubbleText(el, text) {
    el.replaceChildren();
    String(text).split('\n').forEach((p, i) => {
      if (i) el.append(h('br'));
      el.append(document.createTextNode(p));
    });
  }
  // #ai-log grows; the real scroller is the panel body
  function panelNearBottom() {
    return els.body.scrollHeight - els.body.scrollTop - els.body.clientHeight < 48;
  }
  function scrollPanelBottom() { els.body.scrollTop = els.body.scrollHeight; }
  function updateStreamingBubble(entry) {
    const el = $('#ai-stream');
    if (!el) return;
    const stick = panelNearBottom(); // don't yank a user who scrolled up to re-read
    setBubbleText(el, entry.text);
    if (stick) scrollPanelBottom();
  }

  // scene-side application of a model-proposed map action (validated defensively)
  function applyMapActionScene(action) {
    if (!scene || !action || typeof action !== 'object') return false;
    let did = false;
    const focus = Array.isArray(action.focus) ? action.focus.filter((id) => graph.nodeById.has(id)) : [];
    const pairs = Array.isArray(action.edges)
      ? action.edges.filter((p) => Array.isArray(p) && graph.byKey.has(p[0] + '>' + p[1]))
      : [];
    if (focus.length || pairs.length) {
      const nodeOrders = new Map(focus.map((id) => [id, 1]));
      const edgeOrders = new Map();
      pairs.forEach(([f, tt], i) => {
        edgeOrders.set(f + '>' + tt, Math.min(4, i + 1));
        nodeOrders.set(f, nodeOrders.get(f) || 1);
        nodeOrders.set(tt, nodeOrders.get(tt) || 1);
      });
      scene.setHighlight({ nodeOrders, edgeOrders, selectedId: null });
      scene.focusNodes([...nodeOrders.keys()]);
      // a fresh highlight without its own shocks clears earlier chat-driven tints
      if (!(action.shocks && typeof action.shocks === 'object' && Object.keys(action.shocks).length)) {
        scene.setPressures(null);
      }
      did = true;
    }
    if (action.shocks && typeof action.shocks === 'object') {
      const sh = {};
      for (const [k, v] of Object.entries(action.shocks)) {
        if (graph.nodeById.has(k) && typeof v === 'number') sh[k] = Math.max(-1, Math.min(1, v));
      }
      if (Object.keys(sh).length) {
        const res = propagate(graph, sh);
        const tint = new Map(Object.entries(sh));
        for (const r of res) tint.set(r.id, r.value);
        scene.setPressures(tint);
        did = true;
      }
    }
    return did;
  }

  function renderActionButtons(action, host) {
    if (!action || typeof action !== 'object') return;
    const hasVis = (Array.isArray(action.focus) && action.focus.length)
      || (Array.isArray(action.edges) && action.edges.length)
      || (action.shocks && Object.keys(action.shocks).length);
    if (hasVis) {
      host.append(h('button', { class: 'preset-btn', onclick: () => {
        applyMapActionScene(action);
        announce(t('관련 경로를 지도에 표시했습니다'));
      } }, '◈ ' + t('지도에 다시 표시')));
    }
    const open = action.open;
    if (open && typeof open === 'object') {
      const c = open.case ? cases.find((x) => x.id === open.case) : null;
      if (c) host.append(h('button', { class: 'preset-btn', onclick: () => { setMode('cases', { quiet: true }); openCase(c.id); } }, '▶︎ ' + L(c.title)));
      const lp = open.loop ? loops.find((x) => x.id === open.loop) : null;
      if (lp) host.append(h('button', { class: 'preset-btn', onclick: () => { setMode('loops', { quiet: true }); openLoop(lp.id); } }, '⟳ ' + L(lp.name)));
    }
  }

  async function sendChat(raw) {
    const text = String(raw || '').trim();
    const p = curProviderId();
    const prov = AI_PROVIDERS[p];
    const key = getKey(p);
    if (!key || chatBusy || !text) return;
    // read live field values so an un-blurred model/base edit still applies
    const model = ($('#ai-model')?.value || curModel(p)).trim();
    const baseUrl = prov.custom ? ($('#ai-base')?.value || prefs.aiCompatBase || '') : '';
    chatBusy = true;
    chatLog.push({ role: 'user', text });
    const entry = { role: 'assistant', text: '', streaming: true };
    chatLog.push(entry);
    renderPanel();
    scrollPanelBottom();

    // history: skip streaming/errored/empty entries, then merge adjacent
    // same-role turns (skipping can create them; providers require alternation),
    // and attach app-state context to the final user message
    const raw2 = [];
    for (const m of chatLog) {
      if (m.streaming || m.error) continue;
      if (!String(m.text || '').trim()) continue;
      raw2.push({ role: m.role, content: m.text });
    }
    raw2[raw2.length - 1] = { role: 'user', content: appStateContext() + '\n' + text };
    const msgs = [];
    for (const m of raw2) {
      const last = msgs[msgs.length - 1];
      if (last && last.role === m.role) last.content += '\n' + m.content;
      else msgs.push({ ...m });
    }
    let trimmed = msgs.slice(-12);
    while (trimmed.length && trimmed[0].role !== 'user') trimmed.shift();

    chatAbort = new AbortController();
    try {
      const req = prov.build(buildAiSystem(), trimmed, model, key, baseUrl);
      const resp = await fetch(req.url, {
        method: 'POST', signal: chatAbort.signal,
        headers: req.headers, body: JSON.stringify(req.body),
      });
      if (!resp.ok) {
        let detail = '';
        try { detail = (await resp.text()).slice(0, 200); } catch { /* ignore */ }
        throw new Error(
          (resp.status === 401 || resp.status === 403) ? t('API 키가 올바르지 않습니다. 키를 확인해 주세요.')
            : resp.status === 429 ? t('요청이 너무 잦습니다. 잠시 후 다시 시도해 주세요.')
              : resp.status === 404 ? t('모델 이름을 찾을 수 없습니다. 모델 ID를 확인해 주세요.') + ' (' + model + ')'
                : t('요청이 실패했습니다') + ' (HTTP ' + resp.status + ')' + (detail ? ' ' + detail : ''),
        );
      }
      const reader = resp.body.getReader();
      const dec = new TextDecoder();
      let buf = '';
      let stopReason = null;
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const lines = buf.split('\n');
        buf = lines.pop();
        for (const line of lines) {
          if (!line.startsWith('data:')) continue;
          const payload = line.slice(5).trim();
          if (!payload || payload === '[DONE]') continue;
          let evd;
          try { evd = JSON.parse(payload); } catch { continue; }
          // mid-stream provider errors (overloaded, in-stream {error}) would
          // otherwise be silently swallowed, leaving an empty bubble
          if (evd && (evd.type === 'error' || evd.error)) {
            const em = (evd.error && (evd.error.message || evd.error.code)) || '';
            throw new Error(em ? String(em).slice(0, 200) : t('요청이 실패했습니다'));
          }
          const d = prov.extract(evd);
          if (d.text) { entry.text += d.text; updateStreamingBubble(entry); }
          if (d.stop) stopReason = d.stop;
        }
      }
      if (stopReason === 'refusal' || stopReason === 'content_filter' || stopReason === 'SAFETY') {
        entry.text = (entry.text ? entry.text + '\n\n' : '') + '(' + t('안전상 이 질문에는 답변이 제한되었습니다.') + ')';
      }
      const mAct = entry.text.match(/```map\s*([\s\S]*?)```/);
      if (mAct) {
        entry.text = entry.text.replace(mAct[0], '').trim();
        try { entry.action = JSON.parse(mAct[1]); } catch { entry.action = null; }
      }
    } catch (err) {
      if (err && err.name === 'AbortError') {
        entry.suffix = '(' + t('중단됨') + ')'; // display only — never replayed to the model
      } else {
        entry.error = true; // excluded from future request history; gets a retry button
        const msg = (err instanceof TypeError)
          ? t('네트워크에 연결할 수 없습니다. 인터넷 연결을 확인해 주세요.')
          : ((err && err.message) || t('요청이 실패했습니다'));
        entry.text = (entry.text ? entry.text + '\n\n' : '') + '⚠︎ ' + msg;
      }
    } finally {
      entry.streaming = false;
      chatBusy = false;
      chatAbort = null;
      // a stream that finishes after the user moved to another tab must not
      // hijack the current panel or map; the log is correct when they return
      if (state.mode === 'ai') {
        renderPanel();
        if (entry.action && !entry.error) {
          if (applyMapActionScene(entry.action)) announce(t('관련 경로를 지도에 표시했습니다')); // 답변과 동시에 지도 반영
        }
        if (!entry.action || entry.error) {
          announce(entry.error ? entry.text.slice(0, 140) : t('답변 도착'));
        }
        scrollPanelBottom();
        $('#ai-input')?.focus();
      }
    }
  }

  function providerSelect(p) {
    const sel = h('select', {
      class: 'ai-model', 'aria-label': t('AI 제공자'), 'data-fkey': 'ai-provider',
      onchange: (e) => { prefs.aiProvider = e.target.value; savePrefs(); renderPanel(); },
    });
    for (const [id, pr] of Object.entries(AI_PROVIDERS)) {
      const o = h('option', { value: id }, L(pr.label));
      if (id === p) o.setAttribute('selected', '');
      sel.append(o);
    }
    return sel;
  }
  // destructive toolbar actions: two-tap confirm, and abort any in-flight stream
  function confirmBtn(label, fkey, action) {
    const btn = h('button', { class: 'preset-btn', 'data-fkey': fkey });
    let armed = false; let timer = null;
    const paint = () => { btn.textContent = armed ? t('한 번 더 누르면 실행') : label; };
    paint();
    btn.addEventListener('click', () => {
      if (!armed) {
        armed = true; paint();
        timer = setTimeout(() => { armed = false; paint(); }, 3000);
        return;
      }
      clearTimeout(timer);
      chatAbort?.abort();
      action();
    });
    return btn;
  }
  function modelField(p, host) {
    const prov = AI_PROVIDERS[p];
    const dl = h('datalist', { id: 'ai-models' });
    for (const m of prov.models) dl.append(h('option', { value: m.id }, m.label || m.id));
    host.append(dl);
    return h('input', {
      id: 'ai-model', class: 'ai-model-input', list: 'ai-models', value: curModel(p),
      placeholder: t('모델 ID'), autocomplete: 'off', 'aria-label': t('모델'),
      onchange: (e) => { prefs.aiModelBy = prefs.aiModelBy || {}; prefs.aiModelBy[p] = e.target.value.trim(); savePrefs(); },
    });
  }
  function compatKeyUrl() {
    const pr = AI_PROVIDERS.openai_compat.presets.find((x) => x.id === (prefs.aiCompatPreset || 'openrouter'));
    return pr ? pr.keyUrl : '';
  }

  function renderAI() {
    const b = els.body;
    const p = curProviderId();
    const prov = AI_PROVIDERS[p];
    const key = getKey(p);

    if (!key) {
      b.append(h('div', { class: 'card' },
        h('h3', {}, t('지도와 대화하기')),
        h('p', {}, t('이 지도에 담긴 변수·인과·역사 사례·현재 상황을 아는 AI에게 투자 환경, 비즈니스, 사회 현상 질문을 던져 보세요. 답변과 동시에 관련 인과 경로가 지도에 켜집니다.')),
      ));
      const setup = h('div', { class: 'card' });
      setup.append(h('h3', {}, t('AI 제공자와 API 키')));
      setup.append(h('p', {}, t('서버가 없는 앱이라 본인의 API 키로 브라우저에서 제공자에 직접 요청합니다. 키는 이 브라우저에만 저장되고 해당 제공자 외 어디로도 전송되지 않으며, 사용량은 본인 계정에 과금됩니다.')));
      setup.append(h('div', { class: 'presets', style: 'margin:8px 0' }, providerSelect(p)));

      if (prov.custom) {
        const curPreset = prefs.aiCompatPreset || 'openrouter';
        const presetSel = h('select', {
          class: 'ai-model', 'aria-label': t('서비스'),
          onchange: (e) => {
            prefs.aiCompatPreset = e.target.value;
            const pr = prov.presets.find((x) => x.id === e.target.value);
            if (pr && pr.id !== 'custom') {
              prefs.aiCompatBase = pr.base;
              prefs.aiModelBy = prefs.aiModelBy || {}; prefs.aiModelBy.openai_compat = pr.model;
            }
            savePrefs(); renderPanel();
          },
        });
        for (const pr of prov.presets) {
          const o = h('option', { value: pr.id }, L(pr.label));
          if (pr.id === curPreset) o.setAttribute('selected', '');
          presetSel.append(o);
        }
        setup.append(h('div', { class: 'presets', style: 'margin-bottom:8px' }, presetSel));
        if (curPreset === 'custom') {
          setup.append(h('input', {
            id: 'ai-base', class: 'ai-key-input', style: 'margin-bottom:8px',
            placeholder: 'https://api.example.com/v1', value: prefs.aiCompatBase || '', 'aria-label': 'Base URL',
            onchange: (e) => { prefs.aiCompatBase = e.target.value.trim(); savePrefs(); },
          }));
        }
      }

      setup.append(modelField(p, setup));
      const keyInput = h('input', {
        type: 'password', class: 'ai-key-input', style: 'margin-top:8px',
        placeholder: prov.keyHint, 'aria-label': 'API key', autocomplete: 'off',
      });
      const saveK = () => {
        const v = keyInput.value.trim();
        if (!v) { toast(t('API 키를 입력해 주세요')); keyInput.focus(); return; }
        if (!prov.validate(v)) { toast(t('키 형식이 올바르지 않습니다') + ' (' + prov.keyHint + ')'); keyInput.focus(); return; }
        setKey(p, v); renderPanel(); announce(t('AI 대화가 준비되었습니다'));
      };
      keyInput.addEventListener('keydown', (ev) => { if (ev.key === 'Enter') saveK(); });
      setup.append(keyInput);
      setup.append(h('button', { class: 'btn primary', style: 'margin-top:8px', onclick: saveK }, t('저장하고 시작')));
      const keyUrl = prov.custom ? compatKeyUrl() : prov.keyUrl;
      if (keyUrl) setup.append(h('p', { class: 'rd-src', style: 'margin-top:8px' }, t('키 발급') + ': ' + keyUrl));
      if (prov.custom) setup.append(h('p', { class: 'rd-src' }, t('참고: OpenAI 본체 API는 브라우저 직접 호출을 막아(CORS) 이 앱에서 직접 쓸 수 없습니다. GPT는 OpenRouter로 이용하세요.')));
      b.append(setup);
      return;
    }

    b.append(h('div', { class: 'presets ai-toolbar' },
      providerSelect(p),
      modelField(p, b),
      confirmBtn(t('대화 지우기'), 'ai-clear', () => {
        chatLog.length = 0;
        scene?.clearHighlight();
        scene?.setPressures(null);
        renderPanel();
      }),
      confirmBtn(t('키 삭제'), 'ai-delkey', () => { setKey(p, ''); renderPanel(); }),
    ));

    const log = h('div', { id: 'ai-log' });
    if (!chatLog.length) {
      log.append(h('div', { class: 'card' }, h('p', {},
        t('무엇이든 물어보세요. 답변의 근거가 되는 인과 경로가 지도에 함께 켜지고, 관련 역사 사례로 바로 건너갈 수 있습니다.'))));
    }
    chatLog.forEach((m, i) => {
      const bubble = h('div', { class: 'ai-msg ' + (m.role === 'user' ? 'user' : 'assistant') });
      const txt = h('div', { class: 'ai-text' });
      const shown = (m.text || '') + (m.suffix ? (m.text ? '\n' : '') + m.suffix : '');
      setBubbleText(txt, shown || (m.streaming ? '…' : ''));
      if (m.streaming && i === chatLog.length - 1) txt.id = 'ai-stream';
      bubble.append(txt);
      if (m.error && !m.streaming && !chatBusy) {
        // failed turn: offer a retry that re-sends the preceding user message
        bubble.append(h('div', { class: 'ai-actions presets' },
          h('button', { class: 'preset-btn', onclick: () => {
            const idx = chatLog.indexOf(m);
            const prev = chatLog[idx - 1];
            if (!prev || prev.role !== 'user') return;
            chatLog.splice(idx - 1, 2);
            sendChat(prev.text);
          } }, t('다시 시도'))));
      }
      if (m.action && !m.streaming && !m.error) {
        const actions = h('div', { class: 'ai-actions presets' });
        renderActionButtons(m.action, actions);
        if (actions.children.length) bubble.append(actions);
      }
      log.append(bubble);
    });
    b.append(log);

    if (!chatLog.length) {
      const sug = h('div', { class: 'presets' });
      for (const q of [
        t('금리가 오르면 왜 주가가 떨어지나요? 반대로 호재가 되는 경우도 있나요?'),
        t('원화 약세가 수입 원자재를 쓰는 사업에 미치는 영향을 경로로 보여주세요.'),
        t('지금의 AI 반도체 붐은 2000년 닷컴 버블과 무엇이 같고 무엇이 다른가요?'),
      ]) {
        sug.append(h('button', { class: 'preset-btn sug', onclick: () => sendChat(q) }, q));
      }
      b.append(sug);
    }

    const ta = h('textarea', {
      id: 'ai-input', rows: '2',
      placeholder: t('예: 지금 금리가 내리면 부동산은 어떻게 되나요?'),
      'aria-label': t('질문 입력'),
    });
    const autosize = () => { ta.style.height = 'auto'; ta.style.height = Math.min(ta.scrollHeight, 160) + 'px'; };
    ta.addEventListener('input', autosize);
    ta.addEventListener('keydown', (ev) => {
      if (ev.isComposing || ev.keyCode === 229) return; // Hangul IME mid-composition
      if (ev.key === 'Enter' && !ev.shiftKey) { ev.preventDefault(); submit(); }
    });
    const submit = () => {
      if (chatBusy) return; // don't wipe a draft typed while a reply streams
      const v = ta.value;
      ta.value = '';
      ta.style.height = '';
      sendChat(v);
    };
    const rowEls = [ta];
    const btns = h('div', { class: 'ai-btns' });
    if (chatBusy) btns.append(h('button', { class: 'btn sm', onclick: () => chatAbort && chatAbort.abort() }, '■ ' + t('중지')));
    btns.append(h('button', { class: 'btn primary sm', onclick: submit, disabled: chatBusy ? '' : null },
      chatBusy ? t('생성 중…') : t('보내기')));
    rowEls.push(btns);
    b.append(h('div', { class: 'ai-inputrow' }, ...rowEls));
    b.append(h('p', { class: 'rd-src', style: 'margin-top:6px' },
      t('교육 목적 도구입니다. 투자 조언이 아니며, 답변은 부정확할 수 있습니다.')));
    if (chatLog.length && !chatBusy) scrollPanelBottom(); // entering the tab lands on the latest turn
  }

  // ---------- search palette (Ctrl+K / '/') ----------
  const CHO_LIST = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'];
  function chosungOf(s) {
    let out = '';
    for (const ch of s) {
      const c = ch.codePointAt(0);
      if (c >= 0xAC00 && c <= 0xD7A3) out += CHO_LIST[Math.floor((c - 0xAC00) / 588)];
      else out += ch;
    }
    return out;
  }
  const TYPE_BADGE = {
    node: { ko: '변수', en: 'Variable' },
    caseStudy: { ko: '사례', en: 'Case' },
    loop: { ko: '루프', en: 'Loop' },
    theme: { ko: '지금', en: 'Now' },
  };
  let searchItems = null;
  let searchActive = 0;
  function getSearchItems() {
    if (searchItems) return searchItems;
    searchItems = [];
    for (const n of graph.nodes) {
      searchItems.push({
        type: 'node', id: n.id, obj: n,
        ko: n.name.ko, en: n.name.en.toLowerCase(), cho: chosungOf(n.name.ko),
        extra: (descById.get(n.id) ? descById.get(n.id).ko : '').toLowerCase(),
        color: catById.get(n.cat).color,
      });
    }
    for (const c of cases) {
      searchItems.push({
        type: 'caseStudy', id: c.id, obj: c,
        ko: c.title.ko, en: c.title.en.toLowerCase(), cho: chosungOf(c.title.ko),
        extra: c.period.toLowerCase(), color: '#ffd166',
      });
    }
    for (const lp of loops) {
      searchItems.push({
        type: 'loop', id: lp.id, obj: lp,
        ko: lp.name.ko, en: lp.name.en.toLowerCase(), cho: chosungOf(lp.name.ko),
        extra: lp.nodes.join(' '), color: '#57e39a',
      });
    }
    for (const th of situation.themes) {
      searchItems.push({
        type: 'theme', id: th.id, obj: th,
        ko: th.title.ko, en: th.title.en.toLowerCase(), cho: chosungOf(th.title.ko),
        extra: th.body.ko.toLowerCase(), color: '#54e0ff',
      });
    }
    return searchItems;
  }
  function searchScore(item, q, isCho) {
    const ko = item.ko.toLowerCase();
    if (ko.startsWith(q) || item.en.startsWith(q)) return 0;
    if (ko.includes(q) || item.en.includes(q)) return 1;
    if (isCho && item.cho.includes(q)) return 2;
    if (item.extra.includes(q)) return 3;
    return -1;
  }
  function renderSearchResults() {
    const host = $('#search-results');
    const q = $('#search-input').value.trim().toLowerCase();
    host.replaceChildren();
    let list;
    if (!q) {
      // curated empty state: the recommended entry points, not raw data order
      const all = getSearchItems();
      list = [
        ...['policy_rate', 'oil', 'fx', 'risk_sentiment'].map((id) => all.find((x) => x.type === 'node' && x.id === id)),
        all.find((x) => x.type === 'caseStudy'),
        all.find((x) => x.type === 'loop'),
        all.find((x) => x.type === 'theme'),
      ].filter(Boolean);
    } else {
      const isCho = [...q].every((ch) => CHO_LIST.includes(ch));
      list = getSearchItems()
        .map((it) => ({ it, s: searchScore(it, q, isCho) }))
        .filter((x) => x.s >= 0)
        .sort((a, b) => a.s - b.s)
        .slice(0, 12)
        .map((x) => x.it);
    }
    host.__list = list;
    const input = $('#search-input');
    if (!list.length) {
      host.append(h('div', { class: 'search-empty' }, t('결과가 없습니다. 다른 검색어를 시도해 보세요.')));
      searchActive = 0;
      input.removeAttribute('aria-activedescendant');
      input.setAttribute('aria-expanded', 'false');
      return;
    }
    if (searchActive >= list.length) searchActive = 0;
    input.setAttribute('aria-activedescendant', 'sr-' + searchActive);
    input.setAttribute('aria-expanded', 'true');
    list.forEach((it, i) => {
      const name = (it.type === 'caseStudy' || it.type === 'theme') ? L(it.obj.title) : L(it.obj.name);
      host.append(h('button', {
        class: 'search-item' + (i === searchActive ? ' active' : ''),
        id: 'sr-' + i, role: 'option', 'aria-selected': String(i === searchActive),
        onclick: () => pickSearch(it),
      },
        h('span', { class: 'si-dot', style: 'background:' + it.color }),
        h('span', { class: 'si-name' }, name),
        h('span', { class: 'si-type' }, L(TYPE_BADGE[it.type])),
      ));
    });
  }
  function moveSearchActive(delta) {
    const host = $('#search-results');
    const n = host.__list ? host.__list.length : 0;
    if (!n) return;
    searchActive = (searchActive + delta + n) % n;
    [...host.children].forEach((el, i) => {
      el.classList.toggle('active', i === searchActive);
      el.setAttribute('aria-selected', String(i === searchActive));
    });
    if (host.children[searchActive]) host.children[searchActive].scrollIntoView({ block: 'nearest' });
    $('#search-input').setAttribute('aria-activedescendant', 'sr-' + searchActive);
  }
  function pickSearch(it) {
    $('#dlg-search').close();
    if (it.type === 'node') { setMode('explore', { quiet: true }); selectNode(it.id); }
    else if (it.type === 'caseStudy') { setMode('cases', { quiet: true }); openCase(it.id); }
    else if (it.type === 'theme') { setMode('now', { quiet: true }); openTheme(it.id); }
    else { setMode('loops', { quiet: true }); openLoop(it.id); }
  }
  function openSearch() {
    searchActive = 0;
    const input = $('#search-input');
    input.value = '';
    renderSearchResults();
    $('#dlg-search').showModal();
    input.focus();
  }

  // ---------- deep links (hash router) ----------
  let applyingHash = false;
  function currentHash() {
    if (state.mode === 'ai') return '#/ai';
    if (state.mode === 'now' && state.nowThemeId) return '#/now/' + state.nowThemeId;
    if (state.mode === 'now') return '#/now';
    if (state.mode === 'cases' && state.caseId) return '#/case/' + state.caseId + '/' + state.phaseIdx;
    if (state.mode === 'cases') return '#/cases';
    if (state.mode === 'loops' && state.loopId) return '#/loop/' + state.loopId;
    if (state.mode === 'loops') return '#/loops';
    if (state.mode === 'sim') {
      const parts = Object.entries(state.simShocks)
        .filter(([, v]) => v)
        .map(([k, v]) => k + ':' + Math.round(v * 100));
      return '#/sim' + (parts.length ? '/' + parts.join(',') : '');
    }
    if (state.selectedId) return '#/v/' + state.selectedId;
    return '#/';
  }
  function syncHash(push) {
    if (applyingHash) return;
    const hash = currentHash();
    if (location.hash === hash) return;
    try {
      if (push) history.pushState(null, '', hash);
      else history.replaceState(null, '', hash);
    } catch { /* sandboxed contexts */ }
  }
  function applyHashFromLocation() {
    const seg = location.hash.replace(/^#\/?/, '').split('/');
    applyingHash = true;
    try {
      if (seg[0] === 'v' && graph.nodeById.has(seg[1])) {
        setMode('explore', { force: true });
        selectNode(seg[1]);
      } else if (seg[0] === 'case' && cases.some((c) => c.id === seg[1])) {
        setMode('cases', { force: true });
        openCase(seg[1]);
        const ph = parseInt(seg[2], 10);
        if (!Number.isNaN(ph)) gotoPhase(ph);
      } else if (seg[0] === 'cases') {
        setMode('cases', { force: true });
      } else if (seg[0] === 'loop' && loops.some((l) => l.id === seg[1])) {
        setMode('loops', { force: true });
        openLoop(seg[1]);
      } else if (seg[0] === 'loops') {
        setMode('loops', { force: true });
      } else if (seg[0] === 'now') {
        setMode('now', { force: true });
        if (seg[1] && situation.themes.some((x) => x.id === seg[1])) openTheme(seg[1]);
      } else if (seg[0] === 'ai') {
        setMode('ai', { force: true });
      } else if (['v', 'case', 'loop'].includes(seg[0]) && seg[1]) {
        // route shape is right but the id is unknown (stale/mistyped link) — say so
        toast(t('링크가 가리키던 항목을 찾을 수 없어 처음 화면을 보여드립니다.'));
        announce(t('링크가 가리키던 항목을 찾을 수 없어 처음 화면을 보여드립니다.'));
        setMode('explore', { force: true });
        if (state.selectedId) selectNode(null);
      } else if (seg[0] === 'sim') {
        setMode('sim', { force: true });
        for (const k of Object.keys(state.simShocks)) state.simShocks[k] = 0;
        if (seg[1]) {
          for (const pair of seg[1].split(',')) {
            const [k, v] = pair.split(':');
            if (k in state.simShocks) state.simShocks[k] = Math.max(-1, Math.min(1, (Number(v) || 0) / 100));
          }
        }
        applySimTints();
        renderPanel();
      } else {
        setMode('explore', { force: true });
        if (state.selectedId) selectNode(null);
      }
    } finally {
      applyingHash = false;
    }
  }

  // ---------- panel collapse (mobile) ----------
  const mobileViewport = window.matchMedia('(max-width: 900px)');
  function isMobile() { return mobileViewport.matches; }
  function syncMapViewportReservation() {
    const reserve = shouldReserveMapViewport(
      window.innerWidth,
      els.panel.classList.contains('collapsed'),
    );
    document.documentElement.classList.toggle('map-viewport-reserved', reserve);
  }
  function setPanelCollapsed(collapsed) {
    if (isMobile() && !collapsed) els.legend.removeAttribute('open');
    els.panel.classList.toggle('collapsed', collapsed);
    els.toggle.setAttribute('aria-expanded', String(!collapsed));
    els.toggle.querySelector('span').textContent = collapsed ? t('펼치기') : t('접기');
    syncMapViewportReservation();
  }
  function expandPanelIfMobile(expand) {
    if (isMobile()) setPanelCollapsed(!expand);
  }

  // ---------- wiring ----------
  function wire() {
    document.querySelectorAll('.mode-tab').forEach((b) => {
      b.addEventListener('click', () => setMode(b.dataset.mode));
    });
    els.toggle.addEventListener('click', () => setPanelCollapsed(!els.panel.classList.contains('collapsed')));
    $('#btn-help').addEventListener('click', openOnboarding);
    $('#btn-sources').addEventListener('click', openSources);
    $('#btn-sources-mini').addEventListener('click', openSources);

    // search palette
    $('#btn-search').addEventListener('click', openSearch);
    // touch has no Esc: tapping the backdrop closes the palette
    const dlgSearch = $('#dlg-search');
    dlgSearch.addEventListener('click', (e) => { if (e.target === dlgSearch) dlgSearch.close(); });
    const sInput = $('#search-input');
    sInput.addEventListener('input', () => { searchActive = 0; renderSearchResults(); });
    sInput.addEventListener('keydown', (ev) => {
      if (ev.key === 'ArrowDown') { ev.preventDefault(); moveSearchActive(1); }
      else if (ev.key === 'ArrowUp') { ev.preventDefault(); moveSearchActive(-1); }
      else if (ev.key === 'Enter') {
        ev.preventDefault();
        const list = $('#search-results').__list;
        if (list && list.length) pickSearch(list[searchActive] || list[0]);
      }
    });

    // home button: return to the Explore hub (fresh start screen)
    $('#btn-home').addEventListener('click', () => {
      stopAutoplay();
      state.selectedId = null;
      state.caseId = null;
      state.loopId = null;
      state.nowThemeId = null;
      setMode('explore', { force: true });
    });

    // deep links: restore on back/forward
    window.addEventListener('popstate', applyHashFromLocation);

    const motionBtn = $('#btn-motion');
    function syncMotion() {
      const rm = reducedMotion();
      motionBtn.setAttribute('aria-pressed', String(rm));
      document.documentElement.classList.toggle('reduce-motion', rm);
      // explicit in-app opt-in must beat the OS prefers-reduced-motion CSS kill switch
      document.documentElement.classList.toggle('motion-on', prefs.motion === 'on');
      scene?.setReducedMotion(rm);
    }
    motionBtn.addEventListener('click', () => {
      prefs.motion = reducedMotion() ? 'on' : 'off';
      savePrefs();
      syncMotion();
      toast(reducedMotion() ? t('모션을 줄였습니다') : t('모션을 켰습니다'));
    });
    mediaReduced.addEventListener?.('change', syncMotion); // OS setting changed mid-session
    mobileViewport.addEventListener?.('change', syncMapViewportReservation);
    syncMotion();

    document.addEventListener('keydown', (ev) => {
      if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === 'k') {
        ev.preventDefault();
        if (!document.querySelector('dialog[open]')) openSearch();
        return;
      }
      if (document.querySelector('dialog[open]')) return; // dialogs own the keyboard
      if (ev.key === '/' && !/^(INPUT|TEXTAREA|SELECT)$/.test(ev.target.tagName)) {
        ev.preventDefault();
        openSearch();
        return;
      }
      if (ev.key === 'Escape') {
        if (state.mode === 'explore' && state.selectedId) selectNode(null);
        else if (state.mode === 'cases') closeCase();
        else if (state.mode === 'loops') closeLoop();
        else if (state.mode === 'sim') setMode('explore');
        else if (state.mode === 'now' && state.nowThemeId) closeTheme();
      }
      if (state.mode === 'cases' && state.caseId) {
        if (ev.key === 'ArrowRight') gotoPhase(state.phaseIdx + 1);
        if (ev.key === 'ArrowLeft') gotoPhase(state.phaseIdx - 1);
      }
    });

    if (isMobile()) setPanelCollapsed(true); // map leads on a phone; panel expands on selection
    // desktop: open legend by default; mobile: keep collapsed
    if (!isMobile() && prefs.legendOpen !== false) els.legend.setAttribute('open', '');
    els.legend.addEventListener('toggle', () => {
      prefs.legendOpen = els.legend.hasAttribute('open');
      savePrefs();
    });

    els.status.textContent = 'NODES ' + graph.nodes.length + ' · LINKS ' + graph.edges.length + ' · ' + version;
    applyLabelTitles();
    applyLabelValues();
  }

  // hover tooltips: variable description on the 3D label chips
  function applyLabelTitles() {
    if (!scene) return;
    const map = new Map();
    for (const n of graph.nodes) {
      const d = descById.get(n.id);
      if (d) map.set(n.id, L(d));
    }
    scene.setLabelTitles(map);
  }

  // ---------- integrity (dev aid, logged once) ----------
  function integrityReport() {
    const problems = [];
    for (const lp of loops) {
      const edges = loopEdges(graph, lp.nodes);
      if (!edges) { problems.push('loop broken: ' + lp.id); continue; }
      const sign = loopNetSign(edges);
      const expect = lp.type === 'reinforcing' ? 1 : -1;
      if (sign !== expect) problems.push('loop sign mismatch: ' + lp.id);
    }
    for (const c of cases) {
      for (const p of c.phases) {
        for (const [f, tt] of p.activeEdges) {
          if (!graph.byKey.has(f + '>' + tt)) problems.push('case ' + c.id + ' unknown edge ' + f + '>' + tt);
        }
        for (const id of p.focusNodes) if (!graph.nodeById.has(id)) problems.push('case ' + c.id + ' unknown node ' + id);
      }
    }
    if (problems.length) console.warn('[macroscope] data integrity:', problems);
    return problems;
  }

  return {
    state,
    setMode,
    selectNode,
    renderPanel,
    renderLegend,
    openOnboarding,
    openSources,
    wire,
    integrityReport,
    reducedMotion,
    prefs,
    savePrefs,
    onLeverDrag,
    onLeverDragEnd,
    onModelStatusChange() {
      if (state.mode === 'explore' && state.selectedId) renderPanel();
    },
    onLangChange() {
      renderLegend();
      renderPanel();
      scene?.setLang(window.I18n.lang);
      applyLabelTitles();
      applyLabelValues();
      els.toggle.querySelector('span').textContent = els.panel.classList.contains('collapsed') ? t('펼치기') : t('접기');
    },
    initFromHash() {
      if (location.hash && location.hash !== '#/' && location.hash !== '#') applyHashFromLocation();
    },
    maybeShowOnboarding() {
      if (prefs.onboarded) return;
      // list mode: the tour teaches 3D gestures that do not exist here
      if (state.listMode) { prefs.onboarded = true; savePrefs(); return; }
      // deep-linked visitor came to see specific content — don't cover it;
      // the tour still shows on their first plain visit (onboarded stays false)
      if (location.hash.replace(/^#\/?/, '')) {
        toast(t('처음이시면 오른쪽 위 ? 버튼에서 읽는 법을 볼 수 있습니다.'));
        return;
      }
      openOnboarding();
      prefs.onboarded = true;
      savePrefs();
    },
    enableListMode() {
      state.listMode = true;
      renderPanel();
      if (isMobile()) setPanelCollapsed(false);
      toast(t('이 기기에서는 3D를 사용할 수 없어 목록 모드로 표시합니다. 모든 설명은 아래 패널에서 그대로 볼 수 있습니다.'));
    },
  };
}
