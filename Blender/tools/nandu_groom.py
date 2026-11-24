"""Nandu's hair, beard, moustache and brows as tapered fibers on the sculpted head.

Short, unkempt and salt-and-pepper: cropped hair combed down and back under the
head wrap, a short rough beard with grey strands, a moustache over the lip and
heavy brows. Placement uses the sculpted face's canonical frame (sculpted_face):
the beard follows its beard mask and avoids the lips.
"""

from __future__ import annotations

import math
import random
from typing import List, Tuple

import bpy
import numpy as np
from mathutils import Vector

from groom import FiberGroup
import nandu_body as nb


ROOT = (.017, .012, .010)
HIGHLIGHT = (.150, .143, .135)    # ash grey at the light end of the ramp: grey strands
CENTRE = Vector((0, .008, 1.455))  # canonical centre of the skull


def hairline(theta: float) -> float:
    """Canonical height of the hairline by azimuth (0 = front, ±π = back)."""
    a = abs(theta)
    temple = nb.smooth01(0, 1.05, a)
    back = nb.smooth01(1.4, 2.6, a)
    return 1.497 - .040*temple - .012*nb.smooth01(1.05, 1.6, a) - .040*back


def _direction(theta: float, phi: float) -> Vector:
    return Vector((math.cos(phi)*math.sin(theta), -math.cos(phi)*math.cos(theta), math.sin(phi)))


def _surface(c, tree, theta: float, phi: float):
    """Hit on the head (design units) along a ray from the canonical skull centre."""
    ratio = c.sculpted.size/c.scale
    centre = CENTRE*ratio
    direction = _direction(theta, phi)
    hit, normal, _, _ = tree.ray_cast(centre + direction*.3, -direction, .4)
    if hit is None:
        return None, None
    if normal.dot(direction) < 0:
        normal = -normal
    return hit, normal


def _strand(tree, root: Vector, normal: Vector, comb: Vector, length: float, lift: float,
            curl: float, rand: random.Random, points: int = 5) -> List[Vector]:
    tangent = (comb - normal*comb.dot(normal))
    if tangent.length < 1e-6:
        tangent = Vector((0, 0, -1))
    tangent.normalize()
    side = normal.cross(tangent).normalized()
    path = []
    for i in range(points):
        t = i/(points - 1)
        p = root + tangent*length*t + side*curl*length*t*t
        near, n, _, _ = tree.find_nearest(p)
        if near is None:
            near, n = p, normal
        path.append(near + n*(.00045 + lift*(.25 + .75*t)*min(1, t*3)))
    return path


def _shade(rand: random.Random, grey: float) -> Tuple[int, int]:
    shade = 6 if rand.random() < grey else rand.choice((0, 0, 1, 1, 2, 2, 3))
    return shade, min(6, shade + rand.randrange(2))


def scalp(c, tree, fibers: FiberGroup, rand: random.Random, count: int) -> None:
    ratio = c.sculpted.size/c.scale
    made = 0
    while made < count:
        theta = rand.uniform(-math.pi, math.pi)
        phi = math.radians(rand.uniform(-35, 88))
        hit, normal = _surface(c, tree, theta, phi)
        if hit is None or hit.z/ratio < hairline(theta):
            continue
        comb = Vector((math.sin(theta)*.25, .45, -1.0))         # down and back
        length = rand.uniform(.010, .021)
        fibers.add(_strand(tree, hit, normal, comb, length, rand.uniform(.0012, .0035),
                           rand.uniform(-.5, .5), rand), rand.uniform(.00013, .00026), *_shade(rand, .16))
        made += 1


def scalp_undercoat(c, tree, material) -> None:
    """A dark shell just above the skin under the hair so the roots read as dense."""
    head = bpy.data.objects[f'{c.name}_Head']
    ratio = c.sculpted.size/c.scale
    verts, faces, remap = [], [], {}
    for polygon in head.data.polygons:
        corners = []
        for index in polygon.vertices:
            v = head.data.vertices[index]
            p = v.co/c.scale
            q = p/ratio - CENTRE
            theta = math.atan2(q.x, -q.y)
            if p.z/ratio < hairline(theta) + .002:
                corners = None
                break
            if index not in remap:
                remap[index] = len(verts)
                verts.append(tuple(p + v.normal*.0007))
            corners.append(remap[index])
        if corners:
            faces.append(tuple(corners))
    obj = c.mesh('Scalp undercoat', verts, faces, material, 'head')
    obj['Groom'] = 'Root shadow under the cropped hair.'


def beard(c, tree, fibers: FiberGroup, rand: random.Random, count: int) -> None:
    face = c.sculpted
    ratio = face.size/c.scale
    made, tries = 0, 0
    while made < count and tries < count*30:
        tries += 1
        theta = rand.uniform(-1.95, 1.95)
        phi = math.radians(rand.uniform(-58, -8))
        hit, normal = _surface(c, tree, theta, phi)
        if hit is None:
            continue
        canonical = np.array([tuple(hit/ratio)])
        if face.beard_mask(canonical)[0] < .45 or face.lip_mask(canonical)[0] > .2:
            continue
        upper_lip = canonical[0][2] > 1.374 + .004
        comb = Vector((math.sin(theta)*.6, -.15, -1.0)) if not upper_lip else Vector((math.copysign(.9, hit.x), 0, -1.0))
        length = rand.uniform(.004, .011) if not upper_lip else rand.uniform(.006, .010)
        fibers.add(_strand(tree, hit, normal, comb, length, rand.uniform(.0008, .0024), rand.uniform(-.9, .9),
                           rand, 4), rand.uniform(.00011, .00021), *_shade(rand, .24))
        made += 1


def brows(c, tree, fibers: FiberGroup, rand: random.Random) -> None:
    face = c.sculpted
    ratio = face.size/c.scale
    for sign in (1, -1):
        for _ in range(240):
            u = rand.random()
            x, z = face.brow_curve(u, sign)
            z += rand.uniform(-.0022, .0022)*(1 - .5*u)
            point, normal = face.on_skin(x, z)
            root = Vector(point)*ratio
            n = Vector(normal)
            comb = Vector((sign*1.0, 0, .25 - .6*u))               # inner hairs up, outer hairs out and down
            length = rand.uniform(.005, .009)
            fibers.add(_strand(tree, root, n, comb, length, .0009, rand.uniform(-.3, .3), rand, 4),
                       rand.uniform(.00010, .00017), *_shade(rand, .08))


def groom(c) -> None:
    tree = nb.head_surface(c)
    rand = random.Random(1203)
    fibers = FiberGroup(c, ROOT, HIGHLIGHT)
    scalp_undercoat(c, tree, c.mat('Scalp beneath the fibers', tuple(v*.8 for v in ROOT), .9))
    scalp(c, tree, fibers, rand, 9000)
    fibers.make_mesh('Scalp groom fibers')
    beard(c, tree, fibers, rand, 6500)
    brows(c, tree, fibers, rand)
    fibers.make_mesh('Facial groom fibers')
