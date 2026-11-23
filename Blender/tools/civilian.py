"""Reusable adult townsperson base for witnesses and crowd members.

`Civilian` subclasses `Character` without changing it, so the existing cast
builds exactly as before. It keeps every bone name of the shared 34-bone
skeleton (clips stay interchangeable) and adds:

* two extra joints per finger and one per thumb, for readable points and grips;
* a skin torso and limb girth / belly controls for heavier or slighter bodies;
* a sculpted, parametric face (brow ridge, hooded lids, cheek fat, nasolabial
  folds, jowls, chin and double chin) driven by `SPEC['face']`;
* realistic eye proportions, wet sclera, cornea highlights and a lash line;
* a per-vertex skin tint layer (flush, stubble shadow, scalp sheen).

Witness modules supply SPEC values and their own wardrobe and groom.
"""

from __future__ import annotations

from contextlib import contextmanager
import math
from typing import Callable, Iterator, Sequence

import bpy
from mathutils import Vector

from character import Character
from face_surface import lip_surface, pigment_material, vertex_pigment


Point = tuple[float, float, float]
Weights = str | dict[str, float]
TintFunction = Callable[[float, float, float], tuple[float, float, float, float]]

TINT_ATTRIBUTE = 'Skin tint'
SHEEN_ATTRIBUTE = 'Skin sheen'

# (z, centre_y, half width, half depth) of the skull at each height, before
# `face_width`. Fuller lower face than the hero cast; same landmarks.
CIVILIAN_PROFILE: tuple[tuple[float, float, float, float], ...] = (
    (1.486, -.036, .018, .036), (1.497, -.030, .058, .072), (1.517, -.022, .088, .094),
    (1.545, -.015, .105, .106), (1.585, -.012, .116, .110), (1.630, -.010, .124, .111),
    (1.675, -.008, .120, .106), (1.722, -.003, .116, .103), (1.760, .003, .107, .095),
    (1.789, .006, .081, .073), (1.807, .007, .040, .040), (1.814, .007, .008, .008),
)

FACE_DEFAULTS: dict[str, float] = dict(
    eye_x=.047, eye_radius=.0235, upper_lid=.0071, lower_lid=.0061, iris=.79,
    bridge=.029, nose_tip=.034, nose_wing=.016, nose_drop=0, socket=.0078,
    brow_ridge=.0055, hood=.0022, eye_bag=.0016, temple=.004, cheek=.0060,
    cheek_fat=.0040, nasolabial=.0016, muzzle=.0053, mentolabial=.0026,
    chin=.0070, jowl=.0030, marionette=.0008, forehead=.0030, wrinkles=.00035,
    ear_size=1.0, ear_out=0, double_chin=0, tip_width=1.0, lid_crease=.00045,
    lip_full=1.0, lower_lip=1.0, mouth_width=.033,
)

# Each finger: (y at the knuckle, length, radius); x of the knuckle per digit.
FINGERS: tuple[tuple[float, float, float], ...] = (
    (-.029, .074, .0099), (-.0095, .082, .0103), (.0105, .077, .0097), (.0295, .062, .0087),
)
KNUCKLE_X: tuple[float, ...] = (.789, .793, .790, .782)
PHALANX: tuple[float, float, float] = (.45, .30, .25)
SEGMENTS: tuple[str, str, str] = ('', '_mid', '_tip')
WRIST_X = .700


def gaussian(x: float, z: float, cx: float, cz: float, wx: float, wz: float) -> float:
    return math.exp(-(((x - cx) / wx) ** 2 + ((z - cz) / wz) ** 2))


def crease(x: float, z: float, start: tuple[float, float], end: tuple[float, float],
           width: float) -> float:
    """1 on the line segment between two face points, falling off sideways and at the ends."""
    ax, az = start
    bx, bz = end
    dx, dz = bx - ax, bz - az
    length_sq = dx * dx + dz * dz
    t = max(0., min(1., ((x - ax) * dx + (z - az) * dz) / length_sq))
    px, pz = ax + t * dx, az + t * dz
    across = math.hypot(x - px, z - pz)
    ends = math.sin(math.pi * t) ** .5
    return math.exp(-(across / width) ** 2) * ends


def profile(table: Sequence[tuple[float, float, float, float]], z: float) -> tuple[float, float, float]:
    """Cubic Hermite interpolation of a skull profile table at height z."""
    if z <= table[0][0]:
        return table[0][1:]
    if z >= table[-1][0]:
        return table[-1][1:]
    index = next(i for i in range(len(table) - 1) if z <= table[i + 1][0])
    before, lower, upper, after = (table[i] for i in
                                   (max(index - 1, 0), index, index + 1, min(index + 2, len(table) - 1)))
    gap = upper[0] - lower[0]
    t = (z - lower[0]) / gap
    weights = (2 * t ** 3 - 3 * t * t + 1, t ** 3 - 2 * t * t + t, -2 * t ** 3 + 3 * t * t, t ** 3 - t * t)
    return tuple(weights[0] * a + weights[1] * gap * (b - prev) / (upper[0] - before[0]) +
                 weights[2] * b + weights[3] * gap * (nxt - a) / (after[0] - lower[0])
                 for prev, a, b, nxt in zip(before[1:], lower[1:], upper[1:], after[1:]))


def smoothstep(edge0: float, edge1: float, value: float) -> float:
    t = max(0., min(1., (value - edge0) / (edge1 - edge0)))
    return t * t * (3 - 2 * t)


