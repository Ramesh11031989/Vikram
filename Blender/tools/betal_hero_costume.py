"""Shyam Munshi's worn angarkha, shoulder cloth, and wrapped dhoti."""

import math

from mathutils import Vector
from mathutils.bvhtree import BVHTree

from hero_wardrobe import (
    body_weights,
    build_angarkha,
    coat_point,
    fabric,
    joint,
    limb_radii,
    mix,
    patch,
    profile_at,
    smooth,
    torso_face,
    weights,
)
from textile import store_rest_positions


DHOTI_HEMS = {'L': .184, 'R': .234}


def coat_closure(c, profile, hem_cloth, thread, tie_cloth):
    """Turned collar, offset overlap, and humble cotton tie closures."""
    collar_rows = []
    for row in range(8):
        t = row / 7
        z = mix(1.484, 1.563, t)
        _, cy, _, ry = profile_at(profile, z)
        collar_rows.append([
            Vector((mix(.110, .086, t) * math.cos(angle),
                    cy - .014*t + mix(ry+.003, .101, t) * math.sin(angle),
                    z - .009*t * max(0, -math.sin(angle))**7))
            for angle in (math.tau*i/56 for i in range(56))
        ])
    collar_binding = [weights('chest','neck',.40*i/7) for i in range(8)]
    patch(c, 'Angarkha • softened stand collar', collar_rows, collar_binding,
          hem_cloth, closed=True)
    c.tube('Angarkha • collar edge', collar_rows[-1], .00118, thread,
           [collar_binding[-1]]*len(collar_rows[-1]), cyclic=True)

    overlap = []
    for row in range(29):
        t = row / 28
        z = mix(1.506, .933, t)
        x = mix(-.021, .133, math.sin(t*math.pi/2))
        width = mix(.018, .027, t)
        overlap.append([torso_face(profile, z, x+width*(u-.5), -1, .010+.004*math.sin(math.pi*u))
                        for u in (0,.18,.42,.67,.85,1)])
    skinning = [body_weights(row[0].z) for row in overlap]
    patch(c, 'Angarkha • turned crossover edge', overlap, skinning, hem_cloth, flip=True)
    c.tube('Angarkha • hand-sewn centre binding', [row[-1] for row in overlap],
           .00140, thread, skinning)

    for index, row in enumerate((13, 18, 22), 1):
        p = overlap[row][-2] + Vector((.006, -.006, 0))
        bone = max(skinning[row], key=skinning[row].get)
        c.ovoid(f'Angarkha • cloth knot {index}', p, (.007, .005, .0055), tie_cloth, bone)
        for side in (-1, 1):
            d = side * (1 if index % 2 else -1)
            c.tube(f'Angarkha • tied tail {index} {side}',
                   [p, p+Vector((.010*d, -.004, .005)),
                    p+Vector((.015*d, -.002, -.008)), p+Vector((.017*d, -.001, -.019))],
                   (.0017, .0018, .0016, .0011), tie_cloth, bone)


def coat_tails(c, profile, coat, hem_cloth, thread):
    """Two flexible tails with a broad opening for sitting and climbing."""
    _, cy, rx, ry = profile_at(profile, .924)
    for side, start, end in (('L', -1.46, 1.64), ('R', 1.57, 4.58)):
        rows = []
        for row in range(25):
            t = row / 24
            ring = []
            for j in range(45):
                angle = mix(start, end, j/44)
                front = max(0, -math.sin(angle))
                z = .918 - t*(.245 - .072*front**4 + .011*math.cos(3*angle))
                fold = t*(.008*math.cos(9*angle+2*t)+.004*math.sin(17*angle-3*t))
                ring.append(Vector(((rx+.022+.096*t+fold)*math.cos(angle),
                                    cy+(ry+.023+.103*t+fold)*math.sin(angle), z)))
            rows.append(ring)
        skinning = [weights('hips', f'thigh.{side}', .82*smooth(i/24)) for i in range(len(rows))]
        patch(c, f'Angarkha • split tail {side}', rows, skinning, coat, flip=True)
        turned = [[p + Vector((0, .0015 if p.y>cy else -.0015, -.001)) for p in row]
                  for row in rows[-3:]]
        patch(c, f'Angarkha • turned hem {side}', turned, skinning[-3:], hem_cloth, flip=True)
        c.tube(f'Angarkha • hem stitch {side}', turned[-1], .00135, thread,
               [skinning[-1]]*len(turned[-1]))


