"""Precision instruments for the real-economy and equity batch.

Each builder is scene-independent.  It appends closed, disconnected shells to
one body and one accent assembler while leaving normalization, materials,
object creation, and export to the shared authoring pipeline.  Coordinates use
Blender's +Z-up, -Y-front convention.  Runtime glTF axes therefore map back to
Blender as ``(x, z, -y)``.
"""

from __future__ import annotations

import math

from hard_surface import MeshAssembler, ModelGeometry


_QUARTER_TURN = math.pi * 0.5


def _annular_sector_points(
    inner_radius: float,
    outer_radius: float,
    start_angle: float,
    end_angle: float,
    steps: int = 3,
) -> list[tuple[float, float]]:
    """Return a deterministic XZ annular-sector loop for Y extrusion."""

    outer: list[tuple[float, float]] = []
    inner: list[tuple[float, float]] = []
    for index in range(steps + 1):
        ratio = index / steps
        angle = start_angle + (end_angle - start_angle) * ratio
        outer.append(
            (outer_radius * math.cos(angle), outer_radius * math.sin(angle))
        )
    for index in reversed(range(steps + 1)):
        ratio = index / steps
        angle = start_angle + (end_angle - start_angle) * ratio
        inner.append(
            (inner_radius * math.cos(angle), inner_radius * math.sin(angle))
        )
    return outer + inner


