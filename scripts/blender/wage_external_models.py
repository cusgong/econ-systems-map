"""Precision instruments for the wage and external-economy batch.

Every builder is scene-independent.  It appends closed primitive shells to a
body and an accent assembler, leaving normalization, material assignment, and
Blender object creation to the shared authoring pipeline.  Coordinates follow
the library convention: Blender +Z is up and -Y faces the camera.
"""

from __future__ import annotations

import math

from hard_surface import MeshAssembler, ModelGeometry


_QUARTER_TURN = math.pi * 0.5


def _radial_xz(radius: float, angle: float, y: float, z_offset: float = 0.0):
    """Return a point on an XZ working circle used by front-facing mechanisms."""

    return (
        radius * math.cos(angle),
        y,
        z_offset + radius * math.sin(angle),
    )


def _ratchet_tooth_points(angle: float) -> tuple[tuple[float, float], ...]:
    """Return one directional five-point ratchet tooth attached to its carrier."""

    inner_radius = 0.55
    shoulder_radius = 0.64
    tip_radius = 0.72
    leading = angle - math.radians(9.0)
    trailing = angle + math.radians(9.0)
    tip = angle - math.radians(4.0)
    return (
        (inner_radius * math.cos(leading), inner_radius * math.sin(leading)),
        (inner_radius * math.cos(trailing), inner_radius * math.sin(trailing)),
        (shoulder_radius * math.cos(trailing), shoulder_radius * math.sin(trailing)),
        (tip_radius * math.cos(tip), tip_radius * math.sin(tip)),
        (shoulder_radius * math.cos(leading), shoulder_radius * math.sin(leading)),
    )


def _tapered_vane_points(
    angle: float,
    inner_radius: float,
    outer_radius: float,
    root_half_width: float,
    tip_half_width: float,
) -> tuple[tuple[float, float], ...]:
    """Return a tapered XZ deployment vane with parallel hinge and shoe faces."""

    radial = (math.cos(angle), math.sin(angle))
    tangent = (-math.sin(angle), math.cos(angle))

    def point(radius: float, half_width: float, side: float):
        return (
            radial[0] * radius + tangent[0] * half_width * side,
            radial[1] * radius + tangent[1] * half_width * side,
        )

    return (
        point(inner_radius, root_half_width, -1.0),
        point(outer_radius, tip_half_width, -1.0),
        point(outer_radius, tip_half_width, 1.0),
        point(inner_radius, root_half_width, 1.0),
    )


def _rotate_point_xyz(
    point: tuple[float, float, float],
    rotation: tuple[float, float, float],
) -> tuple[float, float, float]:
    """Apply the shared XYZ Euler convention to one local attachment point."""

    x, y, z = point
    rx, ry, rz = rotation
    y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
    x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
    x, y = x * math.cos(rz) - y * math.sin(rz), x * math.sin(rz) + y * math.cos(rz)
    return (x, y, z)


def _add_annular_band_y(
    assembler: MeshAssembler,
    *,
    inner_radius: float,
    outer_radius: float,
    start_angle: float,
    end_angle: float,
    steps: int,
    depth: float,
    location: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
    bevel: bool = False,
) -> None:
    """Append one closed, quad-faced structural band without a concave N-gon."""

    half = depth * 0.5
    local_loops: list[list[tuple[float, float, float]]] = []
    for y in (half, -half):
        outer = []
        inner = []
        for index in range(steps + 1):
            ratio = index / steps
            angle = start_angle + (end_angle - start_angle) * ratio
            outer.append(
                (outer_radius * math.cos(angle), y, outer_radius * math.sin(angle))
            )
            inner.append(
                (inner_radius * math.cos(angle), y, inner_radius * math.sin(angle))
            )
        local_loops.extend((outer, inner))

    vertices = []
    for loop in local_loops:
        for point in loop:
            x, y, z = _rotate_point_xyz(point, rotation)
            vertices.append((x + location[0], y + location[1], z + location[2]))

    count = steps + 1
    outer_front = 0
    inner_front = count
    outer_back = count * 2
    inner_back = count * 3
    faces: list[tuple[int, ...]] = []
    for index in range(steps):
        following = index + 1
        faces.extend(
            (
                (
                    outer_front + index,
                    outer_front + following,
                    inner_front + following,
                    inner_front + index,
                ),
                (
                    outer_back + following,
                    outer_back + index,
                    inner_back + index,
                    inner_back + following,
                ),
                (
                    outer_front + index,
                    outer_back + index,
                    outer_back + following,
                    outer_front + following,
                ),
                (
                    inner_front + following,
                    inner_back + following,
                    inner_back + index,
                    inner_front + index,
                ),
            )
        )
    faces.extend(
        (
            (outer_front, inner_front, inner_back, outer_back),
            (
                outer_front + steps,
                outer_back + steps,
                inner_back + steps,
                inner_front + steps,
            ),
        )
    )
    assembler.append(vertices, faces, bevel=bevel)


