"""Real-economy proof instruments built from the shared hard-surface API.

The builders in this module create geometry only.  They deliberately avoid
``bpy`` scene objects so authoring, validation, and export all consume the same
deterministic body/accent mesh contract.
"""

from __future__ import annotations

import math

from hard_surface import MeshAssembler, ModelGeometry


_QUARTER_TURN = math.pi * 0.5
def build_housing() -> ModelGeometry:
    """Build an unmistakable gabled house on a ground plinth.

    Solid walls carry a dark eave fascia band and, above it, the
    category-coloured gable-roof prism (the accent crown).  A chimney with a
    cap breaks the ridge silhouette, and the front face carries a recessed
    door inside a proud frame plus one crossbar window, so the model reads
    "a house" at a glance from the 3/4 turntable camera.  The dark fascia
    both keeps the accent area inside the 0.10..0.20 contract and swallows
    the wall-top corners so nothing pokes through the roof slopes.
    """

    body = MeshAssembler()
    accent = MeshAssembler()

    # Ground plinth the house stands on (also the top-view footprint).
    body.add_box(size=(2.00, 1.52, 0.20), location=(0.0, 0.0, -0.71), bevel=True)
    # Solid walls, sunk 0.02 into the plinth.
    body.add_box(size=(1.44, 1.04, 0.92), location=(0.0, 0.0, -0.17), bevel=True)
    # Dark eave fascia band between the walls and the coloured roof.
    body.add_box(size=(1.52, 1.10, 0.10), location=(0.0, 0.0, 0.32), bevel=True)
    # Chimney and cap on the right roof slope, rising past the ridge.
    body.add_box(size=(0.20, 0.20, 0.46), location=(0.40, 0.14, 0.64), bevel=True)
    body.add_box(size=(0.28, 0.28, 0.07), location=(0.40, 0.14, 0.895), bevel=True)
    # Recessed front door: proud frame ring with a set-back panel.
    body.add_rounded_rect_ring_y(
        outer_width=0.40,
        outer_height=0.68,
        inner_width=0.28,
        inner_height=0.56,
        depth=0.16,
        outer_radius=0.05,
        inner_radius=0.03,
        corner_segments=1,
        location=(-0.38, -0.52, -0.28),
        bevel=True,
    )
    body.add_box(size=(0.26, 0.12, 0.54), location=(-0.38, -0.49, -0.30), bevel=True)
    # One front window: proud frame ring with recessed crossbar mullions.
    body.add_rounded_rect_ring_y(
        outer_width=0.46,
        outer_height=0.46,
        inner_width=0.32,
        inner_height=0.32,
        depth=0.14,
        outer_radius=0.05,
        inner_radius=0.03,
        corner_segments=1,
        location=(0.34, -0.52, -0.10),
        bevel=True,
    )
    # The slim crossbars sit below the clamped-bevel thickness floor, so they
    # are intentionally unbeveled (same policy as buried tie details elsewhere).
    body.add_box(size=(0.40, 0.10, 0.08), location=(0.34, -0.50, -0.10))
    body.add_box(size=(0.08, 0.10, 0.40), location=(0.34, -0.50, -0.10))
    # Doorstep in front of the recessed door.
    body.add_box(size=(0.52, 0.30, 0.14), location=(-0.38, -0.57, -0.55), bevel=True)
    # Shutter panels on both side walls (side-view detail).
    body.add_box(size=(0.10, 0.44, 0.36), location=(0.70, 0.05, -0.08), bevel=True)
    body.add_box(size=(0.10, 0.44, 0.36), location=(-0.70, 0.05, -0.08), bevel=True)

    # Category-coloured gable roof: a triangular prism seated 0.02 into the
    # fascia, inset from the fascia rim so no faces are coplanar.
    roof_centroid = (0.0, 0.0, 0.49)
    accent.add_extruded_polygon_y(
        [(-0.74, 0.35), (0.74, 0.35), (0.0, 0.77)],
        depth=1.06,
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:gabled house facade with recessed door, crossbar window, and chimney past the ridge;"
            "side:pitched roof over deep walls and eave fascia on a ground plinth;"
            "top:roof ridge, chimney cap, and doorstep over a rectangular base slab"
        ),
        body_detail=(
            "ground plinth, solid walls, eave fascia, chimney with cap, "
            "recessed door, crossbar window, doorstep, and side shutters"
        ),
        accent_pivot="offset transfer-beam center; translate local Y",
        accent_origin=roof_centroid,
    )


