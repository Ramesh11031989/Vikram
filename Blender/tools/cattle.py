"""गाय — the Halwai's neighbour's cow, the animal she frees by cutting its tether.

A Malvi-type zebu cow (the native breed of the Malwa plateau around Ujjain; the
breed is a guess, the chapter only says "गाय"): silver-grey coat darkening on the
neck, hump and lower legs, small hump, moderate dewlap, short lyre horns,
black switch, dark muzzle and eye rims.

Built at real scale in metres so the tether, her hands and the sickle can be
checked against it: 1.18 m at the withers, about 1.40 m from the point of the
shoulder to the pin bone.

The body, neck, head and legs are one signed-distance sculpt (sdf_sculpt, the
same engine as the realistic cast heads), so muscles, joints and bones blend
into each other like a real animal instead of reading as separate parts.
Horns, ears, hooves, eyes, lashes and the tail switch are separate meshes. One
armature with a 29-bone quadruped skeleton deforms everything (FBX-friendly).
"""

from __future__ import annotations

import math
import random
from typing import Callable, Dict, List, Sequence, Tuple

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from character import Character
from groom import FiberGroup
from sdf_sculpt import Sculpt, capsule, ellipsoid, sphere, surface_nets, taubin

Array = np.ndarray
Weight = Dict[str, float]
Point = Tuple[float, float, float]
Bounds = Tuple[Sequence[float], Sequence[float]]
Shape = Tuple[Callable[[Array, Array, Array], Array], Bounds]


def smooth(a: float, b: float, x):
    t = np.clip((x - a)/(b - a), 0, 1)
    return t*t*(3 - 2*t)


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


def sampled(table: Sequence[Tuple[float, float]], lo: float, hi: float, count: int = 600) -> Callable[[Array], Array]:
    """The Catmull-Rom curve as a fast numpy lookup."""
    xs = np.linspace(lo, hi, count)
    ys = np.array([curve(table, float(x)) for x in xs])
    return lambda x: np.interp(x, xs, ys)


# ------------------------------------------------------------------ anatomy

WITHERS = 1.18
# Barrel: y (rear +, front -) -> spine height, belly height, half width
TOP = ((.77,1.00), (.69,1.13), (.50,1.195), (.30,1.165), (.10,1.142), (-.10,1.145), (-.26,1.175),
       (-.37,1.240), (-.46,1.236), (-.55,1.13), (-.60,1.03))
BOTTOM = ((.77,.82), (.67,.74), (.52,.64), (.34,.555), (.10,.505), (-.15,.515), (-.35,.560),
          (-.50,.600), (-.58,.680), (-.61,.80))
WIDTH = ((.77,.07), (.71,.17), (.58,.222), (.46,.243), (.30,.256), (.10,.272), (-.10,.266),
         (-.28,.232), (-.42,.205), (-.53,.170), (-.61,.10))

# Neck: y, centre z, half width, height above centre, depth below centre
NECK = ((-.50,.93,.170,.30,.31), (-.62,.955,.142,.225,.235), (-.73,.99,.118,.160,.180),
        (-.83,1.03,.098,.118,.155), (-.90,1.07,.088,.095,.125), (-.95,1.085,.080,.080,.110))
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
EYE_R = .0172
STEP = .003               # voxel size of the body sculpt


def head_frame() -> Tuple[Vector, Vector, Vector]:
    axis = (HEAD_END-HEAD_START).normalized()
    side = Vector((1, 0, 0))
    dorsal = axis.cross(side).normalized()
    return axis, side, dorsal


HEAD_LENGTH = (HEAD_END - HEAD_START).length


def head_point(s: float, x: float, d: float) -> Vector:
    axis, side, dorsal = head_frame()
    return HEAD_START + (HEAD_END-HEAD_START)*s + side*x + dorsal*d


def hp(s: float, x: float, d: float) -> Point:
    return tuple(head_point(s, x, d))


def eye_centre(sign: int) -> Vector:
    return head_point(.25, sign*.0985, .020)


def eye_axis(sign: int) -> Vector:
    return Vector((sign*.92, -.20, .22)).normalized()


# ------------------------------------------------------------ sculpt fields

def squashed(shape: Shape, sx: float) -> Shape:
    """A shape flattened across x (an approximate distance, fine for blending)."""
    field, (lo, hi) = shape

    def flat(x, y, z):
        return field(x/sx, y, z)*sx
    return flat, ((lo[0]*sx, lo[1], lo[2]), (hi[0]*sx, hi[1], hi[2]))


def barrel() -> Shape:
    top, bottom, width = sampled(TOP, -.61, .77), sampled(BOTTOM, -.61, .77), sampled(WIDTH, -.61, .77)

    def field(x, y, z):
        t, b, w = top(y), bottom(y), width(y)
        zc, h = (t + b)/2, (t - b)/2
        v = (z - zc)/h
        upper = np.clip(v, 0, 1)
        w = w*(1 - .16*upper**2)                     # the back narrows to the spine
        u = x/w
        n = np.where(v > 0, 2.6, 2.1)                # a boxy back over a rounder belly
        r = (np.abs(u)**n + np.abs(v)**n)**(1/n)
        d = (r - 1)*np.minimum(w, h)
        return np.maximum(d, np.maximum(-.61 - y, y - .77))
    return field, ((-.30, -.62, .48), (.30, .78, 1.26))


def neck() -> Shape:
    rows = sorted(NECK)
    ys = [r[0] for r in rows]
    centre, half, up, down = (sampled([(r[0], r[k]) for r in rows], ys[0], ys[-1]) for k in (1, 2, 3, 4))

    def field(x, y, z):
        zc, w, a, b = centre(y), half(y), up(y), down(y)
        v = np.where(z > zc, (z - zc)/a, (z - zc)/b)
        w = w*(1 - .28*np.clip(v, 0, 1)**3)          # narrower crest
        u = x/w
        r = np.sqrt(u*u + v*v)
        d = (r - 1)*np.minimum(w, np.where(z > zc, a, b))
        return np.maximum(d, np.maximum(ys[0] - y, y - (ys[-1] + .02)))
    return field, ((-.18, ys[0] - .01, .60), (.18, ys[-1] + .03, 1.26))


