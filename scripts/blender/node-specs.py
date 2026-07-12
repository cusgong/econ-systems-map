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
        "blenderTranslation": (0.113864593, 0.0, -0.045545854),
    },
    "oil": {
        "pivotLabel": "coaxial side-handwheel hub; Blender Y exports to glTF Z",
        "blenderTranslation": (0.385164529, -0.461752892, 0.244914398),
    },
    "housing": {
        "pivotLabel": "offset transfer-beam center; translate local Y",
        "blenderTranslation": (0.193240196, -0.155534804, 0.558511257),
    },
    "gdp": {
        "pivotLabel": "asymmetric counterweight hub center; scale XYZ",
        "blenderTranslation": (-0.018568849, 0.0, 0.012370927),
    },
    "risk_sentiment": {
        "pivotLabel": "upper pendulum hinge",
        "blenderTranslation": (0.0, -0.123495959, 0.527664542),
    },
    "market_rate": {
        "pivotLabel": "maturity carriage centroid; translate along glTF X / Blender X",
        "blenderTranslation": (0.11950956, 0.021142018, -0.041641646),
    },
    "liquidity": {
        "pivotLabel": "central circulation rotor hub; glTF Y equals Blender Z",
        "blenderTranslation": (0.0, 0.0, 0.078138823),
    },
    "credit_spread": {
        "pivotLabel": "moving jaw slide center; translate along glTF X / Blender X",
        "blenderTranslation": (0.417967223, 0.057470493, 0.062695083),
    },
    "bank_lending": {
        "pivotLabel": "linked piston-face center; glTF +Z advances along Blender -Y",
        "blenderTranslation": (0.0, -0.520834425, 0.078495545),
    },
    "cpi": {
        "pivotLabel": "weighted drum index axis; glTF +Z is Blender -Y",
        "blenderTranslation": (-0.022251722, -0.290064055, -0.000802558),
    },
    "inflation_exp": {
        "pivotLabel": "forward focus-lens center; glTF +Z advances along Blender -Y",
        "blenderTranslation": (0.071056959, -0.421090063, 0.239227718),
    },
    "wages": {
        "pivotLabel": "ratchet step axis; glTF Z rotation is Blender -Y",
        "blenderTranslation": (-0.027025283, -0.310501175, 0.01527055),
    },
    "exports": {
        "pivotLabel": "outbound vane plate; glTF +Z advances along Blender -Y",
        "blenderTranslation": (-0.005920718, -0.346381733, -0.035524308),
    },
    "current_account": {
        "pivotLabel": "bilateral balance axle; glTF Z rotation is Blender -Y",
        "blenderTranslation": (0.012594465, -0.362090876, 0.157534949),
    },
    "capital_flows": {
        "pivotLabel": "inflow gate face; glTF +Z advances along Blender -Y",
        "blenderTranslation": (0.005921125, -0.401074079, 0.067807877),
    },
    "fed_rate": {
        "pivotLabel": "orbital governor axis; glTF Y rotation is Blender Z",
        "blenderTranslation": (-0.09965805, 0.0, 0.286894386),
    },
    "global_growth": {
        "pivotLabel": "orthogonal growth-band centroid; scale XYZ",
        "blenderTranslation": (-0.025691239, 0.091176004, -0.00004871),
    },
    "consumption": {
        "pivotLabel": "inertia flywheel clutch axis; scale XYZ about the central hub",
        "blenderTranslation": (-0.004444095, -0.165113561, 0.04903402),
    },
    "investment": {
        "pivotLabel": "lower truss hinge; rotate about glTF X / Blender X",
        "blenderTranslation": (-0.31260567, -0.231879583, -0.328496076),
    },
    "employment": {
        "pivotLabel": "three-column locking-ring centroid; translate along glTF Y / Blender Z",
        "blenderTranslation": (0.0, -0.086492246, 0.170440603),
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
        "blenderTranslation": (0.053718327, -0.309519886, 0.102320624),
    },
    "household_debt": {
        "pivotLabel": "tightening coil axis; rotate glTF Y / Blender Z",
        "blenderTranslation": (0.028632849, 0.0, -0.023039953),
    },
    "commodity": {
        "pivotLabel": "faceted ore-core lift center; glTF Y equals Blender Z",
        "blenderTranslation": (0.0, 0.0, 0.0),
    },
    "fiscal": {
        "pivotLabel": "three-outlet valve-bank center; glTF Z equals Blender -Y",
        "blenderTranslation": (0.0, -0.196796509, 0.578694136),
    },
    "geopolitics": {
        "pivotLabel": "opposed C-clamp tension axis; rotate glTF Y / Blender Z",
        "blenderTranslation": (-0.000222626, 0.020040749, 0.0),
    },
    "tech": {
        "pivotLabel": "compressor impeller bearing hub; glTF Z equals Blender -Y",
        "blenderTranslation": (0.0, -0.098511963, 0.0),
    },
    "consumer_conf": {
        "pivotLabel": "central confidence-vane lift center; glTF Y equals Blender Z",
        "blenderTranslation": (0.0, -0.131208829, 0.058315035),
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
    "policy_rate": "2cbb913f0a956c0c9e0aec4ceb21a832c9ccf3cb65ff633e94953d500d34251d",
    "market_rate": "3115414cab27f2a4962f62a1003153f8afc9da7e80f088e670a5bb1801241daf",
    "liquidity": "17f913f3ad44746bee6ad5f80542bd3ceee802fb98bd789f598f15aae16c1491",
    "credit_spread": "6faeca43968e78a7fa3449c2356f81253b05333c5da3e9029eb98ddfe602c42b",
    "bank_lending": "5a09763d08ab4c9b73f83f9d7b2a1338a0bb7923316dee8cfac8d550ecddca44",
    "cpi": "e20966949b4917713a6aaed4b187af263bed971dd05ab190138d0de09cb50039",
    "inflation_exp": "ead69863ce3eb3d2847d3296472d715f0cc09ae36126ccf75088bd7776380088",
    "wages": "8cf14c683de9ce5b020958e791e1f79a6c5045356b4b64721fec3ef4c6ccb357",
    "fx": "9092f21572914b605cf00d5be07b0534020f7f0179dd1930f7c216e689496b7c",
    "exports": "076ae55ac49fc979674cfd673894b35264a15a24125e8358f0666fc441f0e3b5",
    "current_account": "77bfd2c305b92f466f8c0aeebbcb16ad614e1f7b1b243def0c15aa386cec1f64",
    "capital_flows": "452c74b36bce3b6ba28826874de91d161ec436b1339ffdab0362d01b21d00824",
    "fed_rate": "36f780c13c0584c40f8244d2282db6970bdcd1922461d55c2a385f77635d8cc0",
    "global_growth": "5378acec3d08ecd1dcf5cb006d3a6f7f1e5fbcb163541d52bff77f361b70c7e5",
    "consumption": "391c1d0136d7db3fd0fccb68691f0795a2513a6772652ebe8c64c541bfb0fe11",
    "investment": "ecf7711e5f07a8fbed5f26b9cf11ae57fd9de2fd67a23bc7ea5a41dd1ada84ee",
    "employment": "c417507d1cb36510ad57caf3a488fb6f9f9ad481b37f63a26727e5b6d99fe32a",
    "earnings": "27edbacd38a2df00f5e7a1a423504c72bea8dae607be3fb3945bcf8fc941e5f5",
    "defaults": "f084d9ca496fa8e73202560e1db25efb5149054e9c7af79e7e60e4f76c3855fa",
    "gdp": "cb33ae45349abb334f03aed3e1b324228d3f00f9fdbed94fdf5591aea4de3e3c",
    "stocks": "5a0170a01e8a452859c0510985a8a2647014ec984e959ce1ae2ba43593d3857d",
    "housing": "a6f7c7ee857f72bef1231a22b2627ab01d508ba149295b703debec91078b48a3",
    "household_debt": "67f1dfc9b68e51c6d6a24db31effb72b136e7ce09cdd17f51285c58c4682be3d",
    "oil": "01f554d6c78aa39801e3e65c87eb24a5ce2a5978eea0ca906f4c11105a3673d7",
    "commodity": "4f5286153f6cc2d6839ec6a2d7503fad4a3d7cacf257f04974647292c9395c38",
    "fiscal": "35ceac6a445e57e02980c094a553e56dc277bb8d8ae09dbb1f31a61a6503b8c4",
    "geopolitics": "2df2a812f10bd644553431c810da1194ee29da86dce68e7dc31722183df4ba0c",
    "tech": "99c917d967198f304e679797333a17cf27ce8bdd2ee8b1b1f7ac6e3c43419ac0",
    "risk_sentiment": "273e257a1702aa8f5306f6644c1ebd549db7fa2a548c0af97e5fcf604cc4fff0",
    "consumer_conf": "ff56d967ff5bd1672ec745014d570d7bee0e1534aed043473c0fb750c4d0855d",
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
