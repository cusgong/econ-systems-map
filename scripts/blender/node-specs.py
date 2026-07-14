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
MONEY_PRICE_IDS = (
    "market_rate",
    "liquidity",
    "credit_spread",
    "bank_lending",
    "cpi",
    "inflation_exp",
)
WAGE_EXTERNAL_IDS = (
    "wages",
    "exports",
    "current_account",
    "capital_flows",
    "fed_rate",
    "global_growth",
)
REAL_EQUITY_IDS = (
    "consumption",
    "investment",
    "employment",
    "earnings",
    "defaults",
    "stocks",
)
ASSET_POLICY_IDS = (
    "household_debt",
    "commodity",
    "fiscal",
    "geopolitics",
    "tech",
    "consumer_conf",
)

# Canonical authored child-space contracts.  Blender uses +Z up and exports a
# child translation (x, y, z) as glTF (x, z, -y).  These values are deliberately
# stored outside the .blend so a wrong-but-nonempty pivot label or a subtly
# drifted child transform cannot self-certify through asset metadata.
ACCENT_CONTRACTS = {
    "policy_rate": {
        "pivotLabel": "needle_rotation_center",
        "blenderTranslation": (0.0, 0.0, 0.0),
    },
    "fx": {
        "pivotLabel": "true offset ring center; counter-rotate local Y",
        "blenderTranslation": (0.0, 0.0, 0.189254373),
    },
    "oil": {
        "pivotLabel": "coaxial side-handwheel hub; Blender Y exports to glTF Z",
        "blenderTranslation": (0.386154979, -0.518823147, 0.26635474),
    },
    "housing": {
        "pivotLabel": "offset transfer-beam center; translate local Y",
        "blenderTranslation": (0.0, 0.0, 0.283682168),
    },
    "gdp": {
        "pivotLabel": "asymmetric counterweight hub center; scale XYZ",
        "blenderTranslation": (0.091623865, 0.0, 0.516425312),
    },
    "risk_sentiment": {
        "pivotLabel": "upper pendulum hinge",
        "blenderTranslation": (0.0, 0.016958633, 0.48453176),
    },
    "market_rate": {
        "pivotLabel": "maturity carriage centroid; translate along glTF X / Blender X",
        "blenderTranslation": (0.462436497, 0.082038425, 0.372194201),
    },
    "liquidity": {
        "pivotLabel": "central circulation rotor hub; glTF Y equals Blender Z",
        "blenderTranslation": (0.0, 0.0, 0.057451032),
    },
    "credit_spread": {
        "pivotLabel": "moving jaw slide center; translate along glTF X / Blender X",
        "blenderTranslation": (0.0, 0.0, 0.106977254),
    },
    "bank_lending": {
        "pivotLabel": "linked piston-face center; glTF +Z advances along Blender -Y",
        "blenderTranslation": (0.0, -0.506167293, -0.316993654),
    },
    "cpi": {
        "pivotLabel": "weighted drum index axis; glTF +Z is Blender -Y",
        "blenderTranslation": (0.0, 0.0, 0.193972602),
    },
    "inflation_exp": {
        "pivotLabel": "forward focus-lens center; glTF +Z advances along Blender -Y",
        "blenderTranslation": (0.0, -0.137158737, 0.22402592),
    },
    "wages": {
        "pivotLabel": "ratchet step axis; glTF Z rotation is Blender -Y",
        "blenderTranslation": (0.319042146, 0.0, 0.342674881),
    },
    "exports": {
        "pivotLabel": "outbound vane plate; glTF +Z advances along Blender -Y",
        "blenderTranslation": (0.0, -0.461323857, 0.077255189),
    },
    "current_account": {
        "pivotLabel": "bilateral balance axle; glTF Z rotation is Blender -Y",
        "blenderTranslation": (0.038677376, 0.0, 0.267225444),
    },
    "capital_flows": {
        "pivotLabel": "inflow gate face; glTF +Z advances along Blender -Y",
        "blenderTranslation": (0.0, 0.0, 0.547074854),
    },
    "fed_rate": {
        "pivotLabel": "orbital governor axis; glTF Y rotation is Blender Z",
        "blenderTranslation": (0.0, 0.0, 0.469661504),
    },
    "global_growth": {
        "pivotLabel": "orthogonal growth-band centroid; scale XYZ",
        "blenderTranslation": (0.0, 0.0, 0.54979527),
    },
    "consumption": {
        "pivotLabel": "inertia flywheel clutch axis; scale XYZ about the central hub",
        "blenderTranslation": (0.0, 0.0, 0.496395916),
    },
    "investment": {
        "pivotLabel": "lower truss hinge; rotate about glTF X / Blender X",
        "blenderTranslation": (-0.298793852, -0.283969134, -0.313982129),
    },
    "employment": {
        "pivotLabel": "three-column locking-ring centroid; translate along glTF Y / Blender Z",
        "blenderTranslation": (0.0, -0.330531627, -0.550886035),
    },
    "earnings": {
        "pivotLabel": "stair-carrier centroid; translate along glTF Y / Blender Z",
        "blenderTranslation": (0.314508706, -0.015725434, 0.338096857),
    },
    "defaults": {
        "pivotLabel": "safety-latch hinge; rotate about glTF Z / Blender -Y",
        "blenderTranslation": (-1.7e-08, 0.0, 0.4250817),
    },
    "stocks": {
        "pivotLabel": "price-spindle carriage center; translate along glTF Y / Blender Z",
        "blenderTranslation": (0.349935025, -0.221477866, 0.124027602),
    },
    "household_debt": {
        "pivotLabel": "tightening coil axis; rotate glTF Y / Blender Z",
        "blenderTranslation": (0.0, 0.0, 0.881324232),
    },
    "commodity": {
        "pivotLabel": "faceted ore-core lift center; glTF Y equals Blender Z",
        "blenderTranslation": (0.0, 0.0, 0.0),
    },
    "fiscal": {
        "pivotLabel": "three-outlet valve-bank center; glTF Z equals Blender -Y",
        "blenderTranslation": (0.0, -0.450984061, -0.328975737),
    },
    "geopolitics": {
        "pivotLabel": "opposed C-clamp tension axis; rotate glTF Y / Blender Z",
        "blenderTranslation": (-0.00021197, 0.0, 0.0),
    },
    "tech": {
        "pivotLabel": "compressor impeller bearing hub; glTF Z equals Blender -Y",
        "blenderTranslation": (0.0, -0.243114233, 0.0),
    },
    "consumer_conf": {
        "pivotLabel": "central confidence-vane lift center; glTF Y equals Blender Z",
        "blenderTranslation": (0.0, -0.366197497, 0.251760811),
    },
}
PROOF_ACCENT_CONTRACTS = {
    node_id: ACCENT_CONTRACTS[node_id] for node_id in PROOF_IDS
}

