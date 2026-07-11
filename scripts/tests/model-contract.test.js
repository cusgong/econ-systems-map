import test from 'node:test';
import assert from 'node:assert/strict';
import { validateModelContract } from '../../js/model-contract.js';

function validRecord(id, overrides = {}) {
  return {
    id,
    roles: ['body', 'accent'],
    radius: 1,
    triangles: 2100,
    rootIdentity: true,
    ...overrides,
  };
}

test('keeps valid records and isolates invalid or duplicate models', () => {
  const result = validateModelContract(['policy_rate', 'fx'], [
    { id: 'policy_rate', roles: ['body', 'accent'], radius: 1, triangles: 2100, rootIdentity: true },
    { id: 'policy_rate', roles: ['body', 'accent'], radius: 1, triangles: 2100, rootIdentity: true },
    { id: 'fx', roles: ['body'], radius: 0, triangles: 0, rootIdentity: false },
    { id: 'alien', roles: ['body', 'accent'], radius: 1, triangles: 50, rootIdentity: true },
  ]);

  assert.deepEqual(result.validIds, []);
  assert.deepEqual(result.missing, []);
  assert.deepEqual(result.extra, ['alien']);
  assert.deepEqual(result.duplicates, ['policy_rate']);
  assert.deepEqual(result.invalid.map((record) => record.id), ['fx']);
});

test('keeps valid and missing ids in expected order', () => {
  const result = validateModelContract(['policy_rate', 'fx', 'inflation'], [
    validRecord('fx', { triangles: 3000 }),
    validRecord('policy_rate'),
  ]);

  assert.deepEqual(result.validIds, ['policy_rate', 'fx']);
  assert.deepEqual(result.missing, ['inflation']);
  assert.deepEqual(result.extra, []);
  assert.deepEqual(result.duplicates, []);
  assert.deepEqual(result.invalid, []);
});

test('rejects unique expected records outside structural boundaries', () => {
  const invalidIds = [
    'missing_accent',
    'duplicate_body',
    'zero_radius',
    'infinite_radius',
    'zero_triangles',
    'excess_triangles',
    'infinite_triangles',
    'transformed_root',
  ];
  const result = validateModelContract(invalidIds, [
    validRecord('missing_accent', { roles: ['body'] }),
    validRecord('duplicate_body', { roles: ['body', 'body', 'accent'] }),
    validRecord('zero_radius', { radius: 0 }),
    validRecord('infinite_radius', { radius: Number.POSITIVE_INFINITY }),
    validRecord('zero_triangles', { triangles: 0 }),
    validRecord('excess_triangles', { triangles: 3001 }),
    validRecord('infinite_triangles', { triangles: Number.POSITIVE_INFINITY }),
    validRecord('transformed_root', { rootIdentity: 1 }),
  ]);

  assert.deepEqual(result.validIds, []);
  assert.deepEqual(result.missing, []);
  assert.deepEqual(result.extra, []);
  assert.deepEqual(result.duplicates, []);
  assert.deepEqual(result.invalid.map((record) => record.id), invalidIds);
});
