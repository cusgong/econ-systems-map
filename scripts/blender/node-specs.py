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
        "blenderTranslation": (0.113874286, -0.022774857, -0.045549728),
    },
    "oil": {
        "pivotLabel": "coaxial side-handwheel hub; Blender Y exports to glTF Z",
        "blenderTranslation": (0.386154979, -0.518823147, 0.26635474),
    },
    "housing": {
        "pivotLabel": "offset transfer-beam center; translate local Y",
        "blenderTranslation": (0.184746787, -0.161061332, 0.561345994),
    },
    "gdp": {
        "pivotLabel": "asymmetric counterweight hub center; scale XYZ",
        "blenderTranslation": (-0.016911505, 0.0, 0.011266772),
    },
    "risk_sentiment": {
        "pivotLabel": "upper pendulum hinge",
        "blenderTranslation": (0.0, -0.184055194, 0.46759966),
    },
    "market_rate": {
        "pivotLabel": "maturity carriage centroid; translate along glTF X / Blender X",
        "blenderTranslation": (0.10401421, 0.0, -0.09159901),
    },
    "liquidity": {
        "pivotLabel": "central circulation rotor hub; glTF Y equals Blender Z",
        "blenderTranslation": (0.0, 0.0, 0.057451032),
    },
    "credit_spread": {
        "pivotLabel": "moving jaw slide center; translate along glTF X / Blender X",
        "blenderTranslation": (0.385996073, 0.0, 0.139923587),
    },
    "bank_lending": {
        "pivotLabel": "linked piston-face center; glTF +Z advances along Blender -Y",
        "blenderTranslation": (0.0, -0.415979475, -0.019808527),
    },
    "cpi": {
        "pivotLabel": "weighted drum index axis; glTF +Z is Blender -Y",
        "blenderTranslation": (-0.021479525, -0.353672683, -0.000774685),
    },
    "inflation_exp": {
        "pivotLabel": "forward focus-lens center; glTF +Z advances along Blender -Y",
        "blenderTranslation": (0.076443359, -0.43873474, 0.203108996),
    },
    "wages": {
        "pivotLabel": "ratchet step axis; glTF Z rotation is Blender -Y",
        "blenderTranslation": (-0.024892416, -0.295373261, 0.014065397),
    },
    "exports": {
        "pivotLabel": "outbound vane plate; glTF +Z advances along Blender -Y",
        "blenderTranslation": (-0.006036391, -0.434617996, -0.036218166),
    },
    "current_account": {
        "pivotLabel": "bilateral balance axle; glTF Z rotation is Blender -Y",
        "blenderTranslation": (0.011621565, -0.395133615, 0.081351019),
    },
    "capital_flows": {
        "pivotLabel": "inflow gate face; glTF +Z advances along Blender -Y",
        "blenderTranslation": (0.005921125, -0.401074079, 0.067807877),
    },
    "fed_rate": {
        "pivotLabel": "orbital governor axis; glTF Y rotation is Blender Z",
        "blenderTranslation": (-0.120200329, 0.0, 0.246410653),
    },
    "global_growth": {
        "pivotLabel": "orthogonal growth-band centroid; scale XYZ",
        "blenderTranslation": (-0.025691239, 0.091176004, -0.00004871),
    },
    "consumption": {
        "pivotLabel": "inertia flywheel clutch axis; scale XYZ about the central hub",
        "blenderTranslation": (-0.004210508, -0.185766399, 0.04645671),
    },
    "investment": {
        "pivotLabel": "lower truss hinge; rotate about glTF X / Blender X",
        "blenderTranslation": (-0.298793852, -0.283969134, -0.313982129),
    },
    "employment": {
        "pivotLabel": "three-column locking-ring centroid; translate along glTF Y / Blender Z",
        "blenderTranslation": (0.0, -0.159827262, 0.224273741),
    },
    "earnings": {
        "pivotLabel": "stair-carrier centroid; translate along glTF Y / Blender Z",
        "blenderTranslation": (0.067396335, -0.342598037, 0.039314529),
    },
    "defaults": {
        "pivotLabel": "safety-latch hinge; rotate about glTF Z / Blender -Y",
        "blenderTranslation": (0.13396167, -0.523008688, 0.022326945),
    },
    "stocks": {
        "pivotLabel": "price-spindle carriage center; translate along glTF Y / Blender Z",
        "blenderTranslation": (0.053486314, -0.33619988, 0.106972672),
    },
    "household_debt": {
        "pivotLabel": "tightening coil axis; rotate glTF Y / Blender Z",
        "blenderTranslation": (0.024852229, 0.0, -0.044025287),
    },
    "commodity": {
        "pivotLabel": "faceted ore-core lift center; glTF Y equals Blender Z",
        "blenderTranslation": (0.0, 0.0, 0.0),
    },
    "fiscal": {
        "pivotLabel": "three-outlet valve-bank center; glTF Z equals Blender -Y",
        "blenderTranslation": (0.0, -0.19692634, 0.560146034),
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
        "blenderTranslation": (0.0, -0.415843666, 0.042650625),
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
    "fx": {"body": 28, "accent": 24},
    "oil": {"body": 48, "accent": 48},
    "housing": {"body": 119, "accent": 54},
    "gdp": {"body": 84, "accent": 72},
    "risk_sentiment": {"body": 48, "accent": 24},
    "market_rate": {"body": 60, "accent": 72},
    "liquidity": {"body": 56, "accent": 60},
    "credit_spread": {"body": 100, "accent": 48},
    "bank_lending": {"body": 100, "accent": 68},
    "cpi": {"body": 132, "accent": 24},
    "inflation_exp": {"body": 84, "accent": 24},
    "wages": {"body": 116, "accent": 36},
    "exports": {"body": 148, "accent": 72},
    "current_account": {"body": 108, "accent": 108},
    "capital_flows": {"body": 140, "accent": 100},
    "fed_rate": {"body": 176, "accent": 52},
    "global_growth": {"body": 48, "accent": 48},
    "consumption": {"body": 156, "accent": 44},
    "investment": {"body": 128, "accent": 72},
    "employment": {"body": 120, "accent": 64},
    "earnings": {"body": 144, "accent": 104},
    "defaults": {"body": 64, "accent": 36},
    "stocks": {"body": 88, "accent": 64},
    "household_debt": {"body": 137, "accent": 60},
    "commodity": {"body": 142, "accent": 48},
    "fiscal": {"body": 112, "accent": 60},
    "geopolitics": {"body": 120, "accent": 72},
    "tech": {"body": 112, "accent": 94},
    "consumer_conf": {"body": 152, "accent": 52},
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
    "policy_rate": "0454fd0dc0995b20ce3c4d4f745db4e7b2ade286dd51601ba97fea5993e0cc1f",
    "market_rate": "c123ec28380a541b7958f915f8c4a3b42a293f2c0f3fe3313d920f1cd5cf3c88",
    "liquidity": "ab4ee3aa25d765d3b032a570f184cd34b5a6070e6279122161202996a13545e0",
    "credit_spread": "5a14feb425a67dc2b6bdda791af2b7706ae71f7ea760d67cb8095377ec54be57",
    "bank_lending": "268a46734228a058411c9123b6e689a51a455f9de8f6702a76c573d08626ea36",
    "cpi": "59a3ed39e17f4a052312a86d3314dcf0b08a58002d9f5b3e2b9da44f2e235edf",
    "inflation_exp": "08208434fc3c2090dba723a849c8aa36c882ce9dc69b82b70678d29a968c9381",
    "wages": "d1757d2f1e3c652efd7015ea6e89845fa36b8175d9e013e0516ea4908dd4d089",
    "fx": "3fd2d9971b459ba7d4b5f5eb9f7657e4cf3d577282bba7d95bb12082a6ca9275",
    "exports": "3270cee265235905282e8e65d0e8c0fd0bd6cdda78843b79fe619255abdad6ff",
    "current_account": "a5e7cb98f5ef1b3c865e994346c5429e3d4a9a4267abfffb4a8e3e0beae4a7f0",
    "capital_flows": "452c74b36bce3b6ba28826874de91d161ec436b1339ffdab0362d01b21d00824",
    "fed_rate": "0702e0393eaa0389c00804bec55b02d6568084f4e8bb5e189da0b396341aa6d5",
    "global_growth": "5378acec3d08ecd1dcf5cb006d3a6f7f1e5fbcb163541d52bff77f361b70c7e5",
    "consumption": "0167bdc0fdf690b598fab5e55e84d337a1798f2abb480f209b0e12860631bc71",
    "investment": "c333ecaaf5caec2b52504952b52572660d02b17df46a502fea520495c6e56f88",
    "employment": "4f6deb4e217a447bdde2468137c615ebbb14248e055fe3ba57fdb5723e9e99d9",
    "earnings": "27edbacd38a2df00f5e7a1a423504c72bea8dae607be3fb3945bcf8fc941e5f5",
    "defaults": "f084d9ca496fa8e73202560e1db25efb5149054e9c7af79e7e60e4f76c3855fa",
    "gdp": "243212c74b85ccb2ca26823c599b38c859cded86d3259e750c8e3296f59244fa",
    "stocks": "afd40b50703d2a3991fa0a04d06cda8fceedc809a8589e8fbbbcb6001bab1161",
    "housing": "f81153dd1c101c17020e48ee9bf1768af997570a2195f631af0356ad6ff9a8da",
    "household_debt": "28512a3a79eddd531f39922edfcd469303f24b53f3f7ded765d3e0fb7b3ecba4",
    "oil": "29e99e46ca8ac2523601116491490c355cfeb7bc12a14e00e29b2a534b76dcf1",
    "commodity": "4f5286153f6cc2d6839ec6a2d7503fad4a3d7cacf257f04974647292c9395c38",
    "fiscal": "f2f4493069a26d43800a3906e62768b77afe0f31a65d9955b26ec1d9656f4bf5",
    "geopolitics": "90fa5cd39d6668c807ca2167370805ba77ff5b9dbe0e64bd920ab7f07a9def24",
    "tech": "fc6c9eca3a8723527c05b2790c3c2d6f2b86e56b12897c3596cfb826172203e6",
    "risk_sentiment": "6fe7a5d0fd3503117969197932fdc735513d4d9a8e82b8c9e897a017e4c9ee9c",
    "consumer_conf": "9c6f5cf5233490ffef42f4258627a4db7e59a41172ce747d2e7ed99b80d1ddaf",
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
