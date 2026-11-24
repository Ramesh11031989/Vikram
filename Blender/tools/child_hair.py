"""Strand grooms for the child cast: a centre parting combed into two braids.

The scalp hair is authored on the unwarped design head (like `groom.py`) and
then follows the child-face warp; the braids are authored directly in child
space so they hang on the child's own back and shoulders.  Every fibre uses the
shared `groom.FiberGroup` (tapered three-sided strands, FiberUV, head-bone
skinning), so the child exports and shades like the adult cast.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import math
import random

from mathutils import Vector

from child import ChildCharacter, smoothstep
from groom import FiberGroup, mix


RGB = tuple[float, float, float]


@dataclass(frozen=True)
class BraidStyle:
    seed: int
    root: RGB
    highlight: RGB
    scalp_fibers: int = 2600
    # Hairline as (|angle| from the face, polar angle from the crown) pairs.
    # Stays above the ears (|angle| 1.35-1.9) so the combed hair clears them.
    hairline: Sequence[tuple[float, float]] = ((0, .89), (.55, .96), (1.0, 1.18), (1.35, 1.25),
                                               (1.85, 1.26), (2.15, 1.70), (2.6, 2.04), (math.pi, 2.16))
    part_gap: float = .0026       # half-width of the bare centre parting, m
    anchor: tuple[float, float] = (2.30, 1.86)  # braid base: angle and polar angle
    braid_length: float = .175    # child space, m (excluding the tuft)
    braid_width: float = .024
    braid_pitch: float = .021     # length of one full three-strand crossing
    tuft: float = .026
    fibers_per_strand: int = 70


def _interpolate(table: Sequence[tuple[float, float]], value: float) -> float:
    for (a, pa), (b, pb) in zip(table, table[1:]):
        if a <= value <= b:
            t = (value - a) / (b - a)
            return mix(pa, pb, .5 - .5 * math.cos(math.pi * t))
    return table[-1][1]


def hairline(style: BraidStyle, angle: float) -> float:
    angle = abs(math.remainder(angle, math.tau))
    return _interpolate(style.hairline, angle) + .006 * math.sin(9 * angle + .7) + .004 * math.sin(23 * angle)


def scalp_point(head, angle: float, phi: float) -> tuple[Vector, Vector]:
    """Surface point and outward normal of the design head (`groom.surface` convention)."""
    z = 1.638 + .1735 * math.cos(phi)
    radial = Vector((math.sin(angle), -math.cos(angle), 0))
    center = Vector((0, .005, z))
    point, normal, _, _ = head.ray_cast(center + radial * .27, -radial, .28)
    if point is None:
        return center, radial
    if normal.dot(radial) < 0:
        normal.negate()
    return point, normal


def _part_distance(angle: float, phi: float) -> float:
    """Approximate distance on the scalp from the front-to-nape centre parting."""
    off_meridian = min(abs(angle), math.pi - abs(angle))
    return math.sin(phi) * off_meridian * .11


def undercoat(c: ChildCharacter, head, style: BraidStyle) -> None:
    dark = c.mat('Scalp beneath the fibers', tuple(v * .8 for v in style.root), rough=.9)
    meridians, rows = 96, 26
    verts = [(0, .005, 1.8132)]  # crown of the design head plus the root lift
    for row in range(1, rows + 1):
        for col in range(meridians):
            angle = math.tau * col / meridians
            point, normal = scalp_point(head, angle, hairline(style, angle) * row / rows)
            verts.append(tuple(point + normal * .0011))
    faces = [(0, 1 + i, 1 + (i + 1) % meridians) for i in range(meridians)]
    for index in range(rows - 1):
        start = 1 + index * meridians
        for i in range(meridians):
            j = (i + 1) % meridians
            faces.append((start + i, start + i + meridians, start + j + meridians, start + j))
    c.mesh('Scalp undercoat', verts, faces, dark, 'head')


def combed_scalp(c: ChildCharacter, head, style: BraidStyle, rand: random.Random,
                 fibers: FiberGroup) -> None:
    """Fibres from a centre parting, combed back over the ears to each braid base."""
    made = 0
    while made < style.scalp_fibers:
        angle = rand.uniform(-math.pi, math.pi)
        edge = hairline(style, angle)
        phi = mix(.05, edge * .985, rand.random() ** .6)
        if _part_distance(angle, phi) < style.part_gap * rand.uniform(.8, 1.3):
            continue
        side = 1 if angle > 0 else -1
        target_angle = side * style.anchor[0] + rand.gauss(0, .07)
        target_phi = style.anchor[1] + max(-.09, min(.09, (phi - style.anchor[1]) * .07)) + rand.gauss(0, .025)
        flyaway = rand.random() < .07
        path = []
        for i in range(10):
            t = i / 9
            # Rise over the ear first, then drop behind it to the braid base.
            theta = mix(angle, target_angle, t ** 1.15)
            pitch = mix(phi, target_phi, t ** 2.3)
            pitch = min(pitch, hairline(style, theta) + .03) if t < .9 else pitch
            point, normal = scalp_point(head, theta, pitch)
            # Soft volume over the crown and ears, settling again at the braid base.
            lift = (.0009 + .0058 * t ** 1.5 * (1 - .35 * t ** 6) + .0018 * math.sin(math.pi * t)
                    + (rand.uniform(.001, .004) * math.sin(math.pi * t) if flyaway else 0))
            path.append(point + normal * lift)
        shade = rand.choice((0, 1, 1, 2, 2, 2, 3, 3, 4, 5))
        fibers.add(path, rand.uniform(.00011, .00024) * (1.1 if flyaway else 1), shade, min(6, shade + 1))
        made += 1
    # Short baby hairs along the front hairline.
    for _ in range(260):
        angle = rand.uniform(-1.35, 1.35)
        if abs(angle) < .05:
            continue
        edge = hairline(style, angle)
        path = []
        length = rand.uniform(.05, .13)
        for i in range(5):
            t = i / 4
            point, normal = scalp_point(head, angle + math.copysign(.12 * t, angle), edge - .02 - length * (1 - t))
            path.append(point + normal * (.0005 + .0016 * math.sin(math.pi * t)))
        fibers.add(path, rand.uniform(.00006, .00011), rand.randrange(2, 6), 6)


def _catmull(points: Sequence[Vector], t: float) -> Vector:
    count = len(points) - 1
    segment = min(int(t * count), count - 1)
    u = t * count - segment
    p0 = points[max(segment - 1, 0)]
    p1, p2 = points[segment], points[segment + 1]
    p3 = points[min(segment + 2, count)]
    return .5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u
                 + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)


def braid(c: ChildCharacter, base: Vector, side: int, style: BraidStyle, rand: random.Random,
          fibers: FiberGroup, ties: list[tuple[Vector, Vector, float]]) -> None:
    """A three-strand plait hanging from `base` (child space), ending in a tied tuft."""
    length = style.braid_length
    controls = [base,
                base + Vector((side * .004, .010, -.030)),
                base + Vector((side * .012, .026, -.085)),
                base + Vector((side * .020, .030, -length))]
    stations = 90
    centers = [_catmull(controls, i / (stations - 1)) for i in range(stations)]
    frames = []
    for i, point in enumerate(centers):
        tangent = (centers[min(i + 1, stations - 1)] - centers[max(i - 1, 0)]).normalized()
        lateral = Vector((0, 1, 0)).cross(tangent).normalized()
        depth = tangent.cross(lateral).normalized()
        frames.append((point, tangent, lateral, depth))
    seeds = [[(math.sqrt(rand.random()), rand.uniform(0, math.tau), rand.uniform(.85, 1.08))
              for _ in range(style.fibers_per_strand)] for _ in range(3)]
    for strand in range(3):
        phase = math.tau * strand / 3
        for radius_scale, polar, stretch in seeds[strand]:
            path = []
            for i, (point, tangent, lateral, depth) in enumerate(frames):
                s = i / (stations - 1)
                # Strands converge at the hair tie and gather at the base.
                plait = smoothstep(0, .12, s) * (1 - smoothstep(.86, 1, s))
                width = style.braid_width * (1 - .3 * s)
                angle = math.tau * s * length / style.braid_pitch + phase
                centre = (lateral * math.sin(angle) * width * .34 * plait
                          + depth * math.sin(2 * angle) * width * .12 * plait)
                r = width * .26 * (1 - .45 * (1 - plait))
                twist = polar + 3.0 * s
                offset = (lateral * math.cos(twist) + depth * math.sin(twist)) * r * radius_scale
                path.append(point + centre + offset)
            # Tuft below the tie, splaying slightly.
            end, tangent, lateral, depth = frames[-1]
            spread = (lateral * math.cos(polar) + depth * math.sin(polar)) * radius_scale
            tuft = style.tuft * stretch
            for k in range(1, 5):
                t = k / 4
                path.append(end + tangent * tuft * t + spread * (style.braid_width * (.12 + .3 * t)))
            shade = rand.choice((0, 1, 1, 2, 2, 3, 3, 4, 5))
            fibers.add(path, rand.uniform(.00012, .00022), shade, min(6, shade + 1))
    point, tangent, _, _ = frames[-1]
    ties.append((point - tangent * .002, tangent, style.braid_width * .2))
    point, tangent, _, _ = frames[4]
    ties.append((point, tangent, style.braid_width * .32))


def thread_wraps(c: ChildCharacter, ties: Sequence[tuple[Vector, Vector, float]], material) -> None:
    for index, (center, tangent, radius) in enumerate(ties):
        lateral = Vector((0, 1, 0)).cross(tangent).normalized()
        depth = tangent.cross(lateral).normalized()
        for turn in range(3):
            offset = tangent * (turn - 1) * .0016
            ring = [center + offset + (lateral * math.cos(a) + depth * math.sin(a)) * (radius + .0012)
                    for a in (math.tau * j / 20 for j in range(20))]
            c.tube(f'Braid tie {index + 1}.{turn + 1}', [tuple(p) for p in ring], .0009, material, 'head',
                   cyclic=True)


def child_eyebrows(c: ChildCharacter, fibers: FiberGroup, rand: random.Random, count: int = 380) -> None:
    """Fine, soft brows along `ChildCharacter.brow_point`.

    Hairs grow upward at the inner end and turn to lie outward along the arch,
    and the band thins toward the tail, as on a young child.
    """
    for sign in (1, -1):
        for _ in range(count):
            t = rand.random() ** 1.15
            x, z = c.brow_point(sign, t)
            z += rand.uniform(-.0036, .0030) * (1 - .45 * t)
            angle = mix(1.2, -.22, smoothstep(0, .45, t)) + rand.gauss(0, .13)
            length = mix(.0034, .0052, t) * rand.uniform(.75, 1.15)
            path = []
            for i in range(4):
                s = i / 3
                hair_x = x + sign * math.cos(angle) * length * s
                hair_z = z + math.sin(angle) * length * s - .0005 * s * s
                lift = .00045 + .0010 * math.sin(math.pi * s * .8)
                path.append(Vector((hair_x, c.face_y(hair_x, hair_z) - lift, hair_z)))
            shade = rand.randrange(0, 4)
            fibers.add(path, rand.uniform(.00012, .0002), shade, min(shade + 2, 6))


def braided_groom(c: ChildCharacter, style: BraidStyle, tie_material) -> None:
    rand = random.Random(style.seed)
    head = c.design_head()
    fibers = FiberGroup(c, style.root, style.highlight)
    undercoat(c, head, style)
    combed_scalp(c, head, style, rand, fibers)
    fibers.make_mesh('Scalp groom fibers')
    ties: list[tuple[Vector, Vector, float]] = []
    with c.native_space():
        for side in (1, -1):
            point, normal = scalp_point(head, side * style.anchor[0], style.anchor[1])
            base = c.child_point(tuple(point + normal * .006))
            braid(c, base, side, style, rand, fibers, ties)
        fibers.make_mesh('Braid fibers')
        thread_wraps(c, ties, tie_material)
    child_eyebrows(c, fibers, rand)
    fibers.make_mesh('Facial groom fibers')
