"""Shared paper mesh, fold shape keys, oil-cloth bundle and ledger for the evidence props.

Units are metres. Paper is 0.24 x 0.32 m (portrait, texture 1200 x 1600 px), UV mapped
1:1 so every page uses the same mesh and only the texture differs.
"""

import math
from pathlib import Path

import bpy
from mathutils import Vector

PAPER_W, PAPER_H, THICK = .24, .32, .0006
NX, NY = 24, 32  # grid quads
TEX = Path(__file__).resolve().parents[1] / 'Props' / 'Documents' / 'Textures'


def paper_mesh(name):
    """A thin double-sided sheet: front and back grids, shared edge ring, full UVs."""
    verts, faces, uvs = [], [], []
    for side, z in ((0, THICK/2), (1, -THICK/2)):
        for j in range(NY+1):
            for i in range(NX+1):
                verts.append((i/NX*PAPER_W - PAPER_W/2, j/NY*PAPER_H - PAPER_H/2, z))
    stride = (NX+1)*(NY+1)
    for j in range(NY):
        for i in range(NX):
            a = j*(NX+1)+i
            faces.append((a, a+1, a+NX+2, a+NX+1))
            faces.append((stride+a, stride+a+NX+1, stride+a+NX+2, stride+a+1))
    # close the rim with quads between matching front/back boundary verts
    boundary = ([j*(NX+1) for j in range(NY+1)] + [NY*(NX+1)+i for i in range(1, NX+1)] +
                [(NY-j)*(NX+1)+NX for j in range(1, NY+1)] + [NX-i for i in range(1, NX)])
    for k in range(len(boundary)):
        a, b = boundary[k], boundary[(k+1) % len(boundary)]
        faces.append((a, stride+a, stride+b, b))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    uv = mesh.uv_layers.new(name='UVMap')
    for poly in mesh.polygons:
        for loop in poly.loop_indices:
            x, y, _ = verts[mesh.loops[loop].vertex_index]
            front = poly.vertices[0] < stride
            u = (x + PAPER_W/2)/PAPER_W
            uv.data[loop].uv = (u if front else 1-u, (y + PAPER_H/2)/PAPER_H)
    for p in mesh.polygons:
        p.use_smooth = False
    mesh.update()
    return mesh


def add_fold_keys(obj):
    """Shape keys: Basis, Fold_Half (folded across the middle), Fold_Third (letter fold),
    Corner_Curl (lower right corner lifts) and Crumple (soft wrinkles)."""
    obj.shape_key_add(name='Basis')
    base = [Vector(v.co) for v in obj.data.vertices]

    def key(name, fn):
        sk = obj.shape_key_add(name=name, from_mix=False)
        for v, co in zip(sk.data, base):
            v.co = fn(co)
        sk.value = 0.0

    def fold(co, line_y, radius=.008):
        """Fold everything below line_y up and over it, with a rounded crease."""
        d = line_y - co.y
        if d <= 0:
            return co.copy()
        if d < radius*math.pi:
            a = d/radius
            return Vector((co.x, line_y - radius*math.sin(a) + 0, co.z + radius*(1-math.cos(a))))
        return Vector((co.x, line_y + (d - radius*math.pi), co.z + 2*radius + .0006))

    key('Fold_Half', lambda c: fold(c, 0.0))
    def letter_fold(c, radius=.006):
        """Bottom third folds up over the middle, top third folds down over it."""
        lo, hi = -PAPER_H/6, PAPER_H/6
        if c.y < lo:
            p = fold(c, lo, radius)
            return Vector((p.x, p.y, p.z + .0006))
        if c.y > hi:
            mirrored = fold(Vector((c.x, -c.y, c.z)), lo, radius)
            return Vector((mirrored.x, -mirrored.y, mirrored.z + .0018))
        return c.copy()

    key('Fold_Third', letter_fold)

    def curl(c):
        x, y = c.x - PAPER_W/2, c.y + PAPER_H/2
        reach = max(0.0, 1 - math.hypot(x, y)/.09)
        return Vector((c.x, c.y, c.z + .035*reach**2))

    key('Corner_Curl', curl)
    key('Crumple', lambda c: Vector((c.x + .0015*math.sin(c.y*90), c.y,
                                     c.z + .0035*math.sin(c.x*70 + c.y*40))))


