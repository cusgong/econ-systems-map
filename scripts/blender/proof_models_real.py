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
    """Build an asymmetric portal-frame load path, not a literal house.

    Three chamfered portal frames step through depth above one foundation beam.
    A single knee brace and an offset transfer beam make the structure read as
    engineered framing instead of a stack of appliance-like slabs.  Every
    visible portal, beam, and gusset rim uses the common precision bevel.
    """

    body = MeshAssembler()
    accent = MeshAssembler()

    portals = (
        # outer width/height, inner width/height, depth, x/y/z offset
        (1.42, 1.24, 1.14, 0.90, 0.24, -0.06, 0.34, 0.02),
        (1.24, 1.08, 0.96, 0.76, 0.22, 0.04, 0.00, 0.03),
        (1.02, 0.91, 0.76, 0.63, 0.20, 0.15, -0.38, 0.06),
    )
    for outer_w, outer_h, inner_w, inner_h, depth, x, y, z in portals:
        body.add_rounded_rect_ring_y(
            outer_width=outer_w,
            outer_height=outer_h,
            inner_width=inner_w,
            inner_height=inner_h,
            depth=depth,
            outer_radius=0.10,
            inner_radius=0.07,
            corner_segments=1,
            location=(x, y, z),
            bevel=True,
        )

    # One foundation beam replaces the previous noisy stack of floor slabs.
    body.add_box(
        size=(1.38, 0.46, 0.13),
        location=(-0.04, 0.13, -0.58),
        bevel=True,
    )
    # The exposed triangular knee plate is a hard-surface gusset and is fully
    # tagged.  The slim diagonal cylinder behind it is a curved internal tie;
    # both ends are buried in the frame, so it intentionally has no cap bevel.
    body.add_extruded_polygon_y(
        [(-0.58, -0.49), (-0.36, -0.49), (-0.25, -0.08), (-0.39, -0.08)],
        depth=0.12,
        location=(0.0, -0.22, 0.0),
        bevel=True,
    )
    body.add_cylinder_between(
        (-0.42, -0.12, -0.43),
        (-0.30, -0.12, -0.05),
        radius=0.045,
        segments=10,
    )

    upper_plate_origin = (0.19, -0.18, 0.61)
    accent.add_rounded_box_y(
        width=1.14,
        height=0.14,
        depth=0.40,
        radius=0.035,
        corner_segments=2,
        location=upper_plate_origin,
        bevel=True,
    )
    accent.add_extruded_polygon_y(
        [(0.30, 0.48), (0.55, 0.48), (0.66, 0.60), (0.47, 0.60)],
        depth=0.28,
        location=(0.0, -0.18, 0.0),
        bevel=True,
    )
    accent.add_cylinder_between(
        (-0.31, -0.39, 0.57),
        (-0.31, 0.00, 0.57),
        radius=0.065,
        segments=10,
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:three offset portal frames with one knee brace;"
            "side:stepped frame depths and cantilever transfer beam;"
            "top:asymmetric beam overhang with transverse load pin"
        ),
        body_detail="three chamfered portal frames, foundation beam, and knee brace",
        accent_pivot="offset transfer-beam center; translate local Y",
        accent_origin=upper_plate_origin,
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
