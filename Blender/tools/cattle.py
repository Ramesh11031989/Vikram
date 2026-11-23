"""गाय — the Halwai's neighbour's cow, the animal she frees by cutting its tether.

A Malvi-type zebu cow (the native breed of the Malwa plateau around Ujjain; the
breed is a guess, the chapter only says "गाय"): silver-grey coat darkening on the
neck and hump, small hump, moderate dewlap, short lyre horns, black switch.
Built to real scale in metres so the tether, her hands and the sickle can be
checked against it: 1.18 m at the withers, 1.30 m point of shoulder to pin bone.

It reuses the cast pipeline's skinned-mesh helpers (one armature, every part
weighted to named bones, FBX-friendly) with its own 29-bone quadruped skeleton.
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Sequence, Tuple

import bpy
from mathutils import Euler, Matrix, Vector

from character import Character
from groom import FiberGroup


Weight = Dict[str, float]


def smooth(a: float, b: float, x: float) -> float:
    t = max(0.0, min(1.0, (x-a)/(b-a)))
    return t*t*(3-2*t)


def normalise(weights: Weight) -> Weight:
    kept = {k: v for k, v in weights.items() if v > .004}
    total = sum(kept.values())
    return {k: v/total for k, v in kept.items()}


def curve(table: Sequence[Tuple[float, float]], x: float) -> float:
    """Catmull-Rom through (x, value) pairs sorted by x."""
    points = sorted(table)
    if x <= points[0][0]:
        return points[0][1]
    if x >= points[-1][0]:
        return points[-1][1]
    i = next(i for i in range(len(points)-1) if x <= points[i+1][0])
    p0, p1, p2, p3 = (points[max(i-1, 0)], points[i], points[i+1], points[min(i+2, len(points)-1)])
    t = (x-p1[0])/(p2[0]-p1[0])
    m1 = (p2[1]-p0[1])/(p2[0]-p0[0])*(p2[0]-p1[0])
    m2 = (p3[1]-p1[1])/(p3[0]-p1[0])*(p2[0]-p1[0])
    return ((2*t**3-3*t*t+1)*p1[1] + (t**3-2*t*t+t)*m1 + (-2*t**3+3*t*t)*p2[1] + (t**3-t*t)*m2)


# ------------------------------------------------------------------ anatomy

WITHERS = 1.18
TOP = ((.77,1.00), (.69,1.13), (.50,1.195), (.30,1.165), (.10,1.142), (-.10,1.145), (-.26,1.175),
       (-.37,1.240), (-.46,1.236), (-.55,1.13), (-.60,1.03))
BOTTOM = ((.77,.82), (.67,.74), (.52,.64), (.34,.555), (.10,.505), (-.15,.515), (-.35,.560),
          (-.50,.600), (-.58,.680), (-.61,.80))
WIDTH = ((.77,.07), (.71,.17), (.58,.222), (.46,.243), (.30,.256), (.10,.272), (-.10,.266),
         (-.28,.232), (-.42,.205), (-.53,.170), (-.61,.10))

# y, centre z, half width, height above centre, depth below centre
NECK = ((-.50,.93,.170,.30,.31), (-.62,.955,.142,.225,.235), (-.73,.99,.118,.160,.180),
        (-.83,1.03,.098,.118,.155), (-.90,1.07,.088,.095,.125))
ROPE_Y = -.765            # where the tether loop sits on the neck

HEAD_START = Vector((0, -.875, 1.118))
HEAD_END = Vector((0, -1.215, .795))
# s along the head, half width, dorsal (forehead) extent, ventral (jaw) extent
HEAD = ((0.00,.080,.055,.090), (0.07,.098,.072,.140), (0.20,.106,.074,.160), (0.33,.096,.068,.152),
        (0.48,.076,.062,.122), (0.63,.066,.057,.098), (0.78,.063,.056,.082), (0.90,.067,.056,.074),
        (0.965,.064,.050,.064), (1.00,.044,.032,.040))

FRONT_LEG = (Vector((.200,-.470,.930)), Vector((.170,-.385,.620)), Vector((.157,-.382,.360)),
             Vector((.152,-.398,.128)), Vector((.150,-.432,.058)))
REAR_LEG = (Vector((.200,.500,1.020)), Vector((.222,.375,.720)), Vector((.172,.600,.470)),
            Vector((.162,.585,.128)), Vector((.160,.552,.058)))
TAIL = (Vector((0,.745,1.055)), Vector((0,.790,1.000)), Vector((0,.812,.860)), Vector((0,.808,.660)),
        Vector((0,.795,.470)))


def head_frame() -> Tuple[Vector, Vector, Vector]:
    axis = (HEAD_END-HEAD_START).normalized()
    side = Vector((1, 0, 0))
    dorsal = axis.cross(side).normalized()
    return axis, side, dorsal


def head_section(s: float) -> Tuple[float, float, float]:
    return tuple(curve([(row[0], row[k]) for row in HEAD], s) for k in (1, 2, 3))


def head_point(s: float, x: float, d: float) -> Vector:
    axis, side, dorsal = head_frame()
    return HEAD_START + (HEAD_END-HEAD_START)*s + side*x + dorsal*d


def neck_section(y: float) -> Tuple[float, float, float, float]:
    return tuple(curve([(row[0], row[k]) for row in NECK], y) for k in (1, 2, 3, 4))


def body_point(y: float, t: float, side: int) -> Vector:
    """t = 0 on the spine, 1 under the belly."""
    top, bottom, width = curve(TOP, y), curve(BOTTOM, y), curve(WIDTH, y)
    zf = (1+math.cos(math.pi*t))/2
    z = bottom + (top-bottom)*zf
    belly = smooth(0, .66, t)
    x = width*math.sin(math.pi*t)**.62*(.60+.40*belly)
    x += .034*math.exp(-((y-.47)/.06)**2-((t-.20)/.08)**2)      # hook bones
    x += .018*math.exp(-((y-.67)/.04)**2-((t-.32)/.07)**2)      # pin bones
    x += .022*math.exp(-((y+.50)/.07)**2-((t-.52)/.12)**2)      # point of shoulder
    x += .016*math.exp(-((y+.38)/.10)**2-((t-.30)/.12)**2)      # shoulder blade
    x -= .010*math.exp(-((y-.30)/.07)**2-((t-.25)/.07)**2)      # paralumbar hollow
    z += .008*math.exp(-(x/.03)**2)*zf                          # spine
    return Vector((side*x, y, z))


# ------------------------------------------------------------------ the cow

class Cow(Character):
    """Reuses the cast's skinned-mesh helpers with a quadruped skeleton."""

    def __init__(self, name: str = 'Cow'):
        self.spec = {'name': name}
        self.name = name
        self.scale = 1.0
        self.scene = bpy.data.scenes.new(name)
        self.scene.render.fps = 24
        self.scene.unit_settings.system = 'METRIC'
        bpy.context.window.scene = self.scene
        self.collection = bpy.data.collections.new(f'AN_{name}')
        self.scene.collection.children.link(self.collection)
        self.collection.asset_mark()
        self.collection.asset_data.description = 'Malvi-type zebu cow | Vikram–Betal, real scale, 24 fps'
        self.parts = []
        self.rig = self.make_rig()

    def make_rig(self):
        armature = bpy.data.armatures.new(f'{self.name}_Skeleton')
        rig = bpy.data.objects.new(f'{self.name}_Rig', armature)
        self.collection.objects.link(rig)
        rig.show_in_front = True
        armature.display_type = 'STICK'
        bpy.context.view_layer.objects.active = rig
        rig.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')

        def bone(name, head, tail, parent=None, deform=True):
            item = armature.edit_bones.new(name)
            item.head, item.tail = Vector(head), Vector(tail)
            item.use_deform = deform
            if parent:
                item.parent = armature.edit_bones[parent]

        bone('root', (0,0,0), (0,0,.3), deform=False)
        bone('pelvis', (0,.50,1.10), (0,.15,1.11), 'root')
        bone('spine', (0,.15,1.11), (0,-.20,1.11), 'pelvis')
        bone('chest', (0,-.20,1.11), (0,-.48,1.06), 'spine')
        bone('neck_1', (0,-.48,1.00), (0,-.68,.98), 'chest')
        bone('neck_2', (0,-.68,.98), (0,-.86,1.04), 'neck_1')
        bone('head', HEAD_START, HEAD_END, 'neck_2')
        for side, sign in (('L',1), ('R',-1)):
            base = head_point(.06, sign*.082, -.012)
            bone(f'ear.{side}', base, base + Vector((sign*.17, .05, -.07)), 'head')
            f, r = [Vector((sign*p.x, p.y, p.z)) for p in FRONT_LEG], [Vector((sign*p.x, p.y, p.z)) for p in REAR_LEG]
            names = (f'upper_arm.{side}', f'forearm.{side}', f'front_cannon.{side}', f'front_pastern.{side}')
            parent = 'chest'
            for i, name in enumerate(names):
                bone(name, f[i], f[i+1], parent)
                parent = name
            names = (f'thigh.{side}', f'shin.{side}', f'rear_cannon.{side}', f'rear_pastern.{side}')
            parent = 'pelvis'
            for i, name in enumerate(names):
                bone(name, r[i], r[i+1], parent)
                parent = name
        parent = 'pelvis'
        for i in range(4):
            bone(f'tail_{i+1}', TAIL[i], TAIL[i+1], parent)
            parent = f'tail_{i+1}'
        bpy.ops.object.mode_set(mode='OBJECT')
        rig['Usage'] = 'Quadruped FK skeleton. Neck_2 carries the tether loop; tail and ears are free for secondary motion.'
        return rig


