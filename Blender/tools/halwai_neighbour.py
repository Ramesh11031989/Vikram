"""हलवाई की पड़ोसन — the Halwai's neighbour, a witness who cut her cow's tether.

She is built on the shared cast skeleton (the same 34 bone names and hierarchy as
Vikram, Betal and Gopal, in the same T-pose) with extra finger and thumb
segments per hand (20 in all) so she can close a hand around the rope in the cutting close-up. Her
proportions are realistic (about 7.3 heads, 1.54 m) rather than the stylized
cast's 5.8 heads, following the realism of the series reference.

Costume (a guess, marked in the asset notes): Malwa village dress of ghagra,
kurti and an odhni drawn over the head with one end tucked at the waist.
Story-neutral jewellery only; no marital markers, because the chapter does not
say whether she is married. No red cloth, which belongs to Nandu's clue.
"""

from __future__ import annotations

import math
import random
from typing import Callable, Dict, List, Sequence, Tuple, Union

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

from character import Character
from groom import FiberGroup
import facial_controls
import sculpted_face as sf
from textile import finish_fabric, store_rest_positions


Weight = Union[str, Dict[str, float]]
Point = Tuple[float, float, float]

SPEC = dict(name='HalwaiNeighbour', height=.868, skin=(.385,.205,.112),
            hair=(.034,.023,.017), iris=(.072,.038,.017), face_width=.95,
            nose_width=.93, brow_lift=.002)


# ---------------------------------------------------------------- proportions

def smooth(a: float, b: float, x: float) -> float:
    t = max(0.0, min(1.0, (x-a)/(b-a)))
    return t*t*(3-2*t)


def _stretch(z: float) -> float:
    """Vertical stretch of the shared body: longer torso, shorter neck, smaller head."""
    k = 1.0
    k += (1.2388-1.0)*smooth(1.02,1.07,z)
    k += (.60-1.2388)*smooth(1.35,1.40,z)
    k += (.72-.60)*smooth(1.47,1.52,z)
    return k


_STEP = .0005
_TABLE: List[float] = [0.0]
for _i in range(1, 4400):
    _z0 = (_i-1)*_STEP
    _TABLE.append(_TABLE[-1] + _STEP*.5*(_stretch(_z0)+_stretch(_z0+_STEP)))


def vertical(z: float) -> float:
    if z <= 0:
        return z
    position = z/_STEP
    index = min(int(position), len(_TABLE)-2)
    t = position-index
    return _TABLE[index]*(1-t) + _TABLE[index+1]*t


def girth(z: float) -> float:
    """Horizontal scale: a fuller neck, then a smaller head."""
    s = 1 + .13*smooth(1.36,1.40,z)
    s += (.80-1.13)*smooth(1.45,1.50,z)
    return s


HEAD_AXIS_Y = -.008


def morph(p: Vector) -> Vector:
    """Map a point of the shared (stylized) body to her realistic proportions."""
    x, y, z = p
    s = girth(z)
    return Vector((x*s, HEAD_AXIS_Y + (y-HEAD_AXIS_Y)*s, vertical(z)))


ARM_Z = vertical(1.375)
EYE_Z = vertical(1.675)
HEAD_TOP = vertical(1.840)


# ------------------------------------------------------------- hand anatomy

# index, MCP (x, y), sideways spread, segment lengths, proximal radius
FINGERS = (
    (1, (.887,-.0345), -.15, (.039,.024,.021), .0094),
    (2, (.891,-.0115), -.05, (.043,.027,.022), .0097),
    (3, (.887,.0115), .06, (.040,.026,.021), .0092),
    (4, (.877,.0335), .19, (.031,.020,.018), .0079),
)
PALM_END = .899
THUMB = ((.795,-.020,-.010), (.830,-.048,-.016), (.857,-.065,-.019), (.879,-.078,-.021))


def finger_joints(spread: float, mcp: Tuple[float, float], lengths: Sequence[float]) -> List[Vector]:
    direction = Vector((1, spread, -.035)).normalized()
    start = Vector((mcp[0], mcp[1], ARM_Z-.002))
    points = [start]
    for length in lengths:
        points.append(points[-1] + direction*length)
    return points


def thumb_joints() -> List[Vector]:
    return [Vector((x, y, ARM_Z+z)) for x, y, z in THUMB]


def mirror(point: Sequence[float], sign: int) -> Point:
    return (sign*point[0], point[1], point[2])


# ---------------------------------------------------------------- character

