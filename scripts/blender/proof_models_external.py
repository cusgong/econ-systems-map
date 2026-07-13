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

    The nested front rings are backed by a genuine three-axis rotor cage: an
    X-axis rotor drum that fills the side (Y-Z) end-view, a flat X-Y gimbal ring
    that fills the top periphery and extends the thin Blender-Y axis, and an
    enlarged counter-rotating accent ring.  The evaluated (post-bevel) triangle
    total is ~2,740, inside the 3,000 runtime cap.
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
        (ring_pivot[0], -0.62, ring_pivot[2]),
        (ring_pivot[0], 0.60, ring_pivot[2]),
        radius=0.115,
        segments=14,
        bevel=True,
    )
    for y in (-0.66, 0.64):
        body.add_cylinder(
            radius=0.24,
            depth=0.20,
            segments=12,
            location=(ring_pivot[0], y, ring_pivot[2]),
            rotation=(math.pi * 0.5, 0.0, 0.0),
        )

    # A rotor drum faces the Y-Z (side) plane so the gyroscope reads as bulk
    # edge-on instead of a flat ring stack.  Paired gimbal side plates sit at
    # +/-Y over the existing front footprint: they fill the thin side (Y-Z) and
    # top (X-Y) silhouettes while overlapping the front ring reading, so the
    # front silhouette stays intact and the instrument gains real Blender-Y
    # depth from every angle.
    rotor_center = (0.03, 0.0, 0.0)
    body.add_cylinder(
        radius=0.92,
        depth=0.82,
        segments=28,
        location=rotor_center,
        rotation=(0.0, math.pi * 0.5, 0.0),
    )
    # A third gimbal ring lies flat in the X-Y plane.  Edge-on it barely touches
    # the front and side silhouettes, but its annulus fills the wide top (X-Y)
    # periphery the rotor drum cannot reach and extends the thin Blender-Y axis.
    body.add_torus(
        major_radius=0.92,
        minor_radius=0.14,
        major_segments=30,
        minor_segments=6,
        location=rotor_center,
        rotation=(0.0, 0.0, 0.0),
    )
    # The restrained category accent is a third, smaller exchange ring.  Its
    # authored center becomes the true local origin so runtime Y rotation is a
    # counter-rotation around the ring rather than an orbit around the model.
    accent.add_torus(
        major_radius=0.52,
        minor_radius=0.16,
        major_segments=28,
        minor_segments=8,
        location=ring_pivot,
        rotation=(math.radians(91.0), math.radians(27.0), math.radians(-11.0)),
    )
    # A visible keyed center hub makes the counter-rotating accent a precision
    # mechanism rather than a decorative ring.  Its exposed cap loops carry
    # the selective three-segment bevel.
    accent.add_cylinder(
        radius=0.20,
        depth=0.16,
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
    """Build a horizontal pressure capsule with a coaxial side handwheel.

    Source triangle budget before the evaluated precision bevel:
    The wheel, shaft, and flanged body boss share one Blender-Y axis.  Blender
    exports that axis as glTF Z, so the declared rotate-z signature remains a
    physical handwheel rotation without a compensating child transform.
    """

    body = MeshAssembler()
    accent = MeshAssembler()

    # A continuous capsule profile supplies a cylindrical pressure chamber and
    # genuinely domed endcaps without reading as either a barrel or a droplet.
    body.add_capsule_x(
        half_length=0.78,
        radius=0.42,
        segments=34,
        hemisphere_steps=5,
    )
    body.add_torus(
        major_radius=0.47,
        minor_radius=0.095,
        major_segments=26,
        minor_segments=8,
        location=(-0.20, 0.0, 0.0),
        rotation=(0.0, math.pi * 0.5, 0.0),
    )
    # Bolted bonnet flanges girdle the pressure chamber.  Each is a
    # full-diameter disc facing the long X axis, kept thin in X so it barely
    # touches the front and top silhouettes yet fills the thin side (Y-Z)
    # end-view and broadens the vessel's Y and Z cross-section out of its flat,
    # narrow-barrel reading.
    for flange_x, flange_r, flange_d in (
        (-0.02, 0.72, 0.18),
        (-0.52, 0.60, 0.14),
        (0.44, 0.58, 0.14),
    ):
        body.add_cylinder(
            radius=flange_r,
            depth=flange_d,
            segments=28,
            location=(flange_x, 0.0, 0.0),
            rotation=(0.0, math.pi * 0.5, 0.0),
        )

    valve_pivot = (0.46, -0.62, 0.36)
    # A turned flange and boss project directly from the capsule flank.  Both
    # exposed cap rims receive the common precision bevel.  Their rear caps are
    # buried in the vessel, while the front caps overlap the rotating shaft.
    body.add_cylinder_between(
        (valve_pivot[0], -0.30, valve_pivot[2]),
        (valve_pivot[0], -0.49, valve_pivot[2]),
        radius=0.18,
        segments=12,
        bevel=True,
    )
    body.add_cylinder_between(
        (valve_pivot[0], -0.43, valve_pivot[2]),
        (valve_pivot[0], -0.55, valve_pivot[2]),
        radius=0.13,
        segments=12,
        bevel=True,
    )

    # Blender exports +Y as glTF +Z.  Authoring the complete valve wheel in the
    # XZ plane therefore gives the runtime's declared rotate-z motion the true
    # wheel normal, with no compensating object rotation or off-center orbit.
    accent.add_torus(
        major_radius=0.33,
        minor_radius=0.12,
        major_segments=22,
        minor_segments=6,
        location=(valve_pivot[0], valve_pivot[1], valve_pivot[2]),
        rotation=(math.pi * 0.5, 0.0, 0.0),
    )
    spoke_inner = 0.09
    spoke_outer = 0.28
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
            radius=0.09,
            segments=8,
        )
    accent.add_cylinder(
        radius=0.18,
        depth=0.15,
        segments=12,
        location=valve_pivot,
        rotation=(math.pi * 0.5, 0.0, 0.0),
        bevel=True,
    )
    # The rotating shaft is collinear with the wheel hub and penetrates the
    # stationary boss.  Its rear cap is hidden inside that boss; its exposed
    # front shoulder uses the same three-segment bevel as the hub.
    accent.add_cylinder_between(
        (valve_pivot[0], valve_pivot[1] - 0.04, valve_pivot[2]),
        (valve_pivot[0], -0.50, valve_pivot[2]),
        radius=0.075,
        segments=12,
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:horizontal domed capsule with offset side handwheel; "
            "side:wheel shaft seated in a coaxial flanged boss; "
            "top:long vessel axis opposed by a four-spoke calibration wheel"
        ),
        body_detail="domed pressure capsule, reinforcing collar, and coaxial side boss",
        accent_pivot="coaxial side-handwheel hub; Blender Y exports to glTF Z",
        accent_origin=valve_pivot,
    )
