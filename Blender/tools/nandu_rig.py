"""Nandu's story-specific controls: tied/free wrists, red gamchha, reed boat, grips, expressions.

Everything here sits on top of the shared adult rig, so Nandu keeps the same 34
bone names as Gopal and the rest of the cast. The extra wrist-binding bones are
added after them and only the rope is weighted to them.
"""

from __future__ import annotations

import math
import bpy
from mathutils import Matrix, Quaternion, Vector

from facial_controls import driver_from_property, property_control, shape_from_delta
import reed_boat as reed_boat_prop
from nandu_body import morph
from textile import finish_fabric, store_rest_positions


TIED = 'wrists_tied'
EXPRESSIONS = ('expr_fear', 'expr_pleading', 'expr_relief', 'expr_tenderness')
# From the daughter thread: about 1.10 m, palm about 6 cm wide, 11 cm wrist to fingertip.
CHILD_PALM_WIDTH = .060
CHILD_HAND_LENGTH = .110

Vec3 = tuple[float, float, float]


def prop_driver(owner, path: str, source, prop: str, expression: str = 'value') -> None:
    curve = owner.driver_add(path)
    driver = curve.driver
    driver.type = 'SCRIPTED'
    variable = driver.variables.new()
    variable.name, variable.type = 'value', 'SINGLE_PROP'
    variable.targets[0].id = source
    variable.targets[0].data_path = f'["{prop}"]'
    driver.expression = expression


# ---------------------------------------------------------------- wrist states

def add_wrist_rig(c) -> None:
    """Binding bones plus IK/rotation constraints that switch on with one property."""
    rig, s = c.rig, c.scale
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    bones = rig.data.edit_bones
    centre = Vector((0, -.25, 1.08))
    bind = bones.new('wrist_bind')
    bind.head, bind.tail = centre*s, (centre+Vector((0, -.07, 0)))*s
    bind.parent = bones['chest']
    bind.use_deform = True
    for side, sign in (('L', 1), ('R', -1)):
        item = bones.new(f'wrist_bind.{side}')
        head = centre + Vector((sign*.05, 0, 0))
        item.head, item.tail = head*s, (head+Vector((0, -.11, 0)))*s
        # Bone Z points away from the centre, so the palm (-Z of the hand) faces in.
        item.align_roll(Vector((sign, 0, 0)))
        item.parent = bind
        item.use_deform = True
    bpy.ops.object.mode_set(mode='OBJECT')

    property_control(rig, TIED, '1 = wrists bound with jute rope in front of the body, 0 = free hands')
    for side in ('L', 'R'):
        forearm = rig.pose.bones[f'forearm.{side}']
        ik = forearm.constraints.new('IK')
        ik.name = 'Tied wrists IK'
        ik.target, ik.subtarget = rig, f'wrist_bind.{side}'
        # No pole target: with one the legacy solver stopped ~6 cm short of the wrists;
        # without it the bound hands meet exactly and the elbows fall naturally outward.
        ik.chain_count = 2
        ik.use_stretch = False
        prop_driver(ik, 'influence', rig, TIED)
        hand = rig.pose.bones[f'hand.{side}']
        rotation = hand.constraints.new('COPY_ROTATION')
        rotation.name = 'Tied wrists orientation'
        rotation.target, rotation.subtarget = rig, f'wrist_bind.{side}'
        prop_driver(rotation, 'influence', rig, TIED)
    rig['Wrist_states'] = ('Set wrists_tied to 1 for the bound state. Move the wrist_bind bone to place '
                           'both hands; rotate the upper arms to adjust the elbows. 0 frees the hands with no rebuild.')


