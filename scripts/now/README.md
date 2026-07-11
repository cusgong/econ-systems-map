# NOW board auto-update pipeline

The "지금(NOW)" board updates unattended in two layers. `data/situation.js` is GENERATED -
never hand-edit it.

| Layer | Source of truth | Writer | Cadence |
|---|---|---|---|
| Numbers (value/trend/date of 15 readings) | `readings-live.json` | `fetch_readings.py` via `.github/workflows/now-readings.yml` | daily 19:05 KST |
| Editorial (notes, geopolitics/global_growth readings, themes) | `editorial.json` | Claude agent under `EDITORIAL-PROTOCOL.md` via `.github/workflows/now-editorial.yml` | Mon 07:00 KST |

Both workflows rebuild `data/situation.js` with `build_situation.py` (validates node/case/loop
ids, theme edges against `data/edges.js`, ko/en completeness, >=2 sources per theme, dates,
advice-phrase lint), commit as `MacroScope Bot <globin0806@gmail.com>` (Vercel validates the
commit author email even on CLI deploys - a noreply address gets deployments BLOCKED), and
deploy with the Vercel CLI. Validation failure = no publish; the live site keeps the last good
version and GitHub emails the failure.

## Files

- `series-map.json`: node -> official series (ECOS/FRED), transform, unit scale, sanity bounds,
  trend epsilon, display source label. All 15 mappings live-verified 2026-07-11 against the
  ECOS demo key / FRED public CSV (see `_verified` fields).
- `fetch_readings.py`: fetch + transform (latest / yoy_pct / yoy_delta / mom_delta / mom_pct /
  qoq_pct) + 6-month trend + per-node formatting. A failing or out-of-bounds series keeps its
  previous entry; >3 failures or any sanity violation exits non-zero.
- `build_situation.py`: merge the two JSONs -> `data/situation.js` (adds `readingsAsOf` +
  `themesAsOf`; the app warns when either goes stale).
- `EDITORIAL-PROTOCOL.md`: the weekly agent's contract (verify-then-write, 2+ sources, no
  forecasts/advice, edits only `editorial.json`).

## Local run

```
ECOS_API_KEY=... FRED_API_KEY=... python scripts/now/fetch_readings.py --dry-run
python scripts/now/build_situation.py
```

## Required GitHub Actions secrets (repo: cusgong/econ-systems-map)

`ECOS_API_KEY`, `FRED_API_KEY` (free official keys), `VERCEL_TOKEN`, `VERCEL_ORG_ID`,
`VERCEL_PROJECT_ID` (from `.vercel/project.json`), `CLAUDE_CODE_OAUTH_TOKEN`
(`claude setup-token`, 1-year subscription token; rotate by re-running and replacing).

## Ops notes (from the 2026-07-11 research pass)

- ECOS ingestion lag watchlist: exports table loads mid-month (~1 month behind the press
  release); wages table was 7 months behind (ends 202512 as of 2026-07-11); policy-rate daily
  series forward-fills with 1-2 business-day lag. Honest per-reading dates cover this.
- fed_rate uses FRED DFEDTARU (target-range upper, daily); ECOS/BIS only has the monthly
  midpoint. oil uses FRED DCOILBRENTEU (daily Brent); ECOS only has monthly averages.
- housing switched semantics to KB 서울 아파트 monthly MoM (ECOS 901Y062/P63ACA): the
  부동산원 monthly table inside ECOS ran ~5 months stale, and the weekly R-ONE API would need
  a separate key. household_debt is 예금취급기관 (ECOS 151Y002), narrower than the 금융위
  전금융권 press number the board used to quote.
- Scheduled-workflow auto-disable (public repo, 60 days without repo activity): the daily
  job's own commits reset the clock; the real failure mode is "workflow silently broken ->
  no commits -> disabled at day 60". GitHub emails both failures and the auto-disable.
- Concurrency group `now-board-writers` is shared by both workflows so they never write
  `data/situation.js` simultaneously.
- ECOS demo key: the literal string `sample` works on any statistic, capped at 10 rows per
  call - handy for probing series without a real key.