class NeighbourCharacter(Character):
    """The shared Character, with her proportions and a fuller hand rig."""

    def __init__(self, spec):
        self.morphing = False
        super().__init__(spec)

    def mesh(self, name, verts, faces, material, bone, smooth=True):
        if self.morphing:
            verts = [tuple(morph(Vector(p))) for p in verts]
        return super().mesh(name, verts, faces, material, bone, smooth)

    def make_rig(self):
        armature = bpy.data.armatures.new(f'{self.name}_Skeleton')
        rig = bpy.data.objects.new(f'{self.name}_Rig', armature)
        self.collection.objects.link(rig)
        rig.show_in_front = True
        armature.display_type = 'STICK'
        bpy.context.view_layer.objects.active = rig
        rig.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')

        def bone(name, start, end, parent=None, deform=True, warp=False):
            item = armature.edit_bones.new(name)
            head, tail = Vector(start), Vector(end)
            if warp:
                head, tail = morph(head), morph(tail)
            item.head = head*self.scale
            item.tail = tail*self.scale
            item.use_deform = deform
            if parent:
                item.parent = armature.edit_bones[parent]
            return item

        bone('root', (0,0,0), (0,0,.19), deform=False)
        bone('hips', (0,0,.91), (0,0,1.04), 'root', warp=True)
        bone('spine', (0,0,1.04), (0,0,1.22), 'hips', warp=True)
        bone('chest', (0,0,1.22), (0,0,1.39), 'spine', warp=True)
        bone('neck', (0,0,1.39), (0,-.013,1.5), 'chest', warp=True)
        bone('head', (0,-.013,1.5), (0,-.013,1.801), 'neck', warp=True)
        for side, sign in (('L',1), ('R',-1)):
            bone(f'clavicle.{side}', (sign*.040,-.004,ARM_Z-.006), (sign*.175,0,ARM_Z), 'chest')
            bone(f'upper_arm.{side}', (sign*.175,0,ARM_Z), (sign*.515,.005,ARM_Z), f'clavicle.{side}')
            bone(f'forearm.{side}', (sign*.515,.005,ARM_Z), (sign*.780,0,ARM_Z), f'upper_arm.{side}')
            bone(f'hand.{side}', (sign*.780,0,ARM_Z), (sign*.884,-.001,ARM_Z-.002), f'forearm.{side}')
            for digit, mcp, spread, lengths, _ in FINGERS:
                joints = finger_joints(spread, mcp, lengths)
                parent = f'hand.{side}'
                for segment, suffix in enumerate(('', '_mid', '_tip')):
                    name = f'finger_{digit:02d}{suffix}.{side}'
                    bone(name, mirror(joints[segment], sign), mirror(joints[segment+1], sign), parent)
                    parent = name
            joints = thumb_joints()
            parent = f'hand.{side}'
            for segment, suffix in enumerate(('', '_mid', '_tip')):
                name = f'thumb{suffix}.{side}'
                bone(name, mirror(joints[segment], sign), mirror(joints[segment+1], sign), parent)
                parent = name
            hip, knee = (sign*.125,0,.91), (sign*.135,-.014,.52)
            ankle, ball = (sign*.135,0,.14), (sign*.135,-.122,.045)
            bone(f'thigh.{side}', hip, knee, 'hips')
            bone(f'shin.{side}', knee, ankle, f'thigh.{side}')
            bone(f'foot.{side}', ankle, ball, f'shin.{side}')
            bone(f'toes.{side}', ball, (sign*.135,-.18,.045), f'foot.{side}')
            eye_x = sign*self.EYE_X*self.spec.get('face_width',1)
            bone(f'eye.{side}', (eye_x,-.09,1.675), (eye_x,-.144,1.675), 'head', warp=True)
        bpy.ops.object.mode_set(mode='OBJECT')
        rig['Usage'] = ('Shared cast skeleton (34 core bones, T-pose) plus finger_0N_mid/_tip '
                        'and thumb_mid/_tip segments. Select the Mouth mesh for phoneme shape keys.')
        return rig

    # Realistic eye: smaller opening, lids over the iris, a wet corneal shell.
    EYE_X = .0505
    EYE_RADIUS = .0238
    UPPER_LID = .0071
    LOWER_LID = .0070
    IRIS = .0094

    def eyelid_point(self, cx: float, cz: float, sign: int, angle: float, size: float) -> Tuple[float, float]:
        u, w = math.cos(angle), math.sin(angle)
        if w > 0:
            height = (self.UPPER_LID + sign*.0002)*(1-.22*abs(u)**1.4)*(1-.10*u*sign)
        else:
            height = (self.LOWER_LID + sign*.0002)*(1-.30*abs(u)**1.6)*(1+.06*u*sign)
        x = cx + self.EYE_RADIUS*size*u
        z = cz + size*(w*height + sign*.0017*u) - .0007*max(0.0, -u*sign)**3
        return x, z

    def eye_surface(self, cx: float, cz: float, sign: int, x: float, z: float) -> float:
        horizontal, vertical = (x-cx)/self.EYE_RADIUS, (z-cz)/.0105
        dome = max(0, 1-horizontal**2-(vertical-sign*.12*horizontal)**2)
        return self.face_y(x, z) - .0019 - .0068*dome**.7

    def eye(self, side, sign, width, sclera, rim, iris):
        cx, cz = sign*self.EYE_X*width, 1.675
        angles = tuple(math.tau*i/64 for i in range(64))
        surface = lambda x, z: self.eye_surface(cx, cz, sign, x, z)

        # Sclera with a wet shell bulging over the iris (the cornea), one mesh so it blinks.
        verts, colors = [], []
        sizes = (1, .9, .76, .6, .45, .3, .15, .03)
        for size in sizes:
            for angle in angles:
                x, z = self.eyelid_point(cx, cz, sign, angle, size)
                verts.append((x, surface(x, z) + size**5*.0006, z))
                corner = max(0.0, -math.cos(angle)*sign)**6*max(0.0, (size-.55)/.45)
                lid_shadow = .55 + .45*(1 - max(0.0, math.sin(angle))*size**.6)
                shade = (.55 + .45*(1-size**2.5))*lid_shadow
                white = tuple(v*shade for v in (.56,.49,.45))
                colors.append(tuple(a*(1-corner)+b*corner for a, b in zip(white, (.42,.20,.18))))
        faces = []
        for r in range(len(sizes)-1):
            for i in range(64):
                n = (i+1) % 64
                faces.append((r*64+i, r*64+n, (r+1)*64+n, (r+1)*64+i))
        shell_start = len(verts)
        for size in sizes:
            for angle in angles:
                x, z = self.eyelid_point(cx, cz, sign, angle, size*1.02)
                distance = math.hypot(x-(cx+sign*.0006), (z-cz)/1.0)
                bulge = .0021*max(0.0, 1-(distance/(self.IRIS*1.18))**2)**.8
                verts.append((x, surface(x, z) - .00045 - bulge, z))
                colors.append((1, 1, 1))
        for r in range(len(sizes)-1):
            for i in range(64):
                n = (i+1) % 64
                a, b = shell_start+r*64, shell_start+(r+1)*64
                faces.append((a+i, a+n, b+n, b+i))
        eye = self.mesh(f'Eye.{side}', verts, faces, sclera, 'head')
        wet = self.wet_material()
        eye.data.materials.append(wet)
        for polygon in eye.data.polygons[(len(sizes)-1)*64:]:
            polygon.material_index = 1
        from face_surface import pigment_material, vertex_pigment
        if not sclera.get('pigmented'):
            pigment_material(sclera, 'Sclera pigment')
            sclera['pigmented'] = True
        vertex_pigment(eye, 'Sclera pigment', colors)

        # Lids: margin, a soft fold and a crease on the upper lid.
        lid_rings = []
        for size, depth, crease in ((1, .0011, 0), (1.06, .0024, 0), (1.17, .0021, .0004), (1.34, .0006, .0012),
                                    (1.56, -.0003, -.0007), (1.82, -.0007, 0)):
            ring = []
            for angle in angles:
                x, z = self.eyelid_point(cx, cz, sign, angle, size)
                upper = max(0.0, math.sin(angle))
                if size > 1.3:
                    z += upper*.0016*(size-1.3)
                y = self.face_y(x, z) - depth - .0011*upper - crease*upper**1.5
                ring.append((x, y, z))
            lid_rings.append(ring)
        lid = self.ring_mesh(f'Eyelids.{side}', lid_rings[::-1], self.m['skin'], 'head', cap=False)
        lid.data.materials.append(rim)
        for polygon in list(lid.data.polygons)[-len(angles):]:
            polygon.material_index = 1

        iris_rings, colors = [], []
        for radius, shade in ((self.IRIS*1.0, .22), (self.IRIS*.94, .55), (self.IRIS*.84, .85),
                              (self.IRIS*.68, .95), (self.IRIS*.52, 1.15), (self.IRIS*.43, 1.0),
                              (self.IRIS*.375, .55), (self.IRIS*.35, .06), (.0017, .045), (.00009, .045)):
            ring = []
            for angle in angles:
                x = cx + sign*.0006 + radius*math.cos(angle)
                z = cz + radius*math.sin(angle)
                ring.append((x, surface(x, z) - .0009 + .0003*(radius/self.IRIS)**2, z))
                streak = (.74 + .26*math.sin(23*angle + 160*radius)**2 + .22*math.sin(37*angle - 470*radius)**2)
                strength = shade*(streak if radius > self.IRIS*.37 else 1)
                colors.append(tuple(ch*strength for ch in self.spec['iris']))
            iris_rings.append(ring)
        pigment = self.ring_mesh(f'Iris.{side}', iris_rings, iris, f'eye.{side}', cap=False)
        vertex_pigment(pigment, 'Iris pigment', colors)

    def nostril(self, side, sign, nose, material):
        """Smaller, softer nostril shadows that read from below rather than as marks on the face."""
        rings = []
        for size in (1, .6, .08):
            ring = []
            for step in range(24):
                angle = math.tau*step/24
                u, w = math.cos(angle)*size, math.sin(angle)*size
                x = sign*(.0155*u*.42 + .0170)*nose
                z = 1.6032 + .0017*w + .0011*u
                ring.append((x, self.face_y(x, z) + .0006, z))
            rings.append(ring if sign == 1 else ring[::-1])
        self.ring_mesh(f'Nostril.{side}', rings, material, 'head', cap=False)

    def wet_material(self):
        name = f'{self.name} • Corneal wet shell'
        existing = bpy.data.materials.get(name)
        if existing:
            return existing
        material = bpy.data.materials.new(name)
        material.use_nodes = True
        tree = material.node_tree
        tree.nodes.clear()
        out = tree.nodes.new('ShaderNodeOutputMaterial')
        clear = tree.nodes.new('ShaderNodeBsdfTransparent')
        gloss = tree.nodes.new('ShaderNodeBsdfGlossy')
        gloss.inputs['Roughness'].default_value = .06
        fresnel = tree.nodes.new('ShaderNodeFresnel')
        fresnel.inputs['IOR'].default_value = 1.376
        mix = tree.nodes.new('ShaderNodeMixShader')
        tree.links.new(fresnel.outputs[0], mix.inputs[0])
        tree.links.new(clear.outputs[0], mix.inputs[1])
        tree.links.new(gloss.outputs[0], mix.inputs[2])
        tree.links.new(mix.outputs[0], out.inputs['Surface'])
        return material

    def mouth(self, lip, inner):
        """Fuller lips with a cupid's bow and a rounded vermilion; same eight-shape interface."""
        segments = 64
        angles = [math.tau*i/segments for i in range(segments)]
        middle = 1.566

        def outline(width, opening, roundness):
            points = []
            rings = ((width+.0046, opening+.0100, opening+.0122, 0),
                     (width+.0030, opening+.0085, opening+.0105, .0042),
                     (width+.0013, opening+.0060, opening+.0074, .0074),
                     (width+.0002, opening+.0025, opening+.0030, .0061),
                     (width*.985, opening, opening, .0021),
                     (.0015, .00065, .0012, .0010))
            for ring, (rx, up, down, depth) in enumerate(rings):
                for angle in angles:
                    u, w = math.cos(angle), math.sin(angle)
                    rz = up if w > 0 else down
                    x = rx*u
                    z = rz*w*(1 - (1-roundness)*abs(u)**1.2)
                    if ring < 3 and w > 0:
                        z = z*.9 - .0016*math.exp(-(u/.20)**2)*w + .0007*math.exp(-((abs(u)-.33)/.12)**2)*w
                    if ring < 4 and w < 0:
                        z *= 1 - .12*abs(u)**3
                    z += middle + .0011*u - .0016*u*u
                    corner = abs(u)**2
                    y = self.face_y(x, z) - depth*(1-.62*corner)
                    if ring == 0:
                        y += .00035
                    points.append((x, y, z))
            return points

        faces = []
        for ring in range(5):
            a, b = ring*segments, (ring+1)*segments
            faces.extend((a+i, a+(i+1) % segments, b+(i+1) % segments, b+i) for i in range(segments))
        faces.append(tuple(range(5*segments, 6*segments)))
        obj = self.mesh('Mouth', outline(.0315, .0010, .66), faces, lip, 'head')
        obj.data.materials.append(inner)
        for face in obj.data.polygons[segments*4:]:
            face.material_index = 1
        base = self.spec['skin']
        factors = ((.97,.90,.87), (.80,.55,.52), (.70,.43,.41), (.64,.37,.36), (.46,.25,.24), (.4,.2,.2))
        samples = []
        for ring, tint in enumerate(factors):
            for angle in angles:
                darker_upper = 1-.12*max(math.sin(angle), 0) if ring else 1
                samples.append(tuple(v*g*darker_upper for v, g in zip(base, tint)))
        from face_surface import vertex_pigment
        vertex_pigment(obj, 'Lip pigment', samples)
        obj.shape_key_add(name='Basis', from_mix=False)
        obj.data.shape_keys.use_relative = True
        for key, shape in {'Mouth_Ah': (.031,.022,.83), 'Mouth_O': (.018,.020,1),
                           'Mouth_Ee': (.044,.008,.7), 'Mouth_MBP': (.032,.0003,.66),
                           'Mouth_FV': (.036,.0036,.73)}.items():
            blend = obj.shape_key_add(name=key, from_mix=False)
            for vertex, coordinate in zip(blend.data, outline(*shape)):
                vertex.co = morph(Vector(coordinate))*self.scale
            blend.value = 0
        obj['Usage'] = 'Use one primary phoneme at a time. Basis is the relaxed mouth.'


# Her skull: longer front-to-back than the stylized cast, softer jaw, fuller cheeks.
FEMALE_PROFILE = (
    (1.497,-.036,.013,.030), (1.508,-.028,.044,.064), (1.530,-.021,.070,.086),
    (1.556,-.012,.088,.102), (1.598,-.004,.104,.112), (1.638,.003,.113,.118),
    (1.678,.010,.112,.124), (1.7325,.016,.109,.124), (1.7775,.019,.100,.115),
    (1.8125,.019,.075,.088), (1.834,.017,.034,.043), (1.840,.016,.006,.008),
)


def _g(x, z, cx, cz, w, h):
    return math.exp(-(((x-cx)/w)**2 + ((z-cz)/h)**2))


def female_relief(x: float, z: float, width: float, nose: float) -> float:
    side = abs(x)
    bridge = .024*_g(x, z, 0, 1.650, .015*nose, .040)
    tip = .028*_g(x, z, 0, 1.621, .020*nose, .0125)
    lobule = .005*_g(x, z, 0, 1.6145, .014*nose, .006)
    wing = .012*_g(side, z, .0215*nose, 1.6125, .0105*nose, .0095)
    nostril = .0042*_g(side, z, .0165*nose, 1.6052, .0068*nose, .0027)
    socket = .0088*_g(side, z, .050*width, 1.679, .030, .0135)
    inner_socket = .0040*_g(side, z, .027*width, 1.671, .010, .010)
    brow = .0035*_g(side, z, .050*width, 1.708, .034, .0085)
    cheekbone = .0080*_g(side, z, .071*width, 1.645, .026, .019)
    cheek = .0058*_g(side, z, .060*width, 1.607, .030, .024)
    fold_x = .031 + (1.615-z)*.32
    nasolabial = .0014*_g(side, z, fold_x, 1.588, .0045, .022)
    muzzle = .0062*_g(x, z, 0, 1.569, .040, .024)
    philtrum = .0022*_g(x, z, 0, 1.592, .0062, .011)
    chin = .0060*_g(x, z, 0, 1.522, .021, .014)
    sulcus = .0020*_g(x, z, 0, 1.545, .016, .0055)
    temple = .0030*_g(side, z, .100*width, 1.700, .014, .030)
    return (socket + inner_socket + nostril + philtrum + sulcus + temple + nasolabial
            - bridge - tip - lobule - wing - cheekbone - cheek - muzzle - chin - brow)


# ------------------------------------------------------------- small helpers

def add_uv(obj, uvs: Sequence[Tuple[float, float]], name: str = 'ClothUV') -> None:
    layer = obj.data.uv_layers.new(name=name)
    for loop in obj.data.loops:
        layer.data[loop.index].uv = uvs[loop.vertex_index]


def fix_uv_wrap(obj, span: float, name: str = 'ClothUV') -> None:
    """On a cyclic grid, the closing faces jump from u=span back to 0; unwrap them."""
    layer = obj.data.uv_layers[name]
    for polygon in obj.data.polygons:
        us = [layer.data[i].uv.x for i in polygon.loop_indices]
        if max(us) - min(us) > span/2:
            for i in polygon.loop_indices:
                if layer.data[i].uv.x < span/2:
                    layer.data[i].uv.x += span


