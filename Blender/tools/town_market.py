"""Set 3: अनाज मंडी tall thatched shed and the neighbour's cattle place."""

import math

import ghat_kit as k
import town_kit as K
import town_cow as C
import town_flora as F
import town_layout as T
import town_props as P


def mandi(m):
    """Raised veranda platform, 12 posts, tie beams, and a tall gabled thatch roof whose ridge is at z = 9."""
    k.use(K.collection_named('Town | Grain market shed (अनाज मंडी का ऊँचा छप्पर)'))
    cx, cy = T.RIDGE[0], T.RIDGE[1]
    pw, pd = T.MANDI['platform']
    pz = T.MANDI['platform_z']
    x0, x1 = T.MANDI['roof_x']
    hy, eave, ridge, thick = T.MANDI['roof_half_y'], T.MANDI['eave_z'], T.MANDI['ridge_z'], T.MANDI['thick']
    k.box('Mandi platform', (cx, cy, pz / 2), (pw, pd, pz), m['stone'], .02)
    for i in range(1, 4):
        k.box(f'Mandi platform step {i}', (cx + 1.5, cy - pd / 2 - i * .3 + .15, pz * (1 - i / 4) / 2), (2.6, .3, pz * (1 - i / 4)), m['stone'], .01)
    post_xs = [x0 + 1.6 + i * (x1 - x0 - 3.2) / 3 for i in range(4)]
    post_ys = (cy - 3.6, cy, cy + 3.6)
    for px in post_xs:
        for j, py in enumerate(post_ys):
            top = eave + (ridge - eave) * (1 - abs(py - cy) / 3.6) * .62 if j == 1 else eave
            k.box('Mandi post', (px, py, (pz + top) / 2), (.34, .34, top - pz), m['wood'], .02)
    for py in post_ys:
        k.box('Mandi tie beam (along X)', (cx, py, eave + .1 if py != cy else eave + (ridge - eave) * .62 + .1), (x1 - x0 - 2.4, .24, .24), m['wood'], .01)
    for px in post_xs:
        k.box('Mandi cross beam', (px, cy, eave + .12), (.24, 7.6, .24), m['wood'], .01)
    # Gabled thatch roof: slopes from the eaves at +-hy up to the ridge, closed ends.
    top = ridge
    verts = [(x0, cy - hy, eave), (x1, cy - hy, eave), (x1, cy + hy, eave), (x0, cy + hy, eave),
             (x0 + 1.0, cy, top), (x1 - 1.0, cy, top)]
    faces = [(0, 1, 5, 4), (2, 3, 4, 5), (3, 0, 4), (1, 2, 5), (3, 2, 1, 0)]
    k.mesh_object('Mandi thatch roof (tall shed)', verts, faces, m['thatch'])
    k.box('Mandi ridge cap', (cx, cy, top + .06), (x1 - x0 - 2.0, .5, .14), m['thatch'], .04)
    # Grain: sacks, a wheat heap and a weighing beam.
    for i in range(12):
        sx, sy = cx - 4.4 + (i % 6) * .9, cy + 2.4 + (i // 6) * .6
        P.sack(f'Grain sack {i + 1}', (sx, sy, pz), m, 40 + i, standing=i % 3 != 2)
    P.wheat_heap('Wheat heap', (cx + 2.8, cy + 1.2, pz), m)
    k.rod('Weighing beam', (cx - 1.6, cy - 1.8, pz + 1.9), (cx + 1.6, cy - 1.8, pz + 1.9), .03, m['wood'], 6)
    k.empty('MARK | Mandi roof ridge (hides the gate from the Halwai roof)', T.RIDGE, 'CUBE', .8)


def cattle_place(m):
    """Neighbour's yard: hitching rail, two tethered cows, trough and hay, with a low mud wall on two sides."""
    k.use(K.collection_named(T.NEIGHBOUR['collection']))
    cx, cy = T.CATTLE['center']
    w, d = T.CATTLE['size']
    k.box('Cattle yard floor (trodden earth)', (cx, cy, .03), (w, d, .06), m['earth'])
    k.box('Cattle yard low wall, north', (cx, cy + d / 2 - .15, .45), (w, .3, .9), m['mud'], .03)
    k.box('Cattle yard low wall, south', (cx, cy - d / 2 + .15, .45), (w, .3, .9), m['mud'], .03)
    rail_y = cy + 1.2
    for dx in (-3.4, 0, 3.4):
        k.rod('Hitching post', (cx + dx, rail_y, 0), (cx + dx, rail_y, 1.3), .08, m['wood'], 8)
    k.rod('Hitching rail', (cx - 3.4, rail_y, 1.1), (cx + 3.4, rail_y, 1.1), .06, m['wood'], 8)
    P.trough('Fodder trough', (cx, cy + d / 2 - .9, 0), (3.4, .6, .6), m)
    F.hay_heap('Hay heap', (cx + 3.5, cy + d / 2 - 1.2, 0), (.9, .7, .6), m)
    for i, (dx, surface) in enumerate(((-1.7, m['cow_a']), (1.7, m['cow_b']))):
        x, y = cx + dx, rail_y - 1.15
        cow = C.build(f'Cow {i + 1} body', (x, y, 0), surface, m, surface)
        cow.rotation_euler.z = math.pi * (.0 if i == 0 else .04)  # faces the rail (+y)
        k.rod(f'Cow {i + 1} tether rope', (x, y + 1.17, .82), (x, rail_y, 1.1), .012, m['rope'], 6)
    k.empty('MARK | Cattle place (where the neighbour unties the cattle)', (cx, cy, 0), 'CUBE', 1.0)
