"""Reproducibly author the six real-economy and equity instruments."""

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
from real_equity_models import (  # noqa: E402
    build_consumption,
    build_defaults,
    build_earnings,
    build_employment,
    build_investment,
    build_stocks,
)


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
    "consumption": build_consumption,
    "investment": build_investment,
    "employment": build_employment,
    "earnings": build_earnings,
    "defaults": build_defaults,
    "stocks": build_stocks,
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
        default=",".join(SPECS.REAL_EQUITY_IDS),
        help="comma-separated subset of the real/equity IDs",
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
    open_output_if_needed(output, "Real/equity")
    if bpy.context.scene.name != "SCENE__ECON_NODE_LIBRARY":
        raise RuntimeError(
            f"Unexpected scene {bpy.context.scene.name!r}; run the canonical scaffold first"
        )
    requested = canonical_requested_ids(
        args.ids,
        SPECS.REAL_EQUITY_IDS,
        SPECS.CANONICAL_IDS,
    )
    summary = author_models(
        output=output,
        specs=SPECS,
        builders=BUILDERS,
        requested=requested,
        required_ready=(
            SPECS.PROOF_IDS
            + SPECS.MONEY_PRICE_IDS
            + SPECS.WAGE_EXTERNAL_IDS
        ),
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
