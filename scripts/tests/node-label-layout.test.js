import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const moduleUrl = new URL('../../js/node-label-layout.js', import.meta.url);

async function loadLayoutModule() {
  assert.ok(existsSync(fileURLToPath(moduleUrl)), 'node-label-layout.js must exist');
  return import(moduleUrl.href);
}

function overlaps(a, b, gap = 0) {
  return a.left < b.right + gap
    && a.right > b.left - gap
    && a.top < b.bottom + gap
    && a.bottom > b.top - gap;
}

function visibleById(layout) {
  return new Map(layout.filter((item) => item.visible).map((item) => [item.id, item]));
}

test('visible labels are clamped inside horizontal viewport bounds', async () => {
  const { layoutNodeLabels } = await loadLayoutModule();
  const layout = layoutNodeLabels({
    viewport: { width: 390, height: 844, padding: 8 },
    candidates: [
      { id: 'left', preferredX: -40, preferredY: 180, width: 120, height: 26, critical: true },
      { id: 'right', preferredX: 460, preferredY: 230, width: 100, height: 26, critical: true },
    ],
  });

  for (const item of layout) {
    assert.equal(item.visible, true);
    assert.ok(item.rect.left >= 8);
    assert.ok(item.rect.right <= 382);
  }
});

test('critical labels sharing a projection are placed without pair overlap', async () => {
  const { layoutNodeLabels } = await loadLayoutModule();
  const visible = visibleById(layoutNodeLabels({
    viewport: { width: 390, height: 844, padding: 8 },
    gap: 4,
    candidates: [
      { id: 'selected', preferredX: 190, preferredY: 180, width: 112, height: 28, priority: 500, critical: true },
      { id: 'highlighted', preferredX: 190, preferredY: 180, width: 112, height: 28, priority: 400, critical: true },
    ],
  }));

  assert.equal(visible.size, 2);
  assert.equal(overlaps(visible.get('selected').rect, visible.get('highlighted').rect, 4), false);
});

test('critical priority wins when only one label can fit', async () => {
  const { layoutNodeLabels } = await loadLayoutModule();
  const layout = layoutNodeLabels({
    viewport: { width: 100, height: 30, padding: 4 },
    gap: 4,
    candidates: [
      { id: 'ordinary', preferredX: 50, preferredY: 15, width: 88, height: 22, priority: 0 },
      { id: 'value', preferredX: 50, preferredY: 15, width: 88, height: 22, priority: 300, critical: true },
    ],
  });
  const byId = new Map(layout.map((item) => [item.id, item]));

  assert.equal(byId.get('value').visible, true);
  assert.equal(byId.get('ordinary').visible, false);
});

test('critical priority does not pin an unprojectable label to the viewport', async () => {
  const { layoutNodeLabels } = await loadLayoutModule();
  const [placement] = layoutNodeLabels({
    viewport: { width: 390, height: 844, padding: 8 },
    candidates: [{
      id: 'behind-camera',
      preferredX: 195,
      preferredY: 180,
      width: 112,
      height: 26,
      priority: 500,
      critical: true,
      eligible: false,
    }],
  });

  assert.equal(placement.visible, false);
});

test('ordinary labels hide instead of drifting beyond their displacement cap', async () => {
  const { layoutNodeLabels } = await loadLayoutModule();
  const [placement] = layoutNodeLabels({
    viewport: { width: 300, height: 300, padding: 8 },
    obstacles: [{ left: 0, top: 100, right: 300, bottom: 200 }],
    candidates: [{
      id: 'ordinary',
      preferredX: 150,
      preferredY: 150,
      width: 80,
      height: 20,
      maxDisplacement: 32,
    }],
  });

  assert.equal(placement.visible, false);
});

test('selected labels lazily search within a finite association cap and request a leader', async () => {
  const { layoutNodeLabels } = await loadLayoutModule();
  const stats = {};
  const [placement] = layoutNodeLabels({
    viewport: { width: 300, height: 300, padding: 8 },
    obstacles: [{ left: 0, top: 0, right: 300, bottom: 260 }],
    candidates: [{
      id: 'selected',
      preferredX: 150,
      preferredY: 150,
      width: 80,
      height: 20,
      maxDisplacement: 160,
      allowDistantFallback: true,
      leaderThreshold: 0.5,
      critical: true,
      priority: 500,
    }],
    stats,
  });

  assert.equal(placement.visible, true);
  assert.ok(placement.displacement > 72, 'all bounded local targets should be blocked');
  assert.ok(placement.displacement <= 160, 'selected label must stay associated with its node');
  assert.equal(placement.showLeader, true);
  assert.ok(stats.fallbackProbes > 0, 'fallback search should begin after local failure');
  assert.ok(stats.fallbackProbes <= 96, 'fallback search must have a fixed operation budget');
});

test('selected fallback stays lazy when a local placement succeeds', async () => {
  const { layoutNodeLabels } = await loadLayoutModule();
  const stats = {};
  const [placement] = layoutNodeLabels({
    viewport: { width: 390, height: 844, padding: 8 },
    candidates: [{
      id: 'selected',
      preferredX: 195,
      preferredY: 220,
      width: 96,
      height: 24,
      maxDisplacement: 160,
      allowDistantFallback: true,
      critical: true,
      priority: 500,
    }],
    stats,
  });

  assert.equal(placement.visible, true);
  assert.equal(placement.displacement, 0);
  assert.equal(stats.fallbackProbes, 0);
});

