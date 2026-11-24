"""PLACEHOLDER landscape for the palace set: terrain, river, ghat steps and town massing.

Sets 2 and 3 (river, ghat, gate, lower settlement and grain market) will replace
everything here. Only the step dimensions and water levels from
`set_world_map` are fixed, because the palace window camera counts them.
"""

from __future__ import annotations

import math
import random

import bpy
from mathutils import Matrix, Vector

import set_kit as kit
import set_materials as mats
import set_world_map as world


COLLECTION = 'PLACEHOLDER | Ghat, river & town (replace with sets 2-3)'


def _smoothstep(e0: float, e1: float, x: float) -> float:
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def _hash_noise(x: float, y: float) -> float:
    """Cheap smooth value noise for distant hills (no Blender dependency)."""
    def lattice(ix: int, iy: int) -> float:
        h = (ix * 374761393 + iy * 668265263) & 0xFFFFFFFF
        h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
        return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0

    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    sx, sy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a = lattice(ix, iy) + (lattice(ix + 1, iy) - lattice(ix, iy)) * sx
    b = lattice(ix, iy + 1) + (lattice(ix + 1, iy + 1) - lattice(ix, iy + 1)) * sx
    return a + (b - a) * sy


def ghat_cut(x: float, y: float) -> float | None:
    """Height limit under the ghat so terrain never pokes through the steps."""
    if abs(x - world.GHAT_CENTER_X) <= world.GHAT_HALF_WIDTH + 4.5 and \
            world.GHAT_TOP_EDGE_Y - 0.5 <= y <= world.QUAY_DEPTH + 0.5:
        return world.QUAY_Z - 0.3
    if abs(x - world.GHAT_CENTER_X) > world.GHAT_HALF_WIDTH + 1.5:
        return None
    if y > world.GHAT_TOP_EDGE_Y + 0.5 or y < world.step_front_y(world.STEP_COUNT) - 3:
        return None
    step = max(1, math.ceil((world.GHAT_TOP_EDGE_Y - y) / world.STEP_TREAD))
    return world.step_top_z(min(step, world.STEP_COUNT)) - 0.5


def height(x: float, y: float) -> float:
    lx, ly, _ = world.world_to_palace((x, y, 0.0))
    x_min, _, _, y_max = world.PALACE_PLINTH_LOCAL
    # The river bastion is the cliff: the bluff ends within a few metres of the battered wall.
    outside = max(x_min - 0.4 - lx, ly - (y_max + 0.4))
    land = world.BLUFF_Z * (1.0 - _smoothstep(0.0, 3.5, outside))
    # Gentle rise of the upper town further inland.
    land += 1.5 * _smoothstep(60.0, 160.0, lx) if outside < 0 else 0.0
    r = math.hypot(x, y)
    land += 14.0 * _smoothstep(240.0, 520.0, r) * _hash_noise(x / 90.0, y / 90.0)
    distance = world.river_distance(x, y)
    if outside > 0.0:
        # Where the river is near, it washes the bastion foot instead of leaving a dry shelf.
        # Limited to the strip the town keeps clear around the palace.
        sink = ((1.0 - _smoothstep(46.0, 60.0, distance)) * _smoothstep(0.0, 3.5, outside)
                * (1.0 - _smoothstep(10.0, 14.0, outside)))
        land += (world.MORNING_WATER_Z - 1.2 - land) * sink
    bank = _smoothstep(world.RIVER_HALF_WIDTH - 5.0, world.RIVER_HALF_WIDTH + world.RIVER_BANK_WIDTH, distance)
    bed = world.RIVERBED_Z + 0.8 * _hash_noise(x / 12.0, y / 12.0)
    z = bed + (land - bed) * bank
    cut = ghat_cut(x, y)
    if cut is not None:
        z = min(z, cut)
    return z


def _axis(limit: float, inner: float, fine: float, coarse: float) -> list[float]:
    values: list[float] = []
    v = -limit
    while v < limit + 1e-6:
        values.append(v)
        v += fine if abs(v) < inner else coarse
    return values


