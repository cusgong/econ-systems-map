"""Fail-closed scene and GLB validator for the economic node library."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys
from typing import Iterable

import bmesh
import bpy
from mathutils import Matrix, Vector


SCRIPT_DIR = Path(__file__).resolve().parent
MAX_MODEL_TRIANGLES = 3_000
MAX_TOTAL_TRIANGLES = 100_000
MAX_GLB_BYTES = 3_000_000
NORMALIZED_RADIUS_MIN = 0.98
NORMALIZED_RADIUS_MAX = 1.02
CENTER_ERROR_RATIO = 0.05
ZERO_EPSILON = 1.0e-10


def _load_specs():
    module_path = SCRIPT_DIR / "node-specs.py"
    spec = importlib.util.spec_from_file_location("econ_node_specs", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load node specs: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SPECS = _load_specs()


def _fresh_summary(scope: str) -> dict:
    return {
        "scope": scope,
        "readyCount": 0,
        "fallbackCount": len(SPECS.CANONICAL_IDS),
        "triangles": 0,
        "primitives": 0,
        "bytes": 0,
        "models": {},
        "errors": [],
    }


def _append_error(summary: dict, message: str) -> None:
    if message not in summary["errors"]:
        summary["errors"].append(message)


def _is_identity_transform(obj: bpy.types.Object, tolerance: float = 1.0e-6) -> bool:
    identity = Matrix.Identity(4)
    local = obj.matrix_local
    return all(
        abs(local[row][column] - identity[row][column]) <= tolerance
        for row in range(4)
        for column in range(4)
    )


def _descendants(root: bpy.types.Object) -> list[bpy.types.Object]:
    result: list[bpy.types.Object] = []
    stack = list(root.children)
    while stack:
        obj = stack.pop()
        result.append(obj)
        stack.extend(obj.children)
    return result


def _scope_roots(roots: dict[str, bpy.types.Object], scope: str, summary: dict):
    ready_ids = [
        node_id
        for node_id in SPECS.CANONICAL_IDS
        if node_id in roots and bool(roots[node_id].get("econ_ready", False))
    ]
    summary["fallbackCount"] = len(SPECS.CANONICAL_IDS) - len(ready_ids)
    if scope == "ready":
        if not ready_ids:
            _append_error(summary, "no ready roots for scope=ready")
        selected_ids = ready_ids
    elif scope == "proof":
        missing = [node_id for node_id in SPECS.PROOF_IDS if node_id not in ready_ids]
        if missing:
            _append_error(summary, f"proof roots are not ready: {missing}")
        selected_ids = [node_id for node_id in SPECS.PROOF_IDS if node_id in ready_ids]
    else:
        missing = [node_id for node_id in SPECS.CANONICAL_IDS if node_id not in ready_ids]
        if missing:
            _append_error(summary, f"full roots are not ready: {missing}")
        selected_ids = ready_ids
    summary["readyCount"] = len(selected_ids)
    return [roots[node_id] for node_id in selected_ids if node_id in roots]


def _check_global_scene_contract(summary: dict) -> dict[str, bpy.types.Object]:
    material_names = [material.name for material in bpy.data.materials]
    collection_names = [collection.name for collection in bpy.data.collections]
    expected_collections = {
        "MASTER__ECON_NODE_LIBRARY",
        "00_ASSETS",
        "10_WIP",
        "90_QA",
        *(f"NODE__{node_id}" for node_id in SPECS.CANONICAL_IDS),
    }
    actual_collections = set(collection_names)
    if actual_collections != expected_collections:
        missing = sorted(expected_collections - actual_collections)
        extra = sorted(actual_collections - expected_collections)
        _append_error(summary, f"collection contract mismatch: missing={missing}, extra={extra}")

    master = bpy.data.collections.get("MASTER__ECON_NODE_LIBRARY")
    assets = bpy.data.collections.get("00_ASSETS")
    wip = bpy.data.collections.get("10_WIP")
    qa = bpy.data.collections.get("90_QA")
    if master is not None and master.name not in {
        child.name for child in bpy.context.scene.collection.children
    }:
        _append_error(summary, "MASTER__ECON_NODE_LIBRARY is not linked to the active scene")
    if master is not None:
        master_children = {child.name for child in master.children}
        expected_master_children = {"00_ASSETS", "10_WIP", "90_QA"}
        if master_children != expected_master_children:
            _append_error(
                summary,
                "master collection children mismatch: "
                f"expected={sorted(expected_master_children)}, actual={sorted(master_children)}",
            )

    roots: dict[str, bpy.types.Object] = {}
    asset_top_level: list[str] = []
    if assets is not None:
        expected_node_collections = {f"NODE__{node_id}" for node_id in SPECS.CANONICAL_IDS}
        actual_node_collections = {child.name for child in assets.children}
        if actual_node_collections != expected_node_collections:
            _append_error(
                summary,
                "asset node collection mismatch: "
                f"missing={sorted(expected_node_collections - actual_node_collections)}, "
                f"extra={sorted(actual_node_collections - expected_node_collections)}",
            )
        if assets.objects:
            _append_error(
                summary,
                f"00_ASSETS must not contain direct objects: {sorted(obj.name for obj in assets.objects)}",
            )
        for node_id in SPECS.CANONICAL_IDS:
            node_collection = bpy.data.collections.get(f"NODE__{node_id}")
            if node_collection is None:
                continue
            candidates = [obj for obj in node_collection.objects if obj.parent is None]
            asset_top_level.extend(obj.name for obj in candidates)
            matching = [obj for obj in candidates if obj.name == node_id]
            if len(candidates) != 1 or len(matching) != 1:
                _append_error(
                    summary,
                    f"{node_id}: NODE collection must contain exactly its canonical top-level root, "
                    f"found={sorted(obj.name for obj in candidates)}",
                )
                continue
            roots[node_id] = matching[0]

    expected_ids = set(SPECS.CANONICAL_IDS)
    actual_ids = set(asset_top_level)
    if actual_ids != expected_ids:
        _append_error(
            summary,
            "canonical root mismatch: "
            f"missing={sorted(expected_ids - actual_ids)}, extra={sorted(actual_ids - expected_ids)}",
        )

    asset_objects = set(assets.all_objects) if assets is not None else set()
    support_objects = set()
    if wip is not None:
        support_objects.update(wip.all_objects)
    if qa is not None:
        support_objects.update(qa.all_objects)
    assigned_objects = asset_objects | support_objects
    unassigned = sorted(obj.name for obj in bpy.data.objects if obj not in assigned_objects)
    if unassigned:
        _append_error(summary, f"objects outside asset/WIP/QA zones: {unassigned}")

    asset_object_names = [obj.name for obj in asset_objects]
    asset_data_names = [
        obj.data.name for obj in asset_objects if obj.type == "MESH" and obj.data is not None
    ]
    protected_names = asset_object_names + asset_data_names + material_names + collection_names
    suffixed = sorted(name for name in protected_names if re_suffix(name))
    if suffixed:
        _append_error(summary, f"forbidden numeric name suffixes: {suffixed}")

    duplicates = sorted(
        name for name in set(asset_object_names) if asset_object_names.count(name) > 1
    )
    if duplicates:
        _append_error(summary, f"duplicate asset object names: {duplicates}")

    for node_id, root in roots.items():
        if root.type != "EMPTY":
            _append_error(summary, f"{node_id}: canonical root must be EMPTY, found {root.type}")
        if not _is_identity_transform(root):
            _append_error(summary, f"{node_id}: root transform is not identity")
        signature, axis, amount = SPECS.NODE_MOTIONS[node_id]
        expected = {
            "econ_schema_version": 1,
            "econ_id": node_id,
            "econ_signature": signature,
            "econ_axis": axis,
            "econ_amount": amount,
        }
        for key, value in expected.items():
            actual = root.get(key)
            if isinstance(value, float):
                valid = isinstance(actual, (int, float)) and math.isclose(
                    float(actual), value, rel_tol=0.0, abs_tol=1.0e-6
                )
            else:
                valid = actual == value
            if not valid:
                _append_error(summary, f"{node_id}: {key} expected {value!r}, found {actual!r}")
        if not isinstance(root.get("econ_ready"), bool):
            _append_error(summary, f"{node_id}: econ_ready must be a boolean")
        duration = root.get("econ_duration")
        if not isinstance(duration, (int, float)) or not 0.16 <= float(duration) <= 0.32:
            _append_error(summary, f"{node_id}: econ_duration must be within 0.16..0.32")

    actual_materials = set(material_names)
    expected_materials = set(SPECS.MATERIAL_NAMES)
    if actual_materials != expected_materials:
        missing = sorted(expected_materials - actual_materials)
        extra = sorted(actual_materials - expected_materials)
        _append_error(summary, f"material library mismatch: missing={missing}, extra={extra}")

    unsupported_cameras = sorted(
        obj.name
        for obj in bpy.data.objects
        if obj.type == "CAMERA" and obj not in support_objects
    )
    if unsupported_cameras:
        _append_error(summary, f"asset scene contains cameras: {unsupported_cameras}")
    unsupported_lights = sorted(
        obj.name
        for obj in bpy.data.objects
        if obj.type == "LIGHT" and obj not in support_objects
    )
    if unsupported_lights:
        _append_error(summary, f"asset scene contains lights: {unsupported_lights}")
    if bpy.data.actions:
        _append_error(summary, f"scene contains animations: {[item.name for item in bpy.data.actions]}")
    external_images = [
        item.name
        for item in bpy.data.images
        if item.source == "FILE" or item.packed_file is not None
    ]
    if external_images:
        _append_error(summary, f"scene contains images: {external_images}")
    armatures = [obj.name for obj in bpy.data.objects if obj.type == "ARMATURE"]
    if armatures:
        _append_error(summary, f"scene contains skins/armatures: {armatures}")
    return roots


def re_suffix(name: str) -> bool:
    if len(name) < 4 or name[-4] != ".":
        return False
    return name[-3:].isdigit()


def _evaluated_mesh_metrics(
    obj: bpy.types.Object,
    depsgraph: bpy.types.Depsgraph,
    summary: dict,
    label: str,
) -> dict:
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=False, depsgraph=depsgraph)
    try:
        mesh.calc_loop_triangles()
        triangles = len(mesh.loop_triangles)
        vertices = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
        if not vertices:
            _append_error(summary, f"{label}: mesh has no vertices")
            return {"triangles": triangles, "area": 0.0, "vertices": []}
        if any(not all(math.isfinite(value) for value in vertex) for vertex in vertices):
            _append_error(summary, f"{label}: mesh contains non-finite vertices")

        area = sum(float(polygon.area) for polygon in mesh.polygons)
        if not math.isfinite(area) or area <= ZERO_EPSILON:
            _append_error(summary, f"{label}: mesh has non-finite or zero surface area")
        zero_faces = sum(1 for polygon in mesh.polygons if polygon.area <= ZERO_EPSILON)
        if zero_faces:
            _append_error(summary, f"{label}: mesh has {zero_faces} zero-area faces")

        invalid_normals = 0
        for polygon in mesh.polygons:
            normal = polygon.normal
            if not all(math.isfinite(value) for value in normal) or normal.length <= ZERO_EPSILON:
                invalid_normals += 1
        if invalid_normals:
            _append_error(summary, f"{label}: mesh has {invalid_normals} invalid face normals")

        bm = bmesh.new()
        try:
            bm.from_mesh(mesh)
            bm.normal_update()
            loose_vertices = sum(1 for vertex in bm.verts if not vertex.link_edges)
            loose_edges = sum(1 for edge in bm.edges if not edge.link_faces)
            nonmanifold = sum(1 for edge in bm.edges if not edge.is_manifold)
            discontinuous = sum(
                1 for edge in bm.edges if edge.is_manifold and not edge.is_contiguous
            )
            if loose_vertices or loose_edges:
                _append_error(
                    summary,
                    f"{label}: loose geometry vertices={loose_vertices}, edges={loose_edges}",
                )
            if nonmanifold:
                _append_error(summary, f"{label}: non-manifold edges={nonmanifold}")
            if discontinuous:
                _append_error(summary, f"{label}: inconsistent normal edges={discontinuous}")
        finally:
            bm.free()

        signed_volume = 0.0
        for triangle in mesh.loop_triangles:
            a, b, c = (mesh.vertices[index].co for index in triangle.vertices)
            signed_volume += a.dot(b.cross(c)) / 6.0
        if not math.isfinite(signed_volume) or signed_volume <= ZERO_EPSILON:
            _append_error(summary, f"{label}: normals do not enclose positive volume")

        return {"triangles": triangles, "area": area, "vertices": vertices}
    finally:
        evaluated.to_mesh_clear()


def _validate_model(
    root: bpy.types.Object,
    depsgraph: bpy.types.Depsgraph,
    summary: dict,
) -> None:
    node_id = root.name
    descendants = _descendants(root)
    meshes = [obj for obj in descendants if obj.type == "MESH"]
    non_meshes = [obj.name for obj in descendants if obj.type != "MESH"]
    if non_meshes:
        _append_error(summary, f"{node_id}: non-render descendants are forbidden: {non_meshes}")

    expected_names = {f"{node_id}__body", f"{node_id}__accent"}
    actual_names = {obj.name for obj in meshes}
    if actual_names != expected_names or len(meshes) != 2:
        _append_error(
            summary,
            f"{node_id}: render mesh mismatch expected={sorted(expected_names)}, actual={sorted(actual_names)}",
        )

    metrics_by_role: dict[str, dict] = {}
    for obj in meshes:
        role = obj.get("econ_role")
        if role not in {"body", "accent"}:
            _append_error(summary, f"{node_id}: {obj.name} missing valid econ_role")
            continue
        if obj.name != f"{node_id}__{role}":
            _append_error(summary, f"{node_id}: {obj.name} does not match econ_role={role}")
        if len(obj.material_slots) != 1 or obj.material_slots[0].material is None:
            _append_error(summary, f"{node_id}: {obj.name} must have exactly one material slot")
        else:
            material_name = obj.material_slots[0].material.name
            if role == "body" and material_name != "MAT__DARK_TITANIUM":
                _append_error(summary, f"{node_id}: body material must be MAT__DARK_TITANIUM")
            if role == "accent":
                expected_material = SPECS.CATEGORY_MATERIALS[SPECS.NODE_CATEGORIES[node_id]]
                if material_name != expected_material:
                    _append_error(
                        summary,
                        f"{node_id}: accent material expected {expected_material}, found {material_name}",
                    )
        metrics_by_role[role] = _evaluated_mesh_metrics(
            obj, depsgraph, summary, f"{node_id}/{role}"
        )

    if set(metrics_by_role) != {"body", "accent"}:
        return
    body = metrics_by_role["body"]
    accent = metrics_by_role["accent"]
    model_triangles = int(body["triangles"] + accent["triangles"])
    if model_triangles > MAX_MODEL_TRIANGLES:
        _append_error(summary, f"{node_id}: triangles {model_triangles} exceed {MAX_MODEL_TRIANGLES}")
    if node_id == "policy_rate" and not 1800 <= body["triangles"] <= 2200:
        _append_error(
            summary,
            f"policy_rate: body triangles {body['triangles']} outside 1800..2200",
        )

    all_vertices = body["vertices"] + accent["vertices"]
    if all_vertices:
        minimum = Vector((min(vertex[i] for vertex in all_vertices) for i in range(3)))
        maximum = Vector((max(vertex[i] for vertex in all_vertices) for i in range(3)))
        extent = maximum - minimum
        center = (minimum + maximum) * 0.5
        radius = max(vertex.length for vertex in all_vertices)
        if any(not math.isfinite(value) or value <= ZERO_EPSILON for value in extent):
            _append_error(summary, f"{node_id}: non-finite or zero model bounds {tuple(extent)}")
        if not NORMALIZED_RADIUS_MIN <= radius <= NORMALIZED_RADIUS_MAX:
            _append_error(summary, f"{node_id}: normalized radius {radius:.6f} outside 0.98..1.02")
        if center.length > CENTER_ERROR_RATIO * max(radius, ZERO_EPSILON):
            _append_error(
                summary,
                f"{node_id}: center error {center.length:.6f} exceeds {CENTER_ERROR_RATIO:.2f} radius",
            )
    else:
        radius = 0.0
        center = Vector((0.0, 0.0, 0.0))

    total_area = body["area"] + accent["area"]
    accent_ratio = accent["area"] / total_area if total_area > ZERO_EPSILON else 0.0
    if not 0.10 <= accent_ratio <= 0.20:
        _append_error(summary, f"{node_id}: accent area ratio {accent_ratio:.6f} outside 0.10..0.20")

    body_obj = next((obj for obj in meshes if obj.get("econ_role") == "body"), None)
    if body_obj is not None:
        bevel_ratio = body_obj.get("econ_bevel_width_ratio")
        bevel_segments = body_obj.get("econ_bevel_segments")
        if not isinstance(bevel_ratio, (int, float)) or not 0.015 <= float(bevel_ratio) <= 0.03:
            _append_error(summary, f"{node_id}: bevel width ratio must be 0.015..0.03")
        if bevel_segments != 3:
            _append_error(summary, f"{node_id}: bevel segments must equal 3")

    summary["models"][node_id] = {
        "bodyTriangles": int(body["triangles"]),
        "accentTriangles": int(accent["triangles"]),
        "triangles": model_triangles,
        "accentAreaRatio": round(accent_ratio, 6),
        "radius": round(float(radius), 6),
        "centerError": round(float(center.length), 6),
        "primitives": 2,
    }
    summary["triangles"] += model_triangles
    summary["primitives"] += 2


def validate_scene(scope: str) -> tuple[dict, list[bpy.types.Object]]:
    summary = _fresh_summary(scope)
    try:
        SPECS.require_blender_version(bpy.app.version[:3])
    except SPECS.NodeSpecError as exc:
        _append_error(summary, str(exc))
        return summary, []
    if bpy.context.scene.name != "SCENE__ECON_NODE_LIBRARY":
        _append_error(
            summary,
            f"scene name expected SCENE__ECON_NODE_LIBRARY, found {bpy.context.scene.name}",
        )
    roots = _check_global_scene_contract(summary)
    selected_roots = _scope_roots(roots, scope, summary)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for root in selected_roots:
        _validate_model(root, depsgraph, summary)
    if summary["triangles"] > MAX_TOTAL_TRIANGLES:
        _append_error(
            summary,
            f"total triangles {summary['triangles']} exceed {MAX_TOTAL_TRIANGLES}",
        )
    return summary, selected_roots


def _read_glb_json(path: Path) -> dict:
    raw = path.read_bytes()
    if len(raw) < 20:
        raise ValueError("GLB is shorter than its header and JSON chunk")
    magic, version, declared_length = struct.unpack_from("<4sII", raw, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(raw):
        raise ValueError(
            f"invalid GLB header magic={magic!r}, version={version}, declared={declared_length}, actual={len(raw)}"
        )
    chunk_length, chunk_type = struct.unpack_from("<II", raw, 12)
    if chunk_type != 0x4E4F534A:
        raise ValueError("first GLB chunk is not JSON")
    payload = raw[20 : 20 + chunk_length].rstrip(b" \t\r\n\x00")
    return json.loads(payload.decode("utf-8"))


def _node_descendants(nodes: list[dict], root_index: int) -> list[int]:
    result: list[int] = []
    stack = list(nodes[root_index].get("children", []))
    while stack:
        index = stack.pop()
        result.append(index)
        stack.extend(nodes[index].get("children", []))
    return result


def validate_glb(path: Path, expected_ids: Iterable[str], base_summary: dict | None = None) -> dict:
    summary = base_summary if base_summary is not None else _fresh_summary("glb")
    summary["bytes"] = path.stat().st_size if path.is_file() else 0
    if not path.is_file():
        _append_error(summary, f"GLB does not exist: {path}")
        return summary
    if summary["bytes"] > MAX_GLB_BYTES:
        _append_error(summary, f"GLB bytes {summary['bytes']} exceed {MAX_GLB_BYTES}")
    try:
        gltf = _read_glb_json(path)
    except Exception as exc:
        _append_error(summary, f"GLB parse failed: {exc}")
        return summary

    for forbidden in ("cameras", "images", "animations", "skins"):
        if gltf.get(forbidden):
            _append_error(summary, f"GLB contains forbidden {forbidden}")
    if gltf.get("extensionsRequired"):
        _append_error(summary, f"GLB requires extensions: {gltf['extensionsRequired']}")
    if gltf.get("extensions", {}).get("KHR_lights_punctual"):
        _append_error(summary, "GLB contains punctual lights")

    nodes = gltf.get("nodes", [])
    node_names = [node.get("name", "") for node in nodes]
    suffixed = sorted(name for name in node_names if re_suffix(name))
    if suffixed:
        _append_error(summary, f"GLB contains numeric suffix names: {suffixed}")
    duplicates = sorted(name for name in set(node_names) if name and node_names.count(name) > 1)
    if duplicates:
        _append_error(summary, f"GLB contains duplicate node names: {duplicates}")

    expected_ids = tuple(expected_ids)
    active_scene_index = gltf.get("scene", 0)
    scenes = gltf.get("scenes", [])
    active_root_indices: list[int] = []
    if not isinstance(active_scene_index, int) or not 0 <= active_scene_index < len(scenes):
        _append_error(summary, f"GLB has invalid active scene index {active_scene_index!r}")
    else:
        active_root_indices = scenes[active_scene_index].get("nodes", [])
    active_root_names = {
        nodes[index].get("name")
        for index in active_root_indices
        if isinstance(index, int) and 0 <= index < len(nodes)
    }
    if active_root_names != set(expected_ids) or len(active_root_indices) != len(expected_ids):
        _append_error(
            summary,
            "GLB active scene root mismatch: "
            f"expected={sorted(expected_ids)}, actual={sorted(str(name) for name in active_root_names)}",
        )

    roots_by_name = {
        node.get("name"): index
        for index, node in enumerate(nodes)
        if node.get("name") in expected_ids
    }
    if set(roots_by_name) != set(expected_ids):
        _append_error(
            summary,
            f"GLB canonical root mismatch: expected={sorted(expected_ids)}, actual={sorted(roots_by_name)}",
        )

    meshes = gltf.get("meshes", [])
    materials = gltf.get("materials", [])
    primitive_count = 0
    glb_triangles = 0
    accessors = gltf.get("accessors", [])
    for node_id in expected_ids:
        if node_id not in roots_by_name:
            continue
        root_index = roots_by_name[node_id]
        root_node = nodes[root_index]
        root_extras = root_node.get("extras", {})
        signature, axis, amount = SPECS.NODE_MOTIONS[node_id]
        expected_extras = {
            "econ_schema_version": 1,
            "econ_id": node_id,
            "econ_ready": True,
            "econ_signature": signature,
            "econ_axis": axis,
            "econ_amount": amount,
        }
        for key, expected in expected_extras.items():
            actual = root_extras.get(key)
            if isinstance(expected, float):
                valid = isinstance(actual, (int, float)) and math.isclose(
                    float(actual), expected, rel_tol=0.0, abs_tol=1.0e-6
                )
            else:
                valid = actual == expected
            if not valid:
                _append_error(
                    summary,
                    f"GLB {node_id}: {key} expected {expected!r}, found {actual!r}",
                )
        duration = root_extras.get("econ_duration")
        if not isinstance(duration, (int, float)) or not 0.16 <= float(duration) <= 0.32:
            _append_error(summary, f"GLB {node_id}: econ_duration must be within 0.16..0.32")

        identity_components = {
            "translation": [0.0, 0.0, 0.0],
            "rotation": [0.0, 0.0, 0.0, 1.0],
            "scale": [1.0, 1.0, 1.0],
        }
        if "matrix" in root_node:
            expected_matrix = [
                1.0, 0.0, 0.0, 0.0,
                0.0, 1.0, 0.0, 0.0,
                0.0, 0.0, 1.0, 0.0,
                0.0, 0.0, 0.0, 1.0,
            ]
            if any(
                not math.isclose(float(actual), expected, rel_tol=0.0, abs_tol=1.0e-6)
                for actual, expected in zip(root_node.get("matrix", []), expected_matrix)
            ) or len(root_node.get("matrix", [])) != 16:
                _append_error(summary, f"GLB {node_id}: root matrix is not identity")
        for key, expected in identity_components.items():
            if key in root_node and (
                len(root_node[key]) != len(expected)
                or any(
                    not math.isclose(float(actual), wanted, rel_tol=0.0, abs_tol=1.0e-6)
                    for actual, wanted in zip(root_node[key], expected)
                )
            ):
                _append_error(summary, f"GLB {node_id}: root {key} is not identity")

        mesh_nodes = [
            index
            for index in _node_descendants(nodes, root_index)
            if "mesh" in nodes[index]
        ]
        if len(mesh_nodes) != 2:
            _append_error(summary, f"GLB {node_id}: expected 2 descendant mesh nodes, found {len(mesh_nodes)}")
        mesh_node_names = {nodes[index].get("name") for index in mesh_nodes}
        expected_mesh_node_names = {f"{node_id}__body", f"{node_id}__accent"}
        if mesh_node_names != expected_mesh_node_names:
            _append_error(
                summary,
                f"GLB {node_id}: mesh node names expected={sorted(expected_mesh_node_names)}, "
                f"actual={sorted(str(name) for name in mesh_node_names)}",
            )
        roles = []
        for node_index in mesh_nodes:
            node = nodes[node_index]
            role = node.get("extras", {}).get("econ_role")
            roles.append(role)
            mesh_index = node["mesh"]
            if not isinstance(mesh_index, int) or not 0 <= mesh_index < len(meshes):
                _append_error(summary, f"GLB {node_id}: invalid mesh index {mesh_index}")
                continue
            primitives = meshes[mesh_index].get("primitives", [])
            primitive_count += len(primitives)
            if len(primitives) != 1:
                _append_error(summary, f"GLB {node_id}/{role}: expected 1 primitive, found {len(primitives)}")
            for primitive in primitives:
                expected_material = (
                    "MAT__DARK_TITANIUM"
                    if role == "body"
                    else SPECS.CATEGORY_MATERIALS[SPECS.NODE_CATEGORIES[node_id]]
                    if role == "accent"
                    else None
                )
                material_index = primitive.get("material")
                if not isinstance(material_index, int) or not 0 <= material_index < len(materials):
                    _append_error(summary, f"GLB {node_id}/{role}: primitive has invalid material")
                elif expected_material is not None:
                    actual_material = materials[material_index].get("name")
                    if actual_material != expected_material:
                        _append_error(
                            summary,
                            f"GLB {node_id}/{role}: material expected {expected_material}, "
                            f"found {actual_material}",
                        )
                attributes = set(primitive.get("attributes", {}))
                if attributes != {"POSITION", "NORMAL"}:
                    _append_error(summary, f"GLB {node_id}/{role}: unexpected attributes {sorted(attributes)}")
                mode = primitive.get("mode", 4)
                if mode != 4:
                    _append_error(summary, f"GLB {node_id}/{role}: primitive mode expected 4, found {mode}")
                index_accessor = primitive.get("indices")
                if not isinstance(index_accessor, int) or not 0 <= index_accessor < len(accessors):
                    _append_error(summary, f"GLB {node_id}/{role}: invalid index accessor {index_accessor!r}")
                    continue
                accessor = accessors[index_accessor]
                count = accessor.get("count")
                if not isinstance(count, int) or count <= 0 or count % 3 != 0:
                    _append_error(
                        summary,
                        f"GLB {node_id}/{role}: index accessor count {count!r} must be positive and divisible by 3",
                    )
                else:
                    glb_triangles += count // 3
                if accessor.get("type") != "SCALAR" or accessor.get("componentType") not in {5121, 5123, 5125}:
                    _append_error(summary, f"GLB {node_id}/{role}: invalid index accessor format")
        if set(roles) != {"body", "accent"}:
            _append_error(summary, f"GLB {node_id}: econ_role set is {sorted(str(role) for role in roles)}")

    if primitive_count != 2 * len(expected_ids):
        _append_error(
            summary,
            f"GLB primitive count {primitive_count} expected {2 * len(expected_ids)}",
        )
    summary["primitives"] = primitive_count
    if glb_triangles and summary.get("triangles") and glb_triangles != summary["triangles"]:
        _append_error(
            summary,
            f"GLB triangles {glb_triangles} do not match scene triangles {summary['triangles']}",
        )
    elif glb_triangles:
        summary["triangles"] = glb_triangles
    return summary


def emit_summary(summary: dict) -> None:
    summary["errors"] = sorted(summary["errors"])
    print(json.dumps(summary, ensure_ascii=True, sort_keys=True, separators=(",", ":")))


def _arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("ready", "proof", "full"), default="ready")
    parser.add_argument("--glb", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _arguments(sys.argv[sys.argv.index("--") + 1 :] if argv is None and "--" in sys.argv else (argv or []))
    summary, roots = validate_scene(args.scope)
    if args.glb is not None and not summary["errors"]:
        summary = validate_glb(args.glb.resolve(), [root.name for root in roots], summary)
    emit_summary(summary)
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