def wrist_rope(c, rope) -> None:
    s = c.scale
    centre = Vector((0, -.25, 1.08))
    parts = []
    for side, sign in (('L', 1), ('R', -1)):
        wrist = centre + Vector((sign*.05, 0, 0))
        for index, (dy, radius) in enumerate(((.012, .029), (.026, .030), (.040, .029))):
            loop = [(wrist.x + radius*math.cos(math.tau*j/28), wrist.y + dy + .003*math.sin(3*math.tau*j/28),
                     wrist.z + radius*.88*math.sin(math.tau*j/28)) for j in range(28)]
            parts.append(c.tube(f'Jute wrist rope {side} {index+1}', loop, .0052, rope,
                                f'wrist_bind.{side}', cyclic=True))
    # Figure-eight binding between the wrists, a knot and the lead end a guard can hold.
    for index, z in enumerate((.026, -.026)):
        parts.append(c.tube(f'Jute rope crossing {index+1}',
                            [(-.054, -.224, 1.08+z), (0, -.236, 1.08+z*.25), (.054, -.224, 1.08-z)],
                            .0055, rope, 'wrist_bind'))
    parts.append(c.ovoid('Jute rope knot', (0, -.236, 1.050), (.016, .013, .014), rope, 'wrist_bind'))
    parts.append(c.tube('Jute rope lead end', [(0, -.236, 1.040), (.006, -.240, .97), (-.004, -.232, .88),
                                               (.010, -.236, .80)], [.006, .0055, .005, .0045], rope, 'wrist_bind'))
    for obj in parts:
        for prop in ('hide_render', 'hide_viewport'):
            prop_driver(obj, prop, c.rig, TIED, 'value < 0.5')


# ---------------------------------------------------------------- red gamchha

def _shoulder_rows() -> list[tuple[float, float, float, float]]:
    """Centre line (z, x, y, half width) from the front of the left chest, over the shoulder, to the back."""
    rows = [(1.000, .122, -.136, .054), (1.100, .130, -.130, .057), (1.200, .140, -.131, .059),
            (1.290, .148, -.126, .060), (1.372, .150, -.100, .058), (1.432, .150, -.056, .056),
            (1.458, .150, .000, .055), (1.432, .150, .056, .056), (1.372, .152, .100, .058),
            (1.290, .150, .126, .060), (1.180, .142, .127, .060), (1.060, .134, .124, .058),
            (.960, .130, .121, .055)]
    dense = []
    for a, b in zip(rows, rows[1:]):
        for step in range(3):
            t = step/3
            dense.append(tuple(x+(y-x)*t for x, y in zip(a, b)))
    return dense + [rows[-1]]


def red_cloth(c):
    """Separate gamchha object, attached by a toggleable Child Of constraint, with a cloth setup."""
    s = c.scale
    material = c.mat('Madder red gamchha', (.42, .032, .026), .9)
    finish_fabric(material, fine=False)
    stripe = c.mat('Gamchha woven stripe', (.62, .48, .30), .9)
    rows = _shoulder_rows()
    across = 9
    verts, faces = [], []
    for z, x, y, width in rows:
        for k in range(across):
            t = k/(across-1)
            point = (x+(t-.5)*width*2, y-.004*math.cos(t*math.tau*2), z+(t-.5)*.016)
            verts.append(Vector(morph(point) if getattr(c, 'morphing', None) is not None else point)*s)
    for r in range(len(rows)-1):
        for k in range(across-1):
            i = r*across+k
            faces.append((i, i+1, i+across+1, i+across))
    mesh = bpy.data.meshes.new('Nandu red gamchha')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    mesh.materials.append(material)
    mesh.materials.append(stripe)
    for face in mesh.polygons:
        face.use_smooth = True
        row = face.index//(across-1)
        face.material_index = 1 if row in (1, len(rows)-3) else 0
    store_rest_positions(mesh)
    cloth = bpy.data.objects.new('Nandu_Red gamchha', mesh)
    c.collection.objects.link(cloth)
    pins = cloth.vertex_groups.new(name='Shoulder pins')
    top = [index for index, (z, *_rest) in enumerate(rows) if z > 1.36]
    for row in top:
        pins.add([row*across+k for k in range(across)], 1.0, 'REPLACE')
    for row in (top[0]-1, top[-1]+1):
        pins.add([row*across+k for k in range(across)], .55, 'REPLACE')

    simulation = cloth.modifiers.new('Gamchha cotton', 'CLOTH')
    settings = simulation.settings
    settings.vertex_group_mass = pins.name
    settings.quality = 8
    settings.mass = .03
    settings.air_damping = 2
    settings.tension_stiffness = 25
    settings.compression_stiffness = 18
    settings.shear_stiffness = 6
    settings.bending_stiffness = .15
    collisions = simulation.collision_settings
    collisions.use_collision = True
    collisions.distance_min = .004
    collisions.use_self_collision = True
    simulation.point_cache.frame_start = 1
    simulation.point_cache.frame_end = 250
    # Off by default so the authored drape holds in every scene; enable and bake per shot.
    simulation.show_viewport = simulation.show_render = False
    smooth = cloth.modifiers.new('Soft folds', 'SUBSURF')
    smooth.levels = smooth.render_levels = 1
    thickness = cloth.modifiers.new('Cloth thickness', 'SOLIDIFY')
    thickness.thickness = .0016
    property_control(cloth, 'attached', '1 = rides on the wearer\'s chest bone, 0 = stays where it was left')
    cloth['attached'] = 1.0
    cloth['Usage'] = ('Separate prop. bind_red_cloth() re-targets it to any rig with the shared bone names, '
                      'for example the anonymous figure at the chauki. Enable "Gamchha cotton" and bake '
                      'per shot; the kurta torso has a collision surface.')
    bind_red_cloth(cloth, c.rig)
    for part in c.parts:
        if part.name.endswith('_Coarse kurta'):
            part.modifiers.new('Gamchha collision', 'COLLISION')
            part.collision.thickness_outer = .004
    return cloth


