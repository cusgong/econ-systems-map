"""Idempotently scaffold the node library and author the policy_rate slice."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
import sys
import warnings

import bmesh
import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from hard_surface import configure_precision_bevel, exposed_primary_edge_pairs  # noqa: E402


SCENE_NAME = "SCENE__ECON_NODE_LIBRARY"
MASTER_COLLECTION_NAME = "MASTER__ECON_NODE_LIBRARY"
POLICY_BEVEL_MINIMUM_ANGLE = math.radians(60.0)


def _load_specs():
    module_path = SCRIPT_DIR / "node-specs.py"
    spec = importlib.util.spec_from_file_location("econ_node_specs", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load node specs: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SPECS = _load_specs()


class MeshAssembler:
    def __init__(self) -> None:
        self.vertices: list[tuple[float, float, float]] = []
        self.faces: list[tuple[int, ...]] = []

    def add_vertex(self, vertex: tuple[float, float, float]) -> int:
        self.vertices.append(vertex)
        return len(self.vertices) - 1

    def add_face(self, *indices: int) -> None:
        self.faces.append(tuple(indices))

    def add_revolved_y(
        self,
        profile: list[tuple[float, float]],
        segments: int,
        back_y: float,
        front_y: float,
        outer_scale=None,
    ) -> None:
        """Add a closed surface of revolution around Blender's Y axis."""

        back_center = self.add_vertex((0.0, back_y, 0.0))
        rings: list[list[int]] = []
        for ring_index, (radius, y_value) in enumerate(profile):
            ring: list[int] = []
            for segment in range(segments):
                angle = math.tau * segment / segments
                scale = outer_scale(ring_index, segment) if outer_scale else 1.0
                ring.append(
                    self.add_vertex(
                        (
                            radius * scale * math.cos(angle),
                            y_value,
                            radius * scale * math.sin(angle),
                        )
                    )
                )
            rings.append(ring)

        for segment in range(segments):
            next_segment = (segment + 1) % segments
            self.add_face(back_center, rings[0][next_segment], rings[0][segment])
        for current, following in zip(rings, rings[1:]):
            for segment in range(segments):
                next_segment = (segment + 1) % segments
                self.add_face(
                    current[segment],
                    current[next_segment],
                    following[next_segment],
                    following[segment],
                )
        front_center = self.add_vertex((0.0, front_y, 0.0))
        for segment in range(segments):
            next_segment = (segment + 1) % segments
            self.add_face(rings[-1][segment], rings[-1][next_segment], front_center)

    def add_annulus_y(
        self,
        outer_radius: float,
        inner_radius: float,
        back_y: float,
        front_y: float,
        segments: int,
    ) -> None:
        rings: list[list[int]] = []
        for radius, y_value in (
            (outer_radius, back_y),
            (outer_radius, front_y),
            (inner_radius, front_y),
            (inner_radius, back_y),
        ):
            ring = []
            for segment in range(segments):
                angle = math.tau * segment / segments
                ring.append(
                    self.add_vertex((radius * math.cos(angle), y_value, radius * math.sin(angle)))
                )
            rings.append(ring)
        outer_back, outer_front, inner_front, inner_back = rings
        for segment in range(segments):
            next_segment = (segment + 1) % segments
            self.add_face(
                outer_back[segment],
                outer_back[next_segment],
                outer_front[next_segment],
                outer_front[segment],
            )
            self.add_face(
                outer_front[segment],
                outer_front[next_segment],
                inner_front[next_segment],
                inner_front[segment],
            )
            self.add_face(
                inner_front[segment],
                inner_front[next_segment],
                inner_back[next_segment],
                inner_back[segment],
            )
            self.add_face(
                inner_back[segment],
                inner_back[next_segment],
                outer_back[next_segment],
                outer_back[segment],
            )

    def add_extruded_polygon_y(
        self,
        points_xz: list[tuple[float, float]],
        back_y: float,
        front_y: float,
    ) -> None:
        back = [self.add_vertex((x, back_y, z)) for x, z in points_xz]
        front = [self.add_vertex((x, front_y, z)) for x, z in points_xz]
        self.add_face(*reversed(back))
        self.add_face(*front)
        count = len(points_xz)
        for index in range(count):
            following = (index + 1) % count
            self.add_face(back[index], back[following], front[following], front[index])


