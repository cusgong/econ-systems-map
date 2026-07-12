"""Fail-closed scene and GLB validator for the economic node library."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from itertools import combinations
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
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from model_authoring import snapshot_material_contract, snapshot_root_contract  # noqa: E402

MAX_MODEL_TRIANGLES = 3_000
MAX_TOTAL_TRIANGLES = 100_000
MAX_GLB_BYTES = 3_000_000
PROOF_MAX_GLB_BYTES = 600_000
PROOF_TOTAL_TRIANGLES_MIN = 10_600
PROOF_TOTAL_TRIANGLES_MAX = 13_000
PROOF_HARD_TRIANGLES_MAX = 18_000
MODEL_TRIANGLE_BANDS = {
    "policy_rate": (2_500, 2_750),
    "fx": (2_200, 2_600),
    "oil": (1_800, 2_200),
    "housing": (1_500, 1_900),
    "gdp": (1_800, 2_200),
    "risk_sentiment": (1_500, 1_900),
    "market_rate": (1_500, 1_900),
    "liquidity": (1_900, 2_300),
    "credit_spread": (1_400, 1_800),
    "bank_lending": (1_700, 2_100),
    "cpi": (1_800, 2_200),
    "inflation_exp": (1_600, 2_000),
    "wages": (1_950, 2_250),
    "exports": (2_500, 2_950),
    "current_account": (1_950, 2_200),
    "capital_flows": (2_250, 2_650),
    "fed_rate": (2_350, 2_990),
    "global_growth": (1_950, 2_350),
    "consumption": (1_800, 2_200),
    "investment": (1_800, 2_200),
    "employment": (1_450, 1_900),
    "earnings": (1_650, 2_100),
    "defaults": (1_700, 2_150),
    "stocks": (1_650, 2_050),
    "household_debt": (1_800, 2_300),
    "commodity": (1_400, 1_900),
    "fiscal": (2_050, 2_350),
    "geopolitics": (2_200, 2_550),
    "tech": (2_450, 2_850),
    "consumer_conf": (1_400, 1_900),
}
NORMALIZED_RADIUS_MIN = 0.98
NORMALIZED_RADIUS_MAX = 1.02
CENTER_ERROR_RATIO = 0.05
ZERO_EPSILON = 1.0e-10
BEVEL_WEIGHT_TOLERANCE = 1.0e-6
GEOMETRY_QUANTIZATION = 100_000
OCCUPANCY_MASK_SIZE = 64
OCCUPANCY_MASK_EXTENT = 1.05
OCCUPANCY_IOU_FAILURE = 0.80
OCCUPANCY_VIEW_AXES = {
    "front": (0, 2),
    "side": (1, 2),
    "top": (0, 1),
}
JSON_CHUNK_TYPE = 0x4E4F534A
BIN_CHUNK_TYPE = 0x004E4942
COMPONENT_SIZES = {
    5120: 1,
    5121: 1,
    5122: 2,
    5123: 2,
    5125: 4,
    5126: 4,
}
COMPONENT_FORMATS = {
    5120: "b",
    5121: "B",
    5122: "h",
    5123: "H",
    5125: "I",
    5126: "f",
}
TYPE_COMPONENTS = {
    "SCALAR": 1,
    "VEC2": 2,
    "VEC3": 3,
    "VEC4": 4,
    "MAT2": 4,
    "MAT3": 9,
    "MAT4": 16,
}


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


def _components_close(actual, expected, tolerance: float = 1.0e-6) -> bool:
    return len(actual) == len(expected) and all(
        math.isclose(float(value), float(wanted), rel_tol=0.0, abs_tol=tolerance)
        for value, wanted in zip(actual, expected)
    )


def _thin_axis_contract_error(node_id: str, extent) -> str | None:
    contract = SPECS.ACCENT_THIN_AXIS_CONTRACTS.get(node_id)
    if contract is None:
        return None
    axis_name, maximum_ratio = contract
    axis_index = {"x": 0, "y": 1, "z": 2}[axis_name]
    other = [float(extent[index]) for index in range(3) if index != axis_index]
    thin_extent = float(extent[axis_index])
    maximum = float(maximum_ratio) * min(other)
    if thin_extent <= maximum:
        return None
    return (
        f"thin {axis_name.upper()} extent must be <= {maximum_ratio:.2f} of both "
        f"orthogonal extents, found {tuple(round(float(value), 6) for value in extent)}"
    )


def _blender_to_gltf_translation(translation) -> tuple[float, float, float]:
    return (
        float(translation[0]),
        float(translation[2]),
        -float(translation[1]),
    )


def _identity_child_rotation_and_scale(obj: bpy.types.Object) -> tuple[bool, bool]:
    _translation, rotation, scale = obj.matrix_basis.decompose()
    rotation_identity = (
        abs(float(rotation.x)) <= 1.0e-6
        and abs(float(rotation.y)) <= 1.0e-6
        and abs(float(rotation.z)) <= 1.0e-6
        and math.isclose(abs(float(rotation.w)), 1.0, rel_tol=0.0, abs_tol=1.0e-6)
    )
    return rotation_identity, _components_close(scale, (1.0, 1.0, 1.0))


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


def _check_global_scene_contract(
    summary: dict,
    *,
    enforce_frozen_roots: bool = True,
) -> dict[str, bpy.types.Object]:
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
    non_culled_materials = sorted(
        material.name
        for material in bpy.data.materials
        if material.name in expected_materials and not material.use_backface_culling
    )
    if non_culled_materials:
        _append_error(
            summary,
            f"opaque closed materials must enable backface culling: {non_culled_materials}",
        )
    for material_name, expected_hash in SPECS.MATERIAL_CONTRACT_HASHES.items():
        material = bpy.data.materials.get(material_name)
        if material is None:
            continue
        actual_hash = snapshot_material_contract(material)
        if actual_hash != expected_hash:
            _append_error(
                summary,
                f"{material_name}: frozen PBR/node contract drift "
                f"expected={expected_hash} actual={actual_hash}",
            )

    root_hashes = getattr(SPECS, "ROOT_CONTRACT_HASHES", {})
    if root_hashes and enforce_frozen_roots:
        for node_id, root in roots.items():
            if not bool(root.get("econ_ready", False)):
                continue
            expected_hash = root_hashes.get(node_id)
            if expected_hash is None:
                _append_error(summary, f"{node_id}: missing frozen root contract hash")
                continue
            actual_hash = snapshot_root_contract(root)
            if actual_hash != expected_hash:
                _append_error(
                    summary,
                    f"{node_id}: frozen root contract drift "
                    f"expected={expected_hash} actual={actual_hash}",
                )

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
            return {
                "triangles": triangles,
                "area": 0.0,
                "vertices": [],
                "triangleVertices": [],
                "triangleVerticesLocal": [],
                "extent": Vector((0.0, 0.0, 0.0)),
            }
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

        minimum = Vector(
            tuple(min(vertex[index] for vertex in vertices) for index in range(3))
        )
        maximum = Vector(
            tuple(max(vertex[index] for vertex in vertices) for index in range(3))
        )
        triangle_vertices = [
            tuple(vertices[index].copy() for index in triangle.vertices)
            for triangle in mesh.loop_triangles
        ]
        triangle_vertices_local = [
            tuple(mesh.vertices[index].co.copy() for index in triangle.vertices)
            for triangle in mesh.loop_triangles
        ]
        return {
            "triangles": triangles,
            "area": area,
            "vertices": vertices,
            "triangleVertices": triangle_vertices,
            "triangleVerticesLocal": triangle_vertices_local,
            "extent": maximum - minimum,
        }
    finally:
        evaluated.to_mesh_clear()


def _mask_coordinate(value: float) -> float:
    normalized = (value + OCCUPANCY_MASK_EXTENT) / (2.0 * OCCUPANCY_MASK_EXTENT)
    return normalized * (OCCUPANCY_MASK_SIZE - 1)


def _edge_sign(point, first, second) -> float:
    return (
        (point[0] - second[0]) * (first[1] - second[1])
        - (first[0] - second[0]) * (point[1] - second[1])
    )


def _projected_occupancy_mask(
    triangle_vertices: list[tuple[Vector, Vector, Vector]],
    axes: tuple[int, int],
) -> set[int]:
    occupied: set[int] = set()
    for triangle in triangle_vertices:
        projected = [
            (
                _mask_coordinate(vertex[axes[0]]),
                _mask_coordinate(vertex[axes[1]]),
            )
            for vertex in triangle
        ]
        area = _edge_sign(projected[0], projected[1], projected[2])
        if abs(area) <= 1.0e-9:
            continue
        minimum_x = max(0, math.floor(min(point[0] for point in projected)))
        maximum_x = min(
            OCCUPANCY_MASK_SIZE - 1,
            math.ceil(max(point[0] for point in projected)),
        )
        minimum_y = max(0, math.floor(min(point[1] for point in projected)))
        maximum_y = min(
            OCCUPANCY_MASK_SIZE - 1,
            math.ceil(max(point[1] for point in projected)),
        )
        for pixel_y in range(minimum_y, maximum_y + 1):
            for pixel_x in range(minimum_x, maximum_x + 1):
                point = (pixel_x + 0.5, pixel_y + 0.5)
                signs = (
                    _edge_sign(point, projected[0], projected[1]),
                    _edge_sign(point, projected[1], projected[2]),
                    _edge_sign(point, projected[2], projected[0]),
                )
                if not (any(value < 0.0 for value in signs) and any(value > 0.0 for value in signs)):
                    occupied.add(pixel_y * OCCUPANCY_MASK_SIZE + pixel_x)
    return occupied


def _occupancy_digest(mask: set[int]) -> str:
    payload = bytearray((OCCUPANCY_MASK_SIZE * OCCUPANCY_MASK_SIZE + 7) // 8)
    for index in mask:
        payload[index // 8] |= 1 << (index % 8)
    return hashlib.sha256(payload).hexdigest()


def _occupancy_iou(first: set[int], second: set[int]) -> float:
    union = first | second
    return len(first & second) / len(union) if union else 1.0


def _canonical_geometry_contract(triangles) -> dict:
    """Return a winding/order-independent digest and bounds for triangle payloads."""

    canonical_triangles = []
    points = []
    for triangle in triangles:
        if len(triangle) != 3:
            raise ValueError(f"geometry contract requires triangles, found {len(triangle)} vertices")
        quantized = []
        for vertex in triangle:
            if len(vertex) != 3 or not all(math.isfinite(float(value)) for value in vertex):
                raise ValueError(f"geometry contract contains invalid vertex {vertex!r}")
            point = tuple(
                int(round(float(value) * GEOMETRY_QUANTIZATION))
                for value in vertex
            )
            quantized.append(point)
            points.append(point)
        # Triangle-list order and the choice of first corner are semantically
        # irrelevant, but winding is not: all proof materials are single-sided.
        # Canonicalize only across the three cyclic rotations.  Reversing B/C
        # therefore produces a different digest and cannot silently flip every
        # rendered face while preserving the GLB JSON contract.
        cyclic_rotations = (
            tuple(quantized),
            (quantized[1], quantized[2], quantized[0]),
            (quantized[2], quantized[0], quantized[1]),
        )
        canonical_triangles.append(min(cyclic_rotations))
    canonical_triangles.sort()
    digest = hashlib.sha256()
    for triangle in canonical_triangles:
        for point in triangle:
            digest.update(struct.pack("<qqq", *point))
    if points:
        minimum = [min(point[axis] for point in points) for axis in range(3)]
        maximum = [max(point[axis] for point in points) for axis in range(3)]
    else:
        minimum = [0, 0, 0]
        maximum = [0, 0, 0]
    return {
        "sha256": digest.hexdigest(),
        "triangles": len(canonical_triangles),
        "boundsQuantized": {"min": minimum, "max": maximum},
        "quantization": GEOMETRY_QUANTIZATION,
    }


def _scene_geometry_contract(local_triangle_vertices) -> dict:
    triangles_gltf = [
        tuple(_blender_to_gltf_translation(vertex) for vertex in triangle)
        for triangle in local_triangle_vertices
    ]
    return _canonical_geometry_contract(triangles_gltf)


def _validate_model(
    root: bpy.types.Object,
    depsgraph: bpy.types.Depsgraph,
    summary: dict,
) -> dict[str, set[int]] | None:
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
    bevels_by_role: dict[str, dict] = {}
    geometry_by_role: dict[str, dict] = {}
    accent_contract = SPECS.ACCENT_CONTRACTS.get(node_id)
    if accent_contract is None:
        _append_error(summary, f"{node_id}: missing canonical accent transform contract")
        accent_contract = {
            "pivotLabel": None,
            "blenderTranslation": (0.0, 0.0, 0.0),
        }
    for obj in meshes:
        role = obj.get("econ_role")
        if role not in {"body", "accent"}:
            _append_error(summary, f"{node_id}: {obj.name} missing valid econ_role")
            continue
        if obj.name != f"{node_id}__{role}":
            _append_error(summary, f"{node_id}: {obj.name} does not match econ_role={role}")
        expected_data_name = f"MESH__{node_id}__{role}"
        if obj.data is None or obj.data.name != expected_data_name:
            actual_data_name = obj.data.name if obj.data is not None else None
            _append_error(
                summary,
                f"{node_id}/{role}: mesh data name expected {expected_data_name}, "
                f"found {actual_data_name}",
            )
        if obj.data is not None and obj.data.users != 1:
            _append_error(
                summary,
                f"{node_id}/{role}: unique mesh ownership required, "
                f"data {obj.data.name} has {obj.data.users} users",
            )
        if obj.data is not None and obj.data.has_custom_normals:
            _append_error(
                summary,
                f"{node_id}/{role}: custom split normals are forbidden; use canonical smooth/sharp topology",
            )
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
        if role == "accent":
            signature, axis, amount = SPECS.NODE_MOTIONS[node_id]
            accent_expected = {
                "econ_signature": signature,
                "econ_axis": axis,
                "econ_amount": amount,
            }
            for key, expected in accent_expected.items():
                actual = obj.get(key)
                if isinstance(expected, float):
                    valid = isinstance(actual, (int, float)) and math.isclose(
                        float(actual), expected, rel_tol=0.0, abs_tol=1.0e-6
                    )
                else:
                    valid = actual == expected
                if not valid:
                    _append_error(
                        summary,
                        f"{node_id}/accent {key} expected {expected!r}, found {actual!r}",
                    )
            pivot = obj.get("econ_pivot")
            expected_pivot = (
                accent_contract.get("pivotLabel") if accent_contract is not None else None
            )
            if pivot != expected_pivot:
                _append_error(
                    summary,
                    f"{node_id}/accent econ_pivot expected {expected_pivot!r}, found {pivot!r}",
                )
        if not all(
            math.isclose(
                float(obj.matrix_parent_inverse[row][column]),
                float(Matrix.Identity(4)[row][column]),
                rel_tol=0.0,
                abs_tol=1.0e-6,
            )
            for row in range(4)
            for column in range(4)
        ):
            _append_error(summary, f"{node_id}/{role} matrix_parent_inverse must be identity")
        expected_location = (
            accent_contract.get("blenderTranslation")
            if role == "accent" and accent_contract is not None
            else (0.0, 0.0, 0.0)
        )
        if expected_location is None or not _components_close(obj.location, expected_location):
            _append_error(
                summary,
                f"{node_id}/{role} child translation expected {expected_location!r}, "
                f"found {tuple(round(float(value), 9) for value in obj.location)!r}",
            )
        rotation_identity, scale_identity = _identity_child_rotation_and_scale(obj)
        if not rotation_identity:
            _append_error(summary, f"{node_id}/{role} child rotation must be identity")
        if not scale_identity:
            _append_error(summary, f"{node_id}/{role} child scale must be identity")
        if obj.data is not None:
            obj.data.calc_loop_triangles()
            raw_triangles = len(obj.data.loop_triangles)
        else:
            raw_triangles = 0
        metrics = _evaluated_mesh_metrics(
            obj, depsgraph, summary, f"{node_id}/{role}"
        )
        metrics_by_role[role] = metrics
        geometry_by_role[role] = _scene_geometry_contract(
            metrics["triangleVerticesLocal"]
        )
        bevel_modifiers = [modifier for modifier in obj.modifiers if modifier.type == "BEVEL"]
        if len(bevel_modifiers) != 1:
            _append_error(
                summary,
                f"{node_id}/{role}: requires exactly one real Bevel modifier, "
                f"found {len(bevel_modifiers)}",
            )
            bevel_width = 0.0
            bevel_segments = 0
            bevel_limit_method = ""
            tagged_edges = 0
        else:
            bevel = bevel_modifiers[0]
            bevel_width = float(bevel.width)
            bevel_segments = int(bevel.segments)
            bevel_limit_method = str(bevel.limit_method)
            if not 0.03 <= bevel_width <= 0.05:
                _append_error(
                    summary,
                    f"{node_id}/{role}: Bevel width {bevel_width:.6f} outside 0.03..0.05",
                )
            if bevel_segments != 3:
                _append_error(
                    summary,
                    f"{node_id}/{role}: Bevel segments must equal 3, found {bevel_segments}",
                )
            if not bevel.show_viewport or not bevel.show_render:
                _append_error(summary, f"{node_id}/{role}: Bevel modifier must be evaluated")
            if bevel_limit_method != "WEIGHT":
                _append_error(
                    summary,
                    f"{node_id}/{role}: Bevel limit_method must be WEIGHT, "
                    f"found {bevel_limit_method}",
                )
            tagged_edges = int(obj.get("econ_bevel_tagged_edges", 0))
            weight_name = str(getattr(bevel, "edge_weight", ""))
            weight_attribute = obj.data.attributes.get(weight_name) if weight_name else None
            weights = (
                [float(item.value) for item in weight_attribute.data]
                if weight_attribute is not None
                else []
            )
            fractional_weights = [
                value
                for value in weights
                if not math.isclose(
                    value, 0.0, rel_tol=0.0, abs_tol=BEVEL_WEIGHT_TOLERANCE
                )
                and not math.isclose(
                    value, 1.0, rel_tol=0.0, abs_tol=BEVEL_WEIGHT_TOLERANCE
                )
            ]
            if fractional_weights:
                sample = ", ".join(f"{value:.6f}" for value in fractional_weights[:4])
                _append_error(
                    summary,
                    f"{node_id}/{role}: bevel weights must be binary 0 or 1 "
                    f"within {BEVEL_WEIGHT_TOLERANCE:g}; found {len(fractional_weights)} "
                    f"fractional values [{sample}]",
                )
            weighted_edges = sum(
                1
                for value in weights
                if math.isclose(
                    value, 1.0, rel_tol=0.0, abs_tol=BEVEL_WEIGHT_TOLERANCE
                )
            )
            if tagged_edges <= 0 or weighted_edges != tagged_edges:
                _append_error(
                    summary,
                    f"{node_id}/{role}: bevel tagged edge count invalid "
                    f"metadata={tagged_edges}, weighted={weighted_edges}",
                )
        minimum_tagged_edges = SPECS.BEVEL_TAGGED_EDGE_MINIMUMS.get(
            node_id, {}
        ).get(role)
        if minimum_tagged_edges is None:
            _append_error(
                summary,
                f"{node_id}/{role}: missing model-specific bevel coverage contract",
            )
            minimum_tagged_edges = 0
        elif tagged_edges < minimum_tagged_edges:
            _append_error(
                summary,
                f"{node_id}/{role}: bevel coverage minimum {minimum_tagged_edges} "
                f"tagged edges, found {tagged_edges}",
            )
        evaluated_delta = int(metrics["triangles"] - raw_triangles)
        if evaluated_delta <= 0:
            _append_error(
                summary,
                f"{node_id}/{role}: Bevel modifier produced no evaluated triangle geometry",
            )
        bevels_by_role[role] = {
            "width": round(bevel_width, 6),
            "segments": bevel_segments,
            "evaluatedTriangleDelta": evaluated_delta,
            "limitMethod": bevel_limit_method,
            "taggedEdges": tagged_edges,
            "minimumTaggedEdges": minimum_tagged_edges,
        }

    if set(metrics_by_role) != {"body", "accent"}:
        return None
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
    if node_id in MODEL_TRIANGLE_BANDS:
        minimum, maximum = MODEL_TRIANGLE_BANDS[node_id]
        if not minimum <= model_triangles <= maximum:
            _append_error(
                summary,
                f"{node_id}: triangles {model_triangles} outside model band {minimum}..{maximum}",
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
    if node_id == "oil":
        accent_extent = accent["extent"]
        if accent_extent[1] >= 0.45 * min(accent_extent[0], accent_extent[2]):
            _append_error(
                summary,
                "oil/accent: side valve must lie in Blender XZ with a thin Y normal "
                f"for exported rotate-z, found extents={tuple(round(float(v), 6) for v in accent_extent)}",
            )
    thin_axis_error = _thin_axis_contract_error(node_id, accent["extent"])
    if thin_axis_error is not None:
        _append_error(summary, f"{node_id}/accent: {thin_axis_error}")

    silhouette = root.get("econ_silhouette")
    if not isinstance(silhouette, str) or len(silhouette.split(";")) != 3:
        _append_error(
            summary,
            f"{node_id}: econ_silhouette must contain three semicolon-delimited view clauses",
        )
        silhouette = ""

    triangle_vertices = body["triangleVertices"] + accent["triangleVertices"]
    occupancy_masks = {
        view: _projected_occupancy_mask(triangle_vertices, axes)
        for view, axes in OCCUPANCY_VIEW_AXES.items()
    }
    blender_translation = tuple(
        float(value) for value in accent_contract["blenderTranslation"]
    )
    gltf_translation = _blender_to_gltf_translation(blender_translation)
    summary["models"][node_id] = {
        "bodyTriangles": int(body["triangles"]),
        "accentTriangles": int(accent["triangles"]),
        "triangles": model_triangles,
        "accentAreaRatio": round(accent_ratio, 6),
        "radius": round(float(radius), 6),
        "centerError": round(float(center.length), 6),
        "primitives": 2,
        "silhouetteSignature": silhouette,
        "occupancyMaskSha256": {
            view: _occupancy_digest(mask) for view, mask in occupancy_masks.items()
        },
        "occupancyPixels": {
            view: len(mask) for view, mask in occupancy_masks.items()
        },
        "bevels": bevels_by_role,
        "geometryByRole": geometry_by_role,
        "accentExtents": [round(float(value), 6) for value in accent["extent"]],
        "accentContract": {
            "pivotLabel": accent_contract["pivotLabel"],
            "blenderTranslation": [round(value, 9) for value in blender_translation],
            "gltfTranslation": [round(value, 9) for value in gltf_translation],
        },
    }
    summary["triangles"] += model_triangles
    summary["primitives"] += 2
    return occupancy_masks


def validate_scene(
    scope: str,
    *,
    enforce_frozen_roots: bool = True,
) -> tuple[dict, list[bpy.types.Object]]:
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
    roots = _check_global_scene_contract(
        summary,
        enforce_frozen_roots=enforce_frozen_roots,
    )
    selected_roots = _scope_roots(roots, scope, summary)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    masks_by_id: dict[str, dict[str, set[int]]] = {}
    for root in selected_roots:
        masks = _validate_model(root, depsgraph, summary)
        if masks is not None:
            masks_by_id[root.name] = masks
    for first_id, second_id in combinations(masks_by_id, 2):
        by_view = {
            view: _occupancy_iou(
                masks_by_id[first_id][view],
                masks_by_id[second_id][view],
            )
            for view in OCCUPANCY_VIEW_AXES
        }
        if all(value >= OCCUPANCY_IOU_FAILURE for value in by_view.values()):
            rendered = ", ".join(
                f"{view}={value:.6f}" for view, value in by_view.items()
            )
            _append_error(
                summary,
                f"three-view silhouette IoU failure {first_id}/{second_id}: {rendered}",
            )
    if summary["triangles"] > MAX_TOTAL_TRIANGLES:
        _append_error(
            summary,
            f"total triangles {summary['triangles']} exceed {MAX_TOTAL_TRIANGLES}",
        )
    if scope == "proof":
        if summary["triangles"] > PROOF_HARD_TRIANGLES_MAX:
            _append_error(
                summary,
                f"proof triangles {summary['triangles']} exceed hard cap {PROOF_HARD_TRIANGLES_MAX}",
            )
        if not PROOF_TOTAL_TRIANGLES_MIN <= summary["triangles"] <= PROOF_TOTAL_TRIANGLES_MAX:
            _append_error(
                summary,
                "proof triangles "
                f"{summary['triangles']} outside {PROOF_TOTAL_TRIANGLES_MIN}..{PROOF_TOTAL_TRIANGLES_MAX}",
            )
    return summary, selected_roots


def _read_glb(path: Path) -> tuple[dict, bytes]:
    raw = path.read_bytes()
    if len(raw) < 20:
        raise ValueError("GLB is shorter than its header and JSON chunk")
    magic, version, declared_length = struct.unpack_from("<4sII", raw, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(raw):
        raise ValueError(
            f"invalid GLB header magic={magic!r}, version={version}, declared={declared_length}, actual={len(raw)}"
        )
    chunks: list[tuple[int, bytes]] = []
    offset = 12
    while offset < len(raw):
        if offset + 8 > len(raw):
            raise ValueError(f"truncated GLB chunk header at byte {offset}")
        chunk_length, chunk_type = struct.unpack_from("<II", raw, offset)
        if chunk_length % 4 != 0:
            raise ValueError(f"GLB chunk length {chunk_length} is not 4-byte aligned")
        start = offset + 8
        end = start + chunk_length
        if end > len(raw):
            raise ValueError(
                f"GLB chunk at byte {offset} declares {chunk_length} bytes beyond file length"
            )
        chunks.append((chunk_type, raw[start:end]))
        offset = end
    if offset != len(raw):
        raise ValueError(f"GLB chunk parsing stopped at {offset}, file length is {len(raw)}")
    if not chunks or chunks[0][0] != JSON_CHUNK_TYPE:
        raise ValueError("first GLB chunk is not JSON")
    json_chunks = [payload for chunk_type, payload in chunks if chunk_type == JSON_CHUNK_TYPE]
    bin_chunks = [payload for chunk_type, payload in chunks if chunk_type == BIN_CHUNK_TYPE]
    unknown_types = sorted(
        {chunk_type for chunk_type, _payload in chunks}
        - {JSON_CHUNK_TYPE, BIN_CHUNK_TYPE}
    )
    if len(json_chunks) != 1:
        raise ValueError(f"expected exactly one JSON chunk, found {len(json_chunks)}")
    if len(bin_chunks) != 1:
        raise ValueError(f"expected exactly one BIN chunk, found {len(bin_chunks)}")
    if unknown_types:
        raise ValueError(f"unexpected GLB chunk types: {unknown_types}")
    payload = json_chunks[0].rstrip(b" \t\r\n\x00")
    return json.loads(payload.decode("utf-8")), bin_chunks[0]


def _node_descendants(
    nodes: list[dict],
    root_index: int,
    summary: dict,
    label: str,
) -> list[int]:
    result: list[int] = []
    visited = {root_index}

    def visit(index: int, ancestors: set[int]) -> None:
        children = nodes[index].get("children", [])
        if not isinstance(children, list):
            _append_error(summary, f"GLB {label}: node {index} children must be an array")
            return
        for child in children:
            if not isinstance(child, int) or not 0 <= child < len(nodes):
                _append_error(summary, f"GLB {label}: invalid child index {child!r} on node {index}")
                continue
            if child in ancestors:
                _append_error(summary, f"GLB {label}: cyclic node graph at child {child}")
                continue
            if child in visited:
                _append_error(summary, f"GLB {label}: node {child} is reused in the node graph")
                continue
            visited.add(child)
            result.append(child)
            visit(child, ancestors | {child})

    if not isinstance(root_index, int) or not 0 <= root_index < len(nodes):
        _append_error(summary, f"GLB {label}: invalid root index {root_index!r}")
        return result
    visit(root_index, {root_index})
    return result


def _validate_binary_layout(gltf: dict, bin_payload: bytes, summary: dict) -> None:
    buffers = gltf.get("buffers", [])
    if not isinstance(buffers, list) or len(buffers) != 1:
        _append_error(summary, f"GLB expected exactly one buffer, found {len(buffers) if isinstance(buffers, list) else 'invalid'}")
        return
    buffer = buffers[0]
    if buffer.get("uri") is not None:
        _append_error(summary, "GLB buffer 0 must use the embedded BIN chunk, not a URI")
    declared_length = buffer.get("byteLength")
    if not isinstance(declared_length, int) or declared_length <= 0:
        _append_error(summary, f"GLB buffer byteLength must be a positive integer, found {declared_length!r}")
        return
    if declared_length > len(bin_payload):
        _append_error(
            summary,
            f"GLB buffer byteLength {declared_length} exceeds BIN payload {len(bin_payload)}",
        )
    if len(bin_payload) - declared_length not in {0, 1, 2, 3}:
        _append_error(
            summary,
            f"GLB BIN padding is invalid: declared={declared_length}, payload={len(bin_payload)}",
        )

    buffer_views = gltf.get("bufferViews", [])
    if not isinstance(buffer_views, list):
        _append_error(summary, "GLB bufferViews must be an array")
        return
    for view_index, view in enumerate(buffer_views):
        buffer_index = view.get("buffer")
        byte_offset = view.get("byteOffset", 0)
        byte_length = view.get("byteLength")
        if buffer_index != 0:
            _append_error(summary, f"GLB bufferView {view_index} references invalid buffer {buffer_index!r}")
        if not isinstance(byte_offset, int) or byte_offset < 0:
            _append_error(summary, f"GLB bufferView {view_index} has invalid byteOffset {byte_offset!r}")
            continue
        if not isinstance(byte_length, int) or byte_length <= 0:
            _append_error(summary, f"GLB bufferView {view_index} has invalid byteLength {byte_length!r}")
            continue
        if byte_offset + byte_length > declared_length:
            _append_error(
                summary,
                f"GLB bufferView {view_index} range {byte_offset}..{byte_offset + byte_length} "
                f"exceeds buffer byteLength {declared_length}",
            )
        if byte_offset + byte_length > len(bin_payload):
            _append_error(
                summary,
                f"GLB bufferView {view_index} range exceeds actual BIN payload {len(bin_payload)}",
            )
        stride = view.get("byteStride")
        if stride is not None and (
            not isinstance(stride, int)
            or stride < 4
            or stride > 252
            or stride % 4 != 0
        ):
            _append_error(summary, f"GLB bufferView {view_index} has invalid byteStride {stride!r}")

    accessors = gltf.get("accessors", [])
    if not isinstance(accessors, list):
        _append_error(summary, "GLB accessors must be an array")
        return
    for accessor_index, accessor in enumerate(accessors):
        if accessor.get("sparse") is not None:
            _append_error(summary, f"GLB accessor {accessor_index} sparse payloads are forbidden")
        view_index = accessor.get("bufferView")
        if not isinstance(view_index, int) or not 0 <= view_index < len(buffer_views):
            _append_error(summary, f"GLB accessor {accessor_index} references invalid bufferView {view_index!r}")
            continue
        view = buffer_views[view_index]
        component_type = accessor.get("componentType")
        accessor_type = accessor.get("type")
        count = accessor.get("count")
        byte_offset = accessor.get("byteOffset", 0)
        component_size = COMPONENT_SIZES.get(component_type)
        component_count = TYPE_COMPONENTS.get(accessor_type)
        if component_size is None:
            _append_error(summary, f"GLB accessor {accessor_index} has invalid componentType {component_type!r}")
            continue
        if component_count is None:
            _append_error(summary, f"GLB accessor {accessor_index} has invalid type {accessor_type!r}")
            continue
        if not isinstance(count, int) or count <= 0:
            _append_error(summary, f"GLB accessor {accessor_index} has invalid count {count!r}")
            continue
        if not isinstance(byte_offset, int) or byte_offset < 0:
            _append_error(summary, f"GLB accessor {accessor_index} has invalid byteOffset {byte_offset!r}")
            continue
        element_size = component_size * component_count
        stride = view.get("byteStride", element_size)
        if not isinstance(stride, int) or stride < element_size or stride % component_size != 0:
            _append_error(
                summary,
                f"GLB accessor {accessor_index} has invalid stride {stride!r} for element size {element_size}",
            )
            continue
        required = byte_offset + (count - 1) * stride + element_size
        view_length = view.get("byteLength")
        if not isinstance(view_length, int) or required > view_length:
            _append_error(
                summary,
                f"GLB accessor {accessor_index} range requires {required} bytes "
                f"inside bufferView {view_index} length {view_length!r}",
            )
        if byte_offset % component_size != 0:
            _append_error(
                summary,
                f"GLB accessor {accessor_index} byteOffset {byte_offset} is not component-aligned",
            )


def _decode_accessor(
    gltf: dict,
    bin_payload: bytes,
    accessor_index: int,
    summary: dict,
    label: str,
):
    accessors = gltf.get("accessors", [])
    buffer_views = gltf.get("bufferViews", [])
    if not isinstance(accessor_index, int) or not 0 <= accessor_index < len(accessors):
        _append_error(summary, f"GLB {label}: invalid accessor {accessor_index!r}")
        return None
    accessor = accessors[accessor_index]
    if accessor.get("sparse") is not None:
        _append_error(summary, f"GLB {label}: sparse accessors are forbidden")
        return None
    view_index = accessor.get("bufferView")
    if not isinstance(view_index, int) or not 0 <= view_index < len(buffer_views):
        return None
    view = buffer_views[view_index]
    component_type = accessor.get("componentType")
    component_count = TYPE_COMPONENTS.get(accessor.get("type"))
    component_size = COMPONENT_SIZES.get(component_type)
    component_format = COMPONENT_FORMATS.get(component_type)
    count = accessor.get("count")
    if (
        component_count is None
        or component_size is None
        or component_format is None
        or not isinstance(count, int)
        or count <= 0
    ):
        return None
    element_size = component_size * component_count
    stride = view.get("byteStride", element_size)
    view_offset = view.get("byteOffset", 0)
    accessor_offset = accessor.get("byteOffset", 0)
    if not all(
        isinstance(value, int) and value >= 0
        for value in (stride, view_offset, accessor_offset)
    ) or stride < element_size:
        return None
    unpack_format = "<" + component_format * component_count
    values = []
    try:
        for item_index in range(count):
            offset = view_offset + accessor_offset + item_index * stride
            if offset + element_size > len(bin_payload):
                raise ValueError(
                    f"item {item_index} range {offset}..{offset + element_size} "
                    f"exceeds BIN payload {len(bin_payload)}"
                )
            decoded = struct.unpack_from(unpack_format, bin_payload, offset)
            values.append(decoded[0] if component_count == 1 else decoded)
    except (ValueError, struct.error) as exc:
        _append_error(summary, f"GLB {label}: accessor decode failed: {exc}")
        return None
    return values


def _primitive_payload_geometry_contract(
    gltf: dict,
    bin_payload: bytes,
    primitive: dict,
    summary: dict,
    label: str,
) -> dict | None:
    position_accessor = primitive.get("attributes", {}).get("POSITION")
    index_accessor = primitive.get("indices")
    positions = _decode_accessor(
        gltf, bin_payload, position_accessor, summary, f"{label} POSITION"
    )
    indices = _decode_accessor(
        gltf, bin_payload, index_accessor, summary, f"{label} INDEX"
    )
    if positions is None or indices is None:
        return None
    if len(indices) % 3 != 0:
        return None
    triangles = []
    for offset in range(0, len(indices), 3):
        triangle = []
        for raw_index in indices[offset : offset + 3]:
            if not isinstance(raw_index, int) or not 0 <= raw_index < len(positions):
                _append_error(
                    summary,
                    f"GLB {label}: INDEX payload value {raw_index!r} outside "
                    f"POSITION count {len(positions)}",
                )
                return None
            position = positions[raw_index]
            if not isinstance(position, tuple) or len(position) != 3:
                _append_error(summary, f"GLB {label}: POSITION payload is not VEC3")
                return None
            triangle.append(position)
        triangles.append(tuple(triangle))
    try:
        return _canonical_geometry_contract(triangles)
    except ValueError as exc:
        _append_error(summary, f"GLB {label}: payload geometry invalid: {exc}")
        return None


def _validate_primitive_normal_payload(
    gltf: dict,
    bin_payload: bytes,
    primitive: dict,
    summary: dict,
    label: str,
) -> None:
    attributes = primitive.get("attributes", {})
    positions = _decode_accessor(
        gltf,
        bin_payload,
        attributes.get("POSITION"),
        summary,
        f"{label} POSITION",
    )
    normals = _decode_accessor(
        gltf,
        bin_payload,
        attributes.get("NORMAL"),
        summary,
        f"{label} NORMAL",
    )
    if positions is None or normals is None:
        return
    if len(normals) != len(positions):
        _append_error(
            summary,
            f"GLB {label} NORMAL count {len(normals)} must equal POSITION count {len(positions)}",
        )
        return
    invalid = []
    for index, normal in enumerate(normals):
        if not isinstance(normal, tuple) or len(normal) != 3:
            invalid.append(index)
            continue
        components = tuple(float(value) for value in normal)
        length = math.sqrt(sum(value * value for value in components))
        if not all(math.isfinite(value) for value in components) or not 0.9 <= length <= 1.1:
            invalid.append(index)
    if invalid:
        _append_error(
            summary,
            f"GLB {label} NORMAL payload must contain unit vectors; "
            f"invalid={len(invalid)} firstIndex={invalid[0]}",
        )


def validate_glb(path: Path, expected_ids: Iterable[str], base_summary: dict | None = None) -> dict:
    summary = base_summary if base_summary is not None else _fresh_summary("glb")
    summary["bytes"] = path.stat().st_size if path.is_file() else 0
    if not path.is_file():
        _append_error(summary, f"GLB does not exist: {path}")
        return summary
    if summary["bytes"] > MAX_GLB_BYTES:
        _append_error(summary, f"GLB bytes {summary['bytes']} exceed {MAX_GLB_BYTES}")
    if summary.get("scope") == "proof" and summary["bytes"] > PROOF_MAX_GLB_BYTES:
        _append_error(
            summary,
            f"proof GLB bytes {summary['bytes']} exceed {PROOF_MAX_GLB_BYTES}",
        )
    try:
        gltf, bin_payload = _read_glb(path)
    except Exception as exc:
        _append_error(summary, f"GLB parse failed: {exc}")
        return summary
    _validate_binary_layout(gltf, bin_payload, summary)

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
        if not isinstance(active_root_indices, list):
            _append_error(summary, "GLB active scene nodes must be an array")
            active_root_indices = []
    for index in active_root_indices:
        _node_descendants(nodes, index, summary, f"active scene root {index!r}")
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
    used_mesh_indices: dict[int, str] = {}
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
        expected_silhouette = summary.get("models", {}).get(node_id, {}).get(
            "silhouetteSignature"
        )
        actual_silhouette = root_extras.get("econ_silhouette")
        if expected_silhouette and actual_silhouette != expected_silhouette:
            _append_error(
                summary,
                f"GLB {node_id}: econ_silhouette expected {expected_silhouette!r}, "
                f"found {actual_silhouette!r}",
            )

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
            for index in _node_descendants(nodes, root_index, summary, node_id)
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
            node_extras = node.get("extras", {})
            role = node_extras.get("econ_role")
            roles.append(role)
            mesh_index = node["mesh"]
            if not isinstance(mesh_index, int) or not 0 <= mesh_index < len(meshes):
                _append_error(summary, f"GLB {node_id}: invalid mesh index {mesh_index}")
                continue
            owner = used_mesh_indices.get(mesh_index)
            if owner is not None:
                _append_error(
                    summary,
                    f"GLB {node_id}/{role}: mesh index reused from {owner}: {mesh_index}",
                )
            else:
                used_mesh_indices[mesh_index] = f"{node_id}/{role}"
            expected_mesh_name = f"MESH__{node_id}__{role}"
            actual_mesh_name = meshes[mesh_index].get("name")
            if actual_mesh_name != expected_mesh_name:
                _append_error(
                    summary,
                    f"GLB {node_id}/{role}: mesh name expected {expected_mesh_name}, "
                    f"found {actual_mesh_name}",
                )
            if role == "accent":
                accent_expected = {
                    "econ_signature": signature,
                    "econ_axis": axis,
                    "econ_amount": amount,
                }
                for key, expected in accent_expected.items():
                    actual = node_extras.get(key)
                    if isinstance(expected, float):
                        valid = isinstance(actual, (int, float)) and math.isclose(
                            float(actual), expected, rel_tol=0.0, abs_tol=1.0e-6
                        )
                    else:
                        valid = actual == expected
                    if not valid:
                        _append_error(
                            summary,
                            f"GLB {node_id}/accent {key} expected {expected!r}, found {actual!r}",
                        )
                scene_contract = summary.get("models", {}).get(node_id, {}).get(
                    "accentContract", {}
                )
                expected_pivot = scene_contract.get("pivotLabel")
                pivot = node_extras.get("econ_pivot")
                if pivot != expected_pivot:
                    _append_error(
                        summary,
                        f"GLB {node_id}/accent econ_pivot expected {expected_pivot!r}, "
                        f"found {pivot!r}",
                    )
            expected_translation = (
                summary.get("models", {})
                .get(node_id, {})
                .get("accentContract", {})
                .get("gltfTranslation", [0.0, 0.0, 0.0])
                if role == "accent"
                else [0.0, 0.0, 0.0]
            )
            actual_translation = node.get("translation", [0.0, 0.0, 0.0])
            if not _components_close(actual_translation, expected_translation):
                _append_error(
                    summary,
                    f"GLB {node_id}/{role} translation expected {expected_translation!r}, "
                    f"found {actual_translation!r}",
                )
            if "matrix" in node:
                _append_error(summary, f"GLB {node_id}/{role} child matrix is forbidden")
            rotation = node.get("rotation", [0.0, 0.0, 0.0, 1.0])
            if not _components_close(rotation, [0.0, 0.0, 0.0, 1.0]):
                _append_error(summary, f"GLB {node_id}/{role} rotation must be identity")
            scale = node.get("scale", [1.0, 1.0, 1.0])
            if not _components_close(scale, [1.0, 1.0, 1.0]):
                _append_error(summary, f"GLB {node_id}/{role} scale must be identity")
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
                    if materials[material_index].get("doubleSided", False) is not False:
                        _append_error(
                            summary,
                            f"GLB {node_id}/{role}: opaque material must have doubleSided=false",
                        )
                attributes = set(primitive.get("attributes", {}))
                if attributes != {"POSITION", "NORMAL"}:
                    _append_error(summary, f"GLB {node_id}/{role}: unexpected attributes {sorted(attributes)}")
                for semantic, accessor_index in primitive.get("attributes", {}).items():
                    if not isinstance(accessor_index, int) or not 0 <= accessor_index < len(accessors):
                        _append_error(
                            summary,
                            f"GLB {node_id}/{role}: {semantic} references invalid accessor {accessor_index!r}",
                        )
                        continue
                    accessor = accessors[accessor_index]
                    if semantic in {"POSITION", "NORMAL"} and (
                        accessor.get("type") != "VEC3"
                        or accessor.get("componentType") != 5126
                    ):
                        _append_error(
                            summary,
                            f"GLB {node_id}/{role}: {semantic} accessor must be float VEC3",
                        )
                    if semantic == "POSITION" and node_id == "oil" and role == "accent":
                        minimum = accessor.get("min")
                        maximum = accessor.get("max")
                        if (
                            not isinstance(minimum, list)
                            or not isinstance(maximum, list)
                            or len(minimum) != 3
                            or len(maximum) != 3
                        ):
                            _append_error(
                                summary,
                                "GLB oil/accent POSITION accessor requires three-axis min/max",
                            )
                        else:
                            extent = [float(maximum[i]) - float(minimum[i]) for i in range(3)]
                            if extent[2] >= 0.45 * min(extent[0], extent[1]):
                                _append_error(
                                    summary,
                                    "GLB oil/accent wheel must be thin on exported Z for rotate-z, "
                                    f"found extents={tuple(round(value, 6) for value in extent)}",
                                )
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
                actual_geometry = _primitive_payload_geometry_contract(
                    gltf,
                    bin_payload,
                    primitive,
                    summary,
                    f"{node_id}/{role}",
                )
                _validate_primitive_normal_payload(
                    gltf,
                    bin_payload,
                    primitive,
                    summary,
                    f"{node_id}/{role}",
                )
                expected_geometry = (
                    summary.get("models", {})
                    .get(node_id, {})
                    .get("geometryByRole", {})
                    .get(role)
                )
                if actual_geometry is not None and expected_geometry is None:
                    _append_error(
                        summary,
                        f"GLB {node_id}/{role}: missing evaluated-scene geometry fingerprint",
                    )
                elif actual_geometry is not None and expected_geometry is not None:
                    if actual_geometry["sha256"] != expected_geometry["sha256"]:
                        _append_error(
                            summary,
                            f"GLB {node_id}/{role} POSITION/INDEX payload fingerprint mismatch "
                            f"expected={expected_geometry['sha256']} "
                            f"actual={actual_geometry['sha256']}",
                        )
                    if (
                        actual_geometry["boundsQuantized"]
                        != expected_geometry["boundsQuantized"]
                    ):
                        _append_error(
                            summary,
                            f"GLB {node_id}/{role} POSITION payload bounds mismatch "
                            f"expected={expected_geometry['boundsQuantized']} "
                            f"actual={actual_geometry['boundsQuantized']}",
                        )
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
    # Geometry fingerprints are an internal scene-to-payload comparison cache.
    # Omitting them from the one-line CLI report keeps Blender's shutdown banner
    # from being coalesced onto an oversized JSON line on Windows stdout.
    rendered = dict(summary)
    rendered["models"] = {
        node_id: {
            key: value
            for key, value in model.items()
            if key != "geometryByRole"
        }
        for node_id, model in summary.get("models", {}).items()
    }
    print(json.dumps(rendered, ensure_ascii=True, sort_keys=True, separators=(",", ":")))


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
