"""Modular architecture kit for the Chapter 1 sets.

Every piece is generated from code: lathed pillars, swept mouldings, jali
screens, doors, roofs and furnishings. Pieces that repeat (pillars, brackets,
lamps, doors) share one mesh datablock, so a large palace stays small on disk.

The vocabulary is early Indian stone architecture: square-octagon-round
pillars with pot-and-foliage capitals and rolled brackets, moulded plinths,
sloping chhajja eaves, barrel (shala) roofs with gavaksha gable windows,
stepped (phamsana) pavilion roofs, corbelled lotus ceilings and jali screens.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import random
from typing import Callable, Iterable, Sequence

import bmesh
import bpy
from mathutils import Matrix, Vector


Vec2 = tuple[float, float]
Vec3 = tuple[float, float, float]
Modulation = Callable[[float], float]

RING = 64
"""Vertices per lathe ring. Divisible by 4, 8 and 16 so polygon corners land on vertices."""


# ---------------------------------------------------------------------------
# Mesh builder
# ---------------------------------------------------------------------------

@dataclass
class MeshBuilder:
    verts: list[Vector] = field(default_factory=list)
    faces: list[tuple[int, ...]] = field(default_factory=list)
    mats: list[int] = field(default_factory=list)
    smooth: list[bool] = field(default_factory=list)

    def vert(self, co: Iterable[float]) -> int:
        self.verts.append(Vector(tuple(co)))
        return len(self.verts) - 1

    def face(self, indices: Sequence[int], mat: int = 0, smooth: bool = False) -> None:
        if len(set(indices)) >= 3:
            self.faces.append(tuple(indices))
            self.mats.append(mat)
            self.smooth.append(smooth)

    def bridge(self, a: Sequence[int], b: Sequence[int], mat: int = 0,
               smooth: bool = False, closed: bool = True) -> None:
        count = len(a)
        last = count if closed else count - 1
        for i in range(last):
            j = (i + 1) % count
            self.face((a[i], a[j], b[j], b[i]), mat, smooth)

    def merge(self, other: 'MeshBuilder', matrix: Matrix | None = None, mat_offset: int = 0) -> None:
        start = len(self.verts)
        for co in other.verts:
            self.verts.append(matrix @ co if matrix is not None else co.copy())
        for face, mat, smooth in zip(other.faces, other.mats, other.smooth):
            self.faces.append(tuple(start + i for i in face))
            self.mats.append(mat + mat_offset)
            self.smooth.append(smooth)

    def transform(self, matrix: Matrix) -> 'MeshBuilder':
        self.verts = [matrix @ co for co in self.verts]
        return self

    # -- primitives -------------------------------------------------------

    def box(self, center: Vec3, size: Vec3, mat: int | dict[str, int] = 0) -> None:
        cx, cy, cz = center
        hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
        idx = [self.vert((cx + sx * hx, cy + sy * hy, cz + sz * hz))
               for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)]

        def m(key: str) -> int:
            return mat.get(key, mat.get('*', 0)) if isinstance(mat, dict) else mat

        self.face((idx[0], idx[2], idx[3], idx[1]), m('-z'))
        self.face((idx[4], idx[5], idx[7], idx[6]), m('+z'))
        self.face((idx[0], idx[1], idx[5], idx[4]), m('-y'))
        self.face((idx[2], idx[6], idx[7], idx[3]), m('+y'))
        self.face((idx[0], idx[4], idx[6], idx[2]), m('-x'))
        self.face((idx[1], idx[3], idx[7], idx[5]), m('+x'))

    def box_between(self, lo: Vec3, hi: Vec3, mat: int | dict[str, int] = 0) -> None:
        center = tuple((a + b) / 2 for a, b in zip(lo, hi))
        size = tuple(abs(b - a) for a, b in zip(lo, hi))
        if min(size) > 1e-5:
            self.box(center, size, mat)

    def lathe(self, sections: Sequence['Section'], ring: int = RING, mat: int = 0,
              smooth: bool = True, cap_bottom: bool = True, cap_top: bool = True,
              origin: Vec3 = (0.0, 0.0, 0.0)) -> None:
        ox, oy, oz = origin
        rings: list[list[int]] = []
        for section in sections:
            loop = []
            for i in range(ring):
                theta = 2 * math.pi * i / ring
                r = section.radius(theta)
                loop.append(self.vert((ox + r * math.cos(theta), oy + r * math.sin(theta), oz + section.z)))
            rings.append(loop)
        for a, b in zip(rings, rings[1:]):
            self.bridge(a, b, mat, smooth)
        if cap_bottom:
            self.face(tuple(reversed(rings[0])), mat)
        if cap_top:
            self.face(tuple(rings[-1]), mat)

    def prism(self, polygon: Sequence[Vec2], length: float, mat: int = 0, smooth: bool = False) -> None:
        """Extrude a polygon drawn in the (y, z) plane along +X from 0 to `length`."""
        a = [self.vert((0.0, y, z)) for y, z in polygon]
        b = [self.vert((length, y, z)) for y, z in polygon]
        self.bridge(a, b, mat, smooth)
        self.face(tuple(reversed(a)), mat)
        self.face(tuple(b), mat)

    def loft(self, loops: Sequence[Sequence[Vec3]], mat: int = 0, smooth: bool = True,
             closed: bool = True, caps: bool = True) -> None:
        rings = [[self.vert(co) for co in loop] for loop in loops]
        for a, b in zip(rings, rings[1:]):
            self.bridge(a, b, mat, smooth, closed)
        if caps and closed:
            self.face(tuple(reversed(rings[0])), mat)
            self.face(tuple(rings[-1]), mat)

    def sweep(self, path: Sequence[Vec2], profile: Sequence[Vec2], mat: int = 0,
              closed_path: bool = True, z0: float = 0.0, smooth: bool = False) -> None:
        """Sweep a closed (out, z) profile along a plan path drawn counter-clockwise.

        `out` pushes away from the path to the right of travel, which is outward
        for a counter-clockwise loop. Corners are mitred.
        """
        count = len(path)
        normals: list[Vector] = []
        edges = count if closed_path else count - 1
        for i in range(edges):
            a, b = Vector(path[i]), Vector(path[(i + 1) % count])
            d = (b - a).normalized()
            normals.append(Vector((d.y, -d.x)))
        loops: list[list[int]] = []
        for i in range(count):
            if closed_path:
                n1, n2 = normals[i - 1], normals[i]
            else:
                n1 = normals[max(i - 1, 0)]
                n2 = normals[min(i, edges - 1)]
            miter = (n1 + n2)
            miter = miter / (1.0 + n1.dot(n2)) if (1.0 + n1.dot(n2)) > 1e-6 else n1
            px, py = path[i]
            loops.append([self.vert((px + miter.x * out, py + miter.y * out, z0 + z)) for out, z in profile])
        pairs = count if closed_path else count - 1
        for i in range(pairs):
            self.bridge(loops[i], loops[(i + 1) % count], mat, smooth)
        if not closed_path:
            self.face(tuple(reversed(loops[0])), mat)
            self.face(tuple(loops[-1]), mat)

    def grid_surface(self, rows: int, cols: int, point: Callable[[float, float], Vec3],
                     mat: int = 0, smooth: bool = True) -> None:
        grid = [[self.vert(point(r / rows, c / cols)) for c in range(cols + 1)] for r in range(rows + 1)]
        for r in range(rows):
            for c in range(cols):
                self.face((grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c]), mat, smooth)

    def torus(self, center: Vec3, major: float, minor: float, segments: int = 24, sides: int = 8,
              mat: int = 0, axis: str = 'Z') -> None:
        loops = []
        for i in range(segments):
            a = 2 * math.pi * i / segments
            loop = []
            for j in range(sides):
                b = 2 * math.pi * j / sides
                r = major + minor * math.cos(b)
                local = Vector((r * math.cos(a), r * math.sin(a), minor * math.sin(b)))
                if axis == 'Y':
                    local = Vector((local.x, local.z, local.y))
                elif axis == 'X':
                    local = Vector((local.z, local.y, local.x))
                loop.append(self.vert(Vector(center) + local))
            loops.append(loop)
        for i in range(segments):
            self.bridge(loops[i], loops[(i + 1) % segments], mat, True)

    def sphere(self, center: Vec3, radius: Vec3 | float, segments: int = 12, rings: int = 8,
               mat: int = 0) -> None:
        rx, ry, rz = (radius, radius, radius) if isinstance(radius, (int, float)) else radius
        sections = []
        for r in range(1, rings):
            phi = math.pi * r / rings
            sections.append(Section(-math.cos(phi) * rz, math.sin(phi)))
        cx, cy, cz = center
        bottom = self.vert((cx, cy, cz - rz))
        top = self.vert((cx, cy, cz + rz))
        loops = []
        for s in sections:
            loops.append([self.vert((cx + rx * s.a * math.cos(2 * math.pi * i / segments),
                                     cy + ry * s.a * math.sin(2 * math.pi * i / segments), cz + s.z))
                          for i in range(segments)])
        for a, b in zip(loops, loops[1:]):
            self.bridge(a, b, mat, True)
        for i in range(segments):
            j = (i + 1) % segments
            self.face((bottom, loops[0][j], loops[0][i]), mat, True)
            self.face((top, loops[-1][i], loops[-1][j]), mat, True)

    # -- output ------------------------------------------------------------

    def mesh(self, name: str, materials: Sequence[bpy.types.Material],
             sharp_angle: float = 38.0) -> bpy.types.Mesh:
        data = bpy.data.meshes.new(name)
        data.from_pydata([tuple(v) for v in self.verts], [], self.faces)
        data.update(calc_edges=True)
        for material in materials:
            data.materials.append(material)
        if self.mats:
            data.polygons.foreach_set('material_index', self.mats)
            data.polygons.foreach_set('use_smooth', self.smooth)
        if any(self.smooth):
            data.set_sharp_from_angle(angle=math.radians(sharp_angle))
        data.validate(clean_customdata=False)
        return data


@dataclass(frozen=True)
class Section:
    """One lathe ring: height, apothem, polygon sides (0 = round) and an optional modulation."""

    z: float
    a: float
    sides: int = 0
    mod: Modulation | None = None
    phase: float = 0.0

    def radius(self, theta: float) -> float:
        r = self.a
        if self.sides:
            step = 2 * math.pi / self.sides
            local = ((theta - self.phase + step / 2) % step) - step / 2
            r = self.a / math.cos(local)
        if self.mod is not None:
            r *= self.mod(theta)
        return r


def flutes(count: int, depth: float) -> Modulation:
    return lambda theta: 1.0 - depth * abs(math.sin(count * theta / 2))


def petals(count: int, depth: float, sharp: float = 1.0) -> Modulation:
    return lambda theta: 1.0 - depth + depth * abs(math.cos(count * theta / 2)) ** sharp


def profile_rings(points: Sequence[tuple[float, float]], sides: int = 0,
                  mod: Modulation | None = None, scale: float = 1.0, z0: float = 0.0) -> list[Section]:
    return [Section(z0 + z * scale, a * scale, sides, mod) for z, a in points]


def arc_rings(z0: float, z1: float, a0: float, bulge: float, steps: int = 6, sides: int = 0,
              mod: Modulation | None = None) -> list[Section]:
    """A rounded moulding (torus-like in elevation) between two heights."""
    rings = []
    for i in range(steps + 1):
        t = i / steps
        rings.append(Section(z0 + (z1 - z0) * t, a0 + bulge * math.sin(math.pi * t), sides, mod))
    return rings


# ---------------------------------------------------------------------------
# Object placement and caching
# ---------------------------------------------------------------------------

class Kit:
    """Creates objects from cached meshes so repeated pieces share data."""

    def __init__(self, root: bpy.types.Collection, parent: bpy.types.Object | None = None) -> None:
        self.root = root
        self.parent = parent
        self.cache: dict[str, bpy.types.Mesh] = {}
        self.collections: dict[str, bpy.types.Collection] = {}

    def collection(self, name: str) -> bpy.types.Collection:
        if name not in self.collections:
            coll = bpy.data.collections.new(name)
            self.root.children.link(coll)
            self.collections[name] = coll
        return self.collections[name]

    def mesh(self, key: str, make: Callable[[], bpy.types.Mesh]) -> bpy.types.Mesh:
        if key not in self.cache:
            self.cache[key] = make()
        return self.cache[key]

    def place(self, name: str, data: bpy.types.Mesh, collection: str,
              location: Vec3 = (0.0, 0.0, 0.0), yaw: float = 0.0,
              scale: Vec3 | None = None, rotation: Vec3 | None = None) -> bpy.types.Object:
        obj = bpy.data.objects.new(name, data)
        self.collection(collection).objects.link(obj)
        obj.location = location
        obj.rotation_euler = rotation if rotation is not None else (0.0, 0.0, math.radians(yaw))
        if scale is not None:
            obj.scale = scale
        if self.parent is not None:
            obj.parent = self.parent
        return obj

    def empty(self, name: str, collection: str, location: Vec3, yaw: float = 0.0,
              display: str = 'PLAIN_AXES', size: float = 0.5) -> bpy.types.Object:
        obj = bpy.data.objects.new(name, None)
        obj.empty_display_type = display
        obj.empty_display_size = size
        self.collection(collection).objects.link(obj)
        obj.location = location
        obj.rotation_euler.z = math.radians(yaw)
        if self.parent is not None:
            obj.parent = self.parent
        return obj


def build(builder: MeshBuilder, name: str, materials: Sequence[bpy.types.Material],
          sharp_angle: float = 38.0) -> bpy.types.Mesh:
    return builder.mesh(name, materials, sharp_angle)


# ---------------------------------------------------------------------------
# Pillars
# ---------------------------------------------------------------------------

def _bracket_profile(arm: float, height: float, rolls: int = 3) -> list[Vec2]:
    """Side view of a rolled (taranga) bracket arm: (u along arm, v up)."""
    core = arm - rolls * (height / (rolls + 0.4))
    step = height / (rolls + 0.4)
    right: list[Vec2] = [(core, 0.0)]
    u, v = core, 0.0
    for _ in range(rolls):
        for k in range(1, 7):
            angle = -math.pi / 2 + (math.pi / 2) * k / 6
            right.append((u + step * math.cos(angle), v + step + step * math.sin(angle)))
        u, v = u + step, v + step
    right.append((arm, height))
    left = [(-x, y) for x, y in reversed(right)]
    return right + left


def bracket_capital(builder: MeshBuilder, z: float, arm: float, height: float, width: float,
                    mat: int = 0, both: bool = True) -> None:
    profile = _bracket_profile(arm, height)
    piece = MeshBuilder()
    piece.prism([(u, v) for u, v in profile], width, mat)
    # The prism runs along +X (thickness) with the arm drawn along Y.
    centre = Matrix.Translation((-width / 2, 0, 0))
    lift = Matrix.Translation((0, 0, z))
    builder.merge(piece, lift @ Matrix.Rotation(math.radians(90), 4, 'Z') @ centre)
    if both:
        along_y = lift @ centre
        builder.merge(piece, along_y)


def _bell(builder: MeshBuilder, center: Vec3, size: float, mat: int) -> None:
    rings = [(0.0, 0.0), (0.0, 0.42), (0.18, 0.5), (0.55, 0.42), (0.85, 0.28), (1.0, 0.1), (1.12, 0.08)]
    sections = [Section(center[2] - size * z, size * a) for z, a in rings]
    sections.reverse()
    builder.lathe(sections, 10, mat, True, origin=(center[0], center[1], 0.0))


def _leaf(builder: MeshBuilder, angle: float, rim_r: float, rim_z: float, length: float,
          width: float, mat: int) -> None:
    ca, sa = math.cos(angle), math.sin(angle)

    def point(t: float, s: float) -> Vec3:
        across = (s - 0.5) * 2
        taper = (1 - t) ** 0.8 * (1 - 0.35 * t)
        r = rim_r + length * 0.42 * math.sin(math.pi * t * 0.85) + 0.012 * (1 - across ** 2)
        z = rim_z + 0.02 - length * t + length * 0.22 * t ** 3
        lateral = across * width / 2 * taper
        return (ca * r - sa * lateral, sa * r + ca * lateral, z)

    builder.grid_surface(6, 4, point, mat, True)


@dataclass(frozen=True)
class PillarStyle:
    height: float = 4.6
    scale: float = 1.0
    bells: bool = True
    bracket: bool = True
    bracket_both: bool = True


def stambha(style: PillarStyle) -> MeshBuilder:
    """Square base, octagonal and sixteen-sided shaft, fluted round neck,
    pot-and-foliage capital and a rolled cruciform bracket."""
    s = style.scale
    b = MeshBuilder()
    base_top = 0.62 * s
    capital = (0.60 + 0.12 + (0.44 if style.bracket else 0.0)) * s
    shaft = style.height - base_top - capital
    if shaft < 0.4:
        raise ValueError(f'Pillar too short for its capital: {style}')
    rings: list[Section] = []
    rings += profile_rings([(0.0, 0.42), (0.13, 0.42), (0.16, 0.39), (0.16, 0.36), (0.22, 0.36)], 4, scale=s)
    rings += arc_rings(0.22 * s, 0.40 * s, 0.32 * s, 0.05 * s, 6, 4)
    rings += profile_rings([(0.42, 0.31), (0.45, 0.30), (0.45, 0.34), (0.55, 0.34), (0.59, 0.31)], 4, scale=s)
    z = base_top
    sq = shaft * 0.30
    oc = shaft * 0.22
    sx = shaft * 0.22
    rd = shaft - sq - oc - sx
    rings += [Section(z, 0.31 * s, 4), Section(z + sq, 0.31 * s, 4)]
    z += sq
    rings += [Section(z + 0.08 * s, 0.30 * s, 8), Section(z + oc * 0.45, 0.30 * s, 8),
              Section(z + oc * 0.45, 0.325 * s, 8), Section(z + oc * 0.45 + 0.06 * s, 0.325 * s, 8),
              Section(z + oc * 0.45 + 0.06 * s, 0.30 * s, 8), Section(z + oc, 0.30 * s, 8)]
    z += oc
    rings += [Section(z + 0.06 * s, 0.285 * s, 16), Section(z + sx, 0.285 * s, 16)]
    bell_z = z + sx * 0.82
    z += sx
    rings += [Section(z, 0.31 * s), Section(z + 0.05 * s, 0.31 * s), Section(z + 0.05 * s, 0.27 * s, 0, flutes(24, 0.05)),
              Section(z + rd, 0.27 * s, 0, flutes(24, 0.05)), Section(z + rd, 0.29 * s),
              Section(z + rd + 0.04 * s, 0.29 * s), Section(z + rd + 0.04 * s, 0.25 * s)]
    z += rd + 0.04 * s
    pot = [(0.0, 0.25), (0.05, 0.29), (0.14, 0.34), (0.25, 0.36), (0.36, 0.34), (0.45, 0.28),
           (0.50, 0.23), (0.53, 0.23), (0.53, 0.31), (0.60, 0.31), (0.60, 0.29)]
    rings += [Section(z + pz * s, pa * s) for pz, pa in pot]
    rim_z = z + 0.53 * s
    z += 0.60 * s
    rings += [Section(z, 0.37 * s, 4), Section(z + 0.12 * s, 0.40 * s, 4)]
    b.lathe(rings, RING, 0, True)
    for i in range(8):
        _leaf(b, 2 * math.pi * i / 8 + math.pi / 8, 0.30 * s, rim_z, 0.24 * s, 0.13 * s, 0)
    if style.bells:
        for i in range(16):
            a = 2 * math.pi * (i + 0.5) / 16
            r = 0.30 * s
            b.sphere((r * math.cos(a), r * math.sin(a), bell_z + 0.03 * s), 0.018 * s, 6, 4)
            _bell(b, (0.305 * s * math.cos(a), 0.305 * s * math.sin(a), bell_z), 0.075 * s, 0)
        b.torus((0, 0, bell_z + 0.035 * s), 0.29 * s, 0.012 * s, 48, 6)
    if style.bracket:
        bracket_capital(b, z + 0.12 * s, 0.78 * s, 0.44 * s, 0.40 * s, 0, style.bracket_both)
    return b


def slender_pillar(height: float, radius: float = 0.08) -> MeshBuilder:
    b = MeshBuilder()
    r = radius
    rings = profile_rings([(0.0, 1.6), (0.08, 1.6), (0.1, 1.3), (0.16, 1.3)], 4, scale=1.0)
    rings = [Section(x.z * r * 10 / 1.6, x.a * r, 4) for x in rings]
    top = height
    rings += [Section(0.16 * r * 10 / 1.6 + 0.02, r * 1.0, 8), Section(top * 0.35, r, 8),
              Section(top * 0.35 + 0.02, r * 1.15), Section(top * 0.37, r * 1.15),
              Section(top * 0.37, r * 0.92, 0, flutes(12, 0.08)), Section(top * 0.82, r * 0.92, 0, flutes(12, 0.08)),
              Section(top * 0.84, r * 1.25), Section(top * 0.88, r * 1.45), Section(top * 0.92, r * 1.2),
              Section(top * 0.95, r * 1.6, 4), Section(top, r * 1.6, 4)]
    b.lathe(rings, 32, 0, True)
    return b


# ---------------------------------------------------------------------------
# Beams, ceilings and mouldings
# ---------------------------------------------------------------------------

BEAM_PROFILE: list[Vec2] = [(-0.22, 0.0), (0.22, 0.0), (0.22, 0.18), (0.25, 0.18), (0.25, 0.34),
                            (0.28, 0.34), (0.28, 0.56), (-0.28, 0.56), (-0.28, 0.34), (-0.25, 0.34),
                            (-0.25, 0.18), (-0.22, 0.18)]
BEAM_HEIGHT = 0.56


def beam(length: float, dentils: bool = True) -> MeshBuilder:
    """Moulded stone architrave along +X, centred on Y, bottom at Z = 0."""
    b = MeshBuilder()
    b.prism(BEAM_PROFILE, length)
    if dentils:
        count = max(2, int(length / 0.2))
        pitch = length / count
        for i in range(count):
            x = (i + 0.5) * pitch
            for side in (-1, 1):
                b.box((x, side * 0.30, 0.45), (pitch * 0.55, 0.05, 0.1))
    return b


def plinth_profile(height: float, projection: float = 0.45) -> list[Vec2]:
    """Adhishthana mouldings: base course, rounded kumuda, recessed neck, kapota cornice."""
    h = height
    p = projection
    pts: list[Vec2] = [(-0.3, 0.0), (p, 0.0), (p, h * 0.16), (p * 0.82, h * 0.16), (p * 0.82, h * 0.24)]
    for i in range(7):
        t = i / 6
        pts.append((p * 0.62 + p * 0.28 * math.sin(math.pi * t), h * (0.26 + 0.24 * t)))
    pts += [(p * 0.55, h * 0.52), (p * 0.38, h * 0.55), (p * 0.38, h * 0.66), (p * 0.5, h * 0.66),
            (p * 0.5, h * 0.70), (p * 0.38, h * 0.70), (p * 0.40, h * 0.74)]
    for i in range(5):
        t = i / 4
        pts.append((p * 0.42 + p * 0.38 * math.sin(math.pi / 2 * t), h * (0.76 + 0.14 * t)))
    pts += [(p * 0.80, h * 0.94), (p * 0.62, h * 0.94), (p * 0.62, h), (-0.3, h)]
    return pts


def chhajja_profile(depth: float = 1.0, drop: float = 0.34, thick: float = 0.12) -> list[Vec2]:
    """Sloping stone eave: (out, z) with z = 0 at the wall junction top."""
    return [(-0.15, 0.0), (0.0, 0.04), (depth, -drop), (depth + 0.02, -drop - 0.02),
            (depth + 0.02, -drop - thick - 0.04), (depth - 0.06, -drop - thick - 0.04),
            (0.0, -thick - 0.1), (-0.15, -thick - 0.1)]


def cornice_profile(depth: float = 0.32, height: float = 0.36) -> list[Vec2]:
    return [(-0.1, 0.0), (depth * 0.4, 0.0), (depth * 0.4, height * 0.25), (depth * 0.7, height * 0.3),
            (depth, height * 0.55), (depth, height * 0.75), (depth * 0.6, height * 0.75),
            (depth * 0.6, height), (-0.1, height)]


def parapet_profile(height: float = 0.95, thick: float = 0.34) -> list[Vec2]:
    t = thick
    return [(-t, 0.0), (0.0, 0.0), (0.0, height - 0.16), (0.06, height - 0.12),
            (0.06, height), (-t - 0.06, height), (-t - 0.06, height - 0.12), (-t, height - 0.16)]


def rect_path(x0: float, x1: float, y0: float, y1: float) -> list[Vec2]:
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def lotus_rosette(radius: float, depth: float = 0.08) -> MeshBuilder:
    b = MeshBuilder()
    rings = [Section(0.0, radius, 0, petals(16, 0.18, 2.0)), Section(-depth * 0.3, radius * 0.85, 0, petals(16, 0.2)),
             Section(-depth * 0.5, radius * 0.6, 0, petals(8, 0.3)), Section(-depth * 0.8, radius * 0.4, 0, petals(8, 0.3)),
             Section(-depth, radius * 0.18), Section(-depth * 1.1, radius * 0.05)]
    b.lathe(rings, RING, 0, True, cap_bottom=False, cap_top=True)
    return b


def lotus_vitana(radius: float, rise: float, courses: int = 6) -> MeshBuilder:
    """Corbelled lotus ceiling seen from below. Z = 0 is the ceiling plane, it rises upward."""
    b = MeshBuilder()
    rings: list[Section] = []
    z = 0.0
    r = radius
    band = rise / (courses + 1.5)
    for i in range(courses):
        sides = 8 if i < 2 else 0
        mod = petals(16 + 8 * (i % 2), 0.10) if i in (2, 4) else None
        rings += [Section(z, r, sides, mod), Section(z + band * 0.7, r, sides, mod)]
        r_next = r * 0.80
        rings += [Section(z + band * 0.7, r_next, sides), Section(z + band, r_next, sides)]
        z += band
        r = r_next
    rings += [Section(z, r * 0.6, 0, petals(16, 0.25)), Section(z + band * 0.6, r * 0.25), Section(z + band * 0.7, 0.01)]
    b.lathe(rings, RING, 0, True, cap_bottom=False, cap_top=True)
    # Hanging lotus pendant.
    pendant = [(0.0, 0.0), (-0.05, 0.10), (-0.18, 0.28), (-0.35, 0.34), (-0.5, 0.26), (-0.62, 0.30),
               (-0.78, 0.22), (-0.92, 0.10), (-1.0, 0.02)]
    sections = [Section(z + band * 0.7 + pz * rise * 0.55, pa * radius * 0.42, 0, petals(16, 0.18))
                for pz, pa in pendant]
    b.lathe(sections, RING, 1, True, cap_bottom=False, cap_top=True)
    return b


# ---------------------------------------------------------------------------
# Walls, openings, doors and screens
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Opening:
    center: float
    width: float
    sill: float
    head: float
    kind: str = 'door'  # 'door', 'window', 'arch', 'jali'


def wall(builder: MeshBuilder, start: Vec2, end: Vec2, z0: float, height: float, thick: float,
         openings: Sequence[Opening] = (), inside: int = 1, mat_out: int = 0, mat_in: int = 1) -> None:
    """Axis-aligned wall from `start` to `end`. `inside` (+1 or -1) is the side,
    relative to the left normal of travel, that receives the plaster material."""
    sx, sy = start
    ex, ey = end
    along_x = abs(ey - sy) < 1e-6
    length = abs(ex - sx) if along_x else abs(ey - sy)
    direction = 1 if (ex - sx if along_x else ey - sy) > 0 else -1
    # Left normal of travel.
    nx, ny = (0.0, float(direction)) if along_x else (-float(direction), 0.0)
    inside_key = ('+y' if ny * inside > 0 else '-y') if along_x else ('+x' if nx * inside > 0 else '-x')
    outside_key = inside_key.replace('+', '#').replace('-', '+').replace('#', '-')
    mats = {'*': mat_out, inside_key: mat_in, outside_key: mat_out}

    def piece(a: float, b: float, z_lo: float, z_hi: float) -> None:
        if b - a < 1e-4 or z_hi - z_lo < 1e-4:
            return
        if along_x:
            x_lo = sx + direction * a
            x_hi = sx + direction * b
            builder.box_between((min(x_lo, x_hi), sy - thick / 2, z_lo), (max(x_lo, x_hi), sy + thick / 2, z_hi), mats)
        else:
            y_lo = sy + direction * a
            y_hi = sy + direction * b
            builder.box_between((sx - thick / 2, min(y_lo, y_hi), z_lo), (sx + thick / 2, max(y_lo, y_hi), z_hi), mats)

    cursor = 0.0
    for opening in sorted(openings, key=lambda o: o.center):
        left = opening.center - opening.width / 2
        right = opening.center + opening.width / 2
        piece(cursor, left, z0, z0 + height)
        piece(left, right, z0, z0 + opening.sill)
        piece(left, right, z0 + opening.head, z0 + height)
        cursor = right
    piece(cursor, length, z0, z0 + height)


def door_frame(width: float, head: float, depth: float, bands: int = 3) -> MeshBuilder:
    """Stepped jamb bands (shakhas) around an opening on the XZ plane, centred on X = 0.

    The frame sits on Y = 0 and projects toward -Y by `depth` per band.
    """
    b = MeshBuilder()
    band_w = 0.11
    for i in range(bands):
        inner = width / 2 + i * band_w
        outer = inner + band_w
        proud = depth * (bands - i)
        mat = i % 2
        b.box_between((-outer, -proud, 0.0), (-inner, 0.0, head + i * band_w + band_w), mat)
        b.box_between((inner, -proud, 0.0), (outer, 0.0, head + i * band_w + band_w), mat)
        b.box_between((-outer, -proud, head + i * band_w), (outer, 0.0, head + (i + 1) * band_w), mat)
    top = head + bands * band_w
    b.box_between((-width / 2 - bands * band_w - 0.12, -depth * bands - 0.08, top),
                  (width / 2 + bands * band_w + 0.12, 0.0, top + 0.16), 0)
    b.box_between((-0.16, -depth * bands - 0.04, head), (0.16, -depth * bands + 0.02, head + bands * band_w), 1)
    b.box_between((-width / 2 - bands * band_w, -depth * bands - 0.04, -0.02),
                  (width / 2 + bands * band_w, 0.02, 0.1), 0)
    return b


def moonstone(radius: float) -> MeshBuilder:
    """Half-round threshold stone (chandrashila) with concentric ridges, flat side on +Y."""
    b = MeshBuilder()
    steps = 24
    ridges = [(1.0, 0.0), (1.0, 0.06), (0.86, 0.06), (0.86, 0.09), (0.7, 0.09), (0.7, 0.07),
              (0.55, 0.07), (0.55, 0.11), (0.3, 0.11), (0.3, 0.12), (0.0, 0.12)]
    loops = []
    for r, z in ridges:
        loops.append([(radius * max(r, 0.001) * math.cos(math.pi + math.pi * i / steps),
                       radius * max(r, 0.001) * math.sin(math.pi + math.pi * i / steps), z) for i in range(steps + 1)])
    b.loft(loops, 0, False, closed=False, caps=False)
    return b


def door_leaf(width: float, height: float, studs: bool = True) -> MeshBuilder:
    """Teak plank door leaf with hinge at X = 0, opening toward +X. Material 0 wood, 1 brass."""
    b = MeshBuilder()
    t = 0.07
    planks = max(3, int(width / 0.16))
    pitch = width / planks
    for i in range(planks):
        b.box_between((i * pitch + 0.004, -t / 2, 0.0), ((i + 1) * pitch - 0.004, t / 2, height), 0)
    for z in (height * 0.12, height * 0.5, height * 0.88):
        for side in (-1, 1):
            b.box((width / 2, side * (t / 2 + 0.018), z), (width - 0.06, 0.036, 0.13), 0)
    if studs:
        rows, cols = 7, max(2, int(width / 0.22))
        for r in range(rows):
            for c in range(cols):
                x = (c + 0.5) * width / cols
                z = height * (0.1 + 0.8 * r / (rows - 1))
                for side in (-1, 1):
                    b.sphere((x, side * (t / 2 + 0.005), z), (0.022, 0.016, 0.022), 8, 4, 1)
        b.torus((width - 0.16, -(t / 2 + 0.03), height * 0.48), 0.07, 0.011, 18, 6, 1, 'Y')
    return b


def jali(width: float, height: float, cell: float = 0.16, frame: float = 0.06,
         pattern: str = 'rosette') -> MeshBuilder:
    """Pierced stone screen in the XZ plane, bottom centre at the origin.

    Give the object a Solidify modifier for thickness.
    """
    b = MeshBuilder()
    cols = max(1, int((width - 2 * frame) / cell))
    rows = max(1, int((height - 2 * frame) / cell))
    cw = (width - 2 * frame) / cols
    ch = (height - 2 * frame) / rows
    x0 = -width / 2 + frame
    z0 = frame
    per_side = 4
    n = per_side * 4
    for r in range(rows):
        for c in range(cols):
            cx = x0 + (c + 0.5) * cw
            cz = z0 + (r + 0.5) * ch
            outer = []
            for k in range(n):
                side, step = divmod(k, per_side)
                t = step / per_side
                if side == 0:
                    p = (-0.5 + t, -0.5)
                elif side == 1:
                    p = (0.5, -0.5 + t)
                elif side == 2:
                    p = (0.5 - t, 0.5)
                else:
                    p = (-0.5, 0.5 - t)
                outer.append(b.vert((cx + p[0] * cw, 0.0, cz + p[1] * ch)))
            inner = []
            for k in range(n):
                side, step = divmod(k, per_side)
                t = step / per_side
                p = [(-0.5 + t, -0.5), (0.5, -0.5 + t), (0.5 - t, 0.5), (-0.5, 0.5 - t)][side]
                angle = math.atan2(p[1], p[0])
                if pattern == 'rosette':
                    radius = 0.36 * (0.78 + 0.22 * math.cos(8 * angle))
                elif pattern == 'star':
                    radius = 0.30 + 0.12 * abs(math.cos(2 * angle))
                else:
                    radius = 0.34
                inner.append(b.vert((cx + math.cos(angle) * radius * cw, 0.0, cz + math.sin(angle) * radius * ch)))
            for k in range(n):
                j = (k + 1) % n
                b.face((outer[k], outer[j], inner[j], inner[k]), 0)
    # Frame
    w2 = width / 2
    for lo, hi in (((-w2, 0.0), (w2, frame)), ((-w2, height - frame), (w2, height)),
                   ((-w2, frame), (-w2 + frame, height - frame)), ((w2 - frame, frame), (w2, height - frame))):
        a = b.vert((lo[0], 0.0, lo[1]))
        b2 = b.vert((hi[0], 0.0, lo[1]))
        c2 = b.vert((hi[0], 0.0, hi[1]))
        d = b.vert((lo[0], 0.0, hi[1]))
        b.face((a, b2, c2, d), 0)
    return b


def finish_jali(data: bpy.types.Mesh) -> bpy.types.Mesh:
    """Weld the cell grid so the solidified screen has clean shared edges."""
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bm.to_mesh(data)
    bm.free()
    return data


# ---------------------------------------------------------------------------
# Roofs and pavilions
# ---------------------------------------------------------------------------

def kalasha(height: float) -> MeshBuilder:
    b = MeshBuilder()
    pts = [(0.0, 0.18), (0.06, 0.2), (0.08, 0.14), (0.14, 0.22), (0.24, 0.34), (0.36, 0.38), (0.5, 0.33),
           (0.6, 0.22), (0.66, 0.13), (0.7, 0.16), (0.74, 0.1), (0.8, 0.12), (0.86, 0.07), (0.94, 0.06),
           (1.0, 0.01)]
    b.lathe([Section(z * height, a * height) for z, a in pts], 32, 0, True)
    return b


def amalaka(radius: float, height: float) -> MeshBuilder:
    b = MeshBuilder()
    rings = arc_rings(0.0, height, radius * 0.55, radius * 0.45, 8, 0, flutes(32, 0.12))
    b.lathe(rings, RING, 0, True)
    return b


def phamsana_roof(base: float, tiers: int = 4, tier_h: float = 0.42, finial: float = 1.2) -> MeshBuilder:
    """Stepped pyramidal pavilion roof built from diminishing eaved slabs."""
    b = MeshBuilder()
    z = 0.0
    size = base
    for i in range(tiers):
        half = size / 2
        b.sweep(rect_path(-half, half, -half, half), chhajja_profile(0.22 + 0.05 * (tiers - i), 0.12, 0.07),
                0, True, z + tier_h)
        b.box((0, 0, z + tier_h / 2), (size, size, tier_h))
        b.box((0, 0, z + tier_h + 0.06), (size * 0.86, size * 0.86, 0.12))
        z += tier_h + 0.12
        size *= 0.78
    bell = [(0.0, 0.48), (0.12, 0.5), (0.3, 0.44), (0.5, 0.3), (0.62, 0.2), (0.68, 0.2)]
    b.lathe([Section(z + bz * size * 1.6, ba * size * 1.4, 4 if i < 2 else 0) for i, (bz, ba) in enumerate(bell)],
            RING, 0, True)
    z += 0.68 * size * 1.6
    am = amalaka(size * 0.6, size * 0.35)
    b.merge(am, Matrix.Translation((0, 0, z)))
    z += size * 0.35
    b.merge(kalasha(finial), Matrix.Translation((0, 0, z)))
    return b


def shala_roof(length: float, width: float, rise: float, ribs: float = 0.75,
               finials: bool = True) -> MeshBuilder:
    """Barrel-vaulted roof along +X, centred, sitting on Z = 0.

    Material 0 stone/plaster, 1 the dark recess of each gable window.
    """
    b = MeshBuilder()
    steps = 20
    thick = 0.25
    outer: list[Vec2] = []
    inner: list[Vec2] = []
    for i in range(steps + 1):
        t = i / steps
        a = math.pi * t
        # Slightly pointed barrel: raise the crown.
        shape = math.sin(a) ** 0.85
        outer.append((-math.cos(a) * width / 2, rise * shape))
        inner.append((-math.cos(a) * (width / 2 - thick), (rise - thick) * shape))
    polygon = outer + list(reversed(inner))
    body = MeshBuilder()
    body.prism(polygon, length, 0, False)
    b.merge(body, Matrix.Translation((-length / 2, 0, 0)))
    rib_poly = [(u * 1.03, v + 0.06) for u, v in outer] + list(reversed(outer))
    count = max(2, int(length / ribs))
    for i in range(count + 1):
        x = -length / 2 + i * length / count
        rib = MeshBuilder()
        rib.prism(rib_poly, 0.12, 0)
        b.merge(rib, Matrix.Translation((x - 0.06, 0, 0)))
    # Gable ends: concentric horseshoe bands framing a dark recessed window.
    for end in (-1, 1):
        x = end * (length / 2 + 0.02)
        for k, scale in enumerate((1.0, 0.86, 0.72)):
            band_outer = [(u * scale, v * scale) for u, v in outer]
            band_inner = [(u * (scale - 0.08), v * (scale - 0.08)) for u, v in outer]
            loops = []
            for (uo, vo), (ui, vi) in zip(band_outer, band_inner):
                loops.append([(x + end * 0.05 * k, uo, vo), (x + end * (0.05 * k + 0.12), uo, vo),
                              (x + end * (0.05 * k + 0.12), ui, vi), (x + end * 0.05 * k, ui, vi)])
            b.loft(loops, 0, False, closed=True, caps=True)
        fill = [(u * 0.64, v * 0.64) for u, v in outer]
        verts = [b.vert((x - end * 0.15, u, v)) for u, v in fill]
        b.face(tuple(verts if end > 0 else list(reversed(verts))), 1)
        b.box((x - end * 0.08, 0.0, rise * 0.02), (0.1, width * 0.64, 0.06), 0)
    if finials:
        stupi = kalasha(0.55)
        count = max(2, int(length / 1.4))
        for i in range(count + 1):
            x = -length / 2 + i * length / count
            b.merge(stupi, Matrix.Translation((x, 0, rise + 0.04)))
    return b


# ---------------------------------------------------------------------------
# Torana gateway and free-standing pillar
# ---------------------------------------------------------------------------

def torana(span: float, height: float) -> MeshBuilder:
    """Triple-architrave gateway with volute ends, centred on X = 0, facing ±Y."""
    b = MeshBuilder()
    post = 0.62
    for side in (-1, 1):
        x = side * span / 2
        rings = profile_rings([(0.0, 0.46), (0.25, 0.46), (0.3, 0.40), (0.3, 0.31)], 4)
        rings += [Section(height * 0.62, post / 2, 4), Section(height * 0.62, post / 2 + 0.04, 4),
                  Section(height * 0.62 + 0.08, post / 2 + 0.04, 4)]
        rings += arc_rings(height * 0.62 + 0.08, height * 0.70, post / 2 - 0.02, 0.10, 6, 0, petals(16, 0.12))
        rings += [Section(height * 0.70, post / 2 + 0.06, 4), Section(height * 0.74, post / 2 + 0.06, 4)]
        rings += [Section(height * 0.74, post / 2, 4), Section(height, post / 2, 4)]
        b.lathe(rings, RING, 0, True, origin=(x, 0, 0))
    beam_h = 0.42
    beam_t = 0.40
    overhang = 1.1
    levels = (height * 0.74, height * 0.74 + 1.25, height * 0.74 + 2.5)
    half = span / 2 + overhang
    for li, z in enumerate(levels):
        sag = 0.18 + 0.04 * li
        loops = []
        steps = 24
        for i in range(steps + 1):
            u = -half + 2 * half * i / steps
            lift = sag * (u / half) ** 2
            loops.append([(u, -beam_t / 2, z + lift), (u, beam_t / 2, z + lift),
                          (u, beam_t / 2, z + lift + beam_h), (u, -beam_t / 2, z + lift + beam_h)])
        b.loft(loops, 0, False, closed=True, caps=True)
        for side in (-1, 1):
            cx = side * (half + 0.18)
            cz = z + sag + beam_h / 2
            rings = [Section(-beam_t / 2 - 0.02, 0.05), Section(-beam_t / 2 - 0.02, 0.32), Section(-beam_t / 2 + 0.04, 0.36),
                     Section(-beam_t / 2 + 0.04, 0.26), Section(-beam_t / 2 + 0.08, 0.24), Section(-beam_t / 2 + 0.08, 0.16),
                     Section(beam_t / 2 - 0.08, 0.16), Section(beam_t / 2 - 0.08, 0.24), Section(beam_t / 2 - 0.04, 0.26),
                     Section(beam_t / 2 - 0.04, 0.36), Section(beam_t / 2 + 0.02, 0.32), Section(beam_t / 2 + 0.02, 0.05)]
            disc = MeshBuilder()
            disc.lathe(rings, 32, 1, True)
            b.merge(disc, Matrix.Translation((cx, 0, cz)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
        if li < 2:
            for u in (-span / 2, -span / 6, span / 6, span / 2):
                lift = sag * (u / half) ** 2
                b.box((u, 0, z + lift + beam_h + 0.40), (0.42, beam_t * 0.9, 0.8), 1)
    top = levels[-1] + 0.18 + beam_h
    for u in (-span / 2, 0.0, span / 2):
        b.merge(kalasha(0.9), Matrix.Translation((u, 0, top)))
    return b


def victory_pillar(height: float) -> MeshBuilder:
    b = MeshBuilder()
    rings = profile_rings([(0.0, 1.1), (0.3, 1.1), (0.3, 0.95), (0.6, 0.95), (0.6, 0.8), (0.75, 0.8)], 4)
    rings += [Section(0.75, 0.42), Section(height * 0.86, 0.30)]
    cap = height * 0.86
    bell = [(0.0, 0.34), (0.05, 0.28), (0.25, 0.36), (0.55, 0.5), (0.8, 0.6), (0.9, 0.62), (0.95, 0.5)]
    rings += [Section(cap + z * 1.0, a, 0, petals(24, 0.12)) for z, a in bell]
    rings += [Section(cap + 1.0, 0.56), Section(cap + 1.0, 0.62), Section(cap + 1.3, 0.62), Section(cap + 1.3, 0.3)]
    b.lathe(rings, RING, 0, True)
    b.merge(kalasha(1.4), Matrix.Translation((0, 0, cap + 1.3)))
    return b


# ---------------------------------------------------------------------------
# Furnishings
# ---------------------------------------------------------------------------

def diya(scale: float = 1.0) -> MeshBuilder:
    """Clay oil lamp; material 0 clay, 1 flame."""
    b = MeshBuilder()
    rings = [Section(0.0, 0.025), Section(0.004, 0.035), Section(0.02, 0.045), Section(0.028, 0.05),
             Section(0.028, 0.043), Section(0.012, 0.03)]
    b.lathe([Section(s.z * scale, s.a * scale, 0, lambda t: 1 + 0.25 * max(0.0, math.cos(t)) ** 8) for s in rings],
            24, 0, True, cap_top=True)
    flame_rings = [Section(0.03, 0.002), Section(0.036, 0.007), Section(0.05, 0.009), Section(0.07, 0.004),
                   Section(0.085, 0.0005)]
    b.lathe([Section(s.z * scale, s.a * scale) for s in flame_rings], 10, 1, True,
            origin=(0.048 * scale, 0, 0))
    return b


def lamp_stand(height: float = 1.4) -> MeshBuilder:
    """Brass deepastambha with a dish of five wicks; material 0 brass, 1 flame."""
    b = MeshBuilder()
    pts = [(0.0, 0.16), (0.03, 0.17), (0.06, 0.12), (0.1, 0.05), (0.2, 0.03), (0.22, 0.05), (0.24, 0.03),
           (0.6, 0.022), (0.62, 0.04), (0.64, 0.022), (0.9, 0.02), (0.92, 0.04), (0.94, 0.02), (0.97, 0.02)]
    rings = [Section(z * height, a) for z, a in pts]
    rings += [Section(height * 0.97, 0.05), Section(height * 0.99, 0.13), Section(height, 0.15),
              Section(height, 0.13), Section(height * 0.985, 0.11)]
    b.lathe(rings, 32, 0, True)
    for i in range(5):
        a = 2 * math.pi * i / 5
        b.lathe([Section(height + 0.005, 0.002), Section(height + 0.02, 0.008), Section(height + 0.045, 0.007),
                 Section(height + 0.075, 0.0005)], 8, 1, True, origin=(0.115 * math.cos(a), 0.115 * math.sin(a), 0))
    b.merge(kalasha(0.18), Matrix.Translation((0, 0, height)))
    return b


def hanging_lamp(drop: float = 1.2) -> MeshBuilder:
    """Brass bowl lamp on chains hanging from Z = 0 down to -drop; 0 brass, 1 flame."""
    b = MeshBuilder()
    for i in range(3):
        a = 2 * math.pi * i / 3
        top = Vector((0, 0, 0))
        bottom = Vector((0.16 * math.cos(a), 0.16 * math.sin(a), -drop))
        links = int(drop / 0.05)
        for k in range(links):
            p = top.lerp(bottom, (k + 0.5) / links)
            b.torus(tuple(p), 0.014, 0.003, 8, 4, 0, 'X' if k % 2 else 'Y')
    bowl = [(0.0, 0.0), (-0.02, 0.06), (-0.06, 0.16), (-0.1, 0.2), (-0.11, 0.18), (-0.06, 0.14), (-0.03, 0.05)]
    b.lathe([Section(-drop + z, a) for z, a in reversed(bowl)], 32, 0, True)
    b.lathe([Section(-drop - 0.08, 0.02), Section(-drop - 0.12, 0.05), Section(-drop - 0.18, 0.0)], 16, 0, True)
    for i in range(4):
        a = 2 * math.pi * i / 4
        b.lathe([Section(-drop - 0.03, 0.002), Section(-drop - 0.015, 0.008), Section(-drop + 0.01, 0.007),
                 Section(-drop + 0.04, 0.0005)], 8, 1, True, origin=(0.17 * math.cos(a), 0.17 * math.sin(a), 0))
    return b


def matka(height: float = 0.42) -> MeshBuilder:
    b = MeshBuilder()
    pts = [(0.0, 0.12), (0.06, 0.28), (0.2, 0.46), (0.4, 0.52), (0.6, 0.48), (0.78, 0.34), (0.88, 0.22),
           (0.92, 0.2), (0.96, 0.24), (1.0, 0.25), (1.0, 0.21), (0.9, 0.18)]
    b.lathe([Section(z * height, a * height) for z, a in pts], 32, 0, True, cap_top=False)
    return b


def bolster(length: float, radius: float) -> MeshBuilder:
    """Cylindrical cushion along X with gathered ends; material 0 cloth, 1 trim."""
    b = MeshBuilder()
    rings = [Section(-length / 2, radius * 0.25), Section(-length / 2 + 0.01, radius * 0.75),
             Section(-length / 2 + 0.05, radius * 0.97), Section(length / 2 - 0.05, radius * 0.97),
             Section(length / 2 - 0.01, radius * 0.75), Section(length / 2, radius * 0.25)]
    piece = MeshBuilder()
    piece.lathe(rings, 32, 0, True)
    b.merge(piece, Matrix.Rotation(math.radians(90), 4, 'Y'))
    for x in (-length / 2 + 0.06, length / 2 - 0.06):
        b.torus((x, 0, 0), radius * 0.98, 0.008, 32, 6, 1, 'X')
    return b


def cushion(size: Vec3, puff: float = 0.25) -> MeshBuilder:
    """Rounded mattress or cushion block, bottom at Z = 0."""
    b = MeshBuilder()
    sx, sy, sz = size
    rows, cols, layers = 6, 6, 4

    def point(u: float, v: float, w: float) -> Vec3:
        x = (u - 0.5) * sx
        y = (v - 0.5) * sy
        bulge = (1 - (2 * u - 1) ** 4) * (1 - (2 * v - 1) ** 4)
        z = w * sz * (1 + puff * bulge * (1 if w > 0.5 else 0))
        return (x, y, z)

    b.grid_surface(rows, cols, lambda u, v: point(u, v, 1.0), 0, True)
    b.grid_surface(rows, cols, lambda u, v: point(v, u, 0.0), 0, True)
    for edge in range(4):
        def side(t: float, s: float, e: int = edge) -> Vec3:
            u, v = [(s, 0.0), (1.0, s), (1 - s, 1.0), (0.0, 1 - s)][e]
            x = (u - 0.5) * sx
            y = (v - 0.5) * sy
            round_out = 0.015 * math.sin(math.pi * t)
            return (x * (1 + round_out), y * (1 + round_out), t * sz)

        b.grid_surface(layers, rows, side, 0, True)
    return b


def low_table(width: float, depth: float, height: float) -> MeshBuilder:
    """Low wooden chowki with turned legs."""
    b = MeshBuilder()
    b.box((0, 0, height - 0.03), (width, depth, 0.06))
    b.box((0, 0, height - 0.08), (width - 0.06, depth - 0.06, 0.05))
    for sx in (-1, 1):
        for sy in (-1, 1):
            leg = [Section(0.0, 0.03), Section(0.02, 0.04), Section(height * 0.25, 0.028), Section(height * 0.35, 0.042),
                   Section(height * 0.45, 0.028), Section(height - 0.1, 0.03)]
            b.lathe(leg, 12, 0, True, origin=(sx * (width / 2 - 0.06), sy * (depth / 2 - 0.06), 0))
    return b


def writing_desk(width: float = 0.9, depth: float = 0.5, height: float = 0.32) -> MeshBuilder:
    """Low sloped scribe's desk for writing while seated on the floor."""
    sides = MeshBuilder()
    sides.prism([(-depth / 2, 0.0), (depth / 2, 0.0), (depth / 2, height), (-depth / 2, height * 0.62)], 0.05)
    out = MeshBuilder()
    for sx in (-1, 1):
        out.merge(sides, Matrix.Translation((sx * (width / 2) - (0.05 if sx > 0 else 0.0), 0, 0)))
    slope = math.atan2(height * 0.38, depth)
    top = MeshBuilder()
    top.box((0, 0, 0), (width + 0.04, depth / math.cos(slope) + 0.04, 0.025))
    out.merge(top, Matrix.Translation((0, 0, height * 0.81 + 0.012)) @ Matrix.Rotation(slope, 4, 'X'))
    out.box((0, -depth / 2 - 0.0, height * 0.62 + 0.03), (width, 0.02, 0.04))
    out.box((0, depth / 2 - 0.08, height + 0.05), (width * 0.5, 0.1, 0.05))
    return out


