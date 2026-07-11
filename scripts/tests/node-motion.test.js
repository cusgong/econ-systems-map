import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const moduleUrl = new URL('../../js/node-motion.js', import.meta.url);

async function loadMotionModule() {
  assert.ok(existsSync(fileURLToPath(moduleUrl)), 'node-motion.js must exist');
  return import(moduleUrl.href);
}

function near(actual, expected, tolerance = 1e-9) {
  assert.equal(actual.length, expected.length);
  actual.forEach((value, index) => {
    assert.ok(
      Math.abs(value - expected[index]) <= tolerance,
      `index ${index}: expected ${expected[index]}, received ${value}`,
    );
  });
}

const BASE = Object.freeze({
  position: Object.freeze([3, -2, 5]),
  quaternion: Object.freeze([0, 0, 0, 1]),
  scale: Object.freeze([2, 3, 4]),
});

test('an inactive signature returns an independent copy of the base transform', async () => {
  const { evaluateSignatureTransform } = await loadMotionModule();
  const result = evaluateSignatureTransform(BASE, {});

  assert.deepEqual(result, {
    position: [3, -2, 5],
    quaternion: [0, 0, 0, 1],
    scale: [2, 3, 4],
  });
  assert.notEqual(result.position, BASE.position);
  assert.notEqual(result.quaternion, BASE.quaternion);
  assert.notEqual(result.scale, BASE.scale);
});

test('rotate composes a local axis-angle rotation onto the base quaternion', async () => {
  const { evaluateSignatureTransform } = await loadMotionModule();
  const result = evaluateSignatureTransform(BASE, {
    signature: 'rotate',
    axis: 'z',
    amount: Math.PI / 2,
    wave: 1,
  });

  near(result.quaternion, [0, 0, Math.SQRT1_2, Math.SQRT1_2]);
  near(result.position, BASE.position);
  near(result.scale, BASE.scale);
});

test('translate follows the signed local axis after base rotation', async () => {
  const { evaluateSignatureTransform } = await loadMotionModule();
  const quarterTurnZ = [0, 0, Math.SQRT1_2, Math.SQRT1_2];
  const result = evaluateSignatureTransform({
    position: [10, 20, 30],
    quaternion: quarterTurnZ,
    scale: [1, 1, 1],
  }, {
    signature: 'translate',
    axis: 'x',
    amount: 2,
    wave: -0.5,
  });

  near(result.position, [10, 19, 30]);
  near(result.quaternion, quarterTurnZ);
});

test('scale applies one uniform multiplier to every base scale component', async () => {
  const { evaluateSignatureTransform } = await loadMotionModule();
  const result = evaluateSignatureTransform(BASE, {
    signature: 'scale',
    axis: 'xyz',
    amount: 0.2,
    wave: 0.5,
  });

  near(result.scale, [2.2, 3.3, 4.4]);
  near(result.position, BASE.position);
  near(result.quaternion, BASE.quaternion);
});

test('arrival pulse multiplies scale after signature evaluation', async () => {
  const { evaluateSignatureTransform } = await loadMotionModule();
  const result = evaluateSignatureTransform(BASE, {
    signature: 'scale',
    amount: 0.25,
    wave: 0.4,
    arrivalScale: 1.08,
  });

  near(result.scale, [2.376, 3.564, 4.752]);
  assert.deepEqual(BASE, {
    position: [3, -2, 5],
    quaternion: [0, 0, 0, 1],
    scale: [2, 3, 4],
  });
});
