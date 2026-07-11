// Pure transform evaluator for event-driven accent signatures.

const AXES = Object.freeze({
  x: Object.freeze([1, 0, 0]),
  y: Object.freeze([0, 1, 0]),
  z: Object.freeze([0, 0, 1]),
});

function finite(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function vector(value, defaults) {
  return defaults.map((fallback, index) => finite(value?.[index], fallback));
}

function normalizeQuaternion(quaternion) {
  const length = Math.hypot(...quaternion);
  if (length <= Number.EPSILON) return [0, 0, 0, 1];
  return quaternion.map((value) => value / length);
}

function multiplyQuaternion(a, b) {
  const [ax, ay, az, aw] = a;
  const [bx, by, bz, bw] = b;
  return [
    aw * bx + ax * bw + ay * bz - az * by,
    aw * by - ax * bz + ay * bw + az * bx,
    aw * bz + ax * by - ay * bx + az * bw,
    aw * bw - ax * bx - ay * by - az * bz,
  ];
}

function rotateVector(value, quaternion) {
  const [x, y, z] = value;
  const [qx, qy, qz, qw] = normalizeQuaternion(quaternion);
  const tx = 2 * (qy * z - qz * y);
  const ty = 2 * (qz * x - qx * z);
  const tz = 2 * (qx * y - qy * x);
  return [
    x + qw * tx + (qy * tz - qz * ty),
    y + qw * ty + (qz * tx - qx * tz),
    z + qw * tz + (qx * ty - qy * tx),
  ];
}

function axisFor(name) {
  return AXES[name] || AXES.z;
}

export function evaluateSignatureTransform(base, options = {}) {
  const position = vector(base?.position, [0, 0, 0]);
  const quaternion = vector(base?.quaternion, [0, 0, 0, 1]);
  const scale = vector(base?.scale, [1, 1, 1]);
  const signature = options.signature;
  const amount = finite(options.amount, 0);
  const wave = finite(options.wave, 0);
  const axis = axisFor(options.axis);

  if (signature === 'rotate') {
    const halfAngle = amount * wave * 0.5;
    const sine = Math.sin(halfAngle);
    const delta = [axis[0] * sine, axis[1] * sine, axis[2] * sine, Math.cos(halfAngle)];
    const rotated = normalizeQuaternion(multiplyQuaternion(quaternion, delta));
    quaternion.splice(0, quaternion.length, ...rotated);
  } else if (signature === 'translate') {
    const distance = amount * wave;
    const displacement = rotateVector(
      [axis[0] * distance, axis[1] * distance, axis[2] * distance],
      quaternion,
    );
    position[0] += displacement[0];
    position[1] += displacement[1];
    position[2] += displacement[2];
  } else if (signature === 'scale') {
    const multiplier = 1 + amount * wave;
    scale[0] *= multiplier;
    scale[1] *= multiplier;
    scale[2] *= multiplier;
  }

  const arrivalScale = finite(options.arrivalScale, 1);
  scale[0] *= arrivalScale;
  scale[1] *= arrivalScale;
  scale[2] *= arrivalScale;

  return { position, quaternion, scale };
}