def throne(width: float = 1.9, depth: float = 1.2) -> MeshBuilder:
    """Simhasana: stepped stone seat with rolled armrests and a rounded back.

    Material 0 carved stone, 1 brass inlay.
    """
    b = MeshBuilder()
    b.sweep(rect_path(-width / 2, width / 2, -depth / 2, depth / 2), plinth_profile(0.5, 0.12), 0, True, 0.0)
    b.box((0, 0, 0.25), (width - 0.1, depth - 0.1, 0.5))
    for sx in (-1, 1):
        arm = [(0.0, 0.11), (0.18, 0.11), (0.2, 0.14), (0.38, 0.12), (0.42, 0.15), (0.44, 0.0)]
        b.lathe([Section(0.5 + z, a) for z, a in arm], 24, 0, True, origin=(sx * (width / 2 - 0.12), -depth / 2 + 0.16, 0))
        b.box((sx * (width / 2 - 0.12), 0.05, 0.72), (0.2, depth - 0.3, 0.44))
        b.box((sx * (width / 2 - 0.12), 0.05, 0.96), (0.26, depth - 0.24, 0.06), 1)
    back_w = width - 0.1
    outline = [(-back_w / 2, 0.0)]
    for i in range(17):
        a = math.pi - math.pi * i / 16
        outline.append((math.cos(a) * back_w / 2, 0.9 + math.sin(a) * 0.55))
    outline.append((back_w / 2, 0.0))
    back = MeshBuilder()
    back.prism(outline, 0.16)
    b.merge(back, Matrix.Translation((0, depth / 2 - 0.02, 0.5)) @ Matrix.Rotation(math.radians(90), 4, 'Z'))
    ring = MeshBuilder()
    ring.torus((0, 0, 0), 0.38, 0.03, 40, 8, 1, 'Y')
    b.merge(ring, Matrix.Translation((0, depth / 2 - 0.12, 1.5)))
    return b


