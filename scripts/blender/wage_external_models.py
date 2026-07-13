"""Iconic instruments for the wage and external-economy batch.

Every builder is scene-independent.  It appends closed primitive shells to a
body and an accent assembler, leaving normalization, material assignment, and
Blender object creation to the shared authoring pipeline.  Coordinates follow
the library convention: Blender +Z is up and -Y faces the camera.

Each model is a machined, chamfered version of a clear economic pictogram: the
dark ``body`` carries the recognizable structure, and the category-colored
``accent`` carries the eye-catching element that names the concept.
"""

from __future__ import annotations

import math

from hard_surface import MeshAssembler, ModelGeometry


_QUARTER_TURN = math.pi * 0.5
_LAY_ALONG_Y = (_QUARTER_TURN, 0.0, 0.0)  # a Z-axis primitive rotated onto Y
_LAY_ONTO_XY = (_QUARTER_TURN, 0.0, 0.0)  # an XZ extrusion rotated flat into XY


def _star_points_xz(
    outer_radius: float,
    inner_radius: float,
    points: int = 5,
    phase: float = _QUARTER_TURN,
) -> tuple[tuple[float, float], ...]:
    """Return a simple (non-self-intersecting) star polygon in the XZ plane."""

    coords: list[tuple[float, float]] = []
    for index in range(points * 2):
        radius = outer_radius if index % 2 == 0 else inner_radius
        angle = phase + math.pi * index / points
        coords.append((radius * math.cos(angle), radius * math.sin(angle)))
    return tuple(coords)


def _right_arrow_points_xz(
    tail_x: float,
    shaft_half: float,
    head_x: float,
    head_half: float,
    tip_x: float,
) -> tuple[tuple[float, float], ...]:
    """Return a block arrow pointing toward +X (an outbound arrow)."""

    return (
        (tail_x, shaft_half),
        (head_x, shaft_half),
        (head_x, head_half),
        (tip_x, 0.0),
        (head_x, -head_half),
        (head_x, -shaft_half),
        (tail_x, -shaft_half),
    )


def _vertical_arrow_points_xz(
    tail_z: float,
    shaft_half: float,
    head_z: float,
    head_half: float,
    tip_z: float,
) -> tuple[tuple[float, float], ...]:
    """Return a block arrow along Z.  tip_z beyond head_z beyond tail_z sets aim."""

    return (
        (-shaft_half, tail_z),
        (shaft_half, tail_z),
        (shaft_half, head_z),
        (head_half, head_z),
        (0.0, tip_z),
        (-head_half, head_z),
        (-shaft_half, head_z),
    )


def _pointer_needle_points_xz(
    half_width: float,
    shoulder_z: float,
    tip_z: float,
    base_z: float,
) -> tuple[tuple[float, float], ...]:
    """Return a spade pointer polygon (base block, tapered tip) pointing +Z."""

    return (
        (-half_width, base_z),
        (half_width, base_z),
        (half_width, shoulder_z),
        (0.0, tip_z),
        (-half_width, shoulder_z),
    )


def _add_conical_wall_z(
    assembler: MeshAssembler,
    *,
    top_outer: float,
    top_inner: float,
    bottom_outer: float,
    bottom_inner: float,
    z_top: float,
    z_bottom: float,
    segments: int,
    bevel: bool = False,
) -> None:
    """Append one closed hollow frustum (a machined funnel/hopper wall)."""

    def ring(radius: float, z: float) -> list[tuple[float, float, float]]:
        return [
            (radius * math.cos(2.0 * math.pi * i / segments),
             radius * math.sin(2.0 * math.pi * i / segments),
             z)
            for i in range(segments)
        ]

    outer_top = ring(top_outer, z_top)
    inner_top = ring(top_inner, z_top)
    outer_bottom = ring(bottom_outer, z_bottom)
    inner_bottom = ring(bottom_inner, z_bottom)
    vertices = outer_top + inner_top + outer_bottom + inner_bottom

    ot, it, ob, ib = 0, segments, 2 * segments, 3 * segments
    faces: list[tuple[int, ...]] = []
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((ot + i, ot + j, ob + j, ob + i))   # outer wall
        faces.append((it + j, it + i, ib + i, ib + j))   # inner wall
        faces.append((ot + j, ot + i, it + i, it + j))   # top annulus
        faces.append((ob + i, ob + j, ib + j, ib + i))   # bottom annulus
    assembler.append(vertices, faces, bevel=bevel)


