from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BLENDER_DIR = PROJECT_ROOT / "scripts" / "blender"
DEFAULT_BLENDER = (
    Path.home()
    / "AppData"
    / "Local"
    / "Programs"
    / "Blender"
    / "5.1.2-portable"
    / "blender-5.1.2-windows-x64"
    / "blender.exe"
)
BLENDER = Path(os.environ.get("BLENDER_EXE", DEFAULT_BLENDER))


def run_blender(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(BLENDER), "--background", "--factory-startup", "--disable-autoexec", *args],
        cwd=PROJECT_ROOT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def summary_from(output: str) -> dict:
    for line in reversed(output.splitlines()):
        line = line.strip()
        if line.startswith("{") and '"errors"' in line:
            return json.loads(line)
    raise AssertionError(f"No JSON validation summary in Blender output:\n{output}")


class BlenderPipelineContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not BLENDER.is_file():
            raise RuntimeError(f"Blender 5.1.2 executable not found: {BLENDER}")

    def test_validator_rejects_factory_scene_with_structured_contract_error(self):
        result = run_blender(
            "--python-exit-code",
            "1",
            "--python",
            str(BLENDER_DIR / "validate-econ-node-library.py"),
            "--",
            "--scope",
            "ready",
        )

        self.assertNotEqual(0, result.returncode, result.stdout)
        summary = summary_from(result.stdout)
        self.assertTrue(summary["errors"])
        self.assertIn("canonical root mismatch", "\n".join(summary["errors"]))
        self.assertEqual(0, summary["readyCount"])

    def test_scaffold_red_then_ready_green_and_atomic_export(self):
        with tempfile.TemporaryDirectory(prefix="econ-blender-test-") as temp_dir:
            temp = Path(temp_dir)
            red_blend = temp / "red.blend"
            ready_blend = temp / "ready.blend"
            output_glb = temp / "library.glb"

            red_scaffold = run_blender(
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "scaffold-econ-node-library.py"),
                "--",
                "--output",
                str(red_blend),
                "--scaffold-only",
            )
            self.assertEqual(0, red_scaffold.returncode, red_scaffold.stdout)

            red_validation = run_blender(
                str(red_blend),
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "validate-econ-node-library.py"),
                "--",
                "--scope",
                "ready",
            )
            self.assertNotEqual(0, red_validation.returncode, red_validation.stdout)
            self.assertIn("no ready roots", "\n".join(summary_from(red_validation.stdout)["errors"]))

            sentinel = b"existing-output-must-survive"
            output_glb.write_bytes(sentinel)
            failed_export = run_blender(
                str(red_blend),
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "export-econ-node-library.py"),
                "--",
                "--scope",
                "ready",
                "--output",
                str(output_glb),
            )
            self.assertNotEqual(0, failed_export.returncode, failed_export.stdout)
            self.assertEqual(sentinel, output_glb.read_bytes())

            ready_scaffold = run_blender(
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "scaffold-econ-node-library.py"),
                "--",
                "--output",
                str(ready_blend),
            )
            self.assertEqual(0, ready_scaffold.returncode, ready_scaffold.stdout)

            preserved_scaffold = run_blender(
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "scaffold-econ-node-library.py"),
                "--",
                "--output",
                str(ready_blend),
            )
            self.assertEqual(0, preserved_scaffold.returncode, preserved_scaffold.stdout)
            self.assertIn('"policyRate":"preserved"', preserved_scaffold.stdout)

            green_validation = run_blender(
                str(ready_blend),
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "validate-econ-node-library.py"),
                "--",
                "--scope",
                "ready",
            )
            self.assertEqual(0, green_validation.returncode, green_validation.stdout)
            green = summary_from(green_validation.stdout)
            self.assertEqual([], green["errors"])
            self.assertEqual(1, green["readyCount"])
            self.assertEqual(2, green["primitives"])
            self.assertGreaterEqual(green["models"]["policy_rate"]["bodyTriangles"], 1800)
            self.assertLessEqual(green["models"]["policy_rate"]["bodyTriangles"], 2200)

            green_export = run_blender(
                str(ready_blend),
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "export-econ-node-library.py"),
                "--",
                "--scope",
                "ready",
                "--output",
                str(output_glb),
            )
            self.assertEqual(0, green_export.returncode, green_export.stdout)
            exported = summary_from(green_export.stdout)
            self.assertEqual([], exported["errors"])
            self.assertEqual(2, exported["primitives"])
            self.assertLess(exported["bytes"], 200_000)
            self.assertEqual(b"glTF", output_glb.read_bytes()[:4])


if __name__ == "__main__":
    unittest.main()
