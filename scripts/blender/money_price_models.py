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
    """Build an L-axis rate chart whose stepped line climbs to a bright marker."""

    body = MeshAssembler()
    accent = MeshAssembler()

    # Chart backing panel: the plate the axes and line are mounted on.  It owns
    # the Blender-Y (front-back) depth so the side and top silhouettes stay
    # solid rather than reading as a thin plaque.
    body.add_box(
        size=(1.48, 1.02, 0.14),
        location=(0.0, 0.0, -0.66),
        bevel=True,
    )
    # L-frame: the tall vertical value axis at the left and the horizontal time
    # axis along the bottom.  Together they read immediately as a chart frame.
    # The value-axis post is deepened in Blender Y so the side silhouette reads
    # as solid rather than a thin edge.
    body.add_box(
        size=(0.18, 0.96, 1.34),
        location=(-0.76, 0.0, 0.00),
        bevel=True,
    )
    body.add_box(
        size=(1.52, 0.66, 0.16),
        location=(0.0, 0.0, -0.52),
        bevel=True,
    )
    # A little mid-panel Y-bulk so the chart is not a thin plaque from the side.
    body.add_box(
        size=(1.20, 0.62, 0.12),
        location=(0.0, 0.0, -0.34),
        bevel=True,
    )

    # Upward-stepping line: this climbing rate line is the ACCENT, so the bright
    # category colour reads instantly as "a line trending up" against the dark
    # chart frame. Three beams (each end higher) with plotted data-point collars,
    # standing proud of the panel, capped by an up-arrowhead.
    step_points = (
        (-0.54, -0.34),
        (-0.18, -0.04),
        (0.18, 0.26),
        (0.54, 0.54),
    )
    for (x0, z0), (x1, z1) in zip(step_points, step_points[1:]):
        accent.add_cylinder_between(
            (x0, 0.10, z0),
            (x1, 0.10, z1),
            radius=0.090,
            segments=12,
            bevel=True,
        )
    for x, z in step_points[1:-1]:
        accent.add_cylinder(
            radius=0.120,
            depth=0.20,
            segments=14,
            location=(x, 0.10, z),
            rotation=(_QUARTER_TURN, 0.0, 0.0),
            bevel=True,
        )
    marker_origin = (0.54, 0.10, 0.54)
    for sign in (-1.0, 1.0):
        accent.add_box(
            size=(0.34, 0.20, 0.12),
            location=(0.54 + sign * 0.10, 0.10, 0.74),
            rotation=(0.0, math.radians(sign * 45.0), 0.0),
            bevel=True,
        )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:L-axis frame under a stepped line climbing to a peak marker;"
            "side:upright value axis and line nodes on a deep chart panel;"
            "top:stepped beams crossing the panel to a forward chevron marker"
        ),
        body_detail="L-axis chart frame, three-beam rising line, and plotted node collars",
        accent_pivot="maturity carriage centroid; translate along glTF X / Blender X",
        accent_origin=marker_origin,
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
    # A fuller central manifold column: a wider through-axis so the two edge-on
    # views (front X-Z and side Y-Z), previously the sparse silhouettes against
    # the broad top rings, gain a full-height barrel of real diameter.
    body.add_cylinder(
        radius=0.24,
        depth=1.12,
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
            (x, y, -0.50),
            (x, y, 0.50),
            radius=0.070,
            segments=8,
        )

    rotor_origin = (0.0, 0.0, 0.03)
    accent.add_cylinder(
        radius=0.21,
        depth=0.17,
        segments=12,
        location=rotor_origin,
        bevel=True,
    )
    for index in range(3):
        angle = math.radians(index * 120.0)
        radius = 0.30
        accent.add_box(
            size=(0.60, 0.21, 0.15),
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
    """Build two unequal bars with a gap bridged by a bold double-arrow gauge."""

    body = MeshAssembler()
    accent = MeshAssembler()

    # Base plate seats both bars and owns the front-back depth.
    body.add_box(
        size=(1.54, 1.00, 0.16),
        location=(0.0, 0.0, -0.66),
        bevel=True,
    )
    # Two clearly separate upright bars of different heights.  The empty span
    # between their inner faces is the "spread" the caliper measures.
    body.add_box(
        size=(0.36, 0.86, 1.16),
        location=(-0.48, 0.0, 0.00),
        bevel=True,
    )
    body.add_box(
        size=(0.36, 0.86, 0.72),
        location=(0.48, 0.0, -0.22),
        bevel=True,
    )
    # Short plinths read each bar as a seated column rather than a slab.
    for x in (-0.48, 0.48):
        body.add_box(
            size=(0.50, 0.90, 0.12),
            location=(x, 0.0, -0.54),
            bevel=True,
        )

    bridge_origin = (0.0, 0.0, 0.04)
    # Bold double-headed arrow bridging the whole gap: one thick shaft plus a
    # large triangular head at each end.  Nominal tips sit at x = -/+0.36:
    # the 0.035 precision bevel pulls a sharp tip back about 0.047, so the
    # rendered tip lands at x = -/+0.313, embedded 0.013 into each bar's
    # inner face (x = -/+0.30), and the contact reads sealed.  Centered at z = 0.04 the tips press the short
    # bar's face 0.10 below its rim (face top z = 0.14), the natural
    # spread-measuring height.
    accent.add_box(
        size=(0.24, 0.34, 0.36),
        location=(0.0, 0.0, 0.04),
        bevel=True,
    )
    # Arrowheads: 0.26 long, 0.64 tall, clearly wider than the shaft.
    accent.add_extruded_polygon_y(
        [(-0.36, 0.04), (-0.09, 0.36), (-0.09, -0.28)],
        depth=0.34,
        bevel=True,
    )
    accent.add_extruded_polygon_y(
        [(0.36, 0.04), (0.09, 0.36), (0.09, -0.28)],
        depth=0.34,
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:two unequal bars split by a gap bridged by one bold double arrow;"
            "side:tall seated columns crossed by a thick gauge beam;"
            "top:separated bar blocks joined by a bold cross beam"
        ),
        body_detail="two unequal seated bars with a measured gap between them",
        accent_pivot="moving jaw slide center; translate along glTF X / Blender X",
        accent_origin=bridge_origin,
    )


