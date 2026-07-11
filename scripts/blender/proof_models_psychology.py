"""Psychology proof instrument geometry."""

from __future__ import annotations

import math

from hard_surface import MeshAssembler, ModelGeometry


def build_risk_sentiment() -> ModelGeometry:
    """Build a split polar yoke with a true-hinge angular pendulum."""

    body = MeshAssembler()
    yoke_rotation = (math.pi * 0.5, 0.0, 0.0)
    body.add_torus_arc(
        0.68,
        0.11,
        math.radians(24.0),
        math.radians(156.0),
        arc_segments=22,
        minor_segments=6,
        location=(0.0, 0.10, 0.0),
        rotation=yoke_rotation,
    )
    body.add_torus_arc(
        0.68,
        0.11,
        math.radians(204.0),
        math.radians(336.0),
        arc_segments=22,
        minor_segments=6,
        location=(0.0, 0.10, 0.0),
        rotation=yoke_rotation,
    )
    body.add_torus(
        0.49,
        0.07,
        major_segments=32,
        minor_segments=6,
        location=(0.0, -0.04, 0.0),
        rotation=(math.radians(66.0), math.radians(17.0), math.radians(12.0)),
    )
    for x, z in ((-0.72, 0.28), (0.72, 0.28), (-0.72, -0.28), (0.72, -0.28)):
        body.add_cylinder(
            0.095,
            0.19,
            segments=12,
            location=(x, 0.10, z),
            rotation=(math.pi * 0.5, 0.0, 0.0),
            bevel=z > 0.0,
        )

    accent = MeshAssembler()
    hinge = (0.0, -0.15, 0.47)
    bob = (0.13, -0.15, -0.32)
    accent.add_cylinder_between(hinge, bob, radius=0.05, segments=16)
    accent.add_uv_sphere(0.18, segments=16, rings=6, location=bob, scale=(0.90, 0.70, 1.0))
    accent.add_cylinder(
        0.09,
        0.20,
        segments=12,
        location=hinge,
        rotation=(math.pi * 0.5, 0.0, 0.0),
        bevel=True,
    )
    accent.add_extruded_polygon_y(
        [(-0.10, -0.06), (0.09, -0.09), (0.14, 0.04), (0.02, 0.14), (-0.12, 0.07)],
        depth=0.09,
        location=(0.11, -0.15, -0.53),
        rotation=(0.0, 0.0, math.radians(-8.0)),
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:split-yoke+angular-pendulum;"
            "side:twisted-gimbal+offset-bob;"
            "top:open-polar-stops"
        ),
        body_detail="split curved yoke; twisted gimbal; four polar stops",
        accent_pivot="upper pendulum hinge",
        accent_origin=hinge,
    )