# Minimum weighted source-edge coverage per proof object and material role.
# The gate is intentionally model-specific: a single token-beveled shell can no
# longer satisfy a complex portal, counterweight cage, or coaxial valve model.
BEVEL_TAGGED_EDGE_MINIMUMS = {
    "policy_rate": {"body": 48, "accent": 22},
    "fx": {"body": 112, "accent": 32},
    "oil": {"body": 48, "accent": 48},
    "housing": {"body": 172, "accent": 8},
    "gdp": {"body": 156, "accent": 16},
    "risk_sentiment": {"body": 120, "accent": 28},
    "market_rate": {"body": 48, "accent": 152},
    "liquidity": {"body": 56, "accent": 60},
    "credit_spread": {"body": 60, "accent": 30},
    "bank_lending": {"body": 160, "accent": 72},
    "cpi": {"body": 120, "accent": 64},
    "inflation_exp": {"body": 132, "accent": 48},
    "wages": {"body": 72, "accent": 104},
    "exports": {"body": 84, "accent": 21},
    "current_account": {"body": 132, "accent": 69},
    "capital_flows": {"body": 56, "accent": 63},
    "fed_rate": {"body": 168, "accent": 73},
    "global_growth": {"body": 40, "accent": 21},
    "consumption": {"body": 76, "accent": 40},
    "investment": {"body": 128, "accent": 72},
    "employment": {"body": 120, "accent": 56},
    "earnings": {"body": 160, "accent": 21},
    "defaults": {"body": 20, "accent": 21},
    "stocks": {"body": 128, "accent": 52},
    "household_debt": {"body": 24, "accent": 36},
    "commodity": {"body": 142, "accent": 48},
    "fiscal": {"body": 88, "accent": 32},
    "geopolitics": {"body": 120, "accent": 72},
    "tech": {"body": 112, "accent": 94},
    "consumer_conf": {"body": 108, "accent": 68},
}
PROOF_BEVEL_TAGGED_EDGE_MINIMUMS = {
    node_id: BEVEL_TAGGED_EDGE_MINIMUMS[node_id] for node_id in PROOF_IDS
}

