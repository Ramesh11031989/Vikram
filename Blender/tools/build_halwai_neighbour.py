"""Builds the Halwai's neighbour witness package.

Ramesh's row for her: "रस्सी काटते समय हाथ, रस्सी और गाय का आकार आपस में मेल खाएँ"
(when she cuts the rope, her hands, the rope and the cow must match in size).

Run with Blender 4.2+ (or the bpy module):

    blender --background --python Blender/tools/build_halwai_neighbour.py

It builds her (halwai_neighbour.py), the Malvi-type cow (cattle.py) and the tether,
peg and sickle (tether_props.py), all at real scale, then:

* stages the rope-cutting moment: her left fist holds the lead up, her right hand
  hooks the sickle behind it a hand's width from the knot, the cut rope beside it;
* writes Blender/HalwaiNeighbour_Witness.blend with one scene per review
  (character, rope cut, scale sheet);
* exports CH_HalwaiNeighbour.fbx, AN_MalviCow.fbx and PR_Tether.fbx to Blender/Exports;
* renders previews and a scale check (JSON) to Blender/Previews.

Pass --no-render to skip the preview renders, --samples N to change their quality.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import bpy
from mathutils import Matrix, Quaternion, Vector

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import build_cast            # noqa: E402
import cattle                # noqa: E402
import halwai_neighbour as hn  # noqa: E402
import tether_props as tp    # noqa: E402

ROOT = TOOLS.parent
NAME = 'HalwaiNeighbour'
EXPORTS = ROOT/'Exports'
PREVIEWS = ROOT/'Previews'/NAME

# The staged moment (metres, world space; the cow faces -y with her left side toward +x)
STAND = Vector((.46, -.98, 0.0))       # where the neighbour stands, facing the cow's neck (-x)
FIST = Vector((.29, -1.12, .80))       # her left fist holding the lead up
CUT_FRACTION = .62                     # the cut, as a fraction of the way from the knot to her fist
ROPE_GRIP = (.089, .020)               # rope centre from the wrist: along the hand, toward the palm (m)
HANDLE_GRIP = (.086, .027)             # sickle handle centre from the wrist


# ------------------------------------------------------------------ posing

def _frame(y_axis: Vector, z_hint: Vector) -> Matrix:
    y = y_axis.normalized()
    z = (z_hint - y*z_hint.dot(y)).normalized()
    x = y.cross(z)
    return Matrix((x, y, z)).transposed()


def set_bone(rig, name: str, head: Vector, y_axis: Vector, z_hint: Vector) -> None:
    """Pose a bone so its head, direction and roll are as given (world space)."""
    world = _frame(y_axis, z_hint).to_4x4()
    world.translation = head
    rig.pose.bones[name].matrix = rig.matrix_world.inverted() @ world
    bpy.context.view_layer.update()


def bone_world(rig, name: str) -> Matrix:
    return rig.matrix_world @ rig.pose.bones[name].matrix


def reach(rig, side: str, wrist: Vector, elbow_hint: Vector, hand_y: Vector, hand_z: Vector) -> float:
    """Two-bone arm IK to a wrist target, then the hand set to the given frame. Returns the miss (m)."""
    upper, fore = f'upper_arm.{side}', f'forearm.{side}'
    shoulder = bone_world(rig, upper).translation
    l1 = rig.pose.bones[upper].bone.length
    l2 = rig.pose.bones[fore].bone.length
    span = wrist - shoulder
    d = min(span.length, (l1 + l2)*.995)
    axis = span.normalized()
    bend = (elbow_hint - axis*elbow_hint.dot(axis)).normalized()
    a = (l1*l1 - l2*l2 + d*d)/(2*d)
    elbow = shoulder + axis*a + bend*math.sqrt(max(l1*l1 - a*a, 0.0))
    reached = shoulder + axis*d
    current = bone_world(rig, upper).to_3x3()
    y1 = (elbow - shoulder).normalized()
    z1 = current.col[1].rotation_difference(y1) @ current.col[2]
    set_bone(rig, upper, shoulder, y1, z1)
    current = bone_world(rig, fore).to_3x3()
    y2 = (reached - elbow).normalized()
    z_min = current.col[1].rotation_difference(y2) @ current.col[2]
    z_hand = hand_z - y2*hand_z.dot(y2)
    set_bone(rig, fore, elbow, y2, z_min.normalized() + z_hand.normalized()*.7)   # forearm shares the twist
    set_bone(rig, f'hand.{side}', reached, hand_y, hand_z)
    return (reached - wrist).length


def curl(rig, side: str, fingers: Sequence[float], thumb: Sequence[float]) -> None:
    """Close a hand: degrees at the three finger joints (MCP, PIP, DIP) and thumb (base, mid, tip)."""
    sign = 1 if side == 'L' else -1
    for digit in (1, 2, 3, 4):
        spread = (digit - 2.5)*.06                  # the little finger curls a touch more
        for segment, angle in zip(('', '_mid', '_tip'), fingers):
            build_cast.turn(rig, f'finger_{digit:02d}{segment}.{side}', (0, sign, 0), angle*(1 + spread))
    base, mid, tip = thumb
    build_cast.turn(rig, f'thumb.{side}', (1, 0, 0), base)
    build_cast.turn(rig, f'thumb_mid.{side}', (0, 0, sign), mid)
    build_cast.turn(rig, f'thumb_tip.{side}', (0, 0, sign), tip)
    bpy.context.view_layer.update()


def stand_and_lean(rig) -> None:
    """Her rig turned to face the cow's neck, bent a little at the waist, looking down at the rope."""
    rig.location = STAND
    rig.rotation_euler = (0, 0, -math.pi/2)
    for bone, degrees in (('spine', 9), ('chest', 7), ('neck', 9), ('head', 14)):
        build_cast.turn(rig, bone, (1, 0, 0), degrees)
    for side, sign in (('L', 1), ('R', -1)):
        build_cast.turn(rig, f'thigh.{side}', (1, 0, 0), -6)
        build_cast.turn(rig, f'shin.{side}', (1, 0, 0), 12)
        build_cast.turn(rig, f'foot.{side}', (1, 0, 0), -6)
    bpy.context.view_layer.update()