def build_wages() -> ModelGeometry:
    """Build an ascending staircase crowned by a coin: pay rising."""

    body = MeshAssembler()
    accent = MeshAssembler()

    # Rising staircase (left -> right), four solid chamfered blocks on a plinth.
    step_depth = 1.30
    baseline = -0.52
    step_layout = (
        (-0.66, 0.42),
        (-0.22, 0.78),
        (0.22, 1.14),
        (0.66, 1.50),
    )
    for x, height in step_layout:
        body.add_box(
            size=(0.46, step_depth, height),
            location=(x, 0.0, baseline + height * 0.5),
            bevel=True,
        )
    body.add_box(
        size=(1.92, step_depth + 0.10, 0.16),
        location=(0.0, 0.0, baseline - 0.08),
        bevel=True,
    )
    # A back riser wall ties the steps into one solid mass for the side view.
    body.add_box(
        size=(1.92, 0.16, 1.60),
        location=(0.0, 0.61, baseline + 0.72),
        bevel=True,
    )

    # The coin: a thick struck disc, thin on Y, standing on the top step.  A
    # raised hub and a colored rim torus give it a minted-coin read.
    coin_center = (0.66, 0.0, 1.02)
    accent.add_cylinder(
        radius=0.54,
        depth=0.26,
        segments=32,
        location=coin_center,
        rotation=_LAY_ALONG_Y,
        bevel=True,
    )
    accent.add_cylinder(
        radius=0.19,
        depth=0.30,
        segments=20,
        location=coin_center,
        rotation=_LAY_ALONG_Y,
        bevel=True,
    )
    accent.add_torus(
        major_radius=0.40,
        minor_radius=0.05,
        major_segments=28,
        minor_segments=6,
        location=coin_center,
        rotation=_LAY_ALONG_Y,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:four rising stair blocks under a struck coin on the top step;"
            "side:deep chamfered stair mass behind a thin face-on coin;"
            "top:stepped tread footprint with one coin disc over the high step"
        ),
        body_detail="four-tread rising staircase, grounding plinth, and back riser wall",
        accent_pivot="ratchet step axis; glTF Z rotation is Blender -Y",
        accent_origin=coin_center,
    )


def build_exports() -> ModelGeometry:
    """Build a corrugated shipping container with an outbound arrow: goods out."""

    body = MeshAssembler()
    accent = MeshAssembler()

    # The container body: a long chamfered box on four short feet.
    container = (0.0, 0.0, 0.06)
    body.add_box(
        size=(1.58, 1.02, 0.98),
        location=container,
        bevel=True,
    )
    # Vertical corrugation ridges raised off the front (-Y) face.  These strips
    # are narrower than twice the fixed bevel width, so they stay unbeveled to
    # avoid clamp-collapsed zero-area faces.
    for x in (-0.60, -0.36, -0.12, 0.12, 0.36, 0.60):
        body.add_box(
            size=(0.06, 0.07, 0.86),
            location=(x, -0.545, 0.06),
            bevel=False,
        )
    # Top and bottom rails plus a door seam keep it reading as a container.
    for z in (0.52, -0.40):
        body.add_box(
            size=(1.60, 0.09, 0.09),
            location=(0.0, -0.52, z + 0.06),
            bevel=True,
        )
    for x in (-0.62, 0.62):
        for y in (-0.36, 0.36):
            body.add_box(
                size=(0.16, 0.18, 0.16),
                location=(x, y, -0.60),
                bevel=True,
            )

    # The outbound arrow: a flat plate on the front face pointing out (+X),
    # thin on Y, translating forward (Blender -Y) as cargo ships.
    arrow_origin = (0.0, -0.60, 0.06)
    accent.add_extruded_polygon_y(
        _right_arrow_points_xz(
            tail_x=-0.60,
            shaft_half=0.22,
            head_x=0.16,
            head_half=0.44,
            tip_x=0.68,
        ),
        depth=0.13,
        location=arrow_origin,
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:a ribbed cargo container carrying one outbound arrow decal;"
            "side:deep footed container box ahead of a thin forward arrow plate;"
            "top:long corrugated container with a projecting outbound arrow"
        ),
        body_detail="corrugated shipping container, top and sill rails, and four feet",
        accent_pivot="outbound vane plate; glTF +Z advances along Blender -Y",
        accent_origin=arrow_origin,
    )