def canopy(width: float, depth: float, height: float) -> MeshBuilder:
    """Four slender poles with a cloth canopy and scalloped valance.

    Material 0 poles (brass), 1 canopy cloth, 2 valance trim.
    """
    b = MeshBuilder()
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.lathe([Section(0.0, 0.05), Section(0.06, 0.04), Section(0.08, 0.022), Section(height - 0.1, 0.02),
                     Section(height - 0.05, 0.035), Section(height, 0.02)], 16, 0, True,
                    origin=(sx * width / 2, sy * depth / 2, 0))
    def top(u: float, v: float) -> Vec3:
        x = (u - 0.5) * (width + 0.1)
        y = (v - 0.5) * (depth + 0.1)
        sag = 0.12 * math.sin(math.pi * u) * math.sin(math.pi * v)
        return (x, y, height + 0.1 - sag)

    b.grid_surface(8, 8, top, 1, True)
    scallops = int((width + depth) * 2 / 0.22)
    perimeter = rect_path(-(width + 0.1) / 2, (width + 0.1) / 2, -(depth + 0.1) / 2, (depth + 0.1) / 2)
    edges = list(zip(perimeter, perimeter[1:] + perimeter[:1]))
    total = sum(math.dist(a, b2) for a, b2 in edges)
    for i in range(scallops):
        d = (i + 0.5) / scallops * total
        for a, c in edges:
            seg = math.dist(a, c)
            if d <= seg:
                t = d / seg
                x = a[0] + (c[0] - a[0]) * t
                y = a[1] + (c[1] - a[1]) * t
                yaw = math.atan2(c[1] - a[1], c[0] - a[0])
                tab = MeshBuilder()

                def scallop(u: float, v: float) -> Vec3:
                    w = (u - 0.5) * 0.2
                    depth_v = 0.2 * (0.55 + 0.45 * math.cos(math.pi * (u - 0.5) * 1.6))
                    return (w, 0.0, -v * depth_v)

                tab.grid_surface(4, 2, lambda u, v: scallop(v, u), 2, True)
                b.merge(tab, Matrix.Translation((x, y, height + 0.1)) @ Matrix.Rotation(yaw, 4, 'Z'))
                break
            d -= seg
    return b