def stage_cut(neighbour, cow, collection) -> Dict[str, object]:
    """Pose her cutting the lead and build the rope and sickle to match. Returns the staging data."""
    rig = neighbour.rig
    stand_and_lean(rig)
    # The intact tether shows where the knot sits; the cut is a fixed share of the way to her fist
    probe = bpy.data.collections.new('probe')
    whole = tp.build_tether(cow, probe, cut=False, via=FIST)
    knot = Vector(whole['knot'])
    for obj in list(probe.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(probe)
    rope = tp.build_tether(cow, collection, cut=True, via=FIST, cut_from_knot=(FIST - knot).length*CUT_FRACTION)
    cut = Vector(rope['cut_point'])
    along = Vector(rope['cut_direction']).normalized()                       # from the knot toward her fist
    # Left fist round the lead: the rope runs across the palm, index side toward the knot
    lead = (FIST - knot).normalized()
    shoulder_l = bone_world(rig, 'upper_arm.L').translation
    hand_y = (FIST - shoulder_l)
    hand_y = (hand_y - lead*hand_y.dot(lead)).normalized()
    x_l = -lead
    z_l = x_l.cross(hand_y)
    wrist_l = FIST - hand_y*ROPE_GRIP[0] + z_l*ROPE_GRIP[1]
    miss_l = reach(rig, 'L', wrist_l, Vector((.3, -.6, -.4)), hand_y, z_l)
    curl(rig, 'L', (66, 92, 58), (38, 28, 32))
    # Sickle: hooked behind the lead from the cow's side, its edge facing her, pulled toward her
    sickle = tp.build_sickle(collection)
    edge = Vector(sickle['edge_point'])
    edge_normal = Vector(sickle['edge_normal'])
    grip = Vector(sickle['grip_point'])
    toward_her = Vector((1, 0, .15)).normalized()
    shoulder_r = bone_world(rig, 'upper_arm.R').translation
    arm_r = rig.pose.bones['upper_arm.R'].bone.length + rig.pose.bones['forearm.R'].bone.length

    blade_local = Matrix((edge_normal, Vector((0, 0, 1)), edge_normal.cross(Vector((0, 0, 1)))))

    def sickle_pose(plane: Vector, pull: Vector) -> Tuple[Matrix, Vector, Vector, Vector]:
        """The sickle with its blade plane normal to `plane` and its edge facing `pull`, the edge resting
        on the rope at the cut; and her right wrist target round its handle."""
        frame = Matrix((pull, plane, pull.cross(plane))).transposed() @ blade_local
        origin = cut + (frame @ -edge_normal)*tp.ROPE_DIAMETER*.5 - frame @ edge
        world = Matrix.Translation(origin) @ frame.to_4x4()
        # Right fist round the handle: the handle runs across the palm, the blade out of the index side
        x_r = -(frame @ Vector((0, 1, 0))).normalized()               # right hand: index side is -x
        grip_world = world @ grip
        hand_y_r = grip_world - shoulder_r
        hand_y_r = (hand_y_r - x_r*hand_y_r.dot(x_r)).normalized()
        z_r = x_r.cross(hand_y_r)
        return world, grip_world - hand_y_r*HANDLE_GRIP[0] + z_r*HANDLE_GRIP[1], hand_y_r, z_r

    # A hooked cut: the lead passes through the crescent across the blade (the blade plane square to
    # the rope) and the edge pulls toward her. Turn the pull round the rope and tilt the blade as little
    # as possible so her right wrist lands with the elbow still bent (80 to 90% of the arm's length),
    # clear in front of her skirt and no lower than her hip.
    front = -(rig.matrix_world.to_3x3() @ Vector((0, 1, 0))).normalized()
    pull0 = (toward_her - along*toward_her.dot(along)).normalized()
    best: Tuple[float, Tuple[Vector, Vector], Tuple[float, ...]] = (math.inf, (along, pull0), (0.0,))
    for sign in (1, -1):
        for turn in range(-90, 91, 5):
            pull = Quaternion(along, math.radians(turn)) @ pull0
            for tilt in range(-30, 31, 6):
                plane = Quaternion(pull, math.radians(tilt)) @ (along*sign)
                wrist = sickle_pose(plane, pull)[1]
                span = (wrist - shoulder_r).length/arm_r
                ahead = (wrist - Vector((STAND[0], STAND[1], wrist.z))).dot(front)
                score = (40*max(0.0, span - .90) + 4*max(0.0, .80 - span) + 20*max(0.0, .22 - ahead)
                         + 20*max(0.0, .84 - wrist.z) + .004*(abs(turn) + abs(tilt)))
                if score < best[0]:
                    best = (score, (plane, pull), (sign, turn, tilt, span, ahead, wrist.z))
    print('sickle (side, turn, tilt, arm span, ahead, wrist z):', [round(v, 3) for v in best[2]],
          'score', round(best[0], 3))
    world, wrist_r, hand_y_r, z_r = sickle_pose(*best[1])
    sickle.matrix_world = world
    bpy.context.view_layer.update()
    miss_r = reach(rig, 'R', wrist_r, Vector((.4, .6, -.3)), hand_y_r, z_r)
    curl(rig, 'R', (56, 76, 46), (36, 22, 26))
    # The sickle rides her right hand from now on
    hand_r = bone_world(rig, 'hand.R')
    world = sickle.matrix_world.copy()
    sickle.parent = rig
    sickle.parent_type = 'BONE'
    sickle.parent_bone = 'hand.R'
    bpy.context.view_layer.update()
    sickle.matrix_world = world
    return {'knot': knot, 'cut': cut, 'cut_direction': along, 'fist': FIST, 'sickle': sickle,
            'rope': rope, 'miss_left_m': miss_l, 'miss_right_m': miss_r, 'hand_r': hand_r}


# ------------------------------------------------------------------ scenes

def daylight(scene, strength: float = 3.2) -> None:
    """Late-morning Malwa sun with a hazy sky."""
    scene.world = bpy.data.worlds.new(f'{scene.name} • Sky')
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get('Background')
    background.inputs['Color'].default_value = (.42, .52, .66, 1)
    background.inputs['Strength'].default_value = .85
    sun = bpy.data.lights.new(f'{scene.name} • Sun', 'SUN')
    sun.energy = strength
    sun.angle = math.radians(1.2)
    sun.color = (1.0, .93, .82)
    obj = bpy.data.objects.new(sun.name, sun)
    scene.collection.objects.link(obj)
    obj.rotation_euler = (math.radians(45), 0, math.radians(45))    # from behind the review cameras, high
    scene.view_settings.view_transform = 'AgX'
    try:
        scene.view_settings.look = 'AgX - Medium High Contrast'
    except TypeError:
        pass
    scene.view_settings.exposure = -.35


def earth_ground(scene, size: float = 14.0) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(f'{scene.name} • Ground')
    h = size/2
    mesh.from_pydata([(-h, -h, 0), (h, -h, 0), (h, h, 0), (-h, h, 0)], [], [(0, 1, 2, 3)])
    obj = bpy.data.objects.new(mesh.name, mesh)
    scene.collection.objects.link(obj)
    m = bpy.data.materials.get('Packed village earth') or bpy.data.materials.new('Packed village earth')
    m.use_nodes = True
    nodes, links = m.node_tree.nodes, m.node_tree.links
    shader = nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value = .95
    noise = nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 3.0
    noise.inputs['Detail'].default_value = 10
    ramp = nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (.16, .11, .07, 1)
    ramp.color_ramp.elements[1].color = (.33, .25, .17, 1)
    links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
    links.new(ramp.outputs['Color'], shader.inputs['Base Color'])
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .4
    grit = nodes.new('ShaderNodeTexNoise')
    grit.inputs['Scale'].default_value = 180
    links.new(grit.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    mesh.materials.append(m)
    return obj


def review_scene(name: str, collections: Sequence[bpy.types.Collection], samples: int,
                 size: Tuple[int, int] = (1600, 1000)) -> bpy.types.Scene:
    scene = bpy.data.scenes.new(f'HN • {name}')
    build_cast.setup_stage(scene, size[0], size[1], samples, .8)
    for collection in collections:
        scene.collection.children.link(collection)
    daylight(scene)
    earth_ground(scene)
    scene.render.film_transparent = False
    return scene


def camera(scene, location: Sequence[float], target: Sequence[float], lens: float) -> bpy.types.Object:
    data = bpy.data.cameras.new(f'{scene.name} • Camera')
    data.lens = lens
    data.clip_start = .02
    obj = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(obj)
    obj.location = location
    build_cast.aim(obj, target)
    scene.camera = obj
    return obj


def ruler(collection, start: Vector, length: float, step: float = .10, name: str = 'Scale ruler') -> None:
    """A black and white staff in decimetres for the scale sheet."""
    white = tp.principled('Ruler white', (.80, .80, .78), .6)
    black = tp.principled('Ruler black', (.02, .02, .02), .6)
    count = int(round(length/step))
    for i in range(count):
        mesh = bpy.data.meshes.new(f'{name} {i}')
        z0, z1 = start.z + i*step, start.z + (i + 1)*step
        w = .025
        verts = [(start.x - w, start.y - w, z0), (start.x + w, start.y - w, z0), (start.x + w, start.y + w, z0),
                 (start.x - w, start.y + w, z0), (start.x - w, start.y - w, z1), (start.x + w, start.y - w, z1),
                 (start.x + w, start.y + w, z1), (start.x - w, start.y + w, z1)]
        faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        mesh.from_pydata(verts, [], faces)
        mesh.materials.append(white if i % 2 else black)
        collection.objects.link(bpy.data.objects.new(mesh.name, mesh))


def a_pose(rig) -> None:
    rig.location = (0, 0, 0)
    rig.rotation_euler = (0, 0, 0)
    for bone in rig.pose.bones:
        bone.rotation_mode = 'QUATERNION'
        bone.rotation_quaternion = (1, 0, 0, 0)
        bone.location = (0, 0, 0)
    for side, sign in (('L', 1), ('R', -1)):
        build_cast.turn(rig, f'clavicle.{side}', (0, 1, 0), sign*7)
        build_cast.turn(rig, f'upper_arm.{side}', (0, 1, 0), sign*66)
        build_cast.turn(rig, f'forearm.{side}', (0, 0, 1), sign*-12)
        curl(rig, side, (14, 18, 10), (8, 6, 6))           # relaxed, slightly curled fingers
    bpy.context.view_layer.update()


def keep_pose(rig, name: str) -> bpy.types.Action:
    """Store the current pose as a one-frame action (so each review pose survives in the .blend)."""
    if rig.animation_data is None:
        rig.animation_data_create()
    action = bpy.data.actions.new(f'HN_{name}')
    action.use_fake_user = True
    rig.animation_data.action = action
    for bone in rig.pose.bones:
        bone.keyframe_insert('rotation_quaternion', frame=1, group=bone.name)
        bone.keyframe_insert('location', frame=1, group=bone.name)
    return action                  # the rig's own placement stays free (set per review scene)


# ------------------------------------------------------------------ measurements

def measure(neighbour, cow, stage: Dict[str, object]) -> Dict[str, object]:
    rig = neighbour.rig
    arm = rig.data.bones
    s = neighbour.scale
    hand_len = (arm['finger_02_tip.L'].tail_local - arm['hand.L'].head_local).length
    breadth = (arm['finger_01.L'].head_local - arm['finger_04.L'].head_local).length + (.0094 + .0079)*s
    finger_width = 2*.0097*s
    loop = cattle.neck_loop(cow)
    girth = sum((loop[i] - loop[i - 1]).length for i in range(len(loop)))
    sickle = stage['sickle']
    to_sickle = sickle.matrix_world.inverted()
    corners = [to_sickle @ (part.matrix_world @ Vector(c)) for part in sickle.children for c in part.bound_box]
    sickle_len = max(c.y for c in corners) - min(c.y for c in corners)     # heel of the handle to the blade's far end
    data = {
        'neighbour_stature_m': round(float(rig.get('Stature_m', 1.54)), 3),
        'hand_length_wrist_to_middle_tip_m': round(hand_len, 4),
        'hand_breadth_m': round(breadth, 4),
        'finger_width_m': round(finger_width, 4),
        'rope_diameter_m': tp.ROPE_DIAMETER,
        'rope_to_finger_width': round(tp.ROPE_DIAMETER/finger_width, 2),
        'fist_closes_round_rope': tp.ROPE_DIAMETER < finger_width*1.2,
        'sickle_overall_m': round(sickle_len, 3),
        'sickle_handle_m': .122,
        'sickle_handle_diameter_m': .030,
        'handle_to_hand_breadth': round(.122/breadth, 2),
        'cow_withers_m': cattle.WITHERS,
        'cow_neck_girth_at_rope_m': round(girth, 3),
        'knot_height_m': round(Vector(stage['knot']).z, 3),
        'cut_height_m': round(Vector(stage['cut']).z, 3),
        'cut_from_knot_m': round((Vector(stage['cut']) - Vector(stage['knot'])).length, 3),
        'left_fist_reach_miss_m': round(float(stage['miss_left_m']), 4),
        'right_fist_reach_miss_m': round(float(stage['miss_right_m']), 4),
        'neighbour_to_withers': round(float(rig.get('Stature_m', 1.54))/cattle.WITHERS, 2),
    }
    # reference ranges (guesses, see the notes): adult woman's hand 16.5 to 18.5 cm, breadth 7 to 8.5 cm
    data['checks'] = {
        'hand_length_ok': .155 <= hand_len <= .19,
        'hand_breadth_ok': .068 <= breadth <= .088,
        'hands_reach_their_grips': max(stage['miss_left_m'], stage['miss_right_m']) < .01,
        'handle_fits_the_fist': .122 >= breadth*1.2,
    }
    return data


# ------------------------------------------------------------------ export

def export_fbx(objects: Sequence[bpy.types.Object], filename: str) -> Path:
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    path = EXPORTS/filename
    result = bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={'ARMATURE', 'MESH', 'EMPTY'},
                                      axis_forward='-Z', axis_up='Y', apply_scale_options='FBX_SCALE_UNITS',
                                      use_mesh_modifiers=False, add_leaf_bones=False, bake_anim=False,
                                      mesh_smooth_type='FACE')
    if 'FINISHED' not in result or path.stat().st_size < 1024:
        raise RuntimeError(f'FBX export failed: {path}')
    return path


def render(scene, path: Path) -> None:
    bpy.context.window.scene = scene
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    if not path.is_file():
        raise RuntimeError(f'Render missing: {path}')


# ------------------------------------------------------------------ main

def main(argv: Sequence[str]) -> None:
    samples = int(argv[argv.index('--samples') + 1]) if '--samples' in argv else 96
    do_render = '--no-render' not in argv
    review_renders = do_render and '--cut-only' not in argv       # --cut-only re-renders just the rope-cut shots
    EXPORTS.mkdir(exist_ok=True)
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    neighbour = hn.build()
    cow = cattle.build()
    props = bpy.data.collections.new('PR_Tether')
    props.asset_mark()
    props.asset_data.description = 'Jute tether (14 mm, intact and cut), peg and sickle | real scale'
    staged = bpy.data.collections.new('PR_RopeCut')
    peg = tp.build_peg(props)
    intact = tp.build_tether(cow, props, cut=False)
    tp.parent_loop_to_neck(cow, intact['rope'])
    # Exports in the rest pose, before any staging
    bpy.context.window.scene = neighbour.scene
    export_fbx([neighbour.rig] + neighbour.parts, f'CH_{NAME}.fbx')
    bpy.context.window.scene = cow.scene
    export_fbx([cow.rig] + [p for p in cow.parts if p.type == 'MESH'], 'AN_MalviCow.fbx')
    # Review scenes in the A-pose
    a_pose(neighbour.rig)
    keep_pose(neighbour.rig, 'A_Pose')
    character = review_scene('Character', [neighbour.collection], samples, (1600, 1000))
    shots: List[Tuple[bpy.types.Scene, Tuple, Tuple, float, str]] = [
        (character, (0, -5.2, 1.0), (0, 0, .80), 55, 'front'),
        (character, (3.4, -3.9, 1.1), (0, 0, .80), 55, 'three_quarter'),
        (character, (5.2, 0, 1.0), (0, 0, .80), 55, 'side'),
        (character, (0, 5.2, 1.0), (0, 0, .80), 55, 'back'),
        (character, (.20, -1.05, 1.44), (0, -.03, 1.40), 85, 'portrait'),
    ]
    scale = review_scene('Scale sheet', [neighbour.collection, cow.collection, props], samples, (1800, 1000))
    ruler(scale.collection, Vector((0, -2.35, 0)), 2.0)
    beside_cow = (Vector((-.15, -1.75, 0)), -math.pi/2)      # in front of the cow's head, facing the camera
    # Rope-cut staging (her pose changes, so the A-pose renders go first)
    for scene, loc, target, lens, tag in shots:          # the cameras stay in the .blend either way
        camera(scene, loc, target, lens)
        if review_renders:
            render(scene, PREVIEWS/f'{NAME}_{tag}.png')
    camera(scale, (-6.6, -.75, .90), (0, -.75, .78), 38)
    if review_renders:
        neighbour.rig.location, neighbour.rig.rotation_euler = beside_cow[0], (0, 0, beside_cow[1])
        render(scale, PREVIEWS/f'{NAME}_scale_sheet.png')
        neighbour.rig.location, neighbour.rig.rotation_euler = (0, 0, 0), (0, 0, 0)
    cut_scene = review_scene('Rope cut', [neighbour.collection, cow.collection, staged], samples, (1600, 1000))
    for obj in [peg] + [o for o in peg.children]:
        staged.objects.link(obj)
    neighbour.rig.animation_data.action = None          # pose freely; the A-pose stays in its action
    stage = stage_cut(neighbour, cow, staged)
    keep_pose(neighbour.rig, 'Rope_Cut')
    intact['rope'].hide_render = True
    intact['rope'].hide_viewport = True
    grip_r = stage['sickle'].matrix_world @ Vector(stage['sickle']['grip_point'])
    focus = (FIST + Vector(stage['cut']) + grip_r)/3
    close = camera(cut_scene, tuple(focus + Vector((-.12, -.42, .52))), tuple(focus), 38)   # above her hands
    if do_render:
        render(cut_scene, PREVIEWS/f'{NAME}_rope_cut_close.png')
        close.location = (-.75, -2.55, 1.30)          # from the cow's head side: her face, both hands, the rope
        build_cast.aim(close, (.24, -.98, .92))
        close.data.lens = 40
        render(cut_scene, PREVIEWS/f'{NAME}_rope_cut_medium.png')
    intact['rope'].hide_render = False
    intact['rope'].hide_viewport = False
    # The props get their own scene, so every rope piece is in the active view layer for the export
    prop_scene = review_scene('Props', [props, staged], samples, (1600, 1000))
    bpy.context.window.scene = prop_scene
    rope_parts = list(dict.fromkeys(o for o in list(props.objects) + list(staged.objects) if o.type == 'MESH'))
    export_fbx(rope_parts, 'PR_Tether.fbx')
    report = measure(neighbour, cow, stage)
    (PREVIEWS/f'{NAME}_scale_check.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2))
    bpy.context.window.scene = cut_scene
    bpy.context.preferences.filepaths.save_version = 0
    result = bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/f'{NAME}_Witness.blend'), compress=True)
    if 'FINISHED' not in result:
        raise RuntimeError('Could not save the witness file')


if __name__ == '__main__':
    main(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
