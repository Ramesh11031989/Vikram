"""Reusable child body for the cast, built from the adult character template.

The adult generators in `character.py` author every mesh in one shared "design"
space: a 1.81 m adult skeleton.  `ChildCharacter` keeps that authoring space, so
existing helpers (`loft`, `tube`, `ovoid`, `face`) and garment code written for
adults still work, and moves each vertex into child proportions as it is
created.  Every vertex follows the bones that skin it: each bone has an affine
map from its adult rest frame to its child rest frame, and a vertex takes the
weighted blend of its bones' maps.  Head vertices first pass through a smooth
child-face warp (rounder cranium, shorter midface, larger eyes, a small low
nose, fuller cheeks) and then a single similarity transform, so the face keeps
its proportions while it is resized.

The child face also replaces a few adult details: rounder eye openings with a
larger iris clipped by the lids, a clear cornea for small catchlights (the
iris and cornea face straight ahead so both eyes share one gaze), fine lashes,
soft low brows drawn by strand hairs over a thin tint, closed lips with a
slight smile, round cheeks without the adult cheekbone ridge, shaded
nostrils, anatomical ears lying along the head, rosy cheeks and finer pores.

The rig keeps the 34 shared cast bone names, so poses and clips stay
interchangeable with the adults.  It adds two-segment fingers and thumbs
(`finger_02_mid.L`, `finger_02_tip.L`, `thumb_mid.L`, ...) for gripping small
props, and non-deforming `prop.L` / `prop.R` sockets at the palms.

Reuse for another child (for example Gopal's niece): give a new SPEC its own
`ChildProportions`, `ChildFace`, colours and dress module.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
import math

import bpy
from mathutils import Matrix, Quaternion, Vector

from character import Character, gaussian, profile_at
from face_surface import vertex_pigment
from facial_controls import MOUTH_KEYS, driver_from_property, property_control, shape_from_delta


Point = tuple[float, float, float]
Weights = Mapping[str, float]
BoneSpec = str | Sequence[str | Weights]

HEAD_GROUP = frozenset({'head', 'eye.L', 'eye.R'})
EYE_LINE = 1.675  # design-space height of the eye centres
# Design-space finger rows: (lateral offset, length).  Index is at -Y (front).
FINGERS = ((-.035, .055), (-.012, .072), (.01, .071), (.033, .05))
KNUCKLE_X = .773
FINGER_JOINTS = (.45, .75)  # proximal / middle / distal split along each finger
THUMB = ((.712, -.020, 1.368), (.733, -.044, 1.360), (.751, -.064, 1.354), (.768, -.080, 1.350))


def smoothstep(edge0: float, edge1: float, value: float) -> float:
    t = max(0., min(1., (value - edge0) / (edge1 - edge0)))
    return t * t * (3 - 2 * t)


@dataclass(frozen=True)
class ChildProportions:
    """Child body relative to the adult design template (factors are ratios).

    Defaults give realistic proportions for a 5-6 year old of 1.10 m (head
    14 x 18.5 x 19.5 cm, shoulders about 25 cm, hand 11.5 cm, foot 16 cm).  The
    adult template's head is stylised (26 cm wide), so the head scale is set
    per axis (width, depth, height); the template iris is drawn wide for the
    same reason and comes out round.
    """
    height: float = 1.10        # skull crown above the floor, metres
    head: tuple[float, float, float] = (.60, .73, .63)
    torso_ratio: float = 1.075  # torso length factor / leg length factor
    neck_length: float = .32
    neck_girth: float = .60
    body_width: float = .52     # hips, waist and chest width
    shoulders: float = .42      # collarbone length
    leg_girth: float = .58
    arm_length: float = .74
    arm_girth: float = .56
    hand: tuple[float, float] = (.80, .58)  # along the fingers / across and through the palm
    foot: tuple[float, float] = (.70, .54)  # along / across the foot bone

    def leg_factor(self, crown_above_head_bone: float) -> float:
        """Solve the leg length factor so the crown lands at `height`."""
        fixed = self.head[2] * crown_above_head_bone + .11 * self.neck_length
        return (self.height - fixed) / (1.04 + .35 * self.torso_ratio)


@dataclass(frozen=True)
class ChildFace:
    """A smooth design-space warp from the adult face template to a child's."""
    lower_face: float = .74     # vertical scale below the eye line: a short child's lower face
    cranium: float = 1.08       # vertical scale above the eye line
    blend: float = .05          # half-width of the smooth transition, m
    eye_size: float = .12       # extra size at the eye centre
    eye_radius: float = .05
    bridge: float = .66         # fraction of the adult nasal bridge removed
    tip: float = .60            # fraction of the adult nose tip removed
    wing: float = .30           # fraction of the adult nostril wings removed (keeps soft alae)
    tip_lift: float = .0026     # upturn of the nose tip, so the nostrils show, m
    socket_fill: float = .25    # how much of the adult eye socket depth is filled in
    cheekbone: float = 1.       # fraction of the adult cheekbone ridge removed
    cheek_fill: float = .004    # broad, soft forward fullness of the cheeks, m
    brow_forward: float = .008  # brings the brow and forehead forward, level with the cheeks, m
    jaw_narrow: float = .20     # a small, round jaw and chin under full cheeks
    mouth_narrow: float = .18
    lip_fullness: float = 1.15  # extra vertical lip height at the centre
    lip_pout: float = 0.        # forward push of the lips, m
    mouth_lift: float = .0055   # raises the mouth toward the nose: a short child's philtrum, m
    eye_open: float = .12       # extra vertical eye opening (rounder eyes)
    forehead: float = .012      # forward fullness of the forehead, m
    iris_size: float = 1.32     # iris radius relative to the adult template
    lash_length: float = .0072  # longest upper lash, design m
    smile: float = .0022        # resting lift of the mouth corners, m
    face_curve: float = .004    # pushes the sides of the face back a little so the eyes sit in a curved face
    eye_width: float = .0282    # half-width of the eye opening (adult template .030)
    upper_lid: float = .0113    # eye opening above the centre (adult template .0105)
    lower_lid: float = .0088    # eye opening below the centre (adult template .0087)
    pinch: float = .13          # how much the opening narrows toward the corners (adult .21)

    def vertical(self, offset: float) -> float:
        """Integral of a smoothly blended scale; continuous slope at the eye line."""
        w, lo, hi = self.blend, self.lower_face, self.cranium

        def integral(u: float) -> float:
            if u <= -w:
                return lo * (u + w)
            if u >= w:
                return w * (lo + hi) + hi * (u - w)
            q = (u + w) / (2 * w)
            return lo * (u + w) + (hi - lo) * 2 * w * (q ** 3 - q ** 4 / 2)
        return integral(offset) - integral(0)