def build_consumption() -> ModelGeometry:
    """Build an asymmetric demand flywheel with one keyed clutch shoe."""

    body = MeshAssembler()
    accent = MeshAssembler()

    flywheel_center = (0.0, 0.02, 0.03)
    body.add_torus(
        major_radius=0.58,
        minor_radius=0.11,
        major_segments=26,
        minor_segments=6,
        location=flywheel_center,
        rotation=(_QUARTER_TURN, 0.0, 0.0),
    )
    body.add_cylinder(
        radius=0.43,
        depth=0.17,
        segments=24,
        location=(0.0, 0.08, 0.03),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    # The hub barrel is extended rearward (deep along Blender Y, the thin axis)
    # and capped by a bearing can so the flywheel gains real depth instead of
    # reading as a shallow coin.  The front face stays at y=-0.15.
    body.add_cylinder(
        radius=0.18,
        depth=0.56,
        segments=18,
        location=(0.0, 0.13, 0.03),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    body.add_cylinder(
        radius=0.30,
        depth=0.26,
        segments=18,
        location=(0.0, 0.40, 0.03),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    # Unequal inertia masses and a compact brake shoe break the equal-spoke
    # fan language.  Their crisp faces sit against the curved continuous rim.
    rim_masses = (
        (42.0, 28.0, 0.50, 0.72, 0.16, -0.010),
        (174.0, 19.0, 0.51, 0.68, 0.14, 0.015),
        (-104.0, 13.0, 0.54, 0.73, 0.12, -0.025),
    )
    for center_degrees, half_sweep_degrees, inner, outer, depth, y in rim_masses:
        center_angle = math.radians(center_degrees)
        half_sweep = math.radians(half_sweep_degrees)
        body.add_extruded_polygon_y(
            _annular_sector_points(
                inner_radius=inner,
                outer_radius=outer,
                start_angle=center_angle - half_sweep,
                end_angle=center_angle + half_sweep,
                steps=3,
            ),
            depth=depth,
            location=(0.0, y, flywheel_center[2]),
        )
    brake_angle = math.radians(-104.0)
    body.add_box(
        size=(0.15, 0.16, 0.20),
        location=(
            0.63 * math.cos(brake_angle),
            -0.10,
            flywheel_center[2] + 0.63 * math.sin(brake_angle),
        ),
        rotation=(0.0, math.radians(14.0), 0.0),
    )

    # The unequal cradle prevents this low rotor from reading as a coin or as
    # the open counterweight geometry used by GDP.
    body.add_rounded_box_y(
        width=1.18,
        height=0.14,
        depth=0.52,
        radius=0.035,
        corner_segments=2,
        location=(-0.02, 0.13, -0.68),
        bevel=True,
    )
    body.add_rounded_box_y(
        width=0.16,
        height=0.34,
        depth=0.32,
        radius=0.035,
        corner_segments=2,
        location=(-0.46, 0.07, -0.53),
        bevel=True,
    )
    body.add_rounded_box_y(
        width=0.22,
        height=0.26,
        depth=0.32,
        radius=0.040,
        corner_segments=2,
        location=(0.42, 0.07, -0.57),
        bevel=True,
    )

    vane_origin = (0.0, -0.16, 0.03)
    clutch_angle = math.radians(-18.0)
    # The clutch greeble is enlarged in step with the deeper body so the accent
    # keeps at least a tenth of the total surface area after the new hub can and
    # bearing barrel raise the body area.
    accent.add_extruded_polygon_y(
        _annular_sector_points(
            inner_radius=0.24,
            outer_radius=0.55,
            start_angle=clutch_angle - math.radians(32.0),
            end_angle=clutch_angle + math.radians(32.0),
            steps=3,
        ),
        depth=0.16,
        location=(0.0, -0.19, vane_origin[2]),
        bevel=True,
    )
    accent.add_cylinder(
        radius=0.14,
        depth=0.24,
        segments=12,
        location=vane_origin,
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    accent.add_rounded_box_y(
        width=0.38,
        height=0.15,
        depth=0.15,
        radius=0.030,
        corner_segments=2,
        location=(
            0.25 * math.cos(clutch_angle),
            -0.19,
            vane_origin[2] + 0.25 * math.sin(clutch_angle),
        ),
        rotation=(0.0, math.radians(18.0), 0.0),
    )
    accent.add_box(
        size=(0.16, 0.16, 0.22),
        location=(
            0.51 * math.cos(clutch_angle),
            -0.19,
            vane_origin[2] + 0.51 * math.sin(clutch_angle),
        ),
        rotation=(0.0, math.radians(18.0), 0.0),
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:continuous inertia flywheel weighted by three unequal rim masses and one keyed clutch sector;"
            "side:shallow rear web with a forward clutch shoe and offset brake block;"
            "top:asymmetric mass distribution around one compact axial clutch assembly"
        ),
        body_detail="continuous demand flywheel, three unequal inertia masses, offset brake shoe, and bearing cradle",
        accent_pivot="inertia flywheel clutch axis; scale XYZ about the central hub",
        accent_origin=vane_origin,
    )


def build_investment() -> ModelGeometry:
    """Build a capital mast carrying one deployable triangular lattice."""

    body = MeshAssembler()
    accent = MeshAssembler()

    # The mast and ballast foot are deepened along Blender Y (the thin axis) and
    # a machinery house is bolted to the mast root so the capital stack gains
    # genuine front-to-back body depth.  The accent truss stays thin on Y.
    body.add_rounded_box_y(
        width=0.22,
        height=1.30,
        depth=0.46,
        radius=0.050,
        corner_segments=2,
        location=(-0.47, 0.05, 0.03),
        bevel=True,
    )
    body.add_rounded_box_y(
        width=1.18,
        height=0.18,
        depth=0.86,
        radius=0.045,
        corner_segments=2,
        location=(-0.03, 0.05, -0.69),
        bevel=True,
    )
    body.add_rounded_box_y(
        width=0.55,
        height=0.46,
        depth=0.55,
        radius=0.050,
        corner_segments=2,
        location=(-0.42, 0.28, -0.42),
        bevel=True,
    )
    body.add_rounded_box_y(
        width=0.42,
        height=0.18,
        depth=0.38,
        radius=0.045,
        corner_segments=2,
        location=(-0.38, 0.05, 0.69),
    )
    body.add_cylinder(
        radius=0.22,
        depth=0.44,
        segments=16,
        location=(-0.47, 0.0, -0.39),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    body.add_torus(
        major_radius=0.23,
        minor_radius=0.050,
        major_segments=16,
        minor_segments=6,
        location=(-0.47, -0.24, -0.39),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
    )
    body.add_cylinder_between(
        (-0.43, 0.16, 0.53),
        (-0.13, 0.16, -0.60),
        radius=0.050,
        segments=9,
    )
    body.add_cylinder_between(
        (-0.54, 0.16, 0.48),
        (-0.78, 0.16, -0.57),
        radius=0.044,
        segments=9,
    )
    body.add_rounded_rect_ring_y(
        outer_width=0.46,
        outer_height=1.20,
        inner_width=0.26,
        inner_height=0.98,
        depth=0.12,
        outer_radius=0.070,
        inner_radius=0.040,
        corner_segments=2,
        location=(-0.47, -0.14, 0.03),
        bevel=True,
    )

    hinge = (-0.31, -0.22, -0.34)
    upper_tip = (0.78, -0.22, 0.57)
    lower_tip = (0.80, -0.22, 0.13)
    upper_mid = (0.24, -0.22, 0.20)
    lower_mid = (0.25, -0.22, -0.11)
    truss_members = (
        (hinge, upper_tip),
        (hinge, lower_tip),
        (lower_tip, upper_tip),
        (upper_mid, lower_mid),
        (hinge, upper_mid),
        (lower_mid, upper_tip),
        (upper_mid, lower_tip),
    )
    for index, (start, end) in enumerate(truss_members):
        member_radius = 0.045 if index < 3 else 0.022
        accent.add_cylinder_between(
            start,
            end,
            radius=member_radius,
            segments=8,
            bevel=index < 3,
        )
    accent.add_cylinder(
        radius=0.10,
        depth=0.28,
        segments=12,
        location=hinge,
        rotation=(0.0, _QUARTER_TURN, 0.0),
        bevel=True,
    )
    accent.add_rounded_box_y(
        width=0.12,
        height=0.20,
        depth=0.11,
        radius=0.030,
        corner_segments=2,
        location=(0.79, -0.22, 0.35),
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:one tall counterbraced capital mast carrying a tapered triangular boom;"
            "side:forward lattice separated from a deep fixed mast and ballast foot;"
            "top:narrow deployable truss hinged ahead of an asymmetric vertical standard"
        ),
        body_detail="vertical capital mast, diagonal backstays, hinge gearbox, and broad ballast foot",
        accent_pivot="lower truss hinge; rotate about glTF X / Blender X",
        accent_origin=hinge,
    )


def build_employment() -> ModelGeometry:
    """Build three load columns captured by one translating locking ring."""

    body = MeshAssembler()
    accent = MeshAssembler()

    # Columns are shortened slightly (lowering the long Z axis) and deepened
    # along Blender Y, and the foundation is thickened with two rear buttresses
    # so the frame stops reading as a flat plate edge-on.
    column_specs = (
        (-0.43, 0.92),
        (0.00, 1.08),
        (0.43, 0.86),
    )
    base_z = -0.50
    for x, height in column_specs:
        center_z = base_z + height * 0.5
        body.add_rounded_box_y(
            width=0.22,
            height=height,
            depth=0.44,
            radius=0.052,
            corner_segments=2,
            location=(x, 0.03, center_z),
            bevel=True,
        )
        body.add_cylinder(
            radius=0.135,
            depth=0.46,
            segments=12,
            location=(x, 0.03, base_z + height),
            rotation=(_QUARTER_TURN, 0.0, 0.0),
            bevel=x == 0.0,
        )
        body.add_box(
            size=(0.055, 0.055, height * 0.66),
            location=(x, -0.175, center_z),
        )
    body.add_rounded_box_y(
        width=1.26,
        height=0.17,
        depth=0.80,
        radius=0.045,
        corner_segments=2,
        location=(0.0, 0.08, -0.59),
        bevel=True,
    )
    body.add_rounded_box_y(
        width=0.20,
        height=0.62,
        depth=0.30,
        radius=0.040,
        corner_segments=2,
        location=(-0.215, 0.33, -0.16),
        bevel=True,
    )
    body.add_rounded_box_y(
        width=0.20,
        height=0.50,
        depth=0.30,
        radius=0.040,
        corner_segments=2,
        location=(0.215, 0.33, -0.22),
        bevel=True,
    )
    body.add_box(
        size=(0.46, 0.38, 0.10),
        location=(-0.34, 0.03, -0.70),
    )

    ring_origin = (0.0, -0.075, 0.20)
    accent.add_rounded_rect_ring_y(
        outer_width=1.18,
        outer_height=0.25,
        inner_width=0.98,
        inner_height=0.11,
        depth=0.24,
        outer_radius=0.075,
        inner_radius=0.035,
        corner_segments=3,
        location=ring_origin,
        bevel=True,
    )
    accent.add_rounded_box_y(
        width=0.18,
        height=0.18,
        depth=0.22,
        radius=0.040,
        corner_segments=2,
        location=(0.0, -0.14, ring_origin[2]),
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:three unequal capped load columns captured by one thin horizontal lock;"
            "side:deep foundation rail behind a shallow translating coupling frame;"
            "top:single wide locking ring crossing three separated column axes"
        ),
        body_detail="three unequal load columns, inspection splines, cap bearings, and shared foundation",
        accent_pivot="three-column locking-ring centroid; translate along glTF Y / Blender Z",
        accent_origin=ring_origin,
    )


def build_earnings() -> ModelGeometry:
    """Build an open profit C-frame with a diagonal datum channel."""

    body = MeshAssembler()
    accent = MeshAssembler()

    # An open, left-heavy C frame replaces the former roof-like solid mass.
    body.add_rounded_box_y(
        width=0.22,
        height=1.10,
        depth=0.56,
        radius=0.050,
        corner_segments=2,
        location=(-0.48, 0.04, 0.00),
        bevel=True,
    )
    body.add_rounded_box_y(
        width=1.08,
        height=0.18,
        depth=0.62,
        radius=0.045,
        corner_segments=2,
        location=(-0.02, 0.04, -0.53),
        bevel=True,
    )
    body.add_rounded_box_y(
        width=0.72,
        height=0.16,
        depth=0.50,
        radius=0.040,
        corner_segments=2,
        location=(-0.24, 0.04, 0.51),
        bevel=True,
    )
    body.add_rounded_box_y(
        width=0.18,
        height=0.38,
        depth=0.52,
        radius=0.040,
        corner_segments=2,
        location=(0.43, 0.04, -0.36),
        bevel=True,
    )

    datum_angle = math.radians(-38.0)
    body.add_rounded_box_y(
        width=1.02,
        height=0.075,
        depth=0.13,
        radius=0.025,
        corner_segments=2,
        location=(-0.02, -0.04, 0.03),
        rotation=(0.0, datum_angle, 0.0),
        bevel=True,
    )
    body.add_rounded_box_y(
        width=0.88,
        height=0.065,
        depth=0.10,
        radius=0.022,
        corner_segments=2,
        location=(-0.05, 0.10, 0.12),
        rotation=(0.0, datum_angle, 0.0),
    )
    body.add_cylinder(
        radius=0.14,
        depth=0.16,
        segments=12,
        location=(-0.36, -0.17, -0.25),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )

    carrier_origin = (0.02, -0.35, 0.02)
    step_specs = (
        (-0.25, -0.21, 0.38),
        (0.03, 0.02, 0.36),
        (0.31, 0.25, 0.34),
    )
    for x, z, width in step_specs:
        accent.add_rounded_box_y(
            width=width,
            height=0.16,
            depth=0.18,
            radius=0.030,
            corner_segments=2,
            location=(x, carrier_origin[1], z),
            bevel=True,
        )
    accent.add_cylinder_between(
        (-0.40, carrier_origin[1] + 0.015, -0.30),
        (0.40, carrier_origin[1] + 0.015, 0.34),
        radius=0.045,
        segments=8,
        bevel=True,
    )
    accent.add_cylinder(
        radius=0.090,
        depth=0.16,
        segments=8,
        location=(0.31, carrier_origin[1], 0.35),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:open left-heavy C frame exposing an enlarged three-step shuttle on a diagonal datum;"
            "side:deep fixed standards behind a thin forward stair carrier;"
            "top:paired diagonal channel rails opening into an asymmetric right-side service gap"
        ),
        body_detail="open profit C frame, paired diagonal datum channel, offset bearing boss, and deep plinth",
        accent_pivot="stair-carrier centroid; translate along glTF Y / Blender Z",
        accent_origin=carrier_origin,
    )


def build_defaults() -> ModelGeometry:
    """Build an upright pressure vessel with a controlled fracture latch."""

    body = MeshAssembler()
    accent = MeshAssembler()

    body.add_cylinder(
        radius=0.44,
        depth=0.80,
        segments=20,
        location=(0.0, 0.02, 0.02),
        bevel=True,
    )
    body.add_uv_sphere(
        radius=0.44,
        segments=18,
        rings=5,
        location=(0.0, 0.02, 0.43),
        scale=(1.0, 1.0, 0.31),
    )
    body.add_uv_sphere(
        radius=0.44,
        segments=18,
        rings=5,
        location=(0.0, 0.02, -0.39),
        scale=(1.0, 1.0, 0.31),
    )
    for z in (-0.38, 0.42):
        body.add_torus(
            major_radius=0.44,
            minor_radius=0.052,
            major_segments=16,
            minor_segments=6,
            location=(0.0, 0.02, z),
        )
    for x in (-0.37, 0.37):
        body.add_rounded_box_y(
            width=0.085,
            height=0.72,
            depth=0.10,
            radius=0.020,
            corner_segments=1,
            location=(x, -0.405, 0.02),
        )
    body.add_rounded_box_y(
        width=0.96,
        height=0.14,
        depth=0.50,
        radius=0.035,
        corner_segments=2,
        location=(0.0, 0.02, -0.62),
        bevel=True,
    )
    body.add_cylinder(
        radius=0.15,
        depth=0.18,
        segments=12,
        location=(0.18, 0.02, 0.66),
    )

    latch_origin = (0.12, -0.50, 0.05)
    fracture_points = (
        (-0.17, -0.50, 0.37),
        (-0.04, -0.50, 0.21),
        (-0.14, -0.50, 0.06),
        (0.01, -0.50, -0.10),
        (-0.09, -0.50, -0.30),
    )
    for start, end in zip(fracture_points, fracture_points[1:]):
        accent.add_cylinder_between(
            start,
            end,
            radius=0.040,
            segments=6,
        )
    accent.add_cylinder(
        radius=0.13,
        depth=0.13,
        segments=10,
        location=latch_origin,
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    accent.add_cylinder_between(
        latch_origin,
        (-0.12, -0.50, 0.05),
        radius=0.055,
        segments=8,
        bevel=True,
    )
    accent.add_rounded_box_y(
        width=0.18,
        height=0.24,
        depth=0.15,
        radius=0.030,
        corner_segments=2,
        location=(-0.15, -0.50, 0.05),
    )
    upper_keeper = (-0.16, -0.50, 0.20)
    lower_keeper = (-0.16, -0.50, -0.10)
    for keeper in (upper_keeper, lower_keeper):
        accent.add_cylinder_between(
            latch_origin,
            keeper,
            radius=0.055,
            segments=7,
        )
    accent.add_cylinder_between(
        upper_keeper,
        lower_keeper,
        radius=0.050,
        segments=7,
    )
    accent.add_torus(
        major_radius=0.15,
        minor_radius=0.030,
        major_segments=16,
        minor_segments=5,
        location=latch_origin,
        rotation=(_QUARTER_TURN, 0.0, 0.0),
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:upright banded pressure vessel crossed by a controlled zigzag release seam;"
            "side:deep cylindrical chamber with forward safety latch and low plinth;"
            "top:offset rupture cap above twin external stiffener rails"
        ),
        body_detail="upright banded pressure chamber, elliptical end bells, external stiffeners, and plinth",
        accent_pivot="safety-latch hinge; rotate about glTF Z / Blender -Y",
        accent_origin=latch_origin,
    )


def build_stocks() -> ModelGeometry:
    """Build captive order-book plungers with a two-rail price spindle."""

    body = MeshAssembler()
    accent = MeshAssembler()

    body.add_rounded_box_y(
        width=1.26,
        height=0.16,
        depth=0.74,
        radius=0.045,
        corner_segments=2,
        location=(0.0, 0.02, -0.55),
        bevel=True,
    )
    for y in (-0.27, 0.27):
        for z in (-0.43, 0.08):
            body.add_rounded_box_y(
                width=1.12,
                height=0.075,
                depth=0.10,
                radius=0.025,
                corner_segments=2,
                location=(0.0, y, z),
            )

    pin_specs = (
        (-0.49, -0.22, 0.56),
        (-0.18, -0.22, 0.86),
        (0.16, -0.22, 0.63),
        (0.49, -0.22, 0.94),
        (-0.39, 0.20, 0.77),
        (-0.06, 0.20, 0.49),
        (0.28, 0.20, 0.82),
        (0.54, 0.20, 0.60),
    )
    pin_base = -0.43
    for x, y, height in pin_specs:
        body.add_cylinder(
            radius=0.073,
            depth=height,
            segments=8,
            location=(x, y, pin_base + height * 0.5),
            bevel=y < 0.0,
        )
        body.add_cylinder(
            radius=0.105,
            depth=0.065,
            segments=8,
            location=(x, y, pin_base + 0.032),
        )
        body.add_cylinder(
            radius=0.098,
            depth=0.075,
            segments=8,
            location=(x, y, 0.08),
        )

    spindle_origin = (0.06, -0.36, 0.10)
    accent.add_cylinder(
        radius=0.064,
        depth=1.06,
        segments=12,
        location=(spindle_origin[0], spindle_origin[1], 0.10),
        bevel=True,
    )
    accent.add_cylinder(
        radius=0.145,
        depth=0.11,
        segments=12,
        location=spindle_origin,
        bevel=True,
    )
    accent.add_rounded_box_y(
        width=0.20,
        height=0.13,
        depth=0.68,
        radius=0.030,
        corner_segments=1,
        location=(spindle_origin[0], -0.02, spindle_origin[2]),
        bevel=True,
    )
    for y in (-0.27, 0.27):
        accent.add_cylinder(
            radius=0.095,
            depth=0.10,
            segments=8,
            location=(spindle_origin[0], y, spindle_origin[2]),
        )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:captive non-monotonic plungers pass through paired lower and upper order-book bridges;"
            "side:two staggered pin rows are locked between socket and guide collars;"
            "top:a traveling crosshead joins both rails to one forward price spindle"
        ),
        body_detail="captive two-row order plungers, lower sockets, upper guide collars, paired bridges, and deep bed",
        accent_pivot="price-spindle carriage center; translate along glTF Y / Blender Z",
        accent_origin=spindle_origin,
    )


__all__ = (
    "build_consumption",
    "build_investment",
    "build_employment",
    "build_earnings",
    "build_defaults",
    "build_stocks",
)
