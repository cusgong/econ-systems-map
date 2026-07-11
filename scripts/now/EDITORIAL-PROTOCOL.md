# NOW Board Editorial Refresh Protocol

You are refreshing the editorial layer of MacroScope's "지금(NOW)" board. This protocol is the
contract for the weekly unattended job (and for any human/local run). Follow it exactly.

## What you own and what you must not touch

- You edit exactly ONE file: `scripts/now/editorial.json`.
- `scripts/now/readings-live.json` is machine-written ground truth for indicator numbers. Read it, never edit it.
- `data/situation.js` is GENERATED. Never edit it directly. Rebuild it via
  `python scripts/now/build_situation.py` and make that pass.
- Do not touch any other file in the repo.

## Inputs to read first

1. `scripts/now/readings-live.json`: fresh numeric values per node (value/trend/date/source).
2. `scripts/now/editorial.json`: the current editorial layer you are updating.
3. `data/nodes.js` (node ids), `data/cases.js` (case ids), `data/loops.js` (loop ids):
   the only ids you may reference.

## Tasks

1. **Reading notes** (`notes.<node>`, ko+en): for every machine-fed reading, check whether the
   one-to-two-sentence note still matches reality. Update notes that reference stale events or
   numbers. Where a note cites a number that overlaps `readings-live.json`, the note must agree
   with that file. Keep notes <= ~130 chars (ko), 합니다체, plain language for non-economists.
2. **Editorial readings** (`readings.geopolitics`, `readings.global_growth`): refresh value
   (qualitative label / latest official forecast), trend (-1/0/1), note, source, date.
3. **Themes** (3-6 items): re-evaluate each theme. Keep it if still a top current storyline
   (update body/numbers/dates), replace it if a bigger storyline has emerged. Each theme needs:
   - `id` (kebab-case, stable if the storyline continues),
   - `title`/`body` ko+en (body ~4-7 sentences, ends by pointing at a causal chain on the map),
   - `nodes` (existing node ids), `edges` (pairs that EXIST in data/edges.js),
   - `relatedCase`/`relatedLoop` (existing id or null),
   - `sources`: >= 2, each with publisher and date.
4. **asOf**: set `editorial.json`'s `asOf` to today (KST, YYYY-MM-DD).
5. **Build**: run `python scripts/now/build_situation.py`. Fix your JSON until it passes.
   If it still fails, stop and exit non-zero. Never hand-edit the generated file to force a pass.

## Verification discipline (non-negotiable)

- Every factual claim (numbers, dates, events, policy decisions) must be verified THIS run via
  web research against at least 2 independent sources. No memory-only claims.
- Prefer primary sources: 한국은행, 통계청, 산업통상자원부, 금융위원회, Fed, IMF, IEA.
- If you cannot verify a claim, omit it. A thinner but true board beats a rich but wrong one.
- No forecasts of your own and no investment advice. Describing an institution's published
  forecast (with attribution) is fine. Phrases like "매수/매도/투자 추천" are forbidden.
- Uncertainty must be visible: if a situation is disputed or fast-moving, say so in the body.
- Style: ko is 합니다체; en is natural English, not literal translation. Foreign names follow
  Korean pronunciation conventions in ko text.

## Output contract

When done: `editorial.json` updated + `build_situation.py` exits 0. The workflow handles
commit/deploy; you do not run git commands unless the job instructions explicitly say so.
