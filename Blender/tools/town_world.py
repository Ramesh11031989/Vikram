"""Set 3 terrain and story areas: ground, lanes, Halwai roof stair, refuge floor, grain market,
neighbour's cattle place and trees."""

import math
import random

import ghat_kit as k
import ghat_layout as G
import town_kit as K
import town_flora as Fl
import town_layout as T
import town_props as P


def ground(m):
    k.use(K.collection_named('Town | Ground & lanes'))
    x0, x1 = T.GROUND_X
    y0, y1 = T.TOWN_Y
    k.flat_polygon('Town ground (continues the ghat quay ground)', [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], 0, m['earth'])
    for name, (ax, ay, bx, by) in T.LANES.items():
        k.box(f'Lane {name} (trodden earth)', ((ax + bx) / 2, (ay + by) / 2, .02), (bx - ax, by - ay, .04), m['lane'])


def halwai_extras(m):
    """Roof stair, shop counter and the oil jar the Halwai saw floating."""
    k.use(K.collection_named(T.HALWAI['collection']))
    s = T.STAIR
    cx, rise = (s['x'][0] + s['x'][1]) / 2, T.HALWAI_ROOF_Z / s['steps']
    for i in range(s['steps']):
        k.box(f'Roof stair step {i + 1}', (cx, s['y0'] + (i + .5) * s['tread'], rise * (i + 1) / 2),
              (s['x'][1] - s['x'][0], s['tread'], rise * (i + 1)), m['stone'], .01)
    k.box('Roof stair landing', (cx, (s['y_top'] + s['landing_to']) / 2, T.HALWAI_ROOF_Z / 2),
          (s['x'][1] - s['x'][0], s['landing_to'] - s['y_top'], T.HALWAI_ROOF_Z), m['stone'], .01)
    hx, hy = T.HALWAI['center']
    front_y = hy - 3.0
    k.box('Shop counter', (hx - 2.2, front_y - .7, .55), (2.6, .6, 1.1), m['wood'], .02)
    k.box('Shop awning', (hx - 2.2, front_y - .9, 2.45), (3.4, 1.6, .06), m['cloth'], .01, tilt=.18)
    for dx in (-3.8, -.6):
        k.rod('Awning post', (hx + dx, front_y - 1.6, 0), (hx + dx, front_y - 1.6, 2.5), .045, m['wood'])
    P.jalebi_tray('Jalebi tray', (hx - 2.8, front_y - .7, 1.1), m)
    P.kadhai('Kadhai (frying pan)', (hx - 1.5, front_y - .7, 1.1), m)
    for i, (dx, dy) in enumerate(((1.6, -.9), (2.2, -.7), (2.0, -1.4))):
        P.oil_jar(f'Oil jar {i + 1}', (hx + dx, front_y + dy, 0), m)
    k.empty('MARK | Halwai roof eye (sees the ghat)', T.HALWAI_EYE, 'SPHERE', .35)
    k.empty('MARK | Halwai west-parapet stance (looks down at the cattle place)', T.WEST_STANCE, 'SPHERE', .3)
    k.empty('MARK | Oil jar the Halwai saw floating', (hx + 1.6, front_y - .9, .8), 'CUBE', .3)


def front_house_extras(m):
    k.use(K.collection_named(T.FRONT['collection']))
    k.empty('MARK | Front roof — the boy who shouted', T.FRONT_BOY, 'SPHERE', .35)
    fx, fy = T.FRONT['center']
    for dx in (-2.5, 2.5):
        k.rod('Roof drying pole', (fx + dx, fy - 1.6, T.FRONT_ROOF_Z), (fx + dx, fy - 1.6, T.FRONT_ROOF_Z + 1.1), .035, m['wood'])
    k.rod('Roof drying line', (fx - 2.5, fy - 1.6, T.FRONT_ROOF_Z + 1.05), (fx + 2.5, fy - 1.6, T.FRONT_ROOF_Z + 1.05), .012, m['rope'], 6)


def refuge(m):
    """Open flagstone floor: flat, empty and unroofed."""
    k.use(K.collection_named('Town | Refuge floor (शरण के लिए खुला फ़र्श)'))
    cx, cy = T.REFUGE['center']
    w, d = T.REFUGE['size']
    top = T.REFUGE['top']
    k.box('Refuge slab', (cx, cy, top / 2), (w, d, top), m['refuge'], .01)
    for i in range(1, 6):
        k.box('Flag joint', (cx - w / 2 + w * i / 6, cy, top + .003), (.03, d, .006), m['joint'])
    for j in range(1, 5):
        k.box('Flag joint', (cx, cy - d / 2 + d * j / 5, top + .003), (w, .03, .006), m['joint'])
    for name, (px, py) in (('west', (cx - w / 2 - .25, cy)), ('east', (cx + w / 2 + .25, cy))):
        k.box(f'Refuge kerb {name}', (px, py, top / 2 + .02), (.5, d + 1.0, top + .04), m['stone'], .02)
    for name, py in (('south', cy - d / 2 - .25), ('north', cy + d / 2 + .25)):
        k.box(f'Refuge kerb {name}', (cx, py, top / 2 + .02), (w, .5, top + .04), m['stone'], .02)
    k.empty('MARK | Refuge floor zone (keep clear)', (cx, cy, top), 'CUBE', 1.0)
    k.rod('Water pot stand post', (cx + w / 2 + 1.3, cy - 4, 0), (cx + w / 2 + 1.3, cy - 4, .8), .06, m['wood'])
    P.pot('Refuge water pot', (cx + w / 2 + 1.3, cy - 4, .8), 1.0, m)


def trees(m):
    k.use(K.collection_named('Town | Trees'))
    for i, (x, y) in enumerate(T.TREES):
        Fl.neem(f'Neem tree {i + 1}', x, y, 100 + i, m, height=1.0 + .12 * (i % 3))
    rng = random.Random(17)
    for i in range(70):  # grass tufts along the lane edges and house footings
        gx, gy = rng.uniform(-88, -10), rng.choice((68.2, 77.3, 63.4, 81.2)) + rng.uniform(-.4, .4)
        Fl.grass_tuft(f'Grass tuft {i + 1}', (gx, gy, 0), m, 200 + i)
