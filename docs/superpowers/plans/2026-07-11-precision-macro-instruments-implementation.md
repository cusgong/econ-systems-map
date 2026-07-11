# Precision Macro Instruments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 30개 경제 변수를 각기 다른 전문적인 Blender 3D 오브제로 표시하고, 크기는 직·간접 인과 허브성, 색은 역할 범주, 움직임은 선택·전파 상태를 전달하는 v2.5.0 지도를 만든다.

**Architecture:** 기존 구체를 즉시 표시되는 개별 폴백으로 유지한 채, 단일 glTF 바이너리(GLB) 라이브러리를 비동기로 읽어 유효한 모델만 점진 교체한다. 허브 점수와 모델 계약은 순수 모듈로 분리해 Node.js로 검증하고, Three.js 노드 시각 시스템은 모델·상태 링·히트 프록시·2D 라벨을 한 계층으로 관리한다. Blender `.blend` 파일이 조형의 정본이며, 검증·내보내기만 자동화한다.

**Tech Stack:** Blender 5.1.2, Blender Python API, Three.js r170 물리 기반 렌더링(PBR), `GLTFLoader`, `RoomEnvironment`, `BufferGeometryUtils`, 정적 ES 모듈, Node.js 24 내장 테스트 러너, Python 3.14 보조 검증, CSS2DRenderer.

## Global Constraints

- 정적 사이트와 무빌드 구조를 유지한다. 런타임 CDN과 새 서버 의존성을 추가하지 않는다.
- Three.js 코어와 모든 부가 모듈은 r170으로 맞춘다.
- Blender 저작·자동화·내보내기는 모두 5.1.2로 맞춘다. Store판과 다른 Blender 버전을 섞지 않는다.
- 30개 canonical ID는 `data/nodes.js`를 단일 진실원으로 삼는다.
- 30개 모두 서로 다른 주 실루엣을 사용한다. 같은 모델의 색·크기 변형으로 대체하지 않는다.
- 범주색은 표면의 10~20%인 인레이·눈금·렌즈·내부광에만 사용하며 상태 변화가 본래 범주색을 덮지 않는다.
- 기존 위치 의미를 바꾸지 않는다. 높이=경제 층위, 반경=국내·글로벌 거리, 각도=부문이다.
- 크기는 1~3홉의 강도·확실성 가중 인과 허브 점수를 사용하며 반지름 범위는 0.82~1.28이다.
- 기본 상태는 정지한다. 상시 모델 회전, 노드 광륜 호흡, 전신 발광을 제거한다.
- 모션 감소 환경에서는 기계 동작을 모두 제거하고 링·명암만 사용한다.
- 모델당 렌더 프리미티브는 원칙적으로 2개, 예외적으로 3개 이하다.
- 전체 모델은 45,000~90,000 삼각형, 하드 실패는 100,000 초과다.
- GLB는 2,000,000바이트 이하 목표, 3,000,000바이트 초과 시 실패한다.
- 기본 장면 전체 드로콜은 150 이하 목표, 180 초과 시 실패한다.
- GLB 실패·일부 ID 누락·비정상 경계구는 해당 노드의 기존 구체 폴백으로 복구한다.
- 한국어·영어 라벨과 키보드·리스트 모드·딥링크·레버 드래그를 보존한다.
- 배포와 원격 push는 이 구현 계획의 자동 권한에 포함하지 않는다. 별도 사용자 지시 후 수행한다.

---

## 확인된 현재 환경

- Microsoft Store판 Blender `5.1.2.0`이 설치되어 있다.
- 패키지 경로는 `C:\Program Files\WindowsApps\BlenderFoundation.Blender_5.1.2.0_x64__ppwjx1n5r4v9t`다.
- Store 패키지 내부 `blender.exe`는 현재 셸에서 `Access Denied`가 발생한다.
- 앱 실행 별칭 `blender-launcher.exe`는 인자를 전달할 수 있지만 표준 출력·오류가 보이지 않아 자동 검증용으로 부적합하다.
- `winget`의 공식 독립 실행 설치 항목은 `BlenderFoundation.Blender` 버전 `5.1.2`다.
- Node.js는 `v24.12.0`, Python은 `3.14.2`, Three.js는 r170이다.
- 현재 테스트용 `package.json`과 자동 브라우저 테스트는 없다.

## 파일 구조와 책임

### 새 파일

| 파일 | 책임 |
|---|---|
| `package.json` | 무빌드 테스트 명령과 ES 모듈 모드만 선언 |
| `js/hub-metrics.js` | 1~3홉 인과 허브 점수·반지름·범례 구간 계산 |
| `js/model-contract.js` | 런타임 GLB의 ID·역할·경계·삼각형 계약을 순수 데이터로 검증 |
| `js/node-visual-system.js` | 폴백, GLB 교체, PBR 재질, 상태 링, 히트 프록시, 라벨, 서명 동작 소유 |
| `scripts/tests/hub-metrics.test.js` | 합성 그래프 규칙과 30개 점수 스냅샷 검증 |
| `scripts/tests/model-contract.test.js` | 누락·중복·잘못된 역할·경계 폴백 검증 |
| `scripts/tests/graph-regression.test.js` | 30노드·107엣지와 기존 ripple·propagate 회귀 검증 |
| `scripts/blender/node-specs.py` | 30개 ID의 서명 동작·증명 집합·검증 범위 정의 |
| `scripts/blender/scaffold-econ-node-library.py` | Blender 장면·컬렉션·루트·재질·QA 골격 생성 |
| `scripts/blender/validate-econ-node-library.py` | `.blend`와 GLB의 구조·형상·성능 계약 검증 |
| `scripts/blender/export-econ-node-library.py` | 임시 GLB 내보내기, 사후검증, 성공 시 원자적 교체 |
| `scripts/blender/README.md` | 고정 Blender 경로, 저작·검증·내보내기 명령 |
| `scripts/blender/econ-node-library.blend` | 30개 모델의 조형 정본 |
| `data/models/econ-node-library.glb` | 브라우저가 읽는 단일 런타임 모델 라이브러리 |
| `vendor/addons/loaders/GLTFLoader.js` | r170 로컬 GLB 로더 |
| `vendor/addons/environments/RoomEnvironment.js` | r170 로컬 PBR 환경광 |
| `vendor/addons/utils/BufferGeometryUtils.js` | r170 엣지 기하 배치 도구 |
| `vendor/THREE-LICENSE.txt` | vendored Three.js 라이선스 |

### 수정 파일

| 파일 | 변경 책임 |
|---|---|
| `js/main.js` | 허브 점수 계산, 노드 라이브러리 URL·킬스위치 전달, v2.5.0 버전 |
| `js/scene.js` | PBR 렌더러 설정, 노드 시각 시스템 연결, 엣지 배치, raycast·레버 계약 유지 |
| `js/ui.js` | 변수 상세 허브 점수, 크기 범례, 압력 오버레이 호출명 연결 |
| `css/main.css` | 허브 범례, 로딩·폴백 상태, 고대비 라벨·상태 링 보조 스타일 |
| `data/strings.js` | 허브·모델 로딩·폴백 설명의 영어 번역 |
| `.gitignore` | Blender 자동 백업·캐시 제외, `.blend` 정본은 포함 |
| `README.md` | 모델·Blender·테스트 폴더와 명령 설명 |
| `PLAN.md` | M6 진행 단계와 검증 게이트 갱신 |
| `docs/plan.md` | v2.5.0 목표·위험·마일스톤 반영 |
| `docs/session-log.md` | 로컬 연속성 기록, 기존 ignore 정책 유지 |
| `docs/superpowers/specs/2026-07-11-precision-macro-instruments-design.md` | 승인·Blender 5.1.2·전역 고유 메시 이름 계약 유지 |

