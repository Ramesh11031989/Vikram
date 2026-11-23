"""Build Set 1, the palace (महल): private chamber, interrogation room and open darbar.

Run from the repository root:

    blender --background --factory-startup --python-exit-code 1 \
        --python Blender/tools/build_palace_set.py

or with Blender as a Python module (`pip install bpy==5.2.2`):

    python Blender/tools/build_palace_set.py

Writes `Blender/Sets/SET_Palace.blend` and `Blender/Sets/SET_Palace_Manifest.json`.
The palace sits on the shared Chapter 1 map in `set_world_map.py`. Every palace
object is parented to `Palace | Map anchor`; local coordinates below are metres
from the centre of the darbar floor, +X toward the public gate, +Y toward the
river façade that holds the ghat window. Local Z = 0 is the plinth top.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import set_ghat_placeholder as ghat  # noqa: E402
import set_kit as kit  # noqa: E402
from set_kit import MeshBuilder, Opening, PillarStyle  # noqa: E402
import set_materials as mats  # noqa: E402
import set_world_map as world  # noqa: E402


ROOT = Path(__file__).resolve().parents[2]
SET_DIR = ROOT / 'Blender' / 'Sets'
BLEND = SET_DIR / 'SET_Palace.blend'
MANIFEST = SET_DIR / 'SET_Palace_Manifest.json'

FLOOR = 0.6
"""Raised floor of every hall and room above the plinth top."""
ROOM_TOP = 5.4
DARBAR_PILLAR = 4.4
DARBAR_CEILING = FLOOR + DARBAR_PILLAR + kit.BEAM_HEIGHT  # 5.56
DARBAR_ROOF = DARBAR_CEILING + 0.3
CLERESTORY = 1.9
NAVE_SPRING = DARBAR_ROOF + CLERESTORY + kit.BEAM_HEIGHT  # 8.32
NAVE_HALF = 3.5
DARBAR_X = (-9.6, 30.8)
DARBAR_Y = 14.2
COLUMN_X = (-2.0, 2.0, 6.0, 10.0, 14.0, 18.0, 22.0, 26.0, 30.0)
ROW_Y = (-13.5, -8.5, -3.5, 3.5, 8.5, 13.5)
JUDGMENT_CENTRE = (2.0, 0.0)
PLATFORM = (-9.2, -3.2, -6.5, 6.5)
PLATFORM_TOP = FLOOR + 1.05
CHALK_CENTRE = (-26.2, -18.2)
CHALK_HALF = (2.0, 1.6)

MORNING, EVENING = 1, 2


# ---------------------------------------------------------------------------
# Scene and palette
# ---------------------------------------------------------------------------

@dataclass
class Palette:
    stone: bpy.types.Material
    carved: bpy.types.Material
    red: bpy.types.Material
    plaster_room: bpy.types.Material
    plaster_darbar: bpy.types.Material
    plaster_court: bpy.types.Material
    floor_hall: bpy.types.Material
    floor_nave: bpy.types.Material
    floor_basalt: bpy.types.Material
    floor_room: bpy.types.Material
    paving: bpy.types.Material
    basalt: bpy.types.Material
    teak: bpy.types.Material
    dark_teak: bpy.types.Material
    brass: bpy.types.Material
    iron: bpy.types.Material
    indigo: bpy.types.Material
    madder: bpy.types.Material
    ochre: bpy.types.Material
    rug_a: bpy.types.Material
    rug_b: bpy.types.Material
    linen: bpy.types.Material
    clay: bpy.types.Material
    flame: bpy.types.Material
    recess: bpy.types.Material
    still_water: bpy.types.Material
    leaves: bpy.types.Material
    tulsi: bpy.types.Material
    bark: bpy.types.Material


def palette() -> Palette:
    room = mats.PaintScheme()
    darbar = mats.PaintScheme(field=(0.74, 0.64, 0.48), dado=(0.36, 0.10, 0.06), frieze=(0.10, 0.17, 0.24),
                              motif=(0.72, 0.52, 0.22), motif_core=(0.42, 0.10, 0.06),
                              dado_height=1.1, frieze_low=4.45, frieze_high=4.95, motif_period=0.6)
    court = mats.PaintScheme(field=(0.70, 0.58, 0.42), dado=(0.40, 0.15, 0.08), floor_z=0.0,
                             frieze_low=3.6, frieze_high=4.0)
    return Palette(
        stone=mats.stone('Palace | weathered sandstone', mats.SANDSTONE),
        carved=mats.stone('Palace | carved sandstone', mats.CARVED_SANDSTONE),
        red=mats.stone('Palace | red sandstone accents', mats.RED_SANDSTONE),
        plaster_room=mats.painted_plaster('Palace | painted lime plaster (rooms)', room),
        plaster_darbar=mats.painted_plaster('Palace | painted lime plaster (darbar)', darbar),
        plaster_court=mats.painted_plaster('Palace | painted lime plaster (courtyard)', court),
        floor_hall=mats.slab_floor('Palace | darbar floor slabs', mats.CARVED_SANDSTONE, (1.6, 1.0), polish=0.32),
        floor_nave=mats.slab_floor('Palace | nave processional slabs', mats.RED_SANDSTONE, (1.1, 1.1), polish=0.3),
        floor_basalt=mats.slab_floor('Palace | interrogation basalt floor', mats.BASALT, (1.5, 1.0), polish=0.12),
        floor_room=mats.slab_floor('Palace | chamber floor slabs', mats.SANDSTONE, (1.2, 0.8), polish=0.3),
        paving=mats.slab_floor('Palace | courtyard paving', mats.SANDSTONE, (0.9, 0.6)),
        basalt=mats.stone('Palace | basalt inlay', mats.BASALT),
        teak=mats.teak('Palace | teak'),
        dark_teak=mats.teak('Palace | smoked teak ceiling', (0.11, 0.055, 0.028)),
        brass=mats.metal('Palace | brass', (0.80, 0.56, 0.24), 0.28),
        iron=mats.metal('Palace | black iron', (0.05, 0.05, 0.05), 0.55, (0.06, 0.04, 0.03)),
        indigo=mats.cloth('Palace | indigo silk', (0.05, 0.07, 0.16), (0.55, 0.38, 0.12), (0.30, 0.06, 0.05)),
        madder=mats.cloth('Palace | madder cotton', (0.34, 0.06, 0.04), (0.62, 0.44, 0.14), (0.06, 0.08, 0.16)),
        ochre=mats.cloth('Palace | ochre brocade', (0.52, 0.34, 0.10), (0.36, 0.09, 0.05), (0.08, 0.10, 0.18), 14),
        rug_a=mats.cloth('Palace | dhurrie indigo-madder', (0.08, 0.09, 0.18), (0.40, 0.08, 0.05),
                         (0.68, 0.52, 0.26), 3.0, 'Y'),
        rug_b=mats.cloth('Palace | dhurrie madder-ochre', (0.36, 0.08, 0.05), (0.55, 0.36, 0.12),
                         (0.08, 0.09, 0.16), 2.4, 'X'),
        linen=mats.cloth('Palace | unbleached cotton', (0.62, 0.55, 0.42), (0.50, 0.40, 0.26), (0.36, 0.10, 0.06), 20),
        clay=mats.terracotta('Palace | terracotta'),
        flame=mats.flame('Palace | lamp flame'),
        recess=mats.flat('Palace | deep shadow recess', (0.025, 0.02, 0.016), 0.95),
        still_water=mats.river_water('Palace | basin water'),
        leaves=mats.foliage('Palace | garden leaves', (0.05, 0.09, 0.03)),
        tulsi=mats.foliage('Palace | tulsi leaves', (0.04, 0.085, 0.025), 34.0),
        bark=mats.teak('Palace | garden bark', (0.12, 0.08, 0.05)),
    )


def reset_scene() -> bpy.types.Scene:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = 'Palace • Set 1'
    scene.unit_settings.system = 'METRIC'
    scene.render.fps = 24
    scene.frame_start, scene.frame_end = MORNING, EVENING
    return scene


# ---------------------------------------------------------------------------
# Placement helpers
# ---------------------------------------------------------------------------

class Palace:
    def __init__(self, scene: bpy.types.Scene) -> None:
        self.scene = scene
        self.root = bpy.data.collections.new('SET_Palace')
        scene.collection.children.link(self.root)
        self.anchor = bpy.data.objects.new('Palace | Map anchor', None)
        self.anchor.empty_display_type = 'ARROWS'
        self.anchor.empty_display_size = 4
        self.root.objects.link(self.anchor)
        self.kit = kit.Kit(self.root, self.anchor)
        self.m = palette()

    def add(self, name: str, builder: MeshBuilder, materials: list[bpy.types.Material], collection: str,
            location: tuple[float, float, float] = (0.0, 0.0, 0.0), yaw: float = 0.0,
            sharp: float = 38.0) -> bpy.types.Object:
        return self.kit.place(name, builder.mesh(name, materials, sharp), collection, location, yaw)

    def shared(self, key: str, make: callable, materials: list[bpy.types.Material]) -> bpy.types.Mesh:
        return self.kit.mesh(key, lambda: make().mesh(key, materials))

    def instance(self, name: str, mesh: bpy.types.Mesh, collection: str, location: tuple[float, float, float],
                 yaw: float = 0.0, scale: tuple[float, float, float] | None = None) -> bpy.types.Object:
        return self.kit.place(name, mesh, collection, location, yaw, scale)

    def pillar(self, style: PillarStyle, collection: str, location: tuple[float, float, float],
               name: str = 'Stambha') -> bpy.types.Object:
        key = f'Pillar h{style.height:.2f} s{style.scale:.2f} b{int(style.bells)}{int(style.bracket)}{int(style.bracket_both)}'
        mesh = self.shared(key, lambda: kit.stambha(style), [self.m.carved])
        return self.instance(name, mesh, collection, location)

    def beam(self, collection: str, start: tuple[float, float], end: tuple[float, float], z: float,
             name: str = 'Architrave') -> bpy.types.Object:
        length = math.dist(start, end)
        key = f'Beam {length:.2f}'
        mesh = self.shared(key, lambda: kit.beam(length), [self.m.carved])
        yaw = math.degrees(math.atan2(end[1] - start[1], end[0] - start[0]))
        return self.instance(name, mesh, collection, (start[0], start[1], z), yaw)

    def jali(self, collection: str, centre: tuple[float, float], z: float, width: float, height: float,
             yaw: float, pattern: str = 'rosette', name: str = 'Jali screen') -> bpy.types.Object:
        key = f'Jali {width:.2f}x{height:.2f} {pattern}'
        mesh = self.kit.mesh(key, lambda: kit.finish_jali(kit.jali(width, height, 0.17, 0.07, pattern)
                                                            .mesh(key, [self.m.carved], 30.0)))
        obj = self.instance(name, mesh, collection, (centre[0], centre[1], z), yaw)
        solid = obj.modifiers.new('Stone thickness', 'SOLIDIFY')
        solid.thickness = 0.09
        solid.offset = 0.0
        return obj

    def door(self, collection: str, hinge: tuple[float, float], width: float, height: float,
             yaw: float, name: str, z: float = FLOOR) -> bpy.types.Object:
        """Door leaf hinged at `hinge`; yaw 0 lays the closed leaf along +X."""
        key = f'Door leaf {width:.2f}x{height:.2f}'
        mesh = self.shared(key, lambda: kit.door_leaf(width, height), [self.m.teak, self.m.brass])
        return self.instance(name, mesh, collection, (hinge[0], hinge[1], z), yaw)

    def frame(self, collection: str, centre: tuple[float, float], z: float, width: float, head: float,
              yaw: float, name: str = 'Door frame') -> bpy.types.Object:
        key = f'Door frame {width:.2f}x{head:.2f}'
        mesh = self.shared(key, lambda: kit.door_frame(width, head, 0.035), [self.m.carved, self.m.red])
        return self.instance(name, mesh, collection, (centre[0], centre[1], z), yaw)


# ---------------------------------------------------------------------------
# Plinth, bastions and enclosing walls
# ---------------------------------------------------------------------------

def plinth(p: Palace) -> None:
    c = 'Palace | Plinth, bastions & walls'
    x0, x1, y0, y1 = world.PALACE_PLINTH_LOCAL
    b = MeshBuilder()
    b.box_between((x0, y0, -2.0), (x1, y1, 0.0), {'*': 0, '+z': 1})
    b.sweep([(x0, y0), (x1, y0), (x1, y1)], kit.plinth_profile(2.0, 0.55), 0, False, -2.0)
    p.add('Palace plinth (jagati)', b, [p.m.stone, p.m.paving], c)

    # River-facing bastion: battered wall with string courses and a cornice.
    bastion: list[tuple[float, float]] = [(-0.1, -17.5), (2.6, -17.5), (2.2, -14.2), (2.4, -14.2), (2.4, -13.9),
                                          (2.0, -13.9), (1.5, -9.2), (1.7, -9.2), (1.7, -8.9), (1.3, -8.9),
                                          (0.8, -4.2), (1.0, -4.2), (1.0, -3.9), (0.6, -3.9), (0.35, -1.0),
                                          (0.55, -0.8), (0.75, -0.45), (0.75, -0.2), (0.45, -0.2),
                                          (0.45, 0.0), (-0.1, 0.0)]
    b = MeshBuilder()
    b.sweep([(x1, y1), (x0, y1), (x0, y0)], bastion, 0, False, 0.0)
    p.add('River bastion (battered retaining wall)', b, [p.m.stone], c)

    tower_rings = [kit.Section(-17.5, 1.0), kit.Section(-4.0, 0.82), kit.Section(-4.0, 0.86), kit.Section(-3.7, 0.86),
                   kit.Section(-3.7, 0.80), kit.Section(-0.6, 0.76), kit.Section(-0.4, 0.82), kit.Section(-0.2, 0.84),
                   kit.Section(-0.2, 0.78), kit.Section(0.0, 0.78)]
    for (tx, ty, radius, rises) in ((x0, y1, 5.4, True), (x1, y1, 4.2, True), (x0, y0, 4.6, True),
                                    (6.0, y1, 3.0, False), (30.0, y1, 3.0, False), (x0, 0.0, 3.2, False)):
        # Push each tower outward so it clasps the corner instead of cutting into the rooms.
        out_x = -1 if tx == x0 else (1 if tx == x1 else 0)
        out_y = 1 if ty == y1 else (-1 if ty == y0 else 0)
        push = 0.72 if rises else 0.78
        tx += out_x * radius * push
        ty += out_y * radius * push
        b = MeshBuilder()
        top = 6.6 if rises else 0.0
        rings = [kit.Section(s.z, s.a * radius) for s in tower_rings]
        if rises:
            rings = rings[:-1] + [kit.Section(top - 0.5, 0.78 * radius), kit.Section(top - 0.3, 0.86 * radius),
                                  kit.Section(top, 0.86 * radius)]
        b.lathe(rings, kit.RING, 0, True)
        para = kit.parapet_profile(1.0, 0.36)
        circle = [(tx + 0.86 * radius * math.cos(2 * math.pi * i / 48),
                   ty + 0.86 * radius * math.sin(2 * math.pi * i / 48)) for i in range(48)]
        b.sweep([(x - tx, y - ty) for x, y in circle], para, 0, True, top)
        tower = p.add('Bastion tower (burj)', b, [p.m.stone], c, (tx, ty, 0.0))
        tower['Top'] = top
        roof_size = radius * 0.9 if rises else radius * 1.0
        mesh = p.shared(f'Chhatri {roof_size:.2f}', lambda s=roof_size: kit.chhatri(s, 2.2), [p.m.carved])
        p.instance('Tower chhatri', mesh, 'Palace | Roofs & pavilions', (tx, ty, top))

    # Fortified enclosure on the town sides, with round-topped merlons.
    b = MeshBuilder()
    wall_h = 4.4
    for (sx, sy), (ex, ey) in (((-9.6, y0 + 0.5), (x1 - 0.5, y0 + 0.5)), ((x1 - 0.5, y0 + 0.5), (x1 - 0.5, -9.0)),
                               ((x1 - 0.5, 9.0), (x1 - 0.5, y1 - 0.5))):
        kit.wall(b, (sx, sy), (ex, ey), 0.0, wall_h, 1.0, (), 1, 0, 0)
        length = math.dist((sx, sy), (ex, ey))
        yaw = math.atan2(ey - sy, ex - sx)
        b.merge(kit.merlons(length, 0.95, 0.52, 0.6, 0.5), Matrix.Translation((sx, sy, wall_h)) @
                Matrix.Rotation(yaw, 4, 'Z'))
        b.merge(_strip(length, 0.25, 0.18), Matrix.Translation((sx, sy, wall_h - 0.18)) @ Matrix.Rotation(yaw, 4, 'Z'))
    p.add('Enclosure wall with merlons', b, [p.m.stone], c)
    # Pilasters and a red frieze on the town faces of the enclosure.
    b = MeshBuilder()
    for origin, yaw, length in (((-9.6, y0), 0.0, x1 - 0.5 + 9.6), ((x1, y0 + 0.5), 90.0, -9.0 - y0 - 0.5),
                                ((x1, 9.0), 90.0, y1 - 0.5 - 9.0)):
        bays = max(1, round(length / 4.6))
        b.merge(kit.facade_bays(length, wall_h - 0.2, bays, False, 0.14),
                Matrix.Translation((origin[0], origin[1], 0.0)) @ Matrix.Rotation(math.radians(yaw), 4, 'Z'))
    p.add('Enclosure wall pilasters & frieze', b, [p.m.stone, p.m.recess, p.m.red], c)
    # River terrace parapet between the private wing and the gate.
    b = MeshBuilder()
    b.sweep([(x1 - 0.5, y1 - 0.1), (-9.6, y1 - 0.1)], kit.parapet_profile(0.95, 0.4), 0, False, 0.0)
    p.add('River terrace parapet', b, [p.m.stone], c)


def _strip(length: float, depth: float, height: float) -> MeshBuilder:
    b = MeshBuilder()
    b.box_between((0.0, -depth - 0.5, 0.0), (length, depth + 0.5, height))
    return b


# ---------------------------------------------------------------------------
# Darbar (open court hall)
# ---------------------------------------------------------------------------

def darbar(p: Palace) -> dict[str, object]:
    c = 'Palace | Darbar (open court)'
    m = p.m
    x0, x1 = DARBAR_X
    # Raised hall floor with moulded edges.
    b = MeshBuilder()
    b.box_between((x0, -DARBAR_Y, 0.0), (x1, DARBAR_Y, FLOOR), {'*': 0, '+z': 1})
    b.sweep(kit.rect_path(x0, x1, -DARBAR_Y, DARBAR_Y), kit.plinth_profile(FLOOR, 0.26), 0, True, 0.0)
    p.add('Darbar floor platform', b, [m.stone, m.floor_hall], c)
    b = MeshBuilder()
    b.box_between((-1.4, -2.2, FLOOR), (x1, 2.2, FLOOR + 0.012))
    p.add('Nave processional floor (red sandstone)', b, [m.floor_nave], c)
    b = MeshBuilder()
    cx, cy = JUDGMENT_CENTRE
    z_inlay = FLOOR + 0.014
    b.lathe([kit.Section(z_inlay, 2.62, 8), kit.Section(z_inlay, 2.47, 8)], kit.RING, 0, False, False, False,
            origin=(cx, cy, 0))
    b.lathe([kit.Section(z_inlay, 2.3), kit.Section(z_inlay, 2.25)], kit.RING, 1, False, False, False, origin=(cx, cy, 0))
    b.lathe([kit.Section(z_inlay, 1.15, 0, kit.petals(16, 0.42, 1.5)), kit.Section(z_inlay, 0.95, 0, kit.petals(16, 0.42, 1.5))],
            kit.RING, 0, False, False, False, origin=(cx, cy, 0))
    b.lathe([kit.Section(z_inlay, 0.62, 0, kit.petals(8, 0.35, 1.5)), kit.Section(z_inlay, 0.5, 0, kit.petals(8, 0.35, 1.5))],
            kit.RING, 1, False, False, False, origin=(cx, cy, 0))
    b.lathe([kit.Section(z_inlay, 0.18), kit.Section(z_inlay, 0.0)], kit.RING, 0, False, False, False, origin=(cx, cy, 0))
    p.add('Judgment octagon inlay (basalt and brass)', b, [m.basalt, m.brass], c)
    b = MeshBuilder()
    b.merge(kit.stairs(10.0, 0.15, 0.45, 4), Matrix.Translation((x1, 0, 0.0)))
    for side in (-1, 1):
        b.merge(kit.stairs(6.0, 0.15, 0.4, 4), Matrix.Translation((14.0, side * DARBAR_Y, 0.0)) @
                Matrix.Rotation(math.radians(90 * side), 4, 'Z'))
    p.add('Darbar entrance steps', b, [m.stone], c)

    # Pillars: main grid, the judgment bay is opened by omitting x = 2 on the nave rows.
    style = PillarStyle(DARBAR_PILLAR, 1.0, True, True, True)
    for x in COLUMN_X:
        for y in ROW_Y:
            if x == 2.0 and abs(y) == NAVE_HALF:
                continue
            p.pillar(style, c, (x, y, FLOOR), 'Darbar stambha')
    # Architraves on the pillars.
    z_beam = FLOOR + DARBAR_PILLAR
    for y in ROW_Y:
        xs = [x for x in COLUMN_X if not (x == 2.0 and abs(y) == NAVE_HALF)]
        for a, b2 in zip(xs, xs[1:]):
            p.beam(c, (a, y), (b2, y), z_beam)
    for x in COLUMN_X:
        for ya, yb in ((-13.5, -8.5), (-8.5, -3.5), (3.5, 8.5), (8.5, 13.5)):
            p.beam(c, (x, ya), (x, yb), z_beam)
    # Back zone (platform) beams and the back wall.
    for y in (-8.5, -3.5, 3.5, 8.5):
        p.beam(c, (x0 + 0.4, y), (-2.0, y), z_beam)
    walls = MeshBuilder()
    kit.wall(walls, (x0, -DARBAR_Y), (x0, DARBAR_Y), FLOOR, DARBAR_CEILING - FLOOR, 0.8,
             (Opening(5.7, 1.6, 0.0, 3.0), Opening(22.7, 1.6, 0.0, 3.0), Opening(14.2, 3.6, 1.6, 4.6, 'jali')),
             -1, 0, 1)
    for side in (-1, 1):
        y = side * 13.8
        inside = -1 if side > 0 else 1
        kit.wall(walls, (x0 + 0.4, y), (-2.45, y), FLOOR, DARBAR_CEILING - FLOOR, 0.6,
                 (Opening(3.4, 1.8, 1.2, 3.8, 'jali'),), inside, 0, 1)
    p.add('Darbar back and side walls', walls, [m.stone, m.plaster_darbar], c)
    p.jali(c, (x0, 0.0), FLOOR + 1.6, 3.6, 3.0, 90, 'rosette', 'Throne jali (backlit from courtyard)')
    for side in (-1, 1):
        p.jali(c, (x0 + 0.4 + 3.4, side * 13.8), FLOOR + 1.2, 1.8, 2.6, 0, 'star', 'Platform side jali')
        p.frame(c, (x0 + 0.42, side * 8.5), FLOOR, 1.6, 3.0, -90, 'Private door frame')
        p.door(c, (x0 + 0.45, side * 8.5 - 0.8), 0.8, 3.0, 90 - 100, 'Private door leaf')
        p.door(c, (x0 + 0.45, side * 8.5 + 0.8), 0.8, 3.0, -90 + 100, 'Private door leaf')
    frame = p.frame(c, (x0 + 0.42, 0.0), FLOOR + 1.6, 3.6, 3.0, -90, 'Throne jali frame')
    frame.scale = (1.0, 1.0, 1.0)

    # Ceilings: coffered aisle slabs with lotus rosettes; low ceiling over the platform.
    ceiling = MeshBuilder()
    for ya, yb in ((NAVE_HALF + 0.28, DARBAR_Y), (-DARBAR_Y, -NAVE_HALF - 0.28)):
        ceiling.box_between((-2.0 - 0.3, ya, DARBAR_CEILING), (x1, yb, DARBAR_ROOF))
    ceiling.box_between((x0, -DARBAR_Y, DARBAR_CEILING), (-2.0 - 0.3, DARBAR_Y, DARBAR_ROOF))
    p.add('Darbar aisle ceiling slabs', ceiling, [m.carved], c)
    rosette = p.shared('Lotus rosette 0.7', lambda: kit.lotus_rosette(0.7, 0.12), [m.carved])
    for xa, xb in zip(COLUMN_X, COLUMN_X[1:]):
        for ya, yb in ((-13.5, -8.5), (-8.5, -3.5), (3.5, 8.5), (8.5, 13.5)):
            p.instance('Ceiling lotus', rosette, c, ((xa + xb) / 2, (ya + yb) / 2, DARBAR_CEILING))
    for y in (-11.0, -6.0, 0.0, 6.0, 11.0):
        p.instance('Ceiling lotus', rosette, c, (-5.6, y, DARBAR_CEILING), scale=(1.3, 1.3, 1.3))
    outer = MeshBuilder()
    outer.sweep(kit.rect_path(x0 - 0.4, x1, -DARBAR_Y, DARBAR_Y), kit.chhajja_profile(1.25, 0.42, 0.12), 0, True,
                DARBAR_ROOF - 0.05)
    outer.sweep(kit.rect_path(x0 - 0.4, x1, -DARBAR_Y, DARBAR_Y), kit.cornice_profile(0.25, 0.32), 0, True,
                DARBAR_ROOF)
    for ya, yb in ((NAVE_HALF + 0.4, DARBAR_Y), (-DARBAR_Y, -NAVE_HALF - 0.4)):
        path = [(x0 - 0.2, ya), (x1 - 0.2, ya), (x1 - 0.2, yb), (x0 - 0.2, yb)]
        path = [(x0 - 0.2, ya), (x1 - 0.2, ya), (x1 - 0.2, yb), (x0 - 0.2, yb)]
        outer.sweep(path, kit.parapet_profile(0.85, 0.32), 0, True, DARBAR_ROOF + 0.32)
    p.add('Darbar eaves, cornice and roof parapets', outer, [m.stone], 'Palace | Roofs & pavilions')

    # Clerestory over the nave rows, then the barrel vault and the judgment drum.
    roofs = 'Palace | Roofs & pavilions'
    small = PillarStyle(CLERESTORY, 0.55, False, True, False)
    clerestory_x = (-2.0, 2.0, 6.0, 10.0, 14.0, 18.0, 22.0, 26.0, 30.0)
    for y in (-NAVE_HALF, NAVE_HALF):
        for x in clerestory_x:
            p.pillar(small, roofs, (x, y, DARBAR_ROOF), 'Clerestory pillar')
        for xa, xb in zip(clerestory_x, clerestory_x[1:]):
            p.jali(roofs, ((xa + xb) / 2, y), DARBAR_ROOF + 0.05, 3.3, CLERESTORY - 0.35, 0, 'rosette',
                   'Clerestory jali')
            p.beam(roofs, (xa, y), (xb, y), DARBAR_ROOF + CLERESTORY)
    b = MeshBuilder()
    b.box_between((-2.4, -NAVE_HALF - 0.3, DARBAR_ROOF), (-1.7, NAVE_HALF + 0.3, NAVE_SPRING))
    p.add('Judgment bay west clerestory wall', b, [m.stone], roofs)
    p.jali(roofs, (-2.05, 0.0), DARBAR_ROOF + 0.2, 4.2, 1.9, 90, 'star', 'Judgment bay west jali')
    vault_len = 24.0
    barrel = p.add('Nave shala vault', kit.shala_roof(vault_len + 0.4, 2 * NAVE_HALF + 0.6, 3.3, 0.8),
                   [m.stone, m.recess], roofs, (18.0, 0.0, NAVE_SPRING))
    barrel['Note'] = 'Ribbed barrel vault seen from the nave; gavaksha gable faces the forecourt.'
    p.add('Nave vault timber ribs', kit.barrel_ribs(vault_len, 2 * NAVE_HALF + 0.6, 3.3, 0.25), [m.dark_teak], c,
          (18.0, 0.0, NAVE_SPRING))
    # Judgment bay: ceiling with a corbelled lotus dome, a drum and a stepped roof.
    b = MeshBuilder()
    half = 3.2
    z = NAVE_SPRING
    b.box_between((-2.4, -NAVE_HALF - 0.3, z), (6.4, -half, z + 0.3))
    b.box_between((-2.4, half, z), (6.4, NAVE_HALF + 0.3, z + 0.3))
    b.box_between((-2.4, -half, z), (cx - half, half, z + 0.3))
    b.box_between((cx + half, -half, z), (6.4, half, z + 0.3))
    corner = half * math.tan(math.radians(22.5))
    for sx in (-1, 1):
        for sy in (-1, 1):
            pts = [(cx + sx * half, sy * corner), (cx + sx * half, sy * half), (cx + sx * corner, sy * half)]
            for zz in (z, z + 0.3):
                ids = [b.vert((px, py, zz)) for px, py in pts]
                b.face(ids if sx * sy > 0 else list(reversed(ids)))
    for wx0, wy0, wx1, wy1 in ((-2.4, -NAVE_HALF - 0.3, 6.4, -NAVE_HALF + 0.1), (-2.4, NAVE_HALF - 0.1, 6.4, NAVE_HALF + 0.3),
                               (-2.4, -NAVE_HALF, -2.0, NAVE_HALF), (6.0, -NAVE_HALF, 6.4, NAVE_HALF)):
        b.box_between((wx0, wy0, z + 0.3), (wx1, wy1, z + 3.6))
    b.sweep(kit.rect_path(-2.4, 6.4, -NAVE_HALF - 0.3, NAVE_HALF + 0.3), kit.chhajja_profile(0.9, 0.3, 0.1), 0, True,
            z + 3.6)
    p.add('Judgment bay ceiling and drum', b, [m.carved], roofs)
    p.add('Judgment lotus dome (vitana)', kit.lotus_vitana(half, 2.5, 6), [m.carved, m.carved], c, (cx, 0.0, z))
    p.add('Judgment bay stepped roof (phamsana)', kit.phamsana_roof(8.0, 4, 0.55, 2.2), [m.stone], roofs,
          (cx, 0.0, z + 3.6))
    # Royal platform, throne, canopy.
    px0, px1, py0, py1 = PLATFORM
    b = MeshBuilder()
    b.box_between((px0, py0, FLOOR), (px1, py1, PLATFORM_TOP), {'*': 0, '+z': 1})
    b.sweep(kit.rect_path(px0, px1, py0, py1), kit.plinth_profile(PLATFORM_TOP - FLOOR, 0.18), 0, True, FLOOR)
    b.merge(kit.stairs(4.4, 0.175, 0.3, 6), Matrix.Translation((px1, 0.0, FLOOR)))
    p.add('Royal platform (simhasana-vedi)', b, [m.carved, m.floor_room], c)
    d = 'Palace | Dressing'
    p.add('Royal carpet', kit.rug(5.4, 11.6), [m.rug_a], d, ((px0 + px1) / 2, 0.0, PLATFORM_TOP))
    throne = p.add('Throne (simhasana)', kit.throne(2.0, 1.25), [m.carved, m.brass], c, (-7.3, 0.0, PLATFORM_TOP), 90)
    throne['Story'] = 'Vikram reads the order and dictates its withdrawal from here.'
    p.add('Throne cushion', kit.cushion((1.45, 0.9, 0.12)), [m.madder], d, (-7.25, 0.0, PLATFORM_TOP + 0.5), 90)
    p.add('Throne bolster', kit.bolster(1.4, 0.15), [m.ochre, m.brass], d, (-7.75, 0.0, PLATFORM_TOP + 0.72), 90)
    p.add('Throne canopy (chhatra)', kit.canopy(2.6, 2.2, 2.75), [m.brass, m.madder, m.ochre], d,
          (-7.3, 0.0, PLATFORM_TOP), 90)
    # Clerk's writing place beside the platform.
    p.add('Darbar clerk mat', kit.rug(1.4, 1.2), [m.rug_b], d, (-0.6, -6.6, FLOOR))
    p.add('Darbar clerk cushion', kit.cushion((0.6, 0.5, 0.08)), [m.madder], d, (-0.6, -6.9, FLOOR + 0.012))
    p.add('Darbar clerk writing desk', kit.writing_desk(), [m.teak], d, (-0.6, -6.2, FLOOR + 0.012))
    # Lamps.
    stand = p.shared('Lamp stand 1.6', lambda: kit.lamp_stand(1.6), [m.brass, m.flame])
    for y in (-2.9, 2.9):
        p.instance('Brass lamp stand', stand, d, (-1.0, y, FLOOR))
    for x in (8.0, 16.0, 24.0):
        for y in (-5.6, 5.6):
            p.instance('Brass lamp stand', stand, d, (x, y, FLOOR))
    hanging = p.shared('Hanging lamp 3.4', lambda: kit.hanging_lamp(3.4), [m.brass, m.flame])
    for x in (10.0, 16.0, 22.0, 28.0):
        p.instance('Hanging lamp', hanging, d, (x, 0.0, NAVE_SPRING + 0.6))
    hanging_small = p.shared('Hanging lamp 1.4', lambda: kit.hanging_lamp(1.4), [m.brass, m.flame])
    for y in (-3.0, 3.0):
        p.instance('Hanging lamp', hanging_small, d, (-5.6, y, DARBAR_CEILING - 0.4))
    # Courtier seating along the outer aisles.
    for side in (-1, 1):
        y = side * 11.0
        p.add('Courtier seating platform', kit.stepped_platform(13.0, 1.4, 0.32), [m.carved], d, (5.0, y, FLOOR))
        p.add('Courtier dhurrie', kit.rug(12.6, 1.2), [m.rug_b], d, (5.0, y, FLOOR + 0.32))
        p.add('Courtier bolster', kit.bolster(12.0, 0.13), [m.indigo, m.brass], d,
              (5.0, y + side * 0.55, FLOOR + 0.45))
    return {}


# ---------------------------------------------------------------------------
# Private wing: chamber, ante-room, courtyard, interrogation and waiting hall
# ---------------------------------------------------------------------------

def private_wing(p: Palace) -> None:
    m = p.m
    c_ch = 'Palace | Private chamber (निजी कक्ष)'
    c_iq = 'Palace | Interrogation & waiting (पूछताछ)'
    c_ct = 'Palace | Courtyard & verandahs'
    d = 'Palace | Dressing'
    x0 = world.PALACE_PLINTH_LOCAL[0]
    east = DARBAR_X[0]
    # Raised floors for the two blocks.
    for name, ya, yb, mat in (('North block floor', 9.3, 24.0, m.floor_room), ('South block floor', -24.0, -9.3, m.paving)):
        b = MeshBuilder()
        b.box_between((x0, ya, 0.0), (east, yb, FLOOR), {'*': 0, '+z': 1})
        edge_y = ya if ya > 0 else yb
        path = [(east, edge_y), (x0, edge_y)] if ya > 0 else [(x0, edge_y), (east, edge_y)]
        b.sweep(path, kit.plinth_profile(FLOOR, 0.22), 0, False, 0.0)
        p.add(name, b, [m.stone, mat], c_ct)
    b = MeshBuilder()
    b.box_between((-33.2, -23.2, FLOOR + 0.002), (-19.3, -13.3, FLOOR + 0.012))
    p.add('Interrogation basalt floor', b, [m.floor_basalt], c_iq)
    b = MeshBuilder()
    b.box_between((-18.7, -23.2, FLOOR + 0.002), (-10.0, -13.3, FLOOR + 0.008))
    p.add('Waiting hall floor', b, [m.floor_room], c_iq)

    # North block walls: private chamber and ante-room.
    w = MeshBuilder()
    kit.wall(w, (-33.6, 23.6), (east, 23.6), FLOOR, ROOM_TOP - FLOOR, 0.8,
             (Opening(6.6, 2.6, 0.35, 3.0, 'jharokha'), Opening(16.1, 1.4, 1.2, 3.4, 'jali'),
              Opening(21.1, 1.4, 1.2, 3.4, 'jali')), -1, 0, 1)
    kit.wall(w, (-33.6, 13.0), (-33.6, 24.0), FLOOR, ROOM_TOP - FLOOR, 0.8,
             (Opening(5.2, 1.6, 1.1, 3.4, 'jali'),), -1, 0, 1)
    kit.wall(w, (-21.0, 13.3), (-21.0, 23.2), FLOOR, ROOM_TOP - FLOOR, 0.6,
             (Opening(2.9, 1.4, 0.0, 2.75, 'guard door'),), 1, 1, 1)
    kit.wall(w, (east, DARBAR_Y), (east, 24.0), FLOOR, ROOM_TOP - FLOOR, 0.8,
             (Opening(4.8, 1.8, 0.0, 3.0),), 1, 0, 1)
    kit.wall(w, (-34.0, 13.0), (-10.0, 13.0), FLOOR, ROOM_TOP - FLOOR, 0.6,
             (Opening(3.6, 1.6, 1.1, 3.4, 'jali'), Opening(9.6, 1.6, 1.1, 3.4, 'jali'),
              Opening(19.0, 1.8, 0.0, 3.0)), 1, 1, 1)
    p.add('Chamber block walls', w, [m.stone, m.plaster_room], c_ch)
    # South block walls: interrogation room and waiting hall.
    w = MeshBuilder()
    kit.wall(w, (-34.0, -23.6), (east, -23.6), FLOOR, ROOM_TOP - FLOOR, 0.8,
             (Opening(7.8, 1.8, 2.2, 3.9, 'jali'), Opening(20.0, 1.6, 0.0, 2.8)), 1, 0, 1)
    kit.wall(w, (-33.6, -23.2), (-33.6, -13.0), FLOOR, ROOM_TOP - FLOOR, 0.8,
             (Opening(2.2, 1.4, 1.1, 3.6, 'jali'), Opening(7.6, 1.4, 1.1, 3.6, 'jali')), -1, 0, 1)
    kit.wall(w, (-19.0, -23.2), (-19.0, -13.3), FLOOR, ROOM_TOP - FLOOR, 0.6,
             (Opening(8.0, 1.4, 0.0, 2.75, 'witness door'),), 1, 1, 1)
    kit.wall(w, (east, -23.2), (east, -DARBAR_Y), FLOOR, ROOM_TOP - FLOOR, 0.8, (), 1, 0, 1)
    kit.wall(w, (-34.0, -13.0), (-10.0, -13.0), FLOOR, ROOM_TOP - FLOOR, 0.6,
             (Opening(4.4, 1.6, 0.0, 3.0), Opening(8.6, 1.6, 1.2, 3.6, 'jali'), Opening(12.4, 1.6, 1.2, 3.6, 'jali'),
              Opening(19.6, 1.6, 2.3, 3.6, 'jali')), -1, 1, 1)
    p.add('Interrogation block walls', w, [m.stone, m.plaster_room], c_iq)
    # Courtyard west wall with a deep blind niche.
    w = MeshBuilder()
    kit.wall(w, (-33.6, -13.0), (-33.6, 13.0), 0.0, 4.6, 0.8, (Opening(13.0, 3.0, 0.6, 4.0, 'niche'),), -1, 0, 1)
    w.box_between((-34.0, -1.5, 0.6), (-33.85, 1.5, 4.0), 2)
    w.box_between((-34.0, -1.5, 0.0), (-33.2, 1.5, 0.6))
    p.add('Courtyard west wall and niche', w, [m.stone, m.plaster_court, m.recess], c_ct)
    p.frame(c_ct, (-33.15, 0.0), 0.6, 3.0, 3.4, 90, 'Courtyard niche frame')
    p.add('Niche lamp', kit.lamp_stand(1.2), [m.brass, m.flame], d, (-33.6, 0.0, 0.6))

    # Window screens and frames.
    for centre, z, width, height, yaw, name, coll in (
            ((-33.6, 18.2), FLOOR + 1.1, 1.6, 2.3, 90, 'Chamber river jali', c_ch),
            ((-30.4, 13.0), FLOOR + 1.1, 1.6, 2.3, 0, 'Chamber verandah jali', c_ch),
            ((-24.4, 13.0), FLOOR + 1.1, 1.6, 2.3, 0, 'Chamber verandah jali', c_ch),
            ((-17.5, 23.6), FLOOR + 1.2, 1.4, 2.2, 0, 'Ante-room river jali', c_ch),
            ((-12.5, 23.6), FLOOR + 1.2, 1.4, 2.2, 0, 'Ante-room river jali', c_ch),
            ((-26.2, -23.6), FLOOR + 2.2, 1.8, 1.7, 0, 'Interrogation high jali', c_iq),
            ((-33.6, -21.0), FLOOR + 1.1, 1.4, 2.5, 90, 'Interrogation river jali', c_iq),
            ((-33.6, -15.6), FLOOR + 1.1, 1.4, 2.5, 90, 'Interrogation river jali', c_iq),
            ((-25.6, -13.0), FLOOR + 1.2, 1.6, 2.4, 0, 'Interrogation courtyard jali', c_iq),
            ((-21.6, -13.0), FLOOR + 1.2, 1.6, 2.4, 0, 'Interrogation courtyard jali', c_iq),
            ((-14.4, -13.0), FLOOR + 2.3, 1.6, 1.3, 0, 'Waiting hall high jali', c_iq)):
        p.jali(coll, centre, z, width, height, yaw, 'rosette' if 'river' in name else 'star', name)
    # Doors.
    p.frame(c_ch, (-20.72, 16.2), FLOOR, 1.4, 2.75, 90, 'Guard door frame (ante-room side)')
    p.frame(c_ch, (-21.28, 16.2), FLOOR, 1.4, 2.75, -90, 'Guard door frame (chamber side)')
    p.door(c_ch, (-20.66, 15.5), 0.7, 2.75, 15, 'Guard door leaf (open)')
    p.door(c_ch, (-20.66, 16.9), 0.7, 2.75, -15, 'Guard door leaf (open)')
    p.frame(c_ch, (-15.0, 12.72), FLOOR, 1.8, 3.0, 180, 'Ante-room door frame')
    p.frame(c_ch, (east + 0.38, 18.8), FLOOR, 1.8, 3.0, 90, 'Ante-room court door frame')
    p.frame(c_iq, (-19.28, -15.2), FLOOR, 1.4, 2.75, -90, 'Witness door frame (interrogation side)')
    p.frame(c_iq, (-18.72, -15.2), FLOOR, 1.4, 2.75, 90, 'Witness door frame (waiting side)')
    p.door(c_iq, (-18.66, -15.9), 0.7, 2.75, 90, 'Witness door leaf (closed)')
    p.door(c_iq, (-18.66, -14.5), 0.7, 2.75, -90, 'Witness door leaf (closed)')
    p.frame(c_iq, (-29.6, -12.72), FLOOR, 1.6, 3.0, 180, 'Interrogation door frame')
    p.door(c_iq, (-30.4, -12.66), 0.8, 3.0, 100, 'Interrogation door leaf (open)')
    p.door(c_iq, (-28.8, -12.66), 0.8, 3.0, 80, 'Interrogation door leaf (open)')
    p.frame(c_iq, (-14.0, -23.22), FLOOR, 1.6, 2.8, 0, 'Witness entrance frame')
    p.door(c_iq, (-14.8, -23.3), 0.8, 2.8, 0, 'Witness entrance leaf (closed)')
    p.door(c_iq, (-13.2, -23.3), 0.8, 2.8, 180, 'Witness entrance leaf (closed)')
    moon = p.shared('Moonstone 1.1', lambda: kit.moonstone(1.1), [m.carved])
    p.instance('Moonstone threshold', moon, c_ct, (-15.0, 12.3, FLOOR), 180)
    p.instance('Moonstone threshold', moon, c_ct, (-29.6, -12.3, FLOOR), 0)

    # Witness privacy screen in the waiting hall.
    b = MeshBuilder()
    b.box_between((-17.05, -16.7, FLOOR), (-16.75, -13.3, FLOOR + 2.7))
    b.sweep(kit.rect_path(-17.05, -16.75, -16.7, -13.3), kit.cornice_profile(0.06, 0.14), 0, True, FLOOR + 2.7)
    b.sweep(kit.rect_path(-17.05, -16.75, -16.7, -13.3), kit.plinth_profile(0.25, 0.06), 0, True, FLOOR)
    for y0, y1 in ((-16.45, -15.15), (-14.85, -13.55)):
        for z0, z1 in ((FLOOR + 0.45, FLOOR + 1.45), (FLOOR + 1.65, FLOOR + 2.45)):
            for x in (-17.09, -16.71):
                b.box_between((x - 0.02, y0, z0), (x + 0.02, y1, z0 + 0.06), 1)
                b.box_between((x - 0.02, y0, z1 - 0.06), (x + 0.02, y1, z1), 1)
                b.box_between((x - 0.02, y0, z0), (x + 0.02, y0 + 0.06, z1), 1)
                b.box_between((x - 0.02, y1 - 0.06, z0), (x + 0.02, y1, z1), 1)
    p.add('Waiting hall privacy screen (blocks the witness door)', b, [m.carved, m.red], c_iq)
    rosette = p.shared('Lotus rosette 0.32', lambda: kit.lotus_rosette(0.32, 0.06), [m.carved])
    for y in (-15.8, -14.2):
        for z in (FLOOR + 0.95, FLOOR + 2.05):
            for x, yaw in ((-17.08, 0.0), (-16.72, 180.0)):
                obj = p.instance('Screen lotus medallion', rosette, c_iq, (x, y, z))
                obj.rotation_euler = (0.0, math.radians(90 if yaw == 0 else -90), 0.0)

    # Ceilings: smoked teak beams and planks under a stone roof slab.
    ceiling = MeshBuilder()
    roof = MeshBuilder()
    for (ax, bx, ay, by) in ((-33.2, -21.3, 13.3, 23.2), (-20.7, -10.0, 13.3, 23.2), (-33.2, -19.3, -23.2, -13.3),
                             (-18.7, -10.0, -23.2, -13.3)):
        ceiling.box_between((ax, ay, ROOM_TOP - 0.15), (bx, by, ROOM_TOP))
        span_x = bx - ax
        count = int(span_x / 0.9)
        for i in range(count + 1):
            x = ax + 0.25 + i * (span_x - 0.5) / count
            ceiling.box_between((x - 0.09, ay, ROOM_TOP - 0.42), (x + 0.09, by, ROOM_TOP - 0.15))
        ceiling.box_between((ax, ay, ROOM_TOP - 0.5), (bx, ay + 0.22, ROOM_TOP - 0.15))
        ceiling.box_between((ax, by - 0.22, ROOM_TOP - 0.5), (bx, by, ROOM_TOP - 0.15))
    p.add('Teak beam ceilings', ceiling, [m.dark_teak], c_ch)
    for ya, yb in ((12.7, 24.0), (-24.0, -12.7)):
        roof.box_between((x0, ya, ROOM_TOP), (east - 0.4, yb, ROOM_TOP + 0.3))
    for ya, yb in ((9.3, 12.7), (-12.7, -9.3)):
        roof.box_between((x0 + 0.8, ya, ROOM_TOP - 0.06), (east - 0.4, yb, ROOM_TOP + 0.24))
    for ya, yb in ((9.3, 24.0), (-24.0, -9.3)):
        roof.sweep(kit.rect_path(x0 - 0.05, east - 0.4, ya, yb), kit.cornice_profile(0.28, 0.34), 0, True, ROOM_TOP + 0.3)
        roof.sweep(kit.rect_path(x0 + 0.1, east - 0.5, ya + 0.15, yb - 0.15), kit.parapet_profile(0.9, 0.32), 0, True,
                   ROOM_TOP + 0.64)
    for y, flip in ((9.3, 1), (-9.3, -1)):
        path = [(east - 0.4, y), (x0 + 0.8, y)] if flip > 0 else [(x0 + 0.8, y), (east - 0.4, y)]
        roof.sweep(path, kit.chhajja_profile(1.0, 0.36, 0.1), 0, False, ROOM_TOP - 0.06)
    p.add('Private wing roofs, eaves and parapets', roof, [m.stone], 'Palace | Roofs & pavilions')

    # Courtyard verandahs: pillars, beams and steps down to the court.
    style = PillarStyle(ROOM_TOP - 0.06 - FLOOR - kit.BEAM_HEIGHT, 0.78, True, True, True)
    xs = (-31.4, -28.0, -24.6, -21.2, -17.8, -14.4, -11.0)
    for y in (-9.75, 9.75):
        for x in xs:
            p.pillar(style, c_ct, (x, y, FLOOR), 'Verandah stambha')
        z_top = FLOOR + style.height
        p.beam(c_ct, (-33.2, y), (xs[0], y), z_top)
        for a, b2 in zip(xs, xs[1:]):
            p.beam(c_ct, (a, y), (b2, y), z_top)
        p.beam(c_ct, (xs[-1], y), (east - 0.4, y), z_top)
        steps = MeshBuilder()
        yaw = -90 if y > 0 else 90
        steps.merge(kit.stairs(5.2, 0.15, 0.36, 4), Matrix.Rotation(math.radians(yaw), 4, 'Z'))
        p.add('Verandah steps to the court', steps, [m.stone], c_ct, (-22.9, y + (-0.45 if y > 0 else 0.45), 0.0))
    # Courtyard fountain basin and garden.
    b = MeshBuilder()
    rings = [kit.Section(0.0, 3.0, 8), kit.Section(0.12, 3.0, 8), kit.Section(0.12, 2.85, 8), kit.Section(0.5, 2.85, 8),
             kit.Section(0.5, 3.05, 8), kit.Section(0.62, 3.05, 8), kit.Section(0.62, 2.7, 8), kit.Section(0.3, 2.7, 8)]
    b.lathe(rings, kit.RING, 0, True, cap_bottom=False, cap_top=True)
    b.merge(kit.kalasha(1.3), Matrix.Translation((0, 0, 0.3)))
    b.lathe([kit.Section(0.3, 0.9, 0, kit.petals(16, 0.3)), kit.Section(0.36, 1.2, 0, kit.petals(16, 0.35)),
             kit.Section(0.4, 0.5)], kit.RING, 0, True)
    p.add('Courtyard lotus fountain basin', b, [m.carved], c_ct, (-21.6, 0.0, 0.0))
    water = MeshBuilder()
    water.lathe([kit.Section(0.46, 2.72, 8), kit.Section(0.46, 0.01, 8)], kit.RING, 0, False, False, False)
    p.add('Courtyard basin water', water, [m.still_water], c_ct, (-21.6, 0.0, 0.0))
    altar = p.shared('Tulsi vrindavan', kit.tulsi_vrindavan, [m.carved, m.recess])
    basil = p.shared('Tulsi bush', lambda: kit.bush(5, 0.62, 0.36), [m.bark, m.tulsi])
    for gx, gy in ((-29.5, -5.5), (-29.5, 5.5), (-13.5, -5.5), (-13.5, 5.5)):
        yaw = 0.0 if gy < 0 else 180.0
        p.instance('Tulsi vrindavan (holy basil altar)', altar, c_ct, (gx, gy, 0.0), yaw)
        p.instance('Tulsi bush', basil, c_ct, (gx, gy, 1.07), 37.0 * gx)

    # --- Dressing: private chamber -------------------------------------------------
    p.add('Chamber rug', kit.rug(4.8, 3.6), [m.rug_a], d, (-27.2, 18.0, FLOOR))
    p.add('Chamber gaddi mattress', kit.cushion((1.5, 2.6, 0.16), 0.15), [m.linen], d, (-32.3, 18.2, FLOOR))
    p.add('Chamber gaddi bolster', kit.bolster(2.4, 0.17), [m.indigo, m.brass], d, (-32.85, 18.2, FLOOR + 0.3), 90)
    for y in (17.1, 19.3):
        p.add('Chamber round cushion', kit.bolster(0.55, 0.16), [m.madder, m.brass], d, (-31.6, y, FLOOR + 0.3))
    p.add('Jharokha seat cushion', kit.cushion((2.5, 1.05, 0.1), 0.2), [m.indigo], d, (-27.0, 24.8, FLOOR + 0.35))
    p.add('Jharokha bolster', kit.bolster(1.0, 0.13), [m.ochre, m.brass], d, (-28.1, 24.8, FLOOR + 0.58), 90)
    table = p.add('Reading chowki (paper-reading spot)', kit.low_table(0.95, 0.62, 0.34), [m.teak], d,
                  (-27.0, 22.05, FLOOR))
    table['Story'] = 'Vikram folds the seventh statement and reads the first here, by the ghat window.'
    p.add('Reading floor cushion', kit.cushion((0.95, 0.75, 0.1), 0.2), [m.indigo], d, (-27.0, 21.25, FLOOR + 0.012))
    stand = p.shared('Lamp stand 1.4', lambda: kit.lamp_stand(1.4), [m.brass, m.flame])
    for x in (-29.6, -24.4):
        p.instance('Chamber lamp stand', stand, d, (x, 22.45, FLOOR))
    p.add('Chamber chest', kit.chest(1.1, 0.55, 0.55), [m.teak, m.brass], d, (-21.85, 21.4, FLOOR), 90)
    pot = p.shared('Matka', lambda: kit.matka(0.44), [m.clay])
    p.instance('Water matka', pot, d, (-22.0, 14.2, FLOOR + 0.42))
    p.add('Matka stand', kit.low_table(0.5, 0.5, 0.42), [m.teak], d, (-22.0, 14.2, FLOOR))
    p.instance('Chamber hanging lamp', p.shared('Hanging lamp 1.6', lambda: kit.hanging_lamp(1.6), [m.brass, m.flame]),
               d, (-27.2, 18.0, ROOM_TOP - 0.42))
    p.add('Ante-room guard bench', kit.bench(2.6), [m.carved], d, (-15.0, 13.75, FLOOR), 0)
    p.instance('Ante-room lamp stand', stand, d, (-11.0, 14.2, FLOOR))
    diya = p.shared('Diya', lambda: kit.diya(1.0), [m.clay, m.flame])
    niche = p.shared('Lamp niche', _lamp_niche, [m.carved, m.recess])
    for loc, yaw in (((-33.18, 15.2, FLOOR + 1.6), -90), ((-33.18, 21.4, FLOOR + 1.6), -90),
                     ((-27.2, 13.32, FLOOR + 1.6), 0), ((-21.32, 20.8, FLOOR + 1.6), 90),
                     ((-33.18, -18.2, FLOOR + 1.7), -90), ((-26.2, -23.18, FLOOR + 1.6), 180),
                     ((-10.42, -19.0, FLOOR + 1.6), 90), ((-18.68, -21.0, FLOOR + 1.6), -90)):
        p.instance('Lamp niche', niche, d, loc, yaw)
        offset = Vector((0.0, 0.0, 0.0))
        p.instance('Niche diya', diya, d, (loc[0] + offset.x, loc[1] + offset.y, loc[2] + 0.06), yaw)

    # --- Dressing: interrogation room and waiting hall ------------------------------
    p.add('Clerk takht (writing platform)', kit.stepped_platform(1.9, 4.0, 0.35), [m.teak], d, (-32.25, -18.6, FLOOR))
    p.add('Clerk takht dhurrie', kit.rug(1.8, 3.9), [m.rug_b], d, (-32.25, -18.6, FLOOR + 0.35))
    p.add('Clerk cushion', kit.cushion((0.62, 0.55, 0.08)), [m.madder], d, (-32.55, -18.6, FLOOR + 0.36))
    desk = p.add('Clerk writing desk (मुंशी का लेखन-स्थान)', kit.writing_desk(), [m.teak], d,
                 (-31.95, -18.6, FLOOR + 0.36), -90)
    desk['Story'] = 'The clerk records each witness from here, facing the chalk floor.'
    p.add('Clerk bolster', kit.bolster(1.6, 0.13), [m.indigo, m.brass], d, (-33.0, -18.6, FLOOR + 0.5), 90)
    p.add('Records chest', kit.chest(1.2, 0.55, 0.6), [m.teak, m.brass], d, (-32.6, -21.9, FLOOR), 90)
    bundles = MeshBuilder()
    for i, (bx, by, bz) in enumerate(((0, 0, 0), (0.05, 0.42, 0), (0.0, 0.2, 0.17), (-0.02, -0.4, 0))):
        bundles.box((bx, by, bz + 0.085), (0.42, 0.38, 0.17), i % 2)
    p.add('Cloth-wrapped record bundles', bundles, [m.madder, m.ochre], d, (-32.6, -21.9, FLOOR + 0.62))
    for x in (-29.8, -22.6):
        p.instance('Interrogation lamp stand', stand, d, (x, -22.6, FLOOR))
    p.add("Vikram's floor seat (interrogation)", kit.cushion((1.4, 0.9, 0.12), 0.12), [m.indigo], d,
          (-26.2, -22.45, FLOOR + 0.012))
    p.add('Waiting bench (east wall)', kit.bench(6.4, 0.48, 0.45), [m.carved], d, (-10.55, -19.4, FLOOR), 90)
    p.add('Waiting bench (south wall)', kit.bench(5.0, 0.48, 0.45), [m.carved], d, (-15.0, -22.72, FLOOR), 0)
    p.instance('Waiting hall matka', pot, d, (-18.1, -22.6, FLOOR + 0.42))
    p.add('Waiting matka stand', kit.low_table(0.5, 0.5, 0.42), [m.teak], d, (-18.1, -22.6, FLOOR))
    p.instance('Waiting hall lamp stand', stand, d, (-11.0, -14.0, FLOOR))


def _lamp_niche() -> MeshBuilder:
    """Wall-mounted lamp shelf with a pointed backing panel, facing -Y."""
    b = MeshBuilder()
    b.box((0, -0.07, 0.0), (0.42, 0.16, 0.06), 0)
    b.box((0, -0.03, 0.27), (0.36, 0.04, 0.5), 1)
    outline = [(-0.25, 0.0)] + [(0.25 * math.cos(math.pi - math.pi * i / 10), 0.42 + 0.22 * math.sin(math.pi * i / 10))
                                for i in range(11)] + [(0.25, 0.0)]
    frame = MeshBuilder()
    frame.prism([(u, v) for u, v in outline], 0.03)
    b.merge(frame, Matrix.Translation((0, -0.02, 0.0)) @ Matrix.Rotation(math.radians(90), 4, 'Z'))
    return b


# ---------------------------------------------------------------------------
# Ghat window bay (jharokha) and river façade pavilion
# ---------------------------------------------------------------------------

def jharokha(p: Palace) -> None:
    m = p.m
    c = 'Palace | Private chamber (निजी कक्ष)'
    cx = world.JHAROKHA_LOCAL[0]
    y_wall = 24.0
    depth = 1.6
    half = 1.6
    floor_z = FLOOR + 0.35
    b = MeshBuilder()
    b.box_between((cx - half, y_wall - 0.8, floor_z - 0.25), (cx + half, y_wall + depth, floor_z), {'*': 0, '+z': 1})
    b.sweep([(cx + half, y_wall), (cx + half, y_wall + depth), (cx - half, y_wall + depth), (cx - half, y_wall)],
            kit.cornice_profile(0.12, 0.25), 0, False, floor_z - 0.25)
    # Corbel brackets stepping down into the bastion.
    for x in (cx - 1.1, cx, cx + 1.1):
        corbel = [(0.0, 0.0), (0.0, -1.6), (0.25, -1.45), (0.4, -1.1), (0.7, -0.85), (0.95, -0.55), (1.3, -0.35),
                  (1.55, -0.15), (1.6, 0.0)]
        piece = MeshBuilder()
        piece.prism([(u, v) for u, v in corbel], 0.32)
        b.merge(piece, Matrix.Translation((x - 0.16, y_wall, floor_z - 0.25)))
        b.merge(kit.kalasha(0.35), Matrix.Translation((x, y_wall + 0.2, floor_z - 1.95)) @
                Matrix.Rotation(math.pi, 4, 'X'))
    # Parapet under the openings: low pierced panels on three sides.
    rail_h = 0.42
    pil_h = 2.15
    for sx in (-1, 1):
        for y in (y_wall + 0.12, y_wall + depth - 0.12):
            b.merge(kit.slender_pillar(pil_h, 0.075), Matrix.Translation((cx + sx * (half - 0.12), y, floor_z + rail_h)))
    for sx in (-0.42, 0.42):
        b.merge(kit.slender_pillar(pil_h, 0.06), Matrix.Translation((cx + sx * 1.9, y_wall + depth - 0.12, floor_z + rail_h)))
    for lo, hi in (((cx - half, y_wall + depth - 0.18), (cx + half, y_wall + depth)),
                   ((cx - half, y_wall), (cx - half + 0.18, y_wall + depth)),
                   ((cx + half - 0.18, y_wall), (cx + half, y_wall + depth))):
        b.box_between((lo[0], lo[1], floor_z + rail_h - 0.06), (hi[0], hi[1], floor_z + rail_h))
    top = floor_z + rail_h + pil_h
    b.box_between((cx - half, y_wall - 0.05, top), (cx + half, y_wall + depth, top + 0.18))
    b.sweep([(cx + half, y_wall), (cx + half, y_wall + depth), (cx - half, y_wall + depth), (cx - half, y_wall)],
            kit.chhajja_profile(0.75, 0.3, 0.09), 0, False, top + 0.18)
    roof = kit.shala_roof(2 * half + 0.2, depth + 0.3, 1.1, 0.5, True)
    b.merge(roof, Matrix.Translation((cx, y_wall + depth / 2, top + 0.2)) @ Matrix.Rotation(math.radians(90), 4, 'Z'),
            mat_offset=0)
    bay = p.add('Ghat window bay (jharokha)', b, [m.carved, m.floor_room], c)
    bay['Story'] = 'Fixed window camera: five ghat steps in the morning, three in the evening.'
    p.jali(c, (cx, y_wall + depth - 0.1), floor_z, 2 * half - 0.3, rail_h - 0.06, 0, 'star', 'Jharokha front rail jali')
    for sx in (-1, 1):
        p.jali(c, (cx + sx * (half - 0.1), y_wall + depth / 2), floor_z, depth - 0.2, rail_h - 0.06, 90, 'star',
               'Jharokha side rail jali')
    p.frame(c, (cx, y_wall - 0.82), FLOOR + 0.35, 2.6, 2.65, 0, 'Jharokha opening frame (room side)')
    # Curtain tie-backs: light cotton drapes gathered at the sides of the bay opening.
    for sx in (-1, 1):
        drape = MeshBuilder()

        def cloth(u: float, v: float, s: int = sx) -> tuple[float, float, float]:
            z = floor_z + 0.1 + (1 - u) * 2.6
            gather = 0.35 + 0.4 * abs(u - 0.45)
            x = s * (1.25 + gather * v * 0.4)
            fold = 0.05 * math.sin(v * math.pi * 6)
            return (x, -0.86 + fold, z)

        drape.grid_surface(10, 12, cloth, 0, True)
        p.add('Jharokha drape', drape, [m.linen], 'Palace | Dressing', (cx, y_wall, 0.0))

    # Upper pavilion over the chamber, its barrel gable facing the river.
    roofs = 'Palace | Roofs & pavilions'
    base = ROOM_TOP + 0.64
    style = PillarStyle(3.0, 0.6, False, True, False)
    for x in (-32.0, -28.67, -25.33, -22.0):
        for y in (15.0, 18.8, 22.6):
            p.pillar(style, roofs, (x, y, base), 'Upper pavilion pillar')
    for y in (15.0, 18.8, 22.6):
        for a, b2 in ((-32.0, -28.67), (-28.67, -25.33), (-25.33, -22.0)):
            p.beam(roofs, (a, y), (b2, y), base + 3.0)
    pb = MeshBuilder()
    pb.box_between((-32.6, 14.4, base - 0.05), (-21.4, 23.2, base + 0.05))
    pb.box_between((-32.6, 14.4, base + 3.56), (-21.4, 23.2, base + 3.8))
    pb.sweep(kit.rect_path(-32.6, -21.4, 14.4, 23.2), kit.chhajja_profile(0.9, 0.32, 0.1), 0, True, base + 3.8)
    p.add('Upper pavilion floor and entablature', pb, [m.stone], roofs)
    p.add('Upper pavilion shala roof (river gable)', kit.shala_roof(9.4, 11.6, 3.6, 0.8), [m.stone, m.recess], roofs,
          (-27.0, 18.8, base + 3.8), 90)
    ribs = kit.barrel_ribs(9.0, 11.6, 3.6, 0.25)
    p.add('Upper pavilion vault ribs', ribs, [m.dark_teak], roofs, (-27.0, 18.8, base + 3.8), 90)
    # Chhatris on the private wing terraces.
    mesh = p.shared('Chhatri 2.20', lambda: kit.chhatri(2.2, 2.0), [m.carved])
    for loc in ((-12.5, 21.0), (-31.0, -21.0), (-12.5, -21.0), (-12.5, 15.8)):
        p.instance('Terrace chhatri', mesh, roofs, (loc[0], loc[1], ROOM_TOP + 0.64))
    for loc in ((x - 0.0, y) for x, y in ((-7.6, 12.0), (-7.6, -12.0), (28.6, 12.0), (28.6, -12.0))):
        p.instance('Darbar roof chhatri', mesh, roofs, (loc[0], loc[1], DARBAR_ROOF + 0.32))


# ---------------------------------------------------------------------------
# Forecourt, gate and torana
# ---------------------------------------------------------------------------

def forecourt(p: Palace) -> None:
    m = p.m
    c = 'Palace | Forecourt & public gate'
    x1 = world.PALACE_PLINTH_LOCAL[1]
    tor = p.add('Torana gateway', kit.torana(5.6, 6.0), [m.carved, m.red], c, (42.5, 0.0, 0.0), 90)
    tor['Story'] = 'Public approach to the open darbar.'
    gx0, gx1 = x1 - 3.2, x1
    b = MeshBuilder()
    for sy in (-1, 1):
        ya, yb = (3.6, 9.0) if sy > 0 else (-9.0, -3.6)
        b.box_between((gx0, ya, 0.0), (gx1, yb, 9.0))
        b.sweep(kit.rect_path(gx0, gx1, ya, yb), kit.plinth_profile(1.2, 0.3), 0, True, 0.0)
        b.sweep(kit.rect_path(gx0, gx1, ya, yb), kit.chhajja_profile(0.9, 0.3, 0.1), 0, True, 6.4)
        b.sweep(kit.rect_path(gx0, gx1, ya, yb), kit.cornice_profile(0.3, 0.4), 0, True, 9.0)
        b.merge(kit.merlons(yb - ya, 0.95, 0.52, 0.6, 0.5), Matrix.Translation((gx1 - 0.25, ya, 9.4)) @
                Matrix.Rotation(math.radians(90), 4, 'Z'))
    b.box_between((gx0, -3.6, 6.0), (gx1, 3.6, 7.8))
    b.sweep([(gx1, -3.6), (gx1, 3.6)], kit.cornice_profile(0.25, 0.3), 0, False, 7.8)
    p.add('Public gatehouse towers', b, [m.stone], c)
    # Dress the towers: pilastered bays with shrine niches below the chhajja, a blind arcade above,
    # and a carved red lintel panel with lotus medallions over the gate.
    d = MeshBuilder()
    face_h = 6.4 - 1.2 - 0.25
    upper_z, upper_h = 6.4 + 0.42, 9.0 - 6.4 - 0.42 - 0.2
    for sy in (-1, 1):
        near, far = 3.6 * sy, 9.0 * sy
        inner = near + 0.45 * sy
        lo, hi = min(inner, far), max(inner, far)
        # Town face (+X) runs south to north; court face (-X) runs north to south.
        d.merge(kit.facade_bays(hi - lo, face_h, 2), Matrix.Translation((gx1, lo, 1.2)) @
                Matrix.Rotation(math.radians(90), 4, 'Z'))
        d.merge(kit.facade_bays(hi - lo, face_h, 2), Matrix.Translation((gx0, hi, 1.2)) @
                Matrix.Rotation(math.radians(-90), 4, 'Z'))
        d.merge(kit.blind_arcade(abs(far - near) - 0.3, upper_h), Matrix.Translation((gx1, min(near, far) + 0.15, upper_z)) @
                Matrix.Rotation(math.radians(90), 4, 'Z'))
        d.merge(kit.blind_arcade(abs(far - near) - 0.3, upper_h), Matrix.Translation((gx0, max(near, far) - 0.15, upper_z)) @
                Matrix.Rotation(math.radians(-90), 4, 'Z'))
        # Outer flank, above the enclosure wall.
        flank = (Matrix.Translation((gx1 - 0.15, far, upper_z)) @ Matrix.Rotation(math.radians(180), 4, 'Z')
                 if sy > 0 else Matrix.Translation((gx0 + 0.15, far, upper_z)))
        d.merge(kit.blind_arcade(gx1 - gx0 - 0.3, upper_h), flank)
    d.box_between((gx1, -3.3, 6.62), (gx1 + 0.07, 3.3, 7.62), 2)
    d.box_between((gx1, -3.4, 6.54), (gx1 + 0.12, 3.4, 6.62))
    d.box_between((gx1, -3.4, 7.62), (gx1 + 0.12, 3.4, 7.72))
    for k in range(5):
        d.merge(kit.lotus_rosette(0.34, 0.1), Matrix.Translation((gx1 + 0.07, -2.6 + k * 1.3, 7.12)) @
                Matrix.Rotation(math.radians(-90), 4, 'Y'))
    p.add('Gatehouse carving (pilasters, niches, arcade, lintel)', d, [m.carved, m.recess, m.red], c)
    p.frame(c, (gx1 + 0.02, 0.0), 0.0, 7.2, 6.0, 90, 'Gate frame')
    p.frame(c, (gx0 - 0.02, 0.0), 0.0, 7.2, 6.0, -90, 'Gate frame (inner)')
    for sy in (-1, 1):
        p.door(c, (gx0 + 0.3, sy * 3.55), 3.5, 5.8, -90 * sy + 70 * sy, 'Public gate leaf (open)', 0.0)
    roofs = 'Palace | Roofs & pavilions'
    style = PillarStyle(2.8, 0.6, False, True, False)
    for x in (gx0 + 0.4, gx1 - 0.4):
        for y in (-7.8, -2.6, 2.6, 7.8):
            p.pillar(style, roofs, (x, y, 9.0), 'Gate pavilion pillar')
    pb = MeshBuilder()
    pb.box_between((gx0 - 0.2, -8.6, 11.8), (gx1 + 0.2, 8.6, 12.1))
    p.add('Gate pavilion entablature', pb, [m.stone], roofs)
    p.add('Gate pavilion shala roof', kit.shala_roof(17.6, 4.4, 2.6, 0.8), [m.stone, m.recess], roofs,
          ((gx0 + gx1) / 2, 0.0, 12.1), 90)
    stairs = MeshBuilder()
    stairs.merge(kit.stairs(10.0, 0.167, 0.42, 12), Matrix.Translation((0, 0, 0)))
    for sy in (-1, 1):
        stairs.box_between((0.0, sy * 5.0 - 0.4, 0.0), (12 * 0.42, sy * 5.0 + 0.4, 2.6))
    p.add('Public stair to the upper town', stairs, [m.stone], c, (x1, 0.0, -2.0))
    pillar = p.shared('Victory pillar 11', lambda: kit.victory_pillar(11.0), [m.red])
    p.instance('Victory pillar (jaya-stambha)', pillar, c, (37.0, 13.0, 0.0))
    stone_lamp = p.shared('Stone lamp pillar', _stone_lamp_pillar, [m.carved])
    for y in (-6.5, 6.5):
        p.instance('Stone lamp pillar (deepastambha)', stone_lamp, c, (34.6, y, 0.0))
    shrub = p.shared('Forecourt tree', lambda: kit.tree(21, 7.5, 3.6), [m.bark, m.leaves])
    for loc in ((40.0, -17.0), (24.0, 19.5), (8.0, 19.5), (12.0, -19.5), (28.0, -19.5)):
        planter = MeshBuilder()
        planter.lathe([kit.Section(0.0, 1.3, 8), kit.Section(0.6, 1.3, 8), kit.Section(0.6, 1.45, 8),
                       kit.Section(0.72, 1.45, 8), kit.Section(0.72, 1.2, 8)], 32, 0, True)
        p.add('Tree platform', planter, [m.carved], c, (loc[0], loc[1], 0.0))
        p.instance('Court tree (neem stand-in)', shrub, c, (loc[0], loc[1], 0.6))


def _stone_lamp_pillar() -> MeshBuilder:
    b = MeshBuilder()
    rings = kit.profile_rings([(0.0, 0.6), (0.3, 0.6), (0.3, 0.45), (0.5, 0.45)], 4)
    rings += [kit.Section(0.5, 0.3, 8), kit.Section(5.6, 0.22, 8), kit.Section(5.8, 0.38), kit.Section(6.0, 0.25)]
    b.lathe(rings, kit.RING, 0, True)
    for k in range(6):
        z = 1.4 + k * 0.75
        for i in range(8):
            a = 2 * math.pi * (i + 0.5 * (k % 2)) / 8
            r = 0.3 - k * 0.012
            b.box((r * math.cos(a), r * math.sin(a), z), (0.16, 0.16, 0.06))
    b.merge(kit.kalasha(0.6), Matrix.Translation((0, 0, 6.0)))
    return b


# ---------------------------------------------------------------------------
# Story marks, cameras, light and time of day
# ---------------------------------------------------------------------------

def flags(p: Palace) -> None:
    """Saffron pennants on the highest roofs, flying with the river wind."""
    m = p.m
    saffron = mats.cloth('Palace | saffron flag cloth', (0.78, 0.36, 0.06), (0.86, 0.62, 0.22), (0.55, 0.20, 0.04), 30)
    tops = [o for o in p.root.all_objects if o.name.startswith(('Judgment bay stepped roof', 'Tower chhatri',
                                                                  'Gate pavilion shala roof'))]
    for i, obj in enumerate(tops):
        height = max(v[2] for v in obj.bound_box) * obj.scale.z
        pole = 4.0 if obj.name.startswith('Judgment') else 2.6
        mesh = p.shared(f'Flag {pole}', lambda pl=pole: kit.flag(pl, pl * 0.55, pl * 0.3, 3), [m.brass, saffron])
        x, y, z = obj.location
        if obj.name.startswith('Gate'):
            for dy in (-8.6, 8.6):
                p.instance('Saffron pennant (dhvaja)', mesh, 'Palace | Roofs & pavilions', (x, y + dy, z + 1.6), 150)
            continue
        p.instance('Saffron pennant (dhvaja)', mesh, 'Palace | Roofs & pavilions', (x, y, z + height - 0.2), 150 + i * 4)


def story_marks(p: Palace) -> dict[str, bpy.types.Object]:
    c = 'Palace | Story marks'
    marks: dict[str, bpy.types.Object] = {}

    def mark(key: str, name: str, loc: tuple[float, float, float], yaw: float = 0.0, display: str = 'SINGLE_ARROW',
             size: float = 0.6, **props: object) -> None:
        obj = p.kit.empty(f'MARK | {name}', c, loc, yaw, display, size)
        for k, v in props.items():
            obj[k] = v
        marks[key] = obj

    cx = world.JHAROKHA_LOCAL[0]
    mark('reading', 'Chamber — Vikram reads statements (by the ghat window)', (cx, 21.25, FLOOR + 0.1), 90)
    mark('guard_door', 'Chamber — guard speaks from the door', (-21.0, 16.2, FLOOR), 180)
    mark('chalk', 'Interrogation — empty floor for the chalk map', (*CHALK_CENTRE, FLOOR + 0.012), 0, 'CUBE', 1.0,
         half_size_x=CHALK_HALF[0], half_size_y=CHALK_HALF[1])
    marks['chalk'].scale = (CHALK_HALF[0], CHALK_HALF[1], 0.02)
    mark('clerk_iq', 'Interrogation — clerk writes (takht)', (-32.55, -18.6, FLOOR + 0.36), -90 + 180)
    mark('vikram_iq', 'Interrogation — Vikram stands (guess)', (-23.2, -16.0, FLOOR), 200)
    mark('witness_door', 'Interrogation — witness enters', (-19.3, -15.2, FLOOR), 180)
    mark('next_witness', 'Waiting hall — next witness waits', (-11.0, -20.6, FLOOR + 0.45), 180)
    mark('throne', 'Darbar — Vikram on the throne', (-7.2, 0.0, PLATFORM_TOP + 0.5), 0)
    mark('nandu', 'Darbar — Nandu stands (faces the throne)', (2.6, 0.0, FLOOR), 180)
    mark('nandu_hands', "Darbar — Nandu's bound hands", (2.95, 0.0, FLOOR + 1.05), 0, 'SPHERE', 0.12)
    mark('daughter', 'Darbar — daughter enters (public steps)', (31.2, 0.4, FLOOR), 180)
    mark('clerk_darbar', 'Darbar — clerk writes beside the platform', (-0.6, -6.9, FLOOR), 90)
    mark('crowd', 'Darbar — crowd standing zone', (18.5, 0.0, FLOOR + 0.9), 0, 'CUBE', 1.0)
    marks['crowd'].scale = (10.5, 12.5, 0.9)
    mark('sc04_origin', 'Interrogation — SC04 staging origin (approximate)', (*CHALK_CENTRE, FLOOR), 180, 'ARROWS', 1.0)
    marks['sc04_origin']['Note'] = ('Link the SC04 performance scene here: SC04 +Y (back wall) maps to the room '
                                    'south wall, SC04 +X (clerk side) maps to the takht side.')
    # Daughter's path from the public steps to Nandu.
    curve = bpy.data.curves.new('PATH | Darbar — daughter to Nandu', 'CURVE')
    curve.dimensions = '3D'
    spline = curve.splines.new('POLY')
    pts = [(31.2, 0.4), (26.0, -1.3), (20.0, 1.2), (14.0, -0.8), (8.0, 0.9), (3.4, 0.15)]
    spline.points.add(len(pts) - 1)
    for item, (x, y) in zip(spline.points, pts):
        item.co = (x, y, FLOOR + 0.02, 1.0)
    path = bpy.data.objects.new('PATH | Darbar — daughter to Nandu', curve)
    p.kit.collection(c).objects.link(path)
    path.parent = p.anchor
    marks['daughter_path'] = path
    return marks


def aim_camera(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat('-Z', 'Y').to_euler()


def cameras(p: Palace) -> dict[str, bpy.types.Object]:
    c = 'Palace | Cameras'
    cams: dict[str, bpy.types.Object] = {}

    def cam(key: str, name: str, loc: tuple[float, float, float], target: tuple[float, float, float], lens: float,
            local: bool = True, note: str = '') -> None:
        data = bpy.data.cameras.new(name)
        data.lens = lens
        data.sensor_width = 36
        data.clip_start = 0.05
        data.clip_end = 2000
        obj = bpy.data.objects.new(name, data)
        p.kit.collection(c).objects.link(obj)
        if local:
            obj.location = loc
            aim_camera(obj, Vector(target))
            obj.parent = p.anchor
        else:
            obj.location = loc
            aim_camera(obj, Vector(target))
        if note:
            obj['Story'] = note
        cams[key] = obj

    ghat_target = Vector(world.world_to_palace((world.GHAT_CENTER_X, world.step_front_y(3), world.step_top_z(3))))
    cx = world.JHAROKHA_LOCAL[0]
    cam('window', 'CAM | Chamber window — ghat steps (fixed)', (cx + 0.35, 20.9, FLOOR + 1.9),
        tuple(ghat_target + Vector((0.0, 0.0, 6.5))), 30,
        note='Same camera, frame 1 morning: five dry steps; frame 2 evening: three dry steps.')
    cam('window_tele', 'CAM | Chamber window — ghat steps (close)', (cx, 23.7, FLOOR + 1.55),
        tuple(ghat_target + Vector((0.0, 0.0, 1.0))), 105, note='Tighter check on the step count.')
    cam('guard', 'CAM | Chamber — guard at the door', (-27.6, 22.0, FLOOR + 1.25), (-20.9, 16.2, FLOOR + 1.6), 30)
    cam('chamber_wide', 'CAM | Chamber — wide to the ghat window', (-21.9, 13.9, FLOOR + 2.0), (-28.0, 23.5, FLOOR + 1.6), 18)
    cam('iq_wide', 'CAM | Interrogation — wide over the chalk floor', (-19.9, -13.85, FLOOR + 3.4),
        (-27.0, -18.6, FLOOR + 0.4), 18)
    cam('iq_top', 'CAM | Interrogation — overhead chalk floor', (CHALK_CENTRE[0], CHALK_CENTRE[1], FLOOR + 4.6),
        (CHALK_CENTRE[0], CHALK_CENTRE[1] + 0.001, FLOOR), 22)
    cam('waiting', 'CAM | Waiting hall — next witness outside', (-11.2, -14.1, FLOOR + 1.55), (-18.0, -18.8, FLOOR + 1.0), 20)
    cam('darbar_story', "CAM | Darbar — daughter's entrance to Nandu's hands", (-3.7, -2.3, PLATFORM_TOP + 1.25),
        (14.0, 0.4, FLOOR + 1.05), 28, note='Clear line from the public steps down the nave to the mark for the hands.')
    cam('darbar_wide', 'CAM | Darbar — wide toward the throne', (29.6, 0.0, FLOOR + 1.75), (-7.0, 0.0, FLOOR + 2.9), 22)
    cam('darbar_aisle', 'CAM | Darbar — from the side aisle', (24.0, -11.2, FLOOR + 2.2), (0.0, 1.0, FLOOR + 2.0), 24)
    cam('darbar_low', "CAM | Darbar — daughter's eye line", (22.0, 1.4, FLOOR + 0.95), (2.6, 0.0, FLOOR + 1.1), 32)
    cam('courtyard', 'CAM | Courtyard — verandahs and throne jali', (-31.8, -7.6, 1.7), (-12.0, 3.0, 2.6), 18)
    cam('gate', 'CAM | Exterior — public gate and torana', (74.0, -10.0, -0.3), (44.0, 0.0, 5.5), 24)
    jw = world.palace_to_world((cx + 14.0, 12.0, 4.0))
    flank_top = world.QUAY_Z + 0.9
    cam('from_ghat', 'CAM | Exterior — palace from the ghat bastion', (world.GHAT_HALF_WIDTH + 2.4, -10.6, flank_top + 1.6),
        (jw[0], jw[1], jw[2] + 1.0), 28, local=False,
        note='Hero view: the palace on its river bastion, seen from the riverside end of the ghat flank.')
    cam('from_river', 'CAM | Exterior — palace from the river', (6.0, -30.0, world.MORNING_WATER_Z + 1.4),
        (jw[0], jw[1], jw[2] + 2.0), 24, local=False, note='Boat-level view across the bend.')
    cam('aerial', 'CAM | Exterior — aerial map (palace, river bend, ghat)', (-70.0, 58.0, 82.0), (48.0, -24.0, 2.0), 30,
        local=False)
    return cams


def lighting(p: Palace, water: bpy.types.Object) -> dict[str, object]:
    scene = p.scene
    world_data = bpy.data.worlds.new('Chapter 1 sky')
    scene.world = world_data
    nt = world_data.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    sky = nt.nodes.new('ShaderNodeTexSky')
    sky.sky_type = 'MULTIPLE_SCATTERING'
    sky.sun_disc = False
    sky.sun_size = math.radians(0.8)
    sky.altitude = 120
    sky.air_density = 1.2
    sky.aerosol_density = 2.2
    nt.links.new(sky.outputs[0], bg.inputs['Color'])
    nt.links.new(bg.outputs[0], out.inputs['Surface'])
    sun_data = bpy.data.lights.new('Sun', 'SUN')
    sun_data.angle = math.radians(1.2)
    sun = bpy.data.objects.new('LIGHT | Sun (keyed: morning / evening)', sun_data)
    p.kit.collection('Palace | Lights').objects.link(sun)

    def sun_dir(azimuth: float, elevation: float) -> Vector:
        a, e = math.radians(azimuth), math.radians(elevation)
        return Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))

    states = {
        MORNING: dict(az=104.0, el=24.0, sun=3.2, color=(1.0, 0.88, 0.74), sky=0.16, water=world.MORNING_WATER_Z, lit=0.0,
                      exposure=-0.6),
        EVENING: dict(az=248.0, el=4.5, sun=2.0, color=(1.0, 0.50, 0.24), sky=0.12, water=world.EVENING_WATER_Z, lit=1.0,
                      exposure=-0.2),
    }
    flame_lit = p.m.flame.node_tree.nodes['Lamps lit']
    wet = bpy.data.materials['Ghat | river stone, wet line and silt'].node_tree.nodes['Water level']
    for frame, s in states.items():
        scene.frame_set(frame)
        d = sun_dir(s['az'], s['el'])
        sun.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        sun.keyframe_insert('rotation_euler', frame=frame)
        sun_data.energy = s['sun']
        sun_data.color = s['color']
        sun_data.keyframe_insert('energy', frame=frame)
        sun_data.keyframe_insert('color', frame=frame)
        sky.sun_rotation = math.radians(s['az'])
        sky.sun_elevation = math.radians(s['el'])
        sky.keyframe_insert('sun_rotation', frame=frame)
        sky.keyframe_insert('sun_elevation', frame=frame)
        bg.inputs['Strength'].default_value = s['sky']
        bg.inputs['Strength'].keyframe_insert('default_value', frame=frame)
        water.location.z = s['water']
        water.keyframe_insert('location', index=2, frame=frame)
        wet.outputs[0].default_value = s['water']
        wet.outputs[0].keyframe_insert('default_value', frame=frame)
        flame_lit.outputs[0].default_value = s['lit']
        flame_lit.outputs[0].keyframe_insert('default_value', frame=frame)
        scene.view_settings.exposure = s['exposure']
        scene.view_settings.keyframe_insert('exposure', frame=frame)
    for datablock in (sun, sun_data, world_data, water, p.m.flame, bpy.data.materials['Ghat | river stone, wet line and silt'],
                      scene):
        anim = getattr(datablock, 'animation_data', None)
        trees = [anim] if anim else []
        tree = getattr(datablock, 'node_tree', None)
        if tree is not None and tree.animation_data:
            trees.append(tree.animation_data)
        for item in trees:
            if item.action:
                _constant(item.action)
    marker = scene.timeline_markers.new('MORNING — 5 ghat steps dry', frame=MORNING)
    marker.camera = None
    scene.timeline_markers.new('EVENING — 3 ghat steps dry, lamps lit', frame=EVENING)

    # Motivated lamp light and soft interior fills (evening lamps are keyed on).
    lights = p.kit.collection('Palace | Lights')

    def point(name: str, loc: tuple[float, float, float], energy: float, radius: float = 0.05,
              color: tuple[float, float, float] = (1.0, 0.55, 0.22), keyed: bool = True) -> None:
        data = bpy.data.lights.new(name, 'POINT')
        data.energy = energy
        data.color = color
        data.shadow_soft_size = radius
        obj = bpy.data.objects.new(name, data)
        lights.objects.link(obj)
        obj.location = loc
        obj.parent = p.anchor
        if keyed:
            for frame, on in ((MORNING, 0.0), (EVENING, 1.0)):
                data.energy = energy * on
                data.keyframe_insert('energy', frame=frame)
            _constant(data.animation_data.action)

    def area(name: str, loc: tuple[float, float, float], target: tuple[float, float, float], energy: float,
             size: float, color: tuple[float, float, float], evening: float) -> None:
        data = bpy.data.lights.new(name, 'AREA')
        data.shape = 'DISK'
        data.size = size
        data.color = color
        obj = bpy.data.objects.new(name, data)
        lights.objects.link(obj)
        obj.location = loc
        aim_camera(obj, Vector(target))
        obj.parent = p.anchor
        for frame, scale in ((MORNING, 1.0), (EVENING, evening)):
            data.energy = energy * scale
            data.keyframe_insert('energy', frame=frame)
        _constant(data.animation_data.action)

    cx = world.JHAROKHA_LOCAL[0]
    for x in (-29.6, -24.4):
        point('LAMP | Chamber stand', (x, 22.45, FLOOR + 1.52), 18.0)
    point('LAMP | Chamber hanging', (-27.2, 18.0, ROOM_TOP - 2.1), 30.0, 0.1)
    for loc in ((-33.0, 15.2, FLOOR + 1.72), (-33.0, 21.4, FLOOR + 1.72), (-27.2, 13.5, FLOOR + 1.72),
                (-21.5, 20.8, FLOOR + 1.72)):
        point('LAMP | Chamber niche diya', loc, 3.0)
    for y in (-2.9, 2.9):
        point('LAMP | Darbar platform stand', (-1.0, y, FLOOR + 1.72), 30.0)
    for x in (10.0, 16.0, 22.0, 28.0):
        point('LAMP | Darbar hanging', (x, 0.0, NAVE_SPRING + 0.6 - 3.5), 40.0, 0.12)
    for x in (-29.8, -22.6):
        point('LAMP | Interrogation stand', (x, -22.6, FLOOR + 1.52), 20.0)
    area('FILL | Chamber bounce from the window', (cx, 23.0, FLOOR + 2.6), (cx, 17.0, FLOOR), 120.0, 2.4,
         (1.0, 0.86, 0.7), 0.25)
    area('FILL | Interrogation courtyard bounce', (-25.5, -13.6, FLOOR + 3.2), (-26.2, -18.6, FLOOR), 220.0, 4.0,
         (1.0, 0.9, 0.78), 0.3)
    area('FILL | Waiting hall bounce', (-14.4, -13.6, FLOOR + 3.4), (-14.4, -19.0, FLOOR), 90.0, 3.0,
         (1.0, 0.88, 0.75), 0.3)
    area('FILL | Darbar nave sky bounce', (14.0, 0.0, NAVE_SPRING + 1.5), (14.0, 0.0, FLOOR), 900.0, 8.0,
         (0.95, 0.9, 0.82), 0.35)
    area('FILL | Darbar platform bounce', (-1.0, 0.0, DARBAR_CEILING - 0.6), (-7.0, 0.0, PLATFORM_TOP), 260.0, 3.0,
         (1.0, 0.85, 0.7), 0.4)
    return {'sun': sun, 'sky': sky}


def _constant(action: bpy.types.Action) -> None:
    for fcurve in _fcurves(action):
        for key in fcurve.keyframe_points:
            key.interpolation = 'CONSTANT'


def _fcurves(action: bpy.types.Action) -> list[bpy.types.FCurve]:
    curves = list(getattr(action, 'fcurves', []) or [])
    if curves:
        return curves
    found: list[bpy.types.FCurve] = []
    for layer in getattr(action, 'layers', []):
        for strip in layer.strips:
            for bag in strip.channelbags:
                found.extend(bag.fcurves)
    return found


def render_settings(scene: bpy.types.Scene) -> None:
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 96
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.03
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = 'OPENIMAGEDENOISE'
    scene.cycles.max_bounces = 8
    scene.cycles.diffuse_bounces = 4
    scene.cycles.glossy_bounces = 3
    scene.cycles.transmission_bounces = 4
    scene.cycles.transparent_max_bounces = 8
    scene.cycles.blur_glossy = 1.0
    scene.cycles.sample_clamp_indirect = 6.0
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.render.use_persistent_data = True


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def manifest(p: Palace, marks: dict[str, bpy.types.Object], cams: dict[str, bpy.types.Object]) -> dict[str, object]:
    bpy.context.view_layer.update()

    def world_loc(obj: bpy.types.Object) -> list[float]:
        return [round(v, 3) for v in obj.matrix_world.translation]

    def local_loc(obj: bpy.types.Object) -> list[float]:
        return [round(v, 3) for v in (obj.location if obj.parent else world.world_to_palace(tuple(obj.location)))]

    objects = [o for o in p.scene.objects if o.type == 'MESH']
    collections = {coll.name: len(coll.all_objects) for coll in p.root.children_recursive}
    return {
        'set': 'Set 1 — Palace (महल): private chamber, interrogation room, open darbar',
        'blend': str(BLEND.relative_to(ROOT)).replace('\\', '/'),
        'generator': 'Blender/tools/build_palace_set.py',
        'blender': bpy.app.version_string,
        'units': 'metres; +X east, +Y north, +Z up; world Z 0 = ghat quay',
        'palace_anchor': {'world_location': list(world.PALACE_ANCHOR), 'yaw_degrees': world.PALACE_YAW_DEG,
                          'local_axes': '+X toward the public gate, +Y toward the river façade and ghat window'},
        'time_of_day_frames': {'morning': MORNING, 'evening': EVENING},
        'water_levels': {'morning_z': world.MORNING_WATER_Z, 'evening_z': world.EVENING_WATER_Z,
                         'morning_dry_steps': world.MORNING_VISIBLE_STEPS,
                         'evening_dry_steps': world.EVENING_VISIBLE_STEPS,
                         'step_rise': world.STEP_RISE, 'step_tread': world.STEP_TREAD},
        'story_marks': {k: {'name': v.name, 'palace_local': local_loc(v), 'world': world_loc(v)} for k, v in marks.items()},
        'cameras': {k: {'name': v.name, 'lens_mm': v.data.lens, 'world': world_loc(v)} for k, v in cams.items()},
        'map_anchors': [{'name': a.name, 'location': list(a.location), 'certainty': a.certainty, 'note': a.note}
                        for a in world.ANCHORS],
        'collections': collections,
        'mesh_objects': len(objects),
        'unique_meshes': len({o.data.name for o in objects}),
        'placeholders': [ghat.COLLECTION],
        'guesses': [
            'Architectural style: early Indian stone idiom (trabeated halls, rolled brackets, shala vaults, '
            'phamsana roofs); no specific historical palace is copied.',
            'Palace sits on a river bluff at the bend, about 60 m from the ghat; the ghat, gate, market and '
            'Halwai roof positions are placeholders for sets 2 and 3.',
            'Interrogation floor is dark basalt so the white chalk map reads clearly.',
            "Vikram's standing mark in the interrogation room and the crowd zone in the darbar are suggestions.",
        ],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build(save: bool = True) -> tuple[Palace, dict[str, object]]:
    scene = reset_scene()
    p = Palace(scene)
    placeholder = ghat.build(p.root)
    plinth(p)
    darbar(p)
    private_wing(p)
    jharokha(p)
    forecourt(p)
    flags(p)
    marks = story_marks(p)
    cams = cameras(p)
    lighting(p, placeholder['water'])
    render_settings(scene)
    anchor = p.anchor
    anchor.location = world.PALACE_ANCHOR
    anchor.rotation_euler.z = math.radians(world.PALACE_YAW_DEG)
    anchor_inverse = Matrix.Translation(world.PALACE_ANCHOR) @ Matrix.Rotation(math.radians(world.PALACE_YAW_DEG), 4, 'Z')
    del anchor_inverse
    scene.camera = cams['window']
    scene.frame_set(MORNING)
    bpy.context.view_layer.update()
    data = manifest(p, marks, cams)
    if save:
        SET_DIR.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(BLEND), compress=True)
        MANIFEST.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print(f'Saved {BLEND} ({BLEND.stat().st_size / 1e6:.1f} MB), {data["mesh_objects"]} mesh objects, '
              f'{data["unique_meshes"]} unique meshes', flush=True)
    return p, data


def main() -> None:
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-save', action='store_true')
    args = parser.parse_args(argv)
    build(save=not args.no_save)


if __name__ == '__main__':
    main()
