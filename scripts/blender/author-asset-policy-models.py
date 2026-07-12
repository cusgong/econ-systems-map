"""Reproducibly author the final six asset, policy, and exogenous instruments."""

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

from asset_policy_models import (  # noqa: E402
    build_commodity,
    build_consumer_conf,
    build_fiscal,
    build_geopolitics,
    build_household_debt,
    build_tech,
)
from model_authoring import author_models, canonical_requested_ids, open_output_if_needed  # noqa: E402


def _load_specs():
    module_path = SCRIPT_DIR / "node-specs.py"
    spec = importlib.util.spec_from_file_location("econ_node_specs", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load node specs: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SPECS = _load_specs()
BUILDERS = {
    "household_debt": build_household_debt,
    "commodity": build_commodity,
    "fiscal": build_fiscal,
    "geopolitics": build_geopolitics,
    "tech": build_tech,
    "consumer_conf": build_consumer_conf,
}


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
        default=",".join(SPECS.ASSET_POLICY_IDS),
        help="comma-separated subset of the final asset/policy IDs",
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
    open_output_if_needed(output, "Asset/policy")
    if bpy.context.scene.name != "SCENE__ECON_NODE_LIBRARY":
        raise RuntimeError(
            f"Unexpected scene {bpy.context.scene.name!r}; run the canonical scaffold first"
        )
    requested = canonical_requested_ids(
        args.ids,
        SPECS.ASSET_POLICY_IDS,
        SPECS.CANONICAL_IDS,
    )
    current_ids = set(SPECS.ASSET_POLICY_IDS)
    required_ready = tuple(
        node_id for node_id in SPECS.CANONICAL_IDS if node_id not in current_ids
    )
    summary = author_models(
        output=output,
        specs=SPECS,
        builders=BUILDERS,
        requested=requested,
        required_ready=required_ready,
    )
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