## 공통 Blender 객체 계약

```text
SCENE__ECON_NODE_LIBRARY
└─ MASTER__ECON_NODE_LIBRARY
   ├─ 00_ASSETS
   │  └─ NODE__<id>
   │     └─ <id>                       EMPTY, canonical root
   │        ├─ <id>__body              MESH, econ_role="body"
   │        └─ <id>__accent            MESH, econ_role="accent"
   ├─ 10_WIP                           cutters, curves, references
   └─ 90_QA                            cameras, lights, axis guides, export 제외
```

루트 사용자 속성은 다음과 같이 고정한다.

```text
econ_id              canonical ID
econ_schema_version  1
econ_ready           true | false
econ_signature       rotate | translate | scale
econ_axis            x | y | z | xyz
econ_amount          finite number
econ_duration        seconds, 0.16~0.32
```

Blender 저작 좌표는 `+Z`가 위, `-Y`가 정면이다. `export_yup=True`로 내보낸 GLB는 `+Y`가 위, `+Z`가 정면이다. 루트 변환은 항등값이고, 결합 경계구 중심은 원점에서 `0.05 × radius` 이내, 원본 경계구 반지름은 `1.00 ± 0.02`로 맞춘다. `econ_axis`는 내보낸 GLB 좌표를 기준으로 해석한다. 각 body·accent 메시에는 재질 슬롯을 정확히 하나만 두어 모델당 렌더 프리미티브가 두 개를 넘지 않게 한다.

---

### Task 1: 무빌드 테스트 기반과 허브 점수 구현

**Files:**
- Create: `package.json`
- Create: `js/hub-metrics.js`
- Create: `scripts/tests/hub-metrics.test.js`
- Create: `scripts/tests/graph-regression.test.js`

**Interfaces:**
- Consumes: `buildGraph(NODES, EDGES)` 반환값
- Produces: `computeHubMetrics(graph, options) => Map<string, HubMetric>`
- Produces: `radiusScaleFor(hubScore) => number`
- Produces: `hubBandFor(hubScore) => "low" | "medium" | "high"`
- `HubMetric`: `{outInfluence, inExposure, hubRaw, hubScore, score100, radiusScale, band}`

- [ ] **Step 1: 테스트 명령을 선언한다**

```json
{
  "name": "econ-systems-map",
  "private": true,
  "type": "module",
  "scripts": {
    "test": "node --test scripts/tests/*.test.js",
    "test:hub": "node --test scripts/tests/hub-metrics.test.js",
    "test:graph": "node --test scripts/tests/graph-regression.test.js"
  },
  "engines": { "node": ">=24" }
}
```

- [ ] **Step 2: 합성 그래프와 현재 30개 점수 스냅샷의 실패 테스트를 작성한다**

테스트는 다음을 각각 독립 사례로 고정한다.

- 첫 홉에는 깊이 감쇠가 붙지 않는다.
- 2·3홉에는 홉마다 `0.68`이 붙는다.
- 같은 도착점은 최강 경로 하나만 합산한다.
- 경로 안에서 노드를 다시 방문하지 않는다.
- 발신 60%, 수신 40%를 사용한다.
- 10~90 백분위 절삭 뒤 0~1 범위를 보장한다.
- `policy_rate`, `cpi`, `consumption`은 현재 데이터에서 100점이며 `current_account`, `commodity`, `consumer_conf`는 0점이다.

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { NODES } from '../../data/nodes.js';
import { EDGES } from '../../data/edges.js';
import { buildGraph } from '../../js/graph.js';
import { computeHubMetrics, radiusScaleFor } from '../../js/hub-metrics.js';

test('current graph produces deterministic 30-node hub snapshot', () => {
  const metrics = computeHubMetrics(buildGraph(NODES, EDGES));
  const actual = Object.fromEntries([...metrics].map(([id, v]) => [id, v.score100]));
  assert.equal(metrics.size, 30);
  assert.deepEqual(actual, {
    policy_rate:100, market_rate:77, liquidity:7, credit_spread:4, bank_lending:63,
    cpi:100, inflation_exp:71, wages:60, fx:59, exports:90, current_account:0,
    capital_flows:40, fed_rate:8, global_growth:47, consumption:100, investment:56,
    employment:98, earnings:80, defaults:73, gdp:99, stocks:23, housing:20,
    household_debt:13, oil:75, commodity:0, fiscal:18, geopolitics:88, tech:50,
    risk_sentiment:27, consumer_conf:0,
  });
});

test('radius mapping preserves the approved area scale', () => {
  assert.equal(radiusScaleFor(0), 0.82);
  assert.equal(radiusScaleFor(1), 1.28);
});
```

- [ ] **Step 3: 실패를 확인한다**

Run: `npm test`

Expected: FAIL with `ERR_MODULE_NOT_FOUND` for `js/hub-metrics.js`.

- [ ] **Step 4: 순수 허브 계산을 구현한다**

```js
const DEFAULTS = Object.freeze({ maxDepth: 3, decay: 0.68, outWeight: 0.60, inWeight: 0.40 });
const MIN_RADIUS = 0.82;
const MAX_RADIUS = 1.28;

function normalize(values) {
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  return values.map((v) => hi === lo ? 0.5 : (v - lo) / (hi - lo));
}

function quantile(sorted, p) {
  const x = (sorted.length - 1) * p;
  const a = Math.floor(x);
  const b = Math.ceil(x);
  return sorted[a] + (sorted[b] - sorted[a]) * (x - a);
}

function strongestReach(graph, origin, { maxDepth, decay }) {
  const best = new Map();
  function walk(id, depth, score, seen) {
    if (depth >= maxDepth) return;
    for (const edge of graph.out.get(id) || []) {
      if (seen.has(edge.to)) continue;
      const quality = (edge.strength / 3) * (edge.confidence / 3);
      const nextScore = score * quality * (depth === 0 ? 1 : decay);
      if (nextScore > (best.get(edge.to) || 0)) best.set(edge.to, nextScore);
      walk(edge.to, depth + 1, nextScore, new Set([...seen, edge.to]));
    }
  }
  walk(origin, 0, 1, new Set([origin]));
  return best;
}

export function radiusScaleFor(score) {
  const s = Math.max(0, Math.min(1, score));
  const value = Math.sqrt(MIN_RADIUS ** 2 + (MAX_RADIUS ** 2 - MIN_RADIUS ** 2) * s);
  return Number(value.toFixed(6));
}

