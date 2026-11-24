"""Tailor Gopal's series-reference work clothes to the shared adult rig."""

import math

from mathutils import Vector
from mathutils.bvhtree import BVHTree

from hero_wardrobe import (arm_geometry, body_weights, coat_point, fabric, joint,
                           limb_radii, make_uv, mix, patch, profile_at, smooth,
                           torso_face, weights)
from textile import store_rest_positions


SLEEVE_END = .143
TROUSER_HEM = .280
NECK_TOP = 1.519
NECK_DIP = .099


def neck_high(angle):
    """The front V is cut into the actual neckline instead of drawn on the shirt."""
    return NECK_TOP - NECK_DIP * max(0, -math.sin(angle))**13


def vest(c, profile, skin, cloth, binding, thread):
    count, hole_span = 72, 8
    low, high = 1.289, 1.469
    levels = sorted({.907, .922, .937, .957, .980, 1.012, 1.046, 1.081, 1.121, 1.161,
                     1.201, 1.238, 1.264, 1.482, 1.493, 1.503, 1.512, NECK_TOP,
                     *(mix(low, high, i/10) for i in range(11))})
    hole_low, hole_high = levels.index(low), levels.index(high)
    vertices, skinning, faces, uvs = [], [], [], []

    def sew(a, b, ua, ub, skip=(), reverse=False):
        for j in range(len(a)):
            if j in skip:
                continue
            k = (j+1) % len(a)
            face = (a[j], a[k], b[k], b[j])
            s, t = j/len(a), (j+1)/len(a)
            uv = ((s, ua), (t, ua), (t, ub), (s, ub))
            faces.append(face[::-1] if reverse else face)
            uvs.append(uv[::-1] if reverse else uv)

    for nominal in levels:
        for j in range(count):
            a = math.tau*j/count
            z = nominal - (NECK_TOP-neck_high(a)) * smooth((nominal-1.304)/(NECK_TOP-1.304))
            p = coat_point(profile, nominal, a, .007)
            if nominal > high:
                pinch = smooth((nominal-high)/(NECK_TOP-high))
                neck = Vector((.071*math.cos(a), .009+.073*math.sin(a), z))
                if math.sin(a) < -.45:
                    hit = c.skin_bvh.ray_cast(Vector((neck.x,-1,z)), Vector((0,1,0)), 2)[0]
                    if hit is not None:
                        neck.y = hit.y-.009
                p = p.lerp(neck, pinch)
            p.z = z
            # The two gathers lead into the belt instead of repeating evenly around it.
            fold = .006*math.sin(11*a+.38)*math.exp(-((z-.950)/.073)**2)
            p += Vector((math.cos(a)*fold, math.sin(a)*fold, 0))
            vertices.append(p)
            skinning.append(body_weights(z))

    for i in range(len(levels)-1):
        skip = {((center+j) % count) for center in (0,count//2)
                for j in range(-hole_span, hole_span)} if hole_low <= i < hole_high else ()
        sew(list(range(i*count,(i+1)*count)), list(range((i+1)*count,(i+2)*count)),
            i/(len(levels)-1), (i+1)/(len(levels)-1), skip)

    for side, center_index in (('L',0), ('R',count//2)):
        sleeve = f'upper_arm.{side}'
        clavicle = f'clavicle.{side}'
        opening = [(hole_low,j) for j in range(-hole_span, hole_span+1)]
        opening += [(i,hole_span) for i in range(hole_low+1,hole_high+1)]
        opening += [(hole_high,j) for j in range(hole_span-1,-hole_span-1,-1)]
        opening += [(i,-hole_span) for i in range(hole_high-1,hole_low,-1)]
        previous = [i*count+(j+center_index)%count for i,j in opening]
        station, _, _ = arm_geometry(c, side)
        center, _, across, outer = station(.068)
        delta = vertices[previous[0]]-center
        phase = math.atan2(delta.dot(outer),delta.dot(across))
        angles = [phase+math.tau*j/len(previous) for j in range(len(previous))]
        for index in previous:
            skinning[index] = weights('chest',clavicle,.14*smooth((vertices[index].z-low)/(high-low)))

        previous_uv = 0
        for index, distance in enumerate((.067, .090, .110, .129, .139, SLEEVE_END)):
            center, tangent, across, outer = station(distance)
            ry, ro = limb_radii(skin, center, tangent, (across,outer), .022, .095, (.054,.055))
            ry, ro = min(.079, ry+.004), min(.080, ro+.004)
            ring = [center+(ry+.004*math.sin(7*a+40*distance))*math.cos(a)*across
                    +(ro+.003*math.cos(6*a-30*distance))*math.sin(a)*outer for a in angles]
            if not index:
                ring = [vertices[k].lerp(p,.62)+tangent*.012 for k,p in zip(previous,ring)]
            following = list(range(len(vertices),len(vertices)+len(ring)))
            vertices.extend(ring)
            skinning.extend([weights('chest',sleeve, min(1,.56+.24*index))]*len(ring))
            sew(previous, following, previous_uv, (index+1)/6)
            previous, previous_uv = following, (index+1)/6
        c.tube(f'Vest • turned binding {side}', ring, .0030, binding, sleeve, cyclic=True)
        c.tube(f'Vest • sleeve topstitch {side}', [p-.006*tangent for p in ring],
               .00105, thread, sleeve, cyclic=True)

    neckline = vertices[(len(levels)-1)*count:len(levels)*count]
    c.tube('Vest • faded V-neck facing', neckline, .0046, binding,
           [body_weights(p.z) for p in neckline], cyclic=True)
    seam = []
    for j in range(28):
        t = j/27
        z = mix(1.420, 1.144, t)
        x = .063*smooth(t)
        p = torso_face(profile, z, x, -1, .010)
        if j == 0:
            p = neckline[3*count//4].copy()
        seam.append(p)
    c.tube('Vest • off-center closure seam', seam, .0022, binding,
           [body_weights(p.z) for p in seam])
    for index, j in enumerate((5,10,15),1):
        point = seam[j] + Vector((.002,-.008,.001))
        bone = max(body_weights(point.z),key=body_weights(point.z).get)
        c.ovoid(f'Vest • tied closure {index}', point, (.0075,.0048,.0038), thread, bone)
        arc = [point+Vector((-.011,-.002,-.001)), point+Vector((-.003,-.005,.002)),
               point+Vector((.004,-.006,.003)), point+Vector((.010,-.002,.001))]
        c.tube(f'Vest • closure loop {index}', arc, .00145, binding, bone)

    # Remove the original ellipse vertices that sit inside the sleeve openings.
    used = sorted({i for face in faces for i in face})
    index_of = {old:new for new,old in enumerate(used)}
    garment = c.mesh('Vest • continuous handloom body and sleeves', [vertices[i] for i in used],
                     [tuple(index_of[i] for i in face) for face in faces], cloth,
                     [skinning[i] for i in used])
    make_uv(garment, lambda face: uvs[face.index])
    return garment


def trousers(c, skin, cloth, turned, thread):
    count = 64
    vertices, skinning, faces = [], [], []
    inner_seam, top = {}, {}

    def add(point, assignment):
        index = len(vertices)
        vertices.append(point)
        skinning.append(assignment)
        return index

    for side, sign in (('L',1), ('R',-1)):
        hip, knee, ankle = (joint(c, part, side) for part in ('hip','knee','ankle'))
        thigh, shin = f'thigh.{side}', f'shin.{side}'
        previous = []
        for row in range(35):
            t = row/34
            z = mix(TROUSER_HEM,.882,t)
            start,end = (ankle,knee) if z < knee.z else (knee,hip)
            center = start.lerp(end,min(1,(z-start.z)/(end.z-start.z)))
            center.z = z
            ry_hint = .049+.037*t
            radii = limb_radii(skin, center, Vector((0,0,1)), (Vector((1,0,0)),Vector((0,1,0))),
                               .019,.125,(.046+.028*t,ry_hint))
            width = min(.103,radii[0])+.009+.008*math.sin(math.pi*t)
            depth = min(.114,radii[1])+.009+.007*math.sin(math.pi*t)
            knee_weight = smooth((z-knee.z+.091)/.181)
            assignment = weights(thigh,'hips',smooth((t-.68)/.32)) if t > .72 else weights(shin,thigh,knee_weight)
            transition = smooth((t-.69)/.31)
            ring = []
            cuffs = []
            for j in range(count):
                a = -math.pi/2+math.tau*j/count
                fold = (.0035+.0033*math.sin(t*math.pi))*math.sin(9*a+sign*t*3.1)
                fold += .0026*math.cos(5*a-t*4.5)+.0019*math.cos(15*a+t*8)
                hem = .006*math.cos(3*a+sign*.7)*(1-t)**11
                p = Vector((center.x+sign*(width+fold)*math.cos(a),
                            center.y+(depth+fold)*math.sin(a), z+hem))
                concave = max(0, -math.cos(a))
                saddle = Vector((sign*.211*max(0,math.cos(a)), -.008+.134*math.sin(a),
                                 .882-.094*concave**.92))
                p = p.lerp(saddle, transition)
                if row == 34 and (j == 0 or j >= count//2):
                    if j not in inner_seam:
                        inner_seam[j] = add(p,'hips')
                    ring.append(inner_seam[j])
                else:
                    ring.append(add(p,assignment))
                if row == 0:
                    direction = Vector((sign*math.cos(a), math.sin(a), 0))
                    cuffs.append((p,direction))
            if row == 0:
                rolled = [[p+radius * n+Vector((0,0,dz)) for p,n in cuffs]
                          for radius,dz in ((-.003,-.003),(.003,-.004),(.007,.003),(.006,.023),(.001,.027))]
                patch(c,f'Trousers • rolled cuff {side}',rolled,[shin]*len(rolled),turned,
                      closed=True,flip=side=='R')
                c.tube(f'Trousers • cuff thread {side}',rolled[-2],.0013,thread,shin,cyclic=True)
            if previous:
                for j in range(count):
                    k = (j+1)%count
                    face = (previous[j],previous[k],ring[k],ring[j])
                    faces.append(face if side=='L' else face[::-1])
            previous = ring
        top[side] = ring[:count//2+1]

    # Both legs meet at a welded crotch seam and share a single waist tube.
    previous = top['L'] + top['R'][-2:0:-1]
    for i in range(1,9):
        t = i/8
        ring = []
        for j in range(count):
            a = -math.pi/2+math.tau*j/count
            radius = .004*math.cos(a*11+t)*math.sin(t*math.pi)
            point = Vector(((mix(.211,.184,t)+radius)*math.cos(a),
                            -.008+(mix(.134,.121,t)+radius)*math.sin(a), mix(.882,.947,t)))
            ring.append(add(point,'hips'))
        for j in range(count):
            k = (j+1)%count
            faces.append((previous[j],previous[k],ring[k],ring[j]))
        previous = ring
    pants = c.mesh('Trousers • joined cotton work trousers', vertices, faces, cloth, skinning)

    def uv(face):
        # Both legs and waistband are unwrapped separately across their vertical seam.
        v = [(vertices[j].z-TROUSER_HEM)/(.947-TROUSER_HEM) for j in face.vertices]
        u = (face.index%count)/count
        du = 1/count
        order = (0,du,du,0) if face.index < count*34 or face.index >= count*68 else (0,du,du,0)[::-1]
        offset = .52 if count*34 <= face.index < count*68 else 0
        return [(offset+.48*(u+x), y) for x,y in zip(order,v)]

    make_uv(pants, uv)


def waist_wrap(c, profile, cloth, seam):
    rows = [[coat_point(profile,z+.005*math.sin(a+.4),a,ease)
             for a in (math.tau*j/64 for j in range(64))]
            for z,ease in ((.902,.006),(.904,.016),(.913,.026),(.937,.027),(.943,.017),
                           (.958,.026),(.975,.022),(.980,.011))]
    patch(c,'Waist wrap • folded umber cotton',rows,['hips']*len(rows),cloth,closed=True)
    c.tube('Waist wrap • exposed selvedge',rows[5],.00125,seam,'hips',cyclic=True)
    point = torso_face(profile,.946,-.094,-1,.030)
    c.ovoid('Waist wrap • flat tie',point,(.027,.018,.016),cloth,'hips',(0,-.36,-.15))
    tail = [[point+Vector((-.041*t+x,-.006-.009*t,-.022*t+.003*math.cos(x*110)))
             for x in (-.011,-.006,0,.006,.011)] for t in (0,.23,.52,.74,1)]
    patch(c,'Waist wrap • tucked end',tail,['hips']*len(tail),cloth)


def shoulder_cloth(c, profile, shirt, cloth, edge, thread):
    surface = BVHTree.FromPolygons([v.co.copy() for v in shirt.data.vertices],
                                  [p.vertices[:] for p in shirt.data.polygons])

    def edge_row(z, x, width, front, loose):
        points = []
        for j in range(24):
            u = j/23-.5
            zz = z+.016*u + .007*math.cos(5*u+z*4)
            xx = x+width*u
            p = torso_face(profile,zz,xx,front,.016)
            tip = .026*loose
            p.y += front*(tip + .007*math.cos(4*math.pi*u+z*8) + .0025*math.sin(10*math.pi*u-z*7))
            if z < .911:
                p.y = min(p.y,-.142-.033*smooth((.93-z)/.19))
            if z > .92:
                start = Vector((p.x,front,-.001+p.z))
                hit = surface.ray_cast(start,Vector((0,-front,0)),2)[0]
                if hit is not None and abs(hit.y)-abs(p.y) < .060:
                    p.y = front*max(abs(p.y),abs(hit.y)+.011)
            points.append(p)
        return points

    front = [edge_row(mix(.689,1.437,t), .127+.023*t+.012*math.sin(math.pi*t),
                      mix(.112,.129,t), -1, (1-t)**2) for t in (i/40 for i in range(41))]
    back = [edge_row(mix(1.437,.981,t), .150-.026*t, mix(.129,.118,t), 1, t**3)
            for t in (i/28 for i in range(29))]
    bridge = []
    for i in range(1,22):
        t = i/22
        row = []
        for u,(lead,trail) in enumerate(zip(front[-1],back[0])):
            p = lead.lerp(trail,t)
            p.z += (.072+.004*math.sin(u/23*math.tau*2))*math.sin(math.pi*t)**.81
            hit = surface.ray_cast(Vector((p.x,p.y,1.73)),Vector((0,0,-1)),.38)[0]
            if hit is not None:
                p.z = max(p.z,hit.z+.009)
            row.append(p)
        bridge.append(row)
    rows = front + bridge + back
    binding = [weights('hips','thigh.L',.80*smooth((.935-r[12].z)/.26)) if r[12].z < .94
               else body_weights(r[12].z) for r in rows]
    panel = patch(c,'Shoulder cloth • cinnamon handloom',rows,binding,cloth)
    panel['Placement'] = 'Anatomical left shoulder. Longer front end hangs above the left knee.'
    for label,lo,hi in (('inner',0,3),('outer',21,24)):
        border = [[p+Vector((0,-.0008 if r[12].y<0 else .0008,.0010)) for p in r[lo:hi]] for r in rows]
        patch(c,f'Shoulder cloth • {label} selvedge',border,binding,edge)
        c.tube(f'Shoulder cloth • {label} edge thread',[r[1] for r in border],.00095,thread,binding)
    for i in (0,-1):
        end, weight = rows[i], binding[i]
        c.tube(f'Shoulder cloth • rolled end {i}', end, .00165, edge, [weight]*len(end))
        for j,p in enumerate(end[1:-1:2]):
            d = Vector((.0010*math.sin(j*4.3), .0017 if i else -.0022, -.004-.001*math.sin(j)))
            c.tube(f'Shoulder cloth • exposed weft {i}.{j:02}', [p,p+d,p+1.5*d],
                   (.00041,.00032,.00017), thread, [weight]*3)


def dress(c):
    """Build the short working vest, knee-safe trousers, tie, and shoulder cloth."""
    profile = sorted(c.landmarks['torso_profile'])
    skin = [vertex.co.copy() for vertex in c.skin_mesh.data.vertices]
    river = fabric(c,'Faded river turquoise cotton',(.037,.179,.185),1.09,.138,.082,fine=False)
    facing = fabric(c,'Sun-faded vest facing',(.181,.225,.177),.92,.133,.067,fine=False)
    hemp = fabric(c,'Sand-ochre work trouser hemp',(.279,.229,.155),1.31,.155,.097,fine=False)
    cuff = fabric(c,'Dark reverse of rolled hemp',(.222,.181,.119),1.17,.148,.090,fine=False)
    brown = fabric(c,'Umber waist cloth',(.114,.072,.043),1.00,.143,.080,fine=False)
    cinnamon = fabric(c,'Cinnamon shoulder handloom',(.395,.171,.085),1.18,.152,.076,fine=False)
    edge = fabric(c,'Warm oat shoulder selvedge',(.426,.295,.167),.94,.127,.067,fine=False)
    thread = c.mat('Undyed plant fiber stitches',(.408,.330,.222),.92)
    first = len(c.parts)
    shirt = vest(c,profile,skin,river,facing,thread)
    trousers(c,skin,hemp,cuff,thread)
    waist_wrap(c,profile,brown,thread)
    shoulder_cloth(c,profile,shirt,cinnamon,edge,thread)
    fabrics = {river,facing,hemp,cuff,brown,cinnamon,edge}
    for piece in c.parts[first:]:
        if any(material in fabrics for material in piece.data.materials):
            store_rest_positions(piece.data)


def covered_skin(c):
    """Keep the real neck, exposed arms, and muddy feet outside the cloth."""
    arms = []
    for side,sign in (('L',1),('R',-1)):
        shoulder, elbow = (joint(c,part,side) for part in ('shoulder','elbow'))
        arms.append((sign,shoulder,(elbow-shoulder).normalized()))

    def visible(p):
        if p.z < TROUSER_HEM+.019 or p.z > 1.508:
            return True
        in_opening = p.y < -.053 and abs(p.x) < .058 and p.z > 1.407+.084*(abs(p.x)/.058)**.97
        if in_opening:
            return True
        for sign,shoulder,tangent in arms:
            inside = .194 + .22*max(0,1.385-p.z)
            if p.x*sign > inside and (p-shoulder).dot(tangent) > SLEEVE_END-.038:
                return True
        return False

    def fit_neck(point):
        if 1.508 <= point.z < 1.570:
            # Keep the cut shoulder surface inside the facing during neck turns.
            blend = smooth((point.z-1.508)/.062)
            neck_width = mix(.064,.085,blend)
            if abs(point.x) > .051:
                shoulder = (abs(point.x)-.051)/(neck_width-.051)
                fitted = .051+(neck_width-.051)*math.tanh(shoulder)
                point.x = math.copysign(mix(fitted,abs(point.x),smooth((point.z-1.555)/.015)),point.x)
            if point.y > -.068:
                point.y = .012 + (point.y-.012)*mix(.60,1.0,blend)

    c.fit_covered_skin((TROUSER_HEM+.019,1.408,1.508),visible,fit_neck)