def rug(width: float, depth: float) -> MeshBuilder:
    b = MeshBuilder()
    b.box((0, 0, 0.006), (width, depth, 0.012))
    return b


def chest(width: float = 0.9, depth: float = 0.5, height: float = 0.5) -> MeshBuilder:
    """Wooden chest with brass corner straps. Material 0 wood, 1 brass."""
    b = MeshBuilder()
    b.box((0, 0, height / 2 + 0.04), (width, depth, height - 0.08))
    b.box((0, 0, height - 0.02), (width + 0.03, depth + 0.03, 0.06))
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.box((sx * (width / 2 - 0.04), sy * (depth / 2 - 0.04), 0.02), (0.08, 0.08, 0.04))
            b.box((sx * (width / 2 + 0.003), sy * (depth / 2 - 0.05), height / 2), (0.008, 0.1, height - 0.06), 1)
    b.box((0, -depth / 2 - 0.006, height * 0.72), (0.12, 0.012, 0.14), 1)
    return b


def bench(length: float, depth: float = 0.45, height: float = 0.45) -> MeshBuilder:
    b = MeshBuilder()
    b.box((0, 0, height - 0.06), (length, depth, 0.12))
    for x in (-length / 2 + 0.25, length / 2 - 0.25):
        b.box((x, 0, (height - 0.12) / 2), (0.2, depth - 0.06, height - 0.12))
    return b