export function hubBandFor(score) {
  return score < 1 / 3 ? 'low' : score < 2 / 3 ? 'medium' : 'high';
}

export function computeHubMetrics(graph, options = {}) {
  const opts = { ...DEFAULTS, ...options };
  const ids = graph.nodes.map((node) => node.id);
  const reaches = new Map(ids.map((id) => [id, strongestReach(graph, id, opts)]));
  const outgoing = ids.map((id) => [...reaches.get(id).values()].reduce((a, b) => a + b, 0));
  const incoming = ids.map((target) => ids.reduce((sum, origin) => sum + (reaches.get(origin).get(target) || 0), 0));
  const outNorm = normalize(outgoing);
  const inNorm = normalize(incoming);
  const raw = ids.map((id, i) => opts.outWeight * outNorm[i] + opts.inWeight * inNorm[i]);
  const sorted = [...raw].sort((a, b) => a - b);
  const lo = quantile(sorted, 0.10);
  const hi = quantile(sorted, 0.90);
  return new Map(ids.map((id, i) => {
    const score = hi === lo ? 0.5 : Math.max(0, Math.min(1, (raw[i] - lo) / (hi - lo)));
    return [id, Object.freeze({
      outInfluence: outgoing[i], inExposure: incoming[i], hubRaw: raw[i], hubScore: score,
      score100: Math.round(score * 100), radiusScale: radiusScaleFor(score), band: hubBandFor(score),
    })];
  }));
}
```

- [ ] **Step 5: 기존 그래프 회귀 테스트를 고정한다**

`scripts/tests/graph-regression.test.js`는 30개 노드, 107개 유효 엣지, 대표 `ripple()` 경로 깊이, 대표 `propagate()` 부호를 검증한다. 허브 계산은 기존 `ripple()`·`propagate()`를 수정하지 않는다.

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { NODES } from '../../data/nodes.js';
import { EDGES } from '../../data/edges.js';
import { buildGraph, ripple, propagate } from '../../js/graph.js';

const graph = buildGraph(NODES, EDGES);

test('canonical graph shape stays stable', () => {
  assert.equal(graph.nodes.length, 30);
  assert.equal(graph.edges.length, 107);
});

test('policy-rate ripple keeps direct market channels', () => {
  const result = ripple(graph, 'policy_rate', 'down', 3);
  assert.equal(result.nodes.get('market_rate').order, 1);
  assert.equal(result.nodes.get('liquidity').order, 1);
});

test('policy-rate shock preserves representative signs', () => {
  const result = new Map(propagate(graph, { policy_rate: 1 }).map((row) => [row.id, row.value]));
  assert.ok(result.get('market_rate') > 0);
  assert.ok(result.get('liquidity') < 0);
});
```

- [ ] **Step 6: 테스트를 통과시킨다**

Run: `npm test`

Expected: PASS, 0 failures.

- [ ] **Step 7: 커밋한다**

```powershell
git add package.json js/hub-metrics.js scripts/tests
git -c user.name="Marcus Gong" -c user.email="globin0806@gmail.com" commit -m "feat: add causal hub metrics"
```

---

### Task 2: 런타임 모델 계약을 테스트 우선으로 구현

**Files:**
- Create: `js/model-contract.js`
- Create: `scripts/tests/model-contract.test.js`

**Interfaces:**
- Consumes: `expectedIds: string[]`, `records: ModelRecord[]`
- `ModelRecord`: `{id, roles, radius, triangles, rootIdentity}`
- Produces: `validateModelContract(expectedIds, records) => {validIds, missing, extra, duplicates, invalid}`

- [ ] **Step 1: 누락·중복·비정상 경계의 실패 테스트를 작성한다**

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { validateModelContract } from '../../js/model-contract.js';

test('keeps valid records and isolates invalid or duplicate models', () => {
  const result = validateModelContract(['policy_rate', 'fx'], [
    { id:'policy_rate', roles:['body','accent'], radius:1, triangles:2100, rootIdentity:true },
    { id:'policy_rate', roles:['body','accent'], radius:1, triangles:2100, rootIdentity:true },
    { id:'fx', roles:['body'], radius:0, triangles:0, rootIdentity:false },
    { id:'alien', roles:['body','accent'], radius:1, triangles:50, rootIdentity:true },
  ]);
  assert.deepEqual(result.validIds, []);
  assert.deepEqual(result.missing, []);
  assert.deepEqual(result.extra, ['alien']);
  assert.deepEqual(result.duplicates, ['policy_rate']);
  assert.deepEqual(result.invalid.map((x) => x.id), ['fx']);
});
```

- [ ] **Step 2: 실패를 확인한다**

Run: `node --test --test-name-pattern="isolates" scripts/tests/model-contract.test.js`

Expected: FAIL with `ERR_MODULE_NOT_FOUND` for `js/model-contract.js`.

- [ ] **Step 3: 계약 검증을 구현한다**

```js
export function validateModelContract(expectedIds, records) {
  const expected = new Set(expectedIds);
  const counts = new Map();
  for (const record of records) counts.set(record.id, (counts.get(record.id) || 0) + 1);
  const duplicates = [...counts].filter(([, count]) => count > 1).map(([id]) => id).sort();
  const extra = [...counts.keys()].filter((id) => !expected.has(id)).sort();
  const missing = expectedIds.filter((id) => !counts.has(id));
  const invalid = records.filter((record) => {
    const roles = record.roles || [];
    const bodyCount = roles.filter((role) => role === 'body').length;
    const accentCount = roles.filter((role) => role === 'accent').length;
    return expected.has(record.id) && counts.get(record.id) === 1 &&
      (bodyCount !== 1 || accentCount !== 1 || roles.length !== 2 ||
      !Number.isFinite(record.radius) || record.radius <= 0 ||
      !Number.isFinite(record.triangles) || record.triangles <= 0 || record.triangles > 3000 ||
      record.rootIdentity !== true);
  });
  const invalidIds = new Set(invalid.map((record) => record.id));
  const validIds = expectedIds.filter((id) => counts.get(id) === 1 && !invalidIds.has(id));
  return { validIds, missing, extra, duplicates, invalid };
}
```

- [ ] **Step 4: 테스트를 통과시킨다**

Run: `npm test`

Expected: PASS, 0 failures.

- [ ] **Step 5: 커밋한다**

```powershell
git add js/model-contract.js scripts/tests/model-contract.test.js
git -c user.name="Marcus Gong" -c user.email="globin0806@gmail.com" commit -m "test: define node model contract"
```

---

### Task 3: Blender 자동화 경로와 첫 수직 슬라이스를 만든다

**Files:**
- Modify: `.gitignore`
- Create: `scripts/blender/node-specs.py`
- Create: `scripts/blender/scaffold-econ-node-library.py`
- Create: `scripts/blender/validate-econ-node-library.py`
- Create: `scripts/blender/export-econ-node-library.py`
- Create: `scripts/blender/README.md`
- Create: `scripts/blender/econ-node-library.blend`
- Create: `data/models/econ-node-library.glb`

**Interfaces:**
- Consumes: `data/nodes.js` canonical IDs and categories
- Produces: `.blend` with `econ_ready=true` roots
- Produces: one GLB whose ready root names equal canonical IDs
- Produces: JSON validation summary with `readyCount`, `triangles`, `primitives`, `bytes`, `errors`

- [ ] **Step 1: 명령줄 실행 가능한 Blender 5.1.2를 고정한다**

먼저 일반 설치 경로를 확인한다.

```powershell
$Blender = 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
if (-not (Test-Path -LiteralPath $Blender)) {
  winget install --exact --id BlenderFoundation.Blender --version 5.1.2 --source winget --force --silent --accept-package-agreements --accept-source-agreements
}
& $Blender --version
```

Expected: 첫 줄에 `Blender 5.1.2`가 출력되고 exit code 0이다. MSI 설치가 권한 문제로 실패하면 공식 ZIP `https://download.blender.org/release/Blender5.1/blender-5.1.2-windows-x64.zip`을 `%LOCALAPPDATA%\Programs\Blender\5.1.2`에 풀고 그 `blender.exe`를 사용한다. Store판은 그대로 둔다.

