"""Realistic hands as sculpted volumes, for close-ups where the hands do the acting.

The tube-and-ring hands of the shared cast read as mannequin fingers up close:
a blocky palm, a ledge at the knuckles and nails like stickers. Here each hand
is one signed-distance volume (sdf_sculpt): a palm with thenar and hypothenar
pads and a cupped hollow, knuckle heads, phalanges that swell at the joints,
fingertip pads, flexion creases and recessed nail beds. Separate nail plates
with a thickness and a pale free edge sit in the beds.

Everything is built in the rig's rest pose (T-pose: left hand along +x, palm
down, thumb toward -y) in the character's design coordinates, then mirrored
for the right hand. Skin weights come from the digit bones: each vertex rides
the nearest digit, blended across its joints, the palm and the wrist.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

import bpy
import numpy as np
from mathutils import Vector

from sdf_sculpt import Sculpt, capsule, ellipsoid, sphere, surface_nets, taubin

Array = np.ndarray
Point = Tuple[float, float, float]

STEP = .00058            # voxel size in design metres (about 0.5 mm on a 1.54 m woman)


@dataclass(frozen=True)
class Digit:
    """One finger or the thumb: its four joints (base, two knuckles, tip) and bone names."""
    joints: Tuple[Point, Point, Point, Point]
    radius: float
    bones: Tuple[str, str, str]          # proximal, middle, distal
    up: Point = (0.0, 0.0, 1.0)          # the back of the digit (nail side)


@dataclass(frozen=True)
class HandSpec:
    """Rest-pose layout of a left hand (x > 0). The right hand is its mirror."""
    fingers: Tuple[Digit, ...]           # index to little finger
    thumb: Digit
    wrist_x: float                       # where the forearm meets the hand
    z: float                             # height of the hand's mid-plane
    forearm: str = 'forearm'
    hand: str = 'hand'


def _v(p: Sequence[float]) -> Array:
    return np.array(p, dtype=np.float64)


def _unit(v: Array) -> Array:
    return v/np.linalg.norm(v)


def smooth(a: float, b: float, x):
    t = np.clip((x - a)/(b - a), 0, 1)
    return t*t*(3 - 2*t)


# ------------------------------------------------------------------ sculpt

def _digit_shapes(s: Sculpt, d: Digit, thumb: bool) -> None:
    j = [_v(p) for p in d.joints]
    up = _unit(_v(d.up))
    r = d.radius
    direction = [_unit(j[i + 1] - j[i]) for i in range(3)]
    lengths = [float(np.linalg.norm(j[i + 1] - j[i])) for i in range(3)]
    t = tuple
    # phalanges: thick at the base, swelling a little at each knuckle, a rounded tip
    if thumb:
        s.union(capsule(t(j[0]), t(j[1]), r*1.34, r*1.14), .012)          # metacarpal inside the thenar
    else:
        s.union(capsule(t(j[0] - direction[0]*.006), t(j[1]), r*1.00, r*.90), .0055)
    s.union(capsule(t(j[1]), t(j[2]), r*.90, r*.84), .0028)
    tip_end = j[3] - direction[2]*r*.78
    s.union(capsule(t(j[2]), t(tip_end), r*.84, r*.80), .0022)
    # fingertip pad: fuller on the palm side, ahead of the last knuckle
    pad = j[3] - direction[2]*r*1.25 - up*r*.22
    s.union(sphere(t(pad), r*.80), .0035)
    # knuckle heads on the back
    for i, (lift, size) in enumerate(((.46, .46), (.42, .38))):
        s.union(sphere(t(j[i + 1] + up*r*lift), r*size), .0045)
    # flexion creases across the palm side of each knuckle
    for i in (1, 2):
        side = _unit(np.cross(direction[i], up))
        centre = j[i] - up*r*.96 + direction[i]*.0008
        s.subtract(capsule(t(centre - side*r*.70), t(centre + side*r*.70), .00030, .00030), .0012)
    # fine wrinkles over the back of the middle knuckle
    side = _unit(np.cross(direction[1], up))
    for k, offset in enumerate((-.0022, 0.0, .0024)):
        centre = j[1] + up*r*(.92 + .05*(k == 1)) + direction[1]*offset
        s.subtract(capsule(t(centre - side*r*.40), t(centre + side*r*.40), .00016, .00016), .0005)
    # nail bed: a shallow dish on the back of the last phalanx, open at the free edge
    bed = j[2] + direction[2]*lengths[2]*.60 + up*(r*.84 + .0016)
    width = r*(.66 if not thumb else .70)
    s.subtract(ellipsoid(t(bed), (lengths[2]*.40, width, .0021),
                         (0, 0, math.degrees(math.atan2(direction[2][1], direction[2][0])))), .0007)


def hand_sculpt(spec: HandSpec) -> Sculpt:
    s = Sculpt()
    z = spec.z
    w = spec.wrist_x
    # wrist into the palm: an oval column widening toward the knuckles
    for x, ry, rz in ((w - .014, .0270, .0190), (w + .004, .0285, .0192), (w + .020, .0315, .0190)):
        s.union(ellipsoid((x, 0, z - .001), (.016, ry, rz)), .010)
    index_mcp, little_mcp = _v(spec.fingers[0].joints[0]), _v(spec.fingers[-1].joints[0])
    knuckle_x = float((index_mcp[0] + little_mcp[0])/2)
    s.union(ellipsoid((w + .045, -.001, z - .0018), (.036, .0405, .0172)), .016)         # proximal palm
    s.union(ellipsoid((knuckle_x - .022, -.0005, z - .0014), (.030, .0455, .0150)), .014)  # distal palm
    s.union(ellipsoid((w + .038, -.030, z - .0085), (.031, .0165, .0135), (0, 0, -24)), .012)  # thenar
    s.union(ellipsoid((w + .056, .0335, z - .0062), (.034, .0120, .0112), (0, 0, 4)), .012)   # hypothenar
    s.subtract(ellipsoid((w + .068, .002, z - .0206), (.022, .019, .0058)), .008)        # cupped palm
    for d in spec.fingers:
        mcp = _v(d.joints[0])
        s.union(sphere(tuple(mcp + _v((-.003, 0, .0042))), d.radius*1.02), .007)          # knuckle head
        s.union(ellipsoid(tuple(mcp + _v((-.006, 0, -.0080))), (.0105, d.radius*1.12, .0072)), .008)  # palm pad
    # palm creases: distal and proximal transverse, and the thenar (life) line
    s.subtract(capsule((knuckle_x - .020, little_mcp[1] + .006, z - .0150),
                       (knuckle_x - .016, -.006, z - .0158), .00032, .00032), .0016)
    s.subtract(capsule((knuckle_x - .026, .008, z - .0156),
                       (knuckle_x - .031, -.030, z - .0150), .00032, .00032), .0016)
    for a, b in (((w + .060, -.036, z - .0140), (w + .045, -.020, z - .0170)),
                 ((w + .045, -.020, z - .0170), (w + .022, -.012, z - .0172))):
        s.subtract(capsule(a, b, .00030, .00030), .0015)
    for d in spec.fingers:
        _digit_shapes(s, d, thumb=False)
    _digit_shapes(s, spec.thumb, thumb=True)
    return s


# ------------------------------------------------------------------ weights

def _polyline_param(p: Array, joints: Array) -> Tuple[Array, Array]:
    """Distance from each point to a joint polyline, and arc length of the closest point
    (negative behind the first joint)."""
    best = np.full(len(p), np.inf)
    param = np.zeros(len(p))
    start = 0.0
    for i in range(len(joints) - 1):
        a, b = joints[i], joints[i + 1]
        ab = b - a
        length = float(np.linalg.norm(ab))
        t = (p - a) @ ab/(length*length)
        tc = np.clip(t, 0 if i else -np.inf, 1)
        q = a + tc[:, None]*ab
        d = np.linalg.norm(p - q, axis=1)
        closer = d < best
        best[closer] = d[closer]
        param[closer] = start + tc[closer]*length
        start += length
    return best, param


def hand_weights(p: Array, spec: HandSpec, side: str) -> List[Dict[str, float]]:
    """Per-vertex bone weights (rest pose, left-hand coordinates)."""
    digits = list(spec.fingers) + [spec.thumb]
    distances, digit_w = [], []
    for d in digits:
        joints = np.array(d.joints)
        dist, s = _polyline_param(p, joints)
        lengths = np.linalg.norm(np.diff(joints, axis=0), axis=1)
        k0, k1 = lengths[0], lengths[0] + lengths[1]
        names = [f'{spec.hand}.{side}'] + [f'{b}.{side}' for b in d.bones]
        back, lead = (-.010, .012) if d is spec.thumb else (-.014, .008)
        w = np.stack([1 - smooth(back, lead, s),
                      smooth(back, lead, s)*(1 - smooth(k0 - .0045, k0 + .0045, s)),
                      smooth(k0 - .0045, k0 + .0045, s)*(1 - smooth(k1 - .0038, k1 + .0038, s)),
                      smooth(k1 - .0038, k1 + .0038, s)], axis=1)
        distances.append(dist)
        digit_w.append((names, w))
    dist = np.stack(distances, axis=1)
    share = np.exp(-(dist - dist.min(axis=1, keepdims=True))/.0022)
    share /= share.sum(axis=1, keepdims=True)
    forearm = 1 - smooth(spec.wrist_x - .018, spec.wrist_x + .012, p[:, 0])
    result: List[Dict[str, float]] = [dict() for _ in range(len(p))]
    totals: Dict[str, Array] = {}
    for k, (names, w) in enumerate(digit_w):
        for i, name in enumerate(names):
            totals[name] = totals.get(name, 0) + share[:, k]*w[:, i]
    totals = {name: values*(1 - forearm) for name, values in totals.items()}
    totals[f'{spec.forearm}.{side}'] = forearm
    names = list(totals)
    matrix = np.stack([totals[n] for n in names], axis=1)
    matrix[matrix < .002] = 0
    matrix /= matrix.sum(axis=1, keepdims=True)
    for row, values in enumerate(matrix):
        for n, v in zip(names, values):
            if v > 0:
                result[row][n] = float(v)
    return result


# ------------------------------------------------------------------ nails

def nail_material(name: str) -> bpy.types.Material:
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nodes, links = m.node_tree.nodes, m.node_tree.links
    shader = nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value = .24
    shader.inputs['Coat Weight'].default_value = .35
    shader.inputs['Coat Roughness'].default_value = .12
    shader.inputs['Subsurface Weight'].default_value = .35
    shader.inputs['Subsurface Radius'].default_value = (1.0, .45, .3)
    shader.inputs['Subsurface Scale'].default_value = .0012
    tip = nodes.new('ShaderNodeAttribute')
    tip.attribute_name = 'Nail tip'
    mix = nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.inputs['A'].default_value = (.44, .25, .19, 1)        # the bed's pink through the plate
    mix.inputs['B'].default_value = (.70, .62, .54, 1)        # pale free edge
    links.new(tip.outputs['Fac'], mix.inputs['Factor'])
    links.new(mix.outputs['Result'], shader.inputs['Base Color'])
    m.diffuse_color = (.66, .48, .43, 1)
    return m


def nail_plates(sculpt: Sculpt, d: Digit, thumb: bool) -> Tuple[List[Array], List[Tuple[int, ...]], List[float]]:
    """A thin curved plate on the nail bed: top and bottom sheets joined round the rim."""
    j = [_v(p) for p in d.joints]
    up = _unit(_v(d.up))
    direction = _unit(j[3] - j[2])
    side = _unit(np.cross(direction, up))
    up = _unit(np.cross(side, direction))
    r = d.radius
    length = float(np.linalg.norm(j[3] - j[2]))
    rows, columns = 9, 9
    half = r*(.62 if not thumb else .66)
    origins, dirs, params = [], [], []
    for row in range(rows):
        v = row/(rows - 1)
        along = length*(.30 + .66*v)
        for col in range(columns):
            u = col/(columns - 1)*2 - 1
            w = half*(.82 + .18*math.sin(math.pi*min(1.0, .15 + v)))
            o = j[2] + direction*along + side*u*w*.55
            ray = _unit(up + side*u*.55)
            origins.append(o)
            dirs.append(ray)
            params.append((u, v, w))
    origins_a, dirs_a = np.array(origins), np.array(dirs)
    reach = sculpt.surface_along(origins_a, dirs_a, 0.0, r*2.2)
    # beyond the fingertip the ray finds no skin: carry the last height on, drooping a little
    reach = reach.reshape(rows, columns)
    for row in range(rows):
        for col in range(columns):
            if np.isnan(reach[row, col]):
                above = reach[:row, col]
                found = above[~np.isnan(above)]
                reach[row, col] = (found[-1] if len(found) else r*.85) - .0006
    top, bottom, tint = [], [], []
    for (o, ray, (u, v, w)), dist in zip(zip(origins_a, dirs_a, params), reach.ravel()):
        edge = 1 - u*u
        lift = .00012 + .00030*edge                # thicker in the middle, feathered at the sides
        base = o + ray*(dist - .00020)
        top.append(base + up*lift + up*.00025*v*v)
        bottom.append(base - up*.00005)
        tint.append(float(smooth(.80, .95, v)))
    verts = top + bottom
    faces: List[Tuple[int, ...]] = []
    n = rows*columns
    for row in range(rows - 1):
        for col in range(columns - 1):
            a = row*columns + col
            faces.append((a, a + 1, a + columns + 1, a + columns))
            faces.append((n + a, n + a + columns, n + a + columns + 1, n + a + 1))
    rim = ([c for c in range(columns)] + [r_*columns + columns - 1 for r_ in range(1, rows)]
           + [(rows - 1)*columns + c for c in range(columns - 2, -1, -1)] + [r_*columns for r_ in range(rows - 2, 0, -1)])
    for a, b in zip(rim, rim[1:] + rim[:1]):
        faces.append((b, a, n + a, n + b))
    return verts, faces, tint + tint


# ------------------------------------------------------------------ build

def _decimated(verts: Array, quads: Array, ratio: float) -> Tuple[Array, List[Tuple[int, ...]]]:
    """Collapse-decimate a raw surface-nets mesh (about 200k verts a hand) before it is skinned."""
    mesh = bpy.data.meshes.new('hand decimate (temp)')
    mesh.from_pydata([tuple(v) for v in verts], [], [tuple(q) for q in quads.tolist()])
    mesh.update()
    obj = bpy.data.objects.new(mesh.name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    modifier = obj.modifiers.new('Decimate', 'DECIMATE')
    modifier.ratio = ratio
    depsgraph = bpy.context.evaluated_depsgraph_get()
    result = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    co = np.empty(len(result.vertices)*3)
    result.vertices.foreach_get('co', co)
    faces = [tuple(p.vertices) for p in result.polygons]
    bpy.data.meshes.remove(result)
    return co.reshape(-1, 3), faces


def build_hand(c, spec: HandSpec, side: str, sign: int, skin, nail_mat=None):
    """Sculpt, mesh, skin and add nails for one hand; returns (hand, nails) objects."""
    sculpt = hand_sculpt(spec)
    xs = [p[0] for d in spec.fingers for p in d.joints]
    lo = (spec.wrist_x - .032, min(p[1] for d in spec.fingers + (spec.thumb,) for p in d.joints) - .022, spec.z - .036)
    hi = (max(xs) + .010, max(p[1] for d in spec.fingers for p in d.joints) + .024, spec.z + .030)
    values, origin = sculpt.grid(lo, hi, STEP)
    verts, quads = surface_nets(values, origin, STEP)
    del values
    # the open wrist end tucks into the forearm sleeve: drop the faces behind it
    keep = verts[:, 0] > spec.wrist_x - .028
    quads = quads[np.all(keep[quads], axis=1)]
    used = np.unique(quads)
    remap = np.full(len(verts), -1)
    remap[used] = np.arange(len(used))
    verts, quads = verts[used], remap[quads]
    verts = taubin(verts, quads, rounds=4)
    verts, faces_l = _decimated(verts, quads, .30)
    weights = hand_weights(verts, spec, side)
    mirrored = verts*np.array((sign, 1, 1))
    faces = [tuple(f) if sign > 0 else tuple(reversed(f)) for f in faces_l]
    hand = c.mesh(f'Hand.{side}', [tuple(v) for v in mirrored], faces, skin, weights)
    hand['Topology'] = 'Sculpted volume (sculpted_hand.py): one watertight hand, weights from the digit bones.'
    # nails
    material = nail_mat or nail_material(f'{c.name} • Fingernail')
    n_verts, n_faces, n_tint, n_weights = [], [], [], []
    for k, d in enumerate(spec.fingers + (spec.thumb,)):
        v, f, tint = nail_plates(sculpt, d, d is spec.thumb)
        base = len(n_verts)
        n_verts += [tuple(p*np.array((sign, 1, 1))) for p in v]
        n_faces += [tuple(base + i for i in (face if sign > 0 else face[::-1])) for face in f]
        n_tint += tint
        n_weights += hand_weights(np.array(v), spec, side)     # ride exactly as the skin under them
    nails = c.mesh(f'Fingernails.{side}', n_verts, n_faces, material, n_weights)
    nails.data.materials[0] = material
    layer = nails.data.color_attributes.new('Nail tip', 'FLOAT_COLOR', 'POINT')
    rgba = np.ones((len(n_tint), 4), dtype=np.float32)
    rgba[:, :3] = np.array(n_tint)[:, None]
    layer.data.foreach_set('color', rgba.ravel())
    return hand, nails
