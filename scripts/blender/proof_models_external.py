"""Precision proof instruments for foreign exchange and crude oil.

The builders in this module are deliberately data-only: they append closed,
disconnected primitive shells to ``MeshAssembler`` instances and leave Blender
object creation, normalization, materials, and export to the shared pipeline.
"""

from __future__ import annotations

import math

from hard_surface import MeshAssembler, ModelGeometry


def build_fx() -> ModelGeometry:
    """Build the universal currency-exchange icon for KRW/USD.

    An upright won-struck coin (drum + raised face boss + relief marks) stands
    on a plinth pedestal, and the category accent is the classic pair of
    opposing curved arrows: two horizontal torus arcs tipped with arrowhead
    prisms that circulate around the coin in the X-Y plane.  Blender +Z exports
    to glTF +Y, so the runtime rotate-y motion spins the arrow pair around the
    standing coin, which is exactly the "exchange" gesture.
    """

    body = MeshAssembler()
    accent = MeshAssembler()

    # Upright coin core: the drum axis lies along Blender Y so the flat struck
    # face looks straight at the -Y front camera.  The beveled drum rim plus a
    # proud face boss give the stepped edge profile that reads "coin" in
    # silhouette; the 0.46 boss depth keeps the side (Y-Z) view a solid slab.
    coin_center = (0.0, 0.0, 0.14)
    body.add_cylinder(
        radius=0.78,
        depth=0.40,
        segments=40,
        location=coin_center,
        rotation=(math.pi * 0.5, 0.0, 0.0),
        bevel=True,
    )
    body.add_cylinder(
        radius=0.60,
        depth=0.54,
        segments=32,
        location=coin_center,
        rotation=(math.pi * 0.5, 0.0, 0.0),
    )

    # Relief won mark on both struck faces: four alternating strokes make the
    # W and two wider crossing bars complete the currency glyph.  Each mark
    # protrudes 0.07 out of the boss face and stays buried 0.03 inside it, so
    # no shell face is coplanar with the boss caps.
    stroke_tilt = math.radians(16.0)
    for face_y in (-0.29, 0.29):
        for leg_x, tilt_sign in ((-0.15, -1.0), (-0.05, 1.0), (0.05, -1.0), (0.15, 1.0)):
            body.add_box(
                size=(0.09, 0.10, 0.36),
                location=(leg_x, face_y, 0.14),
                rotation=(0.0, tilt_sign * stroke_tilt, 0.0),
            )
        for bar_z in (0.055, 0.225):
            body.add_box(
                size=(0.56, 0.10, 0.08),
                location=(0.0, face_y, bar_z),
            )

    # Plinth pedestal: a short stem buried in both the coin rim and the base
    # keeps every cap hidden, and the wide rounded base balances the top and
    # side occupancy against the horizontal arrow orbit.
    body.add_cylinder(
        radius=0.17,
        depth=0.32,
        segments=16,
        location=(0.0, 0.0, -0.76),
    )
    body.add_rounded_box_y(
        width=1.06,
        height=0.26,
        depth=1.02,
        radius=0.10,
        corner_segments=3,
        location=(0.0, 0.0, -0.98),
        bevel=True,
    )

    # Exchange accent: two opposing 135-degree torus arcs chase each other in
    # the horizontal X-Y plane at coin-equator height.  Their shared center is
    # the authored accent origin, so the runtime local-Y (Blender Z) rotation
    # circulates the arrows around the standing coin.
    orbit_radius = 0.98
    orbit_minor = 0.09
    arc_spans = (
        (math.radians(17.0), math.radians(147.0)),
        (math.radians(197.0), math.radians(327.0)),
    )
    for start_angle, end_angle in arc_spans:
        accent.add_torus_arc(
            major_radius=orbit_radius,
            minor_radius=orbit_minor,
            start_angle=start_angle,
            end_angle=end_angle,
            arc_segments=26,
            minor_segments=8,
            location=coin_center,
            rotation=(0.0, 0.0, 0.0),
            bevel=True,
        )
    # Arrowhead prisms cap each arc tip and point along the counterclockwise
    # travel tangent.  The 0.20 slab thickness fully swallows the arc end cap,
    # and the blades stay razor-thin on Blender Z so the orbit reads as a flat
    # circulation band, never a second disc.
    for end_angle_degrees in (147.0, 327.0):
        end_angle = math.radians(end_angle_degrees)
        accent.add_extruded_polygon_y(
            points_xz=((0.30, 0.0), (-0.12, 0.22), (-0.12, -0.22)),
            depth=0.20,
            location=(
                orbit_radius * math.cos(end_angle),
                orbit_radius * math.sin(end_angle),
                coin_center[2],
            ),
            rotation=(math.pi * 0.5, 0.0, end_angle + math.pi * 0.5),
        )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:upright won-struck coin on a plinth with a level arrow orbit "
            "crossing its equator; "
            "side:thick coin slab pierced by the flat circulation band; "
            "top:two chasing arc arrows circling the coin core"
        ),
        body_detail="upright won-relief coin drum, face bosses, and plinth pedestal",
        accent_pivot="true offset ring center; counter-rotate local Y",
        accent_origin=coin_center,
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