- [ ] **Step 2: 30개 서명 동작 계약을 작성한다**

```python
PROOF_IDS = ("policy_rate", "fx", "oil", "housing", "gdp", "risk_sentiment")
NODE_MOTIONS = {
    "policy_rate": ("rotate", "z", 0.20), "market_rate": ("translate", "x", 0.12),
    "liquidity": ("rotate", "y", 0.35), "credit_spread": ("translate", "x", 0.10),
    "bank_lending": ("translate", "z", 0.12), "cpi": ("rotate", "z", 0.22),
    "inflation_exp": ("translate", "z", 0.12), "wages": ("rotate", "z", 0.18),
    "fx": ("rotate", "y", 0.26), "exports": ("translate", "z", 0.12),
    "current_account": ("rotate", "z", 0.16), "capital_flows": ("translate", "z", 0.13),
    "fed_rate": ("rotate", "y", 0.28), "global_growth": ("scale", "xyz", 0.06),
    "consumption": ("scale", "xyz", 0.06), "investment": ("rotate", "x", 0.18),
    "employment": ("translate", "y", 0.12), "earnings": ("translate", "y", 0.12),
    "defaults": ("rotate", "z", 0.16), "gdp": ("scale", "xyz", 0.07),
    "stocks": ("translate", "y", 0.14), "housing": ("translate", "y", 0.12),
    "household_debt": ("rotate", "y", 0.20), "oil": ("rotate", "z", 0.52),
    "commodity": ("translate", "y", 0.10), "fiscal": ("rotate", "z", 0.16),
    "geopolitics": ("rotate", "y", 0.18), "tech": ("rotate", "z", 0.45),
    "risk_sentiment": ("rotate", "z", 0.30), "consumer_conf": ("translate", "y", 0.12),
}
```

`node-specs.py`는 `data/nodes.js`의 `NODES` 블록을 읽어 위 키 집합과 정확히 일치하는지 import 시점에 검사한다.

- [ ] **Step 3: idempotent 스캐폴드와 장면 계약을 구현한다**

재실행 안전(idempotent) 스캐폴드는 기존에 비어 있지 않은 메시를 절대 교체하지 않는다. `SCENE__ECON_NODE_LIBRARY`, `MASTER__ECON_NODE_LIBRARY`, `00_ASSETS`, `10_WIP`, `90_QA`, 30개 `NODE__<id>` 컬렉션, canonical 루트, 공용 재질을 만든다. 모든 루트는 `econ_ready=false`로 시작한다.

공용 재질 이름은 다음 13개로 제한한다.

```text
MAT__DARK_TITANIUM
MAT__SATIN_ALLOY
MAT__TECHNICAL_CERAMIC
MAT__ACCENT__POLICY
MAT__ACCENT__MONETARY
MAT__ACCENT__ASSETS
MAT__ACCENT__PSYCHOLOGY
MAT__ACCENT__REAL
MAT__ACCENT__PRICES
MAT__ACCENT__COMMODITIES
MAT__ACCENT__EXOGENOUS
MAT__ACCENT__EXTERNAL
MAT__SMOKED_LENS
```

- [ ] **Step 4: 검증과 원자적 내보내기를 구현한다**

검증기는 `--scope ready|proof|full`을 받고 다음을 실패로 처리한다.

- canonical ID 불일치, 중복 이름, `.001` 접미사
- `econ_role` 누락, 몸체·악센트 외 렌더 메시
- body·accent 메시당 재질 슬롯이 하나가 아니거나 모델당 GLB primitive가 두 개가 아님
- 루트 비항등 변환, 비유한·0 경계, 중심 오차 초과
- 느슨한 기하, 비다양체 엣지, 0면적 면, 잘못된 노멀
- 모델당 3,000 삼각형 초과, 전체 100,000 초과
- 카메라·조명·애니메이션·스킨·이미지·필수 확장 포함
- GLB 3,000,000바이트 초과

내보내기 연산자는 다음 옵션을 명시한다.

```python
bpy.ops.export_scene.gltf(
    filepath=temp_glb, export_format="GLB", use_selection=True,
    export_yup=True, export_apply=True, export_normals=True,
    export_tangents=False, export_texcoords=False,
    export_materials="EXPORT", export_image_format="NONE",
    export_vertex_color="NONE", export_cameras=False, export_lights=False,
    export_extras=True, export_animations=False, export_skins=False,
    export_morph=False, export_draco_mesh_compression_enable=False,
    use_mesh_edges=False, use_mesh_vertices=False,
)
```

임시 GLB의 사후검증이 성공한 경우에만 `data/models/econ-node-library.glb`를 교체한다.

- [ ] **Step 5: `policy_rate`를 첫 완성 모델로 저작한다**

- 64분할 저상 원형 베이스, 48분할 제어 크라운, 12개 널링 돌기, 세 개의 보정 홈을 하나의 `policy_rate__body`로 결합한다.
- 눈금 바늘과 얇은 인레이 링을 `policy_rate__accent` 하나로 결합한다.
- 베벨은 모델 지름의 1.5~3%, 3세그먼트로 적용한다.
- 본체는 1,800~2,200 삼각형, 악센트 면적은 전체의 10~20%로 맞춘다.
- 악센트 원점은 바늘 회전 중심이며 `econ_signature="rotate"`, `econ_axis="z"`, `econ_amount=0.20`을 둔다.
- 정면·측면·상면 흑백 실루엣에서 크라운과 바늘이 읽히면 `econ_ready=true`로 바꾼다.

- [ ] **Step 6: 수직 슬라이스를 내보내고 검증한다**

```powershell
$Project = "C:\MG's Workspace\projects\econ-systems-map_personal_260710"
$Blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $Blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python "$Project\scripts\blender\scaffold-econ-node-library.py" -- --output "$Project\scripts\blender\econ-node-library.blend"
& $Blender --background --factory-startup --disable-autoexec "$Project\scripts\blender\econ-node-library.blend" --python-exit-code 1 --python "$Project\scripts\blender\validate-econ-node-library.py" -- --scope ready
& $Blender --background --factory-startup --disable-autoexec "$Project\scripts\blender\econ-node-library.blend" --python-exit-code 1 --python "$Project\scripts\blender\export-econ-node-library.py" -- --scope ready --output "$Project\data\models\econ-node-library.glb"
```

