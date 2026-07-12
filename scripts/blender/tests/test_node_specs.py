from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


BLENDER_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BLENDER_DIR.parents[1]
MODULE_PATH = BLENDER_DIR / "node-specs.py"
NODES_PATH = PROJECT_ROOT / "data" / "nodes.js"


def load_node_specs():
    spec = importlib.util.spec_from_file_location("econ_node_specs", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NodeSpecsContractTests(unittest.TestCase):
    def test_current_nodes_source_matches_all_thirty_motion_signatures(self):
        module = load_node_specs()

        self.assertEqual(30, len(module.CANONICAL_IDS))
        self.assertEqual(set(module.CANONICAL_IDS), set(module.NODE_MOTIONS))
        self.assertEqual(
            ("policy_rate", "fx", "oil", "housing", "gdp", "risk_sentiment"),
            module.PROOF_IDS,
        )
        self.assertEqual(
            (
                "market_rate",
                "liquidity",
                "credit_spread",
                "bank_lending",
                "cpi",
                "inflation_exp",
            ),
            getattr(module, "MONEY_PRICE_IDS", None),
        )
        self.assertEqual(
            (
                "wages",
                "exports",
                "current_account",
                "capital_flows",
                "fed_rate",
                "global_growth",
            ),
            getattr(module, "WAGE_EXTERNAL_IDS", None),
        )
        self.assertEqual(
            (
                "consumption",
                "investment",
                "employment",
                "earnings",
                "defaults",
                "stocks",
            ),
            getattr(module, "REAL_EQUITY_IDS", None),
        )
        self.assertEqual(
            (
                "household_debt",
                "commodity",
                "fiscal",
                "geopolitics",
                "tech",
                "consumer_conf",
            ),
            getattr(module, "ASSET_POLICY_IDS", None),
        )
        authored_ids = (
            set(module.PROOF_IDS)
            | set(module.MONEY_PRICE_IDS)
            | set(module.WAGE_EXTERNAL_IDS)
            | set(module.REAL_EQUITY_IDS)
            | set(module.ASSET_POLICY_IDS)
        )
        self.assertEqual(set(module.CANONICAL_IDS), authored_ids)
        self.assertEqual(authored_ids, set(getattr(module, "ACCENT_CONTRACTS", ())))
        self.assertEqual(
            authored_ids,
            set(getattr(module, "BEVEL_TAGGED_EDGE_MINIMUMS", ())),
        )
        self.assertEqual(
            set(module.MATERIAL_NAMES),
            set(getattr(module, "MATERIAL_CONTRACT_HASHES", ())),
        )
        self.assertEqual(
            set(module.CANONICAL_IDS),
            set(getattr(module, "ROOT_CONTRACT_HASHES", ())),
        )
        for digest in (
            *module.MATERIAL_CONTRACT_HASHES.values(),
            *module.ROOT_CONTRACT_HASHES.values(),
        ):
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
        self.assertEqual(("rotate", "z", 0.20), module.NODE_MOTIONS["policy_rate"])
        self.assertEqual(("scale", "xyz", 0.07), module.NODE_MOTIONS["gdp"])
        self.assertEqual(("translate", "y", 0.12), module.NODE_MOTIONS["housing"])
        self.assertEqual(("translate", "x", 0.12), module.NODE_MOTIONS["market_rate"])
        self.assertEqual(("rotate", "y", 0.35), module.NODE_MOTIONS["liquidity"])
        self.assertEqual(("translate", "x", 0.10), module.NODE_MOTIONS["credit_spread"])
        self.assertEqual(("translate", "z", 0.12), module.NODE_MOTIONS["bank_lending"])
        self.assertEqual(("rotate", "z", 0.22), module.NODE_MOTIONS["cpi"])
        self.assertEqual(("translate", "z", 0.12), module.NODE_MOTIONS["inflation_exp"])
        self.assertEqual(
            {
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
            },
            getattr(module, "ACCENT_THIN_AXIS_CONTRACTS", None),
        )

    def test_contract_rejects_canonical_id_drift(self):
        module = load_node_specs()
        source = NODES_PATH.read_text(encoding="utf-8")
        changed = source.replace("id: 'consumer_conf'", "id: 'consumer_conf_changed'", 1)

        with self.assertRaisesRegex(module.NodeSpecError, "motion IDs do not match canonical IDs"):
            module.validate_nodes_source(changed)

    def test_contract_rejects_unknown_category(self):
        module = load_node_specs()
        source = NODES_PATH.read_text(encoding="utf-8")
        changed = source.replace("cat: 'monetary'", "cat: 'not_a_category'", 1)

        with self.assertRaisesRegex(module.NodeSpecError, "unknown category"):
            module.validate_nodes_source(changed)

    def test_runtime_contract_rejects_any_version_other_than_5_1_2(self):
        module = load_node_specs()

        module.require_blender_version((5, 1, 2))
        with self.assertRaisesRegex(module.NodeSpecError, "requires Blender 5.1.2"):
            module.require_blender_version((5, 1, 3))


if __name__ == "__main__":
    unittest.main()