@dataclass
class BoneMap:
    """Affine map of one bone's rest frame from adult design space to the child."""
    design_head: Vector
    axis: Vector
    child_head: Vector
    along: float
    across: float
    warp: Callable[[Vector], Vector] | None = None
    scale: Vector | None = None  # per-axis scale instead of along / across
    reference: Vector = field(default_factory=Vector)

    def __post_init__(self) -> None:
        self.reference = self.warp(self.design_head) if self.warp else self.design_head.copy()

    def apply(self, point: Vector) -> Vector:
        offset = (self.warp(point) if self.warp else point) - self.reference
        if self.scale is not None:
            return self.child_head + Vector(a * b for a, b in zip(offset, self.scale))
        along = self.axis.dot(offset)
        return self.child_head + self.axis * (along * self.along) + (offset - self.axis * along) * self.across


class ChildCharacter(Character):
    """A child built from the adult template; see the module docstring."""

    def __init__(self, spec: dict) -> None:
        self.proportions: ChildProportions = spec['proportions']
        self.face_shape: ChildFace = spec['child_face']
        self.width = spec.get('face_width', 1.)
        self.nose = spec.get('nose_width', 1.)
        self.bone_maps: dict[str, BoneMap] = {}
        self.design: dict[str, list[Vector]] = {}
        self._native = False
        super().__init__(spec)
        self.rig['Usage'] = ('Child FK skeleton with the 34 shared cast bone names, two-segment '
                             'fingers and thumbs, and prop.L / prop.R palm sockets.')

    # ------------------------------------------------------------------ warp
    def face_warp(self, point: Vector) -> Vector:
        face = self.face_shape
        x, y, z = point
        center, _, depth = profile_at(z)
        front = smoothstep(.15, .55, (center - y) / max(depth, .02))
        if front:
            side, w, n = abs(x), self.width, self.nose
            bridge = .031 * gaussian(x, z, 0, 1.652, .019 * n, .039)
            tip = .034 * gaussian(x, z, 0, 1.620, .024 * n, .012)
            wing = .016 * gaussian(side, z, .025 * n, 1.612, .012 * n, .010)
            nostril = .0048 * gaussian(side, z, .019 * n, 1.605, .008 * n, .003)
            socket = .0064 * gaussian(side, z, .053 * w, 1.678, .034, .015)
            # A child has no cheekbone ridge: remove the adult's and add one broad, round fullness.
            adult_cheek = .0064 * gaussian(side, z, .067 * w, 1.634, .030, .024)
            cheek = gaussian(side, z, .058 * w, 1.628, .042, .040)
            brow_band = smoothstep(1.69, 1.76, z) * math.exp(-(x / (.075 * w)) ** 2)
            lips = front * math.exp(-((z - 1.566) / .014) ** 2 - (x / .045) ** 2)
            y += front * (face.bridge * bridge + face.tip * tip + face.wing * wing - .3 * nostril
                          - face.socket_fill * socket + face.cheekbone * adult_cheek - face.cheek_fill * cheek
                          - face.forehead * brow_band - face.brow_forward * smoothstep(1.645, 1.73, z)
                          + face.face_curve * min(1., (x / (.1 * w)) ** 2)) - face.lip_pout * lips
            mouth = front * math.exp(-((z - 1.566) / .02) ** 2 - (x / .075) ** 4)
            x *= 1 - face.mouth_narrow * mouth
            z = 1.566 + (z - 1.566) * (1 + face.lip_fullness * lips)
            z += face.tip_lift * front * gaussian(x, z, 0, 1.617, .03 * n, .016)
            # Monotonic lift peaking at the lips, zero at the nose base and below the chin.
            # Kept to the mouth and philtrum so it never folds the cheeks beside them.
            hump = smoothstep(1.49, 1.566, z) * (1 - smoothstep(1.566, 1.612, z))
            z += face.mouth_lift * front * hump * math.exp(-(x / .05) ** 4)
        x *= 1 - face.jaw_narrow * smoothstep(1.665, 1.505, z)  # tapers from the eyes down: no corner at the cheeks
        z = EYE_LINE + face.vertical(z - EYE_LINE)
        for cx in (.053 * self.width, -.053 * self.width):
            dx, dz = x - cx, z - EYE_LINE
            r2 = (dx * dx + dz * dz) / face.eye_radius ** 2
            if r2 < 1:
                grow = 1 + face.eye_size * (1 - r2) ** 2
                x, z = cx + dx * grow, EYE_LINE + dz * (grow + face.eye_open * (1 - r2) ** 2)
        return Vector((x, y, z))

    def place(self, point: Vector, weights: Weights) -> Vector:
        result = Vector()
        for joint, weight in weights.items():
            result += weight * self.bone_maps[joint].apply(point)
        return result

    # ------------------------------------------------------------------- rig
    def make_rig(self):
        rig = super().make_rig()  # adult design skeleton (scale 1)
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode='EDIT')
        bones = rig.data.edit_bones
        for side, sign in (('L', 1), ('R', -1)):
            self._segment_digits(bones, side, sign)
        design = {bone.name: (bone.head.copy(), bone.tail.copy(), bone.parent.name if bone.parent else None)
                  for bone in bones}
        self._solve_maps(design)
        for bone in bones:
            mapping = self.bone_maps[bone.name]
            head, tail, _ = design[bone.name]
            bone.head = mapping.apply(head)
            bone.tail = mapping.apply(tail)
            bone.roll = 0
        bpy.ops.object.mode_set(mode='OBJECT')
        return rig

    def _segment_digits(self, bones, side: str, sign: int) -> None:
        hand = bones[f'hand.{side}']
        for digit, (y, length) in enumerate(FINGERS, 1):
            def at(t: float) -> Vector:
                return Vector((sign * (KNUCKLE_X + length * t), y, 1.37 - .006 * t))
            base = bones[f'finger_{digit:02d}.{side}']
            base.tail = at(FINGER_JOINTS[0])
            parent = base
            for label, start, end in (('mid', FINGER_JOINTS[0], FINGER_JOINTS[1]),
                                      ('tip', FINGER_JOINTS[1], 1.)):
                segment = bones.new(f'finger_{digit:02d}_{label}.{side}')
                segment.head, segment.tail = at(start), at(end)
                segment.parent = parent
                segment.use_connect = True
                parent = segment
        points = [Vector((sign * x, y, z)) for x, y, z in THUMB]
        thumb = bones[f'thumb.{side}']
        thumb.head, thumb.tail = points[0], points[1]
        parent = thumb
        for label, index in (('mid', 1), ('tip', 2)):
            segment = bones.new(f'thumb_{label}.{side}')
            segment.head, segment.tail = points[index], points[index + 1]
            segment.parent = parent
            segment.use_connect = True
            parent = segment
        socket = bones.new(f'prop.{side}')
        # On the palm surface; local Y runs toward the fingers, -Z out of the palm.
        socket.head = Vector((sign * .752, -.004, 1.347))
        socket.tail = Vector((sign * .782, -.004, 1.347))
        socket.parent = hand
        socket.use_deform = False

    def _factors(self, name: str) -> tuple[float, float]:
        body = self.proportions
        base = name.split('.')[0]
        leg = self.leg
        if base in ('root', 'hips'):
            return leg, body.body_width
        if base in ('thigh', 'shin'):
            return leg, body.leg_girth
        if base in ('foot', 'toes'):
            return body.foot
        if base in ('spine', 'chest'):
            return leg * body.torso_ratio, body.body_width
        if base == 'neck':
            return body.neck_length, body.neck_girth
        if base == 'clavicle':
            return body.shoulders, body.body_width
        if base in ('upper_arm', 'forearm'):
            return body.arm_length, body.arm_girth
        return body.hand  # hand, fingers, thumbs, prop sockets

    def _solve_maps(self, design: Mapping[str, tuple[Vector, Vector, str | None]]) -> None:
        crown = Vector((0, -.013, 1.812))
        head_ref = self.face_warp(Vector((0, -.013, 1.5)))
        self.leg = self.proportions.leg_factor(self.face_warp(crown).z - head_ref.z)

        def depth(name: str) -> int:
            parent = design[name][2]
            return 0 if parent is None else 1 + depth(parent)

        for name in sorted(design, key=depth):
            head, tail, parent = design[name]
            if parent is None:
                self.bone_maps[name] = BoneMap(head, Vector((0, 0, 1)), head.copy(),
                                               *self._factors(name))
                continue
            child_head = self.bone_maps[parent].apply(head)
            if name in HEAD_GROUP:
                if name == 'head':
                    self.bone_maps[name] = BoneMap(head, Vector((0, 0, 1)), child_head, 1, 1,
                                                   self.face_warp, Vector(self.proportions.head))
                else:  # eyes share the head transform exactly
                    self.bone_maps[name] = self.bone_maps['head']
                continue
            axis = (tail - head).normalized()
            self.bone_maps[name] = BoneMap(head, axis, child_head, *self._factors(name))

    # ---------------------------------------------------------------- meshes
    @contextmanager
    def native_space(self) -> Iterator[None]:
        """Author meshes directly in child space (e.g. braids hanging on the body)."""
        self._native = True
        try:
            yield
        finally:
            self._native = False

    def mesh(self, name, verts, faces, material, bone, smooth=True):
        design = [Vector(p) for p in verts]
        if not self._native:
            if isinstance(bone, str):
                weights: Sequence[Weights] = [{bone: 1.}] * len(design)
            else:
                weights = [{item: 1.} if isinstance(item, str) else item for item in bone]
            if len(weights) != len(design):
                raise ValueError(f'{name}: {len(weights)} weight entries for {len(design)} vertices')
            verts = [self.place(point, weight) for point, weight in zip(design, weights)]
        obj = super().mesh(name, verts, faces, material, bone, smooth)
        self.design[obj.name] = design
        return obj

    def remove_part(self, label: str) -> None:
        obj = next(part for part in self.parts if part.name == f'{self.name}_{label}')
        self.parts.remove(obj)
        self.design.pop(obj.name, None)
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if data.users == 0:
            bpy.data.meshes.remove(data)

    def part(self, label: str):
        return next(part for part in self.parts if part.name == f'{self.name}_{label}')

    # ------------------------------------------------------------------ body
    def body(self) -> None:
        super().body()
        nail = self.mat('Fingernail', tuple(v * f for v, f in zip(self.spec['skin'], (1.32, 1.06, .98))), .33)
        for side, sign in (('L', 1), ('R', -1)):
            for label in ('Finger_1', 'Finger_2', 'Finger_3', 'Finger_4', 'Thumb'):
                self.remove_part(f'{label}.{side}')
            for digit, (y, length) in enumerate(FINGERS, 1):
                path = [Vector((sign * (KNUCKLE_X + length * t), y, 1.37 - .006 * t)) for t in (-.14, 1.)]
                width = .0108 - .0008 * abs(digit - 2.4)
                self.digit(f'Finger_{digit}.{side}', path, f'finger_{digit:02d}', side, FINGER_JOINTS,
                           width, width * 1.08, nail)
            path = [Vector((sign * x, y, z)) for x, y, z in THUMB]
            lengths = [(b - a).length for a, b in zip(path, path[1:])]
            joints = (lengths[0] / sum(lengths), (lengths[0] + lengths[1]) / sum(lengths))
            self.digit(f'Thumb.{side}', path, 'thumb', side, joints, .0128, .0122, nail)

    def digit(self, label: str, path: Sequence[Vector], bone: str, side: str,
              joints: tuple[float, float], width: float, height: float, nail) -> None:
        """A finger or thumb: elliptical rings along a polyline, rounded tip, nail."""
        lengths = [(b - a).length for a, b in zip(path, path[1:])]
        total = sum(lengths)

        def sample(t: float) -> tuple[Vector, Vector]:
            distance = t * total
            for start, end, length in zip(path, path[1:], lengths):
                if distance <= length or end is path[-1]:
                    return start.lerp(end, min(1., distance / length)), (end - start).normalized()
                distance -= length
            raise ValueError('empty digit path')

        names = (f'{bone}.{side}', f'{bone}_mid.{side}', f'{bone}_tip.{side}')
        parent = f'hand.{side}'
        start = .14 / 1.14 if bone.startswith('finger') else 0.

        def weights(t: float) -> dict[str, float]:
            if bone.startswith('finger') and t < start + .06:
                knuckle = smoothstep(start - .06, start + .06, t)
                return {parent: 1 - knuckle, names[0]: knuckle} if knuckle < 1 else {names[0]: 1.}
            u = (t - start) / (1 - start)
            for index, joint in enumerate(joints):
                if u < joint - .045:
                    return {names[index]: 1.}
                if u < joint + .045:
                    blend = smoothstep(joint - .045, joint + .045, u)
                    return {names[index]: 1 - blend, names[index + 1]: blend}
            return {names[2]: 1.}

        stations = [0, .04, .1, .18, .28, .38, .46, .52, .58, .66, .72, .78, .84, .9, .94, .97, .99, 1.]
        segments = 12
        rings, ring_weights = [], []
        for t in stations:
            center, tangent = sample(t)
            up = Vector((0, 0, 1))
            lateral = up.cross(tangent).normalized()
            up = tangent.cross(lateral).normalized()
            u = (t - start) / (1 - start)
            taper = 1 - .2 * max(u, 0)
            swell = 1 + .06 * sum(math.exp(-((u - joint) / .05) ** 2) for joint in joints)
            cap = math.sqrt(max(0., 1 - ((t - .86) / .14) ** 2)) if t > .86 else 1
            cap = max(cap, .08)
            ring = []
            for j in range(segments):
                angle = math.tau * j / segments
                pad = 1 + .1 * max(0., -math.sin(angle))  # fuller pads on the palm side
                ring.append(tuple(center + lateral * (math.cos(angle) * width * taper * swell * cap)
                                  + up * (math.sin(angle) * height * taper * swell * cap * pad)))
            rings.append(ring)
            ring_weights.append(weights(t))
        self.ring_mesh(label, rings, self.m['skin'], ring_weights)
        center, tangent = sample(.885)
        up = Vector((0, 0, 1))
        lateral = up.cross(tangent).normalized()
        up = tangent.cross(lateral).normalized()
        # (lateral, up, tangent) is right-handed for the rings; the nail frame
        # needs (x, y, z) = (-lateral, tangent, up) to stay a proper rotation.
        rotation = Matrix((-lateral, tangent, up)).transposed().to_euler()
        self.ovoid(f'{label} nail', tuple(center + up * (height * .78 * .94)),
                   (width * .62, total * .085, .0011), nail, names[2], tuple(rotation))

    def eye(self, side, sign, width, sclera, rim, iris) -> None:
        """The template eye with a realistic opening: lids cover the top and bottom of the iris.

        The iris is larger than the template's and is clipped to the lid
        opening, so the lids cover its top and bottom like a real eye.
        """
        cx, cz = sign * .053 * width, EYE_LINE
        eye_radius = self.face_shape.eye_width
        upper_lid = self.face_shape.upper_lid + sign * .0003
        lower_lid = self.face_shape.lower_lid + sign * .0002
        pinch = self.face_shape.pinch
        angles = tuple(math.tau * i / 64 for i in range(64))

        def eyelid(angle: float, size: float) -> tuple[float, float]:
            u, w = math.cos(angle), math.sin(angle)
            lid_height = upper_lid if w > 0 else lower_lid
            return cx + eye_radius * size * u, cz + size * (w * lid_height * (1 - pinch * abs(u)) + sign * .0019 * u)

        def bulge(x: float, z: float) -> float:
            horizontal, vertical = (x - cx) / eye_radius, (z - cz) / .0113
            dome = max(0, 1 - horizontal ** 2 - (vertical - sign * .17 * horizontal) ** 2)
            return .0013 + .0058 * dome ** .7  # a shallower globe than the adult's: the eye sits in the socket

        def surface(x: float, z: float) -> float:
            return self.face_y(x, z) - bulge(x, z)

        # The iris and cornea face straight ahead (parallel gaze in both eyes),
        # not along the slope of the face around the eye, and stay in front of the white.
        front = self.face_y(cx, cz)

        def iris_depth(x: float, z: float) -> float:
            return min(front - bulge(x, z) - .0007, surface(x, z) - .0005)

        eye_rings = []
        for size in (1, .85, .68, .52, .35, .13, .015):
            ring = []
            for angle in angles:
                x, z = eyelid(angle, size)
                ring.append((x, surface(x, z) + size ** 5 * .0008, z))
            eye_rings.append(ring)
        self.ring_mesh(f'Eye.{side}', eye_rings, sclera, 'head', cap=False)
        lid_rings = []
        for size, depth in ((1, .0009), (1.105, .0021), (1.25, -.00025), (1.48, -.0011)):
            ring = []
            for angle in angles:
                x, z = eyelid(angle, size)
                # A soft upper lid fold; the lower lid stays nearly flush with the cheek.
                puff = depth if math.sin(angle) > 0 or depth < 0 else depth * .45
                ring.append((x, self.face_y(x, z) - puff - .0012 * max(0, math.sin(angle)), z))
            lid_rings.append(ring)
        lid = self.ring_mesh(f'Eyelids.{side}', lid_rings[::-1], self.m['skin'], 'head', cap=False)
        lid.data.materials.append(rim)
        for face in list(lid.data.polygons)[-len(angles):]:
            face.material_index = 1
        iris_rings, colors = [], []
        for radius, shade in ((.0105, .49), (.0097, .74), (.0088, 1.1), (.0073, 1.02), (.0054, 1.23),
                              (.0045, 1.17), (.0041, .42), (.00395, .07), (.002, .062), (.00009, .063)):
            radius *= self.face_shape.iris_size  # a child's iris fills more of the opening
            ring = []
            for angle in angles:
                x = cx + radius * math.cos(angle)
                z = cz + .81 * radius * math.sin(angle)
                # Clip to the lid opening (just inside the lid margin).
                u = (x - cx) / eye_radius
                middle = cz + sign * .0019 * u
                lid = (upper_lid if z > middle else lower_lid) * (1 - pinch * abs(u))
                limit = lid * math.sqrt(max(0., .94 - u * u))
                z = middle + max(-limit, min(limit, z - middle))
                ring.append((x, iris_depth(x, z), z))
                streak = .76 + .24 * math.sin(19 * angle + 180 * radius) ** 2 + .19 * math.sin(29 * angle - 465 * radius) ** 2
                strength = shade * (streak if radius > .0042 else 1)
                colors.append(tuple(channel * strength for channel in self.spec['iris']))
            iris_rings.append(ring)
        pigment = self.ring_mesh(f'Iris.{side}', iris_rings, iris, f'eye.{side}', cap=False)
        vertex_pigment(pigment, 'Iris pigment', colors)
        # A clear, strongly curved cornea over the iris gives small, crisp catchlights.
        cornea_rings = []
        outer = .0105 * self.face_shape.iris_size * 1.06
        for size in (1, .86, .7, .52, .32, .12, .01):
            ring = []
            for angle in angles:
                x = cx + outer * size * math.cos(angle)
                z = cz + .81 * outer * size * math.sin(angle)
                u = (x - cx) / eye_radius
                middle = cz + sign * .0019 * u
                lid = (upper_lid if z > middle else lower_lid) * (1 - pinch * abs(u))
                limit = lid * math.sqrt(max(0., .97 - u * u))
                z = middle + max(-limit, min(limit, z - middle))
                ring.append((x, iris_depth(x, z) - .0002 - .0022 * (1 - size * size), z))
            cornea_rings.append(ring)
        cornea = self.ring_mesh(f'Cornea.{side}', cornea_rings, self.cornea_material(), f'eye.{side}', cap=False)
        cornea.visible_shadow = False
        self.lashes(side, sign, eyelid, angles)

    def cornea_material(self) -> bpy.types.Material:
        """Fresnel-weighted clear gloss: reflections without refraction, so the iris stays sharp."""
        name = f'{self.name} • Cornea'
        if name in bpy.data.materials:
            return bpy.data.materials[name]
        material = bpy.data.materials.new(name)
        material.use_nodes = True
        material.diffuse_color = (1, 1, 1, .08)
        nodes, links = material.node_tree.nodes, material.node_tree.links
        nodes.clear()
        output = nodes.new('ShaderNodeOutputMaterial')
        output.location = (400, 0)
        clear = nodes.new('ShaderNodeBsdfTransparent')
        clear.location = (0, 120)
        gloss = nodes.new('ShaderNodeBsdfGlossy')
        gloss.location = (0, -60)
        gloss.inputs['Roughness'].default_value = .02
        fresnel = nodes.new('ShaderNodeFresnel')
        fresnel.location = (0, 260)
        fresnel.inputs['IOR'].default_value = 1.376
        mix = nodes.new('ShaderNodeMixShader')
        mix.location = (200, 0)
        links.new(fresnel.outputs['Fac'], mix.inputs['Fac'])
        links.new(clear.outputs['BSDF'], mix.inputs[1])
        links.new(gloss.outputs['BSDF'], mix.inputs[2])
        links.new(mix.outputs['Shader'], output.inputs['Surface'])
        return material

    def nostril(self, side, sign, nose, material) -> None:
        """Teardrop nostrils under the soft alae: a rim that darkens into the opening.

        The head is one closed surface, so the opening is shaded rather than cut:
        the inner rings use a near-black material.  The long axis runs from the
        columella out and slightly up toward the nostril wing; the inner end is
        narrower.
        """
        rings = []
        lean = math.radians(18)
        for size in (1, .8, .58, .34, .05):
            ring = []
            for step in range(24):
                angle = math.tau * step / 24
                u, w = math.cos(angle), math.sin(angle)
                along = .0066 * u * size
                across = .0032 * w * size * (1 + .22 * u)
                x = sign * (.0150 + along * math.cos(lean) - across * math.sin(lean)) * nose
                z = 1.6056 + along * math.sin(lean) + across * math.cos(lean)
                # Clear of the head's flat facets, which cut across the curve under the nose.
                ring.append((x, self.face_y(x, z) - .0009 - .0002 * (1 - size), z))
            rings.append(ring if sign == 1 else ring[::-1])
        hole = self.ring_mesh(f'Nostril.{side}', rings, material, 'head', cap=False)
        opening = self.mat('Nostril opening', tuple(v * .07 for v in self.spec['skin']), .8)
        hole.data.materials.append(opening)
        for face in list(hole.data.polygons)[24:]:
            face.material_index = 1

    def ear(self, side, sign, width, skin, inner) -> None:
        """An anatomical ear: helix rim, scapha, antihelix, concha, tragus and a soft lobe.

        It lies along the side of the head, facing out, leaning back a little
        and flaring about 25 degrees from the skull toward its back edge.  The
        back of the ear runs into the skull so there is no gap behind it.
        """
        tilt = math.radians(14)
        up = (math.sin(tilt), math.cos(tilt))      # (y, z): the long axis leans back
        back = (math.cos(tilt), -math.sin(tilt))
        root_y, root_z = .004, 1.646               # concha centre, design space
        angles = tuple(math.tau * i / 48 for i in range(48))

        def side_x(y: float, z: float) -> float:
            center, radius, depth = profile_at(z)
            return width * radius * math.sqrt(max(0., 1 - ((y - center) / depth) ** 2))

        def outline(theta: float) -> tuple[float, float]:
            c, s = math.cos(theta), math.sin(theta)
            p = c * (.023 if c > 0 else .012) * (1 - .3 * smoothstep(-.4, -1., s))  # the lobe narrows
            return p, s * (.040 if s > 0 else .034)

        def window(degrees: float, start: float, end: float, soft: float = 18) -> float:
            return smoothstep(start - soft, start + soft, degrees) * (1 - smoothstep(end - soft, end + soft, degrees))

        def flare(p: float, q: float) -> float:
            return .0025 + .5 * max(0., p + .010) + .08 * max(0., q)

        def relief(size: float, theta: float) -> float:
            d = math.degrees(math.remainder(theta, math.tau))
            helix = .0029 * math.exp(-((size - .955) / .045) ** 2) * window(d, -80, 160)
            scapha = -.0021 * math.exp(-((size - .80) / .055) ** 2) * window(d, -60, 140)
            antihelix = .0034 * math.exp(-((size - .62) / .085) ** 2) * window(d, -55, 120)
            concha = -.0068 * max(0., 1 - (size / .5) ** 2) * (1 - .45 * window(d, 40, 140, 30))
            tragus = .0042 * math.exp(-((size - .78) / .16) ** 2) * math.exp(-((abs(d) - 180) / 22) ** 2)
            antitragus = .0022 * math.exp(-((size - .58) / .1) ** 2) * math.exp(-((d + 110) / 18) ** 2)
            lobe = .0012 * smoothstep(-.6, -1., math.sin(theta)) * (1 - size)
            return helix + scapha + antihelix + concha + tragus + antitragus + lobe

        def point(size: float, theta: float, outward: float) -> tuple[float, float, float]:
            p, q = outline(theta)
            p, q = p * size, q * size
            y = root_y + p * back[0] + q * up[0]
            z = root_z + p * back[1] + q * up[1]
            return sign * (side_x(y, z) + outward), y, z

        rings = []
        for size in (.03, .12, .22, .32, .42, .5, .58, .66, .74, .82, .88, .93, .97, 1.):
            rings.append([point(size, theta, flare(*(v * size for v in outline(theta))) + relief(size, theta))
                          for theta in angles])
        # Rolled rim, then the back of the ear running into the skull.
        for size, amount, inset in ((1.025, .93, .0004), (1., .84, -.0012), (.9, .6, -.0022),
                                    (.75, .3, -.003), (.6, 0., -.004)):
            rings.append([point(size, theta, flare(*(v * size for v in outline(theta))) * amount + inset)
                          for theta in angles])
        rings = [ring if sign == 1 else ring[::-1] for ring in rings]
        ear = self.ring_mesh(f'Ear.{side}', rings, skin, 'head')
        ear.data.materials.append(inner)
        polygons = ear.data.polygons
        for face in list(polygons[:4 * len(angles)]) + [polygons[len(polygons) - 2]]:
            face.material_index = 1  # the concha

    def lashes(self, side: str, sign: int, eyelid, angles: Sequence[float]) -> None:
        """Fine tapered lashes on the lid margin: long and curled above, short below."""
        verts: list[Vector] = []
        faces: list[tuple[int, int, int, int]] = []
        length = self.face_shape.lash_length
        for index, angle in enumerate(math.tau * i / 96 for i in range(96)):
            upper = math.sin(angle) > 0
            u = math.cos(angle)
            if abs(math.sin(angle)) < .12 or (not upper and (index % 3 or sign * u < -.2)):
                continue
            outer = max(0., sign * u)  # longer and flared toward the outer corner
            x, z = eyelid(angle, 1.02)
            root = Vector((x, self.face_y(x, z) - .0011, z))
            size = (length * (.62 + .5 * outer) * (1 - .25 * abs(u) ** 3) if upper else length * .26)
            lift = 1 if upper else -1
            spine = [root + Vector((sign * outer * size * .35 * t, -size * (.55 * t + .25 * t * t),
                                    lift * size * (.18 * t + .62 * t * t))) for t in (0, .33, .66, 1)]
            for ring_index, point in enumerate(spine):
                radius = (.00019 if upper else .00011) * (1 - .8 * ring_index / 3)
                for k in range(3):
                    a = math.tau * k / 3
                    verts.append(point + Vector((math.cos(a) * radius, 0, math.sin(a) * radius)))
            start = len(verts) - 12
            for ring_index in range(3):
                for k in range(3):
                    a, b = start + ring_index * 3, start + (ring_index + 1) * 3
                    faces.append((a + k, a + (k + 1) % 3, b + (k + 1) % 3, b + k))
        lash = self.mat('Lashes', tuple(v * .6 for v in self.spec['hair']), .62)
        lash.node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value = .22
        self.mesh(f'Lashes.{side}', [tuple(v) for v in verts], faces, lash, 'head')

    def brow_point(self, sign: int, t: float) -> tuple[float, float]:
        """Design-space (x, z) on the soft, low child brow: t = 0 inner end, 1 outer tail."""
        x = sign * (.053 * self.width - .031 + .066 * t)
        z = 1.7045 + .0078 * math.sin(math.pi * min(1., t * 1.1)) ** 1.1 - .0025 * t
        return x, z

    def face(self) -> None:
        super().face()
        # The brow base is a thin, flat band of tint; the strand groom draws the hairs.
        brow_tint = self.mat('Brow', tuple(h * .72 + s * .28 for h, s in zip(self.spec['hair'], self.spec['skin'])), .92)
        for side, sign in (('L', 1), ('R', -1)):
            self.remove_part(f'Brow.{side}')
            points, radii = [], []
            for step in range(9):
                t = step / 8
                x, z = self.brow_point(sign, t)
                points.append((x, self.face_y(x, z) + .0029, z))
                radii.append(.0030 * math.sin(math.pi * (.06 + .86 * t)) ** .5 + .0006)
            self.tube(f'Brow.{side}', points, radii, brow_tint, 'head')
        mouth = self.part('Mouth')
        keys = mouth.data.shape_keys.key_blocks
        for key in keys:
            if key.name != 'Basis':  # the base class writes these in design space
                for vertex in key.data:
                    vertex.co = self.place(vertex.co.copy(), {'head': 1.})
        # Rest mouth: lips closed with a small natural upturn at the corners.
        basis = keys['Basis'].data
        segments = len(basis) // 4
        inner = [basis[i].co for i in range(2 * segments, 3 * segments)]
        middle_z = sum(co.z for co in inner) / segments
        center_x = sum(co.x for co in inner) / segments
        half = max(abs(co.x - center_x) for co in inner)
        for index, item in enumerate(basis):
            point = item.co.copy()
            if index >= 2 * segments:
                point.z = middle_z + (point.z - middle_z) * .12
            point.z += self.face_shape.smile * min(1., abs(point.x - center_x) / half) ** 2
            item.co = point
            mouth.data.vertices[index].co = point
        # Rosier lips than the adult template.
        pigment = mouth.data.color_attributes['Lip pigment']
        for index, item in enumerate(pigment.data):
            if segments <= index < 3 * segments:
                r, g, b, a = item.color
                item.color = (r * 1.12, g * 1.0, b * 1.07, a)
        for label, weight, glossy in (('Iris', 0., .03), ('Eye white', .35, .2)):  # the cornea adds the sharp gloss
            shader = bpy.data.materials[f'{self.name} • {label}'].node_tree.nodes.get('Principled BSDF')
            shader.inputs['Coat Weight'].default_value = weight
            shader.inputs['Coat Roughness'].default_value = glossy
            shader.inputs['Coat IOR'].default_value = 1.376
        nostril = bpy.data.materials[f'{self.name} • Nostril shadow']
        tint = (*[v * f for v, f in zip(self.spec['skin'], (.30, .17, .16))], 1)
        nostril.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = tint
        nostril.diffuse_color = tint
        self.blush()
        self.soften_skin()

    def blush(self) -> None:
        """Warm cheeks and nose tip via a 'Blush' attribute on the head's own skin material."""
        head = self.part('Head')
        values = []
        for point in self.design[head.name]:
            cheeks = .8 * gaussian(abs(point.x), point.z, .060 * self.width, 1.626, .038, .032) * (point.y < -.02)
            tip = .5 * gaussian(point.x, point.z, 0, 1.622, .016, .014) * (point.y < -.05)
            values.append(min(1., cheeks + tip))
        layer = head.data.attributes.new('Blush', 'FLOAT', 'POINT')
        layer.data.foreach_set('value', values)
        face_skin = self.m['skin'].copy()
        face_skin.name = f'{self.name} • Face skin'
        tree = face_skin.node_tree
        shader = tree.nodes.get('Principled BSDF')
        source = shader.inputs['Base Color'].links[0].from_socket
        amount = tree.nodes.new('ShaderNodeAttribute')
        amount.attribute_name = 'Blush'
        amount.attribute_type = 'GEOMETRY'
        amount.location = (-130, 420)
        rosy = tree.nodes.new('ShaderNodeMix')
        rosy.data_type = 'RGBA'
        rosy.blend_type = 'MULTIPLY'
        rosy.label = 'Rosy cheeks'
        rosy.location = (300, 380)
        rosy.inputs['B'].default_value = (1.08, .88, .86, 1)
        tree.links.new(amount.outputs['Fac'], rosy.inputs['Factor'])
        tree.links.new(source, rosy.inputs['A'])
        tree.links.new(rosy.outputs['Result'], shader.inputs['Base Color'])
        head.data.materials[0] = face_skin
        for side in ('L', 'R'):  # the lids share the face shading so they don't read as patches
            self.part(f'Eyelids.{side}').data.materials[0] = face_skin

    def soften_skin(self) -> None:
        """A child's skin: finer, shallower pores and a little more subsurface light."""
        for material in (self.m['skin'], bpy.data.materials[f'{self.name} • Face skin']):
            for node in material.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    node.inputs['Subsurface Weight'].default_value = .07
                elif node.type == 'TEX_VORONOI':
                    node.inputs['Scale'].default_value = 1500
                elif node.type == 'BUMP':
                    node.inputs['Strength'].default_value = .11

    def smooth_render(self, labels: Sequence[str], levels: int = 2) -> None:
        """Render-time subdivision after skinning for the coarse body and garment meshes.

        FBX export skips modifiers, so the interchange meshes are unchanged.
        """
        for part in self.parts:
            label = part.name.removeprefix(f'{self.name}_')
            if any(label.startswith(prefix) for prefix in labels):
                smooth = part.modifiers.new('Render smoothing', 'SUBSURF')
                smooth.levels = 1
                smooth.render_levels = levels
                smooth.boundary_smooth = 'PRESERVE_CORNERS'

    def design_head(self):
        """BVH of the unwarped head surface, for grooming in design space."""
        from mathutils.bvhtree import BVHTree
        head = self.part('Head')
        return BVHTree.FromPolygons(self.design[head.name], [tuple(f.vertices) for f in head.data.polygons])

    def child_point(self, point: Point, bone: str = 'head') -> Vector:
        return self.place(Vector(point), {bone: 1.})