def build_wages() -> ModelGeometry:
    """Build a compensation drum with a sparse, mechanically keyed ratchet."""

    body = MeshAssembler()
    accent = MeshAssembler()

    # A deep compensation barrel carries the Blender-Y mass so the side (Y-Z)
    # silhouette reads as a full drum, not a thin disc.  Coaxial bearing collars
    # on both Y faces extend the barrel without widening the front (X-Z) circle.
    drum_center = (0.0, 0.04, 0.02)
    body.add_cylinder(
        radius=0.56,
        depth=0.70,
        segments=24,
        location=drum_center,
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    for face_y in (0.45, -0.41):
        body.add_cylinder(
            radius=0.31,
            depth=0.14,
            segments=18,
            location=(0.0, face_y, 0.02),
            rotation=(_QUARTER_TURN, 0.0, 0.0),
            bevel=True,
        )
    body.add_cylinder(
        radius=0.20,
        depth=0.16,
        segments=16,
        location=(0.0, 0.55, 0.02),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    body.add_torus(
        major_radius=0.45,
        minor_radius=0.055,
        major_segments=24,
        minor_segments=6,
        location=(0.0, -0.30, 0.02),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
    )
    body.add_box(
        size=(1.18, 0.88, 0.14),
        location=(0.0, 0.03, -0.66),
        bevel=True,
    )
    for x, height in ((-0.47, 0.42), (0.47, 0.34)):
        body.add_box(
            size=(0.17, 0.66, height),
            location=(x, 0.03, -0.48 + height * 0.18),
            bevel=True,
        )

    # The dark pawl is fixed to the drum housing and visibly bears on the
    # leading face of the 31-degree tooth.  Only the indexed carrier and teeth
    # rotate as the category-accent mechanism.
    body.add_extruded_polygon_y(
        (
            (0.46, 0.51),
            (0.55, 0.55),
            (0.65, 0.34),
            (0.59, 0.28),
            (0.52, 0.42),
        ),
        depth=0.12,
        location=(0.0, -0.23, 0.0),
        bevel=False,
    )
    body.add_cylinder(
        radius=0.105,
        depth=0.15,
        segments=6,
        location=(0.51, -0.20, 0.50),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=False,
    )

    ratchet_origin = (0.0, -0.24, 0.02)
    _add_annular_band_y(
        accent,
        inner_radius=0.49,
        outer_radius=0.59,
        start_angle=math.radians(-160.0),
        end_angle=math.radians(120.0),
        steps=13,
        depth=0.065,
        location=(0.0, ratchet_origin[1], ratchet_origin[2]),
        bevel=False,
    )
    for degrees in (-142.0, -86.0, -29.0, 31.0, 94.0):
        angle = math.radians(degrees)
        accent.add_extruded_polygon_y(
            _ratchet_tooth_points(angle),
            depth=0.085,
            location=(0.0, ratchet_origin[1], ratchet_origin[2]),
            bevel=False,
        )
    terminal_angle = math.radians(120.0)
    accent.add_box(
        size=(0.13, 0.10, 0.11),
        location=_radial_xz(
            0.57,
            terminal_angle,
            ratchet_origin[1],
            ratchet_origin[2],
        ),
        rotation=(0.0, -terminal_angle, 0.0),
        bevel=True,
    )
    accent.add_cylinder(
        radius=0.13,
        depth=0.12,
        segments=12,
        location=ratchet_origin,
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:directional five-tooth carrier engaged by one fixed upper-right pawl;"
            "side:thin indexed ratchet plane against a deep compensation drum;"
            "top:hinged pawl bearing on one continuous partial carrier"
        ),
        body_detail="deep compensation drum, recessed hub, unequal standards, and contacting hinged pawl",
        accent_pivot="ratchet step axis; glTF Z rotation is Blender -Y",
        accent_origin=ratchet_origin,
    )


def build_exports() -> ModelGeometry:
    """Build a four-port cargo hub with one translating outward vane plate."""

    body = MeshAssembler()
    accent = MeshAssembler()

    body.add_cylinder(
        radius=0.24,
        depth=0.84,
        segments=18,
        location=(0.0, 0.02, 0.0),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    body.add_torus(
        major_radius=0.34,
        minor_radius=0.052,
        major_segments=22,
        minor_segments=6,
        location=(0.0, 0.25, 0.0),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
    )

    port_specs = (
        ((-0.62, 0.05, 0.18), (0.30, 0.28, 0.22)),
        ((0.61, 0.05, 0.11), (0.34, 0.30, 0.19)),
        ((-0.12, 0.05, 0.61), (0.27, 0.28, 0.32)),
        ((0.14, 0.05, -0.59), (0.32, 0.26, 0.24)),
    )
    for location, size in port_specs:
        body.add_cylinder_between(
            (location[0] * 0.25, 0.05, location[2] * 0.25),
            (location[0] * 0.78, 0.05, location[2] * 0.78),
            radius=0.066,
            segments=8,
            bevel=True,
        )
        body.add_box(size=size, location=location, bevel=True)

    vane_origin = (0.0, -0.34, 0.0)
    vane_specs = (
        (math.radians(-28.0), 0.58),
        (math.radians(8.0), 0.65),
        (math.radians(45.0), 0.56),
    )
    # A deep fixed hinge boss bridges the hub to the translating plate.  Each
    # tapered vane ends in a colored shoe captured by a dark body receiver.
    body.add_cylinder(
        radius=0.17,
        depth=0.16,
        segments=12,
        location=(0.0, -0.25, 0.0),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=False,
    )
    for index, (angle, outer_radius) in enumerate(vane_specs):
        tip_x = outer_radius * math.cos(angle)
        tip_z = outer_radius * math.sin(angle)
        body.add_box(
            size=(0.15, 0.18, 0.15),
            location=(tip_x, -0.245, tip_z),
            rotation=(0.0, -angle, 0.0),
            bevel=False,
        )
        accent.add_extruded_polygon_y(
            _tapered_vane_points(
                angle,
                inner_radius=0.07,
                outer_radius=outer_radius,
                root_half_width=0.075,
                tip_half_width=0.045,
            ),
            depth=0.07,
            location=vane_origin,
            bevel=True,
        )
        accent.add_box(
            size=(0.105, 0.075, 0.115),
            location=(tip_x, vane_origin[1], tip_z),
            rotation=(0.0, -angle, 0.0),
            bevel=index == 0,
        )
    accent.add_cylinder(
        radius=0.11,
        depth=0.10,
        segments=12,
        location=vane_origin,
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:three tapered deployment vanes keyed into separate docking shoes;"
            "side:hinged translating carrier captured by deep fixed receivers;"
            "top:unequal cargo ports behind one interlocking outbound fan"
        ),
        body_detail="four unequal cargo ports, recessed coupling ring, hinge boss, and three docking receivers",
        accent_pivot="outbound vane plate; glTF +Z advances along Blender -Y",
        accent_origin=vane_origin,
    )


def build_current_account() -> ModelGeometry:
    """Build bilateral counter dials around one front-mounted balance axle."""

    body = MeshAssembler()
    accent = MeshAssembler()

    # Deep counter barrels carry the Blender-Y mass so the side (Y-Z) silhouette
    # reads as full drums rather than thin discs.
    for x, radius, z in ((-0.40, 0.34, 0.06), (0.42, 0.30, -0.02)):
        body.add_cylinder(
            radius=radius,
            depth=0.86,
            segments=18,
            location=(x, 0.04, z),
            rotation=(_QUARTER_TURN, 0.0, 0.0),
            bevel=True,
        )
    # A tall Y-deep central spine fills the weak side (Y-Z) silhouette by rising
    # above and below the dials; its narrow X keeps the top (X-Y) footprint from
    # growing, so the min view catches up to the dominant top view.
    body.add_box(
        size=(0.30, 0.84, 1.04),
        location=(0.0, 0.04, 0.0),
        bevel=True,
    )
    body.add_box(
        size=(1.12, 0.66, 0.16),
        location=(0.0, 0.04, -0.52),
        bevel=True,
    )
    body.add_box(
        size=(0.18, 0.66, 0.42),
        location=(-0.54, 0.04, -0.29),
        bevel=True,
    )
    body.add_box(
        size=(0.18, 0.66, 0.36),
        location=(0.55, 0.04, -0.33),
        bevel=True,
    )

    axle_origin = (0.0, -0.30, 0.03)
    accent.add_cylinder_between(
        (-0.56, -0.30, 0.03),
        (0.56, -0.30, 0.03),
        radius=0.045,
        segments=12,
        bevel=True,
    )
    accent.add_box(
        size=(0.98, 0.10, 0.13),
        location=axle_origin,
        bevel=True,
    )
    accent.add_cylinder(
        radius=0.185,
        depth=0.13,
        segments=12,
        location=axle_origin,
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    for x, radius, z in ((-0.47, 0.205, -0.02), (0.48, 0.175, 0.09)):
        accent.add_cylinder(
            radius=radius,
            depth=0.12,
            segments=12,
            location=(x, -0.30, z),
            rotation=(_QUARTER_TURN, 0.0, 0.0),
            bevel=True,
        )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:unequal bilateral counter dials crossed by a level axle;"
            "side:thin balance beam ahead of two deep offset meter barrels;"
            "top:twin separated counters seated on one low datum cradle"
        ),
        body_detail="unequal bilateral counter dials, central bridge, and low datum cradle",
        accent_pivot="bilateral balance axle; glTF Z rotation is Blender -Y",
        accent_origin=axle_origin,
    )


