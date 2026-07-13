"""Precision instruments for the asset, policy, exogenous, and psychology batch.

The six builders are scene-independent.  They author deterministic closed
shells in Blender coordinates (+Z up, -Y front) and return one body and one
category-accent assembler for the shared hard-surface pipeline.  Blender axes
map to glTF as ``(x, z, -y)``; every accent origin below is therefore chosen on
the mechanical axis used by ``NODE_MOTIONS`` rather than at an arbitrary mesh
centroid.
"""

from __future__ import annotations

import math

from hard_surface import MeshAssembler, ModelGeometry


_QUARTER_TURN = math.pi * 0.5


def _add_helix_tube_z(
    assembler: MeshAssembler,
    *,
    radius: float,
    height: float,
    turns: float,
    tube_radius: float,
    path_segments: int,
    tube_segments: int,
    location: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> None:
    """Append a capped, closed helical tube around Blender Z."""

    ox, oy, oz = location
    vertices: list[tuple[float, float, float]] = []
    rings: list[list[int]] = []
    angular_rate = turns * 2.0 * math.pi
    vertical_rate = height / angular_rate

    for index in range(path_segments + 1):
        ratio = index / path_segments
        angle = angular_rate * ratio
        center = (
            ox + radius * math.cos(angle),
            oy + radius * math.sin(angle),
            oz + height * (ratio - 0.5),
        )
        # Radial and binormal vectors form a stable frame around the helical
        # tangent.  Written out explicitly to keep this module mathutils-free.
        radial = (math.cos(angle), math.sin(angle), 0.0)
        tangent = (
            -math.sin(angle),
            math.cos(angle),
            vertical_rate / radius,
        )
        tangent_length = math.sqrt(sum(value * value for value in tangent))
        tangent = tuple(value / tangent_length for value in tangent)
        binormal = (
            tangent[1] * radial[2] - tangent[2] * radial[1],
            tangent[2] * radial[0] - tangent[0] * radial[2],
            tangent[0] * radial[1] - tangent[1] * radial[0],
        )
        binormal_length = math.sqrt(sum(value * value for value in binormal))
        binormal = tuple(value / binormal_length for value in binormal)

        ring: list[int] = []
        for segment in range(tube_segments):
            phase = 2.0 * math.pi * segment / tube_segments
            cosine = math.cos(phase)
            sine = math.sin(phase)
            ring.append(len(vertices))
            vertices.append(
                (
                    center[0]
                    + tube_radius * (radial[0] * cosine + binormal[0] * sine),
                    center[1]
                    + tube_radius * (radial[1] * cosine + binormal[1] * sine),
                    center[2]
                    + tube_radius * (radial[2] * cosine + binormal[2] * sine),
                )
            )
        rings.append(ring)

    faces: list[tuple[int, ...]] = []
    for current, following in zip(rings, rings[1:]):
        for segment in range(tube_segments):
            next_segment = (segment + 1) % tube_segments
            faces.append(
                (
                    current[segment],
                    current[next_segment],
                    following[next_segment],
                    following[segment],
                )
            )
    faces.append(tuple(reversed(rings[0])))
    faces.append(tuple(rings[-1]))
    assembler.append(vertices, faces)


def _add_hollow_frustum_z(
    assembler: MeshAssembler,
    *,
    outer_bottom_radius: float,
    outer_top_radius: float,
    inner_bottom_radius: float,
    inner_top_radius: float,
    outer_bottom_z: float,
    inner_bottom_z: float,
    top_z: float,
    segments: int,
    location_xy: tuple[float, float] = (0.0, 0.0),
    bevel: bool = False,
) -> None:
    """Append a closed, open-topped machined vessel with a solid lower wall."""

    ox, oy = location_xy
    rings: list[list[int]] = []
    vertices: list[tuple[float, float, float]] = []
    for radius, z in (
        (outer_bottom_radius, outer_bottom_z),
        (outer_top_radius, top_z),
        (inner_top_radius, top_z),
        (inner_bottom_radius, inner_bottom_z),
    ):
        ring: list[int] = []
        for segment in range(segments):
            angle = 2.0 * math.pi * segment / segments
            ring.append(len(vertices))
            vertices.append(
                (
                    ox + radius * math.cos(angle),
                    oy + radius * math.sin(angle),
                    z,
                )
            )
        rings.append(ring)

    outer_bottom, outer_top, inner_top, inner_bottom = rings
    faces: list[tuple[int, ...]] = []
    for segment in range(segments):
        following = (segment + 1) % segments
        faces.extend(
            (
                (
                    outer_bottom[segment],
                    outer_bottom[following],
                    outer_top[following],
                    outer_top[segment],
                ),
                (
                    outer_top[segment],
                    outer_top[following],
                    inner_top[following],
                    inner_top[segment],
                ),
                (
                    inner_top[segment],
                    inner_top[following],
                    inner_bottom[following],
                    inner_bottom[segment],
                ),
                (
                    outer_bottom[following],
                    outer_bottom[segment],
                    inner_bottom[segment],
                    inner_bottom[following],
                ),
            )
        )
    assembler.append(vertices, faces, bevel=bevel)


def _add_faceted_ore_core(
    assembler: MeshAssembler,
    *,
    location: tuple[float, float, float] = (0.0, 0.0, 0.0),
    scale: float = 1.0,
) -> None:
    """Append two interlocked truncated ore chunks with a fractured seam."""

    def append_chunk(
        lower_center: tuple[float, float],
        upper_center: tuple[float, float],
        lower_z: float,
        upper_z: float,
        profile: tuple[tuple[float, float, float], ...],
    ) -> None:
        ox, oy, oz = location
        vertices: list[tuple[float, float, float]] = []
        for center, z, radius_index in (
            (lower_center, lower_z, 1),
            (upper_center, upper_z, 2),
        ):
            for values in profile:
                angle = math.radians(values[0])
                radius = values[radius_index]
                vertices.append(
                    (
                        ox + (center[0] + radius * math.cos(angle)) * scale,
                        oy + (center[1] + radius * math.sin(angle)) * scale,
                        oz + z * scale,
                    )
                )
        count = len(profile)
        faces: list[tuple[int, ...]] = [
            tuple(reversed(range(count))),
            tuple(range(count, 2 * count)),
        ]
        for index in range(count):
            following = (index + 1) % count
            faces.append((index, following, following + count, index + count))
        assembler.append(vertices, faces, bevel=True)

    # Neither chunk terminates in an apex.  Offset upper plates and unequal
    # radii create broad fracture planes instead of a centered gemstone or
    # pyramid, while the overlap reads as one mechanically captured ore load.
    append_chunk(
        lower_center=(-0.08, 0.02),
        upper_center=(0.035, -0.045),
        lower_z=-0.30,
        upper_z=0.31,
        profile=(
            (8.0, 0.24, 0.18),
            (63.0, 0.29, 0.16),
            (127.0, 0.26, 0.21),
            (186.0, 0.25, 0.17),
            (247.0, 0.22, 0.15),
            (310.0, 0.28, 0.20),
        ),
    )
    append_chunk(
        lower_center=(0.18, -0.075),
        upper_center=(0.105, 0.075),
        lower_z=-0.24,
        upper_z=0.18,
        profile=(
            (18.0, 0.20, 0.14),
            (91.0, 0.17, 0.13),
            (166.0, 0.22, 0.16),
            (239.0, 0.18, 0.12),
            (314.0, 0.21, 0.15),
        ),
    )


def _add_diagonal_c_clamp_y(
    assembler: MeshAssembler,
    *,
    width: float,
    height: float,
    bar_width: float,
    depth: float,
    location: tuple[float, float, float],
    rotation_y: float,
    open_direction: int,
    bevel: bool = False,
) -> None:
    """Append one thick, open rounded C-frame in Blender XZ."""

    if open_direction not in {-1, 1}:
        raise ValueError("C-clamp open_direction must be -1 or 1")
    ox, oy, oz = location
    cosine = math.cos(rotation_y)
    sine = math.sin(rotation_y)

    def transformed(local_x: float, local_z: float) -> tuple[float, float, float]:
        return (
            ox + cosine * local_x + sine * local_z,
            oy,
            oz - sine * local_x + cosine * local_z,
        )

    spine_x = -open_direction * (width - bar_width) * 0.5
    assembler.add_rounded_box_y(
        width=bar_width,
        height=height,
        depth=depth,
        radius=bar_width * 0.44,
        corner_segments=3,
        location=transformed(spine_x, 0.0),
        rotation=(0.0, rotation_y, 0.0),
        bevel=bevel,
    )
    for local_z in (-(height - bar_width) * 0.5, (height - bar_width) * 0.5):
        assembler.add_rounded_box_y(
            width=width,
            height=bar_width,
            depth=depth,
            radius=bar_width * 0.44,
            corner_segments=3,
            location=transformed(0.0, local_z),
            rotation=(0.0, rotation_y, 0.0),
        )


def _swept_foil_points(
    *,
    angle: float,
    inner_radius: float,
    middle_radius: float,
    outer_radius: float,
    sweep: float,
    inner_half_width: float,
    middle_half_width: float,
    outer_half_width: float,
) -> tuple[tuple[float, float], ...]:
    """Return a six-point tapered compressor foil in Blender XZ."""

    middle_angle = angle + sweep * 0.46
    outer_angle = angle + sweep

    def polar(radius: float, phase: float) -> tuple[float, float]:
        return (radius * math.cos(phase), radius * math.sin(phase))

    return (
        polar(inner_radius, angle - inner_half_width),
        polar(middle_radius, middle_angle - middle_half_width),
        polar(outer_radius, outer_angle - outer_half_width),
        polar(outer_radius, outer_angle + outer_half_width),
        polar(middle_radius, middle_angle + middle_half_width),
        polar(inner_radius, angle + inner_half_width),
    )


def _add_half_ellipsoid_x(
    assembler: MeshAssembler,
    *,
    sign: float,
    radii: tuple[float, float, float],
    longitude_segments: int,
    latitude_steps: int,
    offset_x: float,
) -> None:
    """Append one closed solid hemisphere split at its local X equator."""

    rx, ry, rz = radii
    vertices: list[tuple[float, float, float]] = [
        (offset_x + sign * rx, 0.0, 0.0)
    ]
    rings: list[list[int]] = []
    for step in range(1, latitude_steps + 1):
        polar = _QUARTER_TURN * step / latitude_steps
        ring: list[int] = []
        for segment in range(longitude_segments):
            azimuth = 2.0 * math.pi * segment / longitude_segments
            ring.append(len(vertices))
            vertices.append(
                (
                    offset_x + sign * rx * math.cos(polar),
                    ry * math.sin(polar) * math.cos(azimuth),
                    rz * math.sin(polar) * math.sin(azimuth),
                )
            )
        rings.append(ring)
    cap_center = len(vertices)
    vertices.append((offset_x, 0.0, 0.0))

    faces: list[tuple[int, ...]] = []
    first = rings[0]
    for segment in range(longitude_segments):
        following = (segment + 1) % longitude_segments
        faces.append((0, first[segment], first[following]))
    for current, following_ring in zip(rings, rings[1:]):
        for segment in range(longitude_segments):
            following = (segment + 1) % longitude_segments
            faces.append(
                (
                    current[segment],
                    following_ring[segment],
                    following_ring[following],
                    current[following],
                )
            )
    equator = rings[-1]
    for segment in range(longitude_segments):
        following = (segment + 1) % longitude_segments
        faces.append((cap_center, equator[following], equator[segment]))
    assembler.append(vertices, faces, bevel=True)


def _add_spoked_valve_y(
    assembler: MeshAssembler,
    *,
    center: tuple[float, float, float],
    radius: float,
    phase: float,
) -> None:
    """Append one compact front-facing three-spoke valve rotor."""

    x, y, z = center
    assembler.add_torus(
        major_radius=radius,
        minor_radius=0.026,
        major_segments=12,
        minor_segments=4,
        location=center,
        rotation=(_QUARTER_TURN, 0.0, 0.0),
    )
    assembler.add_cylinder(
        radius=0.055,
        depth=0.095,
        segments=8,
        location=center,
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    for index in range(3):
        angle = phase + index * (2.0 * math.pi / 3.0)
        assembler.add_box(
            size=(radius * 1.55, 0.050, 0.035),
            location=(x, y, z),
            rotation=(0.0, -angle, 0.0),
            bevel=False,
        )


def build_household_debt() -> ModelGeometry:
    """Build a weighted balance beam around one tightening helical coil."""

    body = MeshAssembler()
    accent = MeshAssembler()

    beam_angle = math.radians(-4.0)
    body.add_rounded_box_y(
        width=1.32,
        height=0.17,
        depth=0.32,
        radius=0.055,
        corner_segments=2,
        location=(0.0, 0.0, 0.34),
        rotation=(0.0, beam_angle, 0.0),
        bevel=True,
    )
    body.add_extruded_polygon_y(
        ((-0.30, -0.58), (0.30, -0.58), (0.0, 0.24)),
        depth=0.56,
        location=(0.0, 0.0, 0.0),
        bevel=True,
    )
    body.add_cylinder(
        radius=0.13,
        depth=0.44,
        segments=12,
        location=(0.0, 0.0, 0.35),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    for x, rod_top, weight_radius, weight_depth, weight_z in (
        (-0.44, 0.38, 0.26, 0.35, -0.20),
        (0.44, 0.30, 0.21, 0.47, -0.17),
    ):
        body.add_cylinder_between(
            (x, 0.0, rod_top),
            (x, 0.0, weight_z + weight_depth * 0.5),
            radius=0.035,
            segments=8,
        )
        body.add_cylinder(
            radius=weight_radius,
            depth=weight_depth,
            segments=14,
            location=(x, 0.0, weight_z),
            bevel=True,
        )
    body.add_cylinder(
        radius=0.16,
        depth=0.22,
        segments=12,
        location=(0.0, 0.0, 0.54),
        bevel=True,
    )

    _add_helix_tube_z(
        accent,
        radius=0.34,
        height=0.56,
        turns=2.25,
        tube_radius=0.032,
        path_segments=36,
        tube_segments=6,
    )
    for z in (-0.335, 0.335):
        accent.add_cylinder(
            radius=0.15,
            depth=0.085,
            segments=12,
            location=(0.0, 0.0, z),
            bevel=True,
        )
    accent.add_box(
        size=(0.11, 0.07, 0.10),
        location=(0.30, 0.0, 0.27),
        rotation=(0.0, math.radians(-18.0), 0.0),
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:wide weighted balance beam above a triangular compression fulcrum;"
            "side:deep central bearing wrapped by one exposed tightening coil;"
            "top:asymmetric suspended masses opposed across a keyed coil axis"
        ),
        body_detail="weighted balance beam, unequal suspended masses, and compression fulcrum",
        accent_pivot="tightening coil axis; rotate glTF Y / Blender Z",
        accent_origin=(0.0, 0.0, 0.0),
    )


def build_commodity() -> ModelGeometry:
    """Build a machined open crucible around interlocked fractured ore."""

    body = MeshAssembler()
    accent = MeshAssembler()

    body.add_rounded_rect_ring_y(
        outer_width=1.44,
        outer_height=1.26,
        inner_width=1.08,
        inner_height=0.88,
        depth=0.18,
        outer_radius=0.16,
        inner_radius=0.10,
        corner_segments=2,
        location=(0.0, 0.20, 0.0),
        bevel=True,
    )
    _add_hollow_frustum_z(
        body,
        outer_bottom_radius=0.50,
        outer_top_radius=0.65,
        inner_bottom_radius=0.27,
        inner_top_radius=0.45,
        outer_bottom_z=-0.57,
        inner_bottom_z=-0.34,
        top_z=0.22,
        segments=14,
        bevel=True,
    )
    body.add_cylinder(
        radius=0.58,
        depth=0.13,
        segments=14,
        location=(0.0, 0.0, -0.565),
        bevel=True,
    )
    for x in (-0.61, 0.61):
        body.add_box(
            size=(0.13, 0.24, 0.33),
            location=(x, 0.12, -0.37),
            bevel=True,
        )

    _add_faceted_ore_core(accent, scale=1.18)
    accent.add_cylinder(
        radius=0.19,
        depth=0.10,
        segments=12,
        location=(0.0, 0.0, -0.35),
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:two skewed truncated ore chunks locked inside a broad-shouldered crucible;"
            "side:hollow tapered vessel suspended in a rear machining yoke;"
            "top:offset fractured plates interlock without a centered crystal apex"
        ),
        body_detail="open machined crucible, deep thermal wall, rear yoke, and clamp feet",
        accent_pivot="faceted ore-core lift center; glTF Y equals Blender Z",
        accent_origin=(0.0, 0.0, 0.0),
    )


def build_fiscal() -> ModelGeometry:
    """Build a one-to-three distribution manifold with calibrated valve faces."""

    body = MeshAssembler()
    accent = MeshAssembler()

    body.add_cylinder(
        radius=0.23,
        depth=1.16,
        segments=14,
        location=(0.0, 0.0, -0.03),
        rotation=(0.0, _QUARTER_TURN, 0.0),
        bevel=True,
    )
    outlets = ((-0.48, 0.43), (0.0, 0.52), (0.48, 0.43))
    for x, z in outlets:
        body.add_cylinder_between(
            (x * 0.58, 0.0, 0.05),
            (x, 0.0, z),
            radius=0.075,
            segments=8,
            bevel=x == 0.0,
        )
        body.add_cylinder(
            radius=0.15,
            depth=0.25,
            segments=10,
            location=(x, 0.0, z),
            rotation=(_QUARTER_TURN, 0.0, 0.0),
        )
    body.add_cylinder_between(
        (0.0, 0.0, -0.10),
        (0.0, 0.0, -0.63),
        radius=0.10,
        segments=10,
        bevel=True,
    )
    body.add_cylinder(
        radius=0.19,
        depth=0.22,
        segments=12,
        location=(0.0, 0.0, -0.61),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    for x in (-0.58, 0.58):
        body.add_box(
            size=(0.20, 0.34, 0.14),
            location=(x, 0.0, -0.58),
            bevel=True,
        )
    # Rear supply-header drum paired with the inlet barrel (a real distribution
    # manifold runs a supply header behind the outlet rail).  It hides behind
    # the barrel in the front view (x +/-0.45 < barrel +/-0.58, same z band) so
    # the one-inlet/three-crown silhouette is untouched; the side view gains the
    # double-barrel depth.  Header spans y +0.10..+0.58; two link tubes tie it
    # down onto the inlet barrel.
    body.add_cylinder(
        radius=0.24,
        depth=0.90,
        segments=14,
        location=(0.0, 0.34, -0.03),
        rotation=(0.0, _QUARTER_TURN, 0.0),
        bevel=True,
    )
    for x in (-0.30, 0.30):
        body.add_cylinder_between(
            (x, 0.05, -0.03),
            (x, 0.34, -0.03),
            radius=0.06,
            segments=8,
        )

    valve_y = -0.18
    for index, (x, z) in enumerate(outlets):
        _add_spoked_valve_y(
            accent,
            center=(x, valve_y, z),
            radius=0.125,
            phase=math.radians(12.0 + index * 18.0),
        )
    accent.add_box(
        # The canonical 0.035 bevel needs more than 0.07 across both minor
        # dimensions.  A 0.09 square distribution spine keeps the three valve
        # faces mechanically linked without clamp-overlap collapsing corners
        # into zero-area evaluated polygons.
        size=(1.04, 0.09, 0.09),
        location=(0.0, valve_y + 0.03, 0.17),
        bevel=True,
    )

    valve_bank_origin = (0.0, valve_y, 0.46)
    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:one low inlet branches into three calibrated outlet crowns;"
            "side:deep barrel manifold carrying a forward valve bank;"
            "top:three spaced control faces keyed to one distribution spine"
        ),
        body_detail="single-inlet budget manifold, three rising branches, and calibrated outlets",
        accent_pivot="three-outlet valve-bank center; glTF Z equals Blender -Y",
        accent_origin=valve_bank_origin,
    )


