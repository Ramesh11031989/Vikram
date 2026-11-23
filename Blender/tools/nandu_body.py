"""Nandu's realistic body: sculpted head (sculpted_face), sculpted hands (sculpted_hand),
a longer torso and realistic arms on the shared skeleton names.

Design units are the shared cast's (c.mesh multiplies by c.scale). With
SCALE = .958 the shared legs give a 87 cm hip joint, and the sculpted head
(size = SCALE/CANON_HEIGHT = 1.104) puts the crown at 170 cm. The torso of the
shared body is stretched by `morph()` so the shoulders sit at a realistic
140 cm instead of the stylised cast's 132 cm.

The hand layout follows the Halwai's neighbour (halwai_neighbour.FINGERS and
THUMB, branch claude/project-thread-zwjct1), enlarged to a 19 cm male hand.
"""

from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple

import bpy
import numpy as np
from mathutils import Vector

from character import Character
import sculpted_face as sf
import sculpted_hand as sh


SCALE = .958
LOWER, UPPER = 1.02, 1.39   # the stretched stretch of the shared torso (design z)
LIFT = .086                 # how much higher the shoulders sit than on the shared body
STRETCH = (UPPER + LIFT - LOWER)/(UPPER - LOWER)

Point = Tuple[float, float, float]
Weights = Dict[str, float]


def vertical(z: float) -> float:
    if z <= LOWER:
        return z
    if z >= UPPER:
        return z + LIFT
    return LOWER + (z - LOWER)*STRETCH


def morph(p: Sequence[float]) -> Vector:
    """A point authored on the shared (stylised) torso, moved to Nandu's realistic torso."""
    return Vector((p[0], p[1], vertical(p[2])))


ARM_Z = vertical(1.375)                   # shoulder line in the T-pose (design)
HEAD_BASE = Vector((0, -.010, 1.522))     # head pivot (design): scene ≈ 1.46 m
CROWN = 1.70/SCALE                         # design height of the crown

# The neighbour's hand (her design units), re-based on Nandu's wrist and enlarged.
HER_WRIST, HER_FINGER_DZ = .780, -.002
FINGERS = (
    (1, (.887, -.0345), -.15, (.039, .024, .021), .0094),
    (2, (.891, -.0115), -.05, (.043, .027, .022), .0097),
    (3, (.887, .0115), .06, (.040, .026, .021), .0092),
    (4, (.877, .0335), .19, (.031, .020, .018), .0079),
)
THUMB = ((.795, -.020, -.010), (.830, -.048, -.016), (.857, -.065, -.019), (.879, -.078, -.021))
WRIST_X = .785
# 1.07 x her 17.7 cm hand ≈ 18.9 cm, converted from her scale (.868) to Nandu's.
HAND_K = 1.07*.868/SCALE


def hand_point(x: float, y: float, dz: float) -> Point:
    return (WRIST_X + (x - HER_WRIST)*HAND_K, y*HAND_K, ARM_Z + dz*HAND_K)


def finger_joints(spread: float, mcp: Tuple[float, float], lengths: Sequence[float]) -> List[Point]:
    direction = Vector((1, spread, -.035)).normalized()
    start = Vector(hand_point(mcp[0], mcp[1], HER_FINGER_DZ))
    points = [start]
    for length in lengths:
        points.append(points[-1] + direction*length*HAND_K)
    return [tuple(p) for p in points]


def thumb_joints() -> List[Point]:
    return [hand_point(x, y, z) for x, y, z in THUMB]


def hand_spec() -> sh.HandSpec:
    fingers = []
    for digit, mcp, spread, lengths, radius in FINGERS:
        joints = tuple(finger_joints(spread, mcp, lengths))
        fingers.append(sh.Digit(joints, radius*HAND_K*1.04,
                                (f'finger_{digit:02d}', f'finger_{digit:02d}_mid', f'finger_{digit:02d}_tip')))
    thumb = sh.Digit(tuple(thumb_joints()), .0112*HAND_K*1.04, ('thumb', 'thumb_mid', 'thumb_tip'),
                     tuple(Vector((0, -.62, .78)).normalized()))
    return sh.HandSpec(tuple(fingers), thumb, wrist_x=WRIST_X, z=ARM_Z - .001)