def build_capital_flows() -> ModelGeometry:
    """Build a converging four-inlet manifold with one translating front gate."""

    body = MeshAssembler()
    accent = MeshAssembler()

    body.add_rounded_box_y(
        width=0.70,
        height=0.66,
        depth=0.46,
        radius=0.11,
        corner_segments=3,
        location=(0.0, 0.04, 0.0),
        bevel=True,
    )
    inlet_points = (
        (-0.66, 0.30, 0.39),
        (0.65, 0.30, 0.31),
        (-0.49, 0.30, -0.52),
        (0.54, 0.30, -0.48),
    )
    for x, y, z in inlet_points:
        inner = (x * 0.34, -0.02, z * 0.34)
        body.add_cylinder_between(
            (x, y, z),
            inner,
            radius=0.085,
            segments=10,
            bevel=False,
        )
        dx = x - inner[0]
        dy = y - inner[1]
        dz = z - inner[2]
        direction_length = math.sqrt(dx * dx + dy * dy + dz * dz)
        direction = (
            dx / direction_length,
            dy / direction_length,
            dz / direction_length,
        )
        collar_start = (
            x - direction[0] * 0.065,
            y - direction[1] * 0.065,
            z - direction[2] * 0.065,
        )
        collar_end = (
            x + direction[0] * 0.095,
            y + direction[1] * 0.095,
            z + direction[2] * 0.095,
        )
        body.add_cylinder_between(
            collar_start,
            collar_end,
            radius=0.14,
            segments=12,
            bevel=True,
        )
    body.add_box(
        size=(0.96, 0.34, 0.13),
        location=(0.0, 0.05, -0.61),
        bevel=True,
    )

    # Fixed gate guide rails bridge the visible gap from the plenum face to the
    # translating accent frame.  Their end overlap makes the motion mechanically
    # legible from the perspective and side QA views.
    for x in (-0.24, 0.24):
        body.add_box(
            size=(0.045, 0.30, 0.045),
            location=(x, -0.285, -0.22),
            bevel=False,
        )

    gate_origin = (0.0, -0.38, 0.0)
    accent.add_rounded_rect_ring_y(
        outer_width=0.60,
        outer_height=0.56,
        inner_width=0.40,
        inner_height=0.36,
        depth=0.09,
        outer_radius=0.10,
        inner_radius=0.06,
        corner_segments=3,
        location=gate_origin,
        bevel=True,
    )
    for x in (-0.15, 0.0, 0.15):
        accent.add_box(
            size=(0.085, 0.09, 0.34),
            location=(x, -0.40, 0.0),
            bevel=x != 0.0,
        )
    accent.add_box(
        size=(0.22, 0.10, 0.11),
        location=(0.20, -0.40, 0.32),
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:four coaxial inlet bells converging on a slotted square gate;"
            "side:forward gate captured on twin rails from the deep collection plenum;"
            "top:coaxial flanges and trunks narrowing toward one guided throat"
        ),
        body_detail="four coaxial inlet trunks and bells, collection plenum, twin gate guides, and base rail",
        accent_pivot="inflow gate face; glTF +Z advances along Blender -Y",
        accent_origin=gate_origin,
    )


