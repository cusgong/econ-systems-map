"""Probe already-authored roots in an open .blend (scratch tool).

Opens a .blend, and for each --ids root reports the same gate metrics as
_measure_model.py by reusing the real validator's _evaluated_mesh_metrics.
Used for policy_rate (scaffold pipeline) and post-chain spot checks.

  blender --background --factory-startup --disable-autoexec --python-exit-code 1 \
    <path.blend> --python scripts/blender/_measure_from_blend.py -- --ids policy_rate
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


def _load(module_name: str, filename: str):
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SPECS = _load("econ_node_specs", "node-specs.py")
VALID = _load("econ_validate", "validate-econ-node-library.py")


def _probe(node_id: str) -> dict:
    body_obj = bpy.data.objects.get(f"{node_id}__body")
    accent_obj = bpy.data.objects.get(f"{node_id}__accent")
    if body_obj is None or accent_obj is None:
        return {"id": node_id, "error": "missing body/accent object"}
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
    return {
        "id": node_id,
        "minmax_ratio": round(ratio, 4),
        "extent_xyz": [round(float(v), 4) for v in ext],
        "triangles": tri,
        "body_triangles": int(body["triangles"]),
        "accent_triangles": int(accent["triangles"]),
        "band": VALID.MODEL_TRIANGLE_BANDS.get(node_id),
        "accent_ratio": round(accent_ratio, 4),
        "accent_translation": [round(float(v), 9) for v in accent_obj.location],
        "errors": summary["errors"],
    }


def main(argv=None) -> int:
    args = argv if argv is not None else (
        sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", required=True)
    ns = parser.parse_args(args)
    results = [_probe(i.strip()) for i in ns.ids.split(",") if i.strip()]
    print("PROBE_JSON:" + json.dumps(results, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