# ---- oil-cloth bundle (पोटली) ----
CLOTH = .70   # square side, metres
GRID = 28
BAG_R, BAG_H = .13, .22   # tied pouch: inner radius and wall height


def cloth_mesh(name):
    verts, faces = [], []
    for j in range(GRID+1):
        for i in range(GRID+1):
            verts.append(((i/GRID-.5)*CLOTH, (j/GRID-.5)*CLOTH, 0.0))
    for j in range(GRID):
        for i in range(GRID):
            a = j*(GRID+1)+i
            faces.append((a, a+1, a+GRID+2, a+GRID+1))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    uv = mesh.uv_layers.new(name='UVMap')
    for poly in mesh.polygons:
        for loop in poly.loop_indices:
            x, y, _ = verts[mesh.loops[loop].vertex_index]
            uv.data[loop].uv = (x/CLOTH + .5, y/CLOTH + .5)
    mesh.update()
    return mesh


def tied_profile(s):
    """(radius, height) of a cloth point at distance s from the centre, in the tied pouch."""
    base = .12
    if s < base:
        return s, .002 + .01*(s/base)**2
    if s < base + BAG_H:
        t = (s-base)/BAG_H
        return BAG_R - .01*math.sin(t*math.pi), .012 + t*BAG_H
    top = base + BAG_H
    neck = .17
    if s < top + neck:
        t = (s-top)/neck
        k = t*t*(3-2*t)
        return BAG_R + (.025-BAG_R)*k, .012 + BAG_H + t*.07
    extra = s - top - neck
    return .025 + extra*1.1, .012 + BAG_H + .07 + extra*.7   # corners flare above the knot


def hand_profile(s):
    """Cloth gathered in a closed hand: a small ball with the corners left loose."""
    ball = .33
    if s < ball:
        phi = s/ball*math.pi*.9
        return .065*math.sin(phi), .065 - .065*math.cos(phi)
    extra = s - ball
    return .02 + extra*.9, .13 + extra*.8


def add_bundle_keys(obj):
    """Basis = open and flat. Tied = knotted pouch. In_Hand = gathered up in a hand."""
    obj.shape_key_add(name='Open')
    base = [Vector(v.co) for v in obj.data.vertices]
    for name, profile, wrinkle in (('Tied', tied_profile, .004), ('In_Hand', hand_profile, .006)):
        sk = obj.shape_key_add(name=name, from_mix=False)
        for v, co in zip(sk.data, base):
            s = math.hypot(co.x, co.y)
            angle = math.atan2(co.y, co.x)
            r, z = profile(s)
            r += wrinkle*math.sin(angle*7 + s*30)*min(1, s/.2)
            v.co = (r*math.cos(angle), r*math.sin(angle), z)
        sk.value = 0.0
    for i, v in enumerate(obj.data.vertices):   # the open state: a gentle dish with soft folds
        x, y = base[i].x, base[i].y
        obj.data.shape_keys.key_blocks['Open'].data[i].co = (x, y, .004*math.sin(x*18)*math.cos(y*14))


def build_bundle(name, material):
    obj = bpy.data.objects.new(name, cloth_mesh(name))
    obj.data.materials.append(material)
    return obj


# ---- ledger (राजकीय बही) ----
def box(name, size, loc, material):
    sx, sy, sz = size
    v = [(x*sx/2, y*sy/2, z*sz/2) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(v, [], f)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = loc
    mesh.materials.append(material)
    return obj


LEDGER_W, LEDGER_H, LEDGER_T = .26, .36, .055
TORN_COUNT = 5   # five leaves torn out near the spine; only ragged stubs remain
