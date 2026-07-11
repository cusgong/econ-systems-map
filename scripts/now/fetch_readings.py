# Daily NOW-board numeric feed.
# Fetches official series (BOK ECOS, FRED) per scripts/now/series-map.json, recomputes
# value/trend/date for the machine-fed readings, and rewrites scripts/now/readings-live.json.
# Never touches notes/themes (those live in editorial.json).
# Failure policy: a failing or insane series keeps its previous entry; more than
# MAX_FAILURES failures (or any sanity-bound violation) exits non-zero so CI never publishes.
# Env: ECOS_API_KEY, FRED_API_KEY. Usage: python scripts/now/fetch_readings.py [--dry-run]
import io
import json
import os
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone

NOW_DIR = os.path.dirname(os.path.abspath(__file__))
KST = timezone(timedelta(hours=9))
TODAY = datetime.now(KST).date()
MAX_FAILURES = 3
LOOKBACK_MONTHS = 20  # covers YoY (12m) + 6m trend window with slack

DRY = "--dry-run" in sys.argv


def load_json(name):
    with io.open(os.path.join(NOW_DIR, name), "r", encoding="utf-8-sig") as f:
        return json.load(f)


def http_json(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "macroscope-now-feed/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001 - retry then surface
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"fetch failed after {tries} tries: {last}")


# ---------- providers: return [(iso_date_str, float_value)] ascending ----------

def ecos_time(cycle, d):
    if cycle == "D":
        return d.strftime("%Y%m%d")
    if cycle == "M":
        return d.strftime("%Y%m")
    if cycle == "Q":
        return f"{d.year}Q{(d.month - 1) // 3 + 1}"
    if cycle == "A":
        return d.strftime("%Y")
    raise ValueError(f"unsupported cycle {cycle}")


def ecos_parse_time(cycle, s):
    if cycle == "D":
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    if cycle == "M":
        return f"{s[0:4]}-{s[4:6]}"
    if cycle == "Q":
        return f"{s[0:4]}-Q{s[-1]}"
    return s


def fetch_ecos(entry, key):
    cycle = entry["cycle"]
    start = ecos_time(cycle, TODAY - timedelta(days=LOOKBACK_MONTHS * 31))
    end = ecos_time(cycle, TODAY)
    items = "/".join(entry.get("itemCodes", []))
    url = (f"https://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/1000/"
           f"{entry['statCode']}/{cycle}/{start}/{end}" + (f"/{items}" if items else ""))
    data = http_json(url)
    block = data.get("StatisticSearch")
    if not block or not block.get("row"):
        raise RuntimeError(f"ECOS empty response: {json.dumps(data, ensure_ascii=False)[:200]}")
    out = []
    for row in block["row"]:
        try:
            out.append((ecos_parse_time(cycle, row["TIME"]), float(row["DATA_VALUE"])))
        except (KeyError, TypeError, ValueError):
            continue
    if not out:
        raise RuntimeError("ECOS rows had no numeric DATA_VALUE")
    return out


def fetch_fred(entry, key):
    start = (TODAY - timedelta(days=LOOKBACK_MONTHS * 31)).isoformat()
    url = (f"https://api.stlouisfed.org/fred/series/observations?series_id={entry['seriesId']}"
           f"&api_key={key}&file_type=json&observation_start={start}&sort_order=asc")
    data = http_json(url)
    obs = data.get("observations")
    if not obs:
        raise RuntimeError(f"FRED empty response: {json.dumps(data)[:200]}")
    out = []
    for o in obs:
        if o.get("value") in (None, "", "."):
            continue
        try:
            out.append((o["date"], float(o["value"])))
        except ValueError:
            continue
    if not out:
        raise RuntimeError("FRED observations all missing")
    return out


# ---------- transforms over the raw series ----------

def months_between(a, b):
    """approx months between two iso-ish date strings (YYYY[-MM[-DD]] or YYYY-Qn)."""
    def parse(s):
        if "-Q" in s:
            y, q = s.split("-Q")
            return int(y) * 12 + (int(q) - 1) * 3
        parts = s.split("-")
        y = int(parts[0]); m = int(parts[1]) if len(parts) > 1 else 6
        return y * 12 + (m - 1)
    return parse(b) - parse(a)


def transform(series, kind):
    """series -> transformed [(date, value)]"""
    if kind == "latest":
        return series
    out = []
    if kind in ("yoy_pct", "yoy_delta"):
        for i in range(len(series)):
            d, v = series[i]
            # find the observation ~12 months earlier
            base = None
            for j in range(i - 1, -1, -1):
                if months_between(series[j][0], d) >= 12:
                    base = series[j][1]
                    break
            if base is None:
                continue
            if kind == "yoy_pct":
                if base == 0:
                    continue
                out.append((d, (v / base - 1.0) * 100.0))
            else:
                out.append((d, v - base))
    elif kind == "mom_delta":
        out = [(series[i][0], series[i][1] - series[i - 1][1]) for i in range(1, len(series))]
    elif kind in ("mom_pct", "qoq_pct"):
        out = [(series[i][0], (series[i][1] / series[i - 1][1] - 1.0) * 100.0)
               for i in range(1, len(series)) if series[i - 1][1] != 0]
    else:
        raise RuntimeError(f"unknown transform {kind}")
    if not out:
        raise RuntimeError(f"transform {kind} produced no rows")
    return out


