// Dependency-free contracts for the browser model loader. Keeping these
// policies pure makes overlap, disposal, and malformed GLB identity testable
// without importing Three.js through a browser import map.

export function createLatestLoadCoordinator() {
  let latestTicket = 0;
  let disposed = false;

  function accept(ticket, effect) {
    if (disposed || ticket !== latestTicket) return false;
    if (typeof effect === 'function') effect();
    return true;
  }

  return {
    begin() {
      if (disposed) return null;
      latestTicket += 1;
      return latestTicket;
    },
    succeed(ticket, effect) {
      return accept(ticket, effect);
    },
    fail(ticket, effect) {
      return accept(ticket, effect);
    },
    dispose() {
      disposed = true;
      latestTicket += 1;
    },
  };
}

export function validateNodeModelIdentity(expectedId, candidate) {
  const issues = [];
  if (typeof candidate?.econId !== 'string' || candidate.econId !== expectedId) {
    issues.push('econ-id');
  }
  if (candidate?.name !== expectedId) issues.push('root-name');
  if (candidate?.ready !== true) issues.push('ready');

  const expectedChildren = new Map([
    [`${expectedId}__body`, 'body'],
    [`${expectedId}__accent`, 'accent'],
  ]);
  const children = Array.isArray(candidate?.meshChildren) ? candidate.meshChildren : [];
  if (children.length !== expectedChildren.size) {
    issues.push('mesh-count');
  }
  for (const [name, role] of expectedChildren) {
    const exactMatches = children.filter((child) => child?.name === name && child?.role === role);
    if (exactMatches.length !== 1) issues.push(`${role}-child`);
  }
  if (children.some((child) => expectedChildren.get(child?.name) !== child?.role)) {
    issues.push('unexpected-child');
  }

  return { valid: issues.length === 0, issues: [...new Set(issues)] };
}
