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
        (1.46, 1.24, 1.16, 0.90, 0.13, -0.06, 0.26, 0.02),
        (1.24, 1.08, 0.96, 0.76, 0.11, 0.04, 0.00, 0.03),
        (1.02, 0.91, 0.76, 0.63, 0.10, 0.15, -0.25, 0.06),
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
    """Build a caged macro flywheel with an asymmetric counterweight sector.

    Twin service-gap rails surround one incomplete load band with unequal end
    shoes and a tangential drive dog.  The accent is a continuous mass rather
    than disconnected radial vanes, eliminating the flower, gear, and turbine
    readings while preserving the specified seven-percent XYZ pulse.
    """

    body = MeshAssembler()
    accent = MeshAssembler()

    cage_radius = 0.78
    cage_depth = 0.19
    cage_rotation = (_QUARTER_TURN, 0.0, 0.0)

    # Two unequal capped arcs on each depth rail establish a deliberate service
    # gap.  Their exposed stock ends receive the same bevel; the curved rail
    # tessellation remains smooth and therefore unweighted.
    rail_arcs = (
        (math.radians(-154.0), math.radians(58.0), 18),
        (math.radians(104.0), math.radians(164.0), 6),
    )
    for y in (-cage_depth, cage_depth):
        for start, end, segments in rail_arcs:
            body.add_torus_arc(
                major_radius=cage_radius,
                minor_radius=0.055,
                start_angle=start,
                end_angle=end,
                arc_segments=segments,
                minor_segments=6,
                location=(0.0, y, 0.0),
                rotation=cage_rotation,
                bevel=True,
            )

    # Three axial ties terminate inside the rails, so their circular caps are
    # hidden intersections rather than exposed hard edges.
    for angle_degrees in (-138.0, -28.0, 132.0):
        angle = math.radians(angle_degrees)
        x = cage_radius * math.cos(angle)
        z = cage_radius * math.sin(angle)
        body.add_cylinder_between(
            (x, -cage_depth, z),
            (x, cage_depth, z),
            radius=0.05,
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
        bevel=True,
    )

    # One continuous 225-degree plate replaces six disconnected paddles.  The
    # start end is deliberately heavier than the finish end, forming unequal
    # integrated shoes within the same polygon.  A single overlapping drive dog
    # exits tangentially from the light end and is the only secondary shell.
    start_angle = math.radians(-145.0)
    end_angle = math.radians(80.0)
    steps = 13
    outer_points = []
    inner_points = []
    for index in range(steps + 1):
        ratio = index / steps
        angle = start_angle + (end_angle - start_angle) * ratio
        outer_radius = 0.675
        if index == 0:
            outer_radius = 0.74
        elif index == 1:
            outer_radius = 0.70
        elif index == steps:
            outer_radius = 0.695
        outer_points.append(
            (outer_radius * math.cos(angle), outer_radius * math.sin(angle))
        )
    for index in reversed(range(steps + 1)):
        ratio = index / steps
        angle = start_angle + (end_angle - start_angle) * ratio
        inner_radius = 0.595
        if index == 0:
            inner_radius = 0.535
        elif index == steps:
            inner_radius = 0.61
        inner_points.append(
            (inner_radius * math.cos(angle), inner_radius * math.sin(angle))
        )
    accent.add_extruded_polygon_y(
        outer_points + inner_points,
        depth=0.08,
        bevel=True,
    )
    accent.add_box(
        size=(0.24, 0.08, 0.09),
        location=(0.20, -0.01, 0.645),
        rotation=(0.0, math.radians(-8.0), 0.0),
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:open asymmetric counterweight sector with one drive dog;"
            "side:twin service-gap cage rails around a thin load plate;"
            "top:offset flywheel chassis with unequal counterweight ends"
        ),
        body_detail="central hex hub inside asymmetric twin service-gap rails",
        accent_pivot="asymmetric counterweight hub center; scale XYZ",
        accent_origin=(0.0, 0.0, 0.0),
    )