def terrain(collection: bpy.types.Collection) -> bpy.types.Object:
    xs = _axis(700.0, 190.0, 2.0, 12.0)
    ys = _axis(700.0, 190.0, 2.0, 12.0)
    builder = kit.MeshBuilder()
    rows = []
    for y in ys:
        rows.append([builder.vert((x, y, height(x, y))) for x in xs])
    for r in range(len(ys) - 1):
        for c in range(len(xs) - 1):
            builder.face((rows[r][c], rows[r][c + 1], rows[r + 1][c + 1], rows[r + 1][c]), 0, True)
    data = builder.mesh('PLACEHOLDER Terrain', [mats.terrain('Land | earth, grass and silt')], 60.0)
    obj = bpy.data.objects.new('PLACEHOLDER | Terrain and riverbed', data)
    collection.objects.link(obj)
    return obj


def water(collection: bpy.types.Collection) -> bpy.types.Object:
    builder = kit.MeshBuilder()
    builder.grid_surface(1, 1, lambda u, v: ((u - 0.5) * 1400, (v - 0.5) * 1400, 0.0), 0, True)
    data = builder.mesh('River surface', [mats.river_water('River | silty flood water')])
    obj = bpy.data.objects.new('River | water surface (keyed level)', data)
    collection.objects.link(obj)
    obj['Morning level (5 steps)'] = world.MORNING_WATER_Z
    obj['Evening level (3 steps)'] = world.EVENING_WATER_Z
    return obj


def ghat(collection: bpy.types.Collection) -> list[bpy.types.Object]:
    stone = mats.wet_ghat_stone('Ghat | river stone, wet line and silt', world.MORNING_WATER_Z,
                                world.NIGHT_FLOOD_MARK_Z)
    dressed = mats.stone('Ghat | dressed sandstone', mats.SANDSTONE)
    objects: list[bpy.types.Object] = []
    b = kit.MeshBuilder()
    hw = world.GHAT_HALF_WIDTH
    cx = world.GHAT_CENTER_X
    for k in range(1, world.STEP_COUNT + 1):
        top = world.step_top_z(k)
        front = world.step_front_y(k)
        back = world.step_front_y(k - 1)
        b.box_between((cx - hw, front, world.RIVERBED_Z - 1.0), (cx + hw, back, top))
        # Rounded nosing so each tread edge catches light from the window.
        b.box_between((cx - hw, front - 0.04, top - 0.07), (cx + hw, front + 0.02, top - 0.01))
    b.box_between((cx - hw - 3, world.step_front_y(world.STEP_COUNT) - 2.0, world.RIVERBED_Z - 1.0),
                  (cx + hw + 3, world.step_front_y(world.STEP_COUNT), world.RIVERBED_Z + 0.4))
    data = b.mesh('Ghat steps', [stone])
    steps = bpy.data.objects.new('Ghat | 14 steps (0.40 rise, 0.70 tread)', data)
    collection.objects.link(steps)
    steps['Step rise'] = world.STEP_RISE
    steps['Step tread'] = world.STEP_TREAD
    objects.append(steps)
    q = kit.MeshBuilder()
    q.box_between((cx - hw - 4, world.GHAT_TOP_EDGE_Y, -1.5), (cx + hw + 4, world.QUAY_DEPTH, world.QUAY_Z))
    q.sweep([(cx - hw - 4, world.GHAT_TOP_EDGE_Y), (cx + hw + 4, world.GHAT_TOP_EDGE_Y)],
            [(-0.1, -0.12), (0.05, -0.12), (0.05, 0.0), (-0.1, 0.0)], 0, False, world.QUAY_Z)
    data = q.mesh('Ghat quay', [mats.slab_floor('Ghat | quay paving', mats.GHAT_STONE, (1.4, 0.9))])
    quay = bpy.data.objects.new('Ghat | upper quay', data)
    collection.objects.link(quay)
    objects.append(quay)
    flank = kit.MeshBuilder()
    for side in (-1, 1):
        x0 = cx + side * hw
        x1 = cx + side * (hw + 4.0)
        lo, hi = min(x0, x1), max(x0, x1)
        bottom = world.step_front_y(world.STEP_COUNT) - 2.0
        flank.box_between((lo, bottom, world.RIVERBED_Z - 1.0), (hi, world.GHAT_TOP_EDGE_Y, world.QUAY_Z + 0.9))
        flank.sweep(kit.rect_path(lo, hi, bottom, world.GHAT_TOP_EDGE_Y), kit.cornice_profile(0.18, 0.28), 0, True,
                    world.QUAY_Z + 0.9)
        for z in (-1.0, -3.0):
            flank.sweep(kit.rect_path(lo, hi, bottom, world.GHAT_TOP_EDGE_Y),
                        [(-0.05, 0.0), (0.06, 0.0), (0.06, 0.14), (-0.05, 0.14)], 0, True, z)
    data = flank.mesh('Ghat flanks', [stone])
    flanks = bpy.data.objects.new('Ghat | flanking bastions', data)
    collection.objects.link(flanks)
    objects.append(flanks)
    for side in (-1, 1):
        shrine = small_shrine()
        mesh = shrine.mesh(f'Ghat shrine {side}', [dressed])
        obj = bpy.data.objects.new('Ghat | flank shrine (placeholder)', mesh)
        collection.objects.link(obj)
        obj.location = (cx + side * (hw + 2.0), -4.5, world.QUAY_Z + 1.25)
        objects.append(obj)
    return objects