Expected: `readyCount=1`, `errors=[]`, 모델 3,000 삼각형 이하, GLB 200KB 이하.

- [ ] **Step 7: Blender 임시 파일을 제외한다**

`.gitignore`에 `*.blend1`, `*.blend2`, `*.blend@`, `scripts/blender/__pycache__/`를 추가한다. `econ-node-library.blend`는 포함한다.

- [ ] **Step 8: 커밋한다**

```powershell
git add .gitignore scripts/blender data/models/econ-node-library.glb
git -c user.name="Marcus Gong" -c user.email="globin0806@gmail.com" commit -m "feat: establish blender node asset pipeline"
```

---

### Task 4: Three.js PBR 수직 슬라이스와 개별 폴백을 연결

**Files:**
- Create: `vendor/addons/loaders/GLTFLoader.js`
- Create: `vendor/addons/environments/RoomEnvironment.js`
- Create: `vendor/addons/utils/BufferGeometryUtils.js`
- Create: `vendor/THREE-LICENSE.txt`
- Create: `js/node-visual-system.js`
- Modify: `js/scene.js:50-100,167-238,330-528,576-757`
- Modify: `js/main.js:1-120`

**Interfaces:**
- Consumes: `graph`, `categories`, `hubMetrics`, `nodeLibraryUrl`, `reducedMotion`
- Produces: `createNodeVisualSystem(options)` API
- Preserves: scene outward API `setHighlight`, `clearHighlight`, `setNodeTints`, `focusNodes`, `resetView`, labels, reduced motion

- [ ] **Step 1: 공식 r170 부가 모듈을 로컬로 vendor한다**

```powershell
$Base = 'https://raw.githubusercontent.com/mrdoob/three.js/r170'
Invoke-WebRequest "$Base/examples/jsm/loaders/GLTFLoader.js" -OutFile 'vendor/addons/loaders/GLTFLoader.js'
Invoke-WebRequest "$Base/examples/jsm/environments/RoomEnvironment.js" -OutFile 'vendor/addons/environments/RoomEnvironment.js'
Invoke-WebRequest "$Base/examples/jsm/utils/BufferGeometryUtils.js" -OutFile 'vendor/addons/utils/BufferGeometryUtils.js'
Invoke-WebRequest "$Base/LICENSE" -OutFile 'vendor/THREE-LICENSE.txt'
rg -n "from 'three'" vendor/addons/loaders/GLTFLoader.js vendor/addons/environments/RoomEnvironment.js vendor/addons/utils/BufferGeometryUtils.js
```

Expected: 세 모듈이 bare specifier `three`를 사용하고 기존 import map으로 해석된다.

- [ ] **Step 2: 안정된 노드 계층을 구현한다**

각 노드 기록은 다음 필드를 가진다.

```js
{
  id, node, nodeRoot, modelRoot, fallbackRoot, bodyMeshes, accentRoot,
  selectionRing, pressureRing, leverRing, hitProxy, labelAnchor, chip,
  categoryColor, hubMetric, modelStatus, motionState
}
```

공개 API는 정확히 다음과 같다.

```js
createNodeVisualSystem(options) => ({
  pickTargets,
  loadLibrary(url),
  setHoveredId(id),
  setHighlight(spec),
  clearHighlight(),
  setPressures(map),
  pulseArrival(id, sign),
  setLang(lang),
  setLabelTitles(map),
  setLabelValues(map),
  update(elapsed),
  getDiagnostics(),
  dispose(),
})
```

`loadLibrary()`는 rejection을 외부로 누출하지 않고 다음 결과로 resolve한다.

```js
{ status: 'ready' | 'partial' | 'fallback', loadedIds: [], fallbackIds: [], issues: [] }
```

- [ ] **Step 3: PBR 환경과 모바일 DPR 상한을 연결한다**

`scene.js`의 렌더러 초기화 직후 다음을 적용한다.

```js
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.95;
const mobile = window.matchMedia('(pointer: coarse)').matches;
renderer.setPixelRatio(Math.min(window.devicePixelRatio, mobile ? 1.5 : 2));
const pmrem = new THREE.PMREMGenerator(renderer);
const room = new RoomEnvironment();
const envTarget = pmrem.fromScene(room, 0.04);
scene.environment = envTarget.texture;
scene.add(new THREE.DirectionalLight(0xf2f5ff, 1.35));
```

방향광은 `(24, 36, 18)`에 두고, 약한 차가운 림라이트는 `(-24, 16, -18)`에 둔다. 실시간 그림자는 끈다.

- [ ] **Step 4: 폴백을 즉시 만들고 비동기 업그레이드를 시작한다**

- 구체 폴백, 라벨, 44 CSS 픽셀 상당 히트 프록시는 첫 프레임 전에 만든다.
- 첫 프레임과 로딩 오버레이는 GLB를 기다리지 않는다.
- `policy_rate`만 GLB로 교체되고 나머지 29개는 구체를 유지한다.
- `?nodes=sphere`는 GLB 요청 자체를 생략하는 킬스위치다.
- 문서 루트의 `data-node-models`를 `loading`, `partial`, `ready`, `fallback` 중 하나로 갱신한다.
- GLB 오류는 집계 경고 한 번만 기록하며 부트 fatal UI를 호출하지 않는다.
- body의 Blender 재질 이름은 다크 티타늄·새틴 합금·기술 세라믹 중 하나의 런타임 PBR 재질로 매핑한다. accent는 `data/nodes.js`의 9개 범주색으로 매핑한다.
- 노드별 명암 조절이 다른 노드에 번지지 않도록 공용 재질 템플릿을 노드별로 clone하되 파라미터 정본은 한 곳에 둔다.

- [ ] **Step 5: scene의 상호작용을 새 계층으로 연결한다**

- raycast는 `pickTargets`만 본다.
- 레버 드래그는 `nodeRoot.position.y`만 움직인다.
- 라벨은 `labelAnchor`에 붙고 정규화된 경계 높이와 허브 크기로 Y 오프셋을 계산한다.
- 기존 `ripple()`·`propagate()` 호출과 카메라·엣지·파티클 코드는 유지한다.
- 현재 모든 노드 광륜의 호흡 루프를 삭제한다.
- `dispose()`는 PMREM target, RoomEnvironment, GLB 메시, 재질, 이벤트 리스너를 정리한다.

- [ ] **Step 6: 수직 슬라이스를 실브라우저로 검증한다**

Run: `python -m http.server 5230`

Verify in a foreground browser:

- `/`에서 `policy_rate`만 정밀 모델이고 29개는 구체다.
- `/?nodes=sphere`에서 30개 모두 구체다.
- GLB 요청을 차단해도 앱·탐색·레버가 계속 작동한다.
- `document.documentElement.dataset.nodeModels`가 실제 상태와 일치한다.
- 콘솔 uncaught error가 0이다.

- [ ] **Step 7: 커밋한다**