def grid_faces(rows: int, columns: int, cyclic: bool = False) -> List[Tuple[int, int, int, int]]:
    faces = []
    span = columns if cyclic else columns-1
    for r in range(rows-1):
        for c in range(span):
            n = (c+1) % columns
            faces.append((r*columns+c, r*columns+n, (r+1)*columns+n, (r+1)*columns+c))
    return faces


def normalise(weights: Dict[str, float]) -> Dict[str, float]:
    kept = {k: v for k, v in weights.items() if v > .004}
    total = sum(kept.values())
    return {k: v/total for k, v in kept.items()}


def torso_weight(x: float, z: float) -> Dict[str, float]:
    """Skin weights for anything on the torso, in her final coordinates."""
    w: Dict[str, float] = {}
    hips = 1-smooth(1.10,1.20,z)
    spine = smooth(1.10,1.20,z)*(1-smooth(1.28,1.36,z))
    chest = smooth(1.28,1.36,z)
    side = 'L' if x > 0 else 'R'
    clavicle = .50*smooth(.07,.15,abs(x))*smooth(1.36,1.43,z)
    arm = .50*smooth(.12,.19,abs(x))*smooth(1.38,1.45,z)
    w['hips'] = hips
    w['spine'] = spine
    w['chest'] = chest*(1-clavicle-arm)
    w[f'clavicle.{side}'] = chest*clavicle
    w[f'upper_arm.{side}'] = chest*arm
    return normalise(w)


def material(c, label: str, rgb, rough: float = .8, metal: float = 0):
    return c.mat(label, rgb, rough, metal)


# ------------------------------------------------------------ torso surface

# z, half width, half depth, centre y, bust prominence (her final coordinates)
TORSO = (
    (.98,.180,.122,.006,0), (1.03,.166,.112,.002,0), (1.09,.150,.101,-.001,0),
    (1.15,.150,.102,-.003,0), (1.21,.158,.106,-.006,.010), (1.255,.166,.108,-.008,.027),
    (1.30,.171,.105,-.006,.022), (1.35,.176,.098,-.004,.008), (1.40,.180,.089,.000,0),
    (1.44,.177,.082,.004,0), (1.468,.148,.072,.006,0), (1.486,.106,.063,.004,0), (1.497,.074,.056,.002,0),
)


def torso_section(z: float) -> Tuple[float, float, float, float]:
    rows = TORSO
    if z <= rows[0][0]:
        return rows[0][1:]
    if z >= rows[-1][0]:
        return rows[-1][1:]
    i = next(i for i in range(len(rows)-1) if z <= rows[i+1][0])
    t = (z-rows[i][0])/(rows[i+1][0]-rows[i][0])
    t = t*t*(3-2*t)*.5 + t*.5
    return tuple(a*(1-t)+b*t for a, b in zip(rows[i][1:], rows[i+1][1:]))


def torso_point(angle: float, z: float, inflate: float = 0) -> Vector:
    """A point on the body at an angle (0 = side, -pi/2 = front) and height."""
    rx, ry, cy, bust = torso_section(z)
    x = (rx+inflate)*math.cos(angle)
    front = max(0.0, -math.sin(angle))
    lobes = math.exp(-((x-.066)/.048)**2) + math.exp(-((x+.066)/.048)**2)
    y = cy + (ry+inflate)*math.sin(angle) - bust*lobes*front**1.2
    return Vector((x, y, z))


def torso_front_y(x: float, z: float, inflate: float = 0) -> float:
    rx = torso_section(z)[0]+inflate
    angle = -math.acos(max(-1.0, min(1.0, x/rx)))
    return torso_point(angle, z, inflate).y


# ------------------------------------------------------------------- arms

ARM_RINGS = (  # x, half depth, half height, z offset (deltoid cap sits low, armpit hangs below)
    (.115,.060,.052,-.030), (.150,.058,.050,-.024), (.180,.056,.047,-.018), (.220,.051,.045,-.013),
    (.300,.045,.043,-.006), (.400,.041,.041,-.002), (.470,.038,.038,-.001), (.515,.036,.037,.000),
    (.560,.041,.039,-.001), (.620,.038,.0345,-.001), (.700,.031,.026,-.001), (.750,.0280,.0198,-.001),
    (.764,.0255,.0172,-.001),
)


def arm_weight(x: float, side: str) -> Dict[str, float]:
    upper, lower, hand = (f'{b}.{side}' for b in ('upper_arm','forearm','hand'))
    clav = f'clavicle.{side}'
    w = {'chest': .55*(1-smooth(.11,.17,x)), clav: .45*(1-smooth(.15,.23,x))}
    w[upper] = smooth(.11,.23,x)*(1-smooth(.47,.56,x))
    w[lower] = smooth(.47,.56,x)*(1-smooth(.755,.80,x))
    w[hand] = smooth(.755,.80,x)
    return normalise(w)


def arm_ring(x: float, ry: float, rz: float, dz: float, sign: int, count: int = 28) -> List[Point]:
    ring = []
    for j in range(count):
        a = math.tau*j/count
        ring.append((sign*x, sign*ry*math.cos(a), ARM_Z+dz+rz*math.sin(a)))
    return ring


def build_arm(c, side: str, sign: int, skin) -> None:
    rings = [arm_ring(x, ry, rz, dz, sign) for x, ry, rz, dz in ARM_RINGS]
    c.ring_mesh(f'Arm.{side}', rings, skin, [arm_weight(x, side) for x, *_ in ARM_RINGS], cap=False)


class Geometry:
    """Collects verts, faces and per-vertex weights to build one fused mesh."""

    def __init__(self):
        self.verts: List[Vector] = []
        self.faces: List[Tuple[int, ...]] = []
        self.weights: List[Dict[str, float]] = []

    def rings(self, rings: List[List[Vector]], weights: List[Dict[str, float]], close: bool = True) -> None:
        start = len(self.verts)
        count = len(rings[0])
        for ring, weight in zip(rings, weights):
            self.verts.extend(ring)
            self.weights.extend([weight]*count)
        for r in range(len(rings)-1):
            for j in range(count):
                n = (j+1) % count
                a = start+r*count
                self.faces.append((a+j, a+n, a+count+n, a+count+j))
        if close:
            self.faces.append(tuple(reversed(range(start, start+count))))
            last = start+(len(rings)-1)*count
            self.faces.append(tuple(range(last, last+count)))


def tube_rings(path: List[Vector], radii: List[Tuple[float, float]], up: Vector, count: int = 16) -> List[List[Vector]]:
    rings = []
    for i, point in enumerate(path):
        tangent = (path[min(i+1,len(path)-1)] - path[max(i-1,0)]).normalized()
        side = up.cross(tangent).normalized()
        top = tangent.cross(side).normalized()
        ry, rz = radii[i]
        ring = []
        for j in range(count):
            a = math.tau*j/count
            under = .9 if math.sin(a) < 0 else 1.0
            ring.append(point + side*ry*math.cos(a) + top*rz*under*math.sin(a))
        rings.append(ring)
    return rings


def sample_digit(joints: List[Vector], radius: float, inset: float, step: float = .0035):
    """Points along a finger with radii that swell at the knuckles and round off at the tip."""
    direction = (joints[1]-joints[0]).normalized()
    lengths = [(joints[i+1]-joints[i]).length for i in range(3)]
    total = sum(lengths)
    knuckles = (lengths[0], lengths[0]+lengths[1])
    tip_cap = radius*.92
    distances = []
    d = -inset
    while d < total - tip_cap:
        distances.append(d)
        d += step
    for k in range(1, 7):
        distances.append(total - tip_cap + tip_cap*(1-math.cos(k/7*math.pi/2)))
    distances.append(total - .0004)
    points, radii, params = [], [], []
    for d in distances:
        # follow the joint polyline
        remaining = max(0.0, d)
        segment = 0
        while segment < 2 and remaining > lengths[segment]:
            remaining -= lengths[segment]
            segment += 1
        base = joints[segment]
        seg_dir = (joints[segment+1]-joints[segment]).normalized()
        point = base + seg_dir*min(remaining, lengths[segment]) if d >= 0 else joints[0] + direction*d
        taper = 1 - .14*max(0.0, min(1.0, d/total))
        bulge = 1 + .055*math.exp(-((d-knuckles[0])/.006)**2) + .04*math.exp(-((d-knuckles[1])/.005)**2)
        r = radius*taper*bulge*(1.07 if d < 0 else 1)
        cap = d - (total-tip_cap)
        if cap > 0:
            r *= math.sqrt(max(0.0, 1-(cap/tip_cap)**2))*.97 + .03
        points.append(point)
        radii.append((r, r*.86))
        params.append(d)
    return points, radii, params, knuckles, total


def digit_weight(d: float, knuckles: Tuple[float, float], names: Tuple[str, str, str, str]) -> Dict[str, float]:
    hand, proximal, middle, tip = names
    w = {hand: 1-smooth(-.008, .004, d)}
    w[proximal] = smooth(-.008,.004,d)*(1-smooth(knuckles[0]-.003, knuckles[0]+.003, d))
    w[middle] = smooth(knuckles[0]-.003, knuckles[0]+.003, d)*(1-smooth(knuckles[1]-.0025, knuckles[1]+.0025, d))
    w[tip] = smooth(knuckles[1]-.0025, knuckles[1]+.0025, d)
    return normalise(w)


def palm_rings(sign: int, side: str) -> Tuple[List[List[Vector]], List[Dict[str, float]]]:
    sections = ((.752,.0300,.0205), (.772,.0305,.0205), (.790,.0335,.0202), (.810,.0390,.0199),
                (.832,.0430,.0193), (.854,.0452,.0182), (.872,.0458,.0166), (.885,.0450,.0148),
                (.894,.0420,.0118), (.899,.0360,.0080))
    rings, weights = [], []
    count = 32
    for x, ry, rz in sections:
        ring = []
        for j in range(count):
            a = math.tau*j/count
            c, s = math.cos(a), math.sin(a)
            # A superellipse: flat back of hand, rounder palm.
            ey = math.copysign(abs(c)**(2/2.7), c)
            ez = math.copysign(abs(s)**(2/2.7), s)
            depth = rz*(.86 if s > 0 else 1.06)
            y = ry*ey
            z = depth*ez
            if s < 0:   # thenar and hypothenar pads on the palm side
                z -= .0055*math.exp(-((x-.818)/.022)**2)*math.exp(-((y+.024)/.012)**2)
                z -= .0030*math.exp(-((x-.845)/.030)**2)*math.exp(-((y-.030)/.012)**2)
            ring.append(Vector((sign*x, sign*y, ARM_Z-.001+z)))
        rings.append(ring)
        weights.append(normalise({f'forearm.{side}': 1-smooth(.762,.792,x), f'hand.{side}': smooth(.762,.792,x)}))
    return rings, weights