def small_shrine() -> kit.MeshBuilder:
    b = kit.MeshBuilder()
    for sx in (-1, 1):
        for sy in (-1, 1):
            p = kit.slender_pillar(1.9, 0.09)
            b.merge(p, Matrix.Translation((sx * 0.85, sy * 0.85, 0)))
    b.box((0, 0, -0.08), (2.3, 2.3, 0.16))
    roof = kit.phamsana_roof(2.2, 3, 0.3, 0.6)
    b.merge(roof, Matrix.Translation((0, 0, 1.9)))
    return b


def town(collection: bpy.types.Collection, seed: int = 7) -> list[bpy.types.Object]:
    """Low-detail houses for scale. Keeps the view corridor and the market ground open."""
    rng = random.Random(seed)
    tints = [(0.70, 0.62, 0.50), (0.62, 0.46, 0.32), (0.74, 0.70, 0.62), (0.55, 0.42, 0.33), (0.68, 0.55, 0.38)]
    wall_mats = [mats.whitewash(f'Town | lime wash {i}', t) for i, t in enumerate(tints)]
    roof_mat = mats.stone('Town | roof terrace', mats.RED_SANDSTONE)
    window_mat = mats.flat('Town | dark openings', (0.02, 0.018, 0.015), 0.9)
    window_point = Vector(world.JHAROKHA_WORLD_TARGET)
    ghat_point = Vector((world.GHAT_CENTER_X, world.GHAT_TOP_EDGE_Y - 3.0))
    market = Vector((-38.0, 34.0))
    builders = [kit.MeshBuilder() for _ in wall_mats]
    placed: list[tuple[float, float, float]] = []

    def blocked(x: float, y: float, r: float) -> bool:
        p = Vector((x, y))
        seg = ghat_point - window_point
        t = max(0.0, min(1.0, (p - window_point).dot(seg) / seg.length_squared))
        if (window_point + seg * t - p).length < 10 + r:
            return True
        if world.river_distance(x, y) < world.RIVER_HALF_WIDTH + world.RIVER_BANK_WIDTH + r:
            return True
        if abs(x - world.GHAT_CENTER_X) < world.GHAT_HALF_WIDTH + 6 and y < world.QUAY_DEPTH + 3:
            return True
        if (p - market).length < 16 + r:
            return True
        lx, ly, _ = world.world_to_palace((x, y, 0.0))
        x0, x1, y0, y1 = world.PALACE_PLINTH_LOCAL
        if x0 - 14 < lx < x1 + 14 and y0 - 14 < ly < y1 + 16:
            return True
        return any(math.hypot(x - px, y - py) < r + pr + 1.2 for px, py, pr in placed)

    attempts = 0
    while len(placed) < 230 and attempts < 6000:
        attempts += 1
        x = rng.uniform(-200, 200)
        y = rng.uniform(-60, 220)
        w, d = rng.uniform(5, 10), rng.uniform(5, 9)
        r = math.hypot(w, d) / 2
        if blocked(x, y, r):
            continue
        z = height(x, y)
        if z < -0.5:
            continue
        near_ghat = abs(x) < 45 and y < 30
        storeys = rng.choice((1, 2, 2, 3)) + (1 if near_ghat else 0)
        h = 3.2 * storeys
        yaw = math.radians(rng.choice((0, 90)) + rng.uniform(-6, 6))
        placed.append((x, y, r))
        b = builders[rng.randrange(len(builders))]
        piece = kit.MeshBuilder()
        piece.box((0, 0, h / 2 - 0.5), (w, d, h + 1.0), {'*': 0})
        piece.sweep(kit.rect_path(-w / 2, w / 2, -d / 2, d / 2), kit.parapet_profile(0.7, 0.22), 1, True, h - 0.5)
        piece.sweep(kit.rect_path(-w / 2, w / 2, -d / 2, d / 2), kit.chhajja_profile(0.45, 0.12, 0.06), 1, True,
                    h * 0.55)
        for s in range(storeys):
            for k in range(max(1, int(w / 2.4))):
                u = -w / 2 + (k + 0.5) * w / max(1, int(w / 2.4))
                piece.box((u, -d / 2 - 0.01, 0.9 + s * 3.2 + 0.4), (0.7, 0.05, 1.2), 2)
        b.merge(piece, Matrix.Translation((x, y, z)) @ Matrix.Rotation(yaw, 4, "Z"))
    objects = []
    for i, b in enumerate(builders):
        if not b.faces:
            continue
        data = b.mesh(f'Town massing {i}', [wall_mats[i], roof_mat, window_mat])
        obj = bpy.data.objects.new(f'PLACEHOLDER | Town houses {i}', data)
        collection.objects.link(obj)
        objects.append(obj)
    return objects