def mirror(p: Sequence[float], sign: int) -> Point:
    return (sign*p[0], p[1], p[2])


class NanduCharacter(Character):
    """Shared Character with Nandu's realistic skeleton: same 34 names plus finger and thumb segments."""

    def __init__(self, spec) -> None:
        self.morphing = False
        super().__init__(spec)

    def mesh(self, name, verts, faces, material, bone, smooth=True):
        if self.morphing:
            verts = [tuple(morph(p)) for p in verts]
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
            item.head, item.tail = head*self.scale, tail*self.scale
            item.use_deform = deform
            if parent:
                item.parent = armature.edit_bones[parent]
            return item

        bone('root', (0, 0, 0), (0, 0, .19), deform=False)
        bone('hips', (0, 0, .91), (0, 0, 1.04), 'root', warp=True)
        bone('spine', (0, 0, 1.04), (0, 0, 1.22), 'hips', warp=True)
        bone('chest', (0, 0, 1.22), (0, 0, 1.39), 'spine', warp=True)
        bone('neck', morph((0, 0, 1.39)), HEAD_BASE, 'chest')
        bone('head', HEAD_BASE, (HEAD_BASE.x, HEAD_BASE.y, CROWN), 'neck')
        for side, sign in (('L', 1), ('R', -1)):
            bone(f'clavicle.{side}', (sign*.040, -.004, ARM_Z-.006), (sign*.190, 0, ARM_Z), 'chest')
            bone(f'upper_arm.{side}', (sign*.190, 0, ARM_Z), (sign*.515, .005, ARM_Z), f'clavicle.{side}')
            bone(f'forearm.{side}', (sign*.515, .005, ARM_Z), (sign*WRIST_X, 0, ARM_Z), f'upper_arm.{side}')
            bone(f'hand.{side}', (sign*WRIST_X, 0, ARM_Z), mirror(hand_point(.884, -.001, -.002), sign), f'forearm.{side}')
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
            hip, knee = (sign*.125, 0, .91), (sign*.135, -.014, .52)
            ankle, ball = (sign*.135, 0, .14), (sign*.135, -.122, .045)
            bone(f'thigh.{side}', hip, knee, 'hips')
            bone(f'shin.{side}', knee, ankle, f'thigh.{side}')
            bone(f'foot.{side}', ankle, ball, f'shin.{side}')
            bone(f'toes.{side}', ball, (sign*.135, -.18, .045), f'foot.{side}')
            bone(f'eye.{side}', (sign*.03, -.09, 1.59), (sign*.03, -.13, 1.59), 'head')   # placed by the face
        bpy.ops.object.mode_set(mode='OBJECT')
        rig['Usage'] = ('Shared cast skeleton names (T-pose) plus finger_0N_mid/_tip and thumb_mid/_tip. '
                        'Facial controls are custom properties on this rig.')
        return rig

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


# --------------------------------------------------------------- body

# x, half depth, half height (design): a lean labourer's arm, deltoid to wrist.
ARM_RINGS = ((.150, .052, .056), (.190, .056, .060), (.240, .050, .054), (.300, .044, .047),
             (.370, .042, .045), (.440, .038, .040), (.505, .034, .036), (.540, .039, .040),
             (.600, .037, .036), (.670, .031, .029), (.740, .026, .023), (.800, .024, .020))


def arm_weight(x: float, side: str) -> Weights:
    upper, lower, hand = (f'{b}.{side}' for b in ('upper_arm', 'forearm', 'hand'))
    if x <= .19:
        t = max(0.0, (x - .15)/.04)
        return {'chest': 1 - t*.6, upper: t*.6}
    if x < .47:
        return {upper: 1.0}
    if x < .56:
        t = (x - .47)/.09
        return {upper: 1 - t, lower: t}
    if x < .77:
        return {lower: 1.0}
    t = min(1.0, (x - .77)/.03)
    return {lower: 1 - t, hand: t}


def arm(c, side: str, sign: int, skin) -> None:
    rings, weights = [], []
    for x, ry, rz in ARM_RINGS:
        ring = []
        for j in range(28):
            a = math.tau*j/28
            # flatter under the arm, a little forward roll on the forearm
            ring.append((sign*x, sign*ry*math.cos(a), ARM_Z + rz*math.sin(a) - .004*max(0.0, -math.sin(a))))
        rings.append(ring)
        weights.append(arm_weight(x, side))
    c.ring_mesh(f'Arm.{side}', rings, skin, weights, cap=False)