def bind_red_cloth(cloth, rig, scale: float = 1.0):
    """Attach the gamchha to a rig's chest bone. Works for any rig built by Character."""
    constraint = cloth.constraints.get('Wearer chest') or cloth.constraints.new('CHILD_OF')
    constraint.name = 'Wearer chest'
    constraint.target, constraint.subtarget = rig, 'chest'
    # The cloth is authored around a rig standing at the origin, so the inverse is the
    # chest's rest matrix: on any rig with the shared bones it rides that rig's chest.
    constraint.inverse_matrix = rig.data.bones['chest'].matrix_local.inverted()
    cloth.scale = (scale,)*3
    if not cloth.animation_data or not cloth.animation_data.drivers.find('constraints["Wearer chest"].influence'):
        prop_driver(constraint, 'influence', cloth, 'attached')
    return constraint


# ---------------------------------------------------------------- reed toy boat

def reed_boat(c):
    """The shared reed boat (reed_boat.py), with hand-off constraints for Nandu and his daughter."""
    boat = reed_boat_prop.build(c.collection)
    for side in ('Nandu hand', 'Daughter hand'):
        hold = boat.constraints.new('CHILD_OF')
        hold.name = side
        hold.influence = 0
    hand = boat.constraints['Nandu hand']
    hand.target, hand.subtarget = c.rig, 'hand.R'
    boat['Usage'] = ('Hand-off between hands: key the influence of "Nandu hand" and "Daughter hand" '
                     '(target the daughter rig\'s hand bone once she exists) with Set Inverse at the switch frame.')
    return boat


# ---------------------------------------------------------------- hand grips

def turn(rig, joint: str, axis: Vec3, degrees: float) -> None:
    bone = rig.pose.bones[joint]
    rest = bone.bone.matrix_local.to_quaternion()
    bone.rotation_mode = 'QUATERNION'
    bone.rotation_quaternion = rest.inverted() @ Quaternion(axis, math.radians(degrees)) @ rest


# finger curls at the knuckle (index..little), thumb fold, thumb oppose, wrist bend.
# The middle and end joints follow the knuckle (x1.1 and x0.7), as real fingers do.
GRIPS: dict[str, tuple[tuple[float, float, float, float], float, float, float]] = {
    'Reach': ((6, 4, 8, 12), -10, 4, -14),
    'Take toy boat': ((30, 34, 38, 42), 24, 22, 4),
    'Hold': ((48, 54, 58, 62), 36, 32, 8),
    'Return toy boat': ((12, 10, 12, 16), 4, 10, -6),
}
SEGMENTS = (('', 1.0), ('_mid', 1.1), ('_tip', .7))
HAND_BONES = tuple(f'{name}.{side}' for side in ('L', 'R')
                   for name in ('hand', 'thumb', 'thumb_mid', 'thumb_tip',
                                *(f'finger_{d:02d}{suffix}' for d in range(1, 5) for suffix, _ in SEGMENTS)))