def _hex_color(value: str) -> tuple[float, float, float, float]:
    value = value.lstrip("#")
    return (
        int(value[0:2], 16) / 255.0,
        int(value[2:4], 16) / 255.0,
        int(value[4:6], 16) / 255.0,
        1.0,
    )


MATERIAL_STYLE = {
    "MAT__DARK_TITANIUM": ("#161b22", 0.82, 0.28),
    "MAT__SATIN_ALLOY": ("#8b96a5", 0.76, 0.24),
    "MAT__TECHNICAL_CERAMIC": ("#d7dce2", 0.05, 0.32),
    "MAT__ACCENT__POLICY": ("#35d0b0", 0.48, 0.24),
    "MAT__ACCENT__MONETARY": ("#4fd8ff", 0.48, 0.22),
    "MAT__ACCENT__ASSETS": ("#9d8cff", 0.42, 0.24),
    "MAT__ACCENT__PSYCHOLOGY": ("#ff9ecb", 0.34, 0.28),
    "MAT__ACCENT__REAL": ("#6fe38a", 0.38, 0.28),
    "MAT__ACCENT__PRICES": ("#ff7666", 0.38, 0.26),
    "MAT__ACCENT__COMMODITIES": ("#ffc857", 0.54, 0.24),
    "MAT__ACCENT__EXOGENOUS": ("#c678ff", 0.42, 0.25),
    "MAT__ACCENT__EXTERNAL": ("#5f8dff", 0.45, 0.24),
    "MAT__SMOKED_LENS": ("#202b36", 0.08, 0.18),
}


def _material(name: str) -> bpy.types.Material:
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    color, metallic, roughness = MATERIAL_STYLE[name]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        material.use_nodes = True
        material.use_backface_culling = True
    material.use_fake_user = True
    material.diffuse_color = _hex_color(color)
    nodes = material.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    if principled is None:
        raise RuntimeError(f"{name}: Principled BSDF node is unavailable")
    principled.inputs["Base Color"].default_value = _hex_color(color)
    principled.inputs["Metallic"].default_value = metallic
    principled.inputs["Roughness"].default_value = roughness
    return material