def build_current_account() -> ModelGeometry:
    """Build a balance scale with unequal pans and a reading pointer: trade balance."""

    body = MeshAssembler()
    accent = MeshAssembler()

    # A heavy deep base anchors the instrument and supplies the Y mass.
    body.add_box(
        size=(0.66, 1.26, 0.18),
        location=(0.0, 0.0, -0.86),
        bevel=True,
    )
    # Central upright post.
    body.add_box(
        size=(0.24, 0.62, 1.36),
        location=(0.0, 0.0, -0.10),
        bevel=True,
    )
    # Horizontal balance beam across the top.
    beam_z = 0.58
    body.add_box(
        size=(1.44, 0.52, 0.14),
        location=(0.0, 0.0, beam_z),
        bevel=True,
    )
    # Two unequal hanging pans (short drums, face up).  Left sits lower/larger.
    pan_specs = (
        (-0.58, 0.34, -0.16, 0.14),
        (0.58, 0.28, 0.10, 0.12),
    )
    for x, radius, pan_z, pan_depth in pan_specs:
        body.add_cylinder_between(
            (x, 0.0, beam_z - 0.06),
            (x, 0.0, pan_z + pan_depth * 0.5),
            radius=0.03,
            segments=8,
        )
        body.add_cylinder(
            radius=radius,
            depth=pan_depth,
            segments=24,
            location=(x, 0.0, pan_z),
            bevel=True,
        )

    # The reading element: a colored index disc and a spade pointer at the
    # fulcrum, both flat and thin on Y; the pointer tilts (rotate about Blender
    # -Y) to show which way the balance leans.
    fulcrum = (0.0, 0.0, beam_z)
    accent.add_cylinder(
        radius=0.33,
        depth=0.12,
        segments=28,
        location=fulcrum,
        rotation=_LAY_ALONG_Y,
        bevel=True,
    )
    accent.add_extruded_polygon_y(
        _pointer_needle_points_xz(
            half_width=0.08,
            shoulder_z=0.32,
            tip_z=0.64,
            base_z=-0.13,
        ),
        depth=0.10,
        location=fulcrum,
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:a level beam on a post with two unequal pans and a center pointer;"
            "side:deep base and post behind a thin fulcrum dial and pointer;"
            "top:beam and base footprint with two offset pan discs"
        ),
        body_detail="deep base, upright post, balance beam, and two unequal hanging pans",
        accent_pivot="bilateral balance axle; glTF Z rotation is Blender -Y",
        accent_origin=fulcrum,
    )