def apply_grip(rig, name: str, sides: tuple[str, ...] = ('L', 'R')) -> None:
    curls, fold, oppose, wrist = GRIPS[name]
    for side in sides:
        sign = 1 if side == 'L' else -1
        for digit, curl in enumerate(curls, 1):
            for suffix, share in SEGMENTS:
                turn(rig, f'finger_{digit:02d}{suffix}.{side}', (0, sign, 0), curl*share)
        turn(rig, f'thumb.{side}', (1, 0, 0), fold)
        turn(rig, f'thumb_mid.{side}', (0, 0, sign), oppose*.6)
        turn(rig, f'thumb_tip.{side}', (0, 0, sign), oppose*.5)
        turn(rig, f'hand.{side}', (0, 1, 0), sign*wrist)


def clear_hands(rig) -> None:
    for bone in HAND_BONES:
        rig.pose.bones[bone].rotation_mode = 'QUATERNION'
        rig.pose.bones[bone].rotation_quaternion = (1, 0, 0, 0)


def grip_library(c) -> list:
    """Four pose assets for the Pose Library, keyed on both hands."""
    rig = c.rig
    rig.animation_data_create()
    actions = []
    for name in GRIPS:
        action = bpy.data.actions.new(f'Nandu grip | {name}')
        rig.animation_data.action = action
        clear_hands(rig)
        apply_grip(rig, name)
        for bone in HAND_BONES:
            rig.pose.bones[bone].keyframe_insert('rotation_quaternion', frame=1, group=bone)
        action.use_fake_user = True
        action.asset_mark()
        action.asset_data.description = f'Nandu hand pose: {name}. Both hands; apply to one side by selecting its bones.'
        actions.append(action)
    rig.animation_data.action = None
    clear_hands(rig)
    return actions


# ---------------------------------------------------------------- expressions

# Each expression adds to the shared facial controls' own shape-key drivers, so it layers
# with lip sync: control -> (expression weights). Keys found on any mesh of the character.
EXPRESSION_MIX: dict[str, dict[str, float]] = {
    'mouth_worry': {'fear': .9, 'pleading': .8},
    'mouth_smile': {'relief': .55, 'tenderness': .6},
    'Mouth_Ah': {'fear': .22, 'relief': .10},
    'brow_raise': {'fear': .95, 'pleading': .6, 'relief': .25, 'tenderness': .2},
    'brow_frown': {'pleading': .45},
    'blink_L': {'relief': .22, 'tenderness': .28},
    'blink_R': {'relief': .22, 'tenderness': .28},
}


def add_expressions(c) -> int:
    """Fear, pleading, relief and tenderness, layered into the existing control drivers."""
    rig = c.rig
    for name in EXPRESSIONS:
        property_control(rig, name, f'Expression: {name[5:]}')
    changed = 0
    for obj in c.collection.objects:
        keys = obj.data.shape_keys if obj.type == 'MESH' else None
        if keys is None or keys.animation_data is None:
            continue
        for curve in keys.animation_data.drivers:
            driver = curve.driver
            variable = driver.variables.get('value')
            if variable is None or variable.targets[0].id != rig:
                continue
            control = variable.targets[0].data_path.strip('["]')
            mix = EXPRESSION_MIX.get(control)
            if not mix:
                continue
            terms = []
            for label, amount in mix.items():
                extra = driver.variables.new()
                extra.name, extra.type = label, 'SINGLE_PROP'
                extra.targets[0].id = rig
                extra.targets[0].data_path = f'["expr_{label}"]'
                terms.append(f'{label}*{amount}')
            driver.expression = f'min(1, max(0, value + {" + ".join(terms)}))'
            changed += 1
    rig['Expressions'] = ('expr_fear, expr_pleading, expr_relief and expr_tenderness add to the worry, smile, '
                          'jaw, brow and blink shapes, layering with the speech controls for Hindi lip sync.')
    return changed
