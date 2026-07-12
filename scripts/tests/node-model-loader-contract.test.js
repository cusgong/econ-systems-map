import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

const moduleUrl = new URL('../../js/node-model-loader-contract.js', import.meta.url);
const contract = existsSync(moduleUrl) ? await import(moduleUrl.href) : {};
const visualSource = readFileSync(new URL('../../js/node-visual-system.js', import.meta.url), 'utf8');

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

test('latest load success prevents an older rejection from running failure effects', async () => {
  assert.equal(typeof contract.createLatestLoadCoordinator, 'function');
  const coordinator = contract.createLatestLoadCoordinator();
  const effects = [];
  const a = deferred();
  const b = deferred();

  async function observe(ticket, pending, label) {
    try {
      const value = await pending.promise;
      coordinator.succeed(ticket, () => effects.push(`${label}:${value}`));
    } catch {
      coordinator.fail(ticket, () => effects.push(`${label}:failed`));
    }
  }

  const ticketA = coordinator.begin();
  const runA = observe(ticketA, a, 'A');
  const ticketB = coordinator.begin();
  const runB = observe(ticketB, b, 'B');

  b.resolve('ready');
  await runB;
  a.reject(new Error('late A failure'));
  await runA;

  assert.deepEqual(effects, ['B:ready']);
});

test('dispose invalidates an in-flight load and refuses new tickets', async () => {
  assert.equal(typeof contract.createLatestLoadCoordinator, 'function');
  const coordinator = contract.createLatestLoadCoordinator();
  const effects = [];
  const pending = deferred();
  const ticket = coordinator.begin();
  const observed = pending.promise.catch(() => {
    coordinator.fail(ticket, () => effects.push('failure-side-effect'));
  });

  coordinator.dispose();
  pending.reject(new Error('rejected after dispose'));
  await observed;

  assert.deepEqual(effects, []);
  assert.equal(coordinator.begin(), null);
});

const PUBLIC_LOAD_STATUSES = new Set(['ready', 'partial', 'fallback']);

test('stale load settling while a newer load is pending never exposes loading', async () => {
  assert.equal(typeof contract.normalizePublicLoadStatus, 'function');
  const coordinator = contract.createLatestLoadCoordinator();
  const a = deferred();
  const b = deferred();
  const ticketA = coordinator.begin();
  const settledA = a.promise.then(() => (
    coordinator.succeed(ticketA)
      ? 'ready'
      : contract.normalizePublicLoadStatus('loading')
  ));

  coordinator.begin(); // B is now the current pending load.
  void b;
  a.resolve('late A success');
  const status = await settledA;

  assert.equal(status, 'fallback');
  assert.notEqual(status, 'loading', 'public status must never be loading');
  assert.ok(PUBLIC_LOAD_STATUSES.has(status));
});

test('pending resolve and reject after dispose both normalize to a public status', async () => {
  assert.equal(typeof contract.normalizePublicLoadStatus, 'function');
  for (const outcome of ['resolve', 'reject']) {
    const coordinator = contract.createLatestLoadCoordinator();
    const pending = deferred();
    const ticket = coordinator.begin();
    const publicResult = pending.promise.then(
      () => coordinator.succeed(ticket)
        ? 'ready'
        : contract.normalizePublicLoadStatus('disposed'),
      () => coordinator.fail(ticket)
        ? 'fallback'
        : contract.normalizePublicLoadStatus('disposed'),
    );

    coordinator.dispose();
    if (outcome === 'resolve') pending.resolve('late success');
    else pending.reject(new Error('late failure'));
    const status = await publicResult;

    assert.equal(status, 'fallback');
    assert.notEqual(status, 'loading');
    assert.ok(PUBLIC_LOAD_STATUSES.has(status));
  }
});

function validIdentity(overrides = {}) {
  return {
    name: 'policy_rate',
    econId: 'policy_rate',
    ready: true,
    meshChildren: [
      { name: 'policy_rate__body', role: 'body' },
      { name: 'policy_rate__accent', role: 'accent' },
    ],
    ...overrides,
  };
}

test('model identity requires explicit id, canonical root, ready flag, and exact role children', () => {
  assert.equal(typeof contract.validateNodeModelIdentity, 'function');
  assert.deepEqual(
    contract.validateNodeModelIdentity('policy_rate', validIdentity()),
    { valid: true, issues: [] },
  );

  const malformed = [
    validIdentity({ econId: undefined }),
    validIdentity({ name: 'PolicyRate' }),
    validIdentity({ ready: 1 }),
    validIdentity({ meshChildren: [
      { name: 'policy_rate__body', role: 'accent' },
      { name: 'policy_rate__accent', role: 'body' },
    ] }),
    validIdentity({ meshChildren: [
      { name: 'policy_rate__body', role: 'body' },
      { name: 'policy_rate__accent-copy', role: 'accent' },
    ] }),
    validIdentity({ meshChildren: [
      { name: 'policy_rate__body', role: 'body' },
      { name: 'policy_rate__accent', role: 'accent' },
      { name: 'policy_rate__detail', role: 'detail' },
    ] }),
  ];
  for (const candidate of malformed) {
    assert.equal(contract.validateNodeModelIdentity('policy_rate', candidate).valid, false);
  }
});

test('visual system tilts fallbacks and has one geometry disposal owner', () => {
  assert.match(visualSource, /record\.fallbackRoot\.rotation\.x/);
  assert.match(visualSource, /record\.fallbackRoot\.rotation\.y/);
  assert.doesNotMatch(visualSource, /loadedGeometries/);
});

test('visual system normalizes every stale or disposed load result', () => {
  assert.match(visualSource, /normalizePublicLoadStatus/);
  assert.equal(
    (visualSource.match(/status:\s*normalizePublicLoadStatus\s*\(/g) || []).length,
    3,
  );
});
