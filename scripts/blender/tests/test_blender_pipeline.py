from __future__ import annotations

import json
import os
from pathlib import Path
import struct
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


def glb_json(path: Path) -> dict:
    raw = path.read_bytes()
    chunk_length, chunk_type = struct.unpack_from("<II", raw, 12)
    if chunk_type != 0x4E4F534A:
        raise AssertionError("First GLB chunk is not JSON")
    return json.loads(raw[20 : 20 + chunk_length].rstrip(b" \t\r\n\x00").decode("utf-8"))


def mutate_glb(source: Path, destination: Path, mutate) -> None:
    raw = source.read_bytes()
    magic, version, _declared_length = struct.unpack_from("<4sII", raw, 0)
    json_length, json_type = struct.unpack_from("<II", raw, 12)
    document = json.loads(
        raw[20 : 20 + json_length].rstrip(b" \t\r\n\x00").decode("utf-8")
    )
    mutate(document)
    payload = json.dumps(document, separators=(",", ":")).encode("utf-8")
    payload += b" " * ((-len(payload)) % 4)
    remaining_chunks = raw[20 + json_length :]
    rebuilt = (
        struct.pack("<4sII", magic, version, 20 + len(payload) + len(remaining_chunks))
        + struct.pack("<II", len(payload), json_type)
        + payload
        + remaining_chunks
    )
    destination.write_bytes(rebuilt)


def glb_chunks(path: Path) -> tuple[bytes, int, list[tuple[int, bytes]]]:
    raw = path.read_bytes()
    magic, version, declared_length = struct.unpack_from("<4sII", raw, 0)
    if declared_length != len(raw):
        raise AssertionError("GLB declared length mismatch")
    chunks: list[tuple[int, bytes]] = []
    offset = 12
    while offset < len(raw):
        chunk_length, chunk_type = struct.unpack_from("<II", raw, offset)
        start = offset + 8
        end = start + chunk_length
        chunks.append((chunk_type, raw[start:end]))
        offset = end
    return magic, version, chunks


