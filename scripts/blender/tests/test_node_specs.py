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
        self.assertEqual(("rotate", "z", 0.20), module.NODE_MOTIONS["policy_rate"])
        self.assertEqual(("scale", "xyz", 0.07), module.NODE_MOTIONS["gdp"])
        self.assertEqual(("translate", "y", 0.12), module.NODE_MOTIONS["housing"])

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


if __name__ == "__main__":
    unittest.main()