def _child_collection(parent: bpy.types.Collection, name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
    if collection.name not in {child.name for child in parent.children}:
        parent.children.link(collection)
    return collection


def _ensure_scene() -> bpy.types.Collection:
    scene = bpy.context.scene
    scene.name = SCENE_NAME
    master = _child_collection(scene.collection, MASTER_COLLECTION_NAME)
    assets = _child_collection(master, "00_ASSETS")
    _child_collection(master, "10_WIP")
    _child_collection(master, "90_QA")
    return assets


def _link_exclusively(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    if collection not in obj.users_collection:
        collection.objects.link(obj)
    for existing in list(obj.users_collection):
        if existing != collection:
            existing.objects.unlink(obj)


def _ensure_root(node_id: str, assets: bpy.types.Collection) -> bpy.types.Object:
    node_collection = _child_collection(assets, f"NODE__{node_id}")
    root = bpy.data.objects.get(node_id)
    created = root is None
    if root is None:
        root = bpy.data.objects.new(node_id, None)
        node_collection.objects.link(root)
    else:
        _link_exclusively(root, node_collection)
    root.empty_display_type = "CIRCLE"
    root.empty_display_size = 0.12
    root.location = (0.0, 0.0, 0.0)
    root.rotation_euler = (0.0, 0.0, 0.0)
    root.scale = (1.0, 1.0, 1.0)
    signature, axis, amount = SPECS.NODE_MOTIONS[node_id]
    root["econ_schema_version"] = 1
    root["econ_id"] = node_id
    root["econ_category"] = SPECS.NODE_CATEGORIES[node_id]
    root["econ_signature"] = signature
    root["econ_axis"] = axis
    root["econ_amount"] = amount
    root["econ_duration"] = 0.24
    root["econ_authoring_axes"] = "Blender +Z up/-Y front; glTF +Y up/+Z front"
    if created or "econ_ready" not in root:
        root["econ_ready"] = False
    return root


def _normalise_assemblers(body: MeshAssembler, accent: MeshAssembler) -> None:
    all_vertices = [Vector(vertex) for vertex in body.vertices + accent.vertices]
    minimum = Vector((min(vertex[i] for vertex in all_vertices) for i in range(3)))
    maximum = Vector((max(vertex[i] for vertex in all_vertices) for i in range(3)))
    center = (minimum + maximum) * 0.5
    radius = max((vertex - center).length for vertex in all_vertices)
    if radius <= 0.0:
        raise RuntimeError("Cannot normalise zero-radius policy_rate geometry")

    def convert(vertices):
        return [tuple((Vector(vertex) - center) / radius) for vertex in vertices]

    body.vertices = convert(body.vertices)
    accent.vertices = convert(accent.vertices)


def _mesh_object(
    name: str,
    assembler: MeshAssembler,
    material: bpy.types.Material,
    collection: bpy.types.Collection,
    root: bpy.types.Object,
    role: str,
) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(f"MESH__{name}")
    mesh.from_pydata(assembler.vertices, [], assembler.faces)
    mesh.validate(verbose=False, clean_customdata=True)
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.normal_update()
        for face in bm.faces:
            face.smooth = True
        for edge in bm.edges:
            if edge.is_manifold:
                edge.smooth = edge.calc_face_angle(0.0) < math.radians(32.0)
        bm.to_mesh(mesh)
    finally:
        bm.free()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.parent = root
    obj.location = (0.0, 0.0, 0.0)
    obj.rotation_euler = (0.0, 0.0, 0.0)
    obj.scale = (1.0, 1.0, 1.0)
    obj.data.materials.append(material)
    obj["econ_role"] = role
    if role == "body":
        obj["econ_detail"] = "48-segment base/crown; 12 knurls; 3 calibration grooves"
    else:
        obj["econ_signature"] = "rotate"
        obj["econ_axis"] = "z"
        obj["econ_amount"] = 0.20
        obj["econ_pivot"] = "needle_rotation_center"
    _configure_policy_precision_bevel(obj, role)
    return obj


def _mesh_vertex_components(mesh: bpy.types.Mesh) -> tuple[frozenset[int], ...]:
    adjacency = {vertex.index: set() for vertex in mesh.vertices}
    for edge in mesh.edges:
        first, second = (int(index) for index in edge.vertices)
        adjacency[first].add(second)
        adjacency[second].add(first)

    remaining = set(adjacency)
    components: list[frozenset[int]] = []
    while remaining:
        seed = min(remaining)
        stack = [seed]
        component: set[int] = set()
        while stack:
            current = stack.pop()
            if current in component:
                continue
            component.add(current)
            stack.extend(sorted(adjacency[current] - component, reverse=True))
        remaining.difference_update(component)
        components.append(frozenset(component))
    return tuple(sorted(components, key=lambda item: (len(item), min(item))))


def _policy_precision_bevel_pairs(
    obj: bpy.types.Object,
    role: str,
) -> tuple[tuple[int, int], ...]:
    candidates = exposed_primary_edge_pairs(obj, POLICY_BEVEL_MINIMUM_ANGLE)
    if role == "body":
        # The only 60-degree body candidates form the exposed 48-edge crown
        # transition.  The shallow base rings and knurl tessellation stay clean.
        return candidates
    if role != "accent":
        raise ValueError(f"{obj.name}: unsupported policy bevel role {role!r}")

    # The accent contains a large annulus and a small disconnected needle.
    # Restrict weighting to that needle so the dial face does not become a
    # blanket-beveled, inflated ring.
    components = _mesh_vertex_components(obj.data)
    candidate_vertices = {index for pair in candidates for index in pair}
    eligible = [component for component in components if component & candidate_vertices]
    if not eligible:
        raise ValueError(f"{obj.name}: no connected accent component has bevel candidates")
    needle = min(eligible, key=lambda item: (len(item), min(item)))
    return tuple(pair for pair in candidates if pair[0] in needle and pair[1] in needle)


def _configure_policy_precision_bevel(obj: bpy.types.Object, role: str) -> None:
    bevels = [modifier for modifier in obj.modifiers if modifier.type == "BEVEL"]
    if bevels:
        return
    configure_precision_bevel(obj, _policy_precision_bevel_pairs(obj, role))


def _policy_rate_geometry() -> tuple[MeshAssembler, MeshAssembler]:
    body = MeshAssembler()
    # The exposed base rims use three geometric transition segments over a
    # 0.06-unit width, approximately 2% of the 3.1-unit raw diameter.
    base_profile = [
        (1.47, 0.18),
        (1.50, 0.172),
        (1.532, 0.147),
        (1.55, 0.10),
        (1.55, -0.10),
        (1.532, -0.147),
        (1.50, -0.172),
        (1.47, -0.18),
    ]
    body.add_revolved_y(base_profile, 48, back_y=0.18, front_y=-0.18)

    # Four vertices per tooth make twelve controlled knurl protrusions around
    # the crown. The front profile then cuts three V-shaped calibration grooves.
    crown_profile = [
        (0.91, -0.181),
        (1.01, -0.205),
        (1.08, -0.275),
        (1.045, -0.37),
        (0.94, -0.44),
        (0.79, -0.405),
        (0.68, -0.44),
        (0.55, -0.405),
        (0.47, -0.44),
        (0.35, -0.405),
        (0.25, -0.47),
    ]

    def crown_knurl(ring_index: int, segment: int) -> float:
        if ring_index > 3:
            return 1.0
        tooth_profile = (1.0, 1.045, 1.065, 1.045)
        return tooth_profile[segment % 4]

    body.add_revolved_y(
        crown_profile,
        48,
        back_y=-0.181,
        front_y=-0.47,
        outer_scale=crown_knurl,
    )

    accent = MeshAssembler()
    accent.add_annulus_y(
        outer_radius=0.955,
        inner_radius=0.69,
        back_y=-0.472,
        front_y=-0.515,
        segments=40,
    )
    needle = [
        (-0.075, -0.08),
        (-0.062, 0.42),
        (-0.13, 0.40),
        (0.0, 0.64),
        (0.13, 0.40),
        (0.062, 0.42),
        (0.075, -0.08),
        (0.0, -0.19),
    ]
    accent.add_extruded_polygon_y(needle, back_y=-0.518, front_y=-0.565)
    _normalise_assemblers(body, accent)
    return body, accent


def _author_policy_rate(root: bpy.types.Object, materials: dict[str, bpy.types.Material]) -> str:
    nonempty_meshes = [
        obj
        for obj in root.children_recursive
        if obj.type == "MESH" and obj.data is not None and len(obj.data.polygons) > 0
    ]
    if nonempty_meshes and all(
        len([modifier for modifier in obj.modifiers if modifier.type == "BEVEL"]) == 1
        for obj in nonempty_meshes
    ):
        return "preserved"

    replacing_legacy = bool(nonempty_meshes)

    for obj in list(root.children_recursive):
        if obj.type == "MESH":
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh is not None and mesh.users == 0:
                bpy.data.meshes.remove(mesh)

    node_collection = bpy.data.collections[f"NODE__{root.name}"]
    body, accent = _policy_rate_geometry()
    _mesh_object(
        "policy_rate__body",
        body,
        materials["MAT__DARK_TITANIUM"],
        node_collection,
        root,
        "body",
    )
    _mesh_object(
        "policy_rate__accent",
        accent,
        materials["MAT__ACCENT__MONETARY"],
        node_collection,
        root,
        "accent",
    )
    root["econ_ready"] = True
    root["econ_silhouette"] = "front:crown+needle; side:tiered-low-profile; top:knurled-control"
    return "upgraded" if replacing_legacy else "created"


def _arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--scaffold-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    SPECS.require_blender_version(bpy.app.version[:3])
    args = _arguments(sys.argv[sys.argv.index("--") + 1 :] if argv is None and "--" in sys.argv else (argv or []))
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.is_file():
        bpy.ops.wm.open_mainfile(filepath=str(output), load_ui=False)
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)

    assets = _ensure_scene()
    materials = {name: _material(name) for name in SPECS.MATERIAL_NAMES}
    roots = {node_id: _ensure_root(node_id, assets) for node_id in SPECS.CANONICAL_IDS}
    policy_status = "scaffold-only"
    if not args.scaffold_only:
        policy_status = _author_policy_rate(roots["policy_rate"], materials)

    bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True, check_existing=False)
    print(
        json.dumps(
            {
                "output": str(output),
                "policyRate": policy_status,
                "rootCount": len(roots),
                "readyCount": sum(bool(root.get("econ_ready", False)) for root in roots.values()),
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
