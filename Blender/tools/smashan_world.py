"""Ground, path, boundary wall, gate and horse post for SET_Smashan, plus shared helpers."""

import math
import random

import bmesh
import bpy
from mathutils import Vector

import ghat_kit as k
import smashan_layout as L
import smashan_props as P


def collection(name):
    col = k.collection(name)
    k.use(col)
    return col


def materials():
    return dict(
        earth=k.textured('Smashan | packed ash earth', (.20, .165, .125), .95, 3.5, .5, .3),
        path=k.textured('Smashan | worn path', (.31, .25, .18), .96, 7, .35, .2),
        stone=k.textured('Smashan | old plastered brick', (.34, .30, .25), .9, 5, .4, .4),
        chabutra=k.textured('Smashan | lime-washed platform', (.52, .48, .40), .88, 8, .3, .3),
        bark=k.textured('Smashan | banyan bark', (.117, .074, .039), .95, 20, .55, .6),
        root=k.textured('Smashan | banyan aerial roots', (.081, .051, .028), .93, 30, .5, .5),
        leaf=k.textured('Smashan | banyan leaves', (.05, .14, .045), .7, 14, .45, .1),
        cloth=k.textured('Smashan | hanging white cloth', (.80, .78, .72), .92, 25, .12, .1),
        skin=k.material('Smashan | ankle skin', (.36, .22, .14), .6),
        wood=k.textured('Smashan | dark wood', (.20, .12, .06), .85, 12, .4, .3),
        rope=k.material('Smashan | rope', (.42, .32, .18), .95),
        ash=k.material('Smashan | ash and char', (.07, .065, .06), .98),
        mark=k.material('Smashan | marker', (.9, .3, .1), .5),
    )


def tube(name, centres, radii, surface, sides=12):
    """Tapered capped tube along a polyline."""
    centres = [Vector(c) for c in centres]
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    rings = []
    for i, (c, r) in enumerate(zip(centres, radii)):
        tangent = (centres[min(i + 1, len(centres) - 1)] - centres[max(i - 1, 0)]).normalized()
        helper = Vector((0, 0, 1)) if abs(tangent.z) < .9 else Vector((1, 0, 0))
        a = tangent.cross(helper).normalized()
        b = tangent.cross(a).normalized()
        rings.append([bm.verts.new(c + (a * math.cos(t) + b * math.sin(t)) * r)
                      for t in (math.tau * j / sides for j in range(sides))])
    for ring, nxt in zip(rings, rings[1:]):
        for j in range(sides):
            bm.faces.new((ring[j], ring[(j + 1) % sides], nxt[(j + 1) % sides], nxt[j]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    k._current.objects.link(obj)
    mesh.materials.append(surface)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    return obj


def limb(name, direction, table, surface, steps=14, sway=0.0):
    pts, radii = [], []
    s_end = table[-1][0]
    for i in range(steps + 1):
        s = s_end * i / steps
        z, r = L.profile(table, s)
        x, y, _ = L.along(direction, s)
        pts.append((x, y + sway * math.sin(s * 1.3), z))
        radii.append(r)
    return tube(name, pts, radii, surface)


def ground(m):
    collection('Smashan | Ground and path')
    x0, x1, y0, y1 = L.WALL_BOX
    k.box('Ground | ash earth', ((x0 + x1) / 2, (y0 + y1) / 2, -.1), (x1 - x0 + 14, y1 - y0 + 20, .2), m['earth'])
    k.box('Path | entrance track', (L.PATH_X, (L.PATH_Y[0] + L.PATH_Y[1]) / 2, .005),
          (L.PATH_HALF * 2, L.PATH_Y[1] - L.PATH_Y[0], .02), m['path'])
    rng = random.Random(7)
    for i in range(22):  # loose stones along the path edges
        side = -1 if i % 2 else 1
        y = L.PATH_Y[0] + 1 + i * .75
        k.sphere(f'Path | edge stone {i + 1:02d}', (side * (L.PATH_HALF + .08 + rng.random() * .15), y, .04),
                 (.12 + rng.random() * .08, .1 + rng.random() * .06, .06), m['stone'])
    k.box('Mark | Entrance (Vikram arrives)', (0, L.PATH_Y[0] + 1.0, .02), (.5, .5, .02), m['mark'])


def boundary(m):
    collection('Smashan | Boundary and gate')
    x0, x1, y0, y1 = L.WALL_BOX
    gx = L.GATE_POST_X
    segments = [((x0, y1), (x1, y1)), ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1)),
                ((x0, y0), (-gx - .25, y0)), ((gx + .25, y0), (x1, y0))]
    for i, (a, b2) in enumerate(segments, start=1):
        P.wall_run(f'Wall | low boundary {i}', a, b2, m, 30 + i)
    P.gate_detail(m)


def horse_post(m):
    collection('Smashan | Horse tie')
    (ax, ay), (bx, by) = L.HORSE_POSTS
    for i, (x, y) in enumerate(L.HORSE_POSTS, start=1):
        k.rod(f'Horse post {i}', (x, y, 0), (x, y, 1.4), .09, m['wood'])
    k.rod('Horse rail', (ax, ay, L.HORSE_RAIL_Z), (bx, by, L.HORSE_RAIL_Z), .045, m['wood'])
    k.rod('Horse rope loop', (ax - .25, ay, L.HORSE_RAIL_Z), (ax - .25, ay, .75), .015, m['rope'], vertices=6)
    k.box('Horse | trampled ground', ((ax + bx) / 2, ay - .9, .01), (2.6, 3.0, .02), m['path'])
    k.empty('MARK | Horse (outside the entrance)', L.HORSE_MARK, 'ARROWS', .5)
