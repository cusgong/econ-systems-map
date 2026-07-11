# Merge the two NOW-board sources of truth into the generated data/situation.js.
#   scripts/now/readings-live.json  (machine-fed values: daily cron writes this)
#   scripts/now/editorial.json      (notes/themes/editorial readings: weekly job writes this)
# Validates before writing; exits non-zero on any problem so CI never publishes a broken board.
# Usage: python scripts/now/build_situation.py
import io
import json
import os
import re
import sys
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NOW_DIR = os.path.join(ROOT, "scripts", "now")

NODE_IDS = set("""policy_rate market_rate liquidity credit_spread bank_lending cpi inflation_exp wages
fx exports current_account capital_flows fed_rate global_growth consumption investment employment
earnings defaults gdp stocks housing household_debt oil commodity fiscal geopolitics tech
risk_sentiment consumer_conf""".split())

problems = []


def err(msg):
    problems.append(msg)


def load(name):
    with io.open(os.path.join(NOW_DIR, name), "r", encoding="utf-8-sig") as f:
        return json.load(f)


def read_ids(rel_path, pattern):
    """Extract ids from a generated data/*.js file (id: 'xxx' occurrences)."""
    p = os.path.join(ROOT, rel_path)
    with io.open(p, "r", encoding="utf-8") as f:
        return set(re.findall(pattern, f.read()))


def check_loc(obj, where):
    if not isinstance(obj, dict) or not obj.get("ko") or not obj.get("en"):
        err(f"{where}: missing ko/en")


def check_date(s, where, allow_month=True):
    if not isinstance(s, str):
        err(f"{where}: date not a string")
        return
    for fmt in ("%Y-%m-%d", "%Y-%m") if allow_month else ("%Y-%m-%d",):
        try:
            d = datetime.strptime(s, fmt).date()
            if d > date.today():
                err(f"{where}: date {s} is in the future")
            return
        except ValueError:
            continue
    err(f"{where}: bad date format {s!r} (want YYYY-MM-DD or YYYY-MM)")


live = load("readings-live.json")
edi = load("editorial.json")

# ---- validate top-level ----
check_date(live.get("fetchedAt", ""), "readings-live.fetchedAt", allow_month=False)
check_date(edi.get("asOf", ""), "editorial.asOf", allow_month=False)

order = edi.get("readingOrder") or []
if not order:
    err("editorial.readingOrder missing/empty")

# ---- assemble readings ----
readings = []
for node in order:
    if node not in NODE_IDS:
        err(f"readingOrder: unknown node id {node}")
        continue
    w = f"reading {node}"
    if node in edi.get("readings", {}):
        r = dict(edi["readings"][node])
        r["node"] = node
    elif node in live.get("readings", {}):
        r = dict(live["readings"][node])
        r["node"] = node
        note = edi.get("notes", {}).get(node)
        if note is None:
            err(f"{w}: machine reading has no editorial note")
            note = {"ko": "", "en": ""}
        r["note"] = note
    else:
        err(f"{w}: present in readingOrder but in neither source")
        continue
    if r.get("trend") not in (-1, 0, 1):
        err(f"{w}: bad trend {r.get('trend')!r}")
    check_loc(r.get("value"), w + " value")
    check_loc(r.get("note"), w + " note")
    if not r.get("source"):
        err(f"{w}: missing source")
    check_date(r.get("date", ""), w + " date")
    readings.append({k: r[k] for k in ("node", "trend", "value", "note", "source", "date") if k in r})

# leftovers that never render are a drift signal
for node in set(live.get("readings", {})) - set(order):
    err(f"readings-live has {node} but readingOrder does not")
for node in set(edi.get("readings", {})) - set(order):
    err(f"editorial.readings has {node} but readingOrder does not")

# ---- validate themes ----
case_ids = read_ids("data/cases.js", r"\"id\":\s*\"([\w-]+)\"")
loop_ids = read_ids("data/loops.js", r"\"id\":\s*\"([\w-]+)\"")
edge_txt_p = os.path.join(ROOT, "data", "edges.js")
with io.open(edge_txt_p, "r", encoding="utf-8") as f:
    edges_txt = f.read()
edge_pairs = set(re.findall(r"\"from\":\s*\"(\w+)\",\s*\"to\":\s*\"(\w+)\"", edges_txt))

themes = edi.get("themes") or []
if not (3 <= len(themes) <= 8):
    err(f"themes: expected 3-8, got {len(themes)}")
theme_ids = set()
for t in themes:
    w = f"theme {t.get('id', '?')}"
    if not re.fullmatch(r"[a-z0-9-]+", t.get("id", "")):
        err(f"{w}: bad id")
    if t.get("id") in theme_ids:
        err(f"{w}: duplicate id")
    theme_ids.add(t.get("id"))
    check_loc(t.get("title"), w + " title")
    check_loc(t.get("body"), w + " body")
    for n in t.get("nodes", []) or []:
        if n not in NODE_IDS:
            err(f"{w}: unknown node {n}")
    if not t.get("nodes"):
        err(f"{w}: no nodes")
    for e in t.get("edges", []) or []:
        if not (isinstance(e, list) and len(e) == 2):
            err(f"{w}: malformed edge {e!r}")
            continue
        a, b = e
        if a not in NODE_IDS or b not in NODE_IDS:
            err(f"{w}: edge with unknown node {a}->{b}")
        elif (a, b) not in edge_pairs:
            err(f"{w}: edge {a}->{b} not present in data/edges.js")
    if t.get("relatedCase") is not None and t["relatedCase"] not in case_ids:
        err(f"{w}: unknown relatedCase {t['relatedCase']!r}")
    if t.get("relatedLoop") is not None and t["relatedLoop"] not in loop_ids:
        err(f"{w}: unknown relatedLoop {t['relatedLoop']!r}")
    srcs = t.get("sources") or []
    if len(srcs) < 2:
        err(f"{w}: needs >=2 sources, got {len(srcs)}")

# content principle: no investment advice phrasing (light lint)
ADVICE = ["매수 추천", "매도 추천", "투자 추천", "사야 합니다", "팔아야 합니다"]
for t in themes:
    body_ko = (t.get("body") or {}).get("ko", "")
    for kw in ADVICE:
        if kw in body_ko:
            err(f"theme {t.get('id')}: advice-like phrase {kw!r}")

if problems:
    print("BUILD FAILED (%d problems):" % len(problems))
    for p in problems:
        print("  -", p)
    sys.exit(1)

# ---- emit ----
situation = {
    "asOf": edi["asOf"],  # legacy alias: editorial snapshot date
    "readingsAsOf": live["fetchedAt"],
    "themesAsOf": edi["asOf"],
    "readings": readings,
    "themes": themes,
}
header = (
    "// GENERATED FILE - do not edit by hand.\n"
    "// Sources of truth: scripts/now/readings-live.json (machine-fed values, daily cron)\n"
    "//                 + scripts/now/editorial.json (notes/themes, weekly editorial job).\n"
    "// Rebuild: python scripts/now/build_situation.py\n"
)
body = json.dumps(situation, ensure_ascii=False, indent=2)
out = os.path.join(ROOT, "data", "situation.js")
with io.open(out, "w", encoding="utf-8", newline="\n") as f:
    f.write(header + "export const SITUATION = " + body + ";\n")
print(f"OK: wrote data/situation.js ({len(readings)} readings, {len(themes)} themes; "
      f"readingsAsOf {live['fetchedAt']}, themesAsOf {edi['asOf']})")
