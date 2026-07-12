"""Reusable deterministic batch authoring for Precision Macro Instruments."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import struct
from typing import Callable, Iterable, Mapping

import bpy

from hard_surface import ModelGeometry, finalize_model


Builder = Callable[[], ModelGeometry]
_VALIDATOR = None


def _stable_value(value):
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return round(value, 9)
    if hasattr(value, "to_tuple"):
        value = value.to_tuple()
    if not isinstance(value, (str, bytes)) and hasattr(value, "__iter__"):
        try:
            return [_stable_value(item) for item in value]
        except (TypeError, ValueError):
            return None
    return None


def _load_validator():
    global _VALIDATOR
    if _VALIDATOR is not None:
        return _VALIDATOR
    module_path = Path(__file__).with_name("validate-econ-node-library.py")
    spec = importlib.util.spec_from_file_location("econ_batch_validator", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load validator: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _VALIDATOR = module
    return module


def _require_valid_ready_scene(
    label: str,
    *,
    enforce_frozen_roots: bool = True,
) -> dict:
    summary, _roots = _load_validator().validate_scene(
        "ready",
        enforce_frozen_roots=enforce_frozen_roots,
    )
    if summary["errors"]:
        rendered = " | ".join(summary["errors"])
        raise RuntimeError(f"{label} failed validation: {rendered}")
    return summary


def _require_frozen_contracts(
    specs,
    label: str,
    *,
    enforce_roots: bool = True,
) -> None:
    material_hashes = getattr(specs, "MATERIAL_CONTRACT_HASHES", {})
    for material_name, expected in material_hashes.items():
        material = bpy.data.materials.get(material_name)
        if material is None:
            raise RuntimeError(f"{label} failed frozen contract: missing {material_name}")
        actual = snapshot_material_contract(material)
        if actual != expected:
            raise RuntimeError(
                f"{label} failed frozen contract: {material_name} PBR/node hash drift "
                f"expected={expected} actual={actual}"
            )

    root_hashes = getattr(specs, "ROOT_CONTRACT_HASHES", {})
    if not root_hashes or not enforce_roots:
        return
    for node_id in specs.CANONICAL_IDS:
        root = bpy.data.objects.get(node_id)
        if root is None or not bool(root.get("econ_ready", False)):
            continue
        expected = root_hashes.get(node_id)
        if expected is None:
            raise RuntimeError(f"{label} failed frozen contract: no root hash for {node_id}")
        actual = snapshot_root_contract(root)
        if actual != expected:
            raise RuntimeError(
                f"{label} failed frozen contract: {node_id} root hash drift "
                f"expected={expected} actual={actual}"
            )


def canonical_requested_ids(
    raw_ids: str,
    allowed_ids: Iterable[str],
    canonical_ids: Iterable[str],
) -> tuple[str, ...]:
    """Parse a comma-separated request and return it in canonical order."""

    requested = tuple(node_id.strip() for node_id in raw_ids.split(",") if node_id.strip())
    allowed = set(allowed_ids)
    unknown = sorted(set(requested) - allowed)
    if unknown:
        raise ValueError(f"Unknown builder IDs: {unknown}")
    if len(requested) != len(set(requested)):
        raise ValueError(f"Duplicate builder IDs: {requested}")
    if not requested:
        raise ValueError("At least one builder ID is required")
    requested_set = set(requested)
    return tuple(node_id for node_id in canonical_ids if node_id in requested_set)


def _digest_value(digest: "hashlib._Hash", value) -> None:
    digest.update(json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    digest.update(b"\0")


def snapshot_material_contract(material: bpy.types.Material) -> str:
    """Hash stable material identity, surface settings, and Principled PBR values."""

    digest = hashlib.sha256()
    record = {
        "name": material.name,
        "diffuse_color": [round(float(value), 9) for value in material.diffuse_color],
        "metallic": round(float(material.metallic), 9),
        "roughness": round(float(material.roughness), 9),
        "use_nodes": bool(material.use_nodes),
        "use_backface_culling": bool(material.use_backface_culling),
        "surface_render_method": str(getattr(material, "surface_render_method", "")),
    }
    _digest_value(digest, record)
    _digest_value(
        digest,
        {
            key: material[key]
            for key in sorted(material.keys())
            if isinstance(material[key], (bool, int, float, str))
        },
    )
    if material.use_nodes and material.node_tree is not None:
        node_records = []
        for node in sorted(material.node_tree.nodes, key=lambda item: item.name):
            properties = {}
            for prop in node.bl_rna.properties:
                identifier = prop.identifier
                if identifier in {"rna_type", "name"} or getattr(prop, "is_readonly", False):
                    continue
                stable = _stable_value(getattr(node, identifier, None))
                if stable is not None:
                    properties[identifier] = stable
            inputs = []
            for index, socket in enumerate(node.inputs):
                socket_record = {
                    "index": index,
                    "identifier": socket.identifier,
                    "name": socket.name,
                    "is_linked": bool(socket.is_linked),
                }
                if hasattr(socket, "default_value"):
                    socket_record["default"] = _stable_value(socket.default_value)
                inputs.append(socket_record)
            outputs = []
            for index, socket in enumerate(node.outputs):
                socket_record = {
                    "index": index,
                    "identifier": socket.identifier,
                    "name": socket.name,
                    "is_linked": bool(socket.is_linked),
                }
                if hasattr(socket, "default_value"):
                    socket_record["default"] = _stable_value(socket.default_value)
                outputs.append(socket_record)
            node_records.append(
                {
                    "name": node.name,
                    "bl_idname": node.bl_idname,
                    "properties": properties,
                    "inputs": inputs,
                    "outputs": outputs,
                }
            )
        links = sorted(
            (
                link.from_node.name,
                link.from_socket.identifier,
                link.to_node.name,
                link.to_socket.identifier,
            )
            for link in material.node_tree.links
        )
        _digest_value(digest, {"nodes": node_records, "links": links})
    return digest.hexdigest()


def snapshot_root_contract(root: bpy.types.Object) -> str:
    """Hash a root's authored geometry and runtime-facing object contract."""

    digest = hashlib.sha256()
    objects = [root, *sorted(root.children_recursive, key=lambda item: item.name)]
    for obj in objects:
        _digest_value(digest, (obj.name, obj.type))
        _digest_value(digest, [round(float(value), 9) for row in obj.matrix_local for value in row])
        _digest_value(
            digest,
            {
                "color": _stable_value(obj.color),
                "display_type": obj.display_type,
                "hide_render": bool(obj.hide_render),
                "hide_viewport": bool(obj.hide_viewport),
                "visible_camera": bool(obj.visible_camera),
                "visible_shadow": bool(obj.visible_shadow),
            },
        )
        _digest_value(
            digest,
            {
                key: obj[key]
                for key in sorted(obj.keys())
                if isinstance(obj[key], (bool, int, float, str))
            },
        )
        if obj.type != "MESH" or obj.data is None:
            continue
        mesh = obj.data
        _digest_value(digest, mesh.name)
        _digest_value(
            digest,
            [slot.material.name if slot.material is not None else None for slot in obj.material_slots],
        )
        for vertex in mesh.vertices:
            digest.update(struct.pack("<ddd", *(float(value) for value in vertex.co)))
        for edge in mesh.edges:
            _digest_value(
                digest,
                {
                    "vertices": tuple(int(index) for index in edge.vertices),
                    "sharp": bool(getattr(edge, "use_edge_sharp", False)),
                },
            )
        for polygon in mesh.polygons:
            _digest_value(
                digest,
                {
                    "vertices": tuple(int(index) for index in polygon.vertices),
                    "material_index": int(polygon.material_index),
                    "smooth": bool(polygon.use_smooth),
                },
            )
        _digest_value(digest, {"has_custom_normals": bool(mesh.has_custom_normals)})
        for attribute in sorted(mesh.attributes, key=lambda item: item.name):
            if attribute.domain != "EDGE" or attribute.data_type != "FLOAT":
                continue
            _digest_value(digest, (attribute.name, attribute.domain, attribute.data_type))
            for item in attribute.data:
                digest.update(struct.pack("<d", float(item.value)))
        for modifier in obj.modifiers:
            record = {
                "name": modifier.name,
                "type": modifier.type,
                "show_in_editmode": bool(modifier.show_in_editmode),
                "show_on_cage": bool(modifier.show_on_cage),
                "show_render": bool(modifier.show_render),
                "show_viewport": bool(modifier.show_viewport),
            }
            if modifier.type == "BEVEL":
                for property_name in (
                    "affect",
                    "angle_limit",
                    "edge_weight",
                    "harden_normals",
                    "limit_method",
                    "loop_slide",
                    "mark_seam",
                    "mark_sharp",
                    "material",
                    "miter_inner",
                    "miter_outer",
                    "offset_type",
                    "profile",
                    "profile_type",
                    "segments",
                    "use_clamp_overlap",
                    "vmesh_method",
                    "width",
                ):
                    if not hasattr(modifier, property_name):
                        continue
                    stable = _stable_value(getattr(modifier, property_name))
                    if stable is not None:
                        record[property_name] = stable
            _digest_value(digest, record)
    return digest.hexdigest()