def write_glb_chunks(
    path: Path,
    magic: bytes,
    version: int,
    chunks: list[tuple[int, bytes]],
) -> None:
    body = b"".join(
        struct.pack("<II", len(payload), chunk_type) + payload
        for chunk_type, payload in chunks
    )
    path.write_bytes(struct.pack("<4sII", magic, version, 12 + len(body)) + body)


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

    def test_validator_rejects_nonidentity_quaternion_root_rotation(self):
        with tempfile.TemporaryDirectory(prefix="econ-blender-quaternion-") as temp_dir:
            ready_blend = Path(temp_dir) / "ready.blend"
            scaffold = run_blender(
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "scaffold-econ-node-library.py"),
                "--",
                "--output",
                str(ready_blend),
            )
            self.assertEqual(0, scaffold.returncode, scaffold.stdout)
            expression = (
                "import bpy;"
                "root=bpy.data.objects['policy_rate'];"
                "root.rotation_mode='QUATERNION';"
                "root.rotation_quaternion=(0.0,0.0,1.0,0.0);"
                f"bpy.ops.wm.save_as_mainfile(filepath={str(ready_blend)!r},check_existing=False)"
            )
            mutation = run_blender(str(ready_blend), "--python-exit-code", "1", "--python-expr", expression)
            self.assertEqual(0, mutation.returncode, mutation.stdout)

            validation = run_blender(
                str(ready_blend),
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "validate-econ-node-library.py"),
                "--",
                "--scope",
                "ready",
            )
            self.assertNotEqual(0, validation.returncode, validation.stdout)
            self.assertIn("root transform is not identity", "\n".join(summary_from(validation.stdout)["errors"]))

    def test_wip_and_qa_objects_validate_but_never_export(self):
        with tempfile.TemporaryDirectory(prefix="econ-blender-zones-") as temp_dir:
            temp = Path(temp_dir)
            ready_blend = temp / "ready-with-qa.blend"
            output_glb = temp / "ready-with-qa.glb"
            scaffold = run_blender(
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "scaffold-econ-node-library.py"),
                "--",
                "--output",
                str(ready_blend),
            )
            self.assertEqual(0, scaffold.returncode, scaffold.stdout)
            script = "\n".join(
                (
                    "import bpy",
                    "wip=bpy.data.collections['10_WIP']",
                    "qa=bpy.data.collections['90_QA']",
                    "mesh=bpy.data.meshes.new('WIP__CUTTER_MESH')",
                    "mesh.from_pydata([(-1,-1,0),(1,-1,0),(0,1,0)],[],[(0,1,2)])",
                    "cutter=bpy.data.objects.new('WIP__CUTTER',mesh)",
                    "wip.objects.link(cutter)",
                    "reference=bpy.data.objects.new('WIP__REFERENCE',None)",
                    "wip.objects.link(reference)",
                    "camera_data=bpy.data.cameras.new('QA__CAMERA_DATA')",
                    "camera=bpy.data.objects.new('QA__CAMERA',camera_data)",
                    "qa.objects.link(camera)",
                    "light_data=bpy.data.lights.new('QA__LIGHT_DATA','AREA')",
                    "light=bpy.data.objects.new('QA__LIGHT',light_data)",
                    "qa.objects.link(light)",
                    f"bpy.ops.wm.save_as_mainfile(filepath={str(ready_blend)!r},check_existing=False)",
                )
            )
            mutation = run_blender(
                str(ready_blend),
                "--python-exit-code",
                "1",
                "--python-expr",
                f"exec({script!r})",
            )
            self.assertEqual(0, mutation.returncode, mutation.stdout)

            validation = run_blender(
                str(ready_blend),
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "validate-econ-node-library.py"),
                "--",
                "--scope",
                "ready",
            )
            self.assertEqual(0, validation.returncode, validation.stdout)
            export = run_blender(
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
            self.assertEqual(0, export.returncode, export.stdout)
            exported_names = {node.get("name") for node in glb_json(output_glb).get("nodes", [])}
            self.assertFalse({"WIP__CUTTER", "WIP__REFERENCE", "QA__CAMERA", "QA__LIGHT"} & exported_names)

    def test_glb_validator_rejects_hierarchy_extras_names_material_and_topology_drift(self):
        with tempfile.TemporaryDirectory(prefix="econ-blender-glb-drift-") as temp_dir:
            temp = Path(temp_dir)
            ready_blend = temp / "ready.blend"
            valid_glb = temp / "valid.glb"
            invalid_glb = temp / "invalid.glb"
            scaffold = run_blender(
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "scaffold-econ-node-library.py"),
                "--",
                "--output",
                str(ready_blend),
            )
            self.assertEqual(0, scaffold.returncode, scaffold.stdout)
            export = run_blender(
                str(ready_blend),
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "export-econ-node-library.py"),
                "--",
                "--scope",
                "ready",
                "--output",
                str(valid_glb),
            )
            self.assertEqual(0, export.returncode, export.stdout)

            def drift(document: dict) -> None:
                nodes = document["nodes"]
                root_index = next(index for index, node in enumerate(nodes) if node.get("name") == "policy_rate")
                root = nodes[root_index]
                root["extras"].pop("econ_schema_version", None)
                root["extras"]["econ_axis"] = "x"
                body_index = next(index for index, node in enumerate(nodes) if node.get("name") == "policy_rate__body")
                body = nodes[body_index]
                body["name"] = "policy_rate__body_wrong"
                primitive = document["meshes"][body["mesh"]]["primitives"][0]
                document["materials"][primitive["material"]]["name"] = "MAT__WRONG"
                primitive["mode"] = 1
                index_accessor = document["accessors"][primitive["indices"]]
                index_accessor["count"] += 1
                index_accessor["byteOffset"] = (
                    document["bufferViews"][index_accessor["bufferView"]]["byteLength"] + 4
                )
                document["bufferViews"][0]["byteOffset"] = (
                    document["buffers"][0]["byteLength"] + 4
                )
                root.setdefault("children", []).extend([root_index, len(nodes) + 99])
                wrapper_index = len(nodes)
                nodes.append({"name": "WRAPPER", "children": [root_index]})
                active_scene = document.get("scene", 0)
                document["scenes"][active_scene]["nodes"] = [wrapper_index]

            mutate_glb(valid_glb, invalid_glb, drift)
            validation = run_blender(
                str(ready_blend),
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "validate-econ-node-library.py"),
                "--",
                "--scope",
                "ready",
                "--glb",
                str(invalid_glb),
            )
            self.assertNotEqual(0, validation.returncode, validation.stdout)
            errors = "\n".join(summary_from(validation.stdout)["errors"])
            for expected in (
                "active scene root mismatch",
                "econ_schema_version expected",
                "mesh node names",
                "material expected",
                "primitive mode",
                "index accessor count",
                "bufferView 0 range",
                "range requires",
                "cyclic node graph",
                "invalid child index",
            ):
                self.assertIn(expected, errors)

    def test_glb_validator_rejects_missing_or_truncated_binary_payload(self):
        with tempfile.TemporaryDirectory(prefix="econ-blender-glb-bin-") as temp_dir:
            temp = Path(temp_dir)
            ready_blend = temp / "ready.blend"
            valid_glb = temp / "valid.glb"
            missing_bin_glb = temp / "missing-bin.glb"
            truncated_bin_glb = temp / "truncated-bin.glb"
            scaffold = run_blender(
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "scaffold-econ-node-library.py"),
                "--",
                "--output",
                str(ready_blend),
            )
            self.assertEqual(0, scaffold.returncode, scaffold.stdout)
            export = run_blender(
                str(ready_blend),
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "export-econ-node-library.py"),
                "--",
                "--scope",
                "ready",
                "--output",
                str(valid_glb),
            )
            self.assertEqual(0, export.returncode, export.stdout)

            magic, version, chunks = glb_chunks(valid_glb)
            json_chunks = [chunk for chunk in chunks if chunk[0] == 0x4E4F534A]
            bin_chunks = [chunk for chunk in chunks if chunk[0] == 0x004E4942]
            self.assertEqual(1, len(json_chunks))
            self.assertEqual(1, len(bin_chunks))
            write_glb_chunks(missing_bin_glb, magic, version, json_chunks)
            truncated_payload = bin_chunks[0][1][:-64]
            self.assertEqual(0, len(truncated_payload) % 4)
            write_glb_chunks(
                truncated_bin_glb,
                magic,
                version,
                [json_chunks[0], (0x004E4942, truncated_payload)],
            )

            cases = (
                (missing_bin_glb, "exactly one BIN chunk"),
                (truncated_bin_glb, "buffer byteLength"),
            )
            for invalid_glb, expected_error in cases:
                with self.subTest(invalid_glb=invalid_glb.name):
                    validation = run_blender(
                        str(ready_blend),
                        "--python-exit-code",
                        "1",
                        "--python",
                        str(BLENDER_DIR / "validate-econ-node-library.py"),
                        "--",
                        "--scope",
                        "ready",
                        "--glb",
                        str(invalid_glb),
                    )
                    self.assertNotEqual(0, validation.returncode, validation.stdout)
                    self.assertIn(
                        expected_error,
                        "\n".join(summary_from(validation.stdout)["errors"]),
                    )

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
