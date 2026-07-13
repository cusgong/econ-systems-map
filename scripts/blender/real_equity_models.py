"""Precision instruments for the real-economy and equity batch.

Each builder is scene-independent.  It appends closed, disconnected shells to
one body and one accent assembler while leaving normalization, materials,
object creation, and export to the shared authoring pipeline.  Coordinates use
Blender's +Z-up, -Y-front convention.  Runtime glTF axes therefore map back to
Blender as ``(x, z, -y)``.

This batch is authored as *iconic* machined pictograms: the dark body carries a
recognizable 3D symbol of the concept (a shopping bag, a row of workers, a bar
chart, a broken chain, a candlestick chart) and the category-colored accent is
the semantically defining part (the goods, the badge, the rising arrow, the
break spark, the leading candle).  Every icon still keeps genuine Blender-Y
depth so the three-view silhouette stays balanced.
"""

from __future__ import annotations

import math

from hard_surface import MeshAssembler, ModelGeometry


_QUARTER_TURN = math.pi * 0.5


def _up_arrow_points(
    shaft_hw: float,
    head_hw: float,
    z_bottom: float,
    z_shoulder: float,
    z_tip: float,
) -> list[tuple[float, float]]:
    """Return a deterministic upward-arrow XZ outline for Y extrusion."""

    return [
        (-shaft_hw, z_bottom),
        (shaft_hw, z_bottom),
        (shaft_hw, z_shoulder),
        (head_hw, z_shoulder),
        (0.0, z_tip),
        (-head_hw, z_shoulder),
        (-shaft_hw, z_shoulder),
    ]


def _star_points(
    outer_radius: float,
    inner_radius: float,
    count: int,
    phase: float = 0.0,
) -> list[tuple[float, float]]:
    """Return a deterministic sharp XZ star/burst outline for Y extrusion."""

    points: list[tuple[float, float]] = []
    for index in range(count * 2):
        radius = outer_radius if index % 2 == 0 else inner_radius
        angle = phase + math.pi * index / count
        points.append((radius * math.cos(angle), radius * math.sin(angle)))
    return points


def build_consumption() -> ModelGeometry:
    """Build a shopping bag with two arched handles and goods rising past the mouth."""

    body = MeshAssembler()
    accent = MeshAssembler()

    # Bag sack: a deep rounded box.  Its 0.94 Blender-Y depth is what fills the
    # side and top silhouettes so the front bag face never reads as a flat plate.
    body.add_rounded_box_y(
        width=1.20,
        height=1.02,
        depth=0.94,
        radius=0.075,
        corner_segments=3,
        location=(0.0, 0.0, -0.06),
        bevel=True,
    )
    # Folded top cuff (the open mouth), slightly wider and deeper than the sack.
    body.add_rounded_box_y(
        width=1.28,
        height=0.15,
        depth=1.00,
        radius=0.050,
        corner_segments=3,
        location=(0.0, 0.0, 0.52),
        bevel=True,
    )
    # Two arching carry handles standing in the front X-Z plane above the cuff.
    for handle_x in (-0.32, 0.32):
        body.add_torus_arc(
            major_radius=0.26,
            minor_radius=0.050,
            start_angle=0.0,
            end_angle=math.pi,
            arc_segments=20,
            minor_segments=8,
            location=(handle_x, 0.0, 0.52),
            rotation=(_QUARTER_TURN, 0.0, 0.0),
            bevel=True,
        )

    goods_origin = (0.0, 0.0, 0.72)
    # Goods (category color) rising out of the mouth: two blocks and a round can.
    accent.add_box(
        size=(0.30, 0.38, 0.46),
        location=(-0.19, 0.0, 0.68),
        rotation=(0.0, math.radians(-8.0), 0.0),
        bevel=True,
    )
    accent.add_box(
        size=(0.27, 0.36, 0.52),
        location=(0.20, 0.0, 0.74),
        rotation=(0.0, math.radians(7.0), 0.0),
        bevel=True,
    )
    accent.add_cylinder(
        radius=0.135,
        depth=0.44,
        segments=14,
        location=(0.02, 0.0, 0.58),
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:a rounded shopping bag with two arched handles and goods rising past the mouth;"
            "side:a deep sack with a folded cuff and forward goods breaking the top line;"
            "top:a wide bag mouth spanned by two handle arcs around a cluster of goods"
        ),
        body_detail="deep shopping-bag sack, folded top cuff, and two arched carry handles",
        accent_pivot="inertia flywheel clutch axis; scale XYZ about the central hub",
        accent_origin=goods_origin,
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
    """Build three workers of unequal height on a foundation with a front badge bar."""

    body = MeshAssembler()
    accent = MeshAssembler()

    base_top = -0.62
    # Foundation slab: deep in Blender Y so the row of figures is not a flat plate.
    body.add_rounded_box_y(
        width=1.30,
        height=0.18,
        depth=0.90,
        radius=0.050,
        corner_segments=2,
        location=(0.0, 0.0, base_top - 0.09),
        bevel=True,
    )
    worker_specs = ((-0.42, 0.60), (0.02, 0.78), (0.44, 0.52))
    for worker_x, torso_height in worker_specs:
        torso_center_z = base_top + torso_height * 0.5
        body.add_rounded_box_y(
            width=0.28,
            height=torso_height,
            depth=0.54,
            radius=0.100,
            corner_segments=2,
            location=(worker_x, 0.0, torso_center_z),
            bevel=True,
        )
        shoulder_z = base_top + torso_height + 0.02
        body.add_rounded_box_y(
            width=0.40,
            height=0.14,
            depth=0.56,
            radius=0.060,
            corner_segments=2,
            location=(worker_x, 0.0, shoulder_z),
            bevel=True,
        )
        head_z = shoulder_z + 0.26
        body.add_uv_sphere(
            radius=0.175,
            segments=16,
            rings=8,
            location=(worker_x, 0.0, head_z),
        )

    badge_origin = (0.0, -0.44, -0.30)
    # Shared front badge bar (category color): the "people employed" nameplate.
    accent.add_rounded_box_y(
        width=1.30,
        height=0.26,
        depth=0.24,
        radius=0.050,
        corner_segments=2,
        location=badge_origin,
        bevel=True,
    )
    accent.add_cylinder(
        radius=0.150,
        depth=0.14,
        segments=16,
        location=(0.0, badge_origin[1] - 0.10, badge_origin[2]),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:three unequal capped figures with round heads standing on a slab behind a badge bar;"
            "side:a deep foundation carrying rounded torsos and spherical heads;"
            "top:a wide slab of three figure footprints fronted by a badge bar"
        ),
        body_detail="three unequal worker figures with rounded torsos and spherical heads on a deep slab",
        accent_pivot="three-column locking-ring centroid; translate along glTF Y / Blender Z",
        accent_origin=badge_origin,
    )


