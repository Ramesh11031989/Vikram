"""सहायक दरबारी मुंशी (the assistant court scribe).

He records testimony and writes the return (वापसी) beneath the old order. The
story opens by mentioning two scribes' writing styles, so the model carries two
distinct handwritings on his desk:

OLD ORDER  - the earlier scribe: broad, upright, evenly spaced, heavy black ink.
RETURN     - this scribe: small, right-slanted, quick and tight, thinner brown ink,
             written on the lines under the old order.

The handwriting is geometry (ribbon strokes under a shirorekha headline), not a
font, so it needs no Devanagari font at render or export time.
"""

import random
from math import cos, radians, sin, tau

from mathutils import Vector


SPEC = dict(name='SahayakDarbariMunshi', height=.97, skin=(.36,.195,.105),
            hair=(.05,.04,.034), iris=(.065,.032,.014), face_width=.98,
            nose_width=.98, brow_lift=.001)

# Handwriting styles, sizes in metres on the sheet; ink is RGB.
HAND_OLD = dict(name='Old order hand', seed=11, glyph=.0105, slant=0.0, advance=.0105,
                gap=.011, width=.0019, jitter=.0004, headline=.0022,
                ink=(.012,.011,.010), line_pitch=.0285, words=(3, 5))
HAND_RETURN = dict(name='Return hand', seed=29, glyph=.0072, slant=.45, advance=.0068,
                   gap=.0060, width=.0011, jitter=.0011, headline=.0012,
                   ink=(.12,.055,.022), line_pitch=.0165, words=(4, 7))

DESK_TILT = 18.0


def desk_frame():
    """Origin and axes (u across, v up the slope, n normal) of the slanted desk top."""
    tilt = radians(DESK_TILT)
    u = Vector((1, 0, 0))
    v = Vector((0, cos(tilt), sin(tilt)))
    n = u.cross(v)
    if n.z < 0:
        n = -n
    return Vector((0, -.44, .93)), u, v, n


