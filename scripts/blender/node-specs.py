"""Canonical Blender asset contracts derived from data/nodes.js.

This module intentionally has no bpy dependency so its source-of-truth checks can
run under both the system Python and Blender's bundled Python.
"""

from __future__ import annotations

from pathlib import Path
import re


class NodeSpecError(ValueError):
    """Raised when data/nodes.js no longer matches the Blender asset contract."""


BLENDER_VERSION = (5, 1, 2)


def require_blender_version(version) -> None:
    actual = tuple(int(part) for part in tuple(version)[:3])
    if actual != BLENDER_VERSION:
        rendered = ".".join(str(part) for part in actual)
        raise NodeSpecError(
            f"economic node pipeline requires Blender 5.1.2, found {rendered}"
        )


PROOF_IDS = ("policy_rate", "fx", "oil", "housing", "gdp", "risk_sentiment")

NODE_MOTIONS = {
    "policy_rate": ("rotate", "z", 0.20),
    "market_rate": ("translate", "x", 0.12),
    "liquidity": ("rotate", "y", 0.35),
    "credit_spread": ("translate", "x", 0.10),
    "bank_lending": ("translate", "z", 0.12),
    "cpi": ("rotate", "z", 0.22),
    "inflation_exp": ("translate", "z", 0.12),
    "wages": ("rotate", "z", 0.18),
    "fx": ("rotate", "y", 0.26),
    "exports": ("translate", "z", 0.12),
    "current_account": ("rotate", "z", 0.16),
    "capital_flows": ("translate", "z", 0.13),
    "fed_rate": ("rotate", "y", 0.28),
    "global_growth": ("scale", "xyz", 0.06),
    "consumption": ("scale", "xyz", 0.06),
    "investment": ("rotate", "x", 0.18),
    "employment": ("translate", "y", 0.12),
    "earnings": ("translate", "y", 0.12),
    "defaults": ("rotate", "z", 0.16),
    "gdp": ("scale", "xyz", 0.07),
    "stocks": ("translate", "y", 0.14),
    "housing": ("translate", "y", 0.12),
    "household_debt": ("rotate", "y", 0.20),
    "oil": ("rotate", "z", 0.52),
    "commodity": ("translate", "y", 0.10),
    "fiscal": ("rotate", "z", 0.16),
    "geopolitics": ("rotate", "y", 0.18),
    "tech": ("rotate", "z", 0.45),
    "risk_sentiment": ("rotate", "z", 0.30),
    "consumer_conf": ("translate", "y", 0.12),
}

CATEGORY_IDS = (
    "policy",
    "monetary",
    "assets",
    "psychology",
    "real",
    "prices",
    "commodities",
    "exogenous",
    "external",
)

CATEGORY_MATERIALS = {
    "policy": "MAT__ACCENT__POLICY",
    "monetary": "MAT__ACCENT__MONETARY",
    "assets": "MAT__ACCENT__ASSETS",
    "psychology": "MAT__ACCENT__PSYCHOLOGY",
    "real": "MAT__ACCENT__REAL",
    "prices": "MAT__ACCENT__PRICES",
    "commodities": "MAT__ACCENT__COMMODITIES",
    "exogenous": "MAT__ACCENT__EXOGENOUS",
    "external": "MAT__ACCENT__EXTERNAL",
}

MATERIAL_NAMES = (
    "MAT__DARK_TITANIUM",
    "MAT__SATIN_ALLOY",
    "MAT__TECHNICAL_CERAMIC",
    "MAT__ACCENT__POLICY",
    "MAT__ACCENT__MONETARY",
    "MAT__ACCENT__ASSETS",
    "MAT__ACCENT__PSYCHOLOGY",
    "MAT__ACCENT__REAL",
    "MAT__ACCENT__PRICES",
    "MAT__ACCENT__COMMODITIES",
    "MAT__ACCENT__EXOGENOUS",
    "MAT__ACCENT__EXTERNAL",
    "MAT__SMOKED_LENS",
)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
NODES_PATH = _PROJECT_ROOT / "data" / "nodes.js"
_NODE_RECORD_RE = re.compile(
    r"\{\s*id:\s*'(?P<id>[a-z0-9_]+)'\s*,\s*cat:\s*'(?P<cat>[a-z0-9_]+)'",
    re.MULTILINE,
)


def _array_block(source: str, constant_name: str) -> str:
    marker = f"export const {constant_name} = ["
    start = source.find(marker)
    if start < 0:
        raise NodeSpecError(f"missing {constant_name} block in data/nodes.js")
    start += len(marker)
    end = source.find("\n];", start)
    if end < 0:
        raise NodeSpecError(f"unterminated {constant_name} block in data/nodes.js")
    return source[start:end]


def validate_nodes_source(source: str) -> tuple[tuple[str, str], ...]:
    """Parse and validate canonical node IDs/categories from a nodes.js string."""

    records = tuple(
        (match.group("id"), match.group("cat"))
        for match in _NODE_RECORD_RE.finditer(_array_block(source, "NODES"))
    )
    ids = tuple(node_id for node_id, _category in records)
    if not records:
        raise NodeSpecError("NODES block contains no canonical records")
    if len(ids) != len(set(ids)):
        duplicates = sorted({node_id for node_id in ids if ids.count(node_id) > 1})
        raise NodeSpecError(f"duplicate canonical IDs: {duplicates}")

    unknown_categories = sorted({category for _, category in records} - set(CATEGORY_IDS))
    if unknown_categories:
        raise NodeSpecError(f"unknown category IDs: {unknown_categories}")

    motion_ids = set(NODE_MOTIONS)
    canonical_ids = set(ids)
    if canonical_ids != motion_ids:
        missing = sorted(canonical_ids - motion_ids)
        extra = sorted(motion_ids - canonical_ids)
        raise NodeSpecError(
            "motion IDs do not match canonical IDs: "
            f"missingMotions={missing}, unknownMotions={extra}"
        )
    if len(ids) != 30:
        raise NodeSpecError(f"expected 30 canonical IDs, found {len(ids)}")
    return records


_NODE_SOURCE = NODES_PATH.read_text(encoding="utf-8")
NODE_RECORDS = validate_nodes_source(_NODE_SOURCE)
CANONICAL_IDS = tuple(node_id for node_id, _category in NODE_RECORDS)
NODE_CATEGORIES = dict(NODE_RECORDS)