def build_hand(c, side: str, sign: int, skin, nail_material) -> None:
    geometry = Geometry()
    rings, weights = palm_rings(sign, side)
    geometry.rings(rings, weights)
    nails = Geometry()
    up = Vector((0, 0, 1))
    for digit, mcp, spread, lengths, radius in FINGERS:
        joints = [Vector(mirror(p, sign)) for p in finger_joints(spread, mcp, lengths)]
        points, radii, params, knuckles, total = sample_digit(joints, radius, .013)
        names = (f'hand.{side}', f'finger_{digit:02d}.{side}', f'finger_{digit:02d}_mid.{side}',
                 f'finger_{digit:02d}_tip.{side}')
        geometry.rings(tube_rings(points, radii, up), [digit_weight(d, knuckles, names) for d in params])
        nail(nails, joints, radius, knuckles, total, names[3], up)
    joints = [Vector(mirror(p, sign)) for p in thumb_joints()]
    points, radii, params, knuckles, total = sample_digit(joints, .0112, .022)
    radii = [(ry*(1+.45*(1-smooth(-.02,.02,d))), rz*(1+.35*(1-smooth(-.02,.02,d))))
             for (ry, rz), d in zip(radii, params)]
    thumb_up = Vector((0, -.62*1, .78)).normalized()
    names = (f'hand.{side}', f'thumb.{side}', f'thumb_mid.{side}', f'thumb_tip.{side}')
    geometry.rings(tube_rings(points, radii, thumb_up), [digit_weight(d, knuckles, names) for d in params])
    nail(nails, joints, .0112, knuckles, total, names[3], thumb_up)

    fused = remesh_with_weights(c, f'Hand.{side}', geometry, skin, voxel=.00062)
    fused['Topology'] = 'Voxel-fused palm, fingers and thumb; weights interpolated from the digit rigs.'
    obj = c.mesh(f'Fingernails.{side}', [tuple(v) for v in nails.verts], nails.faces, nail_material, nails.weights)
    obj.data.materials[0] = nail_material


def nail(geometry: Geometry, joints: List[Vector], radius: float, knuckles, total: float,
         bone: str, up: Vector) -> None:
    direction = (joints[3]-joints[2]).normalized()
    side = up.cross(direction).normalized()
    top = direction.cross(side).normalized()
    length = (joints[3]-joints[2]).length
    start = joints[2] + direction*length*.22
    rows, columns = 7, 7
    base = len(geometry.verts)
    for r in range(rows):
        v = r/(rows-1)
        along = start + direction*(length*.50*v)
        width = radius*.66*(.86 + .14*math.sin(math.pi*min(1, v*1.1)))
        # follow the fingertip as it rounds off near the free edge
        drop = radius*.22*max(0.0, v-.6)**2
        for col in range(columns):
            u = col/(columns-1)*2-1
            curve = math.sqrt(max(0, 1-(u*.95)**2))
            height = radius*.86*(.93 + .07*curve) - .0012*u*u - drop + .00012
            geometry.verts.append(along + side*u*width + top*height)
            geometry.weights.append({bone: 1.0})
    geometry.faces.extend((base+f[0], base+f[1], base+f[2], base+f[3]) for f in grid_faces(rows, columns))


def remesh_with_weights(c, name: str, geometry: Geometry, skin, voxel: float):
    """Fuse overlapping parts into one watertight surface and carry the skin weights over."""
    scale = c.scale
    source = bpy.data.meshes.new(f'{c.name}_{name} source')
    source.from_pydata([v*scale for v in geometry.verts], [], geometry.faces)
    source.update()
    temp = bpy.data.objects.new(source.name, source)
    bpy.context.scene.collection.objects.link(temp)
    remesh = temp.modifiers.new('Fuse', 'REMESH')
    remesh.mode = 'VOXEL'
    remesh.voxel_size = voxel*scale
    remesh.adaptivity = 0
    soften = temp.modifiers.new('Soften', 'SMOOTH')
    soften.factor, soften.iterations = .5, 4
    decimate = temp.modifiers.new('Budget', 'DECIMATE')
    decimate.ratio = .30
    depsgraph = bpy.context.evaluated_depsgraph_get()
    fused = bpy.data.meshes.new_from_object(temp.evaluated_get(depsgraph))
    bpy.data.objects.remove(temp, do_unlink=True)
    bpy.data.meshes.remove(source)

    tree = KDTree(len(geometry.verts))
    for index, vertex in enumerate(geometry.verts):
        tree.insert(vertex*scale, index)
    tree.balance()
    verts = [tuple(v.co/scale) for v in fused.vertices]
    faces = [tuple(p.vertices) for p in fused.polygons]
    weights = []
    for vertex in fused.vertices:
        blend: Dict[str, float] = {}
        for _, index, distance in tree.find_n(vertex.co, 6):
            share = 1/(distance*distance + 1e-9)
            for bone, value in geometry.weights[index].items():
                blend[bone] = blend.get(bone, 0) + value*share
        weights.append(normalise(blend))
    bpy.data.meshes.remove(fused)
    return c.mesh(name, verts, faces, skin, weights)


# ------------------------------------------------------------ body assembly

def body(c) -> None:
    c.morphing = True
    c.body()
    c.morphing = False
    for obj in [p for p in c.parts if any(k in p.name for k in ('_Arm.', '_Palm.', '_Finger_', '_Thumb.'))]:
        c.parts.remove(obj)
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.meshes.remove(mesh)
    skin = c.m['skin']
    nails = material(c, 'Fingernail', (.40,.25,.20), .30)
    for side, sign in (('L',1), ('R',-1)):
        build_arm(c, side, sign, skin)
        build_hand(c, side, sign, skin, nails)
    # Skin of the upper chest and shoulders under the kurti neckline.
    rows, columns = 14, 48
    verts, weights = [], []
    for r in range(rows):
        z = 1.36 + (1.497-1.36)*r/(rows-1)
        for k in range(columns):
            a = math.tau*k/columns
            p = torso_point(a, z, -.004)
            verts.append(tuple(p))
            weights.append(torso_weight(p.x, z))
    faces = grid_faces(rows, columns, cyclic=True)
    c.mesh('Upper chest', verts, faces, skin, weights)


def face(c) -> None:
    """Her volumetric head (sculpted_face) in place of the shared revolved face."""
    neck = bpy.data.objects.get(f'{c.name}_Neck')
    if neck is not None:            # the sculpted head carries its own neck
        c.parts.remove(neck)
        mesh = neck.data
        bpy.data.objects.remove(neck, do_unlink=True)
        bpy.data.meshes.remove(mesh)
    c.sculpted = sf.SculptedFace(c, sf.NEIGHBOUR)
    head = c.sculpted.head_mesh(c.m['skin'])
    c.sculpted.build_eyes(head)
    sf.skin_shading(c)
    c.sculpted.paint_head(head)
    ears(c)
    c.sculpted.brow_strips(material(c, 'Brow skin shadow', tuple(v*.70 for v in c.spec['skin']), .7))
    c.sculpted.mouth_lining(material(c, 'Mouth interior', (.045, .010, .009), .55))
    skin_tint(c)


def ears(c) -> None:
    """The shared ear shape, set against the sculpted skull just behind the jaw."""
    inner = material(c, 'Inner ear', tuple(a*f for a, f in zip(c.spec['skin'], (.82, .67, .63))), .72)
    c.morphing = True
    for side, sign in (('L', 1), ('R', -1)):
        c.ear(side, sign, c.spec['face_width'], c.m['skin'], inner)
    c.morphing = False
    for side, sign in (('L', 1), ('R', -1)):
        parts = [bpy.data.objects[f'{c.name}_Ear.{side}'], bpy.data.objects[f'{c.name}_Ear inner fold.{side}']]
        co = [v.co for v in parts[0].data.vertices]
        low = min(sign*p.x for p in co)
        centre = sum(co, Vector())/len(co)
        face = c.sculpted
        target = Vector((0, .006, 1.4255))              # canonical, on the sculpted skull
        hit, _, _, _ = face.tree.ray_cast(Vector((sign*.2, target.y, target.z)), Vector((-sign, 0, 0)), .3)
        surface = (abs(hit.x) if hit is not None else .066)*face.size
        target = face.final(target)
        shift = Vector((sign*(surface - .0035*face.size - low), target.y - centre.y, target.z - centre.z))
        for obj in parts:
            for v in obj.data.vertices:
                v.co += shift


