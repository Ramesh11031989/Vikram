"""Shared geometry helpers for the bell-hearing boy's costume.

All coordinates are in the shared adult-rig space (metres before the spec's
height scale), exactly like `Character.mesh` expects.
"""

import bmesh
from mathutils import Vector


def smooth(a, b, v):
    """Smoothstep from a to b (a may be greater than b)."""
    t = min(1., max(0., (v - a) / (b - a)))
    return t * t * (3 - 2 * t)


def interp(rows, z):
    """Eased interpolation of (z, values...) rows sorted by ascending z."""
    z = min(max(z, rows[0][0]), rows[-1][0])
    for low, high in zip(rows, rows[1:]):
        if z <= high[0]:
            t = (z - low[0]) / (high[0] - low[0])
            t = .5 * t + .5 * t * t * (3 - 2 * t)
            return tuple(a + (b - a) * t for a, b in zip(low[1:], high[1:]))
    return tuple(rows[-1][1:])


def body_weight(point):
    """Skin weights for cloth that hangs from the trunk, by height."""
    z = point.z
    if z > 1.33:
        return 'chest'
    if z > 1.20:
        t = (1.33 - z) / .13
        return {'chest': 1 - t, 'spine': t}
    if z > 1.06:
        t = (1.20 - z) / .14
        return {'spine': 1 - t, 'hips': t}
    return 'hips'


def dominant(weight):
    """One bone name from a weight spec: ovoid() and tube() take a single bone."""
    return weight if isinstance(weight, str) else max(weight, key=weight.get)


def fix_normals(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def thick_grid(c, name, grid, normals, thickness, material, weight):
    """A closed cloth slab: grid[i][j] points, a second layer pushed out along normals."""
    rows, cols = len(grid), len(grid[0])
    verts, weights = [], []
    for layer in (0, 1):
        for i in range(rows):
            for j in range(cols):
                point = Vector(grid[i][j]) + Vector(normals[i][j]).normalized() * thickness * layer
                verts.append(point)
                weights.append(weight(point))

    def at(layer, i, j):
        return layer * rows * cols + i * cols + j

    faces = []
    for i in range(rows - 1):
        for j in range(cols - 1):
            faces.append((at(1, i, j), at(1, i + 1, j), at(1, i + 1, j + 1), at(1, i, j + 1)))
            faces.append((at(0, i, j), at(0, i, j + 1), at(0, i + 1, j + 1), at(0, i + 1, j)))
    for i in range(rows - 1):
        faces.append((at(0, i, 0), at(0, i + 1, 0), at(1, i + 1, 0), at(1, i, 0)))
        faces.append((at(0, i, cols - 1), at(1, i, cols - 1), at(1, i + 1, cols - 1), at(0, i + 1, cols - 1)))
    for j in range(cols - 1):
        faces.append((at(0, 0, j), at(1, 0, j), at(1, 0, j + 1), at(0, 0, j + 1)))
        faces.append((at(0, rows - 1, j), at(0, rows - 1, j + 1), at(1, rows - 1, j + 1), at(1, rows - 1, j)))
    obj = c.mesh(name, verts, faces, material, weights)
    fix_normals(obj)
    return obj


def stitches(c, name, points, normals, material, weight, width=.0017, lift=.0008, fill=.58):
    """Dashed running stitch along a densely sampled path (one flat dash per segment)."""
    verts, faces, weights = [], [], []
    for k in range(len(points) - 1):
        a, b = Vector(points[k]), Vector(points[k + 1])
        normal = Vector(normals[k]).normalized()
        run = b - a
        side = run.cross(normal)
        if run.length < 1e-6 or side.length < 1e-6:
            continue
        side = side.normalized() * (width / 2)
        end = a + run * fill
        base = len(verts)
        for point, sign in ((a, -1), (a, 1), (end, 1), (end, -1)):
            verts.append(point + normal * lift + side * sign)
            weights.append(weight(point))
        faces.append((base, base + 1, base + 2, base + 3))
    if faces:
        c.mesh(name, verts, faces, material, weights, smooth=False)