def build_fed_rate() -> ModelGeometry:
    """Build a twelve-segment horizontal governor with one orbital weight."""

    body = MeshAssembler()
    accent = MeshAssembler()

    # The twelve crown blocks carry the dominant top-view silhouette; their
    # bevels are the single largest triangle sink, so only three keep the
    # weighted edge and the freed budget funds the vertical column below.
    governor_z = 0.14
    for index in range(12):
        angle = 2.0 * math.pi * index / 12.0
        radius = 0.62
        body.add_box(
            size=(0.24, 0.13, 0.12),
            location=(
                radius * math.cos(angle),
                radius * math.sin(angle),
                governor_z,
            ),
            rotation=(0.0, 0.0, angle + _QUARTER_TURN),
            bevel=index < 3,
        )
    _add_annular_band_y(
        body,
        inner_radius=0.52,
        outer_radius=0.68,
        start_angle=math.radians(-165.0),
        end_angle=math.radians(165.0),
        steps=9,
        depth=0.12,
        location=(0.0, 0.0, governor_z),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    # Central stacked column: a fat barrel, a governor-plane hub, a base drum,
    # and a crown cap.  Each stays inside the pedestal top-view radius, so the
    # weak front (X-Z) and side (Y-Z) views fill symmetrically while the strong
    # top (X-Y) view barely changes.
    body.add_cylinder(
        radius=0.29,
        depth=1.02,
        segments=12,
        location=(0.0, 0.0, -0.05),
        bevel=True,
    )
    body.add_cylinder(
        radius=0.37,
        depth=0.26,
        segments=14,
        location=(0.0, 0.0, governor_z),
        bevel=True,
    )
    body.add_cylinder(
        radius=0.40,
        depth=0.32,
        segments=14,
        location=(0.0, 0.0, -0.52),
        bevel=True,
    )
    body.add_cylinder(
        radius=0.23,
        depth=0.16,
        segments=12,
        location=(0.0, 0.0, 0.47),
        bevel=True,
    )
    for angle in (math.radians(25.0), math.radians(145.0), math.radians(265.0)):
        body.add_cylinder_between(
            (0.22 * math.cos(angle), 0.22 * math.sin(angle), -0.23),
            (0.55 * math.cos(angle), 0.55 * math.sin(angle), governor_z),
            radius=0.035,
            segments=8,
            bevel=False,
        )

    # The orbital carriage stays a single weighted arm, but the weight grows in
    # its X-Y disc (never its thin Z depth) and a mid-arm slider collar is added
    # so the accent area recovers its share after the column bulked the body.
    # The orbital carriage stays a single weighted arm.  Area is recovered from
    # a wide arm and a mid slider collar (both inside the crown radius), so the
    # bounding box is not pushed outward and the column keeps its silhouette fill.
    orbit_origin = (0.0, 0.0, governor_z)
    accent.add_box(
        size=(0.80, 0.24, 0.11),
        location=(0.33, 0.0, governor_z),
        bevel=True,
    )
    accent.add_cylinder(
        radius=0.185,
        depth=0.18,
        segments=12,
        location=(0.40, 0.0, governor_z),
        bevel=True,
    )
    accent.add_cylinder(
        radius=0.225,
        depth=0.18,
        segments=14,
        location=(0.66, 0.0, governor_z),
        bevel=True,
    )
    accent.add_torus_arc(
        major_radius=0.66,
        minor_radius=0.05,
        start_angle=math.radians(-27.0),
        end_angle=math.radians(28.0),
        arc_segments=5,
        minor_segments=6,
        location=orbit_origin,
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:vertical governor spindle below an edge-on segmented orbit;"
            "side:twelve-block horizontal crown above a three-brace pedestal;"
            "top:open dodecagonal governor ring with one weighted carriage"
        ),
        body_detail="twelve-segment horizontal governor, spindle, pedestal, and three radial braces",
        accent_pivot="orbital governor axis; glTF Y rotation is Blender Z",
        accent_origin=orbit_origin,
    )


