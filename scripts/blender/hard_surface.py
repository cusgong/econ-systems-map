"""Deterministic closed-manifold hard-surface helpers for economic instruments.

All geometry is authored in Blender coordinates: +Z up and -Y front.  Builders
append disconnected, individually closed shells to one body and one accent mesh;
the runtime therefore retains the two-primitive contract without sacrificing a
multi-part precision-instrument silhouette.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector


Vec3 = tuple[float, float, float]


# Source geometry is normalized to a near-unit pre-bevel radius before Blender
# objects are created.  The small 1.008 compensation keeps an inward-beveled
# evaluated mesh inside the 0.98..1.02 radius contract.  A 0.035-unit bevel is
# 1.736 percent of that full diameter, inside the approved 0.03..0.05
# normalized-width range.  Builders explicitly
# nominate exposed primary shells; only their edges above the source angle
# threshold receive weights.  The modifier therefore retains a reviewable
# source selection while smooth torus/cylinder tessellation remains untouched.
NORMALIZED_SOURCE_RADIUS = 1.008
BEVEL_WIDTH = 0.035
BEVEL_WIDTH_RATIO = BEVEL_WIDTH / (2.0 * NORMALIZED_SOURCE_RADIUS)
BEVEL_SEGMENTS = 3
BEVEL_SOURCE_ANGLE_LIMIT = math.radians(70.0)


@dataclass(frozen=True)
class ModelGeometry:
    body: "MeshAssembler"
    accent: "MeshAssembler"
    silhouette_signature: str
    body_detail: str
    accent_pivot: str
    accent_origin: Vec3 = (0.0, 0.0, 0.0)


def transform_matrix(
    location: Vec3 = (0.0, 0.0, 0.0),
    rotation: Vec3 = (0.0, 0.0, 0.0),
    scale: Vec3 = (1.0, 1.0, 1.0),
) -> Matrix:
    """Return a stable translation/XYZ-Euler/scale transform matrix."""

    return (
        Matrix.Translation(Vector(location))
        @ Euler(rotation, "XYZ").to_matrix().to_4x4()
        @ Matrix.Diagonal((*scale, 1.0))
    )


def _face_normal(vertices: Sequence[Vector], face: Sequence[int]) -> Vector:
    """Return a stable Newell normal for an arbitrary source polygon."""

    normal = Vector((0.0, 0.0, 0.0))
    for index, vertex_index in enumerate(face):
        current = vertices[vertex_index]
        following = vertices[face[(index + 1) % len(face)]]
        normal.x += (current.y - following.y) * (current.z + following.z)
        normal.y += (current.z - following.z) * (current.x + following.x)
        normal.z += (current.x - following.x) * (current.y + following.y)
    if normal.length <= 1.0e-9:
        raise ValueError(f"cannot calculate normal for degenerate face {tuple(face)}")
    return normal.normalized()


def _angle_qualified_edges(
    vertices: Sequence[Vector],
    faces: Sequence[Sequence[int]],
    minimum_angle: float,
) -> set[tuple[int, int]]:
    """Select closed-shell edges above an angle without touching smooth facets."""

    adjacency: dict[tuple[int, int], list[Vector]] = {}
    for face in faces:
        normal = _face_normal(vertices, face)
        for index, first in enumerate(face):
            second = face[(index + 1) % len(face)]
            adjacency.setdefault(tuple(sorted((first, second))), []).append(normal)
    selected: set[tuple[int, int]] = set()
    for edge, normals in adjacency.items():
        if len(normals) != 2:
            continue
        dot = max(-1.0, min(1.0, normals[0].dot(normals[1])))
        if math.acos(dot) + 1.0e-6 >= minimum_angle:
            selected.add(edge)
    return selected


class MeshAssembler:
    """Append deterministic primitive shells into one eventual Blender mesh."""

    def __init__(self) -> None:
        self.vertices: list[Vec3] = []
        self.faces: list[tuple[int, ...]] = []
        self.bevel_edges: set[tuple[int, int]] = set()

    def add_vertex(self, vertex: Sequence[float]) -> int:
        self.vertices.append((float(vertex[0]), float(vertex[1]), float(vertex[2])))
        return len(self.vertices) - 1

    def add_face(self, *indices: int) -> None:
        self.faces.append(tuple(indices))

    def append(
        self,
        vertices: Iterable[Sequence[float]],
        faces: Iterable[Sequence[int]],
        matrix: Matrix | None = None,
        bevel: bool = False,
    ) -> None:
        matrix = matrix or Matrix.Identity(4)
        source_vertices = [Vector(vertex) for vertex in vertices]
        source_faces = [tuple(int(index) for index in face) for face in faces]
        transformed = [matrix @ vertex for vertex in source_vertices]
        offset = len(self.vertices)
        for vertex in transformed:
            self.add_vertex(vertex)
        for face in source_faces:
            self.add_face(*(offset + index for index in face))
        if bevel:
            for first, second in _angle_qualified_edges(
                transformed,
                source_faces,
                BEVEL_SOURCE_ANGLE_LIMIT,
            ):
                self.bevel_edges.add(tuple(sorted((offset + first, offset + second))))

    def extend(self, other: "MeshAssembler", matrix: Matrix | None = None) -> None:
        offset = len(self.vertices)
        self.append(other.vertices, other.faces, matrix)
        self.bevel_edges.update(
            tuple(sorted((offset + first, offset + second)))
            for first, second in other.bevel_edges
        )

    def add_box(
        self,
        size: Vec3,
        location: Vec3 = (0.0, 0.0, 0.0),
        rotation: Vec3 = (0.0, 0.0, 0.0),
        bevel: bool = False,
    ) -> None:
        hx, hy, hz = (value * 0.5 for value in size)
        vertices = [
            (-hx, -hy, -hz),
            (hx, -hy, -hz),
            (hx, hy, -hz),
            (-hx, hy, -hz),
            (-hx, -hy, hz),
            (hx, -hy, hz),
            (hx, hy, hz),
            (-hx, hy, hz),
        ]
        faces = [
            (0, 3, 2, 1),
            (4, 5, 6, 7),
            (0, 1, 5, 4),
            (1, 2, 6, 5),
            (2, 3, 7, 6),
            (3, 0, 4, 7),
        ]
        self.append(vertices, faces, transform_matrix(location, rotation), bevel=bevel)

    def add_cylinder(
        self,
        radius: float,
        depth: float,
        segments: int = 24,
        location: Vec3 = (0.0, 0.0, 0.0),
        rotation: Vec3 = (0.0, 0.0, 0.0),
        bevel: bool = False,
    ) -> None:
        vertices: list[Vec3] = []
        half = depth * 0.5
        for z in (-half, half):
            for segment in range(segments):
                angle = 2.0 * math.pi * segment / segments
                vertices.append((radius * math.cos(angle), radius * math.sin(angle), z))
        faces: list[tuple[int, ...]] = [
            tuple(reversed(range(segments))),
            tuple(range(segments, 2 * segments)),
        ]
        for segment in range(segments):
            following = (segment + 1) % segments
            faces.append((segment, following, following + segments, segment + segments))
        self.append(vertices, faces, transform_matrix(location, rotation), bevel=bevel)

    def add_cylinder_between(
        self,
        start: Vec3,
        end: Vec3,
        radius: float,
        segments: int = 20,
        bevel: bool = False,
    ) -> None:
        start_v = Vector(start)
        end_v = Vector(end)
        direction = end_v - start_v
        length = direction.length
        if length <= 1.0e-9:
            raise ValueError("cylinder-between endpoints must differ")
        z_axis = direction.normalized()
        helper = Vector((0.0, 0.0, 1.0))
        if abs(z_axis.dot(helper)) > 0.94:
            helper = Vector((0.0, 1.0, 0.0))
        x_axis = helper.cross(z_axis).normalized()
        y_axis = z_axis.cross(x_axis).normalized()
        rotation = Matrix((x_axis, y_axis, z_axis)).transposed().to_4x4()
        matrix = Matrix.Translation((start_v + end_v) * 0.5) @ rotation

        shell = MeshAssembler()
        shell.add_cylinder(radius, length, segments, bevel=bevel)
        self.extend(shell, matrix)

    def add_torus(
        self,
        major_radius: float,
        minor_radius: float,
        major_segments: int = 40,
        minor_segments: int = 8,
        location: Vec3 = (0.0, 0.0, 0.0),
        rotation: Vec3 = (0.0, 0.0, 0.0),
    ) -> None:
        vertices: list[Vec3] = []
        for major in range(major_segments):
            u = 2.0 * math.pi * major / major_segments
            for minor in range(minor_segments):
                v = 2.0 * math.pi * minor / minor_segments
                radial = major_radius + minor_radius * math.cos(v)
                vertices.append((radial * math.cos(u), radial * math.sin(u), minor_radius * math.sin(v)))
        faces: list[tuple[int, ...]] = []
        for major in range(major_segments):
            following_major = (major + 1) % major_segments
            for minor in range(minor_segments):
                following_minor = (minor + 1) % minor_segments
                faces.append(
                    (
                        major * minor_segments + minor,
                        following_major * minor_segments + minor,
                        following_major * minor_segments + following_minor,
                        major * minor_segments + following_minor,
                    )
                )
        self.append(vertices, faces, transform_matrix(location, rotation))

    def add_torus_arc(
        self,
        major_radius: float,
        minor_radius: float,
        start_angle: float,
        end_angle: float,
        arc_segments: int = 28,
        minor_segments: int = 8,
        location: Vec3 = (0.0, 0.0, 0.0),
        rotation: Vec3 = (0.0, 0.0, 0.0),
    ) -> None:
        vertices: list[Vec3] = []
        for major in range(arc_segments + 1):
            u = start_angle + (end_angle - start_angle) * major / arc_segments
            for minor in range(minor_segments):
                v = 2.0 * math.pi * minor / minor_segments
                radial = major_radius + minor_radius * math.cos(v)
                vertices.append((radial * math.cos(u), radial * math.sin(u), minor_radius * math.sin(v)))
        faces: list[tuple[int, ...]] = []
        for major in range(arc_segments):
            for minor in range(minor_segments):
                following_minor = (minor + 1) % minor_segments
                faces.append(
                    (
                        major * minor_segments + minor,
                        (major + 1) * minor_segments + minor,
                        (major + 1) * minor_segments + following_minor,
                        major * minor_segments + following_minor,
                    )
                )
        faces.append(tuple(reversed(range(minor_segments))))
        last = arc_segments * minor_segments
        faces.append(tuple(last + index for index in range(minor_segments)))
        self.append(vertices, faces, transform_matrix(location, rotation))

    def add_uv_sphere(
        self,
        radius: float,
        segments: int = 24,
        rings: int = 8,
        location: Vec3 = (0.0, 0.0, 0.0),
        scale: Vec3 = (1.0, 1.0, 1.0),
    ) -> None:
        vertices: list[Vec3] = [(0.0, 0.0, radius)]
        for ring in range(1, rings):
            polar = math.pi * ring / rings
            radial = radius * math.sin(polar)
            z = radius * math.cos(polar)
            for segment in range(segments):
                azimuth = 2.0 * math.pi * segment / segments
                vertices.append((radial * math.cos(azimuth), radial * math.sin(azimuth), z))
        bottom = len(vertices)
        vertices.append((0.0, 0.0, -radius))
        faces: list[tuple[int, ...]] = []
        first_ring = 1
        for segment in range(segments):
            following = (segment + 1) % segments
            faces.append((0, first_ring + segment, first_ring + following))
        for ring in range(rings - 2):
            current = 1 + ring * segments
            following_ring = current + segments
            for segment in range(segments):
                following = (segment + 1) % segments
                faces.append((current + segment, following_ring + segment, following_ring + following, current + following))
        last_ring = 1 + (rings - 2) * segments
        for segment in range(segments):
            following = (segment + 1) % segments
            faces.append((last_ring + segment, bottom, last_ring + following))
        self.append(vertices, faces, transform_matrix(location, scale=scale))

    def add_capsule_x(
        self,
        half_length: float,
        radius: float,
        segments: int = 40,
        hemisphere_steps: int = 5,
        location: Vec3 = (0.0, 0.0, 0.0),
        rotation: Vec3 = (0.0, 0.0, 0.0),
    ) -> None:
        profile: list[tuple[float, float]] = [(-half_length - radius, 0.0)]
        for step in range(1, hemisphere_steps + 1):
            angle = -math.pi * 0.5 + (math.pi * 0.5) * step / hemisphere_steps
            profile.append((-half_length + radius * math.sin(angle), radius * math.cos(angle)))
        profile.append((half_length, radius))
        for step in range(1, hemisphere_steps + 1):
            angle = (math.pi * 0.5) * step / hemisphere_steps
            profile.append((half_length + radius * math.sin(angle), radius * math.cos(angle)))

        vertices: list[Vec3] = [(profile[0][0], 0.0, 0.0)]
        ring_indices: list[list[int]] = []
        for x, radial in profile[1:-1]:
            ring: list[int] = []
            for segment in range(segments):
                angle = 2.0 * math.pi * segment / segments
                ring.append(len(vertices))
                vertices.append((x, radial * math.cos(angle), radial * math.sin(angle)))
            ring_indices.append(ring)
        end_index = len(vertices)
        vertices.append((profile[-1][0], 0.0, 0.0))
        faces: list[tuple[int, ...]] = []
        for segment in range(segments):
            following = (segment + 1) % segments
            faces.append((0, ring_indices[0][following], ring_indices[0][segment]))
        for current, following_ring in zip(ring_indices, ring_indices[1:]):
            for segment in range(segments):
                following = (segment + 1) % segments
                faces.append((current[segment], current[following], following_ring[following], following_ring[segment]))
        for segment in range(segments):
            following = (segment + 1) % segments
            faces.append((ring_indices[-1][segment], ring_indices[-1][following], end_index))
        self.append(vertices, faces, transform_matrix(location, rotation))

    def add_extruded_polygon_y(
        self,
        points_xz: Sequence[tuple[float, float]],
        depth: float,
        location: Vec3 = (0.0, 0.0, 0.0),
        rotation: Vec3 = (0.0, 0.0, 0.0),
        bevel: bool = False,
    ) -> None:
        half = depth * 0.5
        vertices = [(x, half, z) for x, z in points_xz] + [(x, -half, z) for x, z in points_xz]
        count = len(points_xz)
        faces: list[tuple[int, ...]] = [
            tuple(range(count)),
            tuple(reversed(range(count, 2 * count))),
        ]
        for index in range(count):
            following = (index + 1) % count
            faces.append((index, following, following + count, index + count))
        self.append(vertices, faces, transform_matrix(location, rotation), bevel=bevel)

    def add_rounded_box_y(
        self,
        width: float,
        height: float,
        depth: float,
        radius: float,
        corner_segments: int = 3,
        location: Vec3 = (0.0, 0.0, 0.0),
        rotation: Vec3 = (0.0, 0.0, 0.0),
        bevel: bool = False,
    ) -> None:
        points = rounded_rectangle_points(width, height, radius, corner_segments)
        self.add_extruded_polygon_y(points, depth, location, rotation, bevel=bevel)

    def add_rounded_rect_ring_y(
        self,
        outer_width: float,
        outer_height: float,
        inner_width: float,
        inner_height: float,
        depth: float,
        outer_radius: float,
        inner_radius: float,
        corner_segments: int = 4,
        location: Vec3 = (0.0, 0.0, 0.0),
        rotation: Vec3 = (0.0, 0.0, 0.0),
    ) -> None:
        outer = rounded_rectangle_points(outer_width, outer_height, outer_radius, corner_segments)
        inner = rounded_rectangle_points(inner_width, inner_height, inner_radius, corner_segments)
        if len(outer) != len(inner):
            raise ValueError("rounded ring loops must have equal vertex counts")
        count = len(outer)
        half = depth * 0.5
        vertices = (
            [(x, half, z) for x, z in outer]
            + [(x, half, z) for x, z in inner]
            + [(x, -half, z) for x, z in outer]
            + [(x, -half, z) for x, z in inner]
        )
        faces: list[tuple[int, ...]] = []
        outer_front = 0
        inner_front = count
        outer_back = 2 * count
        inner_back = 3 * count
        for index in range(count):
            following = (index + 1) % count
            faces.extend(
                [
                    (outer_front + index, outer_front + following, inner_front + following, inner_front + index),
                    (outer_back + following, outer_back + index, inner_back + index, inner_back + following),
                    (outer_front + index, outer_back + index, outer_back + following, outer_front + following),
                    (inner_front + following, inner_back + following, inner_back + index, inner_front + index),
                ]
            )
        self.append(vertices, faces, transform_matrix(location, rotation))


def rounded_rectangle_points(
    width: float,
    height: float,
    radius: float,
    corner_segments: int,
) -> list[tuple[float, float]]:
    radius = min(radius, width * 0.5, height * 0.5)
    cx = width * 0.5 - radius
    cz = height * 0.5 - radius
    points: list[tuple[float, float]] = []
    corners = (
        (cx, -cz, -math.pi * 0.5),
        (cx, cz, 0.0),
        (-cx, cz, math.pi * 0.5),
        (-cx, -cz, math.pi),
    )
    for center_x, center_z, start in corners:
        for step in range(corner_segments + 1):
            angle = start + (math.pi * 0.5) * step / corner_segments
            points.append((center_x + radius * math.cos(angle), center_z + radius * math.sin(angle)))
    return points


def normalise_pair(
    body: MeshAssembler,
    accent: MeshAssembler,
    accent_origin: Vec3 = (0.0, 0.0, 0.0),
) -> Vec3:
    vertices = [Vector(vertex) for vertex in body.vertices + accent.vertices]
    if not vertices:
        raise ValueError("cannot normalize empty model geometry")
    minimum = Vector(tuple(min(vertex[index] for vertex in vertices) for index in range(3)))
    maximum = Vector(tuple(max(vertex[index] for vertex in vertices) for index in range(3)))
    center = (minimum + maximum) * 0.5
    radius = max((vertex - center).length for vertex in vertices)
    if radius <= 1.0e-9:
        raise ValueError("cannot normalize zero-radius model geometry")
    body.vertices = [
        tuple((Vector(vertex) - center) * (NORMALIZED_SOURCE_RADIUS / radius))
        for vertex in body.vertices
    ]
    pivot = Vector(accent_origin)
    accent.vertices = [
        tuple((Vector(vertex) - pivot) * (NORMALIZED_SOURCE_RADIUS / radius))
        for vertex in accent.vertices
    ]
    return tuple((pivot - center) * (NORMALIZED_SOURCE_RADIUS / radius))


def _remove_mesh_descendants(root: bpy.types.Object) -> None:
    for obj in list(root.children_recursive):
        if obj.type != "MESH":
            continue
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh is not None and mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def exposed_primary_edge_pairs(
    obj: bpy.types.Object,
    minimum_angle: float = BEVEL_SOURCE_ANGLE_LIMIT,
) -> tuple[tuple[int, int], ...]:
    """Return deterministic manifold source edges above a visible angle.

    This adapter lets existing authored meshes, notably ``policy_rate``, use
    the same weighted bevel contract as ``MeshAssembler`` output.  Smooth
    tessellation stays below the threshold and is never weighted.
    """

    if obj.type != "MESH" or obj.data is None:
        raise ValueError(f"{obj.name}: exposed-edge selection requires a mesh object")
    if not 0.0 < minimum_angle < math.pi:
        raise ValueError(f"minimum bevel angle must be between 0 and pi: {minimum_angle}")
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.verts.index_update()
        bm.normal_update()
        pairs = {
            tuple(sorted((int(edge.verts[0].index), int(edge.verts[1].index))))
            for edge in bm.edges
            if edge.is_manifold
            and edge.calc_face_angle(0.0) + 1.0e-6 >= minimum_angle
        }
    finally:
        bm.free()
    return tuple(sorted(pairs))


def configure_precision_bevel(
    obj: bpy.types.Object,
    tagged_vertex_pairs: Iterable[Sequence[int]],
) -> int:
    """Attach the canonical weighted three-segment bevel to a mesh object.

    Callers own the design decision about which exposed primary edges are
    tagged.  Passing vertex pairs rather than Blender edge indices keeps the
    selection deterministic across mesh validation and bmesh normal repair.
    """

    if obj.type != "MESH" or obj.data is None:
        raise ValueError(f"{obj.name}: precision bevel requires a mesh object")
    if any(modifier.type == "BEVEL" for modifier in obj.modifiers):
        raise ValueError(f"{obj.name}: precision bevel already exists")
    expected = {
        tuple(sorted((int(pair[0]), int(pair[1]))))
        for pair in tagged_vertex_pairs
    }
    if not expected:
        raise ValueError(f"{obj.name}: no exposed primary bevel edges were tagged")

    mesh = obj.data
    bevel_attribute = mesh.attributes.get("bevel_weight_edge")
    if bevel_attribute is None:
        bevel_attribute = mesh.attributes.new(
            name="bevel_weight_edge",
            type="FLOAT",
            domain="EDGE",
        )
    for item in bevel_attribute.data:
        item.value = 0.0
    tagged_count = 0
    for edge in mesh.edges:
        key = tuple(sorted((int(edge.vertices[0]), int(edge.vertices[1]))))
        if key in expected:
            bevel_attribute.data[edge.index].value = 1.0
            tagged_count += 1
    if tagged_count != len(expected):
        raise ValueError(
            f"{obj.name}: tagged bevel edge drift "
            f"expected={len(expected)} actual={tagged_count}"
        )

    bevel = obj.modifiers.new(name="BEVEL__PRECISION_3SEG", type="BEVEL")
    bevel.affect = "EDGES"
    bevel.width = BEVEL_WIDTH
    bevel.segments = BEVEL_SEGMENTS
    bevel.limit_method = "WEIGHT"
    bevel.edge_weight = bevel_attribute.name
    bevel.angle_limit = BEVEL_SOURCE_ANGLE_LIMIT
    bevel.offset_type = "OFFSET"
    bevel.profile = 0.5
    bevel.use_clamp_overlap = True
    bevel.loop_slide = True
    bevel.miter_outer = "MITER_SHARP"
    bevel.miter_inner = "MITER_SHARP"
    bevel.harden_normals = False
    obj["econ_bevel_width"] = BEVEL_WIDTH
    obj["econ_bevel_width_ratio"] = BEVEL_WIDTH_RATIO
    obj["econ_bevel_segments"] = BEVEL_SEGMENTS
    obj["econ_bevel_limit_method"] = "WEIGHT"
    obj["econ_bevel_source_angle_degrees"] = math.degrees(BEVEL_SOURCE_ANGLE_LIMIT)
    obj["econ_bevel_tagged_edges"] = tagged_count
    return tagged_count


def _mesh_object(
    name: str,
    assembler: MeshAssembler,
    material: bpy.types.Material,
    collection: bpy.types.Collection,
    root: bpy.types.Object,
    role: str,
    detail: str,
    pivot: str,
    location: Vec3 = (0.0, 0.0, 0.0),
) -> bpy.types.Object:
    existing_mesh = bpy.data.meshes.get(f"MESH__{name}")
    if existing_mesh is not None and existing_mesh.users == 0:
        bpy.data.meshes.remove(existing_mesh)
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
                edge.smooth = edge.calc_face_angle(0.0) < math.radians(34.0)
        bm.to_mesh(mesh)
    finally:
        bm.free()
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    configure_precision_bevel(obj, assembler.bevel_edges)
    collection.objects.link(obj)
    obj.parent = root
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.location = location
    obj.rotation_euler = (0.0, 0.0, 0.0)
    obj.scale = (1.0, 1.0, 1.0)
    obj.data.materials.append(material)
    obj["econ_role"] = role
    if role == "body":
        obj["econ_detail"] = detail
    else:
        obj["econ_pivot"] = pivot
    return obj


def finalize_model(
    root: bpy.types.Object,
    geometry: ModelGeometry,
    body_material: bpy.types.Material,
    accent_material: bpy.types.Material,
) -> None:
    """Replace one proof root deterministically while preserving all other roots."""

    _remove_mesh_descendants(root)
    accent_location = normalise_pair(
        geometry.body,
        geometry.accent,
        geometry.accent_origin,
    )
    collection = bpy.data.collections[f"NODE__{root.name}"]
    _mesh_object(
        f"{root.name}__body",
        geometry.body,
        body_material,
        collection,
        root,
        "body",
        geometry.body_detail,
        "fixed_body_origin",
    )
    accent = _mesh_object(
        f"{root.name}__accent",
        geometry.accent,
        accent_material,
        collection,
        root,
        "accent",
        "category accent",
        geometry.accent_pivot,
        accent_location,
    )
    accent["econ_signature"] = root["econ_signature"]
    accent["econ_axis"] = root["econ_axis"]
    accent["econ_amount"] = root["econ_amount"]
    root["econ_silhouette"] = geometry.silhouette_signature
    root["econ_ready"] = True
