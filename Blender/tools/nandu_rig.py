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
        head = centre + Vector((sign*.036, 0, 0))
        item.head, item.tail = head*s, (head+Vector((0, -.11, 0)))*s
        # Bone Z points away from the centre, so the palm (-Z of the hand) faces in.
        item.align_roll(Vector((sign, 0, 0)))
        item.parent = bind
        item.use_deform = True
        pole = bones.new(f'elbow_pole.{side}')
        pole.head = Vector((sign*.34, .18, .72))*s
        pole.tail = Vector((sign*.34, .18, .77))*s
        pole.parent = bones['chest']
        pole.use_deform = False
    bpy.ops.object.mode_set(mode='OBJECT')

    property_control(rig, TIED, '1 = wrists bound with jute rope in front of the body, 0 = free hands')
    for side in ('L', 'R'):
        forearm = rig.pose.bones[f'forearm.{side}']
        ik = forearm.constraints.new('IK')
        ik.name = 'Tied wrists IK'
        ik.target, ik.subtarget = rig, f'wrist_bind.{side}'
        ik.pole_target, ik.pole_subtarget = rig, f'elbow_pole.{side}'
        ik.pole_angle = math.radians(-90)
        ik.chain_count = 2
        ik.use_stretch = False
        prop_driver(ik, 'influence', rig, TIED)
        hand = rig.pose.bones[f'hand.{side}']
        rotation = hand.constraints.new('COPY_ROTATION')
        rotation.name = 'Tied wrists orientation'
        rotation.target, rotation.subtarget = rig, f'wrist_bind.{side}'
        prop_driver(rotation, 'influence', rig, TIED)
    rig['Wrist_states'] = ('Set wrists_tied to 1 for the bound state. Move the wrist_bind bone to place '
                           'both hands; elbow_pole.L/R aim the elbows. 0 frees the hands with no rebuild.')


def wrist_rope(c, rope) -> None:
    s = c.scale
    centre = Vector((0, -.25, 1.08))
    parts = []
    for side, sign in (('L', 1), ('R', -1)):
        wrist = centre + Vector((sign*.036, 0, 0))
        for index, (dy, radius) in enumerate(((.012, .033), (.026, .034), (.040, .032))):
            loop = [(wrist.x + radius*math.cos(math.tau*j/28), wrist.y + dy + .003*math.sin(3*math.tau*j/28),
                     wrist.z + radius*.88*math.sin(math.tau*j/28)) for j in range(28)]
            parts.append(c.tube(f'Jute wrist rope {side} {index+1}', loop, .0052, rope,
                                f'wrist_bind.{side}', cyclic=True))
    # Figure-eight binding between the wrists, a knot and the lead end a guard can hold.
    for index, z in enumerate((.026, -.026)):
        parts.append(c.tube(f'Jute rope crossing {index+1}',
                            [(-.040, -.224, 1.08+z), (0, -.236, 1.08+z*.25), (.040, -.224, 1.08-z)],
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
            verts.append(Vector((x+(t-.5)*width*2, y-.004*math.cos(t*math.tau*2), z+(t-.5)*.016))*s)
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


# finger curls (index..little), thumb fold, thumb oppose, wrist bend
GRIPS: dict[str, tuple[tuple[float, float, float, float], float, float, float]] = {
    'Reach': ((6, 4, 8, 12), -10, 4, -14),
    'Take toy boat': ((34, 40, 44, 48), 26, 22, 4),
    'Hold': ((62, 70, 74, 76), 42, 34, 8),
    'Return toy boat': ((14, 12, 14, 18), 4, 10, -6),
}
HAND_BONES = tuple(f'{name}.{side}' for side in ('L', 'R')
                   for name in ('hand', 'thumb', 'finger_01', 'finger_02', 'finger_03', 'finger_04'))


def apply_grip(rig, name: str, sides: tuple[str, ...] = ('L', 'R')) -> None:
    curls, fold, oppose, wrist = GRIPS[name]
    for side in sides:
        sign = 1 if side == 'L' else -1
        for digit, curl in enumerate(curls, 1):
            turn(rig, f'finger_{digit:02d}.{side}', (0, 1, 0), sign*curl)
        thumb = rig.pose.bones[f'thumb.{side}']
        rest = thumb.bone.matrix_local.to_quaternion()
        thumb.rotation_mode = 'QUATERNION'
        rotation = Quaternion((1, 0, 0), math.radians(fold)) @ Quaternion((0, 0, 1), math.radians(-sign*oppose))
        thumb.rotation_quaternion = rest.inverted() @ rotation @ rest
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

def _mouth_shape(point: Vector, scale: float, corner: float, widen: float, part: float) -> Vector:
    side = min(1, abs(point.x)/(.034*scale))**2
    point.z += corner*scale*side
    point.x *= widen
    if point.z < 1.566*scale:
        point.z -= part*scale*(1-side*.6)
    return point


def add_expressions(c) -> None:
    """Fear, pleading, relief and tenderness, each one rig property driving several shapes."""
    rig, s = c.rig, c.scale
    for name in EXPRESSIONS:
        property_control(rig, name, f'Expression: {name[5:]}')
    mouth = bpy.data.objects[f'{c.name}_Mouth']
    shapes: dict[str, tuple[float, float, float]] = {
        'Fear': (-.0065, 1.08, .0045), 'Pleading': (-.0055, .96, .0018),
        'Relief': (.0040, 1.03, .0014), 'Tenderness': (.0048, .95, 0),
    }
    for label, (corner, widen, part) in shapes.items():
        key = shape_from_delta(mouth, f'Expr_{label}',
                               lambda p, a=corner, b=widen, d=part: _mouth_shape(p, s, a, b, d))
        driver_from_property(key, rig, f'expr_{label.lower()}')
    for side, sign in (('L', 1), ('R', -1)):
        brow = bpy.data.objects[f'{c.name}_Brow.{side}']
        centre = .053*c.spec['face_width']*s

        def inner(point: Vector) -> Vector:
            weight = max(0, min(1, (centre+.02*s - abs(point.x))/(.05*s)))
            point.z += .009*s*weight
            point.x -= sign*.002*s*weight
            return point
        key = shape_from_delta(brow, 'Inner raise', inner)
        _multi_driver(key, rig, 'min(1, fear + pleading*.9 + relief*.25 + tenderness*.35)')
        for label in ('Eye', 'Iris', 'Eyelids'):
            obj = bpy.data.objects[f'{c.name}_{label}.{side}']

            def wide(point: Vector) -> Vector:
                point.z = 1.675*s + (point.z-1.675*s)*1.16 if point.z > 1.675*s else point.z
                return point

            def soft(point: Vector) -> Vector:
                point.z = 1.675*s + (point.z-1.675*s)*(.74 if point.z > 1.675*s else .9)
                return point
            _multi_driver(shape_from_delta(obj, 'Wide', wide), rig, 'min(1, fear)')
            _multi_driver(shape_from_delta(obj, 'Soft', soft), rig, 'min(1, relief*.8 + tenderness)')
    rig['Expressions'] = ('expr_fear, expr_pleading, expr_relief and expr_tenderness drive mouth, brow and eye '
                          'shapes together. They layer with the eight viseme controls for Hindi lip sync.')


def _multi_driver(block, rig, expression: str) -> None:
    curve = block.driver_add('value')
    driver = curve.driver
    driver.type = 'SCRIPTED'
    for name in EXPRESSIONS:
        variable = driver.variables.new()
        variable.name = name[5:]
        variable.type = 'SINGLE_PROP'
        variable.targets[0].id = rig
        variable.targets[0].data_path = f'["{name}"]'
    driver.expression = expression