test('390px selected label hides when viewport clamping would detach it by 384px', async () => {
  const { layoutNodeLabels } = await loadLayoutModule();
  const [placement] = layoutNodeLabels({
    viewport: { width: 390, height: 844, padding: 8 },
    candidates: [{
      id: 'selected',
      preferredX: -336,
      preferredY: 220,
      width: 80,
      height: 24,
      maxDisplacement: 160,
      allowDistantFallback: true,
      leaderThreshold: 0.5,
      critical: true,
      priority: 500,
    }],
  });

  assert.equal(placement.visible, false);
  assert.equal(placement.displacement, null);
});

test('non-selected critical labels respect their displacement cap', async () => {
  const { layoutNodeLabels } = await loadLayoutModule();
  const [placement] = layoutNodeLabels({
    viewport: { width: 300, height: 300, padding: 8 },
    obstacles: [{ left: 0, top: 80, right: 300, bottom: 220 }],
    candidates: [{
      id: 'highlighted',
      preferredX: 150,
      preferredY: 150,
      width: 80,
      height: 20,
      maxDisplacement: 64,
      critical: true,
      priority: 400,
    }],
  });

  assert.equal(placement.visible, false);
});

test('viewport clamping cannot move a label beyond its displacement cap', async () => {
  const { layoutNodeLabels } = await loadLayoutModule();
  const [placement] = layoutNodeLabels({
    viewport: { width: 100, height: 100, padding: 8 },
    candidates: [{
      id: 'off-edge',
      preferredX: -100,
      preferredY: 50,
      width: 20,
      height: 20,
      maxDisplacement: 32,
    }],
  });

  assert.equal(placement.visible, false);
});

test('layout is deterministic regardless of candidate input order', async () => {
  const { layoutNodeLabels } = await loadLayoutModule();
  const candidates = [
    { id: 'b', preferredX: 180, preferredY: 160, width: 96, height: 24, priority: 100 },
    { id: 'a', preferredX: 180, preferredY: 160, width: 96, height: 24, priority: 100 },
    { id: 'c', preferredX: 200, preferredY: 180, width: 96, height: 24, priority: 100 },
  ];
  const options = { viewport: { width: 390, height: 844, padding: 8 }, candidates };
  const forward = layoutNodeLabels(options);
  const reverse = layoutNodeLabels({ ...options, candidates: [...candidates].reverse() });

  assert.deepEqual(forward, reverse);
});

for (const criticalCount of [8, 19, 30]) {
  test(`${criticalCount} non-selected critical labels stay inside the local operation budget`, async () => {
    const { layoutNodeLabels } = await loadLayoutModule();
    const stats = {};
    const candidates = Array.from({ length: criticalCount }, (_, index) => ({
      id: `critical-${String(index).padStart(2, '0')}`,
      preferredX: 195,
      preferredY: 220,
      width: 104,
      height: 26,
      maxDisplacement: 64,
      critical: true,
      priority: 300 - index,
    }));

    layoutNodeLabels({
      viewport: { width: 390, height: 844, padding: 8 },
      obstacles: [{ left: 0, top: 0, right: 390, bottom: 844 }],
      candidates,
      stats,
    });

    assert.ok(
      stats.localProbes <= criticalCount * 25,
      `expected at most 25 local probes per label, received ${stats.localProbes}`,
    );
    assert.equal(stats.fallbackProbes, 0, 'non-selected critical labels must not search a fallback grid');
    assert.equal(stats.totalProbes, stats.localProbes);
  });
}

for (const scenario of [
  {
    name: 'desktop',
    viewport: { width: 1440, height: 900, padding: 8 },
    obstacles: [
      { left: 0, top: 0, right: 1440, bottom: 86 },
      { left: 1028, top: 94, right: 1428, bottom: 888 },
    ],
    preferredY: 120,
  },
  {
    name: '390px mobile',
    viewport: { width: 390, height: 844, padding: 8 },
    obstacles: [
      { left: 0, top: 0, right: 390, bottom: 108 },
      { left: 0, top: 330, right: 390, bottom: 844 },
    ],
    preferredY: 122,
  },
]) {
  test(`${scenario.name} preserves critical labels outside header and expanded panel`, async () => {
    const { layoutNodeLabels } = await loadLayoutModule();
    const candidates = [
      { id: 'selected', width: 104, height: 26, priority: 500, critical: true },
      { id: 'highlighted', width: 108, height: 26, priority: 400, critical: true },
      { id: 'lever', width: 92, height: 26, priority: 200, critical: true },
      { id: 'value', width: 116, height: 26, priority: 300, critical: true },
      { id: 'ordinary', width: 112, height: 26, priority: 0 },
    ].map((candidate, index) => ({
      ...candidate,
      preferredX: 166 + index * 5,
      preferredY: scenario.preferredY + index * 3,
    }));
    const layout = layoutNodeLabels({
      viewport: scenario.viewport,
      obstacles: scenario.obstacles,
      candidates,
      gap: 4,
    });
    const critical = layout.filter((item) => item.critical);

    assert.equal(critical.length, 4);
    assert.ok(critical.every((item) => item.visible));
    for (const item of layout.filter((entry) => entry.visible)) {
      assert.ok(item.rect.left >= scenario.viewport.padding);
      assert.ok(item.rect.right <= scenario.viewport.width - scenario.viewport.padding);
      for (const obstacle of scenario.obstacles) {
        assert.equal(overlaps(item.rect, obstacle), false, `${item.id} intersects an obstacle`);
      }
    }
    for (let i = 0; i < critical.length; i += 1) {
      for (let j = i + 1; j < critical.length; j += 1) {
        assert.equal(overlaps(critical[i].rect, critical[j].rect, 4), false);
      }
    }
  });
}
