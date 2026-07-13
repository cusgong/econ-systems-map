"""Fast per-model geometry probe for the thickening pass (scratch tool).

Runs one builder through finalize_model in a throwaway scene and reports the
gate-relevant metrics WITHOUT the full 8-stage authoring chain:
  - min/max AABB extent ratio (the flatness target, >= 0.5)
  - evaluated (post-bevel) triangle count vs its MODEL_TRIANGLE_BANDS band
  - accent surface-area ratio (must stay 0.10..0.20)
  - accent child translation (the value that must land in ACCENT_CONTRACTS)
  - accent Blender-Y extent vs the thin-axis contract (where one applies)
  - per-axis extents so a plan can target the thin axis directly

It reuses the real validator's `_evaluated_mesh_metrics`, so the numbers match
the production gate. Usage:

  blender --background --factory-startup --disable-autoexec --python-exit-code 1 \
    --python scripts/blender/_measure_model.py -- --ids policy_rate,household_debt
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import hard_surface  # noqa: E402


def _load(module_name: str, filename: str):
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SPECS = _load("econ_node_specs", "node-specs.py")
VALID = _load("econ_validate", "validate-econ-node-library.py")

# id -> (module filename, builder function name). policy_rate lives in the
# scaffold and is probed separately (see --scaffold).
BUILDER_SOURCES = {
    "money_price_models": [
        "market_rate", "liquidity", "credit_spread", "bank_lending", "cpi", "inflation_exp",
    ],
    "wage_external_models": [
        "wages", "exports", "current_account", "capital_flows", "fed_rate", "global_growth",
    ],
    "real_equity_models": [
        "consumption", "investment", "employment", "earnings", "defaults", "stocks",
    ],
    "asset_policy_models": [
        "household_debt", "commodity", "fiscal", "geopolitics", "tech", "consumer_conf",
    ],
    "proof_models_external": ["fx", "oil"],
    "proof_models_real": ["housing", "gdp"],
    "proof_models_psychology": ["risk_sentiment"],
}

_ID_TO_MODULE = {
    _id: _mod_name for _mod_name, _ids in BUILDER_SOURCES.items() for _id in _ids
}
_MODULE_CACHE = {}


def _builder_for(node_id: str):
    # Lazy per-module import so a probe on one builder file never imports
    # another file that a parallel edit may have left mid-change.
    mod_name = _ID_TO_MODULE[node_id]
    if mod_name not in _MODULE_CACHE:
        _MODULE_CACHE[mod_name] = _load(mod_name, f"{mod_name}.py")
    return getattr(_MODULE_CACHE[mod_name], f"build_{node_id}")


def _dummy_material(name: str) -> bpy.types.Material:
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    return mat


def _probe(node_id: str) -> dict:
    builder = _builder_for(node_id)
    # fresh throwaway scene bits
    coll = bpy.data.collections.new(f"NODE__{node_id}")
    bpy.context.scene.collection.children.link(coll)
    root = bpy.data.objects.new(node_id, None)  # EMPTY
    coll.objects.link(root)
    signature, axis, amount = SPECS.NODE_MOTIONS[node_id]
    root["econ_signature"] = signature
    root["econ_axis"] = axis
    root["econ_amount"] = amount
    body_mat = _dummy_material("MAT__DARK_TITANIUM")
    accent_mat = _dummy_material("MAT__ACCENT__PROBE")

    hard_surface.finalize_model(root, builder(), body_mat, accent_mat)

    body_obj = bpy.data.objects[f"{node_id}__body"]
    accent_obj = bpy.data.objects[f"{node_id}__accent"]
    depsgraph = bpy.context.evaluated_depsgraph_get()
    summary = {"errors": []}
    body = VALID._evaluated_mesh_metrics(body_obj, depsgraph, summary, f"{node_id}/body")
    accent = VALID._evaluated_mesh_metrics(accent_obj, depsgraph, summary, f"{node_id}/accent")

    all_v = body["vertices"] + accent["vertices"]
    mn = Vector((min(v[i] for v in all_v) for i in range(3)))
    mx = Vector((max(v[i] for v in all_v) for i in range(3)))
    ext = mx - mn
    ext_sorted = sorted(float(v) for v in ext)
    ratio = ext_sorted[0] / ext_sorted[2] if ext_sorted[2] > 0 else 0.0
    tri = int(body["triangles"]) + int(accent["triangles"])
    total_area = float(body["area"]) + float(accent["area"])
    accent_ratio = float(accent["area"]) / total_area if total_area > 0 else 0.0
    band = VALID.MODEL_TRIANGLE_BANDS.get(node_id)
    accent_ext = accent["extent"]
    thin = SPECS.ACCENT_THIN_AXIS_CONTRACTS.get(node_id)

    # 3-view silhouette occupancy (the real "reads flat from an angle" metric):
    # a balanced instrument fills a similar area from front/side/top.
    tri_verts = body["triangleVertices"] + accent["triangleVertices"]
    occ = {
        view: len(VALID._projected_occupancy_mask(tri_verts, axes))
        for view, axes in VALID.OCCUPANCY_VIEW_AXES.items()
    }
    occ_max = max(occ.values()) or 1
    occ_ratio = min(occ.values()) / occ_max
    weakest = min(occ, key=occ.get)

    return {
        "id": node_id,
        "minmax_ratio": round(ratio, 4),
        "occupancy": occ,
        "occ_ratio": round(occ_ratio, 4),
        "weakest_view": weakest,
        "extent_xyz": [round(float(v), 4) for v in ext],
        "triangles": tri,
        "band": band,
        "band_ok": (band is None) or (band[0] <= tri <= band[1]),
        "accent_ratio": round(accent_ratio, 4),
        "accent_ratio_ok": 0.10 <= accent_ratio <= 0.20,
        "accent_translation": [round(float(v), 9) for v in accent_obj.location],
        "accent_extent_xyz": [round(float(v), 4) for v in accent_ext],
        "thin_axis_contract": thin,
        "errors": summary["errors"],
    }


def main(argv=None) -> int:
    args = argv if argv is not None else (
        sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", required=True)
    ns = parser.parse_args(args)
    results = []
    for node_id in ns.ids.split(","):
        node_id = node_id.strip()
        if not node_id:
            continue
        results.append(_probe(node_id))
    print("PROBE_JSON:" + json.dumps(results, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
