"""The Halwai: the rooftop witness of chapter 1, built on the shared civilian base.

Recognition at three distances (rooftop wide shot, refuge slope, interrogation
close-up) rests on features he keeps when wet or bare-headed:

* silhouette: short, broad and round-bellied, with a bald crown;
* face: wide jowly face, broad bulbous nose, heavy hooded eyes, a thick
  salt-and-pepper handlebar moustache with upturned ends, a mole on his
  left cheek;
* costume: faded turmeric-yellow kurta with sweet-shop stains, off-white dhoti
  with a brown border and a green-checked gamchha over the left shoulder.

The gamchha is green on purpose: Nandu's red shoulder cloth is a plot clue and
no other witness should carry red near the shoulder.
"""

from __future__ import annotations

import math
import random
from typing import Sequence

import bpy
from mathutils import Quaternion, Vector
from mathutils.bvhtree import BVHTree

from civilian import Civilian, Weights, gaussian, profile, smoothstep
import facial_controls as face_controls
from groom import FiberGroup, surface
from textile import finish_fabric, store_rest_positions


HALWAI_PROFILE = (
    (1.478, -.026, .048, .050), (1.490, -.024, .080, .084), (1.512, -.019, .102, .101),
    (1.545, -.014, .115, .110), (1.585, -.012, .121, .112), (1.630, -.010, .126, .112),
    (1.675, -.008, .122, .108), (1.722, -.003, .119, .105), (1.758, .003, .112, .099),
    (1.786, .006, .091, .082), (1.802, .007, .052, .050), (1.810, .007, .010, .010),
)

SPEC = dict(
    name='Halwai', height=.945, skin=(.255, .142, .088), hair=(.022, .019, .017),
    iris=(.040, .020, .009), face_width=1.10, nose_width=1.26, brow_lift=.0025,
    # head_scale .76 matches proportions.REALISTIC_HEAD (Nandu thread) so the new cast shares one
    # realistic head-to-body ratio; height .945 puts his crown at about 1.64 m.
    build=1.12, belly=1.0, neck=1.15, head_profile=HALWAI_PROFILE, head_scale=.76,
    face=dict(eye_x=.0475, eye_radius=.0226, upper_lid=.0072, lower_lid=.0061, iris=.90, nose_tip=.029,
              tip_width=1.40, nose_wing=.023, nose_drop=.004, bridge=.018, cheek=.0075, cheek_fat=.0150,
              jowl=.0085, chin=.0095, double_chin=.0090, hood=.0055, eye_bag=.0042, nasolabial=.0060,
              marionette=.0030, wrinkles=.00065, brow_ridge=.0090, socket=.0135, mentolabial=.0050, ear_size=1.09, ear_out=.001,
              lid_crease=.0005, lip_full=1.35, lower_lip=1.35, mouth_width=.034),
)

# Kurta rows: (z, half width, front depth, back depth, centre y), ascending.
KURTA_ROWS = (
    (.600, .252, .200, .160, 0), (.700, .244, .196, .155, 0), (.800, .234, .194, .149, 0),
    (.900, .222, .197, .140, 0), (.980, .217, .205, .133, 0), (1.060, .214, .210, .130, 0),
    (1.140, .208, .193, .129, 0), (1.220, .204, .156, .124, 0), (1.290, .204, .128, .119, .002),
    (1.335, .198, .115, .110, .004), (1.368, .182, .103, .100, .004), (1.398, .152, .091, .090, .003),
    (1.422, .122, .079, .081, .001), (1.446, .086, .070, .072, -.005),
)
HEM_Z = .600
SLIT_TOP = .760
PLACKET_BOTTOM = 1.335


# --------------------------------------------------------------------- helpers
def kurta_point(angle: float, z: float, offset: float = 0) -> tuple[float, float, float]:
    rx, front, back, cy = profile(KURTA_ROWS, z)
    c, s = math.cos(angle), math.sin(angle)
    depth = back if s > 0 else front
    return ((rx + offset) * c, cy + (depth + offset) * s, z)


def kurta_top_z(x: float) -> float:
    """Height of the kurta's shoulder line (at y = 0) above a given |x|."""
    z = KURTA_ROWS[-1][0]
    while z > 1.25 and profile(KURTA_ROWS, z)[0] < abs(x):
        z -= .001
    return z


def kurta_surface_y(x: float, z: float, front: bool, offset: float = 0) -> float:
    rx, front_depth, back_depth, cy = profile(KURTA_ROWS, z)
    depth = (front_depth if front else back_depth) + offset
    across = math.sqrt(max(0., 1 - (x / (rx + offset)) ** 2))
    return cy + (-depth if front else depth) * across


def normalised(weights: dict[str, float]) -> Weights:
    weights = {bone: w for bone, w in weights.items() if w > .001}
    total = sum(weights.values())
    return {bone: w / total for bone, w in weights.items()}


def torso_weight(x: float, z: float, shoulders: bool = True) -> Weights:
    """Spine blend by height, upper arm near the shoulder, thighs toward the hem."""
    side = 'L' if x > 0 else 'R'
    if z >= 1.30:
        weights = {'chest': 1.}
    elif z >= 1.14:
        t = (z - 1.14) / .16
        weights = {'chest': t, 'spine': 1 - t}
    elif z >= .98:
        t = (z - .98) / .16
        weights = {'spine': t, 'hips': 1 - t}
    else:
        weights = {'hips': 1.}
    if shoulders:
        share = .45 * smoothstep(.15, .21, abs(x)) * smoothstep(1.25, 1.32, z)
        if share:
            weights = {bone: w * (1 - share) for bone, w in weights.items()}
            weights[f'upper_arm.{side}'] = share
    if z < .90:
        k = .38 * smoothstep(.90, .62, z)
        left = smoothstep(-.06, .06, x)
        weights = {bone: w * (1 - k) for bone, w in weights.items()}
        weights['thigh.L'] = k * left
        weights['thigh.R'] = k * (1 - left)
    return normalised(weights)


