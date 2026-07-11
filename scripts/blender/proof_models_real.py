"""Real-economy proof instruments built from the shared hard-surface API.

The builders in this module create geometry only.  They deliberately avoid
``bpy`` scene objects so authoring, validation, and export all consume the same
deterministic body/accent mesh contract.
"""

from __future__ import annotations

import math

from hard_surface import MeshAssembler, ModelGeometry


_QUARTER_TURN = math.pi * 0.5
_SIXTH_TURN = math.tau / 6.0


def build_housing() -> ModelGeometry:
    """Build a layered structural mass without a literal house silhouette.

    Three rounded portal frames step through depth, while two separated lower
    decks and restrained rail/foot hardware establish an architectural load
    path.  The complete cantilevered upper deck remains one accent mesh so its
    authored centre can translate as a single mechanism.
    """

    body = MeshAssembler()
    accent = MeshAssembler()

    portals = (
        # outer width/height, inner width/height, depth, x/y/z offset
        (1.48, 1.22, 1.14, 0.88, 0.12, 0.00, 0.28, 0.02),
        (1.28, 1.08, 0.96, 0.76, 0.11, -0.04, 0.00, 0.02),
        (1.08, 0.92, 0.78, 0.64, 0.10, 0.02, -0.28, 0.02),
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
            corner_segments=8,
            location=(x, y, z),
        )

    # Depth-separated lower plates read as structural floors rather than a
    # facade.  Rotating the rounded Y extrusion makes Z the plate thickness.
    body.add_box(
        size=(1.42, 0.48, 0.11),
        location=(0.00, 0.19, -0.56),
        bevel=True,
    )
    body.add_rounded_box_y(
        width=1.14,
        height=0.42,
        depth=0.09,
        radius=0.07,
        corner_segments=6,
        location=(0.08, -0.22, -0.41),
        rotation=(_QUARTER_TURN, 0.0, 0.0),
    )

    # Four low bearing feet and four restrained ties give the portal stack a
    # machined base.  Every part is a closed shell and the thinnest dimension
    # remains at least 0.08 before the common radius normalisation.
    for x in (-0.58, 0.58):
        for y in (-0.22, 0.22):
            body.add_cylinder(
                radius=0.08,
                depth=0.10,
                segments=16,
                location=(x, y, -0.68),
            )
    for x in (-0.52, 0.52):
        body.add_box(size=(0.09, 0.64, 0.10), location=(x, 0.0, -0.34))
    for y in (-0.20, 0.20):
        body.add_box(size=(1.10, 0.08, 0.08), location=(0.0, y, -0.46))

    upper_plate_origin = (0.16, -0.18, 0.62)
    accent.add_box(
        size=(1.18, 0.52, 0.10),
        location=upper_plate_origin,
        bevel=True,
    )
    for x in (-0.14, 0.34):
        accent.add_box(size=(0.10, 0.40, 0.08), location=(x, -0.18, 0.53))
    for x in (-0.36, 0.68):
        accent.add_cylinder_between(
            (x - 0.06, -0.18, 0.53),
            (x + 0.06, -0.18, 0.53),
            radius=0.07,
            segments=12,
        )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:nested-offset-portals;"
            "side:stepped-depth-slabs;"
            "top:cantilevered-upper-deck"
        ),
        body_detail="three nested portal frames with separated structural decks",
        accent_pivot="cantilever_plate_center_translate_y",
        accent_origin=upper_plate_origin,
    )


def build_gdp() -> ModelGeometry:
    """Build a caged macro flywheel with six swept, clipped vanes.

    The cage is split into capped arcs instead of a continuous decorative ring.
    Twin depth rails and offset rear struts keep the silhouette mechanical.  All
    six asymmetric vanes are appended to one accent assembler and scale from the
    central hex hub, producing the specified seven-percent XYZ pulse at runtime.
    """

    body = MeshAssembler()
    accent = MeshAssembler()

    cage_radius = 0.78
    cage_depth = 0.19
    arc_gap = 0.075
    cage_rotation = (_QUARTER_TURN, 0.0, 0.0)

    # Two six-piece rails leave visible service gaps at each sector boundary.
    # Each torus arc is individually capped and therefore a closed shell.
    for y in (-cage_depth, cage_depth):
        for sector in range(6):
            start = sector * _SIXTH_TURN + arc_gap
            end = (sector + 1) * _SIXTH_TURN - arc_gap
            body.add_torus_arc(
                major_radius=cage_radius,
                minor_radius=0.055,
                start_angle=start,
                end_angle=end,
                arc_segments=3,
                minor_segments=6,
                location=(0.0, y, 0.0),
                rotation=cage_rotation,
            )

    # Axial ties bind the two cage rails.  Rear-plane radial braces are offset
    # by thirty degrees from the vanes, preventing a flower or gear reading.
    for sector in range(6):
        angle = sector * _SIXTH_TURN
        x = cage_radius * math.cos(angle)
        z = cage_radius * math.sin(angle)
        body.add_cylinder_between(
            (x, -cage_depth, z),
            (x, cage_depth, z),
            radius=0.05,
            segments=8,
        )

        brace_angle = angle + _SIXTH_TURN * 0.5
        body.add_cylinder_between(
            (
                0.37 * math.cos(brace_angle),
                cage_depth,
                0.37 * math.sin(brace_angle),
            ),
            (
                0.64 * math.cos(brace_angle),
                cage_depth,
                0.64 * math.sin(brace_angle),
            ),
            radius=0.045,
            segments=8,
        )

    body.add_cylinder(
        radius=0.27,
        depth=0.12,
        segments=6,
        location=(0.0, 0.0, 0.0),
        rotation=cage_rotation,
        bevel=True,
    )
    body.add_cylinder(
        radius=0.34,
        depth=0.08,
        segments=12,
        location=(0.0, cage_depth, 0.0),
        rotation=cage_rotation,
    )

    # Six clockwise load paddles alternate reach on an intentionally irregular
    # 56..65-degree cadence.  Each root-to-tip centerline sweeps by roughly 36
    # degrees, producing directional turbine plates instead of radial petals or
    # gear teeth.  Every exposed paddle perimeter carries the selective
    # three-segment precision bevel.
    long_paddle = (
        (0.31, -0.150),
        (0.40, -0.200),
        (0.69, 0.060),
        (0.73, 0.130),
        (0.68, 0.220),
        (0.58, 0.230),
        (0.35, -0.020),
    )
    short_paddle = (
        (0.35, -0.120),
        (0.43, -0.160),
        (0.59, 0.040),
        (0.64, 0.100),
        (0.60, 0.170),
        (0.52, 0.190),
        (0.39, -0.020),
    )
    paddles = (
        (long_paddle, 0.0),
        (short_paddle, 58.0),
        (long_paddle, 121.0),
        (short_paddle, 177.0),
        (long_paddle, 242.0),
        (short_paddle, 300.0),
    )
    for paddle, angle_degrees in paddles:
        accent.add_extruded_polygon_y(
            paddle,
            depth=0.10,
            rotation=(0.0, -math.radians(angle_degrees), 0.0),
            bevel=True,
        )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:hex-hub-with-six-unequal-clockwise-swept-paddles;"
            "side:twin-cage-rails;"
            "top:open-flywheel-cage"
        ),
        body_detail="central hex hub inside a twin-rail open macro cage",
        accent_pivot="swept_paddle_hub_center_scale_xyz",
        accent_origin=(0.0, 0.0, 0.0),
    )