def head_loft() -> Shape:
    axis, side, dorsal = head_frame()
    width, up, down = (sampled([(row[0], row[k]) for row in HEAD], 0, 1) for k in (1, 2, 3))
    a = np.array(axis)
    dv = np.array(dorsal)
    o = np.array(HEAD_START)

    def field(x, y, z):
        px, py, pz = x - o[0], y - o[1], z - o[2]
        s = (px*a[0] + py*a[1] + pz*a[2])/HEAD_LENGTH
        d = px*dv[0] + py*dv[1] + pz*dv[2]
        sc = np.clip(s, 0, 1)
        w, u_, l_ = width(sc), up(sc), down(sc)
        v = np.where(d > 0, d/u_, d/l_)
        w = w*(1 - .10*np.clip(-v, 0, 1)**2)        # jaw narrower than the cheekbones
        u = x/w
        n = np.where(d > 0, 2.4, 2.0)               # flat forehead, round jaw
        r = (np.abs(u)**n + np.abs(v)**n)**(1/n)
        dist = (r - 1)*np.minimum(w, np.where(d > 0, u_, l_))
        ends = np.maximum(-.02 - s, s - 1.0)*HEAD_LENGTH
        return np.maximum(dist, ends)
    lo = np.minimum(np.array(HEAD_START), np.array(HEAD_END)) - .19
    hi = np.maximum(np.array(HEAD_START), np.array(HEAD_END)) + .19
    return field, (tuple(lo), tuple(hi))


def spine_ridge() -> Shape:
    """The backbone just under the skin along the topline, from behind the hump to the hips."""
    top = sampled(TOP, -.61, .77)

    def field(x, y, z):
        ridge = np.sqrt(x*x + (z - (top(y) - .004))**2) - .015
        return np.maximum(ridge, np.maximum(-.30 - y, y - .50))
    return field, ((-.05, -.32, 1.05), (.05, .52, 1.27))


def eye_opening(sign: int) -> Shape:
    """Almond opening of the lids around the eye axis (angular field in front of the eyeball)."""
    centre = np.array(eye_centre(sign))
    out = np.array(eye_axis(sign))
    up = np.array((0, 0, 1.0)) - out*out[2]
    up /= np.linalg.norm(up)
    across = np.cross(up, out)

    def field(x, y, z):
        px, py, pz = x - centre[0], y - centre[1], z - centre[2]
        f = px*out[0] + py*out[1] + pz*out[2]
        a = px*across[0] + py*across[1] + pz*across[2]
        b = px*up[0] + py*up[1] + pz*up[2]
        r = np.sqrt(px*px + py*py + pz*pz)
        ang_a = np.degrees(np.arctan2(a, np.maximum(f, 1e-6)))
        ang_b = np.degrees(np.arctan2(b, np.maximum(f, 1e-6)))
        almond = np.sqrt((ang_a/50.0)**2 + (np.where(ang_b > 0, ang_b/30.0, ang_b/24.0))**2) - 1
        angular = np.radians(almond*40)*np.maximum(r, .004)
        return np.maximum(np.maximum(angular, -f), r - (EYE_R + .012))
    reach = EYE_R + .014
    return field, (tuple(centre - reach), tuple(centre + reach))


def mouth_line() -> Shape:
    axis, side, dorsal = head_frame()
    a, dv, o = np.array(axis), np.array(dorsal), np.array(HEAD_START)

    def field(x, y, z):
        px, py, pz = x - o[0], y - o[1], z - o[2]
        s = (px*a[0] + py*a[1] + pz*a[2])/HEAD_LENGTH
        d = px*dv[0] + py*dv[1] + pz*dv[2]
        line = -.047 - .010*smooth(.95, .80, s)          # the gape rises toward the front
        slab = np.abs(d - line) - .0018
        return np.maximum(slab, np.maximum(.80 - s, -1.0))
    lo = np.array(head_point(.78, -.09, -.08)) - .03
    hi = np.array(head_point(1.02, .09, -.02)) + .03
    return field, (tuple(np.minimum(lo, hi)), tuple(np.maximum(lo, hi)))


def leg_shapes(sculpt: Sculpt, sign: int) -> None:
    f = [Vector((sign*p.x, p.y, p.z)) for p in FRONT_LEG]
    r = [Vector((sign*p.x, p.y, p.z)) for p in REAR_LEG]
    t = tuple
    # Forelimb: triceps and shoulder into the chest, a muscular forearm, bony knee, slim cannon
    sculpt.union(ellipsoid((sign*.180, -.43, .77), (.068, .105, .16)), .07)
    sculpt.union(ellipsoid((sign*.168, -.535, .925), (.040, .055, .060)), .08)          # point of shoulder
    sculpt.union(capsule(t(f[1]), t(f[2]), .056, .036), .035)                            # forearm
    sculpt.union(ellipsoid((sign*.168, -.392, .535), (.050, .058, .095)), .03)           # forearm muscles
    sculpt.union(sphere(t(f[2] + Vector((0, -.004, 0))), .037), .02)                    # knee (carpus)
    sculpt.union(capsule(t(f[2]), t(f[3]), .025, .023), .016)                            # cannon
    sculpt.union(capsule(t(f[2] + Vector((0, .019, -.03))), t(f[3] + Vector((0, .021, .025))), .012, .011), .012)
    sculpt.union(sphere(t(f[3] + Vector((0, .006, 0))), .030), .012)                    # fetlock
    sculpt.union(capsule(t(f[3]), t(f[4] + Vector((0, 0, .008))), .024, .029), .010)     # pastern to coronet
    # Hind limb: heavy thigh and quarter, stifle, gaskin, sharp hock with its tendon
    sculpt.union(ellipsoid((sign*.175, .53, .83), (.090, .175, .23)), .06)
    sculpt.union(ellipsoid((sign*.115, .675, .90), (.080, .100, .17)), .06)              # quarter
    sculpt.union(ellipsoid((sign*.205, .400, .735), (.040, .045, .050)), .06)            # stifle
    sculpt.union(capsule(t(r[1]), t(r[2]), .058, .033), .035)                            # gaskin
    sculpt.union(ellipsoid((sign*.186, .530, .600), (.045, .060, .100)), .03)            # calf muscles
    sculpt.union(sphere(t(r[2]), .034), .018)                                           # hock
    sculpt.union(capsule(t(r[2]), t(r[2] + Vector((0, .045, .045))), .022, .019), .014)  # point of hock
    sculpt.union(capsule((sign*.183, .610, .680), t(r[2] + Vector((0, .040, .040))), .013, .012), .016)  # hamstring
    sculpt.union(capsule(t(r[2]), t(r[3]), .026, .023), .016)                            # cannon
    sculpt.union(capsule(t(r[2] + Vector((0, .018, -.04))), t(r[3] + Vector((0, .021, .025))), .012, .011), .012)
    sculpt.union(sphere(t(r[3] + Vector((0, .006, 0))), .030), .012)                    # fetlock
    sculpt.union(capsule(t(r[3]), t(r[4] + Vector((0, 0, .008))), .024, .029), .010)