def build_global_growth() -> ModelGeometry:
    """Build a central support cage inside three orthogonal expanding bands."""

    body = MeshAssembler()
    accent = MeshAssembler()

    body.add_rounded_box_y(
        width=0.38,
        height=0.38,
        depth=0.38,
        radius=0.075,
        corner_segments=2,
        location=(0.0, 0.0, 0.0),
        bevel=True,
    )
    body.add_cylinder(
        radius=0.22,
        depth=0.20,
        segments=12,
        location=(0.0, 0.0, 0.0),
        bevel=True,
    )
    cage_corners = (
        (-0.27, -0.27),
        (0.27, -0.27),
        (0.27, 0.27),
        (-0.27, 0.27),
    )
    for x, y in cage_corners:
        body.add_cylinder_between(
            (x, y, -0.46),
            (x, y, 0.46),
            radius=0.038,
            segments=8,
            bevel=False,
        )
    for z in (-0.46, 0.46):
        for index, first in enumerate(cage_corners):
            second = cage_corners[(index + 1) % len(cage_corners)]
            body.add_cylinder_between(
                (first[0], first[1], z),
                (second[0], second[1], z),
                radius=0.036,
                segments=8,
                bevel=False,
            )

    # Smooth corner nodes and buried radial ties add structural mass without
    # turning the cage into a bevel-count exercise.
    for z in (-0.46, 0.46):
        for x, y in cage_corners:
            body.add_uv_sphere(
                radius=0.07,
                segments=8,
                rings=4,
                location=(x, y, z),
            )
    for endpoint in (
        (0.58, 0.0, 0.0),
        (-0.58, 0.0, 0.0),
        (0.0, 0.58, 0.0),
        (0.0, -0.58, 0.0),
        (0.0, 0.0, 0.58),
        (0.0, 0.0, -0.58),
    ):
        body.add_cylinder_between(
            (0.10 * endpoint[0] / 0.58, 0.10 * endpoint[1] / 0.58, 0.10 * endpoint[2] / 0.58),
            endpoint,
            radius=0.028,
            segments=8,
        )

    growth_origin = (0.0, 0.0, 0.0)
    band_specs = (
        (math.radians(-155.0), math.radians(-50.0), 10, (0.0, 0.0, 0.0)),
        (math.radians(-15.0), math.radians(95.0), 10, (_QUARTER_TURN, 0.0, 0.0)),
        (math.radians(105.0), math.radians(220.0), 11, (0.0, _QUARTER_TURN, 0.0)),
    )
    for band_index, (start_angle, end_angle, steps, rotation) in enumerate(band_specs):
        _add_annular_band_y(
            accent,
            inner_radius=0.61,
            outer_radius=0.695,
            start_angle=start_angle,
            end_angle=end_angle,
            steps=steps,
            depth=0.065,
            location=growth_origin,
            rotation=rotation,
            bevel=band_index == 0,
        )

        # Dark cage-mounted endpoint bearings terminate every colored band and
        # prevent the three partial axes from reading as a decorative wire globe.
        for angle in (start_angle, end_angle):
            bearing = _rotate_point_xyz(
                (0.65 * math.cos(angle), 0.0, 0.65 * math.sin(angle)),
                rotation,
            )
            body.add_rounded_box_y(
                width=0.14,
                height=0.14,
                depth=0.12,
                radius=0.030,
                corner_segments=2,
                location=bearing,
                rotation=rotation,
                bevel=False,
            )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:two staggered structural growth bands anchored to an open cage;"
            "side:third partial band terminates in paired machined bearings;"
            "top:three non-circularized expansion axes around a compact support frame"
        ),
        body_detail="open central support cage, six band-end bearings, radial ties, and compact core block",
        accent_pivot="orthogonal growth-band centroid; scale XYZ",
        accent_origin=growth_origin,
    )


__all__ = (
    "build_wages",
    "build_exports",
    "build_current_account",
    "build_capital_flows",
    "build_fed_rate",
    "build_global_growth",
)