def build_earnings() -> ModelGeometry:
    """Build an ascending three-bar earnings chart under a bold rising arrow."""

    body = MeshAssembler()
    accent = MeshAssembler()

    base_top = -0.50
    # Deep chart plinth: the Blender-Y bulk that keeps the bars from reading flat.
    body.add_rounded_box_y(
        width=1.46,
        height=0.20,
        depth=1.06,
        radius=0.050,
        corner_segments=4,
        location=(0.0, 0.0, base_top - 0.10),
        bevel=True,
    )
    bar_specs = ((-0.52, 0.46), (0.0, 0.72), (0.52, 0.98))
    for bar_x, bar_height in bar_specs:
        body.add_rounded_box_y(
            width=0.34,
            height=bar_height,
            depth=0.64,
            radius=0.045,
            corner_segments=4,
            location=(bar_x, 0.0, base_top + bar_height * 0.5),
            bevel=True,
        )

    arrow_origin = (0.52, -0.02, 0.56)
    arrow_points = _up_arrow_points(
        shaft_hw=0.15,
        head_hw=0.45,
        z_bottom=-0.34,
        z_shoulder=0.00,
        z_tip=0.40,
    )
    # Bold rising arrow (category color): flat and thin on Blender Y per contract.
    accent.add_extruded_polygon_y(
        arrow_points,
        depth=0.28,
        location=arrow_origin,
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:three ascending bars on a plinth beneath one bold upward arrow;"
            "side:a deep chart plinth carrying stepped bars and a thin forward arrow blade;"
            "top:a wide plinth of three bar footprints with a thin arrow plate above the tallest"
        ),
        body_detail="three ascending earnings bars on a deep chart plinth",
        accent_pivot="stair-carrier centroid; translate along glTF Y / Blender Z",
        accent_origin=arrow_origin,
    )