def grid_mesh(c: Civilian, name: str, rows: Sequence[Sequence[tuple[float, float, float]]],
              material, weights: Sequence[Sequence[Weights]], cyclic: bool = True,
              skip=lambda row, column: False, uv: Sequence[Sequence[tuple[float, float]]] | None = None):
    columns = len(rows[0])
    verts = [point for row in rows for point in row]
    faces = []
    span = columns if cyclic else columns - 1
    for r in range(len(rows) - 1):
        for col in range(span):
            if skip(r, col):
                continue
            nxt = (col + 1) % columns
            faces.append((r * columns + col, r * columns + nxt, (r + 1) * columns + nxt, (r + 1) * columns + col))
    obj = c.mesh(name, verts, faces, material, [w for row in weights for w in row])
    if uv is not None:
        layer = obj.data.uv_layers.new(name='UVMap')
        flat = [value for row in uv for value in row]
        for polygon in obj.data.polygons:
            for loop in polygon.loop_indices:
                layer.data[loop].uv = flat[obj.data.loops[loop].vertex_index]
    return obj


# --------------------------------------------------------------------- kurta
def kurta(c: Civilian, cloth, binding, button) -> None:
    columns = 96
    heights = [HEM_Z + (1.425 - HEM_Z) * (i / 52) ** .92 for i in range(53)] + [1.436, 1.446]
    rows, weights = [], []
    for z in heights:
        ring, ring_weights = [], []
        below = smoothstep(.98, .62, z)
        for col in range(columns):
            angle = -math.pi / 2 + math.tau * (col + .5) / columns  # columns straddle the front centre
            fold = below * (.0065 * math.sin(9 * angle + 1.3) + .0032 * math.sin(17 * angle + 4 * z))
            fold += .0015 * smoothstep(1.22, 1.30, z) * smoothstep(1.4, 1.3, z) * math.sin(13 * angle)
            x, y, _ = kurta_point(angle, z, fold)
            hem = .006 * math.sin(5 * angle + 1) * smoothstep(.66, .60, z)
            if z < SLIT_TOP and col in (23, 24, 71, 72):
                spread = .055 * smoothstep(SLIT_TOP, HEM_Z, z) * (1 if col in (24, 72) else -1)
                x, y, _ = kurta_point(angle + spread, z, fold)
            if z >= PLACKET_BOTTOM - .02 and col in (columns - 1, 0):
                side = -1 if col == columns - 1 else 1
                x = side * (.0035 + .0085 * smoothstep(PLACKET_BOTTOM - .02, 1.44, z))
                y = kurta_surface_y(x, z, True)
            ring.append((x, y, z + hem))
            ring_weights.append(torso_weight(x, z))
        rows.append(ring)
        weights.append(ring_weights)

    def skip(row: int, col: int) -> bool:
        z = heights[row]
        mid = -math.pi / 2 + math.tau * (col + 1) / columns
        if z < SLIT_TOP - .001 and col in (23, 71):
            return True  # side slits
        return z >= PLACKET_BOTTOM and col == columns - 1  # front placket opening

    body = grid_mesh(c, 'Turmeric cotton kurta', rows, cloth, weights, skip=skip)
    body['Garment'] = 'Single-layer kurta: side slits from the hem, front placket, half sleeves.'

    # Hem, slit and placket bindings follow the open edges of the grid.
    hem = rows[0]
    for label, select in (('front', lambda p: p[1] <= 0), ('back', lambda p: p[1] > 0)):
        points = [p for p in hem if select(p) and abs(p[0]) < .228]
        points.sort(key=lambda p: math.atan2(p[1], p[0]))
        if len(points) > 2:
            c.tube(f'Kurta hem binding {label}', [(x, y, z + .004) for x, y, z in points], .0042, binding,
                   [torso_weight(x, z) for x, y, z in points])
    slit_rows = [index for index, z in enumerate(heights) if z <= SLIT_TOP + .012]
    for side, pair in (('L', (23, 24)), ('R', (71, 72))):
        for col, label in zip(pair, ('front' if side == 'L' else 'back', 'back' if side == 'L' else 'front')):
            points = [rows[index][col] for index in slit_rows]
            points = [(x * 1.004, y * 1.004, z) for x, y, z in points]
            c.tube(f'Kurta slit binding {side} {label}', points, .0030, binding,
                   [torso_weight(x, z) for x, y, z in points])
        top = rows[slit_rows[-1]][pair[0]]
        c.ovoid(f'Kurta slit bar tack {side}', (top[0] * 1.01, top[1], top[2] + .002), (.004, .007, .005),
                binding, 'hips')
    neck = rows[-1]
    c.tube('Kurta neck binding', [(x, y, z + .002) for x, y, z in neck[1:-1]], .0045, binding, 'chest')
    edge_rows = [index for index, z in enumerate(heights) if z >= PLACKET_BOTTOM - .02]
    for side, col in (('R', columns - 1), ('L', 0)):
        points = [rows[index][col] for index in edge_rows[:-1]]
        points = [(x, y - .0012, z) for x, y, z in points]
        c.tube(f'Kurta placket edge {side}', points, .0034, binding, 'chest')
    for index, z in enumerate((1.418, 1.386, 1.354)):
        width = .0035 + .0085 * smoothstep(PLACKET_BOTTOM - .02, 1.44, z)
        x = width + .006
        c.ovoid(f'Kurta cloth button {index + 1}', (x, kurta_surface_y(x, z, True) - .0045, z),
                (.0056, .0040, .0056), button, 'chest')
        c.tube(f'Kurta button loop {index + 1}', [(-width - .002, kurta_surface_y(-width, z, True) - .003, z),
               (0, kurta_surface_y(0, z, True) - .007, z + .001), (x - .002, kurta_surface_y(x, z, True) - .0055, z)],
               .0011, binding, 'chest')

    for side, sign in (('L', 1), ('R', -1)):
        upper, lower = f'upper_arm.{side}', f'forearm.{side}'
        form = [(.170, .064, 'chest'), (.200, .068, {'chest': .80, upper: .20}),
                (.239, .075, {'chest': .45, upper: .55}), (.312, .077, upper), (.397, .072, upper),
                (.455, .069, {upper: .72, lower: .28}), (.500, .068, {upper: .38, lower: .62})]
        rings, ring_weights = [], []
        for index, (x, radius, weight) in enumerate(form):
            ring = []
            for i in range(40):
                angle = math.tau * i / 40
                c_, s_ = math.cos(angle), math.sin(angle)
                fold = 1 + .045 * math.sin(6 * angle + 2.1 * index) * (index / 6)
                drape = 1 + .12 * max(0, -s_) * (1 - index / 6)  # loose cloth hangs under the arm
                top = 1 - (.40, .28, .12, 0, 0, 0, 0)[index] * max(0, s_)
                ring.append((sign * x, sign * radius * c_ * fold, 1.375 + radius * s_ * fold * drape * top))
            rings.append(ring)
            ring_weights.append(weight)
        with c.arm_space(sign):
            sleeve = c.ring_mesh(f'Kurta half sleeve {side}', rings, cloth, ring_weights, cap=False)
            c.tube(f'Kurta sleeve hem {side}', [(x + sign * .002, y * 1.03, 1.375 + (z - 1.375) * 1.03)
                   for x, y, z in rings[-1]], .0042, binding, [{upper: .38, lower: .62}] * len(rings[-1]), cyclic=True)
        sleeve['Garment'] = 'Half sleeve ending just past the elbow.'