ACCENT_THIN_AXIS_CONTRACTS = {
    "liquidity": ("z", 0.45),
    "bank_lending": ("y", 0.45),
    "cpi": ("y", 0.45),
    "inflation_exp": ("y", 0.45),
    "wages": ("y", 0.45),
    "exports": ("y", 0.45),
    "current_account": ("y", 0.45),
    "capital_flows": ("y", 0.45),
    "fed_rate": ("z", 0.45),
    "investment": ("y", 0.45),
    "earnings": ("y", 0.45),
    "defaults": ("y", 0.45),
    "fiscal": ("y", 0.45),
    "geopolitics": ("y", 0.45),
    "tech": ("y", 0.45),
    "consumer_conf": ("y", 0.45),
}

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

# Frozen Blender 5.1.2 render contracts. These hashes are produced by
# model_authoring.snapshot_material_contract from a fresh canonical scaffold;
# they prevent a pre-existing PBR/node-tree edit from becoming the next batch's
# accepted baseline merely because it remains unchanged during that batch.
MATERIAL_CONTRACT_HASHES = {
    "MAT__ACCENT__ASSETS": "7dd451c99de7404e5741103856415967666ae6595bb9ca88e35c6815cf34c927",
    "MAT__ACCENT__COMMODITIES": "006c5f375c855cf484070f759dfec8a1b715c3f78d5a1598fba787307655f1f0",
    "MAT__ACCENT__EXOGENOUS": "3ecea39bac193ad7d36da4fa912100d82cefb7a5a7ad57bf7e0ca7ddff1573f1",
    "MAT__ACCENT__EXTERNAL": "155457abd2f99f4d4872b9da8e1d629b78048188a05c1e444bbe05878cd7477e",
    "MAT__ACCENT__MONETARY": "19ec08570b93d5bbbceb88e5193a272f2221dc587f62db5f2a7eaecd9e988cbe",
    "MAT__ACCENT__POLICY": "28c3b71ca41c6475f38023672128c73731c33fffbdff57179b8ae79390f9df18",
    "MAT__ACCENT__PRICES": "1dfad5f8f49032cf62589c9569b0106a29d1541352941c298d3b90e62a40399e",
    "MAT__ACCENT__PSYCHOLOGY": "03f9e9ead9d7c85a1c87d877a465e5a13b1c4785f4f52aadaac4bb4515dfe643",
    "MAT__ACCENT__REAL": "428bceefe1fe5d337d7514945ce56110073911f8fb1a3b920f051e8cfa7780ea",
    "MAT__DARK_TITANIUM": "813021b9f4fae05200aca52781827871d86ad7ab175fff500e936acd2157fdd0",
    "MAT__SATIN_ALLOY": "234716ef805fe246ba50294431f8140be024b8454bc74bd34f9eb21db95f55e6",
    "MAT__SMOKED_LENS": "6a4f49271fb732c3a4b4af65d94d2957dd409d84c2471b54fbbf99d339f122c4",
    "MAT__TECHNICAL_CERAMIC": "95e7770812e4adf9f08087cb929af0f06f853836dc05b6f6ffc25b94da18c3a8",
}