def build_bank_lending() -> ModelGeometry:
    """Build a vault with a round door paying one coin out through the front."""

    body = MeshAssembler()
    accent = MeshAssembler()

    # Vault body: a heavy near-cubic safe, the recognizable core of the icon.
    body.add_box(
        size=(1.08, 0.86, 1.08),
        location=(0.0, 0.0, 0.08),
        bevel=True,
    )
    # Round recessed door set into the front (-Y) face, upper half.
    body.add_cylinder(
        radius=0.36,
        depth=0.16,
        segments=20,
        location=(0.0, -0.42, 0.22),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    # Combination wheel: a central hub crossed by two spokes on the door.
    body.add_cylinder(
        radius=0.09,
        depth=0.18,
        segments=12,
        location=(0.0, -0.50, 0.22),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    body.add_box(size=(0.40, 0.10, 0.07), location=(0.0, -0.50, 0.22), bevel=True)
    body.add_box(size=(0.07, 0.10, 0.40), location=(0.0, -0.50, 0.22), bevel=True)
    # Pay-out slot lip on the lower front, where the coin emerges.
    body.add_box(
        size=(0.62, 0.12, 0.12),
        location=(0.0, -0.42, -0.30),
        bevel=True,
    )
    # Four short feet.
    for x in (-0.40, 0.40):
        for y in (-0.30, 0.30):
            body.add_box(
                size=(0.16, 0.16, 0.14),
                location=(x, y, -0.52),
                bevel=True,
            )

    coin_origin = (0.0, -0.62, -0.30)
    # Category-colored coin: a flat disc facing front (thin on Blender Y) that
    # advances out through the pay slot toward the viewer.
    accent.add_cylinder(
        radius=0.30,
        depth=0.09,
        segments=20,
        location=(0.0, -0.62, -0.30),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    # A raised inner relief keeps the disc reading as a struck coin.
    accent.add_cylinder(
        radius=0.19,
        depth=0.12,
        segments=16,
        location=(0.0, -0.62, -0.30),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:round-doored vault paying a coin out through a lower slot;"
            "side:deep safe block with a forward coin clear of the front face;"
            "top:cubic vault footprint with a coin projecting off the front"
        ),
        body_detail="cubic vault, round combination door, pay slot, and feet",
        accent_pivot="linked piston-face center; glTF +Z advances along Blender -Y",
        accent_origin=coin_origin,
    )


def build_cpi() -> ModelGeometry:
    """Build an open shopping basket carrying a weighted price disc of goods."""

    body = MeshAssembler()
    accent = MeshAssembler()

    # Basket floor: a solid pan that fills the top-down view and gives depth.
    body.add_box(
        size=(1.04, 0.86, 0.15),
        location=(0.0, 0.0, -0.44),
        bevel=True,
    )
    # Four upright walls enclosing an open top; the goods sit inside the mouth.
    body.add_box(size=(1.04, 0.11, 0.58), location=(0.0, -0.43, -0.075), bevel=True)
    body.add_box(size=(1.04, 0.11, 0.58), location=(0.0, 0.43, -0.075), bevel=True)
    body.add_box(size=(0.11, 0.86, 0.58), location=(-0.49, 0.0, -0.075), bevel=True)
    body.add_box(size=(0.11, 0.86, 0.58), location=(0.49, 0.0, -0.075), bevel=True)
    # A raised rim frames the open mouth of the basket.
    body.add_box(size=(1.14, 0.13, 0.10), location=(0.0, -0.45, 0.20), bevel=True)
    body.add_box(size=(1.14, 0.13, 0.10), location=(0.0, 0.45, 0.20), bevel=True)
    body.add_box(size=(0.13, 0.98, 0.10), location=(-0.52, 0.0, 0.20), bevel=True)
    body.add_box(size=(0.13, 0.98, 0.10), location=(0.52, 0.0, 0.20), bevel=True)
    # Arc carry handle bowing up over the mouth (X-Z plane).
    body.add_torus_arc(
        major_radius=0.52,
        minor_radius=0.058,
        start_angle=math.radians(14.0),
        end_angle=math.radians(166.0),
        arc_segments=16,
        minor_segments=6,
        location=(0.0, 0.0, 0.18),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )

    goods_origin = (0.0, 0.0, 0.30)
    # Weighted price disc: the colored basket of goods, standing so it rises
    # above the rim, held flat on Blender Y and spinning about that axis.
    accent.add_cylinder(
        radius=0.31,
        depth=0.11,
        segments=20,
        location=(0.0, 0.0, 0.30),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    # Two stacked item tiles beside the disc round out the "goods" reading.
    accent.add_box(size=(0.23, 0.11, 0.34), location=(-0.37, 0.0, 0.24), bevel=True)
    accent.add_box(size=(0.20, 0.11, 0.26), location=(0.38, 0.0, 0.20), bevel=True)

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:open basket brimming with a price disc and stacked goods;"
            "side:walled pan under an arc handle with goods above the rim;"
            "top:rimmed basket mouth filled by a central weighted disc"
        ),
        body_detail="open shopping basket, rimmed mouth, floor pan, and arc handle",
        accent_pivot="weighted drum index axis; glTF +Z is Blender -Y",
        accent_origin=goods_origin,
    )


def build_inflation_exp() -> ModelGeometry:
    """Build a thermometer whose colored mercury column reads high with heat."""

    body = MeshAssembler()
    accent = MeshAssembler()

    # Base plinth: a wide stand that fills the top-down view and steadies the
    # tall instrument, keeping genuine Blender-Y depth.
    body.add_box(
        size=(1.08, 1.08, 0.16),
        location=(0.0, 0.0, -0.80),
        bevel=True,
    )
    # Round bulb at the foot of the thermometer (a flat-fronted puck so the
    # colored mercury can seat flush on its face).
    body.add_cylinder(
        radius=0.31,
        depth=0.36,
        segments=26,
        location=(0.0, 0.0, -0.46),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    # Vertical tube rising from the bulb, flat-fronted to carry the column.
    body.add_rounded_box_y(
        width=0.28,
        height=1.06,
        depth=0.36,
        radius=0.13,
        corner_segments=3,
        location=(0.0, 0.0, 0.18),
        bevel=True,
    )
    # Short neck collar where the tube meets the bulb reads as a gauge fitting.
    body.add_cylinder(
        radius=0.20,
        depth=0.40,
        segments=18,
        location=(0.0, 0.0, -0.26),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )
    # Fitting ring around the neck adds a machined detail and front-back bulk.
    body.add_torus(
        major_radius=0.23,
        minor_radius=0.05,
        major_segments=18,
        minor_segments=6,
        location=(0.0, 0.0, -0.08),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
    )

    column_origin = (0.0, -0.15, 0.16)
    # Mercury: a colored column filling the tube high, plus the colored bulb
    # face.  Both are held in a thin front slab (thin on Blender Y).
    accent.add_box(
        size=(0.18, 0.08, 0.94),
        location=(0.0, -0.15, 0.16),
        bevel=True,
    )
    accent.add_cylinder(
        radius=0.23,
        depth=0.08,
        segments=18,
        location=(0.0, -0.15, -0.46),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:bulbed thermometer with a colored column filled high;"
            "side:upright tube on a round bulb over a broad stand;"
            "top:round bulb and tube centered on a square base plate"
        ),
        body_detail="thermometer tube, round bulb, neck collar, and base plinth",
        accent_pivot="forward focus-lens center; glTF +Z advances along Blender -Y",
        accent_origin=column_origin,
    )


__all__ = (
    "build_market_rate",
    "build_liquidity",
    "build_credit_spread",
    "build_bank_lending",
    "build_cpi",
    "build_inflation_exp",
)