def tree(seed: int, height: float = 9.0, spread: float = 5.0) -> MeshBuilder:
    """Broadleaf tree (neem / pipal stand-in) with forked branches and clumped foliage.

    Material 0 bark, 1 leaves.
    """
    rng = random.Random(seed)
    b = MeshBuilder()
    trunk_top = height * rng.uniform(0.38, 0.48)
    trunk = [Section(0.0, 0.55, 0, flutes(7, 0.25)), Section(0.35, 0.38, 0, flutes(7, 0.15)),
             Section(trunk_top * 0.6, 0.27, 0, flutes(5, 0.06)), Section(trunk_top, 0.22)]
    b.lathe(trunk, 18, 0, True)

    def limb(start: Vector, end: Vector, r0: float, r1: float) -> None:
        bend = Vector((rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), rng.uniform(0.2, 0.6)))
        loops = []
        for k in range(6):
            t = k / 5
            p = start.lerp(end, t) + bend * math.sin(math.pi * t)
            r = r0 + (r1 - r0) * t
            loops.append([(p.x + r * math.cos(2 * math.pi * j / 7), p.y + r * math.sin(2 * math.pi * j / 7), p.z)
                          for j in range(7)])
        b.loft(loops, 0, True)

    tips: list[Vector] = []
    base = Vector((0, 0, trunk_top))
    count = rng.randint(4, 6)
    for i in range(count):
        angle = 2 * math.pi * i / count + rng.uniform(-0.35, 0.35)
        reach = spread * rng.uniform(0.45, 0.75)
        mid = base + Vector((math.cos(angle) * reach * 0.55, math.sin(angle) * reach * 0.55,
                             height * rng.uniform(0.12, 0.2)))
        limb(base, mid, 0.17, 0.09)
        for _ in range(2):
            a2 = angle + rng.uniform(-0.7, 0.7)
            tip = mid + Vector((math.cos(a2) * reach * 0.5, math.sin(a2) * reach * 0.5, height * rng.uniform(0.1, 0.22)))
            limb(mid, tip, 0.08, 0.03)
            tips.append(tip)
    tips.append(base + Vector((0, 0, height * 0.42)))
    scale = spread / 5.0
    for tip in tips:
        for _ in range(rng.randint(14, 20)):
            offset = Vector((rng.gauss(0, 1.0), rng.gauss(0, 1.0), rng.gauss(0.25, 0.6))) * scale
            leaf_clump(b, tip + offset, rng.uniform(0.32, 0.62) * scale, rng, 1)
    return b


