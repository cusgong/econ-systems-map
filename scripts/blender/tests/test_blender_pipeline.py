from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import shutil
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
            return json.JSONDecoder().raw_decode(line)[0]
    raise AssertionError(f"No JSON validation summary in Blender output:\n{output}")


def author_proof_library(output: Path) -> None:
    scaffold = run_blender(
        "--python-exit-code",
        "1",
        "--python",
        str(BLENDER_DIR / "scaffold-econ-node-library.py"),
        "--",
        "--output",
        str(output),
    )
    if scaffold.returncode != 0:
        raise AssertionError(scaffold.stdout)
    proof = run_blender(
        str(output),
        "--python-exit-code",
        "1",
        "--python",
        str(BLENDER_DIR / "author-proof-models.py"),
        "--",
        "--output",
        str(output),
    )
    if proof.returncode != 0:
        raise AssertionError(proof.stdout)


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
            self.assertGreaterEqual(green["models"]["policy_rate"]["bodyTriangles"], 2200)
            self.assertLessEqual(green["models"]["policy_rate"]["bodyTriangles"], 2400)

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

    def test_proof_scope_exports_exact_six_models_deterministically(self):
        proof_ids = {
            "policy_rate",
            "fx",
            "oil",
            "housing",
            "gdp",
            "risk_sentiment",
        }
        triangle_bands = {
            "policy_rate": (2_860, 2_990),
            "fx": (2_540, 2_940),
            "oil": (2_348, 2_748),
            "housing": (1_416, 1_816),
            "gdp": (1_560, 1_920),
            "risk_sentiment": (1_736, 2_136),
        }
        library_blend = BLENDER_DIR / "econ-node-library.blend"
        author_source = BLENDER_DIR / "author-proof-models.py"

        validation = run_blender(
            str(library_blend),
            "--python-exit-code",
            "1",
            "--python",
            str(BLENDER_DIR / "validate-econ-node-library.py"),
            "--",
            "--scope",
            "proof",
        )
        self.assertEqual(0, validation.returncode, validation.stdout)
        self.assertTrue(author_source.is_file(), f"missing reproducible proof authoring source: {author_source}")
        summary = summary_from(validation.stdout)
        self.assertEqual([], summary["errors"])
        self.assertEqual(6, summary["readyCount"])
        self.assertEqual(0, summary["fallbackCount"])
        self.assertEqual(12, summary["primitives"])
        self.assertEqual(proof_ids, set(summary["models"]))
        self.assertGreaterEqual(summary["triangles"], 10_600)
        self.assertLessEqual(summary["triangles"], 14_200)
        self.assertLessEqual(summary["triangles"], 18_000)

        silhouette_signatures = []
        for node_id, (minimum, maximum) in triangle_bands.items():
            model = summary["models"][node_id]
            self.assertGreaterEqual(model["triangles"], minimum, node_id)
            self.assertLessEqual(model["triangles"], maximum, node_id)
            self.assertEqual(2, model["primitives"], node_id)
            self.assertGreaterEqual(model["accentAreaRatio"], 0.10, node_id)
            self.assertLessEqual(model["accentAreaRatio"], 0.20, node_id)
            if node_id == "gdp":
                self.assertLessEqual(
                    model["accentAreaRatio"],
                    0.165,
                    "GDP counterweight must remain a restrained load indicator",
                )
            self.assertGreaterEqual(model["radius"], 0.98, node_id)
            self.assertLessEqual(model["radius"], 1.02, node_id)
            self.assertLessEqual(model["centerError"], 0.05, node_id)
            self.assertEqual(
                {"front", "side", "top"},
                set(model["occupancyMaskSha256"]),
                node_id,
            )
            for view, digest in model["occupancyMaskSha256"].items():
                self.assertEqual(64, len(digest), f"{node_id}/{view}")
                self.assertGreater(model["occupancyPixels"][view], 0, f"{node_id}/{view}")
            self.assertEqual({"body", "accent"}, set(model["bevels"]), node_id)
            for role, bevel in model["bevels"].items():
                self.assertEqual(3, bevel["segments"], f"{node_id}/{role}")
                self.assertGreaterEqual(bevel["width"], 0.03, f"{node_id}/{role}")
                self.assertLessEqual(bevel["width"], 0.05, f"{node_id}/{role}")
                self.assertGreater(bevel["evaluatedTriangleDelta"], 0, f"{node_id}/{role}")
                self.assertEqual("WEIGHT", bevel["limitMethod"], f"{node_id}/{role}")
                self.assertGreaterEqual(
                    bevel["taggedEdges"],
                    bevel["minimumTaggedEdges"],
                    f"{node_id}/{role}",
                )
            accent_contract = model["accentContract"]
            self.assertTrue(accent_contract["pivotLabel"], node_id)
            self.assertEqual(3, len(accent_contract["blenderTranslation"]), node_id)
            self.assertEqual(3, len(accent_contract["gltfTranslation"]), node_id)
            blender_translation = accent_contract["blenderTranslation"]
            self.assertEqual(
                [
                    blender_translation[0],
                    blender_translation[2],
                    -blender_translation[1],
                ],
                accent_contract["gltfTranslation"],
                node_id,
            )
            signature = model.get("silhouetteSignature")
            self.assertIsInstance(signature, str, node_id)
            self.assertEqual(3, len(signature.split(";")), node_id)
            silhouette_signatures.append(signature)
        self.assertEqual(6, len(set(silhouette_signatures)))
        oil_extents = summary["models"]["oil"]["accentExtents"]
        self.assertLess(
            oil_extents[1],
            0.45 * min(oil_extents[0], oil_extents[2]),
            "oil valve must be an XZ-plane side wheel with Blender-Y normal",
        )

        with tempfile.TemporaryDirectory(prefix="econ-blender-proof-export-") as temp_dir:
            first_glb = Path(temp_dir) / "proof-a.glb"
            second_glb = Path(temp_dir) / "proof-b.glb"
            exports = []
            for output in (first_glb, second_glb):
                result = run_blender(
                    str(library_blend),
                    "--python-exit-code",
                    "1",
                    "--python",
                    str(BLENDER_DIR / "export-econ-node-library.py"),
                    "--",
                    "--scope",
                    "proof",
                    "--output",
                    str(output),
                )
                self.assertEqual(0, result.returncode, result.stdout)
                exported = summary_from(result.stdout)
                self.assertEqual([], exported["errors"])
                self.assertEqual(12, exported["primitives"])
                self.assertLessEqual(exported["bytes"], 600_000)
                exports.append(hashlib.sha256(output.read_bytes()).hexdigest())
                document = glb_json(output)
                active_scene = document.get("scene", 0)
                root_names = {
                    document["nodes"][index].get("name")
                    for index in document["scenes"][active_scene].get("nodes", [])
                }
                self.assertEqual(proof_ids, root_names)
            self.assertEqual(exports[0], exports[1], "proof GLB export must be byte-deterministic")
            self.assertEqual(
                "2232a593b5c194a6d4d61dd1778e72d561f0b8ec27872e1fdb5753e11c83db26",
                exports[0],
                "proof geometry/export hash changed while expanding the ready library",
            )

    def test_proof_authoring_is_idempotent_at_the_export_boundary(self):
        source_blend = BLENDER_DIR / "econ-node-library.blend"
        author_script = BLENDER_DIR / "author-proof-models.py"
        with tempfile.TemporaryDirectory(prefix="econ-proof-author-idempotent-") as temp_dir:
            temp = Path(temp_dir)
            authored_blend = temp / "proof.blend"
            shutil.copy2(source_blend, authored_blend)
            hashes = []
            for iteration in range(2):
                author = run_blender(
                    str(authored_blend),
                    "--python-exit-code",
                    "1",
                    "--python",
                    str(author_script),
                    "--",
                    "--output",
                    str(authored_blend),
                )
                self.assertEqual(0, author.returncode, author.stdout)
                self.assertIn('"readyCount":30', author.stdout)

                output_glb = temp / f"proof-{iteration}.glb"
                export = run_blender(
                    str(authored_blend),
                    "--python-exit-code",
                    "1",
                    "--python",
                    str(BLENDER_DIR / "export-econ-node-library.py"),
                    "--",
                    "--scope",
                    "proof",
                    "--output",
                    str(output_glb),
                )
                self.assertEqual(0, export.returncode, export.stdout)
                self.assertEqual([], summary_from(export.stdout)["errors"])
                hashes.append(hashlib.sha256(output_glb.read_bytes()).hexdigest())
            self.assertEqual(hashes[0], hashes[1], "reauthoring changed proof GLB bytes")

    def test_money_price_authoring_produces_exact_twelve_ready_models(self):
        money_price_ids = {
            "market_rate",
            "liquidity",
            "credit_spread",
            "bank_lending",
            "cpi",
            "inflation_exp",
        }
        expected_ready_ids = {
            "policy_rate",
            "fx",
            "oil",
            "housing",
            "gdp",
            "risk_sentiment",
            *money_price_ids,
        }
        triangle_bands = {
            "market_rate": (1_932, 2_332),
            "liquidity": (2_084, 2_484),
            "credit_spread": (1_584, 1_984),
            "bank_lending": (2_376, 2_776),
            "cpi": (2_456, 2_856),
            "inflation_exp": (1_624, 2_024),
        }
        author_script = BLENDER_DIR / "author-money-price-models.py"
        geometry_source = BLENDER_DIR / "money_price_models.py"
        batch_source = BLENDER_DIR / "model_authoring.py"
        self.assertTrue(author_script.is_file(), f"missing Task 7 author source: {author_script}")
        self.assertTrue(geometry_source.is_file(), f"missing Task 7 geometry source: {geometry_source}")
        self.assertTrue(batch_source.is_file(), f"missing reusable batch author source: {batch_source}")

        with tempfile.TemporaryDirectory(prefix="econ-money-price-author-") as temp_dir:
            authored_blend = Path(temp_dir) / "money-price.blend"
            author_proof_library(authored_blend)
            author = run_blender(
                str(authored_blend),
                "--python-exit-code",
                "1",
                "--python",
                str(author_script),
                "--",
                "--output",
                str(authored_blend),
            )
            self.assertEqual(0, author.returncode, author.stdout)
            self.assertIn('"readyCount":12', author.stdout)

            validation = run_blender(
                str(authored_blend),
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "validate-econ-node-library.py"),
                "--",
                "--scope",
                "ready",
            )
            self.assertEqual(0, validation.returncode, validation.stdout)
            summary = summary_from(validation.stdout)
            self.assertEqual([], summary["errors"])
            self.assertEqual(12, summary["readyCount"])
            self.assertEqual(18, summary["fallbackCount"])
            self.assertEqual(24, summary["primitives"])
            self.assertEqual(expected_ready_ids, set(summary["models"]))
            self.assertGreaterEqual(summary["triangles"], 24_500)
            self.assertLessEqual(summary["triangles"], 27_200)
            for node_id, (minimum, maximum) in triangle_bands.items():
                model = summary["models"][node_id]
                self.assertGreaterEqual(model["triangles"], minimum, node_id)
                self.assertLessEqual(model["triangles"], maximum, node_id)
                self.assertGreaterEqual(model["accentAreaRatio"], 0.10, node_id)
                self.assertLessEqual(model["accentAreaRatio"], 0.20, node_id)
                self.assertGreaterEqual(model["radius"], 0.98, node_id)
                self.assertLessEqual(model["radius"], 1.02, node_id)
                self.assertLessEqual(model["centerError"], 0.05, node_id)
                for role in ("body", "accent"):
                    bevel = model["bevels"][role]
                    self.assertGreaterEqual(
                        bevel["taggedEdges"],
                        bevel["minimumTaggedEdges"],
                        f"{node_id}/{role}",
                    )

    def test_money_price_authoring_is_idempotent_and_preserves_proof_export(self):
        author_script = BLENDER_DIR / "author-money-price-models.py"
        self.assertTrue(author_script.is_file(), f"missing Task 7 author source: {author_script}")
        with tempfile.TemporaryDirectory(prefix="econ-money-price-idempotent-") as temp_dir:
            temp = Path(temp_dir)
            authored_blend = temp / "money-price.blend"
            author_proof_library(authored_blend)

            proof_before = temp / "proof-before.glb"
            before_export = run_blender(
                str(authored_blend),
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "export-econ-node-library.py"),
                "--",
                "--scope",
                "proof",
                "--output",
                str(proof_before),
            )
            self.assertEqual(0, before_export.returncode, before_export.stdout)
            proof_hash = hashlib.sha256(proof_before.read_bytes()).hexdigest()

            ready_hashes = []
            for iteration in range(2):
                author = run_blender(
                    str(authored_blend),
                    "--python-exit-code",
                    "1",
                    "--python",
                    str(author_script),
                    "--",
                    "--output",
                    str(authored_blend),
                )
                self.assertEqual(0, author.returncode, author.stdout)
                self.assertIn('"readyCount":12', author.stdout)
                ready_glb = temp / f"ready-{iteration}.glb"
                ready_export = run_blender(
                    str(authored_blend),
                    "--python-exit-code",
                    "1",
                    "--python",
                    str(BLENDER_DIR / "export-econ-node-library.py"),
                    "--",
                    "--scope",
                    "ready",
                    "--output",
                    str(ready_glb),
                )
                self.assertEqual(0, ready_export.returncode, ready_export.stdout)
                ready_hashes.append(hashlib.sha256(ready_glb.read_bytes()).hexdigest())

            proof_after = temp / "proof-after.glb"
            after_export = run_blender(
                str(authored_blend),
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "export-econ-node-library.py"),
                "--",
                "--scope",
                "proof",
                "--output",
                str(proof_after),
            )
            self.assertEqual(0, after_export.returncode, after_export.stdout)
            self.assertEqual(proof_hash, hashlib.sha256(proof_after.read_bytes()).hexdigest())
            self.assertEqual(ready_hashes[0], ready_hashes[1])

    def test_all_authoring_batches_produce_exact_thirty_ready_models(self):
        batch_scripts = (
            ("author-money-price-models.py", 12),
            ("author-wage-external-models.py", 18),
            ("author-real-equity-models.py", 24),
            ("author-asset-policy-models.py", 30),
        )
        for filename, _ready_count in batch_scripts:
            self.assertTrue((BLENDER_DIR / filename).is_file(), filename)

        with tempfile.TemporaryDirectory(prefix="econ-full-author-") as temp_dir:
            temp = Path(temp_dir)
            authored_blend = temp / "full-library.blend"
            author_proof_library(authored_blend)
            for filename, ready_count in batch_scripts:
                author = run_blender(
                    str(authored_blend),
                    "--python-exit-code",
                    "1",
                    "--python",
                    str(BLENDER_DIR / filename),
                    "--",
                    "--output",
                    str(authored_blend),
                )
                self.assertEqual(0, author.returncode, author.stdout)
                self.assertIn(f'"readyCount":{ready_count}', author.stdout)

            validation = run_blender(
                str(authored_blend),
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "validate-econ-node-library.py"),
                "--",
                "--scope",
                "ready",
            )
            self.assertEqual(0, validation.returncode, validation.stdout)
            summary = summary_from(validation.stdout)
            self.assertEqual([], summary["errors"])
            self.assertEqual(30, summary["readyCount"])
            self.assertEqual(0, summary["fallbackCount"])
            self.assertEqual(60, summary["primitives"])
            self.assertEqual(30, len(summary["models"]))
            self.assertGreaterEqual(summary["triangles"], 50_000)
            self.assertLessEqual(summary["triangles"], 70_000)
            for node_id, model in summary["models"].items():
                self.assertGreaterEqual(model["accentAreaRatio"], 0.10, node_id)
                self.assertLessEqual(model["accentAreaRatio"], 0.20, node_id)
                self.assertGreaterEqual(model["radius"], 0.98, node_id)
                self.assertLessEqual(model["radius"], 1.02, node_id)
                self.assertLessEqual(model["centerError"], 0.05, node_id)

    def test_ready_scope_exports_committed_thirty_models_deterministically(self):
        expected_ids = {
            "policy_rate",
            "market_rate",
            "liquidity",
            "credit_spread",
            "bank_lending",
            "cpi",
            "inflation_exp",
            "fx",
            "oil",
            "housing",
            "gdp",
            "risk_sentiment",
            "wages",
            "exports",
            "current_account",
            "capital_flows",
            "fed_rate",
            "global_growth",
            "consumption",
            "investment",
            "employment",
            "earnings",
            "defaults",
            "stocks",
            "household_debt",
            "commodity",
            "fiscal",
            "geopolitics",
            "tech",
            "consumer_conf",
        }
        library_blend = BLENDER_DIR / "econ-node-library.blend"
        validation = run_blender(
            str(library_blend),
            "--python-exit-code",
            "1",
            "--python",
            str(BLENDER_DIR / "validate-econ-node-library.py"),
            "--",
            "--scope",
            "ready",
        )
        self.assertEqual(0, validation.returncode, validation.stdout)
        summary = summary_from(validation.stdout)
        self.assertEqual(30, summary["readyCount"])
        self.assertEqual(0, summary["fallbackCount"])
        self.assertEqual(expected_ids, set(summary["models"]))

        with tempfile.TemporaryDirectory(prefix="econ-ready-thirty-export-") as temp_dir:
            exports = []
            for filename in ("ready-a.glb", "ready-b.glb"):
                output = Path(temp_dir) / filename
                result = run_blender(
                    str(library_blend),
                    "--python-exit-code",
                    "1",
                    "--python",
                    str(BLENDER_DIR / "export-econ-node-library.py"),
                    "--",
                    "--scope",
                    "ready",
                    "--output",
                    str(output),
                )
                self.assertEqual(0, result.returncode, result.stdout)
                exported = summary_from(result.stdout)
                self.assertEqual(60, exported["primitives"])
                self.assertLessEqual(exported["bytes"], 2_000_000)
                document = glb_json(output)
                active_scene = document.get("scene", 0)
                root_names = {
                    document["nodes"][index].get("name")
                    for index in document["scenes"][active_scene].get("nodes", [])
                }
                self.assertEqual(expected_ids, root_names)
                exports.append(output.read_bytes())
            self.assertEqual(exports[0], exports[1])
            committed_glb = PROJECT_ROOT / "data" / "models" / "econ-node-library.glb"
            self.assertTrue(committed_glb.is_file(), "committed ready GLB is missing")
            self.assertEqual(exports[0], committed_glb.read_bytes())

    def test_batch_authoring_material_snapshot_detects_pbr_property_drift(self):
        library_blend = BLENDER_DIR / "econ-node-library.blend"
        script = "\n".join(
            (
                "import sys",
                f"sys.path.insert(0,{str(BLENDER_DIR)!r})",
                "import bpy",
                "from model_authoring import snapshot_material_contract",
                "material=bpy.data.materials['MAT__DARK_TITANIUM']",
                "before=snapshot_material_contract(material)",
                "principled=material.node_tree.nodes['Principled BSDF']",
                "principled.inputs['IOR'].default_value+=0.125",
                "after_ior=snapshot_material_contract(material)",
                "assert before != after_ior, 'material snapshot ignored IOR drift'",
                "value=material.node_tree.nodes.new('ShaderNodeValue')",
                "after_node=snapshot_material_contract(material)",
                "value.outputs[0].default_value=0.371",
                "after_output=snapshot_material_contract(material)",
                "assert after_node != after_output, 'material snapshot ignored output default drift'",
                "material.node_tree.links.new(value.outputs[0],principled.inputs['Roughness'])",
                "after_link=snapshot_material_contract(material)",
                "assert after_output != after_link, 'material snapshot ignored node/link drift'",
            )
        )
        result = run_blender(
            str(library_blend),
            "--python-exit-code",
            "1",
            "--python-expr",
            f"exec({script!r})",
        )
        self.assertEqual(0, result.returncode, result.stdout)

    def test_batch_authoring_root_snapshot_detects_bevel_and_smoothing_drift(self):
        library_blend = BLENDER_DIR / "econ-node-library.blend"
        script = "\n".join(
            (
                "import sys",
                f"sys.path.insert(0,{str(BLENDER_DIR)!r})",
                "import bpy",
                "from model_authoring import snapshot_root_contract",
                "root=bpy.data.objects['policy_rate']",
                "body=bpy.data.objects['policy_rate__body']",
                "before=snapshot_root_contract(root)",
                "bevel=next(modifier for modifier in body.modifiers if modifier.type=='BEVEL')",
                "bevel.profile=0.31",
                "after_profile=snapshot_root_contract(root)",
                "assert before != after_profile, 'root snapshot ignored bevel profile drift'",
                "body.data.polygons[0].use_smooth=not body.data.polygons[0].use_smooth",
                "after_smooth=snapshot_root_contract(root)",
                "assert after_profile != after_smooth, 'root snapshot ignored polygon smoothing drift'",
                "normals=[normal.vector.copy() for normal in body.data.corner_normals]",
                "normals[0]=(1.0,0.0,0.0) if abs(normals[0].x)<0.9 else (0.0,1.0,0.0)",
                "body.data.normals_split_custom_set(normals)",
                "body.data.update()",
                "after_custom=snapshot_root_contract(root)",
                "assert after_smooth != after_custom, 'root snapshot ignored custom corner-normal drift'",
            )
        )
        result = run_blender(
            str(library_blend),
            "--python-exit-code",
            "1",
            "--python-expr",
            f"exec({script!r})",
        )
        self.assertEqual(0, result.returncode, result.stdout)

    def test_validator_rejects_frozen_pbr_and_custom_normal_drift(self):
        with tempfile.TemporaryDirectory(prefix="econ-frozen-render-drift-") as temp_dir:
            mutant_blend = Path(temp_dir) / "render-drift.blend"
            author_proof_library(mutant_blend)
            script = "\n".join(
                (
                    "import bpy",
                    "material=bpy.data.materials['MAT__DARK_TITANIUM']",
                    "material.node_tree.nodes['Principled BSDF'].inputs['IOR'].default_value=1.731",
                    "body=bpy.data.objects['fx__body']",
                    "normals=[normal.vector.copy() for normal in body.data.corner_normals]",
                    "normals[0]=(1.0,0.0,0.0) if abs(normals[0].x)<0.9 else (0.0,1.0,0.0)",
                    "body.data.normals_split_custom_set(normals)",
                    "body.data.update()",
                    f"bpy.ops.wm.save_as_mainfile(filepath={str(mutant_blend)!r},check_existing=False)",
                )
            )
            mutation = run_blender(
                str(mutant_blend),
                "--python-exit-code",
                "1",
                "--python-expr",
                f"exec({script!r})",
            )
            self.assertEqual(0, mutation.returncode, mutation.stdout)
            validation = run_blender(
                str(mutant_blend),
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "validate-econ-node-library.py"),
                "--",
                "--scope",
                "ready",
            )
            self.assertNotEqual(0, validation.returncode, validation.stdout)
            errors = "\n".join(summary_from(validation.stdout)["errors"])
            self.assertIn("frozen PBR/node contract drift", errors)
            self.assertIn("custom split normals are forbidden", errors)
            self.assertIn("frozen root contract drift", errors)

    def test_batch_authoring_rejects_corrupt_ready_predecessor_without_resaving(self):
        with tempfile.TemporaryDirectory(prefix="econ-corrupt-ready-gate-") as temp_dir:
            authored_blend = Path(temp_dir) / "corrupt-ready.blend"
            author_proof_library(authored_blend)
            expression = (
                "import bpy;"
                "root=bpy.data.objects['fx'];"
                "accent=bpy.data.objects['fx__accent'];"
                "accent['econ_pivot']='wrong-but-nonempty';"
                f"bpy.ops.wm.save_as_mainfile(filepath={str(authored_blend)!r},check_existing=False)"
            )
            mutation = run_blender(
                str(authored_blend),
                "--python-exit-code",
                "1",
                "--python-expr",
                expression,
            )
            self.assertEqual(0, mutation.returncode, mutation.stdout)
            corrupted_hash = hashlib.sha256(authored_blend.read_bytes()).hexdigest()

            author = run_blender(
                str(authored_blend),
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "author-money-price-models.py"),
                "--",
                "--output",
                str(authored_blend),
            )
            self.assertNotEqual(0, author.returncode, author.stdout)
            self.assertIn("Existing ready library failed frozen contract", author.stdout)
            self.assertEqual(corrupted_hash, hashlib.sha256(authored_blend.read_bytes()).hexdigest())

    def test_batch_authoring_rejects_preexisting_pbr_drift_without_resaving(self):
        with tempfile.TemporaryDirectory(prefix="econ-corrupt-pbr-gate-") as temp_dir:
            authored_blend = Path(temp_dir) / "corrupt-pbr.blend"
            author_proof_library(authored_blend)
            expression = (
                "import bpy;"
                "material=bpy.data.materials['MAT__DARK_TITANIUM'];"
                "material.node_tree.nodes['Principled BSDF'].inputs['IOR'].default_value=1.731;"
                f"bpy.ops.wm.save_as_mainfile(filepath={str(authored_blend)!r},check_existing=False)"
            )
            mutation = run_blender(
                str(authored_blend),
                "--python-exit-code",
                "1",
                "--python-expr",
                expression,
            )
            self.assertEqual(0, mutation.returncode, mutation.stdout)
            corrupted_hash = hashlib.sha256(authored_blend.read_bytes()).hexdigest()
            author = run_blender(
                str(authored_blend),
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "author-money-price-models.py"),
                "--",
                "--output",
                str(authored_blend),
            )
            self.assertNotEqual(0, author.returncode, author.stdout)
            self.assertIn("Existing ready library failed frozen contract", author.stdout)
            self.assertEqual(corrupted_hash, hashlib.sha256(authored_blend.read_bytes()).hexdigest())

    def test_batch_authoring_rejects_invalid_new_geometry_without_resaving(self):
        with tempfile.TemporaryDirectory(prefix="econ-invalid-post-gate-") as temp_dir:
            authored_blend = Path(temp_dir) / "invalid-post.blend"
            author_proof_library(authored_blend)
            before_hash = hashlib.sha256(authored_blend.read_bytes()).hexdigest()
            script = "\n".join(
                (
                    "import dataclasses, importlib.util, pathlib, sys",
                    f"sys.path.insert(0,{str(BLENDER_DIR)!r})",
                    "from model_authoring import author_models",
                    "from money_price_models import build_market_rate",
                    f"spec_path=pathlib.Path({str(BLENDER_DIR / 'node-specs.py')!r})",
                    "module_spec=importlib.util.spec_from_file_location('post_gate_specs',spec_path)",
                    "specs=importlib.util.module_from_spec(module_spec)",
                    "module_spec.loader.exec_module(specs)",
                    "def invalid_builder():",
                    "    return dataclasses.replace(build_market_rate(),accent_pivot='wrong-but-nonempty')",
                    f"author_models(output=pathlib.Path({str(authored_blend)!r}),specs=specs,builders={{'market_rate':invalid_builder}},requested=('market_rate',),required_ready=specs.PROOF_IDS)",
                )
            )
            author = run_blender(
                str(authored_blend),
                "--python-exit-code",
                "1",
                "--python-expr",
                f"exec({script!r})",
            )
            self.assertNotEqual(0, author.returncode, author.stdout)
            self.assertIn("Authored ready library failed validation", author.stdout)
            self.assertEqual(before_hash, hashlib.sha256(authored_blend.read_bytes()).hexdigest())

    def test_batch_authoring_rejects_valid_but_off_contract_geometry_without_resaving(self):
        with tempfile.TemporaryDirectory(prefix="econ-frozen-post-gate-") as temp_dir:
            authored_blend = Path(temp_dir) / "frozen-post.blend"
            author_proof_library(authored_blend)
            before_hash = hashlib.sha256(authored_blend.read_bytes()).hexdigest()
            script = "\n".join(
                (
                    "import dataclasses, importlib.util, pathlib, sys",
                    f"sys.path.insert(0,{str(BLENDER_DIR)!r})",
                    "from model_authoring import author_models",
                    "from money_price_models import build_market_rate",
                    f"spec_path=pathlib.Path({str(BLENDER_DIR / 'node-specs.py')!r})",
                    "module_spec=importlib.util.spec_from_file_location('frozen_post_specs',spec_path)",
                    "specs=importlib.util.module_from_spec(module_spec)",
                    "module_spec.loader.exec_module(specs)",
                    "def valid_but_off_contract_builder():",
                    "    return dataclasses.replace(build_market_rate(),body_detail='valid alternate body detail')",
                    f"author_models(output=pathlib.Path({str(authored_blend)!r}),specs=specs,builders={{'market_rate':valid_but_off_contract_builder}},requested=('market_rate',),required_ready=specs.PROOF_IDS)",
                )
            )
            author = run_blender(
                str(authored_blend),
                "--python-exit-code",
                "1",
                "--python-expr",
                f"exec({script!r})",
            )
            self.assertNotEqual(0, author.returncode, author.stdout)
            self.assertIn("Serialized authored ready library failed frozen contract", author.stdout)
            self.assertEqual(before_hash, hashlib.sha256(authored_blend.read_bytes()).hexdigest())

    def test_validator_declares_triangle_bands_for_all_thirty_authored_models(self):
        expected = {
            "policy_rate": (2_860, 2_990),
            "fx": (2_540, 2_940),
            "oil": (2_348, 2_748),
            "housing": (1_416, 1_816),
            "gdp": (1_560, 1_920),
            "risk_sentiment": (1_736, 2_136),
            "market_rate": (1_932, 2_332),
            "liquidity": (2_084, 2_484),
            "credit_spread": (1_584, 1_984),
            "bank_lending": (2_376, 2_776),
            "cpi": (2_456, 2_856),
            "inflation_exp": (1_624, 2_024),
            "wages": (2_088, 2_488),
            "exports": (1_520, 1_920),
            "current_account": (1_796, 2_196),
            "capital_flows": (2_148, 2_548),
            "fed_rate": (2_652, 2_952),
            "global_growth": (2_392, 2_792),
            "consumption": (1_756, 2_156),
            "investment": (2_016, 2_416),
            "employment": (2_228, 2_628),
            "earnings": (1_396, 1_796),
            "defaults": (1_508, 1_908),
            "stocks": (1_528, 1_928),
            "household_debt": (1_728, 2_128),
            "commodity": (1_400, 1_900),
            "fiscal": (2_236, 2_636),
            "geopolitics": (2_188, 2_588),
            "tech": (2_560, 2_960),
            "consumer_conf": (1_716, 2_116),
        }
        script = "\n".join(
            (
                "import importlib.util",
                f"path={str(BLENDER_DIR / 'validate-econ-node-library.py')!r}",
                "spec=importlib.util.spec_from_file_location('validator',path)",
                "module=importlib.util.module_from_spec(spec)",
                "spec.loader.exec_module(module)",
                f"assert module.MODEL_TRIANGLE_BANDS == {expected!r}, module.MODEL_TRIANGLE_BANDS",
            )
        )
        result = run_blender(
            "--python-exit-code",
            "1",
            "--python-expr",
            f"exec({script!r})",
        )
        self.assertEqual(0, result.returncode, result.stdout)

    def test_validator_thin_axis_contract_distinguishes_rotor_and_lens_planes(self):
        script = "\n".join(
            (
                "import importlib.util",
                f"path={str(BLENDER_DIR / 'validate-econ-node-library.py')!r}",
                "spec=importlib.util.spec_from_file_location('validator',path)",
                "module=importlib.util.module_from_spec(spec)",
                "spec.loader.exec_module(module)",
                "assert module._thin_axis_contract_error('liquidity',(1.0,0.9,0.40)) is None",
                "assert module._thin_axis_contract_error('liquidity',(1.0,0.9,0.41)) is not None",
                "assert module._thin_axis_contract_error('cpi',(1.0,0.44,1.0)) is None",
                "assert module._thin_axis_contract_error('cpi',(1.0,0.46,1.0)) is not None",
            )
        )
        result = run_blender(
            "--python-exit-code",
            "1",
            "--python-expr",
            f"exec({script!r})",
        )
        self.assertEqual(0, result.returncode, result.stdout)

    def test_validator_rejects_geometry_duplicate_despite_unique_description(self):
        with tempfile.TemporaryDirectory(prefix="econ-proof-duplicate-geometry-") as temp_dir:
            mutant_blend = Path(temp_dir) / "duplicate.blend"
            shutil.copy2(BLENDER_DIR / "econ-node-library.blend", mutant_blend)
            script = "\n".join(
                (
                    "import bpy",
                    "source_root=bpy.data.objects['housing']",
                    "target_root=bpy.data.objects['risk_sentiment']",
                    "source={obj.get('econ_role'):obj for obj in source_root.children_recursive if obj.type=='MESH'}",
                    "target={obj.get('econ_role'):obj for obj in target_root.children_recursive if obj.type=='MESH'}",
                    "for role in ('body','accent'):",
                    "    old=target[role].data",
                    "    old_material=target[role].material_slots[0].material",
                    "    new=source[role].data.copy()",
                    "    target[role].data=new",
                    "    target[role].matrix_local=source[role].matrix_local.copy()",
                    "    if old.users==0: bpy.data.meshes.remove(old)",
                    "    new.name=f'MESH__risk_sentiment__{role}'",
                    "    new.materials.clear()",
                    "    new.materials.append(old_material)",
                    f"bpy.ops.wm.save_as_mainfile(filepath={str(mutant_blend)!r},check_existing=False)",
                )
            )
            mutation = run_blender(
                str(mutant_blend),
                "--python-exit-code",
                "1",
                "--python-expr",
                f"exec({script!r})",
            )
            self.assertEqual(0, mutation.returncode, mutation.stdout)

            validation = run_blender(
                str(mutant_blend),
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "validate-econ-node-library.py"),
                "--",
                "--scope",
                "proof",
            )
            self.assertNotEqual(0, validation.returncode, validation.stdout)
            errors = "\n".join(summary_from(validation.stdout)["errors"])
            self.assertIn("three-view silhouette IoU", errors)
            self.assertIn("housing", errors)
            self.assertIn("risk_sentiment", errors)

    def test_validator_rejects_shared_or_noncanonical_mesh_data(self):
        with tempfile.TemporaryDirectory(prefix="econ-proof-shared-mesh-") as temp_dir:
            mutant_blend = Path(temp_dir) / "shared.blend"
            shutil.copy2(BLENDER_DIR / "econ-node-library.blend", mutant_blend)
            script = "\n".join(
                (
                    "import bpy",
                    "source_root=bpy.data.objects['housing']",
                    "target_root=bpy.data.objects['risk_sentiment']",
                    "source={obj.get('econ_role'):obj for obj in source_root.children_recursive if obj.type=='MESH'}",
                    "target={obj.get('econ_role'):obj for obj in target_root.children_recursive if obj.type=='MESH'}",
                    "for role in ('body','accent'):",
                    "    old=target[role].data",
                    "    old_material=target[role].material_slots[0].material",
                    "    target[role].data=source[role].data",
                    "    target[role].matrix_local=source[role].matrix_local.copy()",
                    "    target[role].material_slots[0].link='OBJECT'",
                    "    target[role].material_slots[0].material=old_material",
                    "    if old.users==0: bpy.data.meshes.remove(old)",
                    f"bpy.ops.wm.save_as_mainfile(filepath={str(mutant_blend)!r},check_existing=False)",
                )
            )
            mutation = run_blender(
                str(mutant_blend),
                "--python-exit-code",
                "1",
                "--python-expr",
                f"exec({script!r})",
            )
            self.assertEqual(0, mutation.returncode, mutation.stdout)
            validation = run_blender(
                str(mutant_blend),
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "validate-econ-node-library.py"),
                "--",
                "--scope",
                "proof",
            )
            self.assertNotEqual(0, validation.returncode, validation.stdout)
            errors = "\n".join(summary_from(validation.stdout)["errors"])
            self.assertIn("mesh data name", errors)
            self.assertIn("unique mesh ownership", errors)

    def test_validator_rejects_token_bevel_coverage(self):
        with tempfile.TemporaryDirectory(prefix="econ-proof-token-bevel-") as temp_dir:
            mutant_blend = Path(temp_dir) / "token-bevel.blend"
            shutil.copy2(BLENDER_DIR / "econ-node-library.blend", mutant_blend)
            script = "\n".join(
                (
                    "import bpy",
                    "obj=bpy.data.objects['housing__body']",
                    "bevel=next(modifier for modifier in obj.modifiers if modifier.type=='BEVEL')",
                    "weights=obj.data.attributes[bevel.edge_weight]",
                    "[setattr(item,'value',0.0) for item in weights.data]",
                    "[setattr(weights.data[index],'value',1.0) for index in range(4)]",
                    "obj['econ_bevel_tagged_edges']=4",
                    f"bpy.ops.wm.save_as_mainfile(filepath={str(mutant_blend)!r},check_existing=False)",
                )
            )
            mutation = run_blender(
                str(mutant_blend),
                "--python-exit-code",
                "1",
                "--python-expr",
                f"exec({script!r})",
            )
            self.assertEqual(0, mutation.returncode, mutation.stdout)
            validation = run_blender(
                str(mutant_blend),
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "validate-econ-node-library.py"),
                "--",
                "--scope",
                "proof",
            )
            self.assertNotEqual(0, validation.returncode, validation.stdout)
            errors = "\n".join(summary_from(validation.stdout)["errors"])
            self.assertIn("housing/body: bevel coverage minimum", errors)

    def test_validator_rejects_fractional_bevel_weight_above_half(self):
        with tempfile.TemporaryDirectory(prefix="econ-proof-fractional-bevel-") as temp_dir:
            mutant_blend = Path(temp_dir) / "fractional-bevel.blend"
            shutil.copy2(BLENDER_DIR / "econ-node-library.blend", mutant_blend)
            script = "\n".join(
                (
                    "import bpy",
                    "obj=bpy.data.objects['housing__body']",
                    "bevel=next(modifier for modifier in obj.modifiers if modifier.type=='BEVEL')",
                    "weights=obj.data.attributes[bevel.edge_weight]",
                    "tagged=next(item for item in weights.data if item.value>0.99)",
                    "tagged.value=0.51",
                    f"bpy.ops.wm.save_as_mainfile(filepath={str(mutant_blend)!r},check_existing=False)",
                )
            )
            mutation = run_blender(
                str(mutant_blend),
                "--python-exit-code",
                "1",
                "--python-expr",
                f"exec({script!r})",
            )
            self.assertEqual(0, mutation.returncode, mutation.stdout)
            validation = run_blender(
                str(mutant_blend),
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "validate-econ-node-library.py"),
                "--",
                "--scope",
                "proof",
            )
            self.assertNotEqual(0, validation.returncode, validation.stdout)
            errors = "\n".join(summary_from(validation.stdout)["errors"])
            self.assertIn("housing/body: bevel weights must be binary", errors)

    def test_validator_rejects_wrong_nonempty_pivot_and_child_rotation(self):
        with tempfile.TemporaryDirectory(prefix="econ-proof-accent-transform-") as temp_dir:
            mutant_blend = Path(temp_dir) / "accent-transform.blend"
            shutil.copy2(BLENDER_DIR / "econ-node-library.blend", mutant_blend)
            script = "\n".join(
                (
                    "import bpy",
                    "housing=bpy.data.objects['housing__accent']",
                    "housing['econ_pivot']='wrong_but_nonempty'",
                    "oil=bpy.data.objects['oil__accent']",
                    "oil.rotation_euler[0]=0.01",
                    f"bpy.ops.wm.save_as_mainfile(filepath={str(mutant_blend)!r},check_existing=False)",
                )
            )
            mutation = run_blender(
                str(mutant_blend),
                "--python-exit-code",
                "1",
                "--python-expr",
                f"exec({script!r})",
            )
            self.assertEqual(0, mutation.returncode, mutation.stdout)
            validation = run_blender(
                str(mutant_blend),
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "validate-econ-node-library.py"),
                "--",
                "--scope",
                "proof",
            )
            self.assertNotEqual(0, validation.returncode, validation.stdout)
            errors = "\n".join(summary_from(validation.stdout)["errors"])
            self.assertIn("housing/accent econ_pivot expected", errors)
            self.assertIn("oil/accent child rotation must be identity", errors)

    def test_glb_validator_rejects_reused_mesh_names_and_accent_motion_drift(self):
        with tempfile.TemporaryDirectory(prefix="econ-proof-glb-ownership-") as temp_dir:
            temp = Path(temp_dir)
            valid_glb = temp / "valid.glb"
            invalid_glb = temp / "invalid.glb"
            library_blend = BLENDER_DIR / "econ-node-library.blend"
            export = run_blender(
                str(library_blend),
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "export-econ-node-library.py"),
                "--",
                "--scope",
                "proof",
                "--output",
                str(valid_glb),
            )
            self.assertEqual(0, export.returncode, export.stdout)

            def drift(document: dict) -> None:
                nodes = document["nodes"]
                housing_body = next(node for node in nodes if node.get("name") == "housing__body")
                risk_body = next(node for node in nodes if node.get("name") == "risk_sentiment__body")
                risk_body["mesh"] = housing_body["mesh"]
                fx_accent = next(node for node in nodes if node.get("name") == "fx__accent")
                document["meshes"][fx_accent["mesh"]]["name"] = "MESH__WRONG"
                oil_accent = next(node for node in nodes if node.get("name") == "oil__accent")
                oil_accent.setdefault("extras", {}).pop("econ_pivot", None)
                oil_accent["extras"]["econ_signature"] = "translate"

            mutate_glb(valid_glb, invalid_glb, drift)
            validation = run_blender(
                str(library_blend),
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "validate-econ-node-library.py"),
                "--",
                "--scope",
                "proof",
                "--glb",
                str(invalid_glb),
            )
            self.assertNotEqual(0, validation.returncode, validation.stdout)
            errors = "\n".join(summary_from(validation.stdout)["errors"])
            self.assertIn("mesh index reused", errors)
            self.assertIn("mesh name expected", errors)
            self.assertIn("econ_pivot", errors)
            self.assertIn("accent econ_signature", errors)

    def test_glb_validator_rejects_wrong_pivot_and_accent_transform_drift(self):
        with tempfile.TemporaryDirectory(prefix="econ-proof-glb-transform-") as temp_dir:
            temp = Path(temp_dir)
            valid_glb = temp / "valid.glb"
            invalid_glb = temp / "invalid.glb"
            library_blend = BLENDER_DIR / "econ-node-library.blend"
            export = run_blender(
                str(library_blend),
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "export-econ-node-library.py"),
                "--",
                "--scope",
                "proof",
                "--output",
                str(valid_glb),
            )
            self.assertEqual(0, export.returncode, export.stdout)

            def drift(document: dict) -> None:
                oil_accent = next(
                    node for node in document["nodes"] if node.get("name") == "oil__accent"
                )
                oil_accent.setdefault("extras", {})["econ_pivot"] = "wrong_but_nonempty"
                oil_accent["rotation"] = [0.00499998, 0.0, 0.0, 0.9999875]
                oil_accent["scale"] = [1.001, 1.0, 1.0]
                translation = list(oil_accent.get("translation", [0.0, 0.0, 0.0]))
                translation[0] += 0.001
                oil_accent["translation"] = translation

            mutate_glb(valid_glb, invalid_glb, drift)
            validation = run_blender(
                str(library_blend),
                "--python-exit-code",
                "1",
                "--python",
                str(BLENDER_DIR / "validate-econ-node-library.py"),
                "--",
                "--scope",
                "proof",
                "--glb",
                str(invalid_glb),
            )
            self.assertNotEqual(0, validation.returncode, validation.stdout)
            errors = "\n".join(summary_from(validation.stdout)["errors"])
            self.assertIn("GLB oil/accent econ_pivot expected", errors)
            self.assertIn("GLB oil/accent rotation must be identity", errors)
            self.assertIn("GLB oil/accent scale must be identity", errors)
            self.assertIn("GLB oil/accent translation expected", errors)

    def test_glb_validator_rejects_position_payload_drift_with_unchanged_json(self):
        with tempfile.TemporaryDirectory(prefix="econ-proof-glb-position-payload-") as temp_dir:
            temp = Path(temp_dir)
            ready_blend = temp / "ready.blend"
            valid_glb = temp / "valid.glb"
            invalid_glb = temp / "invalid-position.glb"
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
            json_payload = next(payload for chunk_type, payload in chunks if chunk_type == 0x4E4F534A)
            bin_payload = bytearray(
                next(payload for chunk_type, payload in chunks if chunk_type == 0x004E4942)
            )
            document = json.loads(
                json_payload.rstrip(b" \t\r\n\x00").decode("utf-8")
            )
            body_node = next(
                node for node in document["nodes"] if node.get("name") == "policy_rate__body"
            )
            primitive = document["meshes"][body_node["mesh"]]["primitives"][0]
            position_accessor = document["accessors"][primitive["attributes"]["POSITION"]]
            position_view = document["bufferViews"][position_accessor["bufferView"]]
            payload_offset = (
                position_view.get("byteOffset", 0)
                + position_accessor.get("byteOffset", 0)
            )
            original = struct.unpack_from("<f", bin_payload, payload_offset)[0]
            struct.pack_into("<f", bin_payload, payload_offset, original + 0.123)
            write_glb_chunks(
                invalid_glb,
                magic,
                version,
                [
                    (chunk_type, bytes(bin_payload) if chunk_type == 0x004E4942 else payload)
                    for chunk_type, payload in chunks
                ],
            )

            self.assertEqual(
                glb_json(valid_glb),
                glb_json(invalid_glb),
                "POSITION payload mutant must preserve the complete GLB JSON chunk",
            )
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
            self.assertIn(
                "GLB policy_rate/body POSITION/INDEX payload fingerprint mismatch",
                errors,
            )

    def test_glb_validator_rejects_reversed_winding_with_unchanged_json(self):
        with tempfile.TemporaryDirectory(prefix="econ-proof-glb-winding-payload-") as temp_dir:
            temp = Path(temp_dir)
            ready_blend = temp / "ready.blend"
            valid_glb = temp / "valid.glb"
            invalid_glb = temp / "invalid-winding.glb"
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
            json_payload = next(payload for chunk_type, payload in chunks if chunk_type == 0x4E4F534A)
            bin_payload = bytearray(
                next(payload for chunk_type, payload in chunks if chunk_type == 0x004E4942)
            )
            document = json.loads(
                json_payload.rstrip(b" \t\r\n\x00").decode("utf-8")
            )
            body_node = next(
                node for node in document["nodes"] if node.get("name") == "policy_rate__body"
            )
            primitive = document["meshes"][body_node["mesh"]]["primitives"][0]
            index_accessor = document["accessors"][primitive["indices"]]
            index_view = document["bufferViews"][index_accessor["bufferView"]]
            component_format = {
                5121: "B",
                5123: "H",
                5125: "I",
            }[index_accessor["componentType"]]
            component_size = struct.calcsize("<" + component_format)
            stride = index_view.get("byteStride", component_size)
            base_offset = (
                index_view.get("byteOffset", 0)
                + index_accessor.get("byteOffset", 0)
            )
            self.assertEqual(0, index_accessor["count"] % 3)
            for triangle_offset in range(0, index_accessor["count"], 3):
                second_offset = base_offset + (triangle_offset + 1) * stride
                third_offset = base_offset + (triangle_offset + 2) * stride
                second = struct.unpack_from(
                    "<" + component_format, bin_payload, second_offset
                )[0]
                third = struct.unpack_from(
                    "<" + component_format, bin_payload, third_offset
                )[0]
                struct.pack_into(
                    "<" + component_format, bin_payload, second_offset, third
                )
                struct.pack_into(
                    "<" + component_format, bin_payload, third_offset, second
                )
            write_glb_chunks(
                invalid_glb,
                magic,
                version,
                [
                    (chunk_type, bytes(bin_payload) if chunk_type == 0x004E4942 else payload)
                    for chunk_type, payload in chunks
                ],
            )

            self.assertEqual(
                glb_json(valid_glb),
                glb_json(invalid_glb),
                "winding mutant must preserve the complete GLB JSON chunk",
            )
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
            self.assertIn(
                "GLB policy_rate/body POSITION/INDEX payload fingerprint mismatch",
                errors,
            )

    def test_glb_validator_rejects_non_unit_normal_payload_with_unchanged_json(self):
        with tempfile.TemporaryDirectory(prefix="econ-glb-normal-payload-") as temp_dir:
            temp = Path(temp_dir)
            ready_blend = temp / "ready.blend"
            valid_glb = temp / "valid.glb"
            invalid_glb = temp / "invalid-normal.glb"
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
            json_payload = next(payload for chunk_type, payload in chunks if chunk_type == 0x4E4F534A)
            bin_payload = bytearray(
                next(payload for chunk_type, payload in chunks if chunk_type == 0x004E4942)
            )
            document = json.loads(json_payload.rstrip(b" \t\r\n\x00").decode("utf-8"))
            body_node = next(
                node for node in document["nodes"] if node.get("name") == "policy_rate__body"
            )
            primitive = document["meshes"][body_node["mesh"]]["primitives"][0]
            normal_accessor = document["accessors"][primitive["attributes"]["NORMAL"]]
            normal_view = document["bufferViews"][normal_accessor["bufferView"]]
            payload_offset = normal_view.get("byteOffset", 0) + normal_accessor.get("byteOffset", 0)
            struct.pack_into("<fff", bin_payload, payload_offset, 0.0, 0.0, 0.0)
            write_glb_chunks(
                invalid_glb,
                magic,
                version,
                [
                    (chunk_type, bytes(bin_payload) if chunk_type == 0x004E4942 else payload)
                    for chunk_type, payload in chunks
                ],
            )
            self.assertEqual(glb_json(valid_glb), glb_json(invalid_glb))

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
            self.assertIn("GLB policy_rate/body NORMAL payload must contain unit vectors", errors)


if __name__ == "__main__":
    unittest.main()