def build_defaults() -> ModelGeometry:
    """Build a broken chain link beside an intact interlocking link with a spark at the gap."""

    body = MeshAssembler()
    accent = MeshAssembler()

    # Main link: a thick ring standing in the front X-Z plane with a clear gap at
    # the top (the break).  The arc spans 316 degrees leaving a 44-degree break.
    body.add_torus_arc(
        major_radius=0.46,
        minor_radius=0.165,
        start_angle=math.radians(112.0),
        end_angle=math.radians(428.0),
        arc_segments=32,
        minor_segments=10,
        location=(-0.14, 0.0, -0.06),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    # Intact neighbour link, interlocked and turned 90 degrees into the Y-Z plane
    # so the pair reads as a chain and the model gains real Blender-Y depth.
    body.add_torus(
        major_radius=0.38,
        minor_radius=0.165,
        major_segments=30,
        minor_segments=10,
        location=(0.30, 0.0, -0.10),
        rotation=(0.0, _QUARTER_TURN, 0.0),
    )

    spark_origin = (-0.14, 0.0, 0.50)
    # Down-arrow at the break (category color): a fall/failure marker, not an
    # award. Flat and thin on Blender Y. A clean non-self-intersecting outline.
    down_arrow = [
        (-0.12, 0.42),
        (0.12, 0.42),
        (0.12, -0.03),
        (0.30, -0.03),
        (0.0, -0.44),
        (-0.30, -0.03),
        (-0.12, -0.03),
    ]
    accent.add_extruded_polygon_y(
        down_arrow,
        depth=0.19,
        location=spark_origin,
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:a broken ring link with a gap at the top and a spark burst at the break;"
            "side:an intact neighbour link turned edgewise giving the chain real depth;"
            "top:two interlocked links crossing at right angles below a thin spark plate"
        ),
        body_detail="one broken front chain link and one intact interlocking neighbour link",
        accent_pivot="safety-latch hinge; rotate about glTF Z / Blender -Y",
        accent_origin=spark_origin,
    )


def build_stocks() -> ModelGeometry:
    """Build a candlestick price chart: three dark candles, one highlighted leading candle, and a trend arrow."""

    body = MeshAssembler()
    accent = MeshAssembler()

    base_top = -0.54
    # Deep chart bed: the Blender-Y bulk under the floating candles.
    body.add_rounded_box_y(
        width=1.16,
        height=0.18,
        depth=0.98,
        radius=0.050,
        corner_segments=3,
        location=(0.0, 0.0, base_top - 0.09),
        bevel=True,
    )
    # (x, low, high, body_bottom, body_top)
    dark_candles = (
        (-0.42, -0.34, 0.30, -0.14, 0.16),
        (-0.14, -0.12, 0.52, 0.02, 0.40),
        (0.14, 0.00, 0.44, 0.10, 0.34),
    )
    for candle_x, low, high, body_bottom, body_top in dark_candles:
        body.add_cylinder(
            radius=0.035,
            depth=high - low,
            segments=10,
            location=(candle_x, 0.0, (high + low) * 0.5),
            bevel=False,
        )
        body.add_rounded_box_y(
            width=0.26,
            height=body_top - body_bottom,
            depth=0.70,
            radius=0.040,
            corner_segments=3,
            location=(candle_x, 0.0, (body_bottom + body_top) * 0.5),
            bevel=True,
        )

    lead_x = 0.44
    lead_origin = (lead_x, 0.0, 0.30)
    # Leading candle (category color): a highlighted body over a tall high-low wick.
    accent.add_cylinder(
        radius=0.038,
        depth=0.92,
        segments=8,
        location=(lead_x, 0.0, 0.24),
        bevel=False,
    )
    accent.add_rounded_box_y(
        width=0.26,
        height=0.48,
        depth=0.42,
        radius=0.040,
        corner_segments=3,
        location=lead_origin,
        bevel=True,
    )
    # Small up-right trend arrow tilted in the front plane (the uptrend cue).
    trend_points = _up_arrow_points(
        shaft_hw=0.050,
        head_hw=0.155,
        z_bottom=-0.17,
        z_shoulder=0.02,
        z_tip=0.19,
    )
    accent.add_extruded_polygon_y(
        trend_points,
        depth=0.18,
        location=(0.18, 0.0, 0.62),
        rotation=(0.0, math.radians(34.0), 0.0),
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:three dark candlesticks and one highlighted leading candle under a rising trend arrow;"
            "side:a deep chart bed carrying floating candle bodies on high-low wicks;"
            "top:a wide chart bed with a row of candle footprints and a tilted trend plate"
        ),
        body_detail="three dark candlesticks with high-low wicks on a deep chart bed",
        accent_pivot="price-spindle carriage center; translate along glTF Y / Blender Z",
        accent_origin=lead_origin,
    )


__all__ = (
    "build_consumption",
    "build_investment",
    "build_employment",
    "build_earnings",
    "build_defaults",
    "build_stocks",
)