def open_output_if_needed(output: Path, label: str) -> None:
    current = Path(bpy.data.filepath).resolve() if bpy.data.filepath else None
    if current == output:
        return
    if not output.is_file():
        raise RuntimeError(f"{label} authoring requires an existing canonical scaffold: {output}")
    bpy.ops.wm.open_mainfile(filepath=str(output), load_ui=False)


def author_models(
    *,
    output: Path,
    specs,
    builders: Mapping[str, Builder],
    requested: Iterable[str],
    required_ready: Iterable[str] = (),
) -> dict:
    """Author one deterministic batch while proving all other roots unchanged."""

    requested = tuple(requested)
    required_ready = tuple(required_ready)
    missing_required = [
        node_id
        for node_id in required_ready
        if bpy.data.objects.get(node_id) is None
        or not bool(bpy.data.objects[node_id].get("econ_ready", False))
    ]
    if missing_required:
        raise RuntimeError(f"Required ready roots are missing: {missing_required}")
    _require_frozen_contracts(specs, "Existing ready library")
    _require_valid_ready_scene("Existing ready library")

    preserved = {
        node_id: snapshot_root_contract(bpy.data.objects[node_id])
        for node_id in specs.CANONICAL_IDS
        if node_id not in requested
    }
    preserved_materials = {
        material_name: snapshot_material_contract(bpy.data.materials[material_name])
        for material_name in specs.MATERIAL_NAMES
        if bpy.data.materials.get(material_name) is not None
    }
    body_material = bpy.data.materials.get("MAT__DARK_TITANIUM")
    if body_material is None:
        raise RuntimeError("MAT__DARK_TITANIUM is missing")

    authored = []
    for node_id in specs.CANONICAL_IDS:
        if node_id not in requested:
            continue
        root = bpy.data.objects.get(node_id)
        if root is None or root.type != "EMPTY":
            raise RuntimeError(f"Missing canonical EMPTY root: {node_id}")
        accent_name = specs.CATEGORY_MATERIALS[specs.NODE_CATEGORIES[node_id]]
        accent_material = bpy.data.materials.get(accent_name)
        if accent_material is None:
            raise RuntimeError(f"{node_id}: required accent material {accent_name} is missing")
        builder = builders.get(node_id)
        if builder is None:
            raise RuntimeError(f"{node_id}: builder is missing")
        finalize_model(root, builder(), body_material, accent_material)
        authored.append(node_id)

    for node_id, before in preserved.items():
        after = snapshot_root_contract(bpy.data.objects[node_id])
        if after != before:
            raise RuntimeError(f"{node_id}: unrelated root contract changed")
    for material_name, before in preserved_materials.items():
        after = snapshot_material_contract(bpy.data.materials[material_name])
        if after != before:
            raise RuntimeError(f"{material_name}: global material contract changed")

    _require_valid_ready_scene(
        "Authored ready library",
        enforce_frozen_roots=False,
    )
    _require_frozen_contracts(
        specs,
        "Authored ready library",
        enforce_roots=False,
    )

    staging = output.with_name(f".{output.stem}.authoring-stage{output.suffix}")
    if staging.exists():
        staging.unlink()
    try:
        bpy.ops.wm.save_as_mainfile(
            filepath=str(staging),
            compress=True,
            check_existing=False,
        )
        bpy.ops.wm.open_mainfile(filepath=str(staging), load_ui=False)
        _require_frozen_contracts(specs, "Serialized authored ready library")
        validated = _require_valid_ready_scene("Serialized authored ready library")
        ready_ids = [
            node_id
            for node_id in specs.CANONICAL_IDS
            if bool(bpy.data.objects[node_id].get("econ_ready", False))
        ]
        accent_translations = {
            node_id: [
                round(float(value), 9)
                for value in bpy.data.objects[f"{node_id}__accent"].location
            ]
            for node_id in authored
        }
        staging.replace(output)
    finally:
        if staging.exists():
            staging.unlink()
    return {
        "accentTranslations": accent_translations,
        "authored": authored,
        "output": str(output),
        "readyCount": validated["readyCount"],
        "readyIds": ready_ids,
    }