def waist_tie(c, profile, cloth, thread):
    levels = ((.894,.010), (.895,.027), (.899,.030), (.914,.031), (.931,.029),
              (.936,.025), (.936,.009))
    rows = [[coat_point(profile, z+.004*math.sin(angle+.4), angle, ease)
             for angle in (math.tau*j/64 for j in range(64))] for z,ease in levels]
    patch(c, 'Dhoti • plain cotton waist tie', rows, ['hips']*len(rows), cloth, closed=True)
    c.tube('Dhoti • waist tie edge', rows[-2], .00122, thread, 'hips', cyclic=True)


def shoulder_cloth(c, profile, coat_mesh, cloth, thread):
    """One removable piece of white cotton, carried over the right shoulder."""
    surface = BVHTree.FromPolygons([vertex.co.copy() for vertex in coat_mesh.vertices],
                                  [face.vertices[:] for face in coat_mesh.polygons])

    def panel_row(z, x, width, direction, looseness):
        row = []
        for j in range(25):
            u = j / 24
            dx = (u-.5)*width
            zz = z + (.022+.28*looseness)*(u-.5) + .006*math.sin(math.tau*u+z*12)
            shoulder_ease = .025*smooth((zz-1.245)/.18)
            point = torso_face(profile, zz, x+dx, direction, .017+looseness+shoulder_ease)
            ridge = (.007*math.cos(5*math.pi*u+z*5) + .0033*math.sin(11*math.pi*u-z*8))
            point.y += direction*ridge
            row.append(point)
        return row

    front = [panel_row(mix(.986, 1.438, i/30), mix(-.059, -.117, i/30)+.012*math.sin(math.pi*i/30),
                       mix(.188, .126, i/30), -1, .045*(1-i/30)**4)
             for i in range(31)]
    back = [panel_row(mix(1.438, .935, i/34), mix(-.117, -.121, i/34),
                      mix(.126, .191, i/34), 1, .055*(i/34)**4)
            for i in range(35)]
    bridge = []
    for i in range(1,20):
        t = i / 20
        seam = []
        for j, (leading, trailing) in enumerate(zip(front[-1], back[0])):
            p = leading.lerp(trailing, t)
            crest = math.sin(math.pi*t)**.80
            hit = surface.ray_cast(Vector((p.x, p.y, 1.70)), Vector((0,0,-1)), .31)[0]
            p.z += crest*(.047+.004*math.cos(j/24*math.tau*3.5))
            if hit is not None:
                p.z = max(p.z, hit.z+.014)
            seam.append(p)
        bridge.append(seam)
    rows = front + bridge + back
    skinning = [body_weights(row[12].z) for row in rows]
    result = patch(c, 'Shoulder cloth • off-white handloom', rows, skinning, cloth)
    result['Placement'] = 'Right shoulder, with short front fold and longer loose back fold'
    for edge in (0,-1):
        c.tube(f'Shoulder cloth • selvedge {edge}', [row[edge] for row in rows], .00110, thread, skinning)
    for end in (0,-1):
        row, bone = rows[end], skinning[end]
        c.tube(f'Shoulder cloth • turned hem {end}', row, .00145, thread, [bone]*len(row))
        for index, point in enumerate(row[1:-1:2]):
            direction = Vector((.0012*math.sin(index*4.4), .0012 if end else -.0012, -.004))
            c.tube(f'Shoulder cloth • loose weft {end}.{index:02}', [point,point+direction,
                   point+direction*1.7], (.00045,.00035,.00016), thread, [bone]*3)


