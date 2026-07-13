"""Precision instruments for the monetary, financial, and price batch.

The builders in this module are deliberately scene-independent.  They append
closed, disconnected primitive shells to one body and one accent assembler,
then leave normalization, materials, object creation, and export to the shared
hard-surface authoring pipeline.  Coordinates use Blender's +Z-up, -Y-front
convention throughout.
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
    """Return a deterministic XZ annular-sector loop for extrusion along Y."""

    outer = []
    inner = []
    for index in range(steps + 1):
        ratio = index / steps
        angle = start_angle + (end_angle - start_angle) * ratio
        outer.append((outer_radius * math.cos(angle), outer_radius * math.sin(angle)))
    for index in reversed(range(steps + 1)):
        ratio = index / steps
        angle = start_angle + (end_angle - start_angle) * ratio
        inner.append((inner_radius * math.cos(angle), inner_radius * math.sin(angle)))
    return outer + inner


def build_market_rate() -> ModelGeometry:
    """Build a shallow twin maturity rail with one keyed moving carriage."""

    body = MeshAssembler()
    accent = MeshAssembler()

    rail_angle = math.radians(-10.0)
    for y, z in ((-0.24, 0.04), (0.24, -0.04)):
        body.add_capsule_x(
            half_length=0.60,
            radius=0.08,
            segments=24,
            hemisphere_steps=3,
            location=(0.0, y, z),
            rotation=(0.0, rail_angle, 0.0),
        )

    # Unequal end standards keep the rail from reading as a line chart.  The
    # short transverse ties provide the remaining exposed primary edge tags.
    # The standards are deepened in Y into full gantry posts that seat on the
    # instrument bed below, so the whole stand gains genuine front-back depth.
    body.add_box(
        size=(0.20, 0.84, 0.48),
        location=(-0.64, 0.0, -0.11),
        rotation=(0.0, rail_angle, 0.0),
        bevel=True,
    )
    body.add_box(
        size=(0.20, 0.84, 0.90),
        location=(0.64, 0.0, 0.02),
        rotation=(0.0, rail_angle, 0.0),
        bevel=True,
    )
    for x in (-0.42, 0.42):
        slope_z = -math.sin(rail_angle) * x
        body.add_cylinder_between(
            (x, -0.29, slope_z + 0.04),
            (x, 0.29, slope_z - 0.04),
            radius=0.045,
            segments=9,
            bevel=True,
        )
    body.add_box(
        size=(0.22, 0.16, 0.10),
        location=(-0.58, -0.23, -0.30),
    )
    # Instrument bed: the chassis the rail stand is bolted to.  It owns the
    # Blender-Y (front-back) extent that was previously the flat thin axis.
    body.add_box(
        size=(1.42, 0.88, 0.16),
        location=(0.0, 0.0, -0.42),
        bevel=True,
    )

    carriage_origin = (0.12, 0.0, 0.02)
    sleeve_centers = (
        (carriage_origin[0], -0.24, 0.061),
        (carriage_origin[0], 0.24, -0.019),
    )
    for center in sleeve_centers:
        accent.add_cylinder(
            radius=0.14,
            depth=0.30,
            segments=12,
            location=center,
            rotation=(0.0, _QUARTER_TURN, 0.0),
            bevel=True,
        )
    accent.add_cylinder_between(
        sleeve_centers[0],
        sleeve_centers[1],
        radius=0.06,
        segments=12,
        bevel=True,
    )
    accent.add_box(
        size=(0.14, 0.10, 0.22),
        location=(0.12, -0.32, 0.17),
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:shallow twin maturity rails crossed by one keyed carriage;"
            "side:staggered dual guides between unequal end standards;"
            "top:offset carriage bridging separated parallel tracks"
        ),
        body_detail="shallow twin maturity rails, unequal end standards, and transverse ties",
        accent_pivot="maturity carriage centroid; translate along glTF X / Blender X",
        accent_origin=carriage_origin,
    )


def build_liquidity() -> ModelGeometry:
    """Build a three-level circulation reservoir around a horizontal rotor."""

    body = MeshAssembler()
    accent = MeshAssembler()

    reservoirs = (
        (0.70, 0.10, 28, -0.38),
        (0.76, 0.10, 30, 0.00),
        (0.66, 0.10, 26, 0.38),
    )
    for major_radius, minor_radius, segments, z in reservoirs:
        body.add_torus(
            major_radius=major_radius,
            minor_radius=minor_radius,
            major_segments=segments,
            minor_segments=6,
            location=(0.0, 0.0, z),
        )
    body.add_cylinder(
        radius=0.14,
        depth=1.05,
        segments=16,
        location=(0.0, 0.0, 0.0),
        bevel=True,
    )
    body.add_cylinder(
        radius=0.34,
        depth=0.16,
        segments=12,
        location=(0.0, 0.0, -0.52),
        bevel=True,
    )
    for x, y in ((-0.49, 0.18), (0.43, 0.24), (0.10, -0.52)):
        body.add_cylinder_between(
            (x, y, -0.43),
            (x, y, 0.43),
            radius=0.045,
            segments=8,
        )

    rotor_origin = (0.0, 0.0, 0.03)
    accent.add_cylinder(
        radius=0.18,
        depth=0.16,
        segments=12,
        location=rotor_origin,
        bevel=True,
    )
    for index in range(3):
        angle = math.radians(index * 120.0)
        radius = 0.28
        accent.add_box(
            size=(0.54, 0.18, 0.14),
            location=(
                radius * math.cos(angle),
                radius * math.sin(angle),
                rotor_origin[2],
            ),
            rotation=(0.0, 0.0, angle),
            bevel=True,
        )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:three stacked reservoir bands around a central manifold;"
            "side:offset return posts and stepped storage levels;"
            "top:three unequal concentric loops around a three-vane rotor"
        ),
        body_detail="three unequal circulation reservoirs, return posts, and central manifold",
        accent_pivot="central circulation rotor hub; glTF Y equals Blender Z",
        accent_origin=rotor_origin,
    )


def build_credit_spread() -> ModelGeometry:
    """Build a horizontal calibration frame with opposed measuring jaws."""

    body = MeshAssembler()
    accent = MeshAssembler()

    body.add_capsule_x(
        half_length=0.66,
        radius=0.12,
        segments=28,
        hemisphere_steps=4,
        location=(0.0, 0.03, -0.42),
    )
    body.add_rounded_box_y(
        width=0.18,
        height=1.00,
        depth=0.56,
        radius=0.045,
        corner_segments=2,
        location=(-0.68, 0.03, -0.02),
        bevel=True,
    )
    body.add_rounded_box_y(
        width=0.34,
        height=0.16,
        depth=0.44,
        radius=0.040,
        corner_segments=2,
        location=(-0.51, 0.03, 0.31),
        bevel=True,
    )
    body.add_rounded_box_y(
        width=0.38,
        height=0.16,
        depth=0.44,
        radius=0.040,
        corner_segments=2,
        location=(-0.48, 0.03, -0.40),
        bevel=True,
    )
    body.add_cylinder(
        radius=0.16,
        depth=0.40,
        segments=14,
        location=(-0.62, -0.16, 0.04),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    # Calibration bench: a mounting plate the caliper frame beds into.  It
    # carries the Blender-Y (front-back) depth that was the flat thin axis.
    body.add_box(
        size=(1.36, 0.84, 0.14),
        location=(0.0, 0.0, -0.55),
        bevel=True,
    )

    jaw_origin = (0.40, 0.0, 0.02)
    accent.add_rounded_box_y(
        width=0.11,
        height=0.56,
        depth=0.22,
        radius=0.028,
        corner_segments=2,
        location=(0.40, 0.0, 0.00),
        bevel=True,
    )
    accent.add_rounded_box_y(
        width=0.18,
        height=0.10,
        depth=0.20,
        radius=0.025,
        corner_segments=2,
        location=(0.28, 0.0, 0.27),
    )
    accent.add_cylinder(
        radius=0.11,
        depth=0.26,
        segments=12,
        location=(0.40, 0.0, -0.42),
        rotation=(0.0, _QUARTER_TURN, 0.0),
        bevel=True,
    )
    # Vernier thumb roller: an unbeveled X-axis knurl that keeps the moving
    # jaw's accent-area share up as the body gains bench mass.
    accent.add_cylinder(
        radius=0.07,
        depth=0.16,
        segments=10,
        location=(0.54, 0.0, -0.20),
        rotation=(0.0, _QUARTER_TURN, 0.0),
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:open horizontal caliper with opposed unequal jaws;"
            "side:deep datum boss over a single slide beam;"
            "top:fixed gauge head opposed by a moving keyed collar"
        ),
        body_detail="horizontal calibration guide, fixed datum jaw, and gauge boss",
        accent_pivot="moving jaw slide center; translate along glTF X / Blender X",
        accent_origin=jaw_origin,
    )


def build_bank_lending() -> ModelGeometry:
    """Build a twin-barrel credit pump with one linked forward piston yoke."""

    body = MeshAssembler()
    accent = MeshAssembler()

    barrel_centers = ((-0.34, 0.02, 0.12), (0.34, 0.02, 0.12))
    for center in barrel_centers:
        body.add_cylinder(
            radius=0.25,
            depth=0.90,
            segments=16,
            location=center,
            rotation=(_QUARTER_TURN, 0.0, 0.0),
            bevel=True,
        )
        body.add_torus(
            major_radius=0.25,
            minor_radius=0.055,
            major_segments=22,
            minor_segments=6,
            location=(center[0], -0.39, center[2]),
            rotation=(_QUARTER_TURN, 0.0, 0.0),
        )
    body.add_box(
        size=(0.88, 0.22, 0.24),
        location=(0.0, 0.44, 0.05),
        bevel=True,
    )
    body.add_cylinder(
        radius=0.15,
        depth=0.20,
        segments=12,
        location=(0.40, 0.43, -0.24),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )

    piston_origin = (0.0, -0.43, 0.08)
    for x in (-0.34, 0.34):
        accent.add_cylinder(
            radius=0.22,
            depth=0.10,
            segments=14,
            location=(x, -0.46, 0.12),
            rotation=(_QUARTER_TURN, 0.0, 0.0),
            bevel=True,
        )
    accent.add_box(
        size=(0.86, 0.12, 0.14),
        location=(0.0, -0.50, -0.15),
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:twin pump faces over an asymmetric check-gate manifold;"
            "side:long paired barrels with one forward linked yoke;"
            "top:parallel cylinders joined by an offset rear manifold"
        ),
        body_detail="parallel credit barrels, front collars, rear manifold, and check gate",
        accent_pivot="linked piston-face center; glTF +Z advances along Blender -Y",
        accent_origin=piston_origin,
    )


def build_cpi() -> ModelGeometry:
    """Build a weighted price-index drum with one broken ratchet band."""

    body = MeshAssembler()
    accent = MeshAssembler()

    drum_center = (0.0, 0.03, 0.02)
    body.add_cylinder(
        radius=0.58,
        depth=0.42,
        segments=24,
        location=drum_center,
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    body.add_cylinder(
        radius=0.64,
        depth=0.13,
        segments=28,
        location=(0.0, 0.22, 0.02),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    body.add_cylinder(
        radius=0.17,
        depth=0.14,
        segments=14,
        location=(0.0, -0.27, 0.02),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    body.add_cylinder(
        radius=0.14,
        depth=0.12,
        segments=12,
        location=(0.0, 0.34, 0.02),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
    )

    sector_specs = (
        (-154.0, -99.0, 0.60),
        (-92.0, -31.0, 0.64),
        (-24.0, 39.0, 0.61),
        (46.0, 111.0, 0.66),
        (118.0, 176.0, 0.62),
    )
    for start_degrees, end_degrees, outer_radius in sector_specs:
        body.add_extruded_polygon_y(
            _annular_sector_points(
                inner_radius=0.43,
                outer_radius=outer_radius,
                start_angle=math.radians(start_degrees),
                end_angle=math.radians(end_degrees),
            ),
            depth=0.08,
            location=(0.0, -0.24, 0.02),
        )

    body.add_box(size=(1.28, 0.34, 0.13), location=(0.0, 0.08, -0.67))
    body.add_box(size=(0.14, 0.34, 0.42), location=(-0.57, 0.08, -0.49))
    body.add_box(size=(0.14, 0.34, 0.34), location=(0.57, 0.08, -0.53))

    index_origin = (0.0, -0.31, 0.02)
    accent.add_torus_arc(
        major_radius=0.70,
        minor_radius=0.065,
        start_angle=math.radians(-140.0),
        end_angle=math.radians(160.0),
        arc_segments=26,
        minor_segments=6,
        location=index_origin,
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    accent.add_box(
        size=(0.18, 0.12, 0.20),
        location=(0.49, -0.31, 0.53),
        rotation=(0.0, math.radians(-8.0), math.radians(-40.0)),
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:weighted five-sector drum in a low U cradle;"
            "side:thick index barrel between stepped bearings;"
            "top:broken reference band and unequal sector depths"
        ),
        body_detail="weighted five-sector price drum, stepped bearings, and low U cradle",
        accent_pivot="weighted drum index axis; glTF +Z is Blender -Y",
        accent_origin=index_origin,
    )


def build_inflation_exp() -> ModelGeometry:
    """Build a thermal expectation core with one forward focusing lens."""

    body = MeshAssembler()
    accent = MeshAssembler()

    body.add_capsule_x(
        half_length=0.42,
        radius=0.22,
        segments=24,
        hemisphere_steps=4,
        location=(-0.18, 0.18, -0.05),
        rotation=(0.0, -_QUARTER_TURN, 0.0),
    )
    for z, width in ((-0.31, 0.48), (-0.05, 0.56), (0.21, 0.44)):
        body.add_box(
            size=(width, 0.12, 0.075),
            location=(-0.18, 0.31, z),
        )

    # A finely faceted collar carries the complete body bevel contract while
    # reading as one heat shroud, not as decorative micro-detail.
    body.add_cylinder(
        radius=0.29,
        depth=0.16,
        segments=42,
        location=(-0.18, 0.18, -0.05),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    body.add_box(size=(0.98, 0.16, 0.12), location=(0.05, 0.18, -0.59))
    body.add_box(size=(0.12, 0.16, 0.70), location=(-0.43, 0.18, -0.24))
    body.add_box(size=(0.12, 0.16, 0.58), location=(0.53, 0.18, -0.18))
    for x in (-0.31, 0.47):
        body.add_cylinder_between(
            (x, -0.48, 0.23),
            (x, 0.15, 0.23),
            radius=0.035,
            segments=8,
        )

    lens_origin = (0.13, -0.43, 0.23)
    accent.add_torus_arc(
        major_radius=0.43,
        minor_radius=0.065,
        start_angle=math.radians(-155.0),
        end_angle=math.radians(170.0),
        arc_segments=28,
        minor_segments=6,
        location=lens_origin,
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    accent.add_box(
        size=(0.16, 0.10, 0.15),
        location=(0.47, -0.43, 0.47),
        rotation=(0.0, 0.0, math.radians(-28.0)),
        bevel=True,
    )
    accent.add_box(
        size=(0.12, 0.08, 0.12),
        location=(-0.18, -0.43, -0.03),
        rotation=(0.0, 0.0, math.radians(-38.0)),
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:offset focus ring above an asymmetric thermal core;"
            "side:floating lens ahead of twin optical rails;"
            "top:forward lens separated from a finned rear heat spine"
        ),
        body_detail="asymmetric thermal core, heat fins, open yoke, and optical rails",
        accent_pivot="forward focus-lens center; glTF +Z advances along Blender -Y",
        accent_origin=lens_origin,
    )


__all__ = (
    "build_market_rate",
    "build_liquidity",
    "build_credit_spread",
    "build_bank_lending",
    "build_cpi",
    "build_inflation_exp",
)