def build_capital_flows() -> ModelGeometry:
    """Build a funnel drawing money in with inflow chevrons: capital flowing in."""

    body = MeshAssembler()
    accent = MeshAssembler()

    # A flared hopper (wide mouth narrowing to a spout), machined as two closed
    # frustum walls with a colored-free dark rim torus at the mouth.
    _add_conical_wall_z(
        body,
        top_outer=0.70,
        top_inner=0.60,
        bottom_outer=0.24,
        bottom_inner=0.16,
        z_top=0.56,
        z_bottom=-0.16,
        segments=28,
        bevel=True,
    )
    _add_conical_wall_z(
        body,
        top_outer=0.24,
        top_inner=0.16,
        bottom_outer=0.205,
        bottom_inner=0.13,
        z_top=-0.16,
        z_bottom=-0.86,
        segments=24,
        bevel=False,
    )
    body.add_torus(
        major_radius=0.66,
        minor_radius=0.06,
        major_segments=30,
        minor_segments=6,
        location=(0.0, 0.0, 0.56),
    )
    # A collar ring at the spout base grounds the throat.
    body.add_torus(
        major_radius=0.205,
        minor_radius=0.05,
        major_segments=20,
        minor_segments=6,
        location=(0.0, 0.0, -0.86),
    )

    # Three inflow chevrons above the mouth, flat and thin on Y, pointing
    # down-and-inward; they translate forward (Blender -Y) as capital arrives.
    chevron_origin = (0.0, 0.0, 0.74)
    chevron_specs = (
        (-0.44, 0.02, -math.radians(24.0)),
        (0.0, 0.14, 0.0),
        (0.44, 0.02, math.radians(24.0)),
    )
    for x, z, tilt in chevron_specs:
        accent.add_extruded_polygon_y(
            _vertical_arrow_points_xz(
                tail_z=0.42,
                shaft_half=0.105,
                head_z=0.04,
                head_half=0.24,
                tip_z=-0.28,
            ),
            depth=0.13,
            location=(x, 0.0, z),
            rotation=(0.0, tilt, 0.0),
            bevel=True,
        )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:a flared funnel with three chevrons descending into its mouth;"
            "side:deep conical hopper and spout under thin inward-tilted chevrons;"
            "top:concentric funnel rings ringed by three inbound chevrons"
        ),
        body_detail="flared funnel bowl, tapering spout, mouth rim, and throat collar",
        accent_pivot="inflow gate face; glTF +Z advances along Blender -Y",
        accent_origin=chevron_origin,
    )


def build_fed_rate() -> ModelGeometry:
    """Build a face-up US rate dial with a star and needle: US central-bank rate."""

    body = MeshAssembler()
    accent = MeshAssembler()

    # A compact dial drum (axis Z, face up) - deliberately distinct from
    # policy_rate's front-facing revolved gauge.
    face_z = 0.34
    body.add_cylinder(
        radius=0.66,
        depth=0.74,
        segments=24,
        location=(0.0, 0.0, -0.02),
        bevel=True,
    )
    # A raised rim torus + a ring of knurl blocks form the distinctive bezel.
    body.add_torus(
        major_radius=0.64,
        minor_radius=0.075,
        major_segments=22,
        minor_segments=6,
        location=(0.0, 0.0, face_z),
    )
    for index in range(12):
        angle = 2.0 * math.pi * index / 12.0
        body.add_box(
            size=(0.09, 0.15, 0.12),
            location=(0.60 * math.cos(angle), 0.60 * math.sin(angle), face_z),
            rotation=(0.0, 0.0, angle + _QUARTER_TURN),
            bevel=index < 4,
        )
    # Tick marks recessed below the rim on the up-facing dial face.
    for index in range(8):
        angle = 2.0 * math.pi * index / 8.0
        body.add_box(
            size=(0.05, 0.05, 0.05),
            location=(0.44 * math.cos(angle), 0.44 * math.sin(angle), face_z + 0.05),
        )
    # A shallow foot ring stabilizes the puck and fills the lower silhouette.
    body.add_cylinder(
        radius=0.72,
        depth=0.12,
        segments=20,
        location=(0.0, 0.0, -0.44),
        bevel=True,
    )

    # The reading: a raised colored five-point star and a needle on the dial
    # face, flat and thin on Blender Z, pivoting about Y.
    star_z = face_z + 0.08
    accent.add_extruded_polygon_y(
        _star_points_xz(outer_radius=0.63, inner_radius=0.25, points=5),
        depth=0.10,
        location=(0.0, 0.0, star_z),
        rotation=_LAY_ONTO_XY,
        bevel=True,
    )
    # Needle laid across the face (thin Z), offset from the hub outward.
    needle_angle = math.radians(58.0)
    accent.add_box(
        size=(0.64, 0.10, 0.06),
        location=(0.30 * math.cos(needle_angle), 0.30 * math.sin(needle_angle), star_z + 0.02),
        rotation=(0.0, 0.0, needle_angle),
        bevel=True,
    )
    accent.add_cylinder(
        radius=0.13,
        depth=0.10,
        segments=18,
        location=(0.0, 0.0, star_z + 0.03),
        bevel=True,
    )

    hub_origin = (0.0, 0.0, star_z)

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:a wide knurled dial drum seen edge-on under a raised star and needle;"
            "side:shallow footed rate puck below a thin face-flat star and pointer;"
            "top:a bezelled dial face carrying a five-point star and one needle"
        ),
        body_detail="wide shallow dial drum, knurled bezel ring, twelve ticks, and foot ring",
        accent_pivot="orbital governor axis; glTF Y rotation is Blender Z",
        accent_origin=hub_origin,
    )


