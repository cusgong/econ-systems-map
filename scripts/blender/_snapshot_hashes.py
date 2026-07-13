"""Snapshot ROOT_CONTRACT_HASHES (and verify material hashes) from an open .blend.

  blender --background --factory-startup --disable-autoexec <blend> \
    --python scripts/blender/_snapshot_hashes.py
Prints a JSON with roots{id:hash} and materials{name:hash} for repopulating
node-specs.py after a legitimate geometry regeneration.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from model_authoring import snapshot_material_contract, snapshot_root_contract  # noqa: E402


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / filename)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


SPECS = _load("econ_node_specs", "node-specs.py")

roots = {}
for node_id in SPECS.CANONICAL_IDS:
    obj = bpy.data.objects.get(node_id)
    if obj is not None and bool(obj.get("econ_ready", False)):
        roots[node_id] = snapshot_root_contract(obj)

materials = {}
for name in SPECS.MATERIAL_NAMES:
    mat = bpy.data.materials.get(name)
    if mat is not None:
        materials[name] = snapshot_material_contract(mat)

print("SNAPSHOT_JSON:" + json.dumps({"roots": roots, "materials": materials}))
