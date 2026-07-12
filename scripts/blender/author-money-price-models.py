"""Reproducibly author the six monetary, finance, and price instruments."""

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
from money_price_models import (  # noqa: E402
    build_bank_lending,
    build_cpi,
    build_credit_spread,
    build_inflation_exp,
    build_liquidity,
    build_market_rate,
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
    "market_rate": build_market_rate,
    "liquidity": build_liquidity,
    "credit_spread": build_credit_spread,
    "bank_lending": build_bank_lending,
    "cpi": build_cpi,
    "inflation_exp": build_inflation_exp,
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
        default=",".join(SPECS.MONEY_PRICE_IDS),
        help="comma-separated subset of the money/price IDs",
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
    open_output_if_needed(output, "Money/price")
    if bpy.context.scene.name != "SCENE__ECON_NODE_LIBRARY":
        raise RuntimeError(
            f"Unexpected scene {bpy.context.scene.name!r}; run the canonical scaffold first"
        )
    requested = canonical_requested_ids(
        args.ids,
        SPECS.MONEY_PRICE_IDS,
        SPECS.CANONICAL_IDS,
    )
    summary = author_models(
        output=output,
        specs=SPECS,
        builders=BUILDERS,
        requested=requested,
        required_ready=SPECS.PROOF_IDS,
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