def dhoti(c, skin, cloth, hem_cloth, thread):
    for side, sign in (('L',1), ('R',-1)):
        hip, knee, ankle = (joint(c, label, side) for label in ('hip','knee','ankle'))
        thigh, shin = f'thigh.{side}', f'shin.{side}'
        rows, skinning = [], []
        for row in range(36):
            t = row / 35
            z = mix(DHOTI_HEMS[side], .954, t)
            lower = z <= knee.z
            start, end = (ankle,knee) if lower else (knee,hip)
            center = start.lerp(end, min(1, (z-start.z)/(end.z-start.z)))
            center.z = z
            radii = limb_radii(skin, center, Vector((0,0,1)), (Vector((1,0,0)),Vector((0,1,0))),
                               .022, .128, (.044+.033*t,.047+.042*t))
            tuck = smooth((t-.70)/.30)
            fullness = math.sin(math.pi*t)**.9
            width = (min(radii[0],.072+.029*t)+.018*fullness)*(1-.24*tuck)
            depth = (min(radii[1],.078+.033*t)+.023*fullness)*(1-.33*tuck)
            center.x -= sign*.024*tuck
            ring = []
            for step in range(68):
                angle = math.tau*step/68
                folds = (.005+.005*fullness)*math.cos(10*angle+2.4*t*sign)
                folds += .0035*math.sin(18*angle+4*t)
                folds += .004*math.exp(-((t-.09)/.070)**2)*math.cos(2*angle+82*t)
                hem = .006*math.cos(3*angle+.7*sign)*(1-t)**6
                ring.append(Vector((center.x+(width+folds)*math.cos(angle),
                                    center.y+(depth+folds)*math.sin(angle), z+hem)))
            rows.append(ring)
            knee_mix = smooth((z-knee.z+.095)/.185)
            skinning.append(weights(thigh,'hips',tuck) if t>.79 else weights(shin,thigh,knee_mix))
        patch(c, f'Dhoti • gathered leg {side}', rows, skinning, cloth, closed=True)
        c.tube(f'Dhoti • wrapped lower hem {side}', rows[0], .0030, hem_cloth, shin, cyclic=True)
        c.tube(f'Dhoti • hand stitch {side}', rows[1], .00105, thread, shin, cyclic=True)


def dress(c):
    """Fit all cloth to the adult rig in its metric A-pose."""
    profile = sorted(c.landmarks['torso_profile'])
    if profile[-1][0] < 1.518:
        _, cx, cy, _, _ = profile[-1]
        profile.append((1.518, cx, cy, .067, .077))
    skin = [vertex.co.copy() for vertex in c.skin_mesh.data.vertices]
    gray = fabric(c,'Woodsmoke-gray handloom angarkha',(.130,.126,.115),1.21,.133,.091,fine=False)
    turned = fabric(c,'Washed-gray turned edges',(.164,.155,.138),1.13,.121,.079,fine=False)
    white = fabric(c,'Unbleached white shoulder cloth',(.742,.711,.645),1.16,.125,.082,fine=False)
    cotton = fabric(c,'Ecru gathered cotton dhoti',(.585,.535,.441),1.28,.110,.094,fine=False)
    waist = fabric(c,'Coarse soot-gray waist cotton',(.082,.072,.060),1.20,.142,.104,fine=False)
    seam = c.mat('Weathered cotton thread',(.217,.205,.178),.91)
    white_thread = c.mat('Unbleached stitch and frayed weft',(.525,.491,.414),.92)

    first = len(c.parts)
    build_angarkha(c, profile, skin, gray, turned, seam)
    coat = c.parts[-1]
    for piece in c.parts[first:]:
        piece.name = piece.name.replace('indigo cuff', 'gray cuff').replace('coutil edge','cuff seam')
    coat_closure(c, profile, turned, seam, waist)
    coat_tails(c, profile, gray, turned, seam)
    waist_tie(c, profile, waist, seam)
    shoulder_cloth(c, profile, coat.data, white, white_thread)
    dhoti(c, skin, cotton, turned, white_thread)

    fabrics = {gray, turned, white, cotton, waist}
    for piece in c.parts[first:]:
        if any(material in fabrics for material in piece.data.materials):
            store_rest_positions(piece.data)