def build_geopolitics() -> ModelGeometry:
    """Build split shield shells held by opposed diagonal C-clamps."""

    body = MeshAssembler()
    accent = MeshAssembler()

    _add_half_ellipsoid_x(
        body,
        sign=-1.0,
        radii=(0.51, 0.37, 0.49),
        longitude_segments=12,
        latitude_steps=4,
        offset_x=-0.045,
    )
    _add_half_ellipsoid_x(
        body,
        sign=1.0,
        radii=(0.51, 0.37, 0.49),
        longitude_segments=12,
        latitude_steps=4,
        offset_x=0.045,
    )
    body.add_cylinder(
        radius=0.065,
        depth=1.34,
        segments=12,
        location=(0.0, 0.0, 0.0),
        bevel=True,
    )
    for z in (-0.60, 0.60):
        body.add_rounded_box_y(
            width=1.18,
            height=0.12,
            depth=0.30,
            radius=0.035,
            corner_segments=2,
            location=(0.0, 0.0, z),
            bevel=True,
        )
    body.add_box(
        size=(0.24, 0.52, 0.18),
        location=(-0.56, 0.0, -0.27),
        rotation=(0.0, math.radians(-18.0), 0.0),
        bevel=True,
    )
    body.add_box(
        size=(0.24, 0.46, 0.24),
        location=(0.56, 0.0, 0.27),
        rotation=(0.0, math.radians(12.0), 0.0),
        bevel=True,
    )

    clamp_y = -0.375
    _add_diagonal_c_clamp_y(
        accent,
        width=0.42,
        height=0.62,
        bar_width=0.055,
        depth=0.075,
        location=(-0.20, clamp_y, -0.02),
        rotation_y=math.radians(14.0),
        open_direction=1,
    )
    _add_diagonal_c_clamp_y(
        accent,
        width=0.42,
        height=0.62,
        bar_width=0.055,
        depth=0.075,
        location=(0.20, clamp_y, 0.02),
        rotation_y=math.radians(-12.0),
        open_direction=-1,
    )

    # Each outer spine terminates in one explicit shoe nested into an unequal
    # dark torsion stop.  Small inner axle shoes keep the opposed brackets
    # mechanically tied without reconstructing any circular orbit.
    accent.add_box(
        size=(0.15, 0.08, 0.09),
        location=(-0.48, clamp_y, -0.23),
        rotation=(0.0, math.radians(-18.0), 0.0),
        bevel=True,
    )
    accent.add_box(
        size=(0.14, 0.08, 0.10),
        location=(0.48, clamp_y, 0.23),
        rotation=(0.0, math.radians(12.0), 0.0),
        bevel=True,
    )
    for z in (-0.43, 0.43):
        accent.add_cylinder(
            radius=0.08,
            depth=0.075,
            segments=12,
            location=(0.0, clamp_y, z),
            rotation=(_QUARTER_TURN, 0.0, 0.0),
            bevel=True,
        )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:split shield lobes gripped by two opposed diagonal C-clamps;"
            "side:shallow armored shells tied by two offset open-backed brackets;"
            "top:nonconcentric clamp spines terminate at unequal side torsion stops"
        ),
        body_detail="split faceted shield shells, long tension axle, and asymmetric torsion stops",
        accent_pivot="opposed C-clamp tension axis; rotate glTF Y / Blender Z",
        accent_origin=(0.0, 0.0, 0.0),
    )