def body(c) -> None:
    c.body()
    for obj in [p for p in c.parts if any(k in p.name for k in ('_Neck', '_Arm.', '_Palm.', '_Finger_', '_Thumb.'))]:
        c.parts.remove(obj)
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.meshes.remove(mesh)
    spec = hand_spec()
    for side, sign in (('L', 1), ('R', -1)):
        arm(c, side, sign, c.m['skin'])
        sh.build_hand(c, spec, side, sign, c.m['skin'])


# --------------------------------------------------------------- face

NANDU_FACE = sf.FaceSpec(eye_size=.91, eye_spacing=.95, eye_depth=.0016, eye_open=.82, brow_ridge=.9,
                         forehead_slope=.5, cheek_fat=.40, jaw_width=1.06, jaw_mass=1.12, chin=1.08,
                         chin_width=1.22, nose_length=1.06, nose_width=1.16, nose_projection=1.0,
                         lip_fullness=.86, mouth_width=1.02, neck=1.12, adams_apple=1.0,
                         lip_colour=(.205, .095, .072), beard_shadow=.75)
# GUESS: a lean, weathered 40-45 year old, a little hooded and tired around the eyes.


def material(c, label: str, rgb, rough: float = .8):
    return c.mat(label, rgb, rough)


def face(c) -> None:
    c.sculpted = sf.SculptedFace(c, NANDU_FACE)
    head = c.sculpted.head_mesh(c.m['skin'])
    c.sculpted.build_eyes(head)
    sf.skin_shading(c)
    c.sculpted.paint_head(head)
    ears(c)
    c.sculpted.brow_strips(material(c, 'Brow skin shadow', tuple(v*.55 for v in c.spec['skin']), .7))
    c.sculpted.mouth_lining(material(c, 'Mouth interior', (.040, .009, .008), .55))


def ears(c) -> None:
    """The shared ear, shrunk to an adult ear and set against the sculpted skull."""
    inner = material(c, 'Inner ear', tuple(a*f for a, f in zip(c.spec['skin'], (.82, .67, .63))), .72)
    face = c.sculpted
    for side, sign in (('L', 1), ('R', -1)):
        c.ear(side, sign, c.spec['face_width'], c.m['skin'], inner)
        parts = [bpy.data.objects[f'{c.name}_Ear.{side}'], bpy.data.objects[f'{c.name}_Ear inner fold.{side}']]
        co = [v.co.copy() for v in parts[0].data.vertices]
        centre = sum(co, Vector())/len(co)
        shrink = .74
        for obj in parts:
            for v in obj.data.vertices:
                v.co = centre + (v.co - centre)*shrink
        low = min(sign*v.co.x for v in parts[0].data.vertices)
        target = Vector((0, .006, 1.4255))
        hit, _, _, _ = face.tree.ray_cast(Vector((sign*.2, target.y, target.z)), Vector((-sign, 0, 0)), .3)
        surface = (abs(hit.x) if hit is not None else .066)*face.size
        target = face.final(target)
        shift = Vector((sign*(surface - .003*face.size - low), target.y - centre.y, target.z - centre.z))
        for obj in parts:
            for v in obj.data.vertices:
                v.co += shift


def finish_face(c) -> None:
    """After the shared facial controls: sculpted blinks, teeth, tongue and speech shapes."""
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


def head_surface(c):
    """BVH of the head in design units, for the wrap and the groom."""
    from mathutils.bvhtree import BVHTree
    head = bpy.data.objects[f'{c.name}_Head']
    return BVHTree.FromPolygons([v.co/c.scale for v in head.data.vertices],
                                [tuple(p.vertices) for p in head.data.polygons])


def canonical(c, p: Vector) -> Vector:
    return p*c.scale/c.sculpted.size


def design(c, p: Sequence[float]) -> Vector:
    return Vector(p)*c.sculpted.size/c.scale


def smooth01(a: float, b: float, x: float) -> float:
    t = max(0.0, min(1.0, (x - a)/(b - a)))
    return t*t*(3 - 2*t)