def leaf_clump(builder: MeshBuilder, center: Vector, radius: float, rng: random.Random, mat: int,
               rough: float = 0.28) -> None:
    """Irregular foliage blob: a coarse sphere with jittered vertices so silhouettes break up."""
    first = len(builder.verts)
    builder.sphere(tuple(center), (radius, radius, radius * rng.uniform(0.65, 0.85)), 9, 5, mat)
    for i in range(first, len(builder.verts)):
        v = builder.verts[i]
        d = v - center
        builder.verts[i] = center + d * (1.0 + rng.uniform(-rough, rough))


def bush(seed: int, height: float = 0.7, spread: float = 0.35) -> MeshBuilder:
    """Small dense shrub (tulsi / jasmine) from thin stems and many small leaf clumps.

    Material 0 stems, 1 leaves. Base at Z = 0.
    """
    rng = random.Random(seed)
    b = MeshBuilder()
    for i in range(7):
        a = 2 * math.pi * i / 7 + rng.uniform(-0.3, 0.3)
        lean = rng.uniform(0.2, 0.55) * spread
        top = Vector((math.cos(a) * lean, math.sin(a) * lean, height * rng.uniform(0.7, 1.0)))
        loops = []
        for k in range(4):
            t = k / 3
            p = Vector((0, 0, 0)).lerp(top, t)
            r = 0.018 * (1 - t) + 0.006
            loops.append([(p.x + r * math.cos(2 * math.pi * j / 5), p.y + r * math.sin(2 * math.pi * j / 5), p.z)
                          for j in range(5)])
        b.loft(loops, 0, True)
        for _ in range(rng.randint(6, 9)):
            t = rng.uniform(0.35, 1.05)
            c = Vector((0, 0, 0)).lerp(top, t) + Vector((rng.gauss(0, 0.06), rng.gauss(0, 0.06), rng.gauss(0, 0.05)))
            leaf_clump(b, c, rng.uniform(0.05, 0.095) * spread / 0.35, rng, 1, 0.35)
    return b