def _ribbon(points, width, lift_point):
    """Quad strip along 2D points; returns (verts, faces)."""
    verts, faces = [], []
    for index, (x, y) in enumerate(points):
        a = points[max(index - 1, 0)]
        b = points[min(index + 1, len(points) - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = (dx*dx + dy*dy) ** .5 or 1
        nx, ny = -dy/length*width, dx/length*width
        verts.append(lift_point(x + nx, y + ny))
        verts.append(lift_point(x - nx, y - ny))
        if index:
            k = 2*index
            faces.append((k-2, k-1, k+1, k))
    return verts, faces


def handwriting(c, hand, rect, lines):
    """Write up to `lines` rows of pseudo-Devanagari words inside rect=(u0,v0,u1,v1).

    Each word has a shirorekha headline with stems, bowls, hooks and tails hanging
    from it. The style dict sets size, slant, spacing and wobble, so the two hands
    look clearly different at the same page size.
    """
    rng = random.Random(hand['seed'])
    origin, u_axis, v_axis, n_axis = desk_frame()
    u0, v0, u1, v1 = rect

    def place(x, y):
        return tuple(origin + u_axis*x + v_axis*y + n_axis*.0016)

    verts, faces = [], []

    def add(points, width):
        base = len(verts)
        new_verts, new_faces = _ribbon(points, width, place)
        verts.extend(new_verts)
        faces.extend(tuple(base + i for i in face) for face in new_faces)

    glyph, slant, wobble = hand['glyph'], hand['slant'], hand['jitter']
    for row in range(lines):
        y_head = v1 - hand['line_pitch']*(row + 1)
        if y_head - glyph*1.8 < v0:
            break
        x = u0 + rng.uniform(0, .006)
        for _ in range(rng.randint(*hand['words'])):
            start = x
            for _ in range(rng.randint(2, 5)):
                kind = rng.choice(('stem', 'stem', 'bowl', 'hook', 'tail'))
                top = y_head
                j = lambda: rng.uniform(-wobble, wobble)
                if kind == 'stem':
                    pts = [(x + j(), top), (x - slant*glyph*.9 + j(), top - glyph*1.15)]
                elif kind == 'bowl':
                    pts = [(x + glyph*.42*(1 - cos(tau*i/10)) - slant*glyph*.35*i/10 + j(),
                            top - glyph*.55 - glyph*.4*sin(tau*i/10) - glyph*.28*(i/10) + j())
                           for i in range(11)]
                elif kind == 'hook':
                    pts = [(x, top), (x - slant*glyph*.5, top - glyph*.7),
                           (x + glyph*.45 - slant*glyph*.8, top - glyph*.95),
                           (x + glyph*.55 - slant*glyph*.7, top - glyph*.55)]
                else:
                    pts = [(x, top), (x - slant*glyph*.9, top - glyph*.8),
                           (x - slant*glyph*1.5 - glyph*.2, top - glyph*1.7)]
                add(pts, hand['width'])
                x += hand['advance'] + rng.uniform(0, hand['advance']*.35)
                if x > u1 - .02:
                    break
            add([(start - .001, y_head), (x, y_head + rng.uniform(-wobble, wobble)*.6)],
                hand['headline'])
            x += hand['gap'] + rng.uniform(0, hand['gap']*.8)
            if x > u1 - .03:
                break
    if not faces:
        raise RuntimeError(f'{hand["name"]}: no strokes were written')
    ink = c.mat(f'{hand["name"]} ink', hand['ink'], .38)
    return c.mesh(hand['name'], verts, faces, ink, 'root', smooth=False)


def _sheet(c, name, centre, size, material):
    origin, u_axis, v_axis, n_axis = desk_frame()
    (cu, cv), (w, h) = centre, size
    corners = [(cu - w/2, cv - h/2), (cu + w/2, cv - h/2), (cu + w/2, cv + h/2), (cu - w/2, cv + h/2)]
    pts = [tuple(origin + u_axis*a + v_axis*b + n_axis*.0006) for a, b in corners]
    return c.mesh(name, pts, [(0, 1, 2, 3)], material, 'root', smooth=False)


def _desk(c):
    wood = c.mat('Scribe desk wood', (.22,.115,.05), .72)
    cloth = c.mat('Desk red cloth', (.30,.05,.04), .9)
    origin, u_axis, v_axis, n_axis = desk_frame()
    half_u, v_low, v_high, thick = .36, -.03, .36, .025
    top = [origin + u_axis*u + v_axis*v for v in (v_low, v_high) for u in (-half_u, half_u)]
    bottom = [p - n_axis*thick for p in top]
    verts = [tuple(p) for p in top + bottom]
    faces = [(0,1,3,2), (4,6,7,5), (0,4,5,1), (2,3,7,6), (0,2,6,4), (1,5,7,3)]
    c.mesh('Desk slab', verts, faces, wood, 'root', smooth=False)
    for sign in (-1, 1):
        for y, top_z in ((-.45, .90), (-.10, 1.05)):
            c.tube(f'Desk leg {sign}{y}', [(sign*.32, y, 0.0), (sign*.32, y, top_z)],
                   .014, wood, 'root')
    c.tube('Desk stretcher', [(-.32, -.45, .4), (.32, -.45, .4)], .01, wood, 'root')
    return cloth


def _props(c):
    paper_old = c.mat('Old order paper (aged)', (.62,.52,.33), .95)
    paper_new = c.mat('Return sheet paper (fresh)', (.78,.70,.50), .95)
    brass = c.mat('Inkwell brass', (.33,.20,.07), .42, .55)
    reed = c.mat('Reed pen', (.43,.30,.12), .7)
    cloth = _desk(c)
    # Upper sheet: the old order. Lower strip: this scribe's return, written beneath it.
    _sheet(c, 'Old order sheet', (-.02, .215), (.46, .25), paper_old)
    _sheet(c, 'Return sheet', (0.0, .03), (.50, .12), paper_new)
    handwriting(c, HAND_OLD, (-.235, .095, .205, .335), 6)
    handwriting(c, HAND_RETURN, (-.245, -.03, .245, .09), 6)
    origin, u_axis, v_axis, n_axis = desk_frame()
    well = origin + u_axis*.29 + v_axis*.30 + n_axis*.02
    c.ovoid('Inkwell', tuple(well), (.026,.026,.022), brass, 'root')
    c.tube('Reed pen', [tuple(well + Vector((-.02, -.02, .02))),
                        tuple(origin + u_axis*.17 + v_axis*.17 + n_axis*.012)],
           .0045, reed, 'root')
    c.ovoid('Desk cloth roll', tuple(origin + u_axis*-.30 + v_axis*.33 + n_axis*.02),
            (.06,.02,.016), cloth, 'root')


def dress(c):
    cotton = c.mat('Scribe off-white kurta', (.60,.54,.40), .91)
    seam = c.mat('Scribe kurta seam', (.32,.26,.17), .91)
    trousers = c.mat('Scribe dhoti cloth', (.66,.61,.48), .93)
    shawl = c.mat('Scribe ink-stained shoulder cloth', (.17,.14,.12), .9)
    leather = c.mat('Scribe sandals', (.08,.045,.022), .8)
    cap_mat = c.mat('Scribe folded cap', (.56,.20,.07), .9)
    c.loft('Scribe kurta torso', [(.80,0,0,.205,.128),(.94,0,0,.205,.128),(1.08,0,0,.168,.108),
           (1.23,0,0,.198,.118),(1.38,0,0,.218,.100),(1.44,0,0,.075,.060)], cotton,
           ['hips','hips','spine','chest','chest','chest'])
    for side, sign in (('L', 1), ('R', -1)):
        source = next(part for part in c.parts if part.name == f'{c.name}_Arm.{side}')
        sleeve = source.copy()
        sleeve.data = source.data.copy()
        sleeve.name = f'{c.name}_Kurta sleeve {side}'
        sleeve.data.materials.clear()
        sleeve.data.materials.append(cotton)
        for vertex in sleeve.data.vertices:
            vertex.co.y *= 1.26
            vertex.co.z = 1.375*c.scale + (vertex.co.z - 1.375*c.scale)*1.26
        c.collection.objects.link(sleeve)
        c.parts.append(sleeve)
        cuff = [tuple(vertex.co/c.scale) for vertex in sleeve.data.vertices[-24:]]
        c.tube(f'Kurta cuff {side}', cuff, .003, seam, f'hand.{side}', cyclic=True)
        c.loft(f'Dhoti leg {side}', [(.12,sign*.135,0,.056,.052),(.5,sign*.135,0,.085,.080),
               (.75,sign*.125,0,.105,.100),(.95,sign*.10,0,.118,.122)], trousers,
               [f'shin.{side}', {f'shin.{side}': .5, f'thigh.{side}': .5}, f'thigh.{side}', 'hips'])
        c.ovoid(f'Sandal {side}', (sign*.135,-.057,.040), (.060,.118,.030), leather, f'foot.{side}')
    c.tube('Shoulder cloth', [(.06,-.10,1.44),(.14,-.04,1.42),(.17,.06,1.34),(.12,.12,1.18)],
           [.022,.026,.024,.018], shawl, 'chest')
    c.ovoid('Scribe hair', (0,.018,1.735), (.118,.104,.080), c.m['hair'], 'head')
    c.ovoid('Scribe folded cap', (0,.006,1.795), (.120,.104,.030), cap_mat, 'head')
    _props(c)