# ---------------------------------------------------------------- face rig
def add_child_facial_controls(c: ChildCharacter) -> None:
    """Facial custom properties matching the adult cast, scaled to the child head."""
    rig = c.rig
    sx, sy, sz = c.proportions.head
    mouth = c.part('Mouth')
    keys = mouth.data.shape_keys.key_blocks
    basis = keys['Basis']
    for name, sources in {'Mouth_U': {'Mouth_O': .9}, 'Mouth_L': {'Mouth_Ah': .58, 'Mouth_Ee': .15},
                          'Mouth_Consonant': {'Mouth_Ee': .32, 'Mouth_Ah': .10}}.items():
        key = mouth.shape_key_add(name=name)
        center_x = sum(v.co.x for v in basis.data) / len(basis.data)
        for index, item in enumerate(key.data):
            point = basis.data[index].co.copy()
            for source, amount in sources.items():
                point += (keys[source].data[index].co - basis.data[index].co) * amount
            if name == 'Mouth_U':
                point.x = center_x + (point.x - center_x) * .78
            item.co = point
    for name in MOUTH_KEYS:
        property_control(rig, name, f'Viseme control: {name}')
        keys[name].value = 0
        driver_from_property(keys[name], rig, name)
    for name in ('blink_L', 'blink_R', 'brow_raise', 'brow_frown', 'mouth_worry', 'mouth_smile'):
        property_control(rig, name, name.replace('_', ' '))
    for side, sign in (('L', 1), ('R', -1)):
        center = c.child_point((sign * .053 * c.width, -.12, EYE_LINE))
        for label in ('Eye', 'Iris', 'Cornea', 'Eyelids', 'Lashes'):
            obj = c.part(f'{label}.{side}')

            def blink(point: Vector, eyelid: bool = label in ('Eyelids', 'Lashes')) -> Vector:
                point.z = center.z + (point.z - center.z) * .035
                point.y += (-.003 if eyelid else .028) * sy
                return point
            driver_from_property(shape_from_delta(obj, 'Blink', blink), rig, f'blink_{side}')
        brow = c.part(f'Brow.{side}')
        for name, delta, control in (('Raise', .0065, 'brow_raise'), ('Frown', -.005, 'brow_frown')):
            def reshape(point: Vector, amount: float = delta) -> Vector:
                point.z += amount * sz * max(.25, 1 - abs(point.x) / (.11 * sx))
                return point
            driver_from_property(shape_from_delta(brow, name, reshape), rig, control)
            if side == 'L':  # the brow hairs follow the same shapes (both sides in one mesh)
                driver_from_property(shape_from_delta(c.part('Facial groom fibers'), name, reshape), rig, control)
    half_width = max(abs(v.co.x) for v in basis.data)
    for name, direction, control in (('Worry', -1, 'mouth_worry'), ('Smile', 1, 'mouth_smile')):
        def corners(point: Vector, sign: int = direction) -> Vector:
            point.z += sign * .004 * sz * min(1., abs(point.x) / half_width) ** 2
            return point
        driver_from_property(shape_from_delta(mouth, name, corners), rig, control)
    teeth = c.mat('Milk teeth', (.70, .66, .56), .42)
    tongue = c.mat('Tongue', (.24, .065, .058), .63)
    for label, center, size, material, control in (
            ('Upper teeth', (0, -.128, 1.576), (.022, .003, .0035), teeth, 'Mouth_Ah'),
            ('Tongue', (0, -.127, 1.553), (.016, .003, .003), tongue, 'Mouth_L')):
        obj = c.ovoid(label, center, size, material, 'head')
        hide = Vector((0, .035 * sy, 0))
        for vertex in obj.data.vertices:
            vertex.co += hide
        key = shape_from_delta(obj, 'Show', lambda point: point - hide)
        driver_from_property(key, rig, control, 'min(1,value*2.0)')
    rig['Facial_controls'] = ('Custom Properties: eight speech shapes, two blinks, brows, worry and smile. '
                              'Eye bones control gaze.')