def tulsi_vrindavan(width: float = 0.95, height: float = 1.05) -> MeshBuilder:
    """Square masonry altar for the holy basil (tulsi chaura) with corner horns and a diya niche.

    Material 0 stone, 1 recess. The planting bed top is at Z = `height`; front niche faces -Y.
    """
    b = MeshBuilder()
    h = width / 2
    b.box_between((-h - 0.18, -h - 0.18, 0.0), (h + 0.18, h + 0.18, 0.12))
    b.box_between((-h - 0.1, -h - 0.1, 0.12), (h + 0.1, h + 0.1, 0.24))
    b.box_between((-h, -h, 0.24), (h, h, height - 0.16))
    b.box_between((-h - 0.06, -h - 0.06, height - 0.36), (h + 0.06, h + 0.06, height - 0.3))
    b.box_between((-h - 0.08, -h - 0.08, height - 0.16), (h + 0.08, h + 0.08, height))
    b.box_between((-h + 0.1, -h + 0.1, height), (h - 0.1, h - 0.1, height + 0.02), 1)
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.box_between((sx * (h + 0.08) - 0.1 * (sx > 0), sy * (h + 0.08) - 0.1 * (sy > 0), height),
                          (sx * (h + 0.08) + 0.1 * (sx < 0), sy * (h + 0.08) + 0.1 * (sy < 0), height + 0.14))
            b.merge(kalasha(0.16), Matrix.Translation((sx * (h + 0.03), sy * (h + 0.03), height + 0.14)))
    # Diya niche (arched recess) on the front face.
    b.box_between((-0.14, -h - 0.004, 0.42), (0.14, -h + 0.002, 0.68), 1)
    b.box_between((-0.2, -h - 0.05, 0.38), (0.2, -h, 0.42))
    b.box_between((-0.2, -h - 0.05, 0.68), (0.2, -h, 0.74))
    for sx in (-1, 1):
        b.box_between((sx * 0.14 - 0.04 * (sx > 0), -h - 0.05, 0.42), (sx * 0.14 + 0.04 * (sx < 0), -h, 0.68))
    return b


def chhatri(size: float, pillar_height: float = 2.0) -> MeshBuilder:
    """Small open pavilion: moulded base, four slender pillars, eave and stepped roof."""
    b = MeshBuilder()
    half = size / 2
    b.sweep(rect_path(-half, half, -half, half), plinth_profile(0.35, 0.08), 0, True, 0.0)
    b.box((0, 0, 0.17), (size - 0.1, size - 0.1, 0.34))
    inset = half - 0.22
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.merge(slender_pillar(pillar_height, 0.07 * size / 1.6 + 0.04),
                    Matrix.Translation((sx * inset, sy * inset, 0.35)))
    top = 0.35 + pillar_height
    b.box((0, 0, top + 0.07), (size, size, 0.14))
    b.sweep(rect_path(-half, half, -half, half), chhajja_profile(0.32, 0.16, 0.06), 0, True, top + 0.14)
    b.merge(phamsana_roof(size * 0.82, 3, 0.26, 0.5 + size * 0.15), Matrix.Translation((0, 0, top + 0.14)))
    return b


