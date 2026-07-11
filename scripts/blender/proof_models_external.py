"""Precision proof instruments for foreign exchange and crude oil.

The builders in this module are deliberately data-only: they append closed,
disconnected primitive shells to ``MeshAssembler`` instances and leave Blender
object creation, normalization, materials, and export to the shared pipeline.
"""

from __future__ import annotations

import math

from hard_surface import MeshAssembler, ModelGeometry


def build_fx() -> ModelGeometry:
    """Build an asymmetric double-gimbal foreign-exchange instrument.

    Source triangle budget before the evaluated precision bevel:
    body = 2*(38*8 + 34*8) + 4*(4*12-4) + (4*14-4)
           + 2*(4*12-4) = 1,468
    accent = 2*28*8 + (4*12-4) = 492
    total = 1,960
    """

    body = MeshAssembler()
    accent = MeshAssembler()

    # The two primary bands use different centers and compound tilts.  Their
    # 0.15-unit radial separation remains a readable shadow break after the
    # final pair normalization.
    body.add_torus(
        major_radius=1.18,
        minor_radius=0.12,
        major_segments=38,
        minor_segments=8,
        location=(-0.05, 0.02, 0.04),
        rotation=(math.radians(88.0), math.radians(8.0), math.radians(-6.0)),
    )
    body.add_torus(
        major_radius=0.80,
        minor_radius=0.11,
        major_segments=34,
        minor_segments=8,
        location=(0.10, -0.03, -0.03),
        rotation=(math.radians(67.0), math.radians(-18.0), math.radians(14.0)),
    )

    # Asymmetric bearing pods lock the rings into a mechanical gimbal reading
    # rather than an atom or globe.  Each pod is a separately closed shell.
    bearing_pods = (
        ((-1.24, 0.02, 0.15), (0.0, math.pi * 0.5, 0.0)),
        ((1.14, -0.01, -0.08), (0.0, math.pi * 0.5, 0.0)),
        ((0.19, -0.12, 0.82), (0.0, 0.0, 0.0)),
        ((0.03, 0.08, -0.86), (0.0, 0.0, 0.0)),
    )
    for location, rotation in bearing_pods:
        body.add_cylinder(
            radius=0.15,
            depth=0.22,
            segments=12,
            location=location,
            rotation=rotation,
        )

    ring_pivot = (0.10, -0.03, -0.02)
    body.add_cylinder_between(
        (ring_pivot[0], -0.29, ring_pivot[2]),
        (ring_pivot[0], 0.26, ring_pivot[2]),
        radius=0.105,
        segments=14,
        bevel=True,
    )
    for y in (-0.31, 0.28):
        body.add_cylinder(
            radius=0.17,
            depth=0.12,
            segments=12,
            location=(ring_pivot[0], y, ring_pivot[2]),
            rotation=(math.pi * 0.5, 0.0, 0.0),
        )
    # The restrained category accent is a third, smaller exchange ring.  Its
    # authored center becomes the true local origin so runtime Y rotation is a
    # counter-rotation around the ring rather than an orbit around the model.
    accent.add_torus(
        major_radius=0.47,
        minor_radius=0.10,
        major_segments=28,
        minor_segments=8,
        location=ring_pivot,
        rotation=(math.radians(91.0), math.radians(27.0), math.radians(-11.0)),
    )
    # A visible keyed center hub makes the counter-rotating accent a precision
    # mechanism rather than a decorative ring.  Its exposed cap loops carry
    # the selective three-segment bevel.
    accent.add_cylinder(
        radius=0.15,
        depth=0.10,
        segments=12,
        location=ring_pivot,
        rotation=(math.pi * 0.5, 0.0, 0.0),
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:offset nested gimbals with unequal bearing pods; "
            "side:crossed tilted bands around a short exchange axle; "
            "top:asymmetric ring stack with displaced inner center"
        ),
        body_detail="double tilted gimbal, four bearing pods, and short exchange axle",
        accent_pivot="true offset ring center; counter-rotate local Y",
        accent_origin=ring_pivot,
    )


def build_oil() -> ModelGeometry:
    """Build a horizontal pressure capsule with an offset calibration valve.

    Source triangle budget before the evaluated precision bevel:
    body = 4*36*5 + 2*30*8 + 2*(4*14-4) = 1,304
    accent = 2*20*6 + 4*(4*8-4) + (4*12-4) = 396
    total = 1,700
    """

    body = MeshAssembler()
    accent = MeshAssembler()

    # A continuous capsule profile supplies a cylindrical pressure chamber and
    # genuinely domed endcaps without reading as either a barrel or a droplet.
    body.add_capsule_x(
        half_length=0.78,
        radius=0.42,
        segments=36,
        hemisphere_steps=5,
    )
    body.add_torus(
        major_radius=0.47,
        minor_radius=0.095,
        major_segments=30,
        minor_segments=8,
        location=(-0.20, 0.0, 0.0),
        rotation=(0.0, math.pi * 0.5, 0.0),
    )

    # The line leaves the front-side shoulder on a diagonal and terminates in a
    # compact calibration socket below the valve, creating a visible offset in
    # front, side, and top views.
    body.add_cylinder_between(
        (0.40, -0.31, 0.18),
        (0.46, -0.53, 0.39),
        radius=0.09,
        segments=14,
    )
    body.add_cylinder(
        radius=0.15,
        depth=0.16,
        segments=14,
        location=(0.46, -0.53, 0.41),
        bevel=True,
    )

    valve_pivot = (0.46, -0.53, 0.67)
    # Blender exports +Y as glTF +Z.  Authoring the complete valve wheel in the
    # XZ plane therefore gives the runtime's declared rotate-z motion the true
    # wheel normal, with no compensating object rotation or off-center orbit.
    accent.add_torus(
        major_radius=0.25,
        minor_radius=0.09,
        major_segments=20,
        minor_segments=6,
        location=valve_pivot,
        rotation=(math.pi * 0.5, 0.0, 0.0),
    )
    spoke_inner = 0.07
    spoke_outer = 0.20
    for index in range(4):
        angle = math.radians(22.5 + index * 90.0)
        cosine = math.cos(angle)
        sine = math.sin(angle)
        accent.add_cylinder_between(
            (
                valve_pivot[0] + cosine * spoke_inner,
                valve_pivot[1],
                valve_pivot[2] + sine * spoke_inner,
            ),
            (
                valve_pivot[0] + cosine * spoke_outer,
                valve_pivot[1],
                valve_pivot[2] + sine * spoke_outer,
            ),
            radius=0.075,
            segments=8,
        )
    accent.add_cylinder(
        radius=0.135,
        depth=0.12,
        segments=12,
        location=valve_pivot,
        rotation=(math.pi * 0.5, 0.0, 0.0),
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:horizontal domed capsule with raised offset valve; "
            "side:reinforcing collar and diagonal pressure takeoff; "
            "top:long vessel axis opposed by a four-spoke calibration wheel"
        ),
        body_detail="domed pressure capsule, reinforcing collar, and offset pipe socket",
        accent_pivot="true side-valve hub; Blender Y normal exports to rotate Z",
        accent_origin=valve_pivot,
    )