# ------------------------------------------------------------------ weights

def body_weight(p: Vector) -> Weight:
    y = p.y
    pelvis = smooth(.10, .40, y)
    chest = 1-smooth(-.40, -.08, y)
    w = {'pelvis': pelvis, 'chest': chest, 'spine': max(0.0, 1-pelvis-chest)}
    side = 'L' if p.x > 0 else 'R'
    thigh = .55*smooth(.30, .52, y)*(1-smooth(.74, .98, p.z))*smooth(.06, .17, abs(p.x))
    arm = .40*(1-smooth(-.30, -.20, y))*smooth(-.62, -.48, y)*(1-smooth(.70, .92, p.z))*smooth(.06, .15, abs(p.x))
    for key in w:
        w[key] *= 1-thigh-arm
    w[f'thigh.{side}'] = thigh
    w[f'upper_arm.{side}'] = arm
    return normalise(w)


def neck_weight(p: Vector) -> Weight:
    y = p.y
    head = 1-smooth(-.90, -.86, y)
    chest = smooth(-.58, -.46, y)
    neck1 = (1-chest)*smooth(-.78, -.66, y)
    neck2 = max(0.0, 1-head-chest-neck1)
    return normalise({'head': head, 'chest': chest, 'neck_1': neck1, 'neck_2': neck2})