def cow_sculpt() -> Sculpt:
    s = Sculpt()
    s.union(barrel())
    s.union(neck(), .07)
    # Skeleton showing through: hump, shoulder blades, spine, hooks and pins, tail head
    s.union(ellipsoid((0, -.415, 1.205), (.075, .115, .068)), .05)                      # hump
    for sign in (1, -1):
        s.union(ellipsoid((sign*.165, -.39, 1.06), (.036, .095, .16), (-22, 0, 0)), .08)   # shoulder blade
        s.union(ellipsoid((sign*.196, .470, 1.118), (.030, .050, .032)), .07)            # hook bone
        s.union(ellipsoid((sign*.095, .705, 1.045), (.026, .036, .026)), .05)            # pin bone
        s.subtract(ellipsoid((sign*.262, .300, 1.035), (.026, .065, .065)), .07)         # paralumbar hollow
    s.union(spine_ridge(), .035)                                                       # spine along the topline
    for sign in (1, -1):                                                                # stifle fold to the belly
        s.union(ellipsoid((sign*.192, .345, .735), (.042, .110, .070), (0, 0, 0)), .08)
    s.union(sphere((0, .745, 1.055), .040), .03)                                       # tail head
    # Dewlap: a soft fold from the throat to the brisket
    for a, b, ra, rb in (((0, -.93, .90), (0, -.84, .80), .040, .060), ((0, -.84, .80), (0, -.72, .70), .060, .070),
                         ((0, -.72, .70), (0, -.60, .62), .070, .055)):
        s.union(squashed(capsule(a, b, ra, rb), .40), .05)
    # Udder and teats
    s.union(ellipsoid((0, .470, .600), (.075, .100, .065)), .035)
    for x in (-.032, .032):
        for y in (.430, .510):
            s.union(capsule((x, y, .565), (x*1.08, y, .500), .0105, .0080), .008)
    # Legs
    for sign in (1, -1):
        leg_shapes(s, sign)
    # Tail, down to the switch
    for i in range(len(TAIL) - 1):
        r0 = .030*(1 - i/4)**.7 + .010
        r1 = .030*(1 - (i + 1)/4)**.7 + .010
        s.union(capsule(tuple(TAIL[i]), tuple(TAIL[i + 1]), r0, r1), .02 if i == 0 else .006)
    # Head
    s.union(head_loft(), .045)
    s.union(ellipsoid(hp(.02, 0, .045), (.062, .030, .032)), .025)                      # poll
    s.union(ellipsoid(hp(.80, 0, .00), (.050, .05, .040)), .03)                         # nasal bridge
    s.union(ellipsoid(hp(.935, 0, -.006), (.066, .045, .060)), .025)                    # muzzle
    s.union(ellipsoid(hp(.905, 0, -.068), (.034, .040, .022)), .02)                     # chin
    s.union(ellipsoid((0, -.94, .925), (.065, .075, .085)), .05)                         # throat latch
    for sign in (1, -1):
        s.union(sphere(hp(.015, sign*.066, .044), .029), .02)                           # horn base
        s.union(ellipsoid(hp(.36, sign*.072, -.078), (.030, .085, .060)), .035)         # masseter
        s.union(capsule(hp(.12, sign*.058, -.140), hp(.86, sign*.032, -.068), .016, .012), .03)  # jaw line
        s.union(sphere(hp(.255, sign*.090, .016), .030), .022)                          # orbit
        s.union(capsule(hp(.20, sign*.080, .055), hp(.30, sign*.094, .040), .012, .010), .02)    # brow over the eye
        s.union(sphere(hp(.965, sign*.034, .016), .017), .010)                          # nostril wing
        s.subtract(ellipsoid(hp(.985, sign*.030, .010), (.0095, .022, .015), (0, 0, sign*-25)), .004)  # nostril
        s.subtract(capsule(hp(.90, sign*.050, .030), hp(.97, sign*.046, -.005), .002, .002), .006)   # nostril groove
        # eye: lids around the eyeball, the opening between them
        centre = tuple(eye_centre(sign))
        s.union(sphere(centre, EYE_R + .0048), .008)
        s.subtract(sphere(centre, EYE_R + .0004), .0008)
        s.subtract(eye_opening(sign), .0012)
    s.subtract(mouth_line(), .0015)
    return s


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

    HAIR_GROUPS = ('Coat density',)       # vertex groups that drive the hair, not bones

    def validate(self):
        """Character.validate, except that the coat-hair density group is neither a bone nor a skin weight."""
        names = set(self.rig.data.bones.keys())
        for obj in self.parts:
            if not len(obj.data.vertices):
                raise ValueError(f'Empty mesh {obj.name}')
            skip = {g.index for g in obj.vertex_groups if g.name in self.HAIR_GROUPS}
            for group in obj.vertex_groups:
                if group.index not in skip and group.name not in names:
                    raise ValueError(f'{obj.name} refers to nonexistent bone {group.name}')
            for vertex in obj.data.vertices:
                if abs(sum(item.weight for item in vertex.groups if item.group not in skip) - 1) > .0001:
                    raise ValueError(f'{obj.name} has invalid weights at vertex {vertex.index}')

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
        bone('jaw', head_point(.18, 0, -.06), head_point(.90, 0, -.07), 'head')
        for side, sign in (('L',1), ('R',-1)):
            base = head_point(.06, sign*.082, -.012)
            bone(f'ear.{side}', base, base + Vector((sign*.17, .05, -.07)), 'head')
            centre = eye_centre(sign)
            bone(f'eye.{side}', centre, centre + eye_axis(sign)*.04, 'head')
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
        rig['Usage'] = ('Quadruped FK skeleton. neck_2 carries the tether loop; jaw opens the mouth; '
                        'tail and ears are free for secondary motion.')
        return rig


