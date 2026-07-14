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

from hard_surface import MeshAssembler, ModelGeometry, rounded_rectangle_points


_QUARTER_TURN = math.pi * 0.5


def _tapered_torso_points(
    width: float,
    height: float,
    radius: float,
    corner_segments: int,
    taper: float,
) -> list[tuple[float, float]]:
    """Return a rounded A-taper torso XZ outline (wider at the base) for Y extrusion."""

    points = rounded_rectangle_points(width, height, radius, corner_segments)
    return [(x * (1.0 - taper * (z / height)), z) for x, z in points]


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
    """Build a tapered shopping bag with a folded cuff, thick handles, and goods."""

    body = MeshAssembler()
    accent = MeshAssembler()

    # Tapered sack: visibly narrower at the base than at the mouth so the
    # profile reads as a paper bag, never a plain box.  The trapezoid outline
    # is extruded along Blender Y to keep genuine front-to-back depth.
    sack_outline = [
        (-0.44, -0.60),
        (0.44, -0.60),
        (0.61, 0.44),
        (-0.61, 0.44),
    ]
    body.add_extruded_polygon_y(sack_outline, depth=0.92, bevel=True)
    # Folded rim cuff overhanging the sack mouth on all four sides.
    body.add_rounded_box_y(
        width=1.34,
        height=0.17,
        depth=1.02,
        radius=0.055,
        corner_segments=3,
        location=(0.0, 0.0, 0.525),
        bevel=True,
    )
    # Two thick carry handles (front sheet and back sheet) arching well above
    # the cuff, leaving the mouth centre clear for the goods.
    for handle_y in (-0.30, 0.30):
        body.add_torus_arc(
            major_radius=0.30,
            minor_radius=0.095,
            start_angle=0.0,
            end_angle=math.pi,
            arc_segments=20,
            minor_segments=8,
            location=(0.0, handle_y, 0.60),
            rotation=(_QUARTER_TURN, 0.0, 0.0),
            bevel=True,
        )

    goods_origin = (0.0, 0.0, 0.70)
    # Goods (category color): one tall leaning carton and one round can, two
    # clearly different items rising past the mouth between the handles.
    accent.add_box(
        size=(0.32, 0.34, 0.70),
        location=(-0.17, 0.0, 0.62),
        rotation=(0.0, math.radians(-6.0), 0.0),
        bevel=True,
    )
    accent.add_cylinder(
        radius=0.155,
        depth=0.56,
        segments=14,
        location=(0.20, 0.0, 0.50),
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:a bag tapering to a narrow base under a folded cuff, one bold handle arc, and two goods;"
            "side:a deep tapered sack with front and back handle arcs rising over the cuff;"
            "top:a wide cuffed mouth crossed by two parallel handle arcs around boxed and round goods"
        ),
        body_detail="tapered shopping-bag sack, overhanging folded cuff, and two thick handle arcs",
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
    """Build three crisp round-headed figures on a low plinth with a team nameplate."""

    body = MeshAssembler()
    accent = MeshAssembler()

    base_top = -0.62
    # Clean low plinth, deep in Blender Y, carrying all three figures.
    body.add_rounded_box_y(
        width=1.40,
        height=0.22,
        depth=0.88,
        radius=0.050,
        corner_segments=2,
        location=(0.0, 0.0, -0.73),
        bevel=True,
    )
    # (x, torso height, head radius): the centre figure stands tallest and the
    # figures are spread wide enough that every gap stays open at a glance.
    worker_specs = ((-0.48, 0.58, 0.20), (0.0, 0.74, 0.22), (0.48, 0.52, 0.20))
    for worker_x, torso_height, head_radius in worker_specs:
        torso_outline = _tapered_torso_points(
            width=0.34,
            height=torso_height,
            radius=0.10,
            corner_segments=3,
            taper=0.16,
        )
        body.add_extruded_polygon_y(
            torso_outline,
            depth=0.60,
            location=(worker_x, 0.0, base_top + torso_height * 0.5),
            bevel=True,
        )
        # Big head floating a clear 0.07 neck gap above the torso shoulder line.
        head_z = base_top + torso_height + 0.07 + head_radius
        body.add_uv_sphere(
            radius=head_radius,
            segments=18,
            rings=9,
            location=(worker_x, 0.0, head_z),
        )

    plate_origin = (0.0, -0.50, -0.73)
    # Team nameplate (category color) mounted flush on the plinth front face,
    # with a round badge emblem proud of the plate.
    accent.add_rounded_box_y(
        width=1.30,
        height=0.22,
        depth=0.18,
        radius=0.060,
        corner_segments=2,
        location=plate_origin,
        bevel=True,
    )
    accent.add_cylinder(
        radius=0.11,
        depth=0.14,
        segments=16,
        location=(0.0, -0.62, -0.73),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:three spaced round-headed figures of stepped height on a plinth with a front nameplate;"
            "side:a deep plinth carrying tapered torsos under big floating spherical heads;"
            "top:a wide plinth of three separated figure footprints with a nameplate proud of the front edge"
        ),
        body_detail="three spaced A-taper worker torsos with big floating heads on a clean low plinth",
        accent_pivot="three-column locking-ring centroid; translate along glTF Y / Blender Z",
        accent_origin=plate_origin,
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

    # Slim chart bed: thinner and smaller than the candles it carries so the
    # candlesticks, not the plinth, dominate the icon.
    body.add_rounded_box_y(
        width=1.18,
        height=0.12,
        depth=0.88,
        radius=0.045,
        corner_segments=3,
        location=(0.0, 0.02, -0.70),
        bevel=True,
    )
    # (x, wick_low, wick_high, body_bottom, body_top): tall bodies with clearly
    # alternating heights, every wick protruding past both ends of its body.
    dark_candles = (
        (-0.45, -0.62, 0.12, -0.44, -0.04),
        (-0.15, -0.42, 0.48, -0.22, 0.32),
        (0.15, -0.54, 0.24, -0.36, 0.08),
    )
    for candle_x, low, high, body_bottom, body_top in dark_candles:
        body.add_cylinder(
            radius=0.050,
            depth=high - low,
            segments=10,
            location=(candle_x, 0.07, (high + low) * 0.5),
            bevel=False,
        )
        body.add_rounded_box_y(
            width=0.28,
            height=body_top - body_bottom,
            depth=0.82,
            radius=0.040,
            corner_segments=3,
            location=(candle_x, 0.07, (body_bottom + body_top) * 0.5),
            bevel=True,
        )

    lead_x = 0.45
    lead_y = -0.25
    lead_origin = (lead_x, lead_y, 0.22)
    # Leading candle (category color): the tallest body, pulled toward the
    # camera, on a thick wick protruding at both ends.
    accent.add_cylinder(
        radius=0.052,
        depth=0.90,
        segments=10,
        location=(lead_x, lead_y, 0.19),
        bevel=False,
    )
    accent.add_rounded_box_y(
        width=0.28,
        height=0.56,
        depth=0.46,
        radius=0.040,
        corner_segments=3,
        location=lead_origin,
        bevel=True,
    )
    # Bold upright arrow directly above the leading candle (the uptrend cue).
    trend_points = _up_arrow_points(
        shaft_hw=0.085,
        head_hw=0.25,
        z_bottom=-0.17,
        z_shoulder=0.02,
        z_tip=0.17,
    )
    accent.add_extruded_polygon_y(
        trend_points,
        depth=0.18,
        location=(lead_x, lead_y, 0.75),
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:four alternating candlesticks stepping up to a tall leading candle under a bold up arrow;"
            "side:deep candle bodies floating on protruding wicks over a slim chart bed;"
            "top:a slim rectangular bed of four candle footprints with the leading candle proud of the front"
        ),
        body_detail="three dark alternating candlesticks with thick protruding wicks on a slim chart bed",
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