def build_gdp() -> ModelGeometry:
    """Build an iconic GDP-growth mark: a bold up-arrow over a growth chart.

    A round base disc carries three ascending chart bars and one dominant,
    deep central arrow shaft.  The category accent is the wide chevron
    arrowhead crowning the shaft, so the front silhouette reads as a single
    confident rising arrow, distinct from a plain earnings bar chart.  The
    accent scales about the arrowhead centroid to pulse the growth tip.
    """

    body = MeshAssembler()
    accent = MeshAssembler()

    shaft_x = 0.10

    # Round base disc: the "base ring" the whole chart stands on.  Its circular
    # X-Y footprint gives the model real Y depth and a filled top-view mask.
    base_top_z = -0.72
    body.add_cylinder(
        radius=0.70,
        depth=0.16,
        segments=44,
        location=(0.0, 0.0, -0.80),
        bevel=True,
    )

    # Three ascending chart bars stepping up toward the arrow, standing on the
    # base.  Kept short and deep so the arrow towers over them while they still
    # carry Y mass for the side-view silhouette.
    bars = (
        # center_x, width_x, depth_y, height_z
        (-0.60, 0.24, 0.34, 0.34),
        (-0.37, 0.24, 0.34, 0.54),
        (-0.14, 0.24, 0.34, 0.74),
    )
    for cx, wx, dy, hz in bars:
        body.add_box(
            size=(wx, dy, hz),
            location=(cx, 0.0, base_top_z + hz * 0.5),
            bevel=True,
        )

    # Dominant central arrow shaft: bolder and deeper than the bars, rising well
    # above them.  A rounded profile keeps it machined rather than blocky.
    shaft_top_z = 0.54
    shaft_height = shaft_top_z - base_top_z
    body.add_rounded_box_y(
        width=0.42,
        height=shaft_height,
        depth=0.48,
        radius=0.10,
        corner_segments=3,
        location=(shaft_x, 0.0, (shaft_top_z + base_top_z) * 0.5),
        bevel=True,
    )

    # Wide chevron arrowhead (accent): overhangs the shaft and points up, so the
    # combined front silhouette is one clear rising arrow.  Extruded to real Y
    # depth so it reads as an arrowhead from every view, not a flat plate.  A
    # concave back notch turns the triangle into a true arrow tip.
    head_base_z = 0.50
    head_tip_z = 1.08
    head_half_w = 0.48
    head_shoulder = 0.15
    head_notch_z = 0.63
    head_points = [
        (0.0, head_tip_z),                 # tip
        (head_half_w, head_base_z),        # right wing
        (head_shoulder, head_base_z),      # right inner shoulder
        (0.0, head_notch_z),               # back notch
        (-head_shoulder, head_base_z),     # left inner shoulder
        (-head_half_w, head_base_z),       # left wing
    ]
    accent.add_extruded_polygon_y(
        [(x + shaft_x, z) for x, z in head_points],
        depth=0.48,
        bevel=True,
    )

    head_centroid = (shaft_x, 0.0, 0.72)

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:one bold up-arrow rising above three ascending chart bars;"
            "side:deep arrow shaft and chevron head over a round base disc;"
            "top:round base ring with a centered arrow mass and stepped bars"
        ),
        body_detail="round base disc, three ascending bars, and a bold central arrow shaft",
        accent_pivot="asymmetric counterweight hub center; scale XYZ",
        accent_origin=head_centroid,
    )