def chain_weight(p: Vector, joints: Sequence[Vector], names: Sequence[str], parent: str) -> Weight:
    """Weight along a limb chain by projected position, blending around each joint."""
    best, best_t, best_d = 0, 0.0, 1e9
    for i in range(len(joints)-1):
        a, b = joints[i], joints[i+1]
        ab = b-a
        t = max(0.0, min(1.0, (p-a).dot(ab)/ab.length_squared))
        d = (a+ab*t-p).length
        if d < best_d:
            best, best_t, best_d = i, t, d
    w: Weight = {names[best]: 1.0}
    length = (joints[best+1]-joints[best]).length
    blend = min(.45, .05/length)
    if best_t < blend:
        share = .5*(1-best_t/blend)
        w[names[best]] = 1-share
        w[names[best-1] if best > 0 else parent] = share
    elif best_t > 1-blend and best+1 < len(names):
        share = .5*(1-(1-best_t)/blend)
        w[names[best]] = 1-share
        w[names[best+1]] = share
    return normalise(w)


# ------------------------------------------------------------------ materials

def coat_material(cow) -> bpy.types.Material:
    m = cow.mat('Malvi grey coat', (.58,.56,.52), .62)
    tree = m.node_tree
    nodes, links = tree.nodes, tree.links
    shader = nodes.get('Principled BSDF')
    shader.inputs['Sheen Weight'].default_value = .55
    shader.inputs['Sheen Roughness'].default_value = .38
    shader.inputs['Specular IOR Level'].default_value = .28
    shader.inputs['Subsurface Weight'].default_value = .03
    shader.inputs['Subsurface Radius'].default_value = (1, .45, .3)
    shader.inputs['Subsurface Scale'].default_value = .01
    regional = nodes.new('ShaderNodeAttribute')
    regional.attribute_name = 'Coat colour'
    regional.location = (-900, 300)
    coords = nodes.new('ShaderNodeTexCoord')
    coords.location = (-1300, 0)
    mottle = nodes.new('ShaderNodeTexNoise')
    mottle.label = 'Dusty mottling'
    mottle.inputs['Scale'].default_value = 9
    mottle.inputs['Detail'].default_value = 6
    links.new(coords.outputs['Object'], mottle.inputs['Vector'])
    vary = nodes.new('ShaderNodeMapRange')
    vary.inputs['To Min'].default_value = .86
    vary.inputs['To Max'].default_value = 1.10
    links.new(mottle.outputs['Fac'], vary.inputs['Value'])
    tint = nodes.new('ShaderNodeVectorMath')
    tint.operation = 'SCALE'
    links.new(regional.outputs['Color'], tint.inputs[0])
    links.new(vary.outputs['Result'], tint.inputs['Scale'])
    links.new(tint.outputs[0], shader.inputs['Base Color'])
    # Short hair lying backwards along the body: streaky microrelief.
    stretch = nodes.new('ShaderNodeMapping')
    stretch.inputs['Scale'].default_value = (900, 95, 340)
    links.new(coords.outputs['Object'], stretch.inputs['Vector'])
    streaks = nodes.new('ShaderNodeTexNoise')
    streaks.label = 'Hair lie'
    streaks.inputs['Scale'].default_value = 1
    streaks.inputs['Detail'].default_value = 2
    links.new(stretch.outputs['Vector'], streaks.inputs['Vector'])
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .32
    bump.inputs['Distance'].default_value = .0007
    links.new(streaks.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    return m


def coat_colour(p: Vector) -> Tuple[float, float, float]:
    base = Vector((.60,.585,.545))
    dark = Vector((.33,.325,.315))
    pale = Vector((.70,.68,.64))
    shade = .85*smooth(-.20, -.52, p.y)*smooth(.80, 1.05, p.z)           # hump and crest
    shade = max(shade, .65*smooth(-.35, -.62, p.y)*smooth(.55, .80, p.z))  # neck and shoulder
    shade = max(shade, .55*(1-smooth(.20, .42, p.z)))                      # lower legs
    belly = smooth(.62, .50, p.z)*smooth(.75, .55, abs(p.y)+.2)*(1-smooth(.12, .22, abs(p.x)))
    colour = base.lerp(dark, shade).lerp(pale, belly*.8)
    return tuple(colour)


def paint(obj, colour_of) -> None:
    attribute = obj.data.color_attributes.new('Coat colour', 'FLOAT_COLOR', 'POINT')
    values = []
    for vertex in obj.data.vertices:
        values.extend((*colour_of(vertex.co), 1))
    attribute.data.foreach_set('color', values)


# ------------------------------------------------------------------ parts

def build_body(cow, coat) -> None:
    rows, columns = 60, 56
    verts, weights = [], []
    for r in range(rows):
        y = .775 - (.775+.605)*r/(rows-1)
        for k in range(columns):
            u = k/columns
            side = 1 if u < .5 else -1
            t = u*2 if u < .5 else (1-u)*2
            p = body_point(y, t, side)
            verts.append(tuple(p))
            weights.append(body_weight(p))
    faces = []
    for r in range(rows-1):
        for k in range(columns):
            n = (k+1) % columns
            faces.append((r*columns+k, (r+1)*columns+k, (r+1)*columns+n, r*columns+n))
    faces.append(tuple(range(columns)))
    last = (rows-1)*columns
    faces.append(tuple(reversed(range(last, last+columns))))
    body = cow.mesh('Body', verts, faces, coat, weights)
    paint(body, coat_colour)


def build_neck(cow, coat) -> None:
    rows, columns = 30, 48
    verts, weights = [], []
    for r in range(rows):
        y = -.48 - (.93-.48)*r/(rows-1)
        zc, hw, up, down = neck_section(y)
        for k in range(columns):
            a = math.tau*k/columns
            c, s = math.cos(a), math.sin(a)
            reach = up if s > 0 else down
            width = hw*(1 - .28*max(0.0, s)**3)         # narrower crest
            x = width*math.copysign(abs(c)**.85, c)
            z = zc + reach*s
            p = Vector((x, y, z))
            verts.append(tuple(p))
            weights.append(neck_weight(p))
    faces = []
    for r in range(rows-1):
        for k in range(columns):
            n = (k+1) % columns
            faces.append((r*columns+k, r*columns+n, (r+1)*columns+n, (r+1)*columns+k))
    neck = cow.mesh('Neck', verts, faces, coat, weights)
    paint(neck, coat_colour)
    # Dewlap: a soft fold hanging from throat to brisket.
    rows, columns = 26, 12
    verts, weights = [], []
    for r in range(rows):
        t = r/(rows-1)
        y = -.88 + (.88-.52)*t
        zc, hw, up, down = neck_section(y)
        top = zc - down*.82
        hang = .045 + .10*math.sin(math.pi*min(1, t*1.15))**1.2
        if y > -.62:
            top = min(top, curve(BOTTOM, y) + .05)
        for k in range(columns):
            a = math.tau*k/columns
            depth = (1 - math.cos(a))/2              # 0 at the attachment, 1 at the free edge
            p = Vector((.014*math.sin(a)*(1-.5*depth), y + .01*math.sin(5*t)*depth, top - hang*depth))
            verts.append(tuple(p))
            weights.append(neck_weight(p) if y < -.55 else normalise({'chest': 1.0}))
    faces = []
    for r in range(rows-1):
        for k in range(columns):
            n = (k+1) % columns
            faces.append((r*columns+k, r*columns+n, (r+1)*columns+n, (r+1)*columns+k))
    dewlap = cow.mesh('Dewlap', verts, faces, coat, weights)
    paint(dewlap, coat_colour)


def build_head(cow, coat, muzzle, horn, eye_m, lid_m, lash_m) -> None:
    rows, columns = 44, 48
    verts, weights = [], []
    axis, side_v, dorsal = head_frame()
    for r in range(rows):
        s = r/(rows-1)
        hw, up, down = head_section(s)
        for k in range(columns):
            a = math.tau*k/columns
            c, sn = math.cos(a), math.sin(a)
            if sn > 0:
                d = up*math.copysign(abs(sn)**.75, sn)
                x = hw*math.copysign(abs(c)**.62, c)
            else:
                d = down*sn
                x = hw*c*(1-.12*max(0.0, -sn))
            # orbit bulge, nostrils and lip line
            x += math.copysign(.016, c)*math.exp(-((s-.24)/.07)**2)*max(0.0, abs(c)-.2)*max(0.0, sn+.4)
            if s > .9:
                nostril = math.exp(-((abs(x)-.026)/.011)**2-((d-.020)/.014)**2)*smooth(.9, .97, s)
                d -= .008*nostril
            lip = math.exp(-((d+.030)/.006)**2)*smooth(.62, .80, s)*max(0.0, abs(c)-.3)
            x -= math.copysign(.0035*lip, c)
            p = head_point(s, x, d)
            verts.append(tuple(p))
            weights.append({'head': 1.0} if s > .06 else neck_weight(p))
    faces = []
    for r in range(rows-1):
        for k in range(columns):
            n = (k+1) % columns
            faces.append((r*columns+k, r*columns+n, (r+1)*columns+n, (r+1)*columns+k))
    last = (rows-1)*columns
    faces.append(tuple(range(last, last+columns)))
    head = cow.mesh('Head', verts, faces, coat, weights)
    head.data.materials.append(muzzle)
    for polygon in head.data.polygons:
        if polygon.index < (rows-1)*columns:
            s = (polygon.index//columns)/(rows-1)
            if s > .86:
                polygon.material_index = 1
        else:
            polygon.material_index = 1

    def head_colour(p: Vector) -> Tuple[float, float, float]:
        base = Vector(coat_colour(p))
        rel = p - HEAD_START
        s = rel.dot(axis)/(HEAD_END-HEAD_START).length
        eye = math.exp(-((s-.24)/.06)**2)*smooth(.06, .10, abs(p.x))
        face = smooth(.4, .8, s)
        colour = base.lerp(Vector((.50,.49,.47)), face*.6).lerp(Vector((.22,.21,.20)), eye*.7)
        return tuple(colour)
    paint(head, head_colour)

    for sign, side in ((1, 'L'), (-1, 'R')):
        # eye
        centre = head_point(.245, sign*.099, .022)
        out = Vector((sign*.92, -.12, .25)).normalized()
        cow.ovoid(f'Eye {side}', tuple(centre), (.0185,.0185,.0170), eye_m, 'head')
        for k, (scale, lift) in enumerate(((1.12, .004), (1.30, .0055), (1.55, .002))):
            ring = []
            for j in range(40):
                a = math.tau*j/40
                local = Vector((0, math.cos(a)*.0185*scale, math.sin(a)*.0150*scale))
                local.z += .0045*scale*max(0.0, math.sin(a))      # heavier upper lid
                rot = Vector((1, 0, 0)).rotation_difference(out)
                ring.append(tuple(centre + rot @ (local + Vector((.0105 + lift*k*.3, 0, 0)))))
            cow.tube(f'Eyelid fold {side} {k+1}', ring, .0032 - .0006*k, lid_m, 'head', cyclic=True)
        # lashes on the upper lid
        lash = FiberGroup(cow, (.05,.045,.04), (.30,.28,.25))
        rot = Vector((1, 0, 0)).rotation_difference(out)
        for j in range(60):
            a = math.pi*(.12 + .76*j/59)
            root = centre + rot @ Vector((.0135, math.cos(a)*.0205, math.sin(a)*.0175 + .004))
            grow = rot @ Vector((.6, math.cos(a)*.35, .9)).normalized()
            length = .016*(.6+.4*math.sin(math.pi*(j/59)))
            path = [root + grow*length*t + Vector((0, 0, -.004*t*t)) for t in (0, .33, .66, 1)]
            lash.add(path, .00016, 2, 4)
        lash.make_mesh(f'Eyelashes {side}')
        # ear: a cupped leaf
        base = head_point(.06, sign*.082, -.012)
        direction = Vector((sign*.92, .26, -.30)).normalized()
        across = Vector((0, -.35, .94)).normalized()
        across = (across - direction*across.dot(direction)).normalized()
        normal = direction.cross(across)
        rows_e, cols_e = 16, 13
        verts_e, weights_e, colours = [], [], []
        for layer, offset in ((0, .0035), (1, -.0035)):
            for i in range(rows_e):
                u = i/(rows_e-1)
                length = .20*u
                width = .052*math.sin(math.pi*min(1, u*1.05))**.7*(1-.25*u)
                for j in range(cols_e):
                    v = j/(cols_e-1)*2-1
                    cup = .018*(1-v*v)*math.sin(math.pi*u)
                    p = base + direction*length + across*v*width + normal*(offset*(1-u*.6) - cup*sign)
                    verts_e.append(tuple(p))
                    weights_e.append(normalise({f'ear.{side}': smooth(0, .3, u), 'head': 1-smooth(0, .3, u)}))
                    colours.append((.36,.30,.28) if layer == 1 and abs(v) < .75 and u > .12 else coat_colour(Vector((0, -.95, 1.1))))
        faces_e = []
        half = rows_e*cols_e
        for i in range(rows_e-1):
            for j in range(cols_e-1):
                a = i*cols_e+j
                faces_e.append((a, a+1, a+cols_e+1, a+cols_e))
                faces_e.append((half+a, half+a+cols_e, half+a+cols_e+1, half+a+1))
        for i in range(rows_e-1):
            for j in (0, cols_e-1):
                a = i*cols_e+j
                faces_e.append((a, a+cols_e, half+a+cols_e, half+a) if j == 0 else (a, half+a, half+a+cols_e, a+cols_e))
        last = (rows_e-1)*cols_e
        for j in range(cols_e-1):
            faces_e.append((last+j, half+last+j, half+last+j+1, last+j+1))
        ear = cow.mesh(f'Ear {side}', verts_e, faces_e, coat, weights_e)
        attribute = ear.data.color_attributes.new('Coat colour', 'FLOAT_COLOR', 'POINT')
        attribute.data.foreach_set('color', [v for c in colours for v in (*c, 1)])
        # horn: lyre shape, outwards, up, then forward
        root = head_point(.015, sign*.064, .046)
        path = [root, root + Vector((sign*.050, .004, .030)), root + Vector((sign*.088, -.004, .090)),
                root + Vector((sign*.100, -.030, .160)), root + Vector((sign*.086, -.052, .215)),
                root + Vector((sign*.066, -.058, .240))]
        radii = [.026, .023, .018, .013, .008, .003]
        cow.tube(f'Horn {side}', [tuple(p) for p in path], radii, horn, 'head')
        for ring_index, t in enumerate((.12, .22, .32)):
            p = path[0].lerp(path[1], t*3) if t < .33 else path[1]
            cow.tube(f'Horn growth ring {side} {ring_index+1}',
                     [tuple(p + Vector((0, .0265*math.cos(math.tau*j/16), .0265*math.sin(math.tau*j/16)))) for j in range(16)],
                     .0016, horn, 'head', cyclic=True)
    cow.ovoid('Poll', tuple(head_point(.02, 0, .052)), (.055,.035,.03), coat, 'head')
    paint(cow.parts[-1], coat_colour)


def build_legs(cow, coat, hoof) -> None:
    front_radii = ((.105,.120), (.072,.085), (.060,.068), (.046,.052), (.040,.046), (.033,.038),
                   (.034,.040), (.040,.045), (.034,.038), (.033,.036))
    rear_radii = ((.110,.150), (.090,.120), (.070,.085), (.050,.070), (.045,.075), (.036,.046),
                  (.033,.040), (.040,.046), (.034,.038), (.033,.036))
    for sign, side in ((1, 'L'), (-1, 'R')):
        for label, joints, radii, names, parent in (
                ('Front leg', FRONT_LEG, front_radii,
                 (f'upper_arm.{side}', f'forearm.{side}', f'front_cannon.{side}', f'front_pastern.{side}'), 'chest'),
                ('Hind leg', REAR_LEG, rear_radii,
                 (f'thigh.{side}', f'shin.{side}', f'rear_cannon.{side}', f'rear_pastern.{side}'), 'pelvis')):
            j = [Vector((sign*p.x, p.y, p.z)) for p in joints]
            # sample the chain densely
            samples = []
            for i in range(len(j)-1):
                for k in range(8 if i < 3 else 5):
                    samples.append((i + k/(8 if i < 3 else 5), j[i].lerp(j[i+1], k/(8 if i < 3 else 5))))
            samples.append((len(j)-1, j[-1]))
            rings, ws = [], []
            for position, point in samples:
                f = position/(len(j)-1)*(len(radii)-1)
                lo = int(min(f, len(radii)-2))
                t = f-lo
                rx = radii[lo][0]*(1-t) + radii[lo+1][0]*t
                ry = radii[lo][1]*(1-t) + radii[lo+1][1]*t
                segment = min(int(position), len(j)-2)
                tangent = (j[segment+1]-j[segment]).normalized()
                u = Vector((1, 0, 0))
                u = (u - tangent*u.dot(tangent)).normalized()
                v = tangent.cross(u).normalized()
                ring = []
                for a in range(24):
                    ang = math.tau*a/24
                    back = max(0.0, math.sin(ang)*(1 if v.y > 0 else -1))
                    tendon = 1 + .10*back*smooth(1.2, 1.6, position)*(1-smooth(2.6, 3.0, position))
                    ring.append(point + u*rx*math.cos(ang) + v*ry*math.sin(ang)*tendon)
                rings.append(ring if sign > 0 else ring[::-1])
                ws.append(chain_weight(point, j, names, parent))
            leg = cow.ring_mesh(f'{label} {side}', [[tuple(p) for p in ring] for ring in rings], coat, ws)
            paint(leg, coat_colour)
            # cloven hoof: two claws
            coronet = j[-1]
            ahead = Vector((0, -1, 0))
            for claw, dx in (('outer', .020), ('inner', -.020)):
                rings_h = []
                for k in range(7):
                    t = k/6
                    z = coronet.z - .004 - (coronet.z - .001)*t
                    reach = .040 + .028*t
                    half = .018 + .004*t
                    ring = []
                    for a in range(20):
                        ang = math.tau*a/20
                        c, s = math.cos(ang), math.sin(ang)
                        y = (reach if s < 0 else .030)*s
                        x = half*c*(1 - .45*max(0.0, -s)**2)
                        ring.append(tuple(Vector((coronet.x + sign*dx + x, coronet.y + y - .012*t, z))))
                    rings_h.append(ring if sign > 0 else ring[::-1])
                cow.ring_mesh(f'Hoof {side} {label} {claw}', rings_h, hoof, names[-1])
            back = Vector((sign*(-.0), .045 if label == 'Front leg' else .040, .0))
            for dx in (.016, -.016):
                cow.ovoid(f'Dewclaw {side} {label} {dx}', tuple(j[3] + Vector((sign*dx, .040, .030))),
                          (.009,.010,.012), hoof, names[-1])


def build_tail(cow, coat, switch_m) -> None:
    points = []
    for i in range(len(TAIL)-1):
        for k in range(6):
            points.append(TAIL[i].lerp(TAIL[i+1], k/6))
    points.append(TAIL[-1] + Vector((0, -.004, -.04)))
    radii = [.032*(1-i/len(points))**.7 + .009 for i in range(len(points))]
    names = [f'tail_{i+1}' for i in range(4)]
    weights = [chain_weight(p, TAIL, names, 'pelvis') for p in points]
    tail = cow.tube('Tail', [tuple(p) for p in points], radii, coat, weights)
    paint(tail, coat_colour)
    rand = random.Random(29)
    switch = FiberGroup(cow, (.012,.011,.010), (.10,.09,.08))
    tip = TAIL[-1]
    for _ in range(700):
        a = rand.uniform(0, math.tau)
        r = .010*math.sqrt(rand.random())
        start = tip + Vector((r*math.cos(a), r*math.sin(a), rand.uniform(-.02, .05)))
        length = rand.uniform(.16, .27)
        spread = Vector((math.cos(a), math.sin(a), 0))*rand.uniform(.01, .04)
        path = [start + spread*t*t + Vector((rand.uniform(-.003, .003), 0, -length*t)) for t in (0, .25, .5, .75, 1)]
        switch.add(path, rand.uniform(.00025, .00042), rand.randrange(0, 5), 5)
    obj_count = len(cow.parts)
    switch.make_mesh('Tail switch')
    switch_obj = cow.parts[-1]
    for group in list(switch_obj.vertex_groups):
        switch_obj.vertex_groups.remove(group)
    switch_obj.vertex_groups.new(name='tail_4').add(list(range(len(switch_obj.data.vertices))), 1, 'REPLACE')


def build_udder(cow, coat, teat_m) -> None:
    udder = cow.ovoid('Udder', (0, .47, .585), (.070, .092, .060), teat_m, 'pelvis')
    for x in (-.032, .032):
        for y in (.43, .51):
            cow.tube(f'Teat {x} {y}', [(x, y, .55), (x*1.05, y, .525), (x*1.08, y, .505)], [.010, .009, .007], teat_m, 'pelvis')


def neck_fibers(cow, coat_parts: Sequence[bpy.types.Object]) -> None:
    """Real short hair over the neck band the camera sees in the rope-cutting close-up."""
    rand = random.Random(57)
    neck = next(p for p in cow.parts if p.name == f'{cow.name}_Neck')
    mesh = neck.data
    fibers = FiberGroup(cow, (.26,.25,.24), (.74,.72,.68))
    triangles = []
    for polygon in mesh.polygons:
        centre = polygon.center
        if -.88 < centre.y < -.64:
            v = [mesh.vertices[i].co for i in polygon.vertices]
            area = polygon.area
            triangles.append((area, v, polygon.normal.copy()))
    total = sum(t[0] for t in triangles)
    count = 26000
    for area, v, normal in triangles:
        n = int(count*area/total + rand.random())
        for _ in range(n):
            a, b = rand.random(), rand.random()
            if a + b > 1:
                a, b = 1-a, 1-b
            root = v[0] + (v[1]-v[0])*a + (v[3 if len(v) > 3 else 2]-v[0])*b
            flow = Vector((0, .85, -.45))
            flow = (flow - normal*flow.dot(normal)).normalized()
            length = rand.uniform(.006, .013)
            wobble = Vector((rand.uniform(-.2, .2), rand.uniform(-.2, .2), rand.uniform(-.2, .2)))
            direction = (flow + wobble*.5 + normal*.35).normalized()
            lay = (flow + wobble*.4 + normal*.05).normalized()
            path = [root - normal*.0006, root + direction*length*.45, root + direction*length*.6 + lay*length*.45]
            fibers.add(path, rand.uniform(.00007, .00012), rand.randrange(0, 7), 6)
    fibers.make_mesh('Neck coat fibers')
    obj = cow.parts[-1]
    for group in list(obj.vertex_groups):
        obj.vertex_groups.remove(group)
    groups: Dict[str, object] = {}
    for vertex in obj.data.vertices:
        for bone, value in neck_weight(vertex.co).items():
            if bone not in groups:
                groups[bone] = obj.vertex_groups.new(name=bone)
            groups[bone].add([vertex.index], value, 'REPLACE')


def build() -> Cow:
    cow = Cow()
    coat = coat_material(cow)
    muzzle = cow.mat('Moist slate muzzle', (.045,.043,.042), .34)
    muzzle.node_tree.nodes.get('Principled BSDF').inputs['Coat Weight'].default_value = .35
    horn = cow.mat('Weathered horn', (.10,.095,.088), .45)
    hoof = cow.mat('Dark hoof keratin', (.06,.055,.05), .5)
    eye = cow.mat('Dark wet eye', (.012,.008,.006), .05)
    eye.node_tree.nodes.get('Principled BSDF').inputs['Coat Weight'].default_value = 1
    lids = cow.mat('Dark eyelid skin', (.10,.085,.08), .55)
    teat = cow.mat('Pink-grey udder skin', (.40,.29,.26), .5)
    build_body(cow, coat)
    build_neck(cow, coat)
    build_head(cow, coat, muzzle, horn, eye, lids, lids)
    build_legs(cow, coat, hoof)
    build_tail(cow, coat, hoof)
    build_udder(cow, coat, teat)
    neck_fibers(cow, cow.parts)
    cow.validate()
    cow.rig['Breed'] = 'Malvi-type zebu cow (guess)'
    cow.rig['Withers_height_m'] = WITHERS
    return cow


def neck_loop(slack: float = .012, sag: float = .035) -> List[Vector]:
    """The tether loop path around the neck at ROPE_Y, in the cow's rest coordinates."""
    zc, hw, up, down = neck_section(ROPE_Y)
    points = []
    for k in range(64):
        a = math.tau*k/64
        c, s = math.cos(a), math.sin(a)
        reach = (up if s > 0 else down) + slack
        width = (hw*(1 - .28*max(0.0, s)**3)) + slack
        x = width*math.copysign(abs(c)**.85, c)
        z = zc + reach*s - sag*max(0.0, -s)**3
        y = ROPE_Y + .018*s    # loop leans back over the crest
        points.append(Vector((x, y, z)))
    return points