def build_tech() -> ModelGeometry:
    """Build a clipped chip lattice around a recessed compressor impeller."""

    body = MeshAssembler()
    accent = MeshAssembler()

    body.add_rounded_rect_ring_y(
        outer_width=1.46,
        outer_height=1.28,
        inner_width=1.02,
        inner_height=0.84,
        depth=0.18,
        outer_radius=0.16,
        inner_radius=0.11,
        corner_segments=3,
        bevel=True,
    )
    for z in (-0.39, 0.39):
        body.add_box(
            size=(1.08, 0.12, 0.075),
            location=(0.0, 0.04, z),
            bevel=True,
        )
    for x in (-0.50, 0.50):
        body.add_box(
            size=(0.075, 0.12, 0.78),
            location=(x, 0.04, 0.0),
            bevel=True,
        )
    for x, z in ((-0.58, -0.48), (-0.58, 0.48), (0.58, -0.48), (0.58, 0.48)):
        body.add_cylinder(
            radius=0.105,
            depth=0.16,
            segments=10,
            location=(x, -0.02, z),
            rotation=(_QUARTER_TURN, 0.0, 0.0),
        )

    # A recessed shroud and a counter-swept stator stage separate this from a
    # generic exposed PC fan.  The chip rails retain the dominant square
    # silhouette while the compressor sits inside their protected bay.
    body.add_torus(
        major_radius=0.36,
        minor_radius=0.035,
        major_segments=12,
        minor_segments=4,
        location=(0.0, -0.105, 0.0),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
    )
    for index in range(6):
        angle = math.radians(7.0 + index * 60.0)
        stator_points = _swept_foil_points(
            angle=angle,
            inner_radius=0.315,
            middle_radius=0.365,
            outer_radius=0.420,
            sweep=math.radians(-12.0),
            inner_half_width=math.radians(2.6),
            middle_half_width=math.radians(2.0),
            outer_half_width=math.radians(1.5),
        )
        body.add_extruded_polygon_y(
            (stator_points[0], stator_points[2], stator_points[3], stator_points[5]),
            depth=0.050,
            location=(0.0, -0.12, 0.0),
        )
    body.add_cylinder(
        radius=0.13,
        depth=0.10,
        segments=12,
        location=(0.0, -0.105, 0.0),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
    )
    # Rear axial-compressor casing barrel behind the chip cage, plus a rear
    # bearing boss.  Both sit on Blender +Y so the square front outline is
    # untouched (r=0.40 < inner-window half 0.42); the side view gains the
    # barrel-behind-cage profile.  Casing spans y +0.10..+0.44, boss to +0.53.
    # bevel=False on the casing keeps the model clear of the 3000 hard cap; the
    # machined rim reads as a sharp compressor case edge either way.
    body.add_cylinder(
        radius=0.40,
        depth=0.34,
        segments=14,
        location=(0.0, 0.27, 0.0),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=False,
    )
    body.add_cylinder(
        radius=0.14,
        depth=0.12,
        segments=10,
        location=(0.0, 0.47, 0.0),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
    )

    rotor_origin = (0.0, -0.18, 0.0)
    accent.add_cylinder(
        radius=0.245,
        depth=0.075,
        segments=12,
        location=(0.0, -0.165, 0.0),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
    )
    accent.add_cylinder(
        radius=0.075,
        depth=0.17,
        segments=12,
        location=(0.0, -0.215, 0.0),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    for index in range(7):
        angle = math.radians(5.0 + index * (360.0 / 7.0))
        accent.add_extruded_polygon_y(
            _swept_foil_points(
                angle=angle,
                inner_radius=0.095,
                middle_radius=0.190,
                outer_radius=0.292,
                sweep=math.radians(30.0),
                inner_half_width=math.radians(8.0),
                middle_half_width=math.radians(6.0),
                outer_half_width=math.radians(3.5),
            ),
            depth=0.110,
            location=(0.0, -0.205, 0.0),
            bevel=index not in {3, 5},
        )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:square chip cage recesses a seven-foil swept compressor impeller;"
            "side:counter-swept stator and shroud sit behind a thin rotor backplate;"
            "top:rectilinear circuit rails protect a compact bearing-led compressor core"
        ),
        body_detail="clipped chip frame, recessed stator shroud, circuit rails, and central bearing",
        accent_pivot="compressor impeller bearing hub; glTF Z equals Blender -Y",
        accent_origin=rotor_origin,
    )