# ------------------------------------------------------------------ weights

def chain_weights(p: Array, joints: Sequence[Vector], names: Sequence[str], parent: str) -> Dict[str, Array]:
    """Weight along a limb chain by projected position, blending around each joint (vectorised)."""
    j = np.array([tuple(v) for v in joints])
    best_d = np.full(len(p), np.inf)
    best_i = np.zeros(len(p), dtype=int)
    best_t = np.zeros(len(p))
    for i in range(len(j) - 1):
        a, ab = j[i], j[i + 1] - j[i]
        t = np.clip(((p - a) @ ab)/(ab @ ab), 0, 1)
        d = np.linalg.norm(a + t[:, None]*ab - p, axis=1)
        closer = d < best_d
        best_d[closer], best_i[closer], best_t[closer] = d[closer], i, t[closer]
    out: Dict[str, Array] = {name: np.zeros(len(p)) for name in (*names, parent)}
    for i, name in enumerate(names):
        here = best_i == i
        length = np.linalg.norm(j[i + 1] - j[i])
        blend = min(.45, .05/length)
        t = best_t[here]
        w_self = np.ones(len(t))
        share_prev = np.where(t < blend, .5*(1 - t/blend), 0)
        share_next = np.where((t > 1 - blend) & (i + 1 < len(names)), .5*(1 - (1 - t)/blend), 0)
        w_self -= share_prev + share_next
        out[name][here] += w_self
        out[names[i - 1] if i > 0 else parent][here] += share_prev
        if i + 1 < len(names):
            out[names[i + 1]][here] += share_next
    return out


def cow_weights(p: Array) -> Dict[str, Array]:
    """Skin weights for every vertex of the sculpted body: trunk, neck, head, jaw, legs and tail."""
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    n = len(p)
    w: Dict[str, Array] = {}

    def add(name: str, values: Array) -> None:
        w[name] = w.get(name, np.zeros(n)) + values

    # head (with the lower jaw separate below the mouth line), from the head's own frame
    axis, side_v, dorsal = head_frame()
    rel = p - np.array(HEAD_START)
    s = rel @ np.array(axis)/HEAD_LENGTH
    d = rel @ np.array(dorsal)
    head_zone = smooth(-.03, .06, s)*smooth(-.24, -.18, d)
    jaw = head_zone*smooth(.25, .42, s)*smooth(-.040, -.056, d)
    head = head_zone - jaw
    # trunk and neck along the spine
    pelvis = smooth(.10, .40, y)
    chest = 1 - smooth(-.40, -.08, y)
    spine = np.clip(1 - pelvis - chest, 0, 1)
    neck_zone = smooth(-.46, -.58, y)
    neck1 = neck_zone*(1 - smooth(-.68, -.80, y))
    neck2 = neck_zone - neck1
    trunk = {'pelvis': pelvis, 'spine': spine, 'chest': chest*(1 - neck_zone), 'neck_1': neck1, 'neck_2': neck2}
    # limbs: how much of each vertex belongs to a leg rather than the trunk
    udder = smooth(.68, .62, z)*smooth(.12, .08, np.abs(x))*smooth(.17, .12, np.abs(y - .47))
    limb = np.zeros(n)
    limb_weights: List[Dict[str, Array]] = []
    for sign, side in ((1, 'L'), (-1, 'R')):
        for joints, names, parent, top_z, centre_y, y_reach in (
                (FRONT_LEG, (f'upper_arm.{side}', f'forearm.{side}', f'front_cannon.{side}', f'front_pastern.{side}'),
                 'chest', .70, -.41, .13),
                (REAR_LEG, (f'thigh.{side}', f'shin.{side}', f'rear_cannon.{side}', f'rear_pastern.{side}'),
                 'pelvis', .78, .52, .17)):
            mirrored = [Vector((sign*v.x, v.y, v.z)) for v in joints]
            on_side = smooth(.02, .09, sign*x)
            near = smooth(y_reach + .06, y_reach, np.abs(y - centre_y))
            share = on_side*near*smooth(top_z + .14, top_z - .06, z)*(1 - udder)
            chain = chain_weights(p, mirrored, names, parent)
            limb_weights.append({k: v*share for k, v in chain.items()})
            limb = limb + share
    limb = np.clip(limb, 0, 1)
    # tail behind the buttocks
    tail_names = [f'tail_{i+1}' for i in range(4)]
    tail_axis = np.array([tuple(v) for v in TAIL])
    tail_d = np.min([np.linalg.norm(p - q, axis=1) for q in tail_axis], axis=0)
    tail_share = smooth(.055, .035, tail_d)*smooth(.76, .79, y)*smooth(1.04, 1.00, z)
    tail = chain_weights(p, TAIL, tail_names, 'pelvis')
    rest = (1 - limb)*(1 - tail_share)
    for name, values in trunk.items():
        add(name, values*(1 - head_zone)*rest)
    add('head', head*rest)
    add('jaw', jaw*rest)
    for chain in limb_weights:
        for name, values in chain.items():
            add(name, values)
    for name, values in tail.items():
        add(name, values*tail_share)
    total = sum(w.values())
    total[total == 0] = 1
    return {k: v/total for k, v in w.items()}


def set_weights(obj, weights: Dict[str, Array], levels: int = 64) -> None:
    """Vertex groups from weight arrays, quantised so every vertex still sums to exactly one."""
    obj.vertex_groups.clear()
    names = list(weights)
    w = np.stack([np.asarray(weights[k], dtype=np.float64) for k in names], axis=1)
    w /= np.maximum(w.sum(axis=1, keepdims=True), 1e-12)
    scaled = w*levels
    q = np.floor(scaled).astype(int)
    short = levels - q.sum(axis=1)
    order = np.argsort(-(scaled - q), axis=1)
    rows = np.arange(len(w))
    for k in range(w.shape[1]):
        bump = short > k
        q[rows[bump], order[bump, k]] += 1
    for column, name in enumerate(names):
        values = q[:, column]
        if not (values > 0).any():
            continue
        group = obj.vertex_groups.new(name=name)
        for level in np.unique(values):
            if level > 0:
                group.add(np.nonzero(values == level)[0].tolist(), float(level)/levels, 'REPLACE')