ROOT_CONTRACT_HASHES = {
    "policy_rate": "21c00bbfae4a8eca9d1118e5887fe0fb33a00058120ac3eecbdaedce0af643a0",
    "market_rate": "f72139f0e5f444258cd170ee9d217118b83190f63930af204d09644b99920eb9",
    "liquidity": "ab4ee3aa25d765d3b032a570f184cd34b5a6070e6279122161202996a13545e0",
    "credit_spread": "2c3f73add6b56c296155c2880c8908d8c2c53e461f51e9f5793a7b67d2716390",
    "bank_lending": "744e762d5dd8edc9af032630cb98b7f3b328c6e8c48dd82bb94faa4105147ed4",
    "cpi": "6fec415c8598d87757ddb496c8c9324b94ec14d5101e1181bc701be801fa7f9b",
    "inflation_exp": "35133c34ae7fcb3b9095956deec6ab35b167de4d61d625393cff5df094f89a26",
    "wages": "72957c2ee925f720caa3f6c33aa8a2767c8e5cf1d8cd493558402f3afbe396e1",
    "fx": "4c90bab014ab11250eca2b464ae70f3893a3a60c0894f9010c246274f6597f75",
    "exports": "c9d89977d595ea2bb48bc7d9bacecfb59b3a0becf1dc9bb6efce279024e50a1d",
    "current_account": "799add5a9ba965578dc3f8aef500a78fc1926b84e6b6513ac3074c63ff008445",
    "capital_flows": "8d6b8b22c6a6881bb516aa58081b2c2ce77a02699d74d24e57657c0969fdabc9",
    "fed_rate": "b8eaec3332c1a6dc2a4ee596c9ec6e01ba60bc16684df4791c45b0a9083498b9",
    "global_growth": "870853dbb61f98562cfc740d3f20bc05212962168cd8507e765f9da56157dea1",
    "consumption": "f1220743607ad708e60e199dffe9aa64692cb0650ddde80bec20df02cec92437",
    "investment": "c333ecaaf5caec2b52504952b52572660d02b17df46a502fea520495c6e56f88",
    "employment": "2d3067d1be88ecc3380826d4bd5da5aa99f49a41e61cb81292eedf717f01f6e2",
    "earnings": "114a1c58e23bfaca691904cafe9fd998a7f0ecbb01de39256bce2aac3c6ae02c",
    "defaults": "70c9c573b961bdf361609c5f478d581d61de51514d3287f7481736a4d780065f",
    "gdp": "11ed6722089addaa9c4ae683f542277c7122083da1f2766dc7f561423080ed2e",
    "stocks": "49f6801001e8a45a20eca87195082f82ee81870480935f1ca3740313ad8f85ab",
    "housing": "3ddf07e389033806db542389576fb5649e4baa0a07f7377f578547e9555b68cf",
    "household_debt": "f752725c54011212e05b054f9d759f24a167ced34234610141b3ce7a9354c3b7",
    "oil": "29e99e46ca8ac2523601116491490c355cfeb7bc12a14e00e29b2a534b76dcf1",
    "commodity": "4f5286153f6cc2d6839ec6a2d7503fad4a3d7cacf257f04974647292c9395c38",
    "fiscal": "02197e8a3cbc79c84eeee0da3b88bdb48ebf54b8c03009ecef25cdb5f855b0af",
    "geopolitics": "90fa5cd39d6668c807ca2167370805ba77ff5b9dbe0e64bd920ab7f07a9def24",
    "tech": "fc6c9eca3a8723527c05b2790c3c2d6f2b86e56b12897c3596cfb826172203e6",
    "risk_sentiment": "1bd39dc4e86619990336b998ae50bcee0a4b02076b5c3b74827959bd6d3513d0",
    "consumer_conf": "ca8e205f9c2592f7a7977483e5b34986bda001bd565e07bcceeed7dacafd11a7",
}

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