# ------------------------------------------------------------------- poses
Rotation = tuple[tuple[float, float, float], float]


@dataclass(frozen=True)
class Pose:
    """A pose: aimed limb directions in armature space, then local turns.

    `aims` points a bone along an armature-space direction and, optionally,
    turns it about that direction so the palm faces a given direction (the
    palm faces -Z in the rest T-pose).  `turns` rotates a bone about
    rest-frame axes relative to its parent, like `build_cast.turn`.
    """
    name: str
    aims: Mapping[str, tuple[Point, Point | None]] = field(default_factory=dict)
    turns: Mapping[str, Sequence[Rotation]] = field(default_factory=dict)
    note: str = ''


def _depth(bone) -> int:
    return 0 if bone.parent is None else 1 + _depth(bone.parent)


def reset_pose(rig) -> None:
    for bone in rig.pose.bones:
        bone.rotation_mode = 'QUATERNION'
        bone.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()


def apply_pose(rig, pose: Pose) -> None:
    reset_pose(rig)
    names = set(pose.aims) | set(pose.turns)
    for bone in sorted((rig.pose.bones[name] for name in names), key=_depth):
        rest = bone.bone.matrix_local.to_quaternion()
        local = Quaternion()
        for axis, degrees in pose.turns.get(bone.name, ()):
            local = rest.inverted() @ Quaternion(axis, math.radians(degrees)) @ rest @ local
        bone.rotation_quaternion = local
        if bone.name in pose.aims:
            bpy.context.view_layer.update()
            direction, palm = pose.aims[bone.name]
            current = bone.matrix.copy()
            target = Vector(direction).normalized()
            swing = current.col[1].xyz.normalized().rotation_difference(target)
            rotation = swing.to_matrix() @ current.to_3x3().normalized()
            if palm is not None:
                rest_palm = bone.bone.matrix_local.to_3x3().inverted() @ Vector((0, 0, -1))
                have = rotation @ rest_palm
                have -= target * target.dot(have)
                want = Vector(palm) - target * target.dot(Vector(palm))
                if have.length > 1e-6 and want.length > 1e-6:
                    have.normalize()
                    want.normalize()
                    angle = have.angle(want)
                    if have.cross(want).dot(target) < 0:
                        angle = -angle
                    rotation = Quaternion(target, angle).to_matrix() @ rotation
            matrix = rotation.to_4x4()
            matrix.translation = current.translation
            bone.matrix = matrix
        bpy.context.view_layer.update()


def save_pose_asset(rig, pose: Pose, character: str) -> bpy.types.Action:
    """Store the current pose as a Pose Library asset (an action marked as asset)."""
    rig.animation_data_create()
    rig.animation_data.action = None
    for bone in rig.pose.bones:
        bone.keyframe_insert('rotation_quaternion', frame=1, group=bone.name)
        bone.keyframe_insert('location', frame=1, group=bone.name)
    action = rig.animation_data.action
    action.name = f'{character} pose | {pose.name}'
    action.use_fake_user = True
    action.asset_mark()
    action.asset_data.description = pose.note or pose.name
    action.asset_data.tags.new(character)
    rig.animation_data.action = None
    return action