class Civilian(Character):
    """An adult townsperson on the shared skeleton, with finger joints and a sculpted face."""

    def __init__(self, spec: dict) -> None:
        self.face_params: dict[str, float] = {**FACE_DEFAULTS, **spec.get('face', {})}
        self.head_table = spec.get('head_profile', CIVILIAN_PROFILE)
        # The cast skeleton puts the shoulder joints wide and high (stylised square shoulders).
        # Civilians move the whole arm chain in and down for a natural shoulder slope.
        self.shoulder_inset: float = spec.get('shoulder_inset', .028)
        self.shoulder_drop: float = spec.get('shoulder_drop', .022)
        self._arm_shift: tuple[float, float] | None = None
        super().__init__(spec)
        self.rig['Civilian_base'] = ('Shared townsperson skeleton: the 34 cast bones plus '
                                     '_mid/_tip finger joints and thumb_tip.')

    # ------------------------------------------------------------------ rig
    def make_rig(self):
        rig = super().make_rig()
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode='EDIT')
        bones = rig.data.edit_bones
        s = self.scale
        p = self.face_params if hasattr(self, 'face_params') else FACE_DEFAULTS
        for side, sign in (('L', 1), ('R', -1)):
            hand = bones[f'hand.{side}']
            hand.head = Vector((sign * WRIST_X, 0, 1.375)) * s
            hand.tail = Vector((sign * KNUCKLE_X[1], -.004, 1.373)) * s
            for digit, ((y, length, _), knuckle) in enumerate(zip(FINGERS, KNUCKLE_X), 1):
                start = Vector((sign * knuckle, y, 1.371))
                spread = (digit - 2.3) * .045
                direction = Vector((sign * math.cos(spread), math.sin(spread), -.02)).normalized()
                parent = None
                for segment, share in zip(SEGMENTS, PHALANX):
                    end = start + direction * length * share
                    name = f'finger_{digit:02d}{segment}.{side}'
                    bone = bones.get(name) or bones.new(name)
                    bone.head, bone.tail = start * s, end * s
                    bone.use_deform = True
                    bone.parent = parent or hand
                    bone.use_connect = parent is not None
                    parent, start = bone, end
            thumb = bones[f'thumb.{side}']
            thumb.head = Vector((sign * .713, -.021, 1.366)) * s
            thumb.tail = Vector((sign * .748, -.055, 1.352)) * s
            tip = bones.new(f'thumb_tip.{side}')
            tip.head = thumb.tail
            tip.tail = Vector((sign * .772, -.079, 1.346)) * s
            tip.parent = thumb
            tip.use_connect = True
            eye = bones[f'eye.{side}']
            eye_x = sign * p['eye_x']
            eye.head = Vector((eye_x, -.094, 1.675)) * s
            eye.tail = Vector((eye_x, -.148, 1.675)) * s
        for side, sign in (('L', 1), ('R', -1)):
            shift = Vector((-sign * self.shoulder_inset, 0, -self.shoulder_drop)) * s
            bones[f'clavicle.{side}'].tail += shift
            for bone in bones:
                if bone.name.endswith(f'.{side}') and bone.name.startswith(
                        ('upper_arm', 'forearm', 'hand', 'finger', 'thumb')):
                    bone.head += shift
                    bone.tail += shift
        bpy.ops.object.mode_set(mode='OBJECT')
        return rig

    @contextmanager
    def arm_space(self, sign: int) -> Iterator[None]:
        """Build arm, hand and sleeve geometry in cast coordinates; it lands on the civilian shoulder."""
        self._arm_shift = (-sign * self.shoulder_inset, -self.shoulder_drop)
        try:
            yield
        finally:
            self._arm_shift = None

    def mesh(self, name, verts, faces, material, bone, smooth=True):
        if self._arm_shift is not None:
            dx, dz = self._arm_shift
            verts = [(x + dx, y, z + dz) for x, y, z in verts]
        return super().mesh(name, verts, faces, material, bone, smooth)

    # ------------------------------------------------------------------ body
    def body_loft(self, name: str, rings: Sequence[tuple[float, float, float, float, float]],
                  material, weights: Sequence[Weights], segments: int = 40, cap: bool = True):
        """Rings of (z, half width, front depth, back depth, centre y); bellies push only the front."""
        coordinates = []
        for z, rx, front, back, cy in rings:
            ring = []
            for i in range(segments):
                angle = math.tau * i / segments
                c, s = math.cos(angle), math.sin(angle)
                depth = back if s > 0 else front
                ring.append((rx * c, cy + depth * s, z))
            coordinates.append(ring)
        return self.ring_mesh(name, coordinates, material, list(weights), cap)

    def body(self) -> None:
        skin = self.m['skin']
        build = self.spec.get('build', 1.0)
        belly = self.spec.get('belly', 0.0)
        neck = self.spec.get('neck', 1.0)
        self.loft('Neck', [(1.353, 0, 0, .072 * neck, .062 * neck), (1.402, 0, -.004, .061 * neck, .057 * neck),
                           (1.46, 0, -.009, .058 * neck, .056 * neck), (1.522, 0, -.012, .066 * neck, .062 * neck)],
                  skin, ['chest', {'chest': .26, 'neck': .74}, 'neck', {'neck': .45, 'head': .55}])
        self.body_loft('Torso', [
            (.905, .158, .105, .108, .004),
            (.975, .163 + .012 * belly, .118 + .040 * belly, .112, .002),
            (1.055, .168 + .020 * belly, .124 + .062 * belly, .113, 0),
            (1.135, .171 + .016 * belly, .121 + .052 * belly, .111, 0),
            (1.215, .178 + .006 * belly, .114 + .022 * belly, .108, 0),
            (1.295, .176, .108, .104, .002),
            (1.355, .160, .094, .094, .004),
            (1.395, .110, .074, .078, .002),
            (1.425, .072 * neck, .060 * neck, .060 * neck, -.004),
        ], skin, ['hips', 'hips', {'hips': .5, 'spine': .5}, 'spine', {'spine': .4, 'chest': .6},
                  'chest', 'chest', 'chest', {'chest': .55, 'neck': .45}])
        for side, sign in (('L', 1), ('R', -1)):
            upper, lower, hand = (f'{bone}.{side}' for bone in ('upper_arm', 'forearm', 'hand'))
            form = [(.183, .053), (.239, .063), (.312, .062), (.397, .050), (.46, .044), (.49, .045),
                    (.545, .049), (.61, .040), (.668, .030), (.705, .027)]
            def top(x: float, s: float) -> float:
                return 1 - .30 * max(0., s) * smoothstep(.26, .17, x)
            rings = [[(sign * x, sign * r * build * math.cos(math.tau * i / 24),
                       1.375 + r * build * .93 * math.sin(math.tau * i / 24) * top(x, math.sin(math.tau * i / 24)))
                      for i in range(24)] for x, r in form]
            with self.arm_space(sign):
                self.ring_mesh(f'Arm.{side}', rings, skin,
                               [{'chest': .85, upper: .15}, {'chest': .45, upper: .55}, upper, upper,
                                {upper: .72, lower: .28}, {upper: .26, lower: .74}, lower, lower,
                                {lower: .7, hand: .3}, {lower: .35, hand: .65}])
                self.hand(side, sign, skin)
            thigh, shin, foot = (f'{bone}.{side}' for bone in ('thigh', 'shin', 'foot'))
            g = build
            self.loft(f'Leg.{side}', [(.071, sign * .135, -.010, .041, .038), (.128, sign * .135, 0, .042 * g, .042 * g),
                      (.185, sign * .135, 0, .041 * g, .045 * g), (.323, sign * .134, .011, .053 * g, .058 * g),
                      (.445, sign * .135, -.008, .052 * g, .054 * g), (.52, sign * .135, -.014, .058 * g, .055 * g),
                      (.599, sign * .131, -.002, .064 * g, .065 * g), (.754, sign * .125, .003, .079 * g, .081 * g),
                      (.898, sign * .109, 0, .087 * g, .092 * g)], skin,
                      [foot, foot, shin, shin, shin, {shin: .52, thigh: .48}, thigh, thigh, thigh])
            self.ovoid(f'Foot.{side}', (sign * .135, -.058, .044), (.058, .111, .041), skin, foot)
            self.ovoid(f'Instep.{side}', (sign * .137, -.013, .063), (.045, .065, .041), skin, foot, (-.38, 0, 0))
            for digit in range(5):
                x = sign * (.092 + digit * .021)
                self.ovoid(f'Toe_{digit}.{side}', (x, -.158 + digit * .008, .026),
                           (.0145 - digit * .0009, .032 - digit * .003, .019 - digit * .0018), skin, f'toes.{side}')
                self.ovoid(f'Toenail_{digit}.{side}', (x, -.176 + digit * .009, .040 - digit * .0016),
                           (.009 - digit * .0009, .012 - digit * .0012, .0022), self.nail, f'toes.{side}')

    @property
    def nail(self):
        existing = bpy.data.materials.get(f'{self.name} • Nail')
        if existing:
            return existing
        base = self.spec['skin']
        material = self.mat('Nail', tuple(min(1, v * f) for v, f in zip(base, (1.32, 1.18, 1.12))), .34)
        material.node_tree.nodes.get('Principled BSDF').inputs['Coat Weight'].default_value = .35
        return material

    def hand(self, side: str, sign: int, skin) -> None:
        """A palm with a thenar pad, three-jointed fingers with nails, and a two-jointed thumb."""
        hand = f'hand.{side}'
        forearm = f'forearm.{side}'
        build = self.spec.get('build', 1.0)
        palm_rings = []
        palm_weights: list[Weights] = []
        for x, half_width, half_height, thenar, bone in (
                (.690, .029, .022, .000, {forearm: .45, hand: .55}),
                (.712, .032, .019, .004, hand), (.738, .037, .0165, .007, hand),
                (.762, .040, .0148, .005, hand), (.781, .041, .0135, .002, hand),
                (.795, .039, .0118, 0, hand)):
            ring = []
            for i in range(28):
                angle = math.tau * i / 28
                c, s = math.cos(angle), math.sin(angle)
                y = half_width * build * c - .003
                z = 1.372 + half_height * build * s
                if s < 0 and c < 0:  # fleshy pad below the thumb, on the palm side
                    z -= thenar * (-s) * (-c) * 1.6
                ring.append((sign * x, y, z))
            palm_rings.append(ring if sign == 1 else ring[::-1])
            palm_weights.append(bone)
        self.ring_mesh(f'Palm.{side}', palm_rings, skin, palm_weights)
        for digit, ((y, length, radius), knuckle) in enumerate(zip(FINGERS, KNUCKLE_X), 1):
            names = [f'finger_{digit:02d}{segment}.{side}' for segment in SEGMENTS]
            spread = (digit - 2.3) * .045
            direction = Vector((sign * math.cos(spread), math.sin(spread), -.02)).normalized()
            base = Vector((sign * (knuckle - .016), y * .92, 1.3725))
            knuckle_point = Vector((sign * knuckle, y, 1.371))
            joints = [0, PHALANX[0], PHALANX[0] + PHALANX[1], 1]
            points: list[Vector] = [base]
            radii: list[float] = [radius * 1.12]
            weights: list[Weights] = [hand]
            samples = (0, .12, .24, .36, .45, .52, .62, .70, .75, .80, .87, .93, .97, 1.0)
            for t in samples:
                points.append(knuckle_point + direction * length * t)
                taper = 1 - .26 * t
                joint_swell = max(math.exp(-((t - j) / .035) ** 2) for j in joints[:-1]) * .07
                tip_round = math.sqrt(max(0, 1 - ((t - .90) / .10) ** 2)) if t > .90 else 1
                radii.append(radius * build * (taper + joint_swell) * max(.18, tip_round))
                weights.append(self._phalanx_weights(t, names, hand))
            self.tube(f'Finger_{digit}.{side}', [tuple(p) for p in points], radii, skin, weights)
            nail_center = knuckle_point + direction * length * .905 + Vector((0, 0, radius * build * .62))
            self.ovoid(f'Fingernail_{digit}.{side}', tuple(nail_center),
                       (radius * .95, radius * .78, .0016), self.nail, names[2], (0, 0, sign * spread))
        thumb, thumb_tip = f'thumb.{side}', f'thumb_tip.{side}'
        thumb_points = [(sign * .700, -.010, 1.370), (sign * .715, -.024, 1.364), (sign * .733, -.040, 1.358),
                        (sign * .748, -.055, 1.352), (sign * .760, -.067, 1.349), (sign * .769, -.076, 1.347),
                        (sign * .774, -.082, 1.346)]
        thumb_radii = [.016, .0145, .0125, .0108, .0102, .0085, .0035]
        thumb_weights: list[Weights] = [{hand: .7, thumb: .3}, {hand: .25, thumb: .75}, thumb,
                                        {thumb: .5, thumb_tip: .5}, thumb_tip, thumb_tip, thumb_tip]
        self.tube(f'Thumb.{side}', thumb_points, [r * build for r in thumb_radii], skin, thumb_weights)
        self.ovoid(f'Thumbnail.{side}', (sign * .7665, -.0735, 1.3565), (.0085, .0075, .0016), self.nail,
                   thumb_tip, (0, -.25, sign * -.75))

    @staticmethod
    def _phalanx_weights(t: float, names: Sequence[str], hand: str) -> Weights:
        borders = (PHALANX[0], PHALANX[0] + PHALANX[1])
        blend = .05
        if t < .04:
            share = t / .04
            return {hand: 1 - share * .5, names[0]: share * .5} if share < 1 else names[0]
        for index, border in enumerate(borders):
            if abs(t - border) < blend:
                share = (t - border + blend) / (2 * blend)
                return {names[index]: 1 - share, names[index + 1]: share}
        if t < borders[0]:
            return names[0]
        return names[1] if t < borders[1] else names[2]

    # ------------------------------------------------------------------ face
    def head_radius(self, z: float) -> float:
        return profile(self.head_table, z)[1] * self.spec.get('face_width', 1)

    def relief(self, x: float, z: float) -> float:
        """Signed depth (positive pushes back, negative forward) of the sculpted face."""
        p = self.face_params
        side = abs(x)
        nose = self.spec.get('nose_width', 1)
        width = self.spec.get('face_width', 1)
        drop = p['nose_drop']
        ex = p['eye_x']
        forward = (
            p['bridge'] * gaussian(x, z, 0, 1.652 - drop * .5, .019 * nose, .039)
            + p['nose_tip'] * gaussian(x, z, 0, 1.620 - drop, .025 * nose * p['tip_width'], .0135 * p['tip_width'])
            + p['nose_wing'] * gaussian(side, z, .026 * nose, 1.611 - drop, .0125 * nose, .0105)
            + p['brow_ridge'] * gaussian(side, z, ex + .004, 1.703, .045, .0095)
            + .0025 * gaussian(x, z, 0, 1.698, .015, .011)
            + p['hood'] * gaussian(side, z, ex + .008, 1.6905, .026, .0055)
            + p['eye_bag'] * gaussian(side, z, ex + .004, 1.6555, .020, .0055)
            + p['cheek'] * gaussian(side, z, .067 * width, 1.630, .032, .026)
            + p['cheek_fat'] * gaussian(side, z, .060 * width, 1.596, .030, .024)
            + p['muzzle'] * gaussian(x, z, 0, 1.567, .044, .026)
            + p['chin'] * gaussian(x, z, 0, 1.514, .025, .016)
            + p['jowl'] * gaussian(side, z, .074 * width, 1.535, .028, .025)
            + p['forehead'] * gaussian(x, z, 0, 1.748, .07, .034)
            + p['double_chin'] * gaussian(x, z, 0, 1.489, .052, .009)
        )
        back = (
            .0048 * gaussian(side, z, .019 * nose, 1.605 - drop, .008 * nose, .003)
            + p['socket'] * gaussian(side, z, ex, 1.678, .031, .014)
            + p['temple'] * gaussian(side, z, .102 * width, 1.700, .020, .030)
            + .0024 * gaussian(x, z, 0, 1.591, .007, .012)
            + p['mentolabial'] * gaussian(x, z, 0, 1.539, .021, .0055)
            + p['nasolabial'] * crease(side, z, (.031 * nose, 1.603), (.050, 1.552), .0052)
            + p['marionette'] * crease(side, z, (.041, 1.555), (.050, 1.522), .0030)
            + p['double_chin'] * .55 * gaussian(x, z, 0, 1.5025, .046, .0036)
        )
        wrinkle = 0.
        if 1.718 < z < 1.778:
            fade = math.sin(math.pi * (z - 1.718) / .06) * math.exp(-(x / .055) ** 2)
            wrinkle = p['wrinkles'] * fade * math.sin((z - 1.718) / .0115 * math.tau + .7 * math.sin(x * 40))
        return back - forward + wrinkle

    def face_y(self, x: float, z: float) -> float:
        center, radius, depth = profile(self.head_table, z)
        width = self.spec.get('face_width', 1)
        frontal = math.sqrt(max(0, 1 - (x / (radius * width)) ** 2))
        return center - depth * frontal + frontal ** 2 * self.relief(x, z)

    def face(self) -> None:
        width = self.spec.get('face_width', 1)
        p = self.face_params
        skin = self.m['skin']
        low, high = self.head_table[0][0], self.head_table[-1][0]
        rings = []
        for level in range(141):
            z = low + level / 140 * (high - low)
            center, radius, depth = profile(self.head_table, z)
            ring = []
            for step in range(144):
                angle = math.tau * step / 144
                facing = math.sin(angle)
                x = width * radius * math.cos(angle)
                y = center + depth * facing + max(-facing, 0) ** 2 * self.relief(x, z)
                ring.append((x, y, z))
            rings.append(ring)
        self.ring_mesh('Head', rings, skin, 'head')
        base = self.spec['skin']
        lips = self.mat('Lips', tuple(a * f for a, f in zip(base, (.74, .52, .52))), .57)
        lip_surface(lips)
        inner = self.mat('Mouth interior', (.035, .008, .007), .63)
        inner_ear = self.mat('Inner ear', tuple(a * f for a, f in zip(base, (.82, .67, .63))))
        sclera = self.mat('Eye white', (.52, .47, .42), .16)
        shader = sclera.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Specular IOR Level'].default_value = .5
        shader.inputs['Coat Weight'].default_value = .6
        shader.inputs['Coat Roughness'].default_value = .02
        pigment_material(sclera, 'Sclera pigment')
        sclera.node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value = .5
        eye_rim = self.mat('Eyelid edge', tuple(a * f for a, f in zip(base, (.66, .45, .42))), .45)
        nostril = self.mat('Nostril shadow', tuple(a * f for a, f in zip(base, (.20, .125, .125))), .81)
        iris = self.m['iris']
        iris.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value = .38
        pigment_material(iris, 'Iris pigment')
        cornea = self.cornea_material()
        for side, sign in (('L', 1), ('R', -1)):
            x = sign * p['eye_x']
            self.ear(side, sign, width, skin, inner_ear)
            self.nostril(side, sign, self.spec.get('nose_width', 1), nostril)
            self.eye(side, sign, width, sclera, eye_rim, iris, cornea)
            lift = self.spec.get('brow_lift', .0)
            brow_points = [(x - sign * .029, 1.704), (x - sign * .014, 1.713 + lift), (x + sign * .006, 1.716 + lift),
                           (x + sign * .024, 1.711 + lift), (x + sign * .036, 1.703)]
            self.tube(f'Brow.{side}', [(bx, self.face_y(bx, bz) + .0012, bz) for bx, bz in brow_points],
                      [.0018, .0028, .0026, .0018, .0007], self.m['hair'], 'head')
        self.mouth(lips, inner)

    def mouth(self, lip, inner) -> None:
        """The cast mouth with fuller, parametric lips; same shape-key names and ring layout."""
        p = self.face_params
        full, lower, width = p['lip_full'], p['lower_lip'], p['mouth_width']
        segments = 64
        angles = [math.tau * i / segments for i in range(segments)]
        middle = 1.566

        def outline(half_width: float, opening: float, roundness: float) -> list[Point]:
            points = []
            rings = ((half_width + .0038, opening + .007 * full, 0), (half_width + .0015, opening + .0048 * full, .0025 * full),
                     (half_width, opening, .0044 * full), (.0015, .00065, .0012))
            for ring, (rx, rz, depth) in enumerate(rings):
                for angle in angles:
                    u, w = math.cos(angle), math.sin(angle)
                    x = rx * u
                    height = rz * (lower if w < 0 and ring < 2 else 1)
                    z = height * w * (1 - (1 - roundness) * abs(u))
                    if ring < 3 and w > 0:
                        z = z * .86 - .00145 * math.exp(-(u / .23) ** 2) * w
                    z += middle + .0011 * u - .0014 * u * u
                    pout = depth * (1.18 if w < 0 and ring == 2 else 1)
                    y = self.face_y(x, z) - pout * (1 - .6 * abs(u) ** 2)
                    if ring in (0, 3):
                        y += .00035 if ring == 0 else -.0009
                    points.append((x, y, z))
            return points

        faces = []
        for ring in range(3):
            a, b = ring * segments, (ring + 1) * segments
            faces.extend((a + i, a + (i + 1) % segments, b + (i + 1) % segments, b + i) for i in range(segments))
        faces.append(tuple(range(3 * segments, 4 * segments)))
        scale_width = width / .033
        obj = self.mesh('Mouth', outline(width, .00125, .66), faces, lip, 'head')
        obj.data.materials.append(inner)
        for face in obj.data.polygons[segments * 2:]:
            face.material_index = 1
        base = self.spec['skin']
        factors = ((1.0, .945, .91), (.84, .63, .60), (.73, .50, .48), (.6, .43, .43))
        color_samples = []
        for ring, tint in enumerate(factors):
            for angle in angles:
                darker_upper = 1 - .13 * max(math.sin(angle), 0) if ring else 1
                color_samples.append(tuple(value * gain * darker_upper for value, gain in zip(base, tint)))
        vertex_pigment(obj, 'Lip pigment', color_samples)
        obj.shape_key_add(name='Basis', from_mix=False)
        obj.data.shape_keys.use_relative = True
        for key, shape in {'Mouth_Ah': (.033, .024, .83), 'Mouth_O': (.019, .022, 1),
                           'Mouth_Ee': (.047, .009, .7), 'Mouth_MBP': (.034, .0004, .66),
                           'Mouth_FV': (.039, .004, .73)}.items():
            blend = obj.shape_key_add(name=key, from_mix=False)
            half_width, opening, roundness = shape
            for vertex, coordinate in zip(blend.data, outline(half_width * scale_width, opening, roundness)):
                vertex.co = Vector(coordinate) * self.scale
            blend.value = 0
        obj['Usage'] = 'Use one primary phoneme at a time. Basis is the relaxed mouth.'

    def nostril(self, side: str, sign: int, nose: float, material) -> None:
        drop = self.face_params['nose_drop']
        rings = []
        for size in (1, .67, .08):
            ring = []
            for step in range(24):
                angle = math.tau * step / 24
                u, w = math.cos(angle) * size, math.sin(angle) * size
                x = sign * (.020 * u * .39 + .020) * nose
                z = 1.605 - drop + .0024 * w + .0018 * u
                ring.append((x, self.face_y(x, z) - .00025, z))
            rings.append(ring if sign == 1 else ring[::-1])
        self.ring_mesh(f'Nostril.{side}', rings, material, 'head', cap=False)

    def ear(self, side: str, sign: int, width: float, skin, inner) -> None:
        p = self.face_params
        size_scale = p['ear_size']
        root = self.head_radius(1.639) - .004 + p['ear_out']
        angles = tuple(math.tau * i / 48 for i in range(48))
        rings = []
        for size, depth, offset in ((.38, .023, 0), (.85, .016, 0), (1, .002, 0), (.94, -.013, 0),
                                    (.78, -.026, 0), (.56, -.019, -.001), (.39, -.009, -.002), (.05, -.01, -.005)):
            ring = []
            for angle in angles:
                u, w = math.cos(angle), math.sin(angle)
                horizontal = .021 * u * (.88 + .15 * max(w, 0) - .22 * max(-w, 0)) + .004 * w
                x = sign * (root + size * horizontal * size_scale + offset)
                z = 1.639 + .042 * size * w * size_scale + .001 * u
                y = depth * size_scale + .007 * u * size + .002 * w
                ring.append((x, y, z))
            rings.append(ring if sign == 1 else ring[::-1])
        ear = self.ring_mesh(f'Ear.{side}', rings, skin, 'head')
        ear.data.materials.append(inner)
        for face in ear.data.polygons[6 * len(angles):7 * len(angles)]:
            face.material_index = 1
        crest = [(sign * (root + .002 + x * size_scale), y * size_scale, 1.639 + (z - 1.639) * size_scale) for x, y, z in
                 ((-.010, -.022, 1.624), (-.006, -.024, 1.635), (.001, -.025, 1.649), (.005, -.022, 1.658))]
        self.tube(f'Ear inner fold.{side}', crest, [.0023, .004, .0034, .001], skin, 'head')

    def eyelid_point(self, sign: int, angle: float, size: float) -> tuple[float, float]:
        p = self.face_params
        cx, cz = sign * p['eye_x'], 1.675
        u, w = math.cos(angle), math.sin(angle)
        # Inner corner (towards the nose) sits lower and more pointed than the outer.
        lid = p['upper_lid'] if w > 0 else p['lower_lid']
        inner = max(0, -sign * u)
        x = cx + p['eye_radius'] * size * u
        z = cz + size * (w * lid * (1 - .24 * abs(u) ** 1.5) * (1 - .12 * inner) + .0016 * sign * u
                         - .0012 * inner * inner)
        return x, z

    def eye_surface(self, sign: int, x: float, z: float) -> float:
        p = self.face_params
        cx = sign * p['eye_x']
        horizontal, vertical = (x - cx) / p['eye_radius'], (z - 1.675) / .0105
        dome = max(0, 1 - horizontal ** 2 - (vertical - sign * .12 * horizontal) ** 2)
        return self.face_y(x, z) - .0012 - .0068 * dome ** .65

    def eye(self, side: str, sign: int, width: float, sclera, rim, iris, cornea) -> None:
        p = self.face_params
        cx, cz = sign * p['eye_x'], 1.675
        angles = tuple(math.tau * i / 72 for i in range(72))
        eye_rings, sclera_colors = [], []
        for size in (1, .9, .78, .64, .5, .35, .2, .08, .01):
            ring = []
            for angle in angles:
                x, z = self.eyelid_point(sign, angle, size)
                ring.append((x, self.eye_surface(sign, x, z) + size ** 5 * .0006, z))
                # Lid shadow on the upper white, pink at the inner corner, warmer at the edges.
                top = max(0, math.sin(angle)) * size ** 3
                inner = max(0, -sign * math.cos(angle)) ** 6 * size ** 2
                tone = (.66 - .30 * top - .06 * size ** 4)
                sclera_colors.append((tone * (1 + .22 * inner), tone * (1 - .18 * inner), tone * (1 - .22 * inner)))
            eye_rings.append(ring)
        eye = self.ring_mesh(f'Eye.{side}', eye_rings, sclera, 'head', cap=False)
        vertex_pigment(eye, 'Sclera pigment', sclera_colors)

        lid_rings = []
        for size, depth in ((1, .0010), (1.06, .0024), (1.14, .0019), (1.28, -.0002), (1.5, -.0011)):
            ring = []
            for angle in angles:
                x, z = self.eyelid_point(sign, angle, size)
                y = self.face_y(x, z) - depth - .0011 * max(0, math.sin(angle))
                ring.append((x, y, z))
            lid_rings.append(ring)
        lid = self.ring_mesh(f'Eyelids.{side}', lid_rings[::-1], self.m['skin'], 'head', cap=False)
        lid.data.materials.append(rim)
        for face in list(lid.data.polygons)[-2 * len(angles):]:
            face.material_index = 1

        iris_rings, colors = [], []
        scale = p['iris']
        for radius, shade in ((.0105, .36), (.0099, .62), (.0091, 1.0), (.0076, 1.05), (.0058, 1.25),
                              (.0047, 1.15), (.0041, .38), (.00395, .05), (.002, .045), (.00009, .045)):
            ring = []
            r = radius * scale
            for angle in angles:
                x = cx + r * math.cos(angle)
                z = cz + .96 * r * math.sin(angle)
                ring.append((x, self.eye_surface(sign, x, z) - .0006, z))
                streak = (.74 + .26 * math.sin(19 * angle + 180 * radius) ** 2 + .2 * math.sin(29 * angle - 465 * radius) ** 2)
                strength = shade * (streak if radius > .0042 else 1)
                colors.append(tuple(channel * strength for channel in self.spec['iris']))
            iris_rings.append(ring)
        pigment = self.ring_mesh(f'Iris.{side}', iris_rings, iris, f'eye.{side}', cap=False)
        vertex_pigment(pigment, 'Iris pigment', colors)

        # Clear corneal bulge: gives the moving catch-light of a real eye.
        cornea_rings = []
        radius = .0112 * scale
        for t in (1, .85, .65, .42, .2, .02):
            ring = []
            r = radius * t
            for angle in angles:
                x = cx + r * math.cos(angle)
                z = cz + .96 * r * math.sin(angle)
                bulge = .0016 * (1 - t * t) ** .5 + .0002
                ring.append((x, self.eye_surface(sign, x, z) - .0006 - bulge, z))
            cornea_rings.append(ring)
        self.ring_mesh(f'Cornea.{side}', cornea_rings, cornea, f'eye.{side}', cap=False)

        # Lash line: a dark, thin margin that reads as lashes at a distance.
        upper = [self.eyelid_point(sign, a, 1.035) for a in angles if 0 <= a <= math.pi]
        line = [(x, self.face_y(x, z) - .0026, z) for x, z in upper]
        self.tube(f'Upper lash line.{side}', line, [.0004] + [.0012] * (len(line) - 2) + [.0004],
                  self.lash_material, 'head')
        if p['lid_crease']:
            fold = [self.eyelid_point(sign, a, 1.42) for a in angles if .25 <= a <= math.pi - .25]
            crease_line = [(x, self.face_y(x, z) + .0002, z + .0012) for x, z in fold]
            radii = [p['lid_crease'] * math.sin(math.pi * i / (len(crease_line) - 1)) ** .5 + .0001
                     for i in range(len(crease_line))]
            self.tube(f'Upper lid crease.{side}', crease_line, radii, self.crease_material, 'head')

    def cornea_material(self):
        """Clear film with a Fresnel gloss: catch-lights without darkening the iris."""
        material = bpy.data.materials.new(f'{self.name} • Cornea')
        material.diffuse_color = (.9, .9, .9, .1)
        material.use_nodes = True
        nodes, links = material.node_tree.nodes, material.node_tree.links
        nodes.remove(nodes.get('Principled BSDF'))
        output = nodes.get('Material Output')
        clear = nodes.new('ShaderNodeBsdfTransparent')
        gloss = nodes.new('ShaderNodeBsdfGlossy')
        gloss.inputs['Roughness'].default_value = .015
        fresnel = nodes.new('ShaderNodeFresnel')
        fresnel.inputs['IOR'].default_value = 1.6
        mix = nodes.new('ShaderNodeMixShader')
        links.new(fresnel.outputs['Fac'], mix.inputs['Fac'])
        links.new(clear.outputs['BSDF'], mix.inputs[1])
        links.new(gloss.outputs['BSDF'], mix.inputs[2])
        links.new(mix.outputs['Shader'], output.inputs['Surface'])
        return material

    @property
    def crease_material(self):
        existing = bpy.data.materials.get(f'{self.name} • Skin crease')
        return existing or self.mat('Skin crease', tuple(v * .62 for v in self.spec['skin']), .8)

    @property
    def lash_material(self):
        existing = bpy.data.materials.get(f'{self.name} • Lash line')
        return existing or self.mat('Lash line', tuple(v * .35 for v in self.spec['hair']), .5)

    # ------------------------------------------------------------------ proportions
    def scale_head(self, factor: float) -> None:
        """Shrink or grow everything weighted to the head about the neck joint, including shape keys.

        Run last, after facial controls exist, so every shape key keeps its delta. The
        cast's heads are large and stylised; 0.84-0.88 gives realistic proportions.
        """
        if abs(factor - 1) < 1e-6:
            return
        pivot = Vector((0, -.013, 1.50)) * self.scale

        def moved(co: Vector, weight: float) -> Vector:
            return co + ((pivot + (co - pivot) * factor) - co) * weight
        for part in self.parts:
            indices = {group.index for group in part.vertex_groups if group.name in ('head', 'eye.L', 'eye.R')}
            if not indices:
                continue
            weights = {}
            for vertex in part.data.vertices:
                share = sum(item.weight for item in vertex.groups if item.group in indices)
                if share > 0:
                    weights[vertex.index] = min(1., share)
            if not weights:
                continue
            for index, weight in weights.items():
                vertex = part.data.vertices[index]
                vertex.co = moved(vertex.co, weight)
            if part.data.shape_keys is not None:
                for block in part.data.shape_keys.key_blocks:
                    for index, weight in weights.items():
                        block.data[index].co = moved(block.data[index].co, weight)
            part.data.update()
        bpy.context.view_layer.objects.active = self.rig
        bpy.ops.object.mode_set(mode='EDIT')
        for name in ('head', 'eye.L', 'eye.R'):
            bone = self.rig.data.edit_bones[name]
            bone.head = pivot + (bone.head - pivot) * factor
            bone.tail = pivot + (bone.tail - pivot) * factor
        bpy.ops.object.mode_set(mode='OBJECT')
        self.rig['Head_scale'] = factor

    # ------------------------------------------------------------------ skin
    def apply_skin_tint(self, tint: TintFunction) -> None:
        """Bake per-vertex tint (RGB multipliers) and sheen (roughness offset) onto the head.

        The skin material reads `Skin tint` as an offset from 1, so parts without the
        layer (arms, hands) keep the plain skin colour.
        """
        head = next(part for part in self.parts if part.name == f'{self.name}_Head')
        tints, sheen = [], []
        for vertex in head.data.vertices:
            x, y, z = (vertex.co / self.scale)
            r, g, b, gloss = tint(x, y, z)
            tints.append((r - 1, g - 1, b - 1))
            sheen.append(gloss)
        layer = head.data.color_attributes.new(name=TINT_ATTRIBUTE, type='FLOAT_COLOR', domain='POINT')
        layer.data.foreach_set('color', [c for color in tints for c in (*color, 1)])
        gloss_layer = head.data.attributes.new(SHEEN_ATTRIBUTE, 'FLOAT', 'POINT')
        gloss_layer.data.foreach_set('value', sheen)

        material = self.m['skin']
        nodes, links = material.node_tree.nodes, material.node_tree.links
        shader = nodes.get('Principled BSDF')
        colour_source = shader.inputs['Base Color'].links[0].from_socket
        attribute = nodes.new('ShaderNodeAttribute')
        attribute.attribute_name = TINT_ATTRIBUTE
        attribute.label = 'Regional skin tint (offset from 1)'
        attribute.location = (-460, 620)
        one = nodes.new('ShaderNodeVectorMath')
        one.operation = 'ADD'
        one.inputs[1].default_value = (1, 1, 1)
        one.location = (-230, 620)
        links.new(attribute.outputs['Vector'], one.inputs[0])
        multiply = nodes.new('ShaderNodeMixRGB')
        multiply.blend_type = 'MULTIPLY'
        multiply.inputs[0].default_value = 1
        multiply.location = (40, 520)
        links.new(colour_source, multiply.inputs[1])
        links.new(one.outputs['Vector'], multiply.inputs[2])
        links.new(multiply.outputs['Color'], shader.inputs['Base Color'])
        rough_source = shader.inputs['Roughness'].links[0].from_socket
        gloss = nodes.new('ShaderNodeAttribute')
        gloss.attribute_name = SHEEN_ATTRIBUTE
        gloss.attribute_type = 'GEOMETRY'
        gloss.location = (-230, -40)
        add = nodes.new('ShaderNodeMath')
        add.operation = 'ADD'
        add.use_clamp = True
        add.location = (330, 40)
        links.new(rough_source, add.inputs[0])
        links.new(gloss.outputs['Fac'], add.inputs[1])
        links.new(add.outputs['Value'], shader.inputs['Roughness'])
        shader.inputs['Subsurface Weight'].default_value = .16
        shader.inputs['Subsurface Scale'].default_value = .006
        shader.inputs['Subsurface Radius'].default_value = (1.0, .35, .18)
        material['Regional tint'] = f'{TINT_ATTRIBUTE} (colour offset) and {SHEEN_ATTRIBUTE} (roughness offset) on the head mesh'