def merlons(length: float, pitch: float = 0.9, width: float = 0.5, height: float = 0.55,
            thick: float = 0.42) -> MeshBuilder:
    """Row of round-topped battlement merlons (kapishirsha) along +X from 0 to `length`."""
    b = MeshBuilder()
    count = max(1, int(length / pitch))
    step = length / count
    top: list[Vec2] = [(-thick / 2, 0.0), (thick / 2, 0.0)]
    arch: list[Vec2] = []
    for i in range(9):
        a = math.pi * i / 8
        arch.append((math.cos(a) * width / 2, height * 0.55 + math.sin(a) * width / 2))
    for i in range(count):
        x = (i + 0.5) * step
        piece = MeshBuilder()
        piece.prism([(u, v) for u, v in arch] + [(-width / 2, 0.0), (width / 2, 0.0)][::-1], thick)
        b.merge(piece, Matrix.Translation((x, thick / 2, 0)) @ Matrix.Rotation(math.radians(-90), 4, 'Z'))
    del top
    return b


def pilaster(builder: MeshBuilder, x: float, z0: float, z1: float, width: float = 0.5, proj: float = 0.16,
             mat: int = 0) -> None:
    """Flat pilaster (bhitti-stambha) on the XZ plane, projecting toward -Y, with base and capital."""
    builder.box_between((x - width / 2, -proj, z0), (x + width / 2, 0.0, z1), mat)
    builder.box_between((x - width / 2 - 0.06, -proj - 0.06, z0), (x + width / 2 + 0.06, 0.0, z0 + 0.32), mat)
    builder.box_between((x - width / 2 - 0.04, -proj - 0.04, z0 + 0.32), (x + width / 2 + 0.04, 0.0, z0 + 0.4), mat)
    builder.box_between((x - width / 2 - 0.05, -proj - 0.05, z1 - 0.34), (x + width / 2 + 0.05, 0.0, z1 - 0.26), mat)
    builder.box_between((x - width / 2 - 0.1, -proj - 0.1, z1 - 0.2), (x + width / 2 + 0.1, 0.0, z1), mat)


def niche(width: float, height: float, crown: bool = True) -> MeshBuilder:
    """Shrine niche (devakoshta) on the XZ plane facing -Y, base at Z = 0, centred on X = 0.

    A dark recess panel (material 1) framed by colonnettes, sill and lintel, with a
    stepped phamsana crown. Everything sits proud of Y = 0 so it can dress any flat wall.
    """
    b = MeshBuilder()
    half = width / 2
    b.box_between((-half - 0.12, -0.26, 0.0), (half + 0.12, 0.0, 0.14))
    b.box_between((-half - 0.06, -0.2, 0.14), (half + 0.06, 0.0, 0.24))
    b.box_between((-half + 0.02, -0.03, 0.24), (half - 0.02, 0.0, height - 0.02), 1)
    for sx in (-1, 1):
        cx = sx * (half - 0.06)
        b.box_between((cx - 0.08, -0.16, 0.24), (cx + 0.08, 0.0, height), 0)
        b.box_between((cx - 0.11, -0.19, height - 0.2), (cx + 0.11, 0.0, height - 0.12), 0)
    b.box_between((-half - 0.1, -0.22, height), (half + 0.1, 0.0, height + 0.16))
    b.box_between((-half - 0.18, -0.3, height + 0.16), (half + 0.18, 0.0, height + 0.24))
    if crown:
        z = height + 0.24
        for k in range(4):
            w = half + 0.06 - k * (half * 0.22)
            h = 0.16 - k * 0.015
            d = 0.26 - k * 0.04
            b.box_between((-w, -d, z), (w, 0.0, z + h))
            b.box_between((-w - 0.05, -d - 0.04, z + h * 0.6), (w + 0.05, 0.0, z + h))
            z += h
        b.merge(amalaka(half * 0.32, 0.12), Matrix.Translation((0, -0.12, z)))
        b.merge(kalasha(0.3), Matrix.Translation((0, -0.12, z + 0.12)))
    return b


def facade_bays(length: float, height: float, bays: int, niches: bool = True, proj: float = 0.16,
                band: bool = True) -> MeshBuilder:
    """Pilastered wall dressing for a flat face on the XZ plane facing -Y, from X = 0 to `length`.

    Pilasters divide the face into `bays`; each bay can carry a shrine niche. A red sandstone
    frieze runs below the capitals. Materials: 0 stone, 1 recess, 2 accent.
    """
    b = MeshBuilder()
    step = length / bays
    for i in range(bays + 1):
        x = min(max(i * step, 0.3), length - 0.3)
        pilaster(b, x, 0.0, height, 0.52, proj)
    if band:
        b.box_between((0.0, -0.05, height - 0.95), (length, 0.0, height - 0.55), 2)
        b.box_between((0.0, -0.09, height - 1.0), (length, 0.0, height - 0.95))
        b.box_between((0.0, -0.09, height - 0.55), (length, 0.0, height - 0.5))
    if niches and step > 1.4:
        w = min(1.2, step * 0.42)
        h = min(2.4, (height - 1.4) * 0.62)
        for i in range(bays):
            b.merge(niche(w, h), Matrix.Translation(((i + 0.5) * step, 0.0, height * 0.18)))
    return b


def blind_arcade(length: float, height: float, pitch: float = 0.9) -> MeshBuilder:
    """Row of shallow arched recesses (material 1) between colonnettes, on the XZ plane facing -Y."""
    b = MeshBuilder()
    count = max(1, int(length / pitch))
    step = length / count
    b.box_between((0.0, -0.12, 0.0), (length, 0.0, 0.1))
    b.box_between((0.0, -0.14, height), (length, 0.0, height + 0.12))
    for i in range(count):
        x0 = i * step
        b.box_between((x0 + 0.07, -0.01, 0.1), (x0 + step - 0.07, 0.0, height - 0.04), 1)
        b.box_between((x0 - 0.06, -0.1, 0.1), (x0 + 0.07, 0.0, height), 0)
        arch: list[Vec2] = []
        half = step / 2 - 0.07
        for k in range(9):
            a = math.pi * k / 8
            arch.append((x0 + step / 2 + math.cos(a) * half, height - 0.04 - half * 0.55 + math.sin(a) * half * 0.55))
        for (ax, az), (bx, bz) in zip(arch, arch[1:]):
            b.box_between((min(ax, bx) - 0.01, -0.06, min(az, bz)), (max(ax, bx) + 0.01, 0.0, height - 0.04), 0)
    b.box_between((length - 0.06, -0.1, 0.1), (length + 0.06, 0.0, height), 0)
    return b


def barrel_ribs(length: float, width: float, rise: float, thick: float, pitch: float = 1.2,
                rib: float = 0.16) -> MeshBuilder:
    """Timber ribs lining the inside of a shala vault (along +X, centred)."""
    b = MeshBuilder()
    steps = 20
    inner: list[Vec2] = []
    for i in range(steps + 1):
        a = math.pi * i / steps
        shape = math.sin(a) ** 0.85
        inner.append((-math.cos(a) * (width / 2 - thick), (rise - thick) * shape))
    face = [(u * 0.97, v * 0.97 - 0.02) for u, v in inner]
    polygon = inner + list(reversed(face))
    count = max(2, int(length / pitch))
    for i in range(count + 1):
        x = -length / 2 + 0.3 + i * (length - 0.6) / count
        piece = MeshBuilder()
        piece.prism(polygon, rib)
        b.merge(piece, Matrix.Translation((x - rib / 2, 0, 0)))
    for side in (-1, 1):
        u, v = inner[4] if side < 0 else inner[-5]
        b.box((0, u * 0.96, v - 0.1), (length - 0.4, 0.14, 0.14))
    return b


def stepped_platform(width: float, depth: float, height: float, step_rise: float = 0.15) -> MeshBuilder:
    """Moulded raised floor with its top at Z = height."""
    b = MeshBuilder()
    b.box((0, 0, height / 2), (width, depth, height))
    b.sweep(rect_path(-width / 2, width / 2, -depth / 2, depth / 2), plinth_profile(height, min(0.3, height * 0.4)),
            0, True, 0.0)
    del step_rise
    return b


def stairs(width: float, rise: float, tread: float, count: int, nosing: float = 0.03) -> MeshBuilder:
    """Flight climbing toward -X: step 0 is lowest at the +X end, top lands at X = 0."""
    b = MeshBuilder()
    for i in range(count):
        top = rise * (i + 1)
        x_front = (count - i) * tread
        b.box_between((0.0, -width / 2, 0.0), (x_front, width / 2, top - 0.0))
        b.box_between((x_front - 0.02, -width / 2, top - 0.05), (x_front + nosing, width / 2, top))
    return b


def flag(pole: float = 3.2, length: float = 1.6, drop: float = 0.9, seed: int = 0) -> MeshBuilder:
    """Pennant (dhvaja) on a slender pole: material 0 pole, 1 cloth. Flies toward +X."""
    rng = random.Random(seed)
    b = MeshBuilder()
    b.lathe([Section(0.0, 0.04), Section(pole, 0.025), Section(pole + 0.02, 0.05), Section(pole + 0.1, 0.0)], 10, 0,
            True)
    phase = rng.uniform(0, 6.28)

    def cloth(u: float, v: float) -> Vec3:
        x = u * length
        taper = 1.0 - 0.85 * u
        z = pole - 0.05 - v * drop * taper - 0.12 * u * u
        y = 0.12 * math.sin(phase + u * 7.0) * u + 0.03 * math.sin(v * 3.0)
        return (x, y, z)

    b.grid_surface(12, 4, lambda u, v: cloth(v, u), 1, True)
    return b