# ------------------------------------------------------------------ materials

def coat_material(cow) -> bpy.types.Material:
    m = cow.mat('Malvi grey coat', (.58,.56,.52), .62)
    tree = m.node_tree
    nodes, links = tree.nodes, tree.links
    shader = nodes.get('Principled BSDF')
    shader.inputs['Sheen Weight'].default_value = .22
    shader.inputs['Sheen Roughness'].default_value = .38
    shader.inputs['Sheen Tint'].default_value = (.80, .78, .74, 1)
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
    vary.inputs['To Min'].default_value = .90
    vary.inputs['To Max'].default_value = 1.08
    links.new(mottle.outputs['Fac'], vary.inputs['Value'])
    tint = nodes.new('ShaderNodeVectorMath')
    tint.operation = 'SCALE'
    links.new(regional.outputs['Color'], tint.inputs[0])
    links.new(vary.outputs['Result'], tint.inputs['Scale'])
    # Dirt and shadowed hair settle in the creases (folds of the dewlap, elbow, flank)
    geometry = nodes.new('ShaderNodeNewGeometry')
    creases = nodes.new('ShaderNodeMapRange')
    creases.inputs['From Min'].default_value = .44
    creases.inputs['From Max'].default_value = .52
    creases.inputs['To Min'].default_value = .62
    creases.inputs['To Max'].default_value = 1.0
    links.new(geometry.outputs['Pointiness'], creases.inputs['Value'])
    darken = nodes.new('ShaderNodeVectorMath')
    darken.operation = 'SCALE'
    links.new(tint.outputs[0], darken.inputs[0])
    links.new(creases.outputs['Result'], darken.inputs['Scale'])
    links.new(darken.outputs[0], shader.inputs['Base Color'])
    # Bare moist skin (muzzle, eye rims, teats) is glossier than the coat
    bare = nodes.new('ShaderNodeAttribute')
    bare.attribute_name = 'Bare skin'
    bare.location = (-900, -300)
    rough = nodes.new('ShaderNodeMix')
    rough.data_type = 'FLOAT'
    rough.inputs['A'].default_value = .62
    rough.inputs['B'].default_value = .30
    links.new(bare.outputs['Fac'], rough.inputs['Factor'])
    links.new(rough.outputs['Result'], shader.inputs['Roughness'])
    sheen = nodes.new('ShaderNodeMath')
    sheen.operation = 'MULTIPLY_ADD'
    sheen.inputs[1].default_value = -.22
    sheen.inputs[2].default_value = .22
    links.new(bare.outputs['Fac'], sheen.inputs[0])
    links.new(sheen.outputs[0], shader.inputs['Sheen Weight'])
    # Short hair lying backwards along the body: streaky microrelief
    stretch = nodes.new('ShaderNodeMapping')
    stretch.inputs['Scale'].default_value = (900, 95, 340)
    links.new(coords.outputs['Object'], stretch.inputs['Vector'])
    streaks = nodes.new('ShaderNodeTexNoise')
    streaks.label = 'Hair lie'
    streaks.inputs['Scale'].default_value = 1
    streaks.inputs['Detail'].default_value = 2
    links.new(stretch.outputs['Vector'], streaks.inputs['Vector'])
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .30
    bump.inputs['Distance'].default_value = .0007
    # The muzzle is pebbled, not haired: cells instead of streaks where the skin is bare
    pebbles = nodes.new('ShaderNodeTexVoronoi')
    pebbles.feature = 'SMOOTH_F1'
    pebbles.inputs['Scale'].default_value = 520
    links.new(coords.outputs['Object'], pebbles.inputs['Vector'])
    surface = nodes.new('ShaderNodeMix')
    surface.data_type = 'FLOAT'
    links.new(bare.outputs['Fac'], surface.inputs['Factor'])
    links.new(streaks.outputs['Fac'], surface.inputs['A'])
    links.new(pebbles.outputs['Distance'], surface.inputs['B'])
    links.new(surface.outputs['Result'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    return m


def coat_colours(p: Array) -> Tuple[Array, Array]:
    """Malvi colouring (a guess): grey-white, smoky grey over hump, neck, shoulders and quarters,
    a paler belly, dusty lower legs; black muzzle, eye rims and hooves."""
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    base = np.array((.50, .49, .46))
    smoke = np.array((.20, .195, .19))
    pale = np.array((.64, .62, .58))
    slate = np.array((.032, .030, .030))
    dust = np.array((.30, .24, .18))
    ax = np.abs(x)
    shade = .80*smooth(-.18, -.50, y)*smooth(.86, 1.12, z)                          # hump and crest
    shade = np.maximum(shade, .62*smooth(-.36, -.60, y)*smooth(.62, .92, z))        # neck and shoulder
    shade = np.maximum(shade, .45*smooth(.40, .66, y)*smooth(.62, .95, z)*smooth(.10, .20, ax))   # quarters
    shade = np.maximum(shade, .40*np.exp(-((z - .36)/.05)**2)*smooth(.20, .12, ax))  # knees and hocks
    belly = smooth(.64, .52, z)*smooth(.75, .55, np.abs(y) + .2)*(1 - smooth(.12, .22, ax))
    colour = base + (smoke - base)*shade[:, None]
    colour = colour + (pale - colour)*(belly*.7)[:, None]
    colour = colour + (dust - colour)*(.55*smooth(.24, .06, z))[:, None]         # dust up the shanks
    axis, side_v, dorsal = head_frame()
    rel = p - np.array(HEAD_START)
    s = rel @ np.array(axis)/HEAD_LENGTH
    d = rel @ np.array(dorsal)
    in_head = smooth(-.86, -.92, y)
    face = smooth(.30, .75, s)*in_head
    colour = colour + (np.array((.40, .39, .37)) - colour)*(face*.55)[:, None]   # greyer face toward the nose
    poll = smooth(.12, .0, s)*smooth(.0, .05, d)*in_head
    colour = colour + (smoke - colour)*(poll*.5)[:, None]
    muzzle = smooth(.86, .91, s)*smooth(-.075, -.060, d)*(1 - smooth(1.04, 1.06, s))
    muzzle = np.maximum(muzzle, smooth(.89, .93, s)*(1 - smooth(1.04, 1.06, s)))
    rims = np.zeros(len(p))
    for sign in (1, -1):
        e = np.linalg.norm(p - np.array(eye_centre(sign)), axis=1)
        rims = np.maximum(rims, smooth(EYE_R + .022, EYE_R + .007, e))
    teats = smooth(.575, .555, z)*smooth(.10, .06, ax)*smooth(.13, .10, np.abs(y - .47))
    bare = np.clip(np.maximum(np.maximum(muzzle, rims*.85), teats), 0, 1)
    teat_colour = np.array((.40, .29, .26))
    colour = colour + (slate - colour)*np.maximum(muzzle, rims*.9)[:, None]
    colour = colour + (teat_colour - colour)*teats[:, None]
    return colour, bare


def write_attribute(obj, name: str, values: Array) -> None:
    layer = obj.data.color_attributes.new(name, 'FLOAT_COLOR', 'POINT')
    rgba = np.ones((len(values), 4), dtype=np.float32)
    rgba[:, :3] = values if values.ndim == 2 else values[:, None]
    layer.data.foreach_set('color', rgba.ravel())


def write_corner_bytes(obj, name: str, values: Array) -> None:
    """The same colours as a byte face-corner layer: the only kind Cycles hands on to particle hair."""
    corner = np.empty(len(obj.data.loops), dtype=np.int64)
    obj.data.loops.foreach_get('vertex_index', corner)
    rgba = np.ones((len(values), 4), dtype=np.float32)
    rgba[:, :3] = values
    layer = obj.data.color_attributes.new(name, 'BYTE_COLOR', 'CORNER')
    layer.data.foreach_set('color', rgba[corner].ravel())


# ------------------------------------------------------------------ coat hair

HAIR_LENGTH = .011        # short summer coat of a zebu (a guess: 8 to 15 mm)


def hair_material(cow) -> bpy.types.Material:
    m = bpy.data.materials.new(f'{cow.name} • Coat hair')
    m.use_nodes = True
    nodes, links = m.node_tree.nodes, m.node_tree.links
    for node in list(nodes):
        if node.bl_idname != 'ShaderNodeOutputMaterial':
            nodes.remove(node)
    output = next(n for n in nodes if n.bl_idname == 'ShaderNodeOutputMaterial')
    hair = nodes.new('ShaderNodeBsdfHairPrincipled')
    hair.parametrization = 'COLOR'
    hair.inputs['Roughness'].default_value = .36
    hair.inputs['Radial Roughness'].default_value = .55
    hair.inputs['Coat'].default_value = .08
    colour = nodes.new('ShaderNodeAttribute')
    colour.attribute_name = 'Coat colour (hair)'
    info = nodes.new('ShaderNodeHairInfo')
    vary = nodes.new('ShaderNodeMapRange')
    vary.inputs['To Min'].default_value = .82
    vary.inputs['To Max'].default_value = 1.10
    links.new(info.outputs['Random'], vary.inputs['Value'])
    tint = nodes.new('ShaderNodeVectorMath')
    tint.operation = 'SCALE'
    links.new(colour.outputs['Color'], tint.inputs[0])
    links.new(vary.outputs['Result'], tint.inputs['Scale'])
    links.new(tint.outputs[0], hair.inputs['Color'])
    links.new(hair.outputs[0], output.inputs['Surface'])
    m.diffuse_color = (.5, .49, .46, 1)
    return m


def coat_hair(cow, body, bare: Array, parents: int = 200_000, children: int = 5) -> None:
    """Short hair over the coat, lying back along the body; none on the muzzle, eye rims, teats or coronets.

    Particle hair follows the armature-deformed body, so it moves with the rig."""
    co = mesh_coords(body.data)
    density = (1 - np.clip(bare*1.6, 0, 1))*smooth(.05, .09, co[:, 2])
    group = body.vertex_groups.new(name=Cow.HAIR_GROUPS[0])
    q = np.round(density*32).astype(int)
    for level in np.unique(q):
        if level > 0:
            group.add(np.nonzero(q == level)[0].tolist(), float(level)/32, 'REPLACE')
    body.data.materials.append(hair_material(cow))
    system = body.modifiers.new('Coat hair', 'PARTICLE_SYSTEM').particle_system
    system.vertex_group_density = group.name
    system.seed = 3
    st = system.settings
    st.name = f'{cow.name} coat hair'
    st.type = 'HAIR'
    st.count = parents
    st.use_advanced_hair = True
    st.normal_factor = .35*HAIR_LENGTH                   # out of the skin a little,
    st.object_align_factor = (0, .90*HAIR_LENGTH, -.35*HAIR_LENGTH)   # lying back toward the tail and down
    st.material = len(body.data.materials)
    st.display_step, st.render_step = 2, 3
    st.child_type = 'INTERPOLATED'
    st.child_percent = 1
    st.rendered_child_count = children
    st.child_radius = .004
    st.roughness_1, st.roughness_2 = .0015, .002
    st.root_radius, st.tip_radius, st.radius_scale = 1.0, 0.0, .00018
    st.use_close_tip = True


# ------------------------------------------------------------------ sculpted body

def mesh_coords(mesh) -> Array:
    co = np.empty(len(mesh.vertices)*3)
    mesh.vertices.foreach_get('co', co)
    return co.reshape(-1, 3)


def detail(co: Array) -> Array:
    """1 where close-ups look (head, neck band of the tether, face of the shoulder), 0 elsewhere."""
    y, z = co[:, 1], co[:, 2]
    return np.maximum(smooth(-.58, -.66, y), .0*z)


def build_body(cow, coat) -> Tuple[bpy.types.Object, Array]:
    sculpt = cow_sculpt()
    values, origin = sculpt.grid((-.34, -1.30, .045), (.34, .87, 1.30), STEP)
    verts, quads = surface_nets(values, origin, STEP)
    del values
    verts = taubin(verts, quads, rounds=5)
    body = cow.mesh('Body', [tuple(v) for v in verts], [tuple(q) for q in quads.tolist()], coat, 'chest')
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(body.data)
    bm.free()
    decimate(body, detail, .30)
    co = mesh_coords(body.data)
    set_weights(body, cow_weights(co))
    colours, bare = coat_colours(co)
    write_attribute(body, 'Coat colour', colours)
    write_attribute(body, 'Bare skin', bare)
    write_corner_bytes(body, 'Coat colour (hair)', colours)
    return body, bare


def decimate(obj, keep_of: Callable[[Array], Array], ratio: float) -> None:
    """Collapse the barrel and legs; keep the head and neck dense for close-ups."""
    keep = keep_of(mesh_coords(obj.data))
    group = obj.vertex_groups.new(name='Detail')
    q = np.round(keep*32).astype(int)
    for level in np.unique(q):
        if level > 0:
            group.add(np.nonzero(q == level)[0].tolist(), float(level)/32, 'REPLACE')
    skin = obj.modifiers.get('Character Skinning')
    if skin:
        skin.show_viewport = False
    modifier = obj.modifiers.new('Decimate', 'DECIMATE')
    modifier.ratio = ratio
    modifier.vertex_group = group.name
    modifier.vertex_group_factor = 20
    modifier.invert_vertex_group = True
    modifier.use_symmetry = True
    modifier.symmetry_axis = 'X'
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
    old = obj.data
    obj.modifiers.remove(modifier)
    obj.data = mesh
    mesh.name = old.name
    bpy.data.meshes.remove(old)
    if skin:
        skin.show_viewport = True
    obj.vertex_groups.remove(obj.vertex_groups['Detail'])
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.normal_update()
    folds = [f for f in bm.faces if f.normal.dot(sum((v.normal for v in f.verts), Vector())) < 0]
    if folds:
        bmesh.ops.reverse_faces(bm, faces=folds)
    bm.to_mesh(mesh)
    bm.free()
    for polygon in mesh.polygons:
        polygon.use_smooth = True


# ------------------------------------------------------------------ separate parts

def build_eyes(cow, eye_m) -> None:
    for sign, side in ((1, 'L'), (-1, 'R')):
        centre = eye_centre(sign)
        rows, columns = 18, 32
        out = eye_axis(sign)
        rot = Vector((0, 0, 1)).rotation_difference(out)
        verts = []
        for r in range(rows + 1):
            v = -math.pi/2 + math.pi*r/rows
            for k in range(columns):
                u = math.tau*k/columns
                local = Vector((math.cos(v)*math.cos(u), math.cos(v)*math.sin(u), math.sin(v)))*EYE_R
                verts.append(tuple(centre + rot @ local))
        faces = []
        for r in range(rows):
            for k in range(columns):
                n = (k + 1) % columns
                faces.append((r*columns + k, r*columns + n, (r + 1)*columns + n, (r + 1)*columns + k))
        cow.mesh(f'Eye.{side}', verts, faces, eye_m, f'eye.{side}')


def build_lashes(cow) -> None:
    lash = FiberGroup(cow, (.05,.045,.04), (.30,.28,.25))
    for sign, side in ((1, 'L'), (-1, 'R')):
        centre = eye_centre(sign)
        out = eye_axis(sign)
        up = (Vector((0, 0, 1)) - out*out.z).normalized()
        across = up.cross(out)
        for j in range(70):
            a = math.radians(-46 + 92*j/69)
            root = centre + out*(EYE_R + .0030)*math.cos(math.radians(24)) + across*math.sin(a)*(EYE_R + .006) \
                + up*(EYE_R*.52 + .0030*math.cos(a))
            grow = (out*.75 + up*.55 + across*math.sin(a)*.25).normalized()
            length = .017*(.55 + .45*math.cos(a*1.1))
            path = [root + grow*length*t + Vector((0, 0, -.005*t*t)) for t in (0, .33, .66, 1)]
            lash.add(path, .00017, 2, 4)
    lash.make_mesh('Eyelashes')
    obj = cow.parts[-1]
    obj.vertex_groups.clear()
    obj.vertex_groups.new(name='head').add(list(range(len(obj.data.vertices))), 1, 'REPLACE')


def build_ears(cow, coat) -> None:
    for sign, side in ((1, 'L'), (-1, 'R')):
        base = head_point(.06, sign*.080, -.012)
        direction = Vector((sign*.92, .26, -.30)).normalized()
        across = Vector((0, -.35, .94)).normalized()
        across = (across - direction*across.dot(direction)).normalized()
        normal = direction.cross(across)
        rows_e, cols_e = 18, 15
        verts_e, weights_e, colours = [], [], []
        for layer, offset in ((0, .0035), (1, -.0035)):
            for i in range(rows_e):
                u = i/(rows_e-1)
                length = .19*u
                width = .050*math.sin(math.pi*min(1, u*1.05))**.7*(1-.25*u) + .016*(1 - u)
                for j in range(cols_e):
                    v = j/(cols_e-1)*2-1
                    cup = .018*(1-v*v)*math.sin(math.pi*u)
                    p = base + direction*(length - .015) + across*v*width + normal*(offset*(1-u*.6) - cup*sign)
                    verts_e.append(tuple(p))
                    a = float(smooth(0, .3, u))
                    weights_e.append({f'ear.{side}': a, 'head': 1-a} if a < 1 else {f'ear.{side}': 1.0})
                    inner = layer == 1 and abs(v) < .75 and u > .12
                    colours.append((.36,.30,.28) if inner else (.50,.49,.46))
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
        ear = cow.mesh(f'Ear.{side}', verts_e, faces_e, coat, weights_e)
        write_attribute(ear, 'Coat colour', np.array(colours))
        write_attribute(ear, 'Bare skin', np.zeros(len(colours)))
        mod = ear.modifiers.new('Subdivision', 'SUBSURF')
        mod.levels = mod.render_levels = 1
        ear.modifiers.move(len(ear.modifiers) - 1, 0)


def build_horns(cow, horn) -> None:
    for sign, side in ((1, 'L'), (-1, 'R')):
        root = head_point(.015, sign*.066, .040)
        path = [root, root + Vector((sign*.050, .004, .030)), root + Vector((sign*.088, -.004, .090)),
                root + Vector((sign*.100, -.030, .160)), root + Vector((sign*.086, -.052, .215)),
                root + Vector((sign*.066, -.058, .240))]
        radii = [.026, .023, .018, .013, .008, .002]
        cow.tube(f'Horn.{side}', [tuple(p) for p in path], radii, horn, 'head')


def build_hooves(cow, hoof) -> None:
    for sign, side in ((1, 'L'), (-1, 'R')):
        for label, joints, bone in (('Front', FRONT_LEG, f'front_pastern.{side}'),
                                    ('Hind', REAR_LEG, f'rear_pastern.{side}')):
            coronet = Vector((sign*joints[-1].x, joints[-1].y, joints[-1].z))
            for claw, dx in (('outer', .019), ('inner', -.019)):
                rings_h = []
                for k in range(8):
                    t = k/7
                    z = coronet.z + .010 - (coronet.z + .010)*t
                    reach = .036 + .030*t
                    half = .017 + .005*t
                    ring = []
                    for a in range(24):
                        ang = math.tau*a/24
                        c, s_ = math.cos(ang), math.sin(ang)
                        y = (reach if s_ < 0 else .030)*s_
                        x = half*c*(1 - .45*max(0.0, -s_)**2)
                        if (dx > 0) == (c < 0):             # the cleft between the claws is flat
                            x *= .55
                        ring.append(tuple(Vector((coronet.x + sign*dx + sign*x, coronet.y + y - .010*t, z))))
                    rings_h.append(ring if sign > 0 else ring[::-1])
                cow.ring_mesh(f'Hoof {label} {side} {claw}', rings_h, hoof, bone)
            fetlock = Vector((sign*joints[3].x, joints[3].y, joints[3].z))
            for dx in (.016, -.016):
                cow.ovoid(f'Dewclaw {label} {side} {"outer" if dx > 0 else "inner"}',
                          tuple(fetlock + Vector((sign*dx, .036, .012))), (.008, .009, .011), hoof, bone)


def build_switch(cow) -> None:
    rand = random.Random(29)
    switch = FiberGroup(cow, (.012,.011,.010), (.10,.09,.08))
    tip = TAIL[-1]
    for _ in range(900):
        a = rand.uniform(0, math.tau)
        r = .010*math.sqrt(rand.random())
        start = tip + Vector((r*math.cos(a), r*math.sin(a), rand.uniform(-.02, .07)))
        length = rand.uniform(.17, .29)
        spread = Vector((math.cos(a), math.sin(a), 0))*rand.uniform(.01, .04)
        path = [start + spread*t*t + Vector((rand.uniform(-.003, .003), 0, -length*t)) for t in (0, .25, .5, .75, 1)]
        switch.add(path, rand.uniform(.00025, .00042), rand.randrange(0, 5), 5)
    switch.make_mesh('Tail switch')
    obj = cow.parts[-1]
    obj.vertex_groups.clear()
    obj.vertex_groups.new(name='tail_4').add(list(range(len(obj.data.vertices))), 1, 'REPLACE')


def neck_fibers(cow, body) -> None:
    """Real short hair over the neck band the camera sees in the rope-cutting close-up."""
    rand = random.Random(57)
    mesh = body.data
    fibers = FiberGroup(cow, (.26,.25,.24), (.74,.72,.68))
    triangles = []
    for polygon in mesh.polygons:
        centre = polygon.center
        if -.88 < centre.y < -.64 and centre.z > .70:
            v = [mesh.vertices[i].co.copy() for i in polygon.vertices]
            triangles.append((polygon.area, v, polygon.normal.copy()))
    total = sum(t[0] for t in triangles)
    count = 26000
    for area, v, normal in triangles:
        n = int(count*area/total + rand.random())
        for _ in range(n):
            a, b = rand.random(), rand.random()
            if a + b > 1:
                a, b = 1-a, 1-b
            root = v[0] + (v[1]-v[0])*a + (v[-1]-v[0])*b
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
    co = mesh_coords(obj.data)
    set_weights(obj, cow_weights(co))


def build(hair_parents: int = 200_000) -> Cow:
    """hair_parents: 0 leaves the coat bare (quick look-dev builds)."""
    cow = Cow()
    coat = coat_material(cow)
    horn = cow.mat('Weathered horn', (.10,.095,.088), .45)
    hoof = cow.mat('Dark hoof keratin', (.06,.055,.05), .5)
    eye = cow.mat('Dark wet eye', (.018,.011,.008), .05)
    eye.node_tree.nodes.get('Principled BSDF').inputs['Coat Weight'].default_value = 1
    body, bare = build_body(cow, coat)
    build_eyes(cow, eye)
    build_lashes(cow)
    build_ears(cow, coat)
    build_horns(cow, horn)
    build_hooves(cow, hoof)
    build_switch(cow)
    if hair_parents:
        coat_hair(cow, body, bare, hair_parents)
    else:
        neck_fibers(cow, body)            # a patch of mesh hair where the rope close-up looks
    cow.body_tree = BVHTree.FromPolygons([v.co.copy() for v in body.data.vertices],
                                         [tuple(p.vertices) for p in body.data.polygons])
    cow.validate()
    cow.rig['Breed'] = 'Malvi-type zebu cow (guess)'
    cow.rig['Withers_height_m'] = WITHERS
    return cow


def neck_loop(cow: Cow, slack: float = .010, sag: float = .030, count: int = 64) -> List[Vector]:
    """The tether loop around the sculpted neck at ROPE_Y: the skin outline plus slack, sagging below."""
    centre_z = curve([(r[0], r[1]) for r in NECK], ROPE_Y)
    centre = Vector((0, ROPE_Y, centre_z))
    points = []
    for k in range(count):
        a = math.tau*k/count
        direction = Vector((math.cos(a), .10*math.sin(a), math.sin(a))).normalized()
        start = centre + direction*.5
        hit, normal, _, _ = cow.body_tree.ray_cast(start, -direction, .5)
        p = hit if hit is not None else centre + direction*.15
        p = p + direction*slack
        p.z -= sag*max(0.0, -math.sin(a))**3
        points.append(p)
    return points