def thin_brows(c) -> None:
    """Keep the brow mesh (it carries the brow shape keys) as a faint shadow under the fiber brows."""
    shadow = material(c, 'Brow skin shadow', tuple(v*.62 for v in c.spec['skin']), .7)
    for side in ('L','R'):
        brow = bpy.data.objects[f'{c.name}_Brow.{side}']
        mesh = brow.data
        for r in range(len(mesh.vertices)//10):
            ring = mesh.vertices[r*10:(r+1)*10]
            centre = sum((v.co for v in ring), Vector())/10
            for v in ring:
                v.co = centre + (v.co-centre)*Vector((.5, .25, .42))
        mesh.materials[0] = shadow


def skin_tint(c) -> None:
    """Regional colour: warmer cheeks, nose and ears, shadowed sockets, darker knuckles and soles."""
    regions = (  # centre (her final coords), radii, rgb offset
        ((.050, -.085, EYE_Z-.045), (.030, .03, .025), (.07, -.015, -.02)),
        ((-.050, -.085, EYE_Z-.045), (.030, .03, .025), (.07, -.015, -.02)),
        ((0, -.11, EYE_Z-.062), (.016, .03, .02), (.06, -.01, -.015)),
        ((.040, -.07, EYE_Z+.004), (.022, .03, .012), (-.16, -.17, -.12)),
        ((-.040, -.07, EYE_Z+.004), (.022, .03, .012), (-.16, -.17, -.12)),
        ((0, -.08, EYE_Z-.142), (.035, .03, .02), (-.04, -.05, -.03)),
    )
    for part in c.parts:
        if part.name.endswith(('_Ear.L', '_Ear.R', '_Hand.L', '_Hand.R', '_Foot.L', '_Foot.R')):
            colors = []
            for vertex in part.data.vertices:
                p = vertex.co/c.scale
                tint = Vector((0, 0, 0))
                for centre, radius, rgb in regions:
                    d = sum(((a-b)/r)**2 for a, b, r in zip(p, centre, radius))
                    tint += Vector(rgb)*math.exp(-d)
                if '_Ear.' in part.name:
                    tint += Vector((.06, -.01, -.01))
                if '_Hand.' in part.name:
                    up = max(0.0, (p.z - ARM_Z)/.02)
                    tint += Vector((-.05, -.06, -.05))*min(1, up)
                    tint += Vector((.10, .07, .05))*min(1, max(0.0, (ARM_Z-.004-p.z)/.012))
                if '_Foot.' in part.name:
                    tint += Vector((.05, .04, .03))*min(1, max(0.0, (.03-p.z)/.02))
                colors.append((*tint, 1))
            attribute = part.data.color_attributes.new('Skin tint', 'FLOAT_COLOR', 'POINT')
            attribute.data.foreach_set('color', [v for col in colors for v in col])
    tree = c.m['skin'].node_tree
    if any(n.label == 'Regional skin tint' for n in tree.nodes):
        return
    shader = tree.nodes.get('Principled BSDF')
    source = shader.inputs['Base Color'].links[0].from_socket
    tint = _node(tree, 'ShaderNodeAttribute', 200, 520, 'Regional skin tint')
    tint.attribute_name = 'Skin tint'
    add = _node(tree, 'ShaderNodeVectorMath', 420, 480)
    add.operation = 'MULTIPLY_ADD'
    tree.links.new(source, add.inputs[0])
    tree.links.new(tint.outputs['Color'], add.inputs[1])
    tree.links.new(source, add.inputs[2])
    tree.links.new(add.outputs[0], shader.inputs['Base Color'])


# ------------------------------------------------------------------- hair

def head_tree(c) -> BVHTree:
    head = next(p.data for p in c.parts if p.name == f'{c.name}_Head')
    return BVHTree.FromPolygons([v.co/c.scale for v in head.vertices], [tuple(f.vertices) for f in head.polygons])


HEAD_CENTRE = morph(Vector((0, .008, 1.66)))


def cast(tree: BVHTree, direction: Vector) -> Tuple[Vector, Vector]:
    direction = direction.normalized()
    origin = HEAD_CENTRE + direction*.35
    point, normal, _, _ = tree.ray_cast(origin, -direction, .4)
    if point is None:
        return HEAD_CENTRE + direction*.09, direction
    if normal.dot(direction) < 0:
        normal = -normal
    return point, normal


def direction(azimuth: float, elevation: float) -> Vector:
    """azimuth 0 = back of the head (+y), +pi/2 = her left; elevation from horizontal."""
    ce = math.cos(elevation)
    return Vector((math.sin(azimuth)*ce, math.cos(azimuth)*ce, math.sin(elevation)))


def hairline(azimuth: float) -> float:
    a = abs(azimuth)
    if a < 1.2:
        return math.radians(-48 + 40*smooth(.3, 1.2, a))
    if a < 1.85:
        return math.radians(-8 + 20*smooth(1.2, 1.85, a))
    return math.radians(14 + 30*smooth(1.85, 2.80, a))


BUN = Vector((0, .11, EYE_Z-.055))   # replaced by place_bun() from the built skull
BUN_RADIUS = .036


def strand_path(tree: BVHTree, azimuth: float, elevation: float, rand: random.Random, layer: float) -> List[Vector]:
    side = 1 if azimuth >= 0 else -1
    frontal = smooth(1.3, 2.7, abs(azimuth))
    waypoint = direction(side*(1.45 - .15*frontal), math.radians(-2 + 6*frontal))
    root_dir = direction(azimuth, elevation)
    target = (BUN + Vector((side*.018*rand.random(), -.012, .012*rand.uniform(-1, 1))) - HEAD_CENTRE).normalized()
    path = []
    steps = 12
    for i in range(steps):
        t = i/(steps-1)
        # quadratic bezier on the sphere through the side of the head
        d = root_dir*(1-t)**2 + waypoint*(2*(1-t)*t*frontal) + target*(t*t + 2*(1-t)*t*(1-frontal))
        point, normal = cast(tree, d)
        lift = .0012 + layer*(.6 + .4*math.sin(math.pi*t)) + .003*t*t
        path.append(point + normal*lift)
    # the last few points lead into the bun
    entry = BUN + (path[-1]-BUN).normalized()*BUN_RADIUS*.7
    path[-1] = path[-1].lerp(entry, .7)
    return path


def place_bun(tree: BVHTree) -> None:
    point, normal = cast(tree, direction(0, math.radians(-24)))
    BUN.xyz = point + normal*(BUN_RADIUS*.62) + Vector((0, 0, -.004))


def hair(c) -> None:
    tree = head_tree(c)
    place_bun(tree)
    rand = random.Random(4417)
    root, tip = (.017,.011,.008), (.075,.045,.028)
    fibers = FiberGroup(c, root, tip)
    under = material(c, 'Hair shadow beneath fibers', (.020,.013,.010), .9)

    # Scalp undercoat
    columns, rows = 72, 22
    verts = []
    for r in range(rows):
        for k in range(columns):
            az = -math.pi + math.tau*k/columns
            inset = hairline(az) + math.radians(3.5)
            el = inset + (math.radians(89)-inset)*(1 - r/(rows-1))**1.4
            point, normal = cast(tree, direction(az, el))
            verts.append(tuple(point + normal*.0011))
    c.mesh('Scalp undercoat', verts, grid_faces(rows, columns, cyclic=True), under, 'head')

    for _ in range(5200):
        az = rand.uniform(-math.pi, math.pi)
        if abs(abs(az)-math.pi) < .035:      # centre parting
            az = math.copysign(math.pi-.035-rand.random()*.03, az)
        edge = hairline(az)
        el = edge + (math.radians(88)-edge)*rand.random()**.75
        layer = .0035*rand.random()**1.5 + .0016*(el-edge)
        path = strand_path(tree, az, el, rand, layer)
        shade = rand.choice((0,1,1,2,2,3,3,4,5))
        fibers.add(path, rand.uniform(.00013,.00026), shade, min(6, shade+1))
    # Low bun, wound from strands
    for i in range(900):
        phase = rand.uniform(0, math.tau)
        tilt = rand.uniform(-1, 1)
        radius = BUN_RADIUS*rand.uniform(.55, 1.0)
        path = []
        for k in range(14):
            t = k/13
            a = phase + t*math.tau*rand.uniform(.8, 1.2)
            v = tilt*.9 + .25*math.sin(a*2+phase)
            local = Vector((math.cos(a)*math.sqrt(max(0, 1-v*v*.6)), .35*v, math.sin(a)*math.sqrt(max(0, 1-v*v*.6))))
            path.append(BUN + Vector((local.x*radius, local.y*radius + .01, local.z*radius*.85)))
        fibers.add(path, rand.uniform(.00018,.00030), rand.randrange(0,5), 4)
    # Fine flyaways at the hairline
    for _ in range(160):
        az = rand.uniform(-math.pi, math.pi)
        el = hairline(az) + math.radians(rand.uniform(0, 6))
        point, normal = cast(tree, direction(az, el))
        drift = Vector((rand.uniform(-.008,.008), rand.uniform(-.006,.006), rand.uniform(-.004,.006)))
        path = [point + normal*.0008 + (normal*.004 + drift)*t*t for t in (0, .35, .7, 1)]
        fibers.add(path, rand.uniform(.00008,.00014), rand.randrange(3,7), 6)
    fibers.make_mesh('Scalp groom fibers')

    brow_fibers = FiberGroup(c, root, (.06,.038,.025))
    for sign, side in ((1,'L'), (-1,'R')):
        for _ in range(270):
            u = rand.random()**.9
            x, z = c.sculpted.brow_curve(u, sign)
            band = .0021*math.sin(math.pi*(.1 + .85*u))**.7
            z += rand.uniform(-1, 1)*band
            root_point, normal = c.sculpted.on_skin(x, z, .0002)
            # hairs at the head of the brow stand up, the rest sweep out toward the tail
            lateral = Vector((sign, 0, 0))
            rise = .9*(1 - smooth(.05, .3, u)) + .18
            sweep = (lateral*(1 - rise*.6) + Vector((0, 0, 1))*rise).normalized()
            length = rand.uniform(.0045, .0070)*(1 - .3*u)
            points = []
            for k in range(4):
                t = k/3
                p = root_point + sweep*length*t + normal*(.0007*math.sin(math.pi*t*.8))
                p.z -= .0006*t*t*u
                points.append(p*c.sculpted.to_scene)
            brow_fibers.add(points, rand.uniform(.000085, .000130), rand.randrange(0,3), 3)
        merge_fibers(c, brow_fibers, f'Brow.{side}')
    lashes(c, rand)


def merge_fibers(c, group: FiberGroup, target_label: str) -> None:
    """Append fibers into an existing head mesh so its facial shape keys move them too."""
    target = bpy.data.objects[f'{c.name}_{target_label}']
    mesh = target.data
    old_verts = [v.co.copy() for v in mesh.vertices]
    old_faces = [tuple(p.vertices) for p in mesh.polygons]
    old_index = [p.material_index for p in mesh.polygons]
    first = len(mesh.materials)
    for m in group.materials:
        mesh.materials.append(m)
    offset = len(old_verts)
    verts = old_verts + [v*c.scale for v in group.verts]
    faces = old_faces + [tuple(i+offset for i in f) for f in group.faces]
    new = bpy.data.meshes.new(mesh.name)
    new.from_pydata(verts, [], faces)
    new.update()
    for m in mesh.materials:
        new.materials.append(m)
    for polygon, index in zip(new.polygons, old_index + [first+i for i in group.indices]):
        polygon.material_index = index
        polygon.use_smooth = True
    target.data = new
    bpy.data.meshes.remove(mesh)
    target.vertex_groups.clear()
    target.vertex_groups.new(name='head').add(list(range(len(verts))), 1, 'REPLACE')
    for collection in (group.verts, group.faces, group.indices, group.uv):
        collection.clear()


def lashes(c, rand: random.Random) -> None:
    for sign, side in ((1,'L'), (-1,'R')):
        group = FiberGroup(c, (.006,.004,.003), (.016,.011,.008))
        face = c.sculpted
        centre = face.eye_centre(sign)
        for lid, count, base_length in (('upper', 96, .0090), ('lower', 40, .0045)):
            roots = face.margin_curve(sign, lid, .32, (sf.UPPER_LID_T if lid == 'upper' else sf.LOWER_LID_T)*.86, count)
            for k, root in enumerate(roots):
                u = k/(count-1)
                root = Vector(root)
                radial = (root - centre).normalized()
                outer = smooth(.35, 1.0, u)
                up = Vector((0, 0, 1 if lid == 'upper' else -1))
                length = base_length*(.45 + .55*math.sin(math.pi*(.15 + .8*u))**.6)*(1 + .2*outer)*rand.uniform(.85, 1.1)
                start = (Vector((0, -1, 0))*.80 + radial*.30 - up*.05).normalized()
                points = []
                for s_ in range(5):
                    t = s_/4
                    p = root + start*length*(.85*t) + up*length*(.45*t*t) + Vector((sign*outer*.30*length*t, 0, 0))
                    points.append(p*face.to_scene)
                group.add(points, rand.uniform(.000085, .000115), 0, 1)
        merge_fibers(c, group, f'Eyelids.{side}')


# ---------------------------------------------------------------- costume

def textile_material(c, label: str, rgb, fine: bool = False, pattern: Callable | None = None):
    m = material(c, label, rgb, .88)
    finish_fabric(m, fine)
    if pattern is not None:
        pattern(m)
    return m


def _node(tree, kind: str, x: float, y: float, label: str = ''):
    n = tree.nodes.new(kind)
    n.location = (x, y)
    n.label = label
    return n


def _dye_socket(m):
    group = next(n for n in m.node_tree.nodes if n.type == 'GROUP')
    return group.inputs['Dye']


def _rest_coordinates(tree):
    attribute = _node(tree, 'ShaderNodeAttribute', -1900, 400, 'Rest position (m)')
    attribute.attribute_name = 'TextileRest'
    return attribute.outputs['Vector']


def _mix(tree, a, b, factor, x: float, y: float, label: str = ''):
    mix = _node(tree, 'ShaderNodeMix', x, y, label)
    mix.data_type = 'RGBA'
    for socket, value in ((mix.inputs[0], factor), (mix.inputs[6], a), (mix.inputs[7], b)):
        if isinstance(value, (float, int)):
            socket.default_value = value
        elif isinstance(value, tuple):
            socket.default_value = (*value[:3], 1)
        else:
            tree.links.new(value, socket)
    return mix.outputs[2]


def _math(tree, op: str, a, b, x: float, y: float):
    n = _node(tree, 'ShaderNodeMath', x, y)
    n.operation = op
    for socket, value in zip(n.inputs, (a, b)):
        if isinstance(value, (float, int)):
            socket.default_value = value
        else:
            tree.links.new(value, socket)
    return n.outputs[0]


def _dots(tree, coordinates, scale: float, radius: float, x: float, y: float, jitter: float = .25):
    voronoi = _node(tree, 'ShaderNodeTexVoronoi', x, y, 'Printed / tied dots')
    voronoi.inputs['Scale'].default_value = scale
    voronoi.inputs['Randomness'].default_value = jitter
    tree.links.new(coordinates, voronoi.inputs['Vector'])
    edge = _math(tree, 'LESS_THAN', voronoi.outputs['Distance'], radius, x+200, y)
    return edge


def ghagra_pattern(m):
    """Dabu block print laid out on the flat cloth (metres in ClothUV), so it gathers at the waist."""
    tree = m.node_tree
    uv = _node(tree, 'ShaderNodeUVMap', -1900, 300)
    uv.uv_map = 'ClothUV'
    split = _node(tree, 'ShaderNodeSeparateXYZ', -1700, 150)
    tree.links.new(uv.outputs['UV'], split.inputs[0])
    indigo, mustard, rust, cream = (.010,.016,.036), (.43,.29,.09), (.20,.07,.03), (.50,.43,.30)

    def rosettes(scale: float, offset: float, x: float, y: float):
        shift = _node(tree, 'ShaderNodeVectorMath', x-200, y)
        shift.operation = 'ADD'
        shift.inputs[1].default_value = (offset/scale, offset/scale, 0)
        tree.links.new(uv.outputs['UV'], shift.inputs[0])
        cells = _node(tree, 'ShaderNodeTexVoronoi', x, y, 'Block-print rosette grid')
        cells.voronoi_dimensions = '2D'
        cells.inputs['Scale'].default_value = scale
        cells.inputs['Randomness'].default_value = 0
        tree.links.new(shift.outputs[0], cells.inputs['Vector'])
        return cells.outputs['Distance']

    a = rosettes(34, 0, -1450, 650)
    b = rosettes(34, .5, -1450, 450)
    dot = _math(tree, 'LESS_THAN', a, .10, -1200, 700)
    ring = _math(tree, 'MULTIPLY', _math(tree, 'GREATER_THAN', a, .20, -1200, 620),
                 _math(tree, 'LESS_THAN', a, .27, -1200, 560), -1050, 600)
    small = _math(tree, 'LESS_THAN', b, .085, -1200, 450)
    # hand-printed irregularity: blotchy registration and ink density
    ink = _node(tree, 'ShaderNodeTexNoise', -1450, 250, 'Uneven ink')
    ink.inputs['Scale'].default_value = 60
    ink.inputs['Detail'].default_value = 4
    tree.links.new(uv.outputs['UV'], ink.inputs['Vector'])
    density = _math(tree, 'MULTIPLY_ADD', ink.outputs['Fac'], .7, -1200, 250)
    density.node.inputs[2].default_value = .55
    field = _mix(tree, indigo, mustard, _math(tree, 'MULTIPLY', dot, density, -1000, 700), -800, 700, 'Mustard dots')
    field = _mix(tree, field, rust, _math(tree, 'MULTIPLY', ring, density, -1000, 600), -650, 650, 'Rust rings')
    field = _mix(tree, field, cream, _math(tree, 'MULTIPLY', small, density, -1000, 450), -500, 600, 'Cream seed dots')

    v = split.outputs['Y']           # metres up from the hem in cloth space
    band = _math(tree, 'LESS_THAN', v, .105, -1200, 100)
    stripes = _node(tree, 'ShaderNodeTexWave', -1450, 0, 'Border stripes')
    stripes.wave_type = 'BANDS'
    stripes.bands_direction = 'Y'
    stripes.inputs['Scale'].default_value = 3.2
    tree.links.new(uv.outputs['UV'], stripes.inputs['Vector'])
    stripe = _math(tree, 'GREATER_THAN', stripes.outputs['Fac'], .70, -1200, 0)
    border = _mix(tree, rust, mustard, stripe, -900, 100, 'Hem border')
    border = _mix(tree, border, indigo, _math(tree, 'MULTIPLY', dot, .8, -1050, -50), -750, 50)
    color = _mix(tree, field, border, band, -400, 450, 'Field and border')

    silt = _node(tree, 'ShaderNodeTexNoise', -1450, -250, 'Silt stain')
    silt.inputs['Scale'].default_value = 7
    silt.inputs['Detail'].default_value = 8
    silt.inputs['Roughness'].default_value = .62
    tree.links.new(uv.outputs['UV'], silt.inputs['Vector'])
    line = _math(tree, 'MULTIPLY_ADD', silt.outputs['Fac'], .16, -1200, -250)
    line.node.inputs[2].default_value = .02
    stain = _node(tree, 'ShaderNodeMapRange', -1000, -250, 'Tide line of dried silt')
    tree.links.new(_math(tree, 'SUBTRACT', line, v, -1150, -320), stain.inputs['Value'])
    stain.inputs['From Min'].default_value = -.03
    stain.inputs['From Max'].default_value = .02
    stain.inputs['To Max'].default_value = .55
    color = _mix(tree, color, (.17,.13,.085), stain.outputs['Result'], -250, 350, 'Dried silt')
    tree.links.new(color, _dye_socket(m))
    group = next(n for n in tree.nodes if n.type == 'GROUP')
    group.inputs['Yarn contrast'].default_value = .18
    tree.nodes.get('Principled BSDF').inputs['Sheen Weight'].default_value = .18


def odhni_pattern(m):
    tree = m.node_tree
    uv = _node(tree, 'ShaderNodeUVMap', -1900, 0)
    uv.uv_map = 'ClothUV'
    split = _node(tree, 'ShaderNodeSeparateXYZ', -1700, 0)
    tree.links.new(uv.outputs['UV'], split.inputs[0])
    rest = _rest_coordinates(tree)
    turmeric, indigo, cream = (.46,.27,.055), (.024,.036,.075), (.62,.52,.33)
    dots = _dots(tree, rest, 95, .13, -1500, 500, .55)
    rings = _dots(tree, rest, 95, .21, -1500, 300, .55)
    ring = _math(tree, 'SUBTRACT', rings, dots, -1250, 400)
    field = _mix(tree, turmeric, cream, dots, -1050, 500, 'Bandhani dots')
    field = _mix(tree, field, (.33,.16,.04), ring, -900, 450)
    u = split.outputs['X']
    edge = _math(tree, 'MINIMUM', u, _math(tree, 'SUBTRACT', 1.0, u, -1500, 0), -1300, 0)
    edge = _math(tree, 'MINIMUM', edge, split.outputs['Y'], -1200, 60)
    border = _math(tree, 'LESS_THAN', edge, .085, -1100, 0)
    fine = _math(tree, 'LESS_THAN', _math(tree, 'ABSOLUTE', _math(tree, 'SUBTRACT', edge, .1, -1300, -150), 0, -1150, -150), .006, -1000, -150)
    color = _mix(tree, field, indigo, border, -800, 300, 'Indigo border')
    color = _mix(tree, color, cream, fine, -650, 250, 'Border pinstripe')
    tree.links.new(color, _dye_socket(m))


def kurti(c, cloth, trim) -> None:
    rows, columns = 46, 64
    verts, weights = [], []
    z_low = 1.02
    for r in range(rows):
        v = r/(rows-1)
        for k in range(columns):
            a = math.tau*k/columns - math.pi/2
            front = max(0.0, -math.sin(a))
            back = max(0.0, math.sin(a))
            top = 1.497 - .040*front**2.2 - .012*back**2
            z = z_low + (top-z_low)*v
            wrinkle = .0018*math.sin(9*a + 23*z) * smooth(1.04, 1.20, z)*(1-smooth(1.22, 1.30, z))
            p = torso_point(a, z, .0045 + wrinkle)
            verts.append(tuple(p))
            weights.append(torso_weight(p.x, z))
    obj = c.mesh('Kurti body', verts, grid_faces(rows, columns, cyclic=True), cloth, weights)
    neckline = [Vector(verts[(rows-1)*columns+k]) for k in range(columns)]
    c.tube('Kurti neckline binding', [tuple(p + Vector((0, 0, -.002))) for p in neckline], .0028, trim,
           [torso_weight(p.x, p.z) for p in neckline], cyclic=True)
    for side, sign in (('L',1), ('R',-1)):
        sections = [(x, ry, rz, dz) for x, ry, rz, dz in ARM_RINGS if x <= .47] + [(.488,.0375,.0375,0)]
        rings = []
        for i, (x, ry, rz, dz) in enumerate(sections):
            fold = .0045 if x > .15 else .003
            ring = []
            for j in range(32):
                a = math.tau*j/32
                ripple = 1 + .05*math.cos(6*a + 30*x)*smooth(.2, .45, x)
                ring.append((sign*x, sign*(ry+fold)*ripple*math.cos(a), ARM_Z+dz+(rz+fold)*ripple*math.sin(a)))
            rings.append(ring)
        c.ring_mesh(f'Kurti sleeve {side}', rings, cloth, [arm_weight(s[0], side) for s in sections], cap=False)
        c.tube(f'Kurti sleeve hem {side}', rings[-1], .0026, trim, [arm_weight(.488, side)]*len(rings[-1]), cyclic=True)


GHAGRA = ((1.088,.158,.118), (1.045,.176,.130), (.95,.210,.158), (.80,.242,.200),
          (.60,.282,.246), (.40,.322,.286), (.20,.356,.320), (.105,.368,.333))


def ghagra_profile(z: float) -> Tuple[float, float]:
    rows = GHAGRA
    for i in range(len(rows)-1):
        if rows[i+1][0] <= z <= rows[i][0]:
            t = (z-rows[i][0])/(rows[i+1][0]-rows[i][0])
            return tuple(a*(1-t)+b*t for a, b in zip(rows[i][1:], rows[i+1][1:]))
    return rows[0][1:] if z > rows[0][0] else rows[-1][1:]


def ghagra(c, cloth, band, cord) -> None:
    SPAN = 90/34      # whole number of print repeats around the skirt
    rand = random.Random(91)
    rows, columns = 70, 176
    phases = [rand.uniform(0, math.tau) for _ in range(12)]
    verts, weights, uvs = [], [], []
    top, hem = GHAGRA[0][0], GHAGRA[-1][0]
    for r in range(rows):
        v = r/(rows-1)
        z0 = top + (hem-top)*v
        rx, ry = ghagra_profile(z0)
        depth = smooth(1.06, .15, z0)
        for k in range(columns):
            a = math.tau*k/columns + math.pi/2
            gathers = .0045*(.5+.5*math.cos(44*a))*(1-smooth(1.08, .85, z0))
            big = .040*depth*(.5+.5*math.sin(13*a + phases[k*12//columns]*.35 + 1.8*math.sin(3*a)))**1.6
            mid = .012*depth*(.5+.5*math.sin(27*a + 2.1*math.sin(5*a+1)))
            radius_bias = 1 + .018*math.sin(2*a+.7)*depth
            ex = rx*radius_bias + gathers + big + mid
            ey = ry*radius_bias + gathers + big + mid
            z = z0 + (.012*math.sin(5*a+1.3) + .006*math.sin(11*a)) * smooth(.4, .1, z0)
            x = ex*math.cos(a)
            y = ey*math.sin(a) + .010*depth
            verts.append((x, y, z))
            side = 'L' if x > 0 else 'R'
            legs = .42*smooth(.98, .45, z0)*abs(math.cos(a))**.8
            w = {'hips': 1-legs, f'thigh.{side}': legs}
            weights.append(normalise(w))
            uvs.append((k/columns*SPAN, (1-v)*.84))
    obj = c.mesh('Ghagra gathered skirt', verts, grid_faces(rows, columns, cyclic=True), cloth, weights)
    add_uv(obj, uvs)
    fix_uv_wrap(obj, SPAN)
    hem_ring = [verts[(rows-1)*columns+k] for k in range(columns)]
    c.tube('Ghagra hem binding', hem_ring, .0032, band, weights[(rows-1)*columns:], cyclic=True)
    waist = []
    for k in range(64):
        a = math.tau*k/64
        waist.append((.163*math.cos(a), .122*math.sin(a)+.001, 1.076))
    c.tube('Ghagra waistband', waist, .0085, band, 'hips', cyclic=True)
    # nada drawstring tie and tassels at her front left
    knot = Vector((.058, -.121, 1.071))
    c.ovoid('Nada knot', tuple(knot), (.010,.007,.008), cord, 'hips')
    for i, (dx, length) in enumerate(((-.006,.13), (.007,.155))):
        path = [knot + Vector((dx*t*3, -.004*math.sin(math.pi*t), -length*t)) for t in (0,.25,.5,.75,1)]
        c.tube(f'Nada cord {i+1}', [tuple(p) for p in path], .0022, cord, 'hips')
        end = path[-1]
        c.ovoid(f'Nada tassel {i+1}', tuple(end+Vector((0,0,-.012))), (.0075,.0075,.019), cord, 'hips')


# ------------------------------------------------------------------ odhni

def hood_radius(tree: BVHTree, phi: float, z: float) -> float:
    """Outermost head, hair or bun distance along a horizontal ray, from the head axis."""
    axis = Vector((0, HEAD_CENTRE.y, z))
    d = Vector((math.sin(phi), math.cos(phi), 0))
    point, _, _, _ = tree.ray_cast(axis + d*.35, -d, .4)
    r = (point - axis).length + .012 if point is not None else .02
    # bun sphere
    offset = BUN - axis
    along = offset.dot(d)
    perpendicular = (offset - d*along).length
    reach = BUN_RADIUS*1.08
    if perpendicular < reach:
        r = max(r, along + math.sqrt(reach*reach - perpendicular*perpendicular) + .006)
    return r


def odhni(c, cloth, edge) -> None:
    tree = head_tree(c)
    top = HEAD_TOP + .006
    z_jaw = vertical(1.585)
    z_shoulder = 1.468
    rows, columns = 64, 72
    rand = random.Random(7)

    def y_edge(z: float) -> float:
        return -.050 + .018*smooth(z_jaw, top-.02, z)

    def span(z: float) -> Tuple[float, float]:
        if z >= z_jaw:
            radius = max(.02, hood_radius(tree, math.pi/2, z))
            limit = math.acos(max(-1, min(1, (y_edge(z) - HEAD_CENTRE.y)/radius)))
            return -limit, limit
        t = smooth(z_jaw, z_shoulder, z)
        lo, hi = span(z_jaw)
        return lo - (2.30 - abs(lo))*t**1.5, hi

    hood_z = []
    top_row = HEAD_TOP - .010
    for r in range(rows):
        v = r/(rows-1)
        hood_z.append(top_row - (top_row - z_shoulder)*v**1.08)
    jaw_index = max(i for i, z in enumerate(hood_z) if z >= z_jaw)
    verts, weights, uvs = [], [], []
    for r, z in enumerate(hood_z):
        lo, hi = span(z)
        for k in range(columns):
            phi = lo + (hi-lo)*k/(columns-1)
            u = k/(columns-1)
            outward = Vector((math.sin(phi), math.cos(phi), 0))
            if r <= jaw_index:
                rad = hood_radius(tree, phi, z)
                p = Vector((outward.x*rad, HEAD_CENTRE.y + outward.y*rad, z))
            else:
                # a curtain falling straight from the head, resting on the shoulders
                rad = hood_radius(tree, phi, z_jaw) + .004*smooth(z_jaw, z_shoulder, z)
                p = Vector((outward.x*rad, HEAD_CENTRE.y + outward.y*rad, z))
                if z < 1.50:
                    angle = math.atan2(p.y, p.x)
                    body = torso_point(angle, z, .016)
                    reach = Vector((body.x, body.y, 0)).length
                    if Vector((p.x, p.y, 0)).length < reach:
                        p.x, p.y = body.x, body.y
            fold = .004*math.sin(9*phi + 3*z)*smooth(top-.02, z_jaw, z)
            p += outward*fold
            verts.append(tuple(p))
            weights.append(normalise({'head': smooth(z_shoulder+.04, z_jaw-.02, z),
                                      'neck': (1-smooth(z_shoulder+.04, z_jaw-.02, z))*.6,
                                      'chest': (1-smooth(z_shoulder+.04, z_jaw-.02, z))*.4}))
            uvs.append((u, 1 - r/(rows-1)*.45))
    faces = grid_faces(rows, columns)
    crown = len(verts)
    verts.append((0, HEAD_CENTRE.y + .012, HEAD_TOP + .013))
    weights.append({'head': 1.0})
    uvs.append((.5, 1.0))
    faces.extend((crown, k+1, k) for k in range(columns-1))
    # back panel hanging from the hood's bottom row behind the shoulders
    bottom = (rows-1)*columns
    lo, hi = span(z_shoulder)
    back_columns = [k for k in range(columns) if abs(lo + (hi-lo)*k/(columns-1)) < 1.32]
    back_rows = 26
    hem = 1.05
    previous = [bottom+k for k in back_columns]
    back_start = len(verts)
    for r in range(1, back_rows):
        v = r/(back_rows-1)
        z = z_shoulder - (z_shoulder-hem)*v
        row = []
        for idx, k in enumerate(back_columns):
            phi = lo + (hi-lo)*k/(columns-1)
            phi *= 1 - .22*v
            angle = math.atan2(math.cos(phi), math.sin(phi))
            fold = .010*v*(.5+.5*math.sin(15*phi + 1.3))**1.5 + .004*v*math.sin(31*phi)
            p = torso_point(angle, z, .020 + .022*v + fold)
            p.z += -.012*v*(1-math.cos(phi))      # hem dips at the sides
            row.append(len(verts))
            verts.append(tuple(p))
            weights.append(torso_weight(p.x, max(z, 1.25)))
            uvs.append((k/(columns-1), .55 - .55*v))
        for i in range(len(row)-1):
            faces.append((previous[i], previous[i+1], row[i+1], row[i]))
        previous = row
    hood = c.mesh('Odhni over head and back', verts, faces, cloth, weights)
    add_uv(hood, uvs)
    pins = hood.vertex_groups.new(name='Pin')
    for r in range(rows):
        for k in range(columns):
            index = r*columns+k
            weight = smooth(z_jaw-.012, z_jaw+.02, hood_z[r])
            if weight > 0:
                pins.add([index], weight, 'REPLACE')
    pins.add([crown], 1.0, 'REPLACE')
    panel = front_panel(c, cloth)
    relax_cloth(c, (hood, panel))

    def hood_weight(p: Vector) -> Dict[str, float]:
        head = smooth(z_shoulder+.03, z_jaw-.01, p.z)
        body = torso_weight(p.x, min(p.z, 1.47))
        w = {'head': head*.8, 'neck': head*.2}
        for bone, value in body.items():
            w[bone] = w.get(bone, 0) + value*(1-head)
        return normalise(w)

    reweight(hood, hood_weight)
    reweight(panel, lambda p: torso_weight(p.x, p.z))
    relaxed = [v.co/c.scale for v in hood.data.vertices]
    face_edge = [relaxed[r*columns] for r in range(rows)][::-1] + [relaxed[r*columns+columns-1] for r in range(rows)]
    face_edge = [p for p in face_edge[::2]]
    c.tube('Odhni face edge', [tuple(p + (p - Vector((0, HEAD_CENTRE.y, p.z))).normalized()*.0008) for p in face_edge],
           .0021, edge, [hood_weight(p) for p in face_edge])
    hem = [relaxed[i] for i in range(len(relaxed)-len(back_columns), len(relaxed))]
    c.tube('Odhni back hem', [tuple(p) for p in hem], .0018, edge, [hood_weight(p) for p in hem])


def reweight(obj, weight: Callable[[Vector], Dict[str, float]]) -> None:
    obj.vertex_groups.clear()
    groups: Dict[str, object] = {}
    character_scale = obj.get('character_scale', 1.0)
    for vertex in obj.data.vertices:
        for bone, value in weight(vertex.co/character_scale).items():
            group = groups.get(bone)
            if group is None:
                group = groups[bone] = obj.vertex_groups.new(name=bone)
            group.add([vertex.index], value, 'REPLACE')


def relax_cloth(c, cloths, frames: int = 28) -> None:
    """Let the procedural drape settle under gravity against the body, then keep the result as rest shape."""
    scene = c.scene
    bpy.context.window.scene = scene
    scene.frame_start, scene.frame_end = 1, frames
    colliders = [p for p in c.parts if any(k in p.name for k in (
        '_Head', '_Ear.', 'Scalp undercoat', '_Neck', 'Upper chest', 'Kurti body', 'Kurti sleeve L',
        'Kurti sleeve R', 'Ghagra gathered', 'Ghagra waistband'))]
    bpy.ops.mesh.primitive_uv_sphere_add(radius=BUN_RADIUS*1.08*c.scale, location=BUN*c.scale, segments=24, ring_count=12)
    bun = bpy.context.object
    bun.name = 'Bun collision proxy'
    if bun.name not in scene.collection.objects:
        scene.collection.objects.link(bun)
    added = []
    for obj in colliders + [bun]:
        modifier = obj.modifiers.new('Drape collision', 'COLLISION')
        settings = obj.collision
        settings.thickness_outer = .006 if 'Scalp' in obj.name else .0025
        settings.cloth_friction = 8
        added.append((obj, modifier))
    for obj in cloths:
        obj['character_scale'] = c.scale
        modifier = obj.modifiers.new('Drape settle', 'CLOTH')
        cloth = modifier.settings
        cloth.quality = 8
        cloth.mass = .12
        cloth.air_damping = 5
        cloth.tension_stiffness = cloth.compression_stiffness = 14
        cloth.shear_stiffness = 6
        cloth.bending_stiffness = 1.0
        cloth.vertex_group_mass = 'Pin'
        cloth.pin_stiffness = 2
        collision = modifier.collision_settings
        collision.distance_min = .0022
        collision.collision_quality = 4
        collision.use_self_collision = True
        collision.self_distance_min = .0018
        modifier.point_cache.frame_start, modifier.point_cache.frame_end = 1, frames
    for frame in range(1, frames+1):
        scene.frame_set(frame)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in cloths:
        evaluated = obj.evaluated_get(depsgraph)
        settled = [v.co.copy() for v in evaluated.to_mesh().vertices]
        evaluated.to_mesh_clear()
        obj.modifiers.remove(obj.modifiers['Drape settle'])
        for vertex, point in zip(obj.data.vertices, settled):
            vertex.co = point
        if 'Pin' in obj.vertex_groups:
            obj.vertex_groups.remove(obj.vertex_groups['Pin'])
    for obj, modifier in added:
        obj.modifiers.remove(modifier)
    bpy.data.objects.remove(bun, do_unlink=True)
    scene.frame_set(1)


def front_panel(c, cloth) -> None:
    """The end that comes forward over her right shoulder and tucks into the waistband at her left."""
    rows, columns = 44, 22
    start, end = Vector((-.112, 0, 1.446)), Vector((.078, 0, 1.074))
    along = (end-start)
    length = along.length
    along.normalize()
    across = Vector((-along.z, 0, along.x))
    if across.z < 0:
        across = -across
    width = .235
    verts, weights, uvs = [], [], []
    for r in range(rows):
        s = r/(rows-1)
        gather = .62 + .38*math.sin(math.pi*min(1, s*1.2))
        for k in range(columns):
            t = k/(columns-1) - .5
            q = start + along*length*s + across*width*t*gather
            q.z = min(q.z, 1.462)
            x, z = q.x, q.z
            fold = .0065*(.5+.5*math.sin(math.tau*3.2*t + 2.2*s))**1.3 + .002*math.sin(math.tau*7*t)
            inflate = .013 + fold - .006*smooth(.86, 1, s)
            y = torso_front_y(x, max(z, 1.0), inflate)
            if z > 1.44:     # roll over the shoulder towards the back
                y += (z-1.44)*.9
            verts.append((x, y, z))
            weights.append(torso_weight(x, z))
            uvs.append((k/(columns-1), s))
    obj = c.mesh('Odhni end tucked at waist', verts, grid_faces(rows, columns), cloth, weights)
    add_uv(obj, uvs)
    pins = obj.vertex_groups.new(name='Pin')
    for r in range(rows):
        s = r/(rows-1)
        weight = max(smooth(.84, .95, s), .9*(1-smooth(.04, .16, s)))
        if weight > 0:
            pins.add(list(range(r*columns, (r+1)*columns)), weight, 'REPLACE')
    return obj


# --------------------------------------------------------------- jewellery

def torus(c, name: str, centre: Vector, axis: Vector, radii: Tuple[float, float], tube: float,
          material, bone: str, segments: int = 48, sides: int = 10):
    """A ring around an axis with an elliptical path; a stable frame, so no seam."""
    axis = axis.normalized()
    a = Vector((0, 1, 0)) if abs(axis.y) < .9 else Vector((0, 0, 1))
    u = (a - axis*a.dot(axis)).normalized()
    v = axis.cross(u)
    verts, faces = [], []
    for i in range(segments):
        t = math.tau*i/segments
        point = centre + u*radii[0]*math.cos(t) + v*radii[1]*math.sin(t)
        outward = (u*radii[1]*math.cos(t) + v*radii[0]*math.sin(t)).normalized()
        for j in range(sides):
            p = math.tau*j/sides
            verts.append(tuple(point + (outward*math.cos(p) + axis*math.sin(p))*tube))
    for i in range(segments):
        for j in range(sides):
            n, m = (i+1) % segments, (j+1) % sides
            faces.append((i*sides+j, i*sides+m, n*sides+m, n*sides+j))
    return c.mesh(name, verts, faces, material, bone)


def jewellery(c) -> None:
    silver = material(c, 'Worn silver', (.62,.60,.57), .32, 1)
    gold = material(c, 'Low-karat gold', (.66,.43,.17), .28, 1)
    glass_green = material(c, 'Green glass bangle', (.05,.20,.08), .08)
    glass_amber = material(c, 'Amber lac bangle', (.36,.17,.035), .28)
    for m, transmission in ((glass_green, .55), (glass_amber, .0)):
        bsdf = m.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Transmission Weight'].default_value = transmission
        bsdf.inputs['Coat Weight'].default_value = .6
    thread = material(c, 'Black cotton thread', (.012,.011,.010), .85)
    for side, sign in (('L',1), ('R',-1)):
        for i, x in enumerate((.728, .7365, .745, .7535, .762)):
            mat = glass_amber if i in (0, 4) else glass_green
            torus(c, f'Bangle {i+1} {side}', Vector((sign*x, 0, ARM_Z-.004)), Vector((1, 0, 0)),
                  (.0345, .0285), .0024 if i in (0, 4) else .0019, mat, f'forearm.{side}')
        ankle = [(sign*.135 + .051*math.cos(math.tau*j/48), .049*math.sin(math.tau*j/48) - .004, .118 + .004*math.sin(math.tau*j/48))
                 for j in range(48)]
        c.tube(f'Silver anklet {side}', ankle, .0042, silver, f'shin.{side}', cyclic=True)
        for b in range(9):
            a = math.tau*b/9 + .2
            c.ovoid(f'Anklet bell {side} {b+1}', (sign*.135 + .055*math.cos(a), .053*math.sin(a) - .004, .106),
                    (.0042,.0042,.0050), silver, f'shin.{side}')
        ear = bpy.data.objects[f'{c.name}_Ear.{side}']
        low = min((v.co for v in ear.data.vertices), key=lambda p: p.z)
        lobe = (low + Vector((-sign*.0012, -.0010, .0042)))/c.scale
        c.tube(f'Ear hoop {side}', [tuple(lobe + Vector((sign*.0015, .006*math.cos(math.tau*j/20) - .003, -.006 + .006*math.sin(math.tau*j/20))))
               for j in range(20)], .0009, gold, 'head', cyclic=True)
        c.ovoid(f'Ear drop {side}', tuple(lobe + Vector((sign*.0015, -.003, -.0135))), (.0028,.0028,.0042), gold, 'head')
    face = c.sculpted
    ala = Vector(face.nose((.0106, -.0856, 1.3980)))   # canonical
    start = ala + Vector((.030, -.018, .002))
    hit, normal, _, _ = face.tree.ray_cast(start, (ala - start).normalized(), .06)
    stud = (hit + normal*.0006) if hit is not None else ala + Vector((.006, -.003, 0))
    c.ovoid('Nose stud', tuple(stud*face.to_scene), (.0019/c.scale, .0011/c.scale, .0019/c.scale), gold, 'head')
    cord = [torso_point(math.tau*k/40, 1.478 - .055*max(0, -math.sin(math.tau*k/40))**1.6, .002) for k in range(40)]
    c.tube('Amulet cord', [tuple(p) for p in cord], .0011, thread, [torso_weight(p.x, p.z) for p in cord], cyclic=True)
    low = min(cord, key=lambda p: p.z)
    c.ovoid('Silver amulet', tuple(low + Vector((0, -.004, -.012))), (.0075,.0032,.011), silver, 'chest')


# ------------------------------------------------------------------- build

def dress(c) -> None:
    ochre_trim = textile_material(c, 'Ochre kurti binding', (.40,.26,.09))
    kurti_cloth = textile_material(c, 'Deep leaf-green kurti cotton', (.060,.105,.052))
    ghagra_cloth = textile_material(c, 'Indigo dabu-print ghagra', (.02,.03,.06), pattern=ghagra_pattern)
    border = textile_material(c, 'Madder-brown ghagra hem band', (.15,.055,.03))
    cord = textile_material(c, 'Twisted cotton nada cord', (.33,.24,.12))
    odhni_cloth = textile_material(c, 'Turmeric bandhani odhni', (.46,.27,.055), pattern=odhni_pattern)
    odhni_edge = textile_material(c, 'Indigo odhni edge', (.024,.036,.075))
    kurti(c, kurti_cloth, ochre_trim)
    ghagra(c, ghagra_cloth, border, cord)
    hair(c)
    odhni(c, odhni_cloth, odhni_edge)
    jewellery(c)
    # Cloth parts carry their rest coordinates for the weave shader.
    for part in c.parts:
        if any(n.type == 'GROUP' and n.node_tree and n.node_tree.name.startswith('Textile')
               for m in part.data.materials if m and m.node_tree for n in m.node_tree.nodes):
            store_rest_positions(part.data)


def fix_blinks(c) -> None:
    """Blinks for the sculpted lids, and her own teeth and tongue in place of the shared placeholders."""
    c.sculpted.eyelid_blinks()
    c.sculpted.head_blinks(bpy.data.objects[f'{c.name}_Head'])
    for label in ('Upper teeth', 'Tongue'):
        obj = bpy.data.objects.get(f'{c.name}_{label}')
        if obj is not None:
            c.parts.remove(obj)
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.meshes.remove(mesh)
    c.sculpted.teeth_and_tongue()
    c.sculpted.speech_shapes(bpy.data.objects[f'{c.name}_Head'])


def build():
    import character as shared
    saved = shared.HEAD_PROFILE, shared.face_relief
    shared.HEAD_PROFILE, shared.face_relief = FEMALE_PROFILE, female_relief
    try:
        c = NeighbourCharacter(SPEC)
        body(c)
        face(c)
        dress(c)
        c.morphing = True
        facial_controls.add_facial_controls(c)
        c.morphing = False
        fix_blinks(c)
        c.validate()
    finally:
        shared.HEAD_PROFILE, shared.face_relief = saved
    c.rig['Character'] = 'हलवाई की पड़ोसन — witness; frees her cow by cutting its tether.'
    c.rig['Stature_m'] = round(HEAD_TOP*c.scale, 3)
    return c