def build_consumer_conf() -> ModelGeometry:
    """Build a wide stability horizon with one central confidence vane."""

    body = MeshAssembler()
    accent = MeshAssembler()

    body.add_rounded_rect_ring_y(
        outer_width=1.56,
        outer_height=0.78,
        inner_width=1.23,
        inner_height=0.45,
        depth=0.20,
        outer_radius=0.13,
        inner_radius=0.08,
        corner_segments=3,
        bevel=True,
    )
    for z in (-0.13, 0.13):
        body.add_rounded_box_y(
            width=1.18,
            height=0.075,
            depth=0.14,
            radius=0.025,
            corner_segments=2,
            location=(0.0, 0.0, z),
            bevel=True,
        )
    for x in (-0.68, 0.68):
        body.add_cylinder(
            radius=0.12,
            depth=0.22,
            segments=10,
            location=(x, 0.0, 0.0),
            rotation=(_QUARTER_TURN, 0.0, 0.0),
            bevel=True,
        )
    body.add_box(size=(0.34, 0.24, 0.12), location=(-0.46, 0.0, -0.43))
    body.add_box(size=(0.22, 0.24, 0.12), location=(0.53, 0.0, -0.43))
    # Rear gauge can along Blender Y (behind the horizon frame): carries the
    # missing depth without touching the front X-Z silhouette.  r=0.30 stays
    # inside the outer frame half-height (0.39), so only the window interior
    # fills; the can spans y +0.10..+0.70.
    body.add_cylinder(
        radius=0.30,
        depth=0.60,
        segments=12,
        location=(0.0, 0.40, 0.0),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )

    vane_origin = (0.0, -0.17, 0.0)
    accent.add_extruded_polygon_y(
        (
            (-0.11, -0.30),
            (0.11, -0.30),
            (0.16, -0.02),
            (0.07, 0.30),
            (-0.07, 0.30),
            (-0.16, -0.02),
        ),
        depth=0.15,
        location=vane_origin,
        bevel=True,
    )
    accent.add_cylinder(
        radius=0.105,
        depth=0.15,
        segments=12,
        location=(0.0, -0.17, -0.06),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    accent.add_box(
        size=(0.56, 0.08, 0.075),
        location=(0.0, -0.17, 0.04),
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:long double horizon frame crossed by one compact central vane;"
            "side:shallow damped chassis with a forward translating stabilizer;"
            "top:wide rectangular datum with no hanging or pendulum mass"
        ),
        body_detail="wide dual-rail horizon frame, side dampers, and unequal datum feet",
        accent_pivot="central confidence-vane lift center; glTF Y equals Blender Z",
        accent_origin=vane_origin,
    )


__all__ = (
    "build_household_debt",
    "build_commodity",
    "build_fiscal",
    "build_geopolitics",
    "build_tech",
    "build_consumer_conf",
)