def build_global_growth() -> ModelGeometry:
    """Build a banded globe with a rising up-arrow: global growth."""

    body = MeshAssembler()
    accent = MeshAssembler()

    # The globe, with raised latitude/longitude band rings (dark structure).
    globe_center = (0.0, 0.0, -0.14)
    body.add_uv_sphere(
        radius=0.78,
        segments=28,
        rings=16,
        location=globe_center,
    )
    body.add_torus(  # equator
        major_radius=0.78,
        minor_radius=0.045,
        major_segments=32,
        minor_segments=6,
        location=globe_center,
    )
    body.add_torus(  # a meridian
        major_radius=0.78,
        minor_radius=0.042,
        major_segments=32,
        minor_segments=6,
        location=globe_center,
        rotation=(0.0, _QUARTER_TURN, 0.0),
    )
    body.add_torus(  # a mid-latitude band
        major_radius=0.60,
        minor_radius=0.038,
        major_segments=28,
        minor_segments=6,
        location=(0.0, 0.0, globe_center[2] + 0.44),
    )
    # A polar cap gives the sphere a machined bevel to satisfy the body bevel.
    body.add_cylinder(
        radius=0.20,
        depth=0.10,
        segments=20,
        location=(0.0, 0.0, globe_center[2] + 0.74),
        bevel=True,
    )

    # A bold up-arrow rising above the globe - a chunky 3D extrusion (this model
    # has no thin-axis contract), pulsing with a scale-XYZ growth beat.
    arrow_origin = (0.0, 0.0, 0.98)
    accent.add_extruded_polygon_y(
        _vertical_arrow_points_xz(
            tail_z=-0.34,
            shaft_half=0.16,
            head_z=0.18,
            head_half=0.34,
            tip_z=0.56,
        ),
        depth=0.40,
        location=arrow_origin,
        bevel=True,
    )

    return ModelGeometry(
        body=body,
        accent=accent,
        silhouette_signature=(
            "front:a banded globe surmounted by a bold rising arrow;"
            "side:latitude-ringed sphere under a deep upward growth arrow;"
            "top:concentric globe rings beneath a compact arrow footprint"
        ),
        body_detail="banded globe with equator, meridian, mid-latitude ring, and polar cap",
        accent_pivot="orthogonal growth-band centroid; scale XYZ",
        accent_origin=arrow_origin,
    )


__all__ = (
    "build_wages",
    "build_exports",
    "build_current_account",
    "build_capital_flows",
    "build_fed_rate",
    "build_global_growth",
)
