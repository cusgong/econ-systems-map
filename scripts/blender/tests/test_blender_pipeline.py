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
            "policy_rate": (2500, 2750),
            "fx": (2200, 2600),
            "oil": (1800, 2200),
            "housing": (1500, 1900),
            "gdp": (1800, 2200),
            "risk_sentiment": (1500, 1900),
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
        self.assertEqual(24, summary["fallbackCount"])
        self.assertEqual(12, summary["primitives"])
        self.assertEqual(proof_ids, set(summary["models"]))
        self.assertGreaterEqual(summary["triangles"], 10_600)
        self.assertLessEqual(summary["triangles"], 13_000)
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
            committed_glb = PROJECT_ROOT / "data" / "models" / "econ-node-library.glb"
            self.assertTrue(committed_glb.is_file(), "committed proof GLB is missing")
            self.assertEqual(
                exports[0],
                hashlib.sha256(committed_glb.read_bytes()).hexdigest(),
                "committed proof GLB must be byte-identical to a fresh canonical export",
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
                self.assertIn('"readyCount":6', author.stdout)

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


if __name__ == "__main__":
    unittest.main()