```powershell
git add vendor js/node-visual-system.js js/scene.js js/main.js
git -c user.name="Marcus Gong" -c user.email="globin0806@gmail.com" commit -m "feat: load pbr node models with fallback"
```

---

### Task 5: 대표 6개를 완성하고 실제 지도에서 시각 승인

**Files:**
- Modify: `scripts/blender/econ-node-library.blend`
- Modify: `data/models/econ-node-library.glb`

**Interfaces:**
- Consumes: Task 3 Blender 계약과 Task 4 런타임
- Produces: 6개 ready 모델, 정확히 12개 GLB 렌더 프리미티브

- [ ] **Step 1: 다음 형상·예산으로 5개를 추가 저작한다**

| ID | 몸체와 악센트 | 삼각형 | 서명 동작 |
|---|---|---:|---|
| `policy_rate` | 저상 베이스·제어 크라운 몸체, 눈금 바늘·인레이 링 악센트 | 1,800~2,200 | 바늘 한 눈금 회전 |
| `fx` | 비대칭 이중 짐벌, 두 번째 링을 악센트로 결합 | 2,200~2,600 | 악센트 링 역회전 |
| `oil` | 압력 캡슐·축 배관 몸체, 보정 밸브 악센트 | 1,800~2,200 | 밸브 30도 회전 |
| `housing` | 포털 프레임·하부 층판 몸체, 상부 층판 악센트 | 1,500~1,900 | 상부 층판 상승 |
| `gdp` | 중앙 허브·외곽 케이지 몸체, 결합된 6개 베인 악센트 | 1,800~2,200 | 베인 7% 팽창 |
| `risk_sentiment` | 양극 프레임·짐벌 몸체, 진자 악센트 | 1,500~1,900 | 진자 왕복 |

모든 노출 모서리는 같은 베벨 폭과 세그먼트를 사용하고, 악센트는 하나의 메시로 결합한다. 스모크 렌즈는 이 게이트에서 사용하지 않는다.

- [ ] **Step 2: Blender 안에서 조형 QA를 수행한다**

- 정면·측면·상면을 회색 단색으로 렌더해 6개가 쌍별로 구별되는지 확인한다.
- 일반 지도 카메라 크기에서 큰 덩어리, 보조 구조, 악센트가 각각 읽히는지 확인한다.
- 클립아트식 집, 물방울, 동전, 사람 형태가 없는지 확인한다.
- 악센트 면적 10~20%, 베벨 하이라이트, 비유한 노멀 0을 확인한다.

- [ ] **Step 3: proof 범위를 내보내고 예산을 검증한다**

Run the Task 3 commands with `--scope proof`.

Expected:

- `readyCount=6`
- 전체 10,600~13,000 삼각형, 절대 상한 18,000
- 12 프리미티브
- GLB 600,000바이트 이하
- 카메라·조명·이미지·애니메이션·필수 확장 0

- [ ] **Step 4: 실제 지도 검수와 사용자 게이트를 통과한다**

데스크톱과 390px 전경 브라우저에서 6개 모델, 라벨, 엣지, 선택, 전파 도착, 레버 드래그, 모션 감소를 보여 준다. 시각 승인 전에는 나머지 24개를 제작하지 않는다.

- [ ] **Step 5: 승인된 proof를 커밋한다**

```powershell
git add scripts/blender/econ-node-library.blend data/models/econ-node-library.glb
git -c user.name="Marcus Gong" -c user.email="globin0806@gmail.com" commit -m "feat: add six precision macro instruments"
```

---

### Task 6: 허브 크기·상태 링·서명 동작·설명을 연결

**Files:**
- Modify: `js/main.js:45-100`
- Modify: `js/node-visual-system.js`
- Modify: `js/scene.js:330-528,626-704,723-757`
- Modify: `js/ui.js:331-345,464-477,759-783,886-894,1005-1020,1265-1274`
- Modify: `css/main.css:115-166,702-764,1238-1243`
- Modify: `data/strings.js`
- Modify: `scripts/tests/hub-metrics.test.js`

**Interfaces:**
- `main.js` passes one `hubMetrics` map to scene and UI.
- `setNodeTints(map)` remains as a compatibility alias that calls `setPressures(map)` until all callers change in one commit.
- `getDiagnostics()` exposes `modelStatus`, `loadedModelCount`, `fallbackCount`, `calls`, `triangles`.

- [ ] **Step 1: 허브 점수를 boot에 연결한다**

```js
const graph = buildGraph(NODES, EDGES);
const hubMetrics = computeHubMetrics(graph);
```

`createScene()`과 `createUI()` 양쪽에 같은 `hubMetrics`를 전달한다. 기존 degree 기반 `size = 1.35 + ...`를 제거한다.

- [ ] **Step 2: 모델 경계와 허브 크기를 분리해 적용한다**

- GLB 모델의 결합 경계구를 계산해 반지름 1로 정규화한다.
- 그 위에 `metric.radiusScale`을 적용한다.
- 폴백 구체에도 같은 허브 크기를 적용한다.
- 라벨 앵커와 히트 프록시는 최종 크기를 기준으로 갱신한다.

- [ ] **Step 3: 범주색을 보존하는 상태 채널을 구현한다**

- 몸체와 인레이는 시나리오 값으로 재색칠하지 않는다.
- 선택은 얇은 중성 선택 링으로 표시한다.
- 상승·하락 압력은 별도 링의 `#ffb36b`·`#6fb5ff`, 두께·스케일로 표시한다.
- 레버 링은 범주색을 유지한다.
- 비선택 노드는 투명화 대신 불투명 PBR 재질의 명도·emissive를 낮춘다.
- 2D 라벨의 ▲·▼와 텍스트는 그대로 유지해 색 단독 정보가 되지 않게 한다.

- [ ] **Step 4: 사건 기반 움직임을 구현한다**

- hover는 `modelRoot` 최대 2도 기울기, 120ms다.
- 선택은 악센트 서명 동작 1회, 220~320ms다.
- 펄스 도착은 전체 `nodeRoot` 바운스 대신 `accentRoot`와 도착 링을 160~220ms 반응시킨다.
- 레버 드래그 중에는 `nodeRoot` Y를 드래그가 독점한다.
- 모션 감소 시 모든 회전·이동·스케일 동작을 즉시 기준값으로 복귀시킨다.

- [ ] **Step 5: 상세 패널과 범례를 이중언어로 추가한다**

변수 헤더에 `인과 허브 78/100`과 낮음·중간·높음 구간을 표시한다. 범례에는 0, 50, 100점 크기의 세 표본과 `강한 직·간접 경로, 최대 3단계` 설명을 둔다.

`data/strings.js`에 최소 다음 키를 추가한다.

```js
'인과 허브': 'Causal hub',
'낮음': 'Low',
'중간': 'Medium',
'높음': 'High',
'강한 직·간접 경로, 최대 3단계': 'Strong direct and indirect paths, up to 3 steps',
'모델을 불러오지 못해 기본 형상으로 표시합니다': 'The default shape is shown because the model could not be loaded',
```

- [ ] **Step 6: 자동·실브라우저 검증을 수행한다**

Run: `npm test`

Foreground browser checks:

- score100과 물체 크기의 순서가 일치한다.
- 시뮬레이션이 범주색을 덮지 않는다.
- hover·선택·도착 동작은 사건 때만 발생한다.
- 모션 감소는 모델 움직임을 제거한다.
- 390px에서 범례가 헤더에 가리지 않고 가로 스크롤이 없다.
- 모든 정보 라벨은 WCAG AA를 통과하고, 작은 보조 텍스트는 7:1을 목표로 하되 4.5:1 아래로 내려가지 않는다.

- [ ] **Step 7: 커밋한다**

```powershell
git add js data/strings.js css/main.css scripts/tests
git -c user.name="Marcus Gong" -c user.email="globin0806@gmail.com" commit -m "feat: encode hubness and node states"
```

---

### Task 7: 통화·금융·물가 배치 6개를 저작

**Files:**
- Modify: `scripts/blender/econ-node-library.blend`
- Modify: `data/models/econ-node-library.glb`

| ID | 몸체와 악센트 | 삼각형 | 서명 동작 |
|---|---|---:|---|
| `market_rate` | 경사진 이중 레일 몸체, 만기 캐리지 악센트 | 1,500~1,900 | 캐리지 이동 |
| `liquidity` | 삼중 저장조 몸체, 내부 로터 악센트 | 1,900~2,300 | 로터 회전 |
| `credit_spread` | 기준 프레임·고정 조 몸체, 이동 조 악센트 | 1,400~1,800 | 간극 확대 |
| `bank_lending` | 이중 실린더 몸체, 결합 피스톤 악센트 | 1,700~2,100 | 피스톤 전진 |
| `cpi` | 가중 분절 드럼 몸체, 기준 인덱스 링 악센트 | 1,800~2,200 | 한 눈금 회전 |
| `inflation_exp` | 열 코어·지지 프레임 몸체, 선행 렌즈 악센트 | 1,600~2,000 | 초점 전진 |

- [ ] 각 모델을 두 렌더 메시로 결합하고 개별 실루엣 QA를 통과시킨다.
- [ ] `econ_ready=true`를 12개 모델에만 적용한다.
- [ ] `--scope ready`로 12개를 내보내고 모델당 3,000 삼각형·전체 3MB 하드캡을 통과시킨다.
- [ ] 실제 지도에서 fallbackCount가 18인지 확인한다.
- [ ] 커밋한다.

```powershell
git add scripts/blender/econ-node-library.blend data/models/econ-node-library.glb
git -c user.name="Marcus Gong" -c user.email="globin0806@gmail.com" commit -m "feat: add money and price instruments"
```

---

### Task 8: 임금·대외 배치 6개를 저작

**Files:**
- Modify: `scripts/blender/econ-node-library.blend`
- Modify: `data/models/econ-node-library.glb`

| ID | 몸체와 악센트 | 삼각형 | 서명 동작 |
|---|---|---:|---|
| `wages` | 보상 드럼 몸체, 래칫 톱니 악센트 | 1,500~1,900 | 한 단계 상승 |
| `exports` | 화물 허브 몸체, 외향 베인 악센트 | 1,600~2,000 | 바깥 전개 |
| `current_account` | 양측 계수판 몸체, 균형축 악센트 | 1,500~1,900 | 수평 복귀 |
| `capital_flows` | 다중 입구 몸체, 유입 게이트 악센트 | 1,800~2,200 | 게이트 전진 |
| `fed_rate` | 12분할 외곽 거버너 몸체, 궤도 추 악센트 | 2,000~2,400 | 궤도 이동 |
| `global_growth` | 중앙 지지 프레임 몸체, 세 직교 밴드·방사 스트럿 악센트 | 2,100~2,500 | 6% 팽창 |

- [ ] 각 모델을 두 렌더 메시로 결합하고 `policy_rate`·`fed_rate` 실루엣 중복을 별도 확인한다.
- [ ] `--scope ready` 결과 readyCount 18과 fallbackCount 12를 확인한다.
- [ ] 커밋한다.

```powershell
git add scripts/blender/econ-node-library.blend data/models/econ-node-library.glb
git -c user.name="Marcus Gong" -c user.email="globin0806@gmail.com" commit -m "feat: add wage and external instruments"
```

---

### Task 9: 실물·주식 배치 6개를 저작

**Files:**
- Modify: `scripts/blender/econ-node-library.blend`
- Modify: `data/models/econ-node-library.glb`

| ID | 몸체와 악센트 | 삼각형 | 서명 동작 |
|---|---|---:|---|
| `consumption` | 수요 플라이휠 몸체, 분절 베인 악센트 | 1,700~2,100 | 6% 수축·복원 |
| `investment` | 수직 마스트 몸체, 삼각 트러스 악센트 | 1,700~2,100 | 트러스 전개 |
| `employment` | 세 기둥 몸체, 연결 링 악센트 | 1,400~1,800 | 링 잠금 |
| `earnings` | 베벨 프리즘 몸체, 상승 계단 악센트 | 1,500~1,900 | 한 칸 상승 |
| `defaults` | 압력용기 몸체, 파열선 래치 악센트 | 1,600~2,000 | 래치 해제·복귀 |
| `stocks` | 호가 핀 어레이 몸체, 가격 스핀들 악센트 | 1,700~2,100 | 스핀들 상승 |

- [ ] 사람 모형·동전·차트 화살표 같은 직역을 사용하지 않는다.
- [ ] `--scope ready` 결과 readyCount 24와 fallbackCount 6을 확인한다.
- [ ] 커밋한다.

```powershell
git add scripts/blender/econ-node-library.blend data/models/econ-node-library.glb
git -c user.name="Marcus Gong" -c user.email="globin0806@gmail.com" commit -m "feat: add real economy instruments"
```

---

### Task 10: 자산·정책·외생·심리 배치 6개를 저작

**Files:**
- Modify: `scripts/blender/econ-node-library.blend`
- Modify: `data/models/econ-node-library.glb`

| ID | 몸체와 악센트 | 삼각형 | 서명 동작 |
|---|---|---:|---|
| `household_debt` | 균형빔·무게추 몸체, 조임 코일 악센트 | 1,700~2,100 | 코일 조임 |
| `commodity` | 가공 도가니 몸체, 다면 원광 악센트 | 1,600~2,000 | 코어 상승 |
| `fiscal` | 배분 매니폴드 몸체, 세 출구 밸브 악센트 | 1,800~2,200 | 밸브 순차 회전 |
| `geopolitics` | 긴장축 몸체, 분할 반구 셸 악센트 | 2,000~2,400 | 반구 비틀림 |
| `tech` | 칩 격자 몸체, 마이크로터빈 악센트 | 1,900~2,300 | 로터 가속 |
| `consumer_conf` | 수평 프레임 몸체, 중앙 신뢰 베인 악센트 | 1,500~1,900 | 베인 상승·고정 |

- [ ] `risk_sentiment`·`consumer_conf`가 같은 분홍색이어도 흑백 실루엣으로 구별되는지 확인한다.
- [ ] `--scope full`로 30개 ID·60 프리미티브·전체 삼각형·GLB 크기를 검증한다.
- [ ] 런타임 `loadedModelCount=30`, `fallbackCount=0`을 확인한다.
- [ ] 커밋한다.

