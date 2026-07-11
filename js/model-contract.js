export function validateModelContract(expectedIds, records) {
  const expected = new Set(expectedIds);
  const counts = new Map();

  for (const record of records) {
    counts.set(record.id, (counts.get(record.id) || 0) + 1);
  }

  const duplicates = [...counts]
    .filter(([, count]) => count > 1)
    .map(([id]) => id)
    .sort();
  const extra = [...counts.keys()]
    .filter((id) => !expected.has(id))
    .sort();
  const missing = expectedIds.filter((id) => !counts.has(id));
  const invalid = records.filter((record) => {
    const roles = record.roles || [];
    const bodyCount = roles.filter((role) => role === 'body').length;
    const accentCount = roles.filter((role) => role === 'accent').length;

    return expected.has(record.id) && counts.get(record.id) === 1 && (
      bodyCount !== 1 ||
      accentCount !== 1 ||
      roles.length !== 2 ||
      !Number.isFinite(record.radius) ||
      record.radius <= 0 ||
      !Number.isFinite(record.triangles) ||
      record.triangles <= 0 ||
      record.triangles > 3000 ||
      record.rootIdentity !== true
    );
  });
  const invalidIds = new Set(invalid.map((record) => record.id));
  const validIds = expectedIds.filter(
    (id) => counts.get(id) === 1 && !invalidIds.has(id),
  );

  return { validIds, missing, extra, duplicates, invalid };
}