def trees(collection: bpy.types.Collection, seed: int = 11) -> list[bpy.types.Object]:
    rng = random.Random(seed)
    bark = mats.teak('Tree | bark', (0.11, 0.08, 0.06))
    leaves = [mats.foliage('Tree | neem leaves', (0.06, 0.09, 0.03)),
              mats.foliage('Tree | pipal leaves', (0.08, 0.10, 0.04))]
    meshes = [kit.tree(s, rng.uniform(8, 13), rng.uniform(4, 6.5)).mesh(f'Tree {s}', [bark, leaves[s % 2]])
              for s in range(5)]
    objects = []
    spots: list[tuple[float, float]] = []
    while len(spots) < 70:
        x = rng.uniform(-260, 260)
        y = rng.uniform(-260, 260)
        d = world.river_distance(x, y)
        if d < world.RIVER_HALF_WIDTH + 6 or d > 120:
            continue
        lx, ly, _ = world.world_to_palace((x, y, 0.0))
        x0, x1, y0, y1 = world.PALACE_PLINTH_LOCAL
        if x0 - 10 < lx < x1 + 10 and y0 - 10 < ly < y1 + 12:
            continue
        if abs(x) < 30 and -15 < y < 15:
            continue
        window_point = Vector(world.JHAROKHA_WORLD_TARGET)
        seg = Vector((0.0, -3.0)) - window_point
        p = Vector((x, y))
        t = max(0.0, min(1.0, (p - window_point).dot(seg) / seg.length_squared))
        if (window_point + seg * t - p).length < 12:
            continue
        spots.append((x, y))
    for i, (x, y) in enumerate(spots):
        obj = bpy.data.objects.new('PLACEHOLDER | Tree', meshes[i % len(meshes)])
        collection.objects.link(obj)
        obj.location = (x, y, height(x, y) - 0.3)
        obj.rotation_euler.z = rng.uniform(0, 6.28)
        s = rng.uniform(0.8, 1.25)
        obj.scale = (s, s, s)
        objects.append(obj)
    return objects


def build(root: bpy.types.Collection) -> dict[str, bpy.types.Object]:
    collection = bpy.data.collections.new(COLLECTION)
    root.children.link(collection)
    land = terrain(collection)
    river = water(collection)
    ghat(collection)
    town(collection)
    trees(collection)
    return {'terrain': land, 'water': river}
