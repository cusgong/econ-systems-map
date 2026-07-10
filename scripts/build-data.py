# Assemble reviewed content JSON (scratchpad) into runtime data modules (data/*.js).
# Validates node-id canonicality, edge dedupe, loop closure + net sign, case edge existence.
# Usage: python scripts/build-data.py <scratch_content_dir>
import json
import sys
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = sys.argv[1] if len(sys.argv) > 1 else None
if not SRC or not os.path.isdir(SRC):
    print("ERROR: pass the scratch content dir")
    sys.exit(2)

IDS = set("""policy_rate market_rate liquidity credit_spread bank_lending cpi inflation_exp wages
fx exports current_account capital_flows fed_rate global_growth consumption investment employment
earnings defaults gdp stocks housing household_debt oil commodity fiscal geopolitics tech
risk_sentiment consumer_conf""".split())

SOURCES = {"BOK", "Mishkin", "Mankiw", "IMF", "BIS", "Dalio", "Shiller", "Minsky", "Empirical"}

problems = []
warnings = []


def load(name):
    p = os.path.join(SRC, name + ".json")
    with io.open(p, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def check_loc(obj, where):
    if not isinstance(obj, dict) or not obj.get("ko") or not obj.get("en"):
        problems.append(f"{where}: missing ko/en")


# ---- edges ----
edges = []
seen = set()
for key in ["edges-A", "edges-B", "edges-C", "edges-D"]:
    data = load(key)
    for e in data["edges"]:
        pair = (e["from"], e["to"])
        w = f"{key} {e['from']}->{e['to']}"
        if e["from"] not in IDS or e["to"] not in IDS:
            problems.append(f"{w}: unknown node id")
            continue
        if pair in seen:
            warnings.append(f"{w}: duplicate pair, skipped")
            continue
        seen.add(pair)
        if e["sign"] not in (1, -1): problems.append(f"{w}: bad sign")
        if e["strength"] not in (1, 2, 3): problems.append(f"{w}: bad strength")
        if e["lag"] not in (0, 1, 2, 3): problems.append(f"{w}: bad lag")
        if e["confidence"] not in (1, 2, 3): problems.append(f"{w}: bad confidence")
        if e["source"] not in SOURCES: warnings.append(f"{w}: nonstandard source {e['source']}")
        check_loc(e["mech"], w + " mech")
        klen = len(e["mech"]["ko"])
        if klen > 110: warnings.append(f"{w}: mech.ko long ({klen})")
        if "note" in e and e["note"]:
            check_loc(e["note"], w + " note")
        edges.append(e)

pairset = {f"{e['from']}>{e['to']}" for e in edges}

# ---- regime flips (optional flips.json: attach flip{ko,en} onto matching edges) ----
if os.path.exists(os.path.join(SRC, "flips.json")):
    flips = load("flips")["flips"]
    by_pair = {(e["from"], e["to"]): e for e in edges}
    for fl in flips:
        pair = (fl["from"], fl["to"])
        w = f"flip {fl['from']}->{fl['to']}"
        if pair not in by_pair:
            problems.append(f"{w}: edge does not exist")
            continue
        check_loc(fl["flip"], w)
        by_pair[pair]["flip"] = fl["flip"]
    print(f"flips attached: {sum(1 for e in edges if 'flip' in e)}")

# ---- descs ----
descs = load("descs")["descs"]
dids = {d["id"] for d in descs}
for d in descs:
    if d["id"] not in IDS: problems.append(f"desc unknown id {d['id']}")
    check_loc(d["desc"], f"desc {d['id']}")
missing = IDS - dids
if missing: problems.append(f"descs missing: {sorted(missing)}")

# ---- loops (base + optional loops-extra.json) ----
loops = load("loops")["loops"]
if os.path.exists(os.path.join(SRC, "loops-extra.json")):
    extra = load("loops-extra")["loops"]
    known = {lp["id"] for lp in loops}
    for lp in extra:
        if lp["id"] in known:
            warnings.append(f"loop {lp['id']}: duplicate id in loops-extra, skipped")
            continue
        loops.append(lp)
for lp in loops:
    ids = lp["nodes"]
    sign = 1
    for i, a in enumerate(ids):
        b = ids[(i + 1) % len(ids)]
        k = f"{a}>{b}"
        if k not in pairset:
            problems.append(f"loop {lp['id']}: missing edge {k}")
        else:
            e = next(x for x in edges if x["from"] == a and x["to"] == b)
            sign *= e["sign"]
    expect = 1 if lp["type"] == "reinforcing" else -1
    if sign != expect:
        problems.append(f"loop {lp['id']}: net sign {sign} != type {lp['type']}")
    check_loc(lp["name"], f"loop {lp['id']} name")
    check_loc(lp["story"], f"loop {lp['id']} story")
    check_loc(lp["example"], f"loop {lp['id']} example")

# ---- cases ----
cases = []
case_files = ["oil70s", "krw97", "gfc08", "covid20"]
if os.path.exists(os.path.join(SRC, "case-dotcom.json")):
    case_files.append("dotcom")
for cid in case_files:
    data = load("case-" + cid)["caseData"]
    keys = [p["key"] for p in data["phases"]]
    if keys != ["cause", "spread", "policy", "psychology", "outcome"]:
        problems.append(f"case {cid}: phase keys {keys}")
    for p in data["phases"]:
        w = f"case {cid}/{p['key']}"
        check_loc(p["title"], w + " title")
        check_loc(p["narration"], w + " narration")
        for nid in p["focusNodes"]:
            if nid not in IDS: problems.append(f"{w}: unknown focus node {nid}")
        bad = [f"{a}>{b}" for a, b in p["activeEdges"] if f"{a}>{b}" not in pairset]
        if bad: warnings.append(f"{w}: activeEdges not in edge set: {bad}")
        for nid, v in p.get("shocks", {}).items():
            if nid not in IDS: problems.append(f"{w}: unknown shock node {nid}")
            if not isinstance(v, (int, float)) or not -1 <= v <= 1:
                problems.append(f"{w}: shock out of range {nid}={v}")
    check_loc(data["comparison"]["common"], f"case {cid} comparison.common")
    check_loc(data["comparison"]["differences"], f"case {cid} comparison.differences")
    if not data.get("sources"): warnings.append(f"case {cid}: no sources")
    cases.append(data)

# ---- coverage ----
outdeg = {i: 0 for i in IDS}
indeg = {i: 0 for i in IDS}
for e in edges:
    outdeg[e["from"]] += 1
    indeg[e["to"]] += 1
isolated = [i for i in IDS if outdeg[i] + indeg[i] == 0]
if isolated: problems.append(f"isolated nodes: {isolated}")
sinks = [i for i in IDS if outdeg[i] == 0]
sources_only = [i for i in IDS if indeg[i] == 0]
print(f"edges={len(edges)} loops={len(loops)} cases={len(cases)} descs={len(descs)}")
print(f"pure sinks (no out): {sinks}")
print(f"pure sources (no in): {sources_only}")

for wmsg in warnings: print("WARN:", wmsg)
for pmsg in problems: print("PROBLEM:", pmsg)
if problems:
    print("FAILED validation; data files NOT written")
    sys.exit(1)


def write_module(fname, const, payload):
    path = os.path.join(ROOT, "data", fname)
    body = json.dumps(payload, ensure_ascii=False, indent=1)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"// Generated by scripts/build-data.py. Edit source JSON + rerun; do not hand-edit.\n")
        f.write(f"export const {const} = {body};\n")
    print("wrote", path)


write_module("edges.js", "EDGES", edges)
write_module("cases.js", "CASES", cases)
write_module("loops.js", "LOOPS", loops)
write_module("descs.js", "DESCS", descs)
print("OK")
