"""Reproducibly author the six Precision Macro Instruments proof models.

Run with Blender 5.1.2 after the canonical scaffold is open.  The approved
policy-rate geometry is preserved and receives the canonical precision bevel
when upgrading an older scaffold.  Only the five other proof roots are rebuilt.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

import bpy


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from model_authoring import author_models, canonical_requested_ids, open_output_if_needed  # noqa: E402
from proof_models_external import build_fx, build_oil  # noqa: E402
from proof_models_psychology import build_risk_sentiment  # noqa: E402
from proof_models_real import build_gdp, build_housing  # noqa: E402


def _load_specs():
    module_path = SCRIPT_DIR / "node-specs.py"
    spec = importlib.util.spec_from_file_location("econ_node_specs", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load node specs: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_scaffold_module():
    module_path = SCRIPT_DIR / "scaffold-econ-node-library.py"
    spec = importlib.util.spec_from_file_location("econ_node_scaffold", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load policy scaffold source: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SPECS = _load_specs()
BUILDERS = {
    "fx": build_fx,
    "oil": build_oil,
    "housing": build_housing,
    "gdp": build_gdp,
    "risk_sentiment": build_risk_sentiment,
}


def _upgrade_policy_precision_geometry(root: bpy.types.Object) -> str:
    """Rebuild policy from the canonical 48/40 source on every proof pass.

    The approved economic semantics and root metadata remain untouched.  Only
    the smooth circular tessellation is rebuilt before the continuous crown
    and needle bevels are attached.  Rebuilding avoids carrying legacy 64/64
    topology or stale modifier settings into a supposedly reproducible export.
    """

    scaffold = _load_scaffold_module()
    for obj in list(root.children_recursive):
        if obj.type != "MESH":
            continue
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh is not None and mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    materials = {
        name: bpy.data.materials.get(name)
        for name in SPECS.MATERIAL_NAMES
    }
    missing = sorted(name for name, material in materials.items() if material is None)
    if missing:
        raise RuntimeError(f"policy_rate: required materials are missing: {missing}")
    status = scaffold._author_policy_rate(root, materials)
    if status != "created":
        raise RuntimeError(f"policy_rate: deterministic topology rebuild failed: {status}")
    return "rebuilt"


def _arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=SCRIPT_DIR / "econ-node-library.blend",
        help="scaffolded Blender library to update",
    )
    parser.add_argument(
        "--ids",
        default=",".join(BUILDERS),
        help="comma-separated subset of the five non-anchor proof IDs",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    SPECS.require_blender_version(bpy.app.version[:3])
    args = _arguments(
        sys.argv[sys.argv.index("--") + 1 :]
        if argv is None and "--" in sys.argv
        else (argv or [])
    )
    output = args.output.resolve()
    open_output_if_needed(output, "Proof")
    if bpy.context.scene.name != "SCENE__ECON_NODE_LIBRARY":
        raise RuntimeError(
            f"Unexpected scene {bpy.context.scene.name!r}; run the canonical scaffold first"
        )

    requested = canonical_requested_ids(args.ids, BUILDERS, SPECS.CANONICAL_IDS)

    policy_root = bpy.data.objects.get("policy_rate")
    if policy_root is None or not policy_root.get("econ_ready", False):
        raise RuntimeError("Approved policy_rate anchor must already be ready")
    policy_status = _upgrade_policy_precision_geometry(policy_root)
    summary = author_models(
        output=output,
        specs=SPECS,
        builders=BUILDERS,
        requested=requested,
        required_ready=("policy_rate",),
    )
    summary["policyRate"] = policy_status
    print(
        json.dumps(
            summary,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