# --------------------------------------------------------------------- dhoti
def dhoti(c: Civilian, cotton, border) -> None:
    for sign, side in ((1, 'L'), (-1, 'R')):
        thigh, shin = f'thigh.{side}', f'shin.{side}'
        rings_spec = [
            (.128, .137, .072, .076, .008, shin), (.144, .138, .076, .080, .008, shin),
            (.166, .139, .081, .085, .009, shin), (.30, .140, .098, .103, .008, shin),
            (.40, .140, .104, .109, .008, shin),
            (.52, .137, .110, .115, .005, {thigh: .5, shin: .5}), (.60, .131, .104, .108, 0, thigh),
            (.70, .121, .099, .103, -.002, thigh), (.82, .112, .101, .105, -.004, thigh),
            (.92, .100, .104, .106, -.002, {'hips': .76, thigh: .24}), (.99, .088, .104, .104, 0, 'hips'),
        ]
        rings, weights = [], []
        for row, (z, x, sx, sy, y, weight) in enumerate(rings_spec):
            ring = []
            for step in range(44):
                angle = math.tau * step / 44
                fold = 1 + .072 * math.cos(7 * angle + sign * (.55 * row + .5)) + .03 * math.sin(13 * angle + row)
                drop = .010 * math.sin(3 * angle + sign) / (row + 1)
                ring.append((sign * x + sx * math.cos(angle) * fold, y + sy * math.sin(angle) * fold, z + drop))
            rings.append(ring)
            weights.append(weight)
        c.ring_mesh(f'Dhoti leg {side}', rings, cotton, weights, cap=False)
        for index in (0, 1):
            c.ring_mesh(f'Dhoti border {side} {index}', [[(px + (px - sign * .137) * .012, py * 1.012 + .0001, pz)
                        for px, py, pz in rings[index]], [(px + (px - sign * .137) * .012, py * 1.012, pz + .0001)
                        for px, py, pz in rings[index + 1]]], border, shin, cap=False)
        c.tube(f'Dhoti hem roll {side}', [(px, py, pz - .001) for px, py, pz in rings[0]], .0038, border, shin, cyclic=True)
    # Front pleats (the gathered fan of the dhoti) hang between the knees.
    columns, rows = 15, 14
    verts, weights = [], []
    for r in range(rows):
        t = r / (rows - 1)
        z = .965 - (.965 - .17) * t
        for col in range(columns):
            u = col / (columns - 1)
            width = .042 + .020 * t
            x = (u - .5) * 2 * width
            pleat = (.007 + .004 * t) * (1 if col % 2 else -1)
            y = -.126 - .004 * t + pleat - .016 * math.sin(math.pi * u)
            k = .30 * t
            left = smoothstep(-.03, .03, x)
            verts.append((x, y, z - .015 * t * math.sin(math.pi * u * 2)))
            weights.append(normalised({'hips': 1 - k, 'thigh.L': k * left, 'thigh.R': k * (1 - left)}))
    faces = [(r * columns + col, r * columns + col + 1, (r + 1) * columns + col + 1, (r + 1) * columns + col)
             for r in range(rows - 1) for col in range(columns - 1)]
    c.mesh('Dhoti front pleats', verts, faces, cotton, weights)
    c.tube('Dhoti pleat border', verts[-columns:], .0035, border, weights[-columns:])