```powershell
git add scripts/blender/econ-node-library.blend data/models/econ-node-library.glb
git -c user.name="Marcus Gong" -c user.email="globin0806@gmail.com" commit -m "feat: complete thirty node instruments"
```

---

### Task 11: 비활성 엣지를 네 배치로 줄여 렌더 예산을 확보

**Files:**
- Modify: `js/scene.js:240-329,380-494`
- Use: `vendor/addons/utils/BufferGeometryUtils.js`

**Interfaces:**
- Preserves: `edgeVis: Map<edgeKey, {e, curve}>`
- Produces: four passive `THREE.LineSegments` batches by sign × confidence band
- Preserves: highlighted edge tube, cone, pulse, flip-gold behavior

- [ ] **Step 1: 현재 드로콜 기준값을 기록한다**

`scene.getDiagnostics()`로 홈·선택·시뮬레이션 상태의 calls·triangles를 기록한다. 107개 개별 passive edge line이 존재하는 것을 확인한다.

- [ ] **Step 2: 곡선을 분절 기하로 변환해 네 그룹으로 합친다**

- 그룹 키는 `positive|negative` × `certain|contested`다.
- 강도 1~3은 vertex color 명도로 인코딩한다.
- 확실성 1은 dashed material, 2·3은 solid material을 쓴다.
- 각 곡선 40구간을 독립된 점 쌍으로 만들어 다른 엣지끼리 연결되지 않게 한다.
- 선택 중에는 네 passive batch의 opacity를 함께 낮추고 highlighted tube만 개별 생성한다.
- `edgeVis`는 개별 Line을 보관하지 않고 원래 곡선과 엣지만 보관한다.

- [ ] **Step 3: 시각·성능 회귀를 검증한다**

- 기본 선의 부호, 점선, 강도 차이가 유지된다.
- 선택·원인 보기·국면반전 금색·펄스 도착이 유지된다.
- 기본 장면 전체 드로콜 150 이하, 하드캡 180 이하를 확인한다.
- 데스크톱 목표 60fps, 중급 모바일 목표 45fps, 30fps 미만 지속 구간이 없음을 확인한다.

- [ ] **Step 4: 커밋한다**

```powershell
git add js/scene.js vendor/addons/utils/BufferGeometryUtils.js
git -c user.name="Marcus Gong" -c user.email="globin0806@gmail.com" commit -m "perf: batch passive causal edges"
```

---

### Task 12: 전체 회귀, 문서, v2.5.0 릴리스 준비

**Files:**
- Modify: `js/main.js:14`
- Modify: `README.md`
- Modify: `PLAN.md`
- Modify: `docs/plan.md`
- Modify: `docs/session-log.md`
- Modify: `.vercelignore` comment only if runtime asset list is stale
- Verify: all created and modified files above

**Interfaces:**
- Produces: locally complete v2.5.0 commit, clean worktree
- Does not produce: remote push or Vercel deployment without explicit authorization

- [ ] **Step 1: 모든 자동 검증을 새로 실행한다**

```powershell
npm test
$Project = "C:\MG's Workspace\projects\econ-systems-map_personal_260710"
$Blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $Blender --background --factory-startup --disable-autoexec "$Project\scripts\blender\econ-node-library.blend" --python-exit-code 1 --python "$Project\scripts\blender\validate-econ-node-library.py" -- --scope full
git diff --check
```

Expected: Node tests 0 failures, Blender errors empty, 30 IDs·60 primitives, GLB 3MB 이하, diff check clean.

- [ ] **Step 2: 전경 실브라우저 회귀를 수행한다**

다음 상태를 실제 전경 브라우저에서 순회한다.

- 첫 로드, 30개 모델, 한국어·영어
- 변수 선택, 결과 보기, 원인 보기, 1·2·3차 전파
- 시뮬레이터 레버 6종과 프리셋
- 사례, 루프, 지금, AI 지도 액션
- 키보드, Escape, 검색, 딥링크, 브라우저 뒤로가기
- 모션 감소, `?nodes=sphere`, 강제 GLB 404, 일부 ID 누락 폴백
- 데스크톱, 390px 모바일, 200% 확대
- 콘솔 오류 0, 라벨 대비 AA, 작은 보조 텍스트 7:1 목표·4.5:1 최저, 터치 타깃 44px, 가로 스크롤 0

인앱 미리보기나 백그라운드 탭의 정지 화면만으로 렌더 통과를 선언하지 않는다.

- [ ] **Step 3: 웹서비스 품질 게이트를 판정한다**

이번 기능 범위의 P0을 모두 통과시키고 L3 Polished를 목표로 한다. 가장 높은 미충족 단계와 사유를 PLAN에 기록한다. 모델 로딩 상태는 기존 구체가 즉시 보이므로 전체 화면을 막는 스피너를 추가하지 않는다.

- [ ] **Step 4: 버전과 문서를 갱신한다**

- `APP_VERSION`을 `v2.5.0`으로 바꾼다.
- README에 `data/models/`, `scripts/blender/`, `npm test`, Blender 검증 명령을 추가한다.
- PLAN에서 M6을 완료하고 성능 실측값과 proof 승인일을 기록한다.
- `docs/plan.md`의 오래된 Current Status와 M6을 갱신한다.
- `docs/session-log.md`에 Blender 5.1.2, 30개 형상, 허브 크기, 폴백·성능 결정을 기록한다.

- [ ] **Step 5: 최종 검증 후 커밋한다**

```powershell
npm test
git diff --check
git status --short
git add js/main.js README.md PLAN.md docs/plan.md .vercelignore
git -c user.name="Marcus Gong" -c user.email="globin0806@gmail.com" commit -m "feat: release precision macro instruments v2.5.0"
git status --short --branch
```

Expected: clean worktree, `main` is ahead only by the new local commits. `docs/session-log.md`는 기존 ignore 정책대로 로컬 연속성 기록으로 남는다.

## 실행 중 필수 검토 게이트

| 게이트 | 시점 | 통과 조건 |
|---|---|---|
| G1 계약 | Task 2 | 누락·중복·비정상 모델이 전체 앱이 아닌 개별 폴백으로 격리됨 |
| G2 수직 슬라이스 | Task 4 | `policy_rate`만 GLB여도 첫 로드·탐색·레버가 정상 |
| G3 대표 6개 시각 승인 | Task 5 | 전문성·실루엣·재질·모바일·성능을 사용자 승인 |
| G4 30개 완결 | Task 10 | 30 ID, 60 primitives, fallback 0, GLB 하드캡 통과 |
| G5 릴리스 | Task 12 | 자동·전경 브라우저·접근성·성능 회귀 통과 |

## 이 계획에서 의도적으로 제외한 것

- Three.js 버전 업그레이드
- Draco·Meshopt·KTX2 압축
- 실시간 그림자와 블룸 후처리
- 모델 안의 텍스트·숫자
- 새 데이터베이스·서버·분석 추적
- 사용자 승인 전 나머지 24개 대량 제작
- 명시적 요청 전 GitHub push·Vercel 배포
