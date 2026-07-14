"""Psychology proof instrument geometry."""

from __future__ import annotations

import math

from hard_surface import MeshAssembler, ModelGeometry


def build_risk_sentiment() -> ModelGeometry:
    """Build an open-arch pendulum mood meter over a graduated fear-greed dial."""

    body = MeshAssembler()
    frame_rotation = (math.pi * 0.5, 0.0, 0.0)
    # Open top arch: the yoke keeps only its 120-degree crown, so its mouth is
    # a 240-degree opening and the whole swing window stays visible from the
    # 3/4 camera (-Y, +Z).  The old front/back cheek plates and bottom arc are
    # gone; they were what hid the pendulum and made the model read as a drum.
    body.add_torus_arc(
        0.64,
        0.10,
        math.radians(30.0),
        math.radians(150.0),
        arc_segments=24,
        minor_segments=6,
        location=(0.0, 0.06, 0.0),
        rotation=frame_rotation,
    )
    # Slimmed yoke cheeks: two outboard columns tie the arch ends to the dial.
    # Their inner faces sit at |x|=0.63, so with an 0.80 arm the pendulum owns
    # an unobstructed swing arc of 2*asin(0.63/0.80) ~= 104 degrees.
    for x in (-0.70, 0.70):
        body.add_box(
            (0.14, 0.56, 0.98),
            location=(x, -0.03, -0.11),
            bevel=True,
        )
    # Pivot boss on the body: the pendulum hangs from a visible hinge pin that
    # bridges the arch crown, keeping the accent purely arm+bob.
    hinge = (0.0, -0.10, 0.44)
    body.add_cylinder(
        0.12,
        0.42,
        segments=16,
        location=hinge,
        rotation=frame_rotation,
        bevel=True,
    )
    # Low arc dial plate under the bob: an annular sector concentric with the
    # hinge (radii 1.13..1.30 over 240..300 degrees) suggesting the
    # greed<->fear range.  Its 1.00 Blender-Y depth carries the side and top
    # silhouettes the removed cheek plates used to provide.
    dial_points = []
    for step in range(15):
        u = math.radians(240.0 + 60.0 * step / 14.0)
        dial_points.append((1.30 * math.cos(u), 1.30 * math.sin(u)))
    for step in range(15):
        u = math.radians(300.0 - 60.0 * step / 14.0)
        dial_points.append((1.13 * math.cos(u), 1.13 * math.sin(u)))
    body.add_extruded_polygon_y(
        dial_points,
        depth=1.00,
        location=(0.0, -0.10, 0.44),
        bevel=True,
    )
    # Five radial graduation ticks on the dial face make the meter reading
    # unmistakable; each long axis points at the hinge.
    for degrees in (250.0, 260.0, 270.0, 280.0, 290.0):
        u = math.radians(degrees)
        body.add_box(
            (0.045, 0.07, 0.17),
            location=(1.215 * math.cos(u), -0.60, 0.44 + 1.215 * math.sin(u)),
            rotation=(0.0, math.radians(90.0 - degrees), 0.0),
        )

    accent = MeshAssembler()
    # Pendulum frozen mid-swing: 0.80 arm tilted 20 degrees off vertical, so
    # bob = hinge + 0.80*(sin20, 0, -cos20).  The bob hangs far below the
    # arch mouth (z=0.32) and clears the dial inner face by 0.08.
    bob = (0.2736, -0.10, -0.3118)
    accent.add_cylinder_between(hinge, bob, radius=0.068, segments=14, bevel=True)
    accent.add_uv_sphere(0.25, segments=22, rings=8, location=bob)

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:open-arch+20deg-pendulum-over-dial;"
            "side:deep-dial-slab+cheek-columns;"
            "top:arc-dial-slab+arch-band"
        ),
        body_detail="open top arch; outboard cheek columns; pivot boss; graduated fear-greed dial arc",
        accent_pivot="upper pendulum hinge",
        accent_origin=hinge,
    )
