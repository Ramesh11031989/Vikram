"""Materials, slope ground and footpath for SET_Sharan."""

import math
import random

import ghat_kit as k
import sharan_layout as L
from smashan_world import collection


def materials():
    return dict(
        grass=k.textured('Sharan | dry slope grass', (.17, .155, .075), .96, 4.0, .55, .35),
        path=k.textured('Sharan | worn footpath', (.32, .26, .185), .96, 8, .35, .25),
        stone=k.textured('Sharan | field stone', (.30, .285, .25), .9, 6, .4, .4),
        mud=k.textured('Sharan | mud plaster', (.36, .25, .155), .95, 7, .3, .3),
        thatch=k.textured('Sharan | old thatch', (.30, .22, .10), .98, 45, .6, .7),
        wood=k.textured('Sharan | dark wood', (.20, .12, .06), .85, 12, .4, .3),
        mat=k.textured('Sharan | woven mat', (.46, .36, .20), .95, 40, .35, .4),
        cloth=k.textured('Sharan | cotton cloth', (.62, .58, .48), .92, 25, .2, .1),
        clay=k.textured('Sharan | clay pot', (.42, .18, .085), .8, 10, .3, .1),
        bark=k.textured('Sharan | neem bark', (.13, .09, .055), .95, 18, .5, .5),
        leaf=k.textured('Sharan | neem leaves', (.055, .15, .05), .7, 14, .45, .1),
        ash=k.material('Sharan | ash and char', (.07, .065, .06), .98),
        paper=k.textured('Sharan | list papers', (.72, .66, .50), .9, 30, .25, .1),
        flame=k.material('Sharan | warm glow', (1.0, .45, .12), .5, emission=6),
        mark=k.material('Sharan | marker', (.9, .3, .1), .5),
    )


def terrain(m):
    collection('Sharan | Slope ground')
    (x0, x1), (y0, y1) = L.X_RANGE, L.Y_RANGE
    step = .5
    nx, ny = int(round((x1 - x0) / step)), int(round((y1 - y0) / step))
    verts = [(x0 + i * step, y0 + j * step, L.ground_z(x0 + i * step, y0 + j * step))
             for j in range(ny + 1) for i in range(nx + 1)]
    faces = [(j * (nx + 1) + i, j * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i)
             for j in range(ny) for i in range(nx)]
    k.mesh_object('Terrain | slope ground', verts, faces, m['grass'], smooth=True)


def path(m):
    collection('Sharan | Path up the slope')
    pts = L.path_points(.5)
    verts, faces = [], []
    for x, y, z in pts:
        dx, dy = L.path_dir(y)
        nx, ny = -dy, dx
        for side in (-1, 1):
            px, py = x + side * nx * L.PATH_HALF, y + side * ny * L.PATH_HALF
            verts.append((px, py, L.ground_z(px, py) + .03))
    for i in range(len(pts) - 1):
        a = i * 2
        faces.append((a, a + 1, a + 3, a + 2))
    k.mesh_object('Path | pagdandi up the slope', verts, faces, m['path'], smooth=True)
    rng = random.Random(3)
    for i, (x, y, z) in enumerate(pts[::3]):  # loose stones along both edges
        dx, dy = L.path_dir(y)
        nx, ny = -dy, dx
        side = -1 if i % 2 else 1
        offset = L.PATH_HALF + .08 + rng.random() * .15
        px, py = x + side * nx * offset, y + side * ny * offset
        k.sphere(f'Path | edge stone {i + 1:02d}', (px, py, L.ground_z(px, py) + .03),
                 (.11 + rng.random() * .08, .1 + rng.random() * .06, .06), m['stone'])
    steps, since, previous = 0, 9.0, pts[0]
    for x, y, z in pts[1:]:  # log steps where the path is steepest
        since += math.hypot(x - previous[0], y - previous[1])
        previous = (x, y, z)
        if L.path_grade_deg(y) > 7.0 and since >= 1.3 and y < L.PATH_Y[1] - .8:
            dx, dy = L.path_dir(y)
            nx, ny = -dy, dx
            a = (x - nx * (L.PATH_HALF + .05), y - ny * (L.PATH_HALF + .05), z + .06)
            b = (x + nx * (L.PATH_HALF + .05), y + ny * (L.PATH_HALF + .05), z + .06)
            steps += 1
            k.rod(f'Path | log step {steps:02d}', a, b, .06, m['wood'], vertices=8)
            since = 0.0
    k.empty('MARK | Vikram starts the climb (foot of the path)', (L.path_x(0.0), 0.0, 0.02), 'ARROWS', .5)
    for y in (12.0, 24.0, 33.0):
        k.empty(f'MARK | Vikram carries Betal up the path (y {y:.0f})',
                (L.path_x(y), y, L.ground_z(L.path_x(y), y)), 'PLAIN_AXES', .35)


def cremation_edge(m):
    collection('Sharan | Cremation ground below')
    gap = L.wall_gap_x()
    x0, x1 = L.X_RANGE[0] + 6, L.X_RANGE[1] - 6
    k.box('Wall | cremation ground west', ((x0 + gap - L.WALL_HALF_GAP) / 2, L.WALL_Y, .45),
          (gap - L.WALL_HALF_GAP - x0, .4, .9), m['stone'], bevel=.03)
    k.box('Wall | cremation ground east', ((gap + L.WALL_HALF_GAP + x1) / 2, L.WALL_Y, .45),
          (x1 - gap - L.WALL_HALF_GAP, .4, .9), m['stone'], bevel=.03)
    k.box('Pyre | ash bed (below the slope)', (-7.0, -6.5, .02), (2.4, 1.2, .04), m['ash'])
    for i, (x, y) in enumerate(((6.0, -6.0), (8.0, -7.2)), start=1):
        k.box(f'Memorial {i} | plinth', (x, y, .15), (.5, .5, .3), m['stone'], bevel=.02)
        k.box(f'Memorial {i} | upright stone', (x, y, .65), (.2, .2, .7), m['stone'], bevel=.02)
    k.empty('MARK | Cremation ground is below (south)', (0, -6.5, 0), 'SPHERE', .3)