def compute_trend(tseries, eps):
    """direction of the (transformed) indicator over ~6 months."""
    last_d, last_v = tseries[-1]
    base = None
    for d, v in reversed(tseries[:-1]):
        if months_between(d, last_d) >= 6:
            base = v
            break
    if base is None:
        base = tseries[0][1]
    diff = last_v - base
    if diff > eps:
        return 1
    if diff < -eps:
        return -1
    return 0


# ---------- per-node display formatting ----------

MONTH_EN = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def month_of(d):
    parts = d.split("-")
    return int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None


def fmt_value(node, v, d):
    m = month_of(d)
    mm = f"{m}월" if m else ""
    me = MONTH_EN[m] if m else ""
    F = {
        "policy_rate": (f"연 {v:.2f}%", f"{v:.2f}%"),
        "fed_rate": (f"상단 {v:.2f}%", f"{v:.2f}% upper"),
        "market_rate": (f"국고 10년 {v:.2f}%", f"10y KTB {v:.2f}%"),
        "cpi": (f"{v:.1f}% ({mm}, 전년比)", f"{v:.1f}% YoY ({me})"),
        "inflation_exp": (f"{v:.1f}% (향후 1년)", f"{v:.1f}% (1y ahead)"),
        "fx": (f"약 {v:,.0f}원", f"~{v:,.0f} KRW/USD"),
        "oil": (f"브렌트 약 {v:.0f}달러", f"Brent ~${v:.0f}"),
        "stocks": (f"KOSPI 약 {v:,.0f}", f"KOSPI ~{v:,.0f}"),
        "housing": (f"서울 아파트 {mm} {v:+.2f}%", f"Seoul apts {v:+.2f}% MoM ({me})"),
        "household_debt": (f"{mm} {v:+.1f}조 원", f"{v:+.1f}tn KRW ({me})"),
        "exports": (f"{mm} {v:+.1f}%", f"{v:+.1f}% YoY ({me})"),
        "current_account": (f"{mm} {v:+,.0f}억 달러", f"{'+' if v >= 0 else '-'}${abs(v) / 10:,.1f}B ({me})"),
        "employment": (f"취업자 {v:+.1f}만 명 ({mm})", f"{v * 10:+,.0f}k jobs ({me})"),
        "wages": (f"{v:+.1f}% ({mm}, 명목)", f"{v:+.1f}% nominal ({me})"),
        "gdp": (f"분기 {v:+.1f}% (전기比)", f"{v:+.1f}% QoQ"),
    }
    if node not in F:
        raise RuntimeError(f"no formatter for {node}")
    ko, en = F[node]
    return {"ko": ko, "en": en}


def main():
    smap = load_json("series-map.json")
    prev = load_json("readings-live.json")
    ecos_key = os.environ.get("ECOS_API_KEY", "")
    fred_key = os.environ.get("FRED_API_KEY", "")

    failures = []
    fatal = []
    readings = dict(prev.get("readings", {}))

    for node, entry in smap.items():
        try:
            if entry["provider"] == "ecos":
                if not ecos_key:
                    raise RuntimeError("ECOS_API_KEY not set")
                raw = fetch_ecos(entry, ecos_key)
            elif entry["provider"] == "fred":
                if not fred_key:
                    raise RuntimeError("FRED_API_KEY not set")
                raw = fetch_fred(entry, fred_key)
            else:
                raise RuntimeError(f"unknown provider {entry['provider']}")

            scale = entry.get("scale", 1)
            if scale != 1:
                raw = [(d0, v0 * scale) for d0, v0 in raw]
            tser = transform(raw, entry.get("transform", "latest"))
            d, v = tser[-1]
            lo, hi = entry["sane"]
            if not (lo <= v <= hi):
                fatal.append(f"{node}: value {v} outside sanity bounds [{lo}, {hi}] - check series mapping")
                continue
            readings[node] = {
                "trend": compute_trend(tser, entry.get("trendEps", 0.0)),
                "value": fmt_value(node, v, d),
                "source": entry["sourceLabel"],
                "date": d,
            }
            print(f"  ok {node}: {readings[node]['value']['ko']} ({d}) trend {readings[node]['trend']:+d}")
        except Exception as e:  # noqa: BLE001 - per-series isolation
            failures.append(f"{node}: {e}")
            print(f"  FAIL {node}: {e}")

    if fatal:
        print(f"FATAL sanity violations ({len(fatal)}):")
        for f in fatal:
            print("  -", f)
        sys.exit(1)
    if len(failures) > MAX_FAILURES:
        print(f"FAILED: {len(failures)} series failed (max {MAX_FAILURES}); keeping previous file")
        sys.exit(1)

    out = {"fetchedAt": TODAY.isoformat(), "readings": readings}
    if DRY:
        print("dry-run: not writing")
        return
    with io.open(os.path.join(NOW_DIR, "readings-live.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"OK: readings-live.json updated ({len(smap) - len(failures)}/{len(smap)} series fresh, "
          f"{len(failures)} kept previous)")


if __name__ == "__main__":
    main()