# --------------------------------------------------------------------- gamchha
def gamchha(c: Civilian, cloth, fringe_material) -> None:
    """A checked cotton towel over the left shoulder, front end longer than the back."""
    across = 11
    path: list[tuple[float, float, bool]] = []  # (z, centre x, on front)
    for z in (1.05, 1.10, 1.16, 1.22, 1.28, 1.33, 1.37, 1.40):
        path.append((z, .118 - .012 * (1.40 - z), True))
    rows_pts, weights, uvs = [], [], []
    length = 0.
    previous = None
    for z, centre, front in path:
        row = []
        for i in range(across):
            u = i / (across - 1)
            x = centre + (u - .5) * (.084 + .034 * smoothstep(1.40, 1.30, z))
            ripple = .004 * math.sin(u * math.tau * 1.5 + z * 20)
            y = kurta_surface_y(x, min(z, 1.425), True, .012) - ripple
            row.append((x, y, z))
        rows_pts.append(row)
    # Over the shoulder, close to the neck so the arm can move freely.
    for y_top in (-.045, -.015, .015, .045):
        row = []
        for i in range(across):
            u = i / (across - 1)
            x = .122 + (u - .5) * .080
            z = kurta_top_z(x) + .009 - .010 * (abs(y_top) / .045) ** 2
            row.append((x, y_top, z))
        rows_pts.append(row)
    for z in (1.40, 1.35, 1.28, 1.20, 1.13, 1.08):
        row = []
        for i in range(across):
            u = i / (across - 1)
            x = .120 + (u - .5) * (.084 + .034 * smoothstep(1.40, 1.30, z)) + .01 * (1.40 - z)
            y = kurta_surface_y(x, z, False, .012) + .003 * math.sin(u * math.tau + z * 15)
            row.append((x, y, z))
        rows_pts.append(row)
    for row in rows_pts:
        centre = Vector(row[across // 2])
        if previous is not None:
            length += (centre - previous).length
        previous = centre
        uvs.append([(i / (across - 1), length) for i in range(across)])
        row_weights = []
        for x, y, z in row:
            if z < 1.30 and y < 0:
                row_weights.append(torso_weight(x, z, shoulders=False))
            elif z < 1.30:
                row_weights.append(torso_weight(x, z, shoulders=False))
            else:
                row_weights.append('chest')
        weights.append(row_weights)
    towel = grid_mesh(c, 'Green checked gamchha', rows_pts, cloth, weights, cyclic=False, uv=uvs)
    towel['Garment'] = 'Cotton gamchha; UVMap U runs across the towel, V is length in metres for the checks.'
    for end, row_index in (('front', 0), ('back', len(rows_pts) - 1)):
        row = rows_pts[row_index]
        for i in range(0, across, 1):
            x, y, z = row[i]
            for strand in range(2):
                dx = (strand - .5) * .004
                c.tube(f'Gamchha fringe {end} {i}-{strand}', [(x + dx, y, z + .001), (x + dx * 1.4, y - .001 * (1 if end == 'front' else -1), z - .012),
                       (x + dx * 1.8, y - .0015 * (1 if end == 'front' else -1), z - .022)],
                       [.0011, .0009, .0005], fringe_material, [weights[row_index][i]] * 3)


# --------------------------------------------------------------------- feet and small props
def chappals(c: Civilian, leather, sole) -> None:
    for sign, side in ((1, 'L'), (-1, 'R')):
        foot, toes = f'foot.{side}', f'toes.{side}'
        x = sign * .135
        c.ovoid(f'Chappal sole {side}', (x, -.062, .010), (.064, .136, .0105), sole, foot)
        c.ovoid(f'Chappal footbed {side}', (x, -.062, .0198), (.058, .128, .0022), leather, foot)
        post = (sign * .113, -.152, .028)
        for end in (sign * .186, sign * .086):
            c.tube(f'Chappal strap {side} {end:+.3f}', [post, (x + (end - x) * .45, -.102, .066),
                   (end, -.066, .037), (end, -.052, .022)], [.0040, .0062, .0058, .0045], leather, foot)
        c.ovoid(f'Chappal toe post {side}', post, (.0045, .0045, .006), leather, toes)


def accessories(c: Civilian, brass, thread) -> None:
    # Black amulet thread under the collar, brass tabeez at the base of the throat.
    points = []
    for i in range(33):
        a = -math.pi / 2 + math.tau * i / 32
        z = 1.392 + .028 * (1 + math.sin(a)) / 2
        r_x, r_y = .066 * 1.13, .063 * 1.13
        y = -.004 + (r_y + .004) * math.sin(a)
        if math.sin(a) < 0:
            y -= .020 * (-math.sin(a)) ** 3
        points.append(((r_x + .004) * math.cos(a), y, z - .040 * max(0, -math.sin(a)) ** 4))
    c.tube('Amulet thread', points, .0011, thread, 'chest', cyclic=True)
    c.tube('Brass tabeez', [(0, -.104, 1.364), (0, -.105, 1.346)], .0042, brass, 'chest')
    for z in (1.364, 1.346):
        c.ovoid(f'Tabeez cap {z}', (0, -.105, z), (.0047, .0047, .0021), brass, 'chest')
    # A plain brass ring on the right ring finger, visible on the pointing hand.
    from civilian import FINGERS, KNUCKLE_X
    y, length, radius = FINGERS[2]
    spread = (3 - 2.3) * .045
    direction = Vector((-math.cos(spread), math.sin(spread), -.02)).normalized()
    centre = Vector((-KNUCKLE_X[2], y, 1.371)) + direction * length * .22
    u = Vector((0, 1, 0)).cross(direction).normalized()
    v = direction.cross(u)
    ring = [tuple(centre + (radius * 1.22) * (math.cos(a) * u + math.sin(a) * v))
            for a in (math.tau * i / 24 for i in range(24))]
    with c.arm_space(-1):
        c.tube('Brass finger ring', ring, .0017, brass, 'finger_03.R', cyclic=True)


# --------------------------------------------------------------------- skin
def scalp_hair_density(angle: float, z: float) -> float:
    """Horseshoe fringe of a bald crown: sides, back and short sideburns."""
    a = abs(angle)
    if a < 1.28:
        return 0.
    back = max(0., (a - 1.3) / (math.pi - 1.3))
    high = 1.716 + .024 * back ** 1.4 + .003 * math.sin(9 * angle) + .002 * math.sin(23 * angle)
    low = 1.645 - .105 * smoothstep(1.55, 2.6, a)
    ear = 1.44 < a < 1.95 and z < 1.690 - .02 * smoothstep(1.80, 1.95, a)
    if ear:
        return 0.
    edge = min(smoothstep(high + .003, high - .016, z), smoothstep(low - .006, low + .006, z),
               smoothstep(1.28, 1.36, a))
    return max(0., edge)


CAVITY: list = []  # set by finish(): the character's relief function


def skin_tint(x: float, y: float, z: float) -> tuple[float, float, float, float]:
    angle = math.atan2(x, -(y + .008))
    cavity = 0.
    if CAVITY and y < -.04 and 1.49 < z < 1.76:
        depth = CAVITY[0](x, z)
        cavity = max(-1., min(1., depth / .006))
    r = g = b = 1.
    sheen = 0.
    hair = scalp_hair_density(angle, z)
    front = smoothstep(-.03, -.09, y)
    stubble = front * smoothstep(1.625, 1.585, z) * smoothstep(1.47, 1.50, z)
    stubble *= 1 - .7 * gaussian(x, z, 0, 1.566, .040, .010)  # lips stay clean
    stubble = max(stubble, .6 * smoothstep(1.62, 1.58, z) * smoothstep(-.05, -.09, y) *
                  smoothstep(.09, .06, abs(x)) * smoothstep(1.555, 1.575, z))
    speckle = .5 + .5 * math.sin(x * 2300) * math.sin(z * 2100 + x * 900)
    stub = stubble * (.10 + .05 * speckle)
    flush = .9 * gaussian(x, z, 0, 1.620, .016, .012) + .7 * gaussian(abs(x), z, .062, 1.615, .028, .022)
    under_eye = gaussian(abs(x), z, .050, 1.653, .022, .006)
    r *= (1 - .62 * hair) * (1 - stub) * (1 + .07 * flush) * (1 - .10 * under_eye)
    g *= (1 - .63 * hair) * (1 - stub) * (1 - .045 * flush) * (1 - .13 * under_eye)
    b *= (1 - .58 * hair) * (1 - stub * .7) * (1 - .05 * flush) * (1 - .09 * under_eye)
    shade = 1 - .22 * max(0., cavity) + .05 * max(0., -cavity)
    r, g, b = r * shade, g * shade * .99, b * shade * .98
    crown = smoothstep(1.70, 1.76, z) * (1 - hair)
    r, g, b = r * (1 + .03 * crown), g * (1 + .01 * crown), b * (1 - .01 * crown)
    for sx, sz, size in ((.052, 1.772, .006), (-.034, 1.79, .004), (.081, 1.745, .005), (-.072, 1.733, .0045)):
        spot = gaussian(x, z, sx, sz, size, size) * smoothstep(-.02, -.07, y)
        r, g, b = r * (1 - .12 * spot), g * (1 - .15 * spot), b * (1 - .15 * spot)
    sheen -= .22 * crown + .10 * gaussian(x, z, 0, 1.735, .05, .03) * front
    sheen -= .12 * gaussian(x, z, 0, 1.622, .015, .015)
    sheen += .10 * hair
    return r, g, b, sheen


def mole(c: Civilian, material) -> None:
    x, z = .060, 1.583
    y = c.face_y(x, z) - .0008
    c.ovoid('Cheek mole', (x, y, z), (.0034, .0016, .0032), material, 'head', (0, 0, -.5))


# --------------------------------------------------------------------- groom
def head_tree(c: Civilian) -> BVHTree:
    head = next(part.data for part in c.parts if part.name == f'{c.name}_Head')
    coords = [v.co / c.scale for v in head.vertices]
    return BVHTree.FromPolygons(coords, [tuple(face.vertices) for face in head.polygons])


def scalp_fringe(c: Civilian, head: BVHTree, rand: random.Random, fibers: FiberGroup, count: int) -> None:
    made = 0
    attempts = 0
    while made < count and attempts < count * 12:
        attempts += 1
        angle = rand.uniform(-math.pi, math.pi)
        z = rand.uniform(1.535, 1.752)
        density = scalp_hair_density(angle, z)
        if rand.random() > density:
            continue
        side = 1 if angle > 0 else -1
        a = abs(angle)
        length = rand.uniform(.010, .024) * (1.25 if a > 2.4 else 1)
        sideburn = a < 1.45
        path = []
        for i in range(6):
            t = i / 5
            # Combed back above the ears, down at the nape and the sideburns.
            back = (.55 if not sideburn else .05) * length * t / .02 * .10
            down = length * t * (.62 if a > 1.9 or sideburn else .38)
            theta = angle + side * back * 1.0
            point, normal = surface(head, theta, z - down)
            lift = .0010 + .0024 * math.sin(math.pi * t) * (1 - .4 * t) + .0006 * t
            path.append(point + normal * lift)
        shade = rand.choice((0, 0, 0, 0, 1, 1, 2, 3, 5, 6))
        fibers.add(path, rand.uniform(.00013, .00025), shade, min(6, shade + 1))
        made += 1


def handlebar_path(s: float) -> tuple[float, float, float]:
    """Centre line of one side of the moustache: (x, z, half thickness) for s in 0..1."""
    keys = ((0.0, .004, 1.589, .0085), (.18, .020, 1.585, .0102), (.38, .038, 1.577, .0102),
            (.55, .053, 1.571, .0086), (.70, .067, 1.574, .0064), (.82, .077, 1.583, .0045),
            (.92, .083, 1.594, .0028), (1.0, .082, 1.604, .0012))
    for (s0, x0, z0, h0), (s1, x1, z1, h1) in zip(keys, keys[1:]):
        if s <= s1:
            t = (s - s0) / (s1 - s0)
            t = t * t * (3 - 2 * t)
            return x0 + (x1 - x0) * t, z0 + (z1 - z0) * t, h0 + (h1 - h0) * t
    return keys[-1][1:]


def moustache_point(c: Civilian, x: float, z: float, standoff: float) -> Vector:
    return Vector((x, c.face_y(x, z) - standoff, z))


def handlebar(c: Civilian, rand: random.Random, fibers: FiberGroup, count: int) -> None:
    for index in range(count):
        sign = 1 if index % 2 else -1
        s0 = rand.random() ** 1.4 * .52
        reach = rand.uniform(.25, .62) * (1.15 if s0 < .2 else 1)
        s1 = min(1., s0 + reach)
        offset = rand.uniform(-1, 1)
        wander = rand.uniform(-.0016, .0016)
        lift_bias = rand.uniform(-.0012, .0012)
        path = []
        for i in range(7):
            t = i / 6
            s = s0 + (s1 - s0) * t
            x, z, half = handlebar_path(s)
            converge = 1 - .35 * t
            z += offset * half * converge + wander * math.sin(math.pi * t)
            out = smoothstep(.55, 1.0, s)
            # Root on the skin, body stands proud of the lip, tips curl off the cheek.
            standoff = .0012 + .0050 * math.sin(math.pi * min(1, t * 1.3)) * (1 - out) + .0105 * out + .0016 * (1 - abs(offset))
            path.append(moustache_point(c, sign * x, z, standoff + lift_bias * math.sin(math.pi * t)))
        shade = rand.choice((0, 0, 0, 0, 0, 1, 1, 1, 2, 2, 3, 5, 6))
        fibers.add(path, rand.uniform(.00009, .00019), shade, min(6, shade + 1))


def moustache_mass(c: Civilian, material) -> None:
    """A soft dark core under the strands so the moustache reads in wide shots."""
    for sign, side in ((1, 'L'), (-1, 'R')):
        points, radii = [], []
        for i in range(15):
            s = i / 14 * .97
            x, z, half = handlebar_path(s)
            out = smoothstep(.55, 1.0, s)
            points.append(tuple(moustache_point(c, sign * x, z, .0024 + .0098 * out)))
            radii.append(half * .40)
        c.tube(f'Handlebar moustache core {side}', points, radii, material, 'head')


def brow_fibers(c: Civilian, rand: random.Random, fibers: FiberGroup, sign: int, count: int) -> None:
    ex = c.face_params['eye_x']
    lift_spec = c.spec.get('brow_lift', 0)
    for _ in range(count):
        position = rand.random()
        x = ex + (position - .45) * .074
        z = 1.7045 + (lift_spec + .010) * math.sin(position * math.pi) ** 1.3 + rand.uniform(-.0035, .0025)
        path = []
        for i in range(5):
            t = i / 4
            hair_x = sign * (x + (.010 + .005 * position) * t)
            hair_z = z + (.0060 * (.7 - position) + rand.uniform(-.0012, .0024)) * t
            lift = .0011 + (.0034 + .0018 * math.sin(math.pi * position)) * math.sin(math.pi * t) ** .6
            path.append(Vector((hair_x, c.face_y(hair_x, hair_z) - lift, hair_z)))
        shade = rand.choice((0, 0, 0, 1, 1, 2, 2, 3, 5, 6))
        fibers.add(path, rand.uniform(.00016, .00027), shade, min(shade + 1, 6))


def lashes(c: Civilian, rand: random.Random, fibers: FiberGroup, sign: int) -> None:
    for lower, count in ((False, 52), (True, 22)):
        for _ in range(count):
            angle = rand.uniform(.12, math.pi - .12)
            angle = -angle if lower else angle
            x, z = c.eyelid_point(sign, angle, 1.03)
            base = Vector((x, c.face_y(x, z) - .0024, z))
            length = rand.uniform(.0045, .0075) * (.55 if lower else 1) * (.6 + .4 * math.sin(abs(angle)))
            outward = (x - sign * c.face_params['eye_x']) * .25
            path = []
            for i in range(4):
                t = i / 3
                vertical = (-1 if lower else 1) * length * (.25 * t + .55 * t * t)
                path.append(base + Vector((outward * t, -length * .85 * t, vertical)))
            fibers.add(path, rand.uniform(.00007, .00011), 0, 1)


def groom(c: Civilian) -> dict[str, int]:
    head = head_tree(c)
    rand = random.Random(1187)
    palette = FiberGroup(c, (.008, .007, .006), (.30, .29, .28))
    scalp_fringe(c, head, rand, palette, 7000)
    palette.make_mesh('Fringe groom fibers')
    handlebar(c, rand, palette, 6500)
    palette.make_mesh('Handlebar moustache fibers')
    moustache_mass(c, c.mat('Moustache core', (.010, .008, .008), .62))
    for sign, side in ((1, 'L'), (-1, 'R')):
        brow_fibers(c, rand, palette, sign, 230)
        palette.make_mesh(f'Brow fibers.{side}')
        lashes(c, rand, palette, sign)
        palette.make_mesh(f'Lash fibers.{side}')
    return {'scalp': 7000, 'moustache': 6500, 'brows': 460, 'lashes': 148}


# --------------------------------------------------------------------- materials
def stained_kurta(material) -> None:
    """Turmeric dye with ghee and syrup stains on the belly and darker hems."""
    tree = material.node_tree
    nodes, links = tree.nodes, tree.links
    textile = next(node for node in nodes if node.type == 'GROUP')
    dye = textile.inputs['Dye'].default_value[:]
    rest = nodes.new('ShaderNodeAttribute')
    rest.attribute_name = 'TextileRest'
    rest.location = (-1500, 500)
    noise = nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 7.5
    noise.inputs['Detail'].default_value = 6
    noise.inputs['Roughness'].default_value = .62
    noise.location = (-1300, 650)
    links.new(rest.outputs['Vector'], noise.inputs['Vector'])
    blotch = nodes.new('ShaderNodeMapRange')
    blotch.inputs['From Min'].default_value = .56
    blotch.inputs['From Max'].default_value = .66
    blotch.location = (-1100, 650)
    links.new(noise.outputs['Fac'], blotch.inputs['Value'])
    xyz = nodes.new('ShaderNodeSeparateXYZ')
    xyz.location = (-1300, 380)
    links.new(rest.outputs['Vector'], xyz.inputs[0])
    front = nodes.new('ShaderNodeMapRange')
    front.inputs['From Min'].default_value = -.06
    front.inputs['From Max'].default_value = -.16
    front.location = (-1100, 420)
    links.new(xyz.outputs['Y'], front.inputs['Value'])
    belly = nodes.new('ShaderNodeMapRange')
    belly.interpolation_type = 'SMOOTHSTEP'
    belly.inputs['From Min'].default_value = .70
    belly.inputs['From Max'].default_value = .95
    belly.location = (-1100, 250)
    links.new(xyz.outputs['Z'], belly.inputs['Value'])
    mask = nodes.new('ShaderNodeMath')
    mask.operation = 'MULTIPLY'
    mask.location = (-900, 420)
    links.new(front.outputs['Result'], mask.inputs[0])
    links.new(belly.outputs['Result'], mask.inputs[1])
    stain = nodes.new('ShaderNodeMath')
    stain.operation = 'MULTIPLY'
    stain.location = (-720, 560)
    links.new(blotch.outputs['Result'], stain.inputs[0])
    links.new(mask.outputs['Value'], stain.inputs[1])
    hem = nodes.new('ShaderNodeMapRange')
    hem.inputs['From Min'].default_value = .64
    hem.inputs['From Max'].default_value = .57
    hem.inputs['To Max'].default_value = .55
    hem.location = (-900, 180)
    links.new(xyz.outputs['Z'], hem.inputs['Value'])
    total = nodes.new('ShaderNodeMath')
    total.operation = 'ADD'
    total.use_clamp = True
    total.location = (-560, 400)
    links.new(stain.outputs['Value'], total.inputs[0])
    links.new(hem.outputs['Result'], total.inputs[1])
    mix = nodes.new('ShaderNodeMixRGB')
    mix.location = (-400, 420)
    mix.inputs[1].default_value = dye
    mix.inputs[2].default_value = (dye[0] * .62, dye[1] * .50, dye[2] * .34, 1)
    links.new(total.outputs['Value'], mix.inputs[0])
    links.new(mix.outputs['Color'], textile.inputs['Dye'])


def checked_towel(material, base: tuple[float, float, float], stripe: tuple[float, float, float],
                  dark: tuple[float, float, float]) -> None:
    tree = material.node_tree
    nodes, links = tree.nodes, tree.links
    textile = next(node for node in nodes if node.type == 'GROUP')
    uv = nodes.new('ShaderNodeUVMap')
    uv.uv_map = 'UVMap'
    uv.location = (-1500, 500)
    split = nodes.new('ShaderNodeSeparateXYZ')
    split.location = (-1320, 500)
    links.new(uv.outputs['UV'], split.inputs[0])

    def bands(socket, repeat: float, duty: float, y: float):
        scaled = nodes.new('ShaderNodeMath')
        scaled.operation = 'MULTIPLY'
        scaled.inputs[1].default_value = repeat
        scaled.location = (-1140, y)
        links.new(socket, scaled.inputs[0])
        frac = nodes.new('ShaderNodeMath')
        frac.operation = 'FRACT'
        frac.location = (-980, y)
        links.new(scaled.outputs['Value'], frac.inputs[0])
        test = nodes.new('ShaderNodeMath')
        test.operation = 'LESS_THAN'
        test.inputs[1].default_value = duty
        test.location = (-820, y)
        links.new(frac.outputs['Value'], test.inputs[0])
        return test.outputs['Value']

    across_wide = bands(split.outputs['X'], 3.0, .26, 640)
    along_wide = bands(split.outputs['Y'], 13.0, .26, 470)
    across_thin = bands(split.outputs['X'], 9.0, .08, 300)
    along_thin = bands(split.outputs['Y'], 39.0, .08, 140)
    plaid = nodes.new('ShaderNodeMath')
    plaid.operation = 'MAXIMUM'
    plaid.location = (-640, 560)
    links.new(across_wide, plaid.inputs[0])
    links.new(along_wide, plaid.inputs[1])
    crossing = nodes.new('ShaderNodeMath')
    crossing.operation = 'MULTIPLY'
    crossing.location = (-640, 400)
    links.new(across_wide, crossing.inputs[0])
    links.new(along_wide, crossing.inputs[1])
    thin = nodes.new('ShaderNodeMath')
    thin.operation = 'MAXIMUM'
    thin.location = (-640, 230)
    links.new(across_thin, thin.inputs[0])
    links.new(along_thin, thin.inputs[1])
    first = nodes.new('ShaderNodeMixRGB')
    first.location = (-460, 560)
    first.inputs[1].default_value = (*base, 1)
    first.inputs[2].default_value = (*stripe, 1)
    links.new(plaid.outputs['Value'], first.inputs[0])
    second = nodes.new('ShaderNodeMixRGB')
    second.location = (-300, 470)
    second.inputs[2].default_value = (*dark, 1)
    links.new(crossing.outputs['Value'], second.inputs[0])
    links.new(first.outputs['Color'], second.inputs[1])
    third = nodes.new('ShaderNodeMixRGB')
    third.location = (-150, 380)
    third.inputs[2].default_value = (*dark, 1)
    factor = nodes.new('ShaderNodeMath')
    factor.operation = 'MULTIPLY'
    factor.inputs[1].default_value = .7
    factor.location = (-300, 230)
    links.new(thin.outputs['Value'], factor.inputs[0])
    links.new(factor.outputs['Value'], third.inputs[0])
    links.new(second.outputs['Color'], third.inputs[1])
    links.new(third.outputs['Color'], textile.inputs['Dye'])


# --------------------------------------------------------------------- facial rig additions
def extend_facial_controls(c: Civilian) -> None:
    """Blink, brow and lip-follow keys for the parts the shared facial rig does not know."""
    rig, scale = c.rig, c.scale
    objects = {obj.name.removeprefix(f'{c.name}_'): obj for obj in c.parts}
    for side in ('L', 'R'):
        for label, eyelid in ((f'Cornea.{side}', False), (f'Upper lash line.{side}', True),
                              (f'Lash fibers.{side}', True)):
            obj = objects.get(label)
            if obj is None:
                continue

            def blink(point: Vector, eyelid: bool = eyelid) -> Vector:
                point.z = 1.675 * scale + (point.z - 1.675 * scale) * (.035 if not eyelid else .12)
                point.y += (-.003 if eyelid else .028) * scale
                return point
            key = face_controls.shape_from_delta(obj, 'Blink', blink)
            face_controls.driver_from_property(key, rig, f'blink_{side}')
        brow = objects.get(f'Brow fibers.{side}')
        if brow is not None:
            for name, delta, prop in (('Raise', .0065, 'brow_raise'), ('Frown', -.005, 'brow_frown')):
                def reshape(point: Vector, amount: float = delta) -> Vector:
                    weight = max(.25, 1 - abs(point.x) / (.11 * scale))
                    point.z += amount * scale * weight
                    return point
                key = face_controls.shape_from_delta(brow, name, reshape)
                face_controls.driver_from_property(key, rig, prop)
    for label in ('Handlebar moustache fibers', 'Handlebar moustache core L', 'Handlebar moustache core R'):
        obj = objects.get(label)
        if obj is None:
            continue

        def lip_follow(point: Vector) -> Vector:
            centre = max(0., 1 - abs(point.x) / (.07 * scale))
            point.z += .0042 * scale * centre
            point.y -= .0012 * scale * centre
            return point
        key = face_controls.shape_from_delta(obj, 'Lip follow', lip_follow)
        curve = key.driver_add('value')
        driver = curve.driver
        driver.type = 'SCRIPTED'
        for prop in ('Mouth_Ah', 'Mouth_O', 'Mouth_U'):
            variable = driver.variables.new()
            variable.name = prop
            variable.type = 'SINGLE_PROP'
            variable.targets[0].id = rig
            variable.targets[0].data_path = f'["{prop}"]'
        driver.expression = 'min(1,max(Mouth_Ah,Mouth_O*.8,Mouth_U*.7))'


# --------------------------------------------------------------------- wardrobe
def dress(c: Civilian) -> dict[str, int]:
    turmeric = c.mat('Turmeric cotton kurta', (.46, .27, .034), .9)
    binding = c.mat('Kurta self binding', (.35, .195, .024), .9)
    button = c.mat('Cloth-covered buttons', (.33, .185, .024), .9)
    cotton = c.mat('Unbleached dhoti cotton', (.50, .45, .36), .93)
    border = c.mat('Dhoti brown border', (.16, .085, .045), .9)
    towel = c.mat('Green checked gamchha', (.56, .52, .40), .92)
    fringe = c.mat('Gamchha fringe', (.50, .47, .37), .94)
    leather = c.mat('Oiled leather strap', (.13, .065, .030), .62)
    sole = c.mat('Worn leather sole', (.075, .045, .028), .8)
    brass = c.mat('Brass', (.42, .26, .085), .38, .85)
    thread = c.mat('Black cotton thread', (.012, .011, .011), .8)
    spot = c.mat('Mole', tuple(v * .32 for v in c.spec['skin']), .7)
    kurta(c, turmeric, binding, button)
    dhoti(c, cotton, border)
    gamchha(c, towel, fringe)
    chappals(c, leather, sole)
    accessories(c, brass, thread)
    mole(c, spot)
    return {'garments': 4}


def finish(c: Civilian) -> None:
    fabrics = {'Turmeric cotton kurta', 'Kurta self binding', 'Cloth-covered buttons', 'Unbleached dhoti cotton',
               'Dhoti brown border', 'Green checked gamchha', 'Gamchha fringe'}
    finished = set()
    for part in c.parts:
        uses = False
        for material in part.data.materials:
            label = material.name.partition(' • ')[2]
            if label in fabrics:
                uses = True
                if material.name not in finished:
                    finish_fabric(material, fine=False)
                    finished.add(material.name)
        if uses:
            store_rest_positions(part.data)
    stained_kurta(bpy.data.materials[f'{c.name} • Turmeric cotton kurta'])
    checked_towel(bpy.data.materials[f'{c.name} • Green checked gamchha'],
                  (.56, .52, .40), (.075, .20, .075), (.025, .075, .035))
    CAVITY[:] = [c.relief]
    c.apply_skin_tint(skin_tint)


# --------------------------------------------------------------------- poses
Rotation = tuple[tuple[float, float, float], float]


def rotate(rig, bone_name: str, rotations: Sequence[Rotation]) -> None:
    """Rotate a bone about axes of the rest-pose armature space, applied in order."""
    bone = rig.pose.bones[bone_name]
    rest = bone.bone.matrix_local.to_quaternion()
    total = Quaternion()
    for axis, degrees in rotations:
        total = Quaternion(axis, math.radians(degrees)) @ total
    bone.rotation_mode = 'QUATERNION'
    bone.rotation_quaternion = rest.inverted() @ total @ rest


def aim_bone(rig, bone_name: str, direction: Sequence[float], twist: float = 0) -> None:
    """Point a bone, from its rest direction, along an armature-space direction, plus a twist."""
    bone = rig.pose.bones[bone_name]
    rest = bone.bone.matrix_local.to_quaternion()
    rest_direction = (bone.bone.tail_local - bone.bone.head_local).normalized()
    target = Vector(direction).normalized()
    swing = rest_direction.rotation_difference(target)
    roll = Quaternion(target, math.radians(twist))
    bone.rotation_mode = 'QUATERNION'
    bone.rotation_quaternion = rest.inverted() @ (roll @ swing) @ rest


def curl(rig, side: str, digit: int, angles: tuple[float, float, float]) -> None:
    sign = 1 if side == 'L' else -1
    for segment, degrees in zip(('', '_mid', '_tip'), angles):
        rotate(rig, f'finger_{digit:02d}{segment}.{side}', [((0, 1, 0), sign * degrees)])


def clear_pose(rig) -> None:
    for bone in rig.pose.bones:
        bone.rotation_mode = 'QUATERNION'
        bone.rotation_quaternion = Quaternion()
        bone.location = (0, 0, 0)
    for prop in list(rig.keys()):
        if isinstance(rig[prop], float):
            rig[prop] = 0.


def relaxed_pose(rig) -> None:
    clear_pose(rig)
    for side, sign in (('L', 1), ('R', -1)):
        rotate(rig, f'upper_arm.{side}', [((0, 1, 0), sign * 71), ((0, 0, 1), sign * 4)])
        rotate(rig, f'forearm.{side}', [((0, 0, 1), sign * -14)])
        rotate(rig, f'hand.{side}', [((1, 0, 0), sign * 6), ((0, 1, 0), sign * 6)])
        for digit, base in enumerate((12, 16, 20, 24), 1):
            curl(rig, side, digit, (base, base * 1.2, base * .8))
        rotate(rig, f'thumb.{side}', [((0, 0, 1), sign * -8), ((0, 1, 0), sign * 10)])
        rotate(rig, f'thumb_tip.{side}', [((0, 1, 0), sign * 12)])
    rotate(rig, 'chest', [((1, 0, 0), -1.5)])
    rotate(rig, 'head', [((1, 0, 0), 2)])


def pointing_pose(rig, yaw: float = 52, pitch: float = -6, mouth: float = .18) -> None:
    """Right arm points across the mandi to the gate; weight on the right foot, head along the arm.

    yaw: degrees from straight ahead toward his right; pitch: negative points down.
    """
    clear_pose(rig)
    y, p = math.radians(yaw), math.radians(pitch)
    direction = (-math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p))
    rotate(rig, 'hips', [((0, 0, 1), -6), ((0, 1, 0), -2)])
    rotate(rig, 'spine', [((0, 0, 1), -5), ((1, 0, 0), -2)])
    rotate(rig, 'chest', [((0, 0, 1), -9), ((1, 0, 0), -3), ((0, 1, 0), 3)])
    rotate(rig, 'neck', [((0, 0, 1), -10)])
    rotate(rig, 'head', [((0, 0, 1), -16), ((1, 0, 0), pitch * .5 - 2), ((0, 1, 0), -3)])
    for side in ('L', 'R'):
        rotate(rig, f'eye.{side}', [((0, 0, 1), -9), ((1, 0, 0), pitch * .6)])
    aim_bone(rig, 'upper_arm.R', direction, twist=0)
    rotate(rig, 'forearm.R', [((0, 0, 1), 9)])
    rotate(rig, 'hand.R', [((0, 1, 0), 4), ((0, 0, 1), -4)])
    curl(rig, 'R', 1, (2, 4, 2))
    curl(rig, 'R', 2, (82, 100, 55))
    curl(rig, 'R', 3, (88, 102, 55))
    curl(rig, 'R', 4, (92, 98, 52))
    rotate(rig, 'thumb.R', [((0, 0, 1), 14), ((0, 1, 0), -22)])
    rotate(rig, 'thumb_tip.R', [((0, 1, 0), -24)])
    # Left hand rests on the belly, fingers loose.
    rotate(rig, 'upper_arm.L', [((0, 1, 0), 66), ((0, 0, 1), -22)])
    rotate(rig, 'forearm.L', [((0, 0, 1), -88), ((1, 0, 0), 10)])
    rotate(rig, 'hand.L', [((0, 1, 0), -8), ((1, 0, 0), 26)])
    for digit, base in enumerate((14, 18, 22, 26), 1):
        curl(rig, 'L', digit, (base, base * 1.1, base * .8))
    rotate(rig, 'thumb.L', [((0, 0, 1), -6)])
    for side, sign in (('L', 1), ('R', -1)):
        rotate(rig, f'thigh.{side}', [((0, 0, 1), -4), ((0, 1, 0), sign * -2)])
    rotate(rig, 'thigh.R', [((1, 0, 0), -4)])
    rotate(rig, 'shin.R', [((1, 0, 0), 5)])
    rotate(rig, 'foot.R', [((1, 0, 0), -2)])
    rig['brow_raise'] = .35
    rig['Mouth_Ah'] = mouth
    rig['mouth_smile'] = .1
