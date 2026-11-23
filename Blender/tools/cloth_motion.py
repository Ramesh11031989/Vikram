"""An isolated 24 fps Betal sash test with live cloth, body collisions and wind."""

from math import pi, sin, tau

import bpy
from mathutils import Vector


MOTION_END = 72
PROBE_FRAMES = (1, 18, 30, 42, 54, 66, MOTION_END)


def _sewn_panel(scene, character, rig, original):
    # The top passes through the visible knot. Pleats open gently toward the hem.
    columns, rows = 14, 38
    vertices, faces = [], []
    for row in range(rows):
        v = row / (rows - 1)
        for column in range(columns):
            u = column / (columns - 1)
            crosswise = u - .5
            fold = (.006 + .004 * v) * sin(tau * (3 * u + .24 * v))
            vertices.append(tuple(character.scale * p for p in (
                .154 + .030 * v + crosswise * (.070 + .060 * v) + .012 * sin(pi * v),
                -.155 - .033 * v + .056 * crosswise + fold,
                .964 - .385 * v + .019 * crosswise + .009 * v * sin(pi * u),
            )))
    for row in range(rows - 1):
        for column in range(columns - 1):
            i = row * columns + column
            faces.append((i, i + columns, i + columns + 1, i + 1))

    mesh = bpy.data.meshes.new('Betal sash • sewn grid')
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh.materials.append(original.data.materials[0])
    uv = mesh.uv_layers.new(name='Weave UV')
    for polygon in mesh.polygons:
        polygon.use_smooth = True
        for loop in polygon.loop_indices:
            row, column = divmod(mesh.loops[loop].vertex_index, columns)
            uv.data[loop].uv = (column / (columns - 1), row / (rows - 1))

    cloth = bpy.data.objects.new('Betal sash • simulated cotton', mesh)
    scene.collection.objects.link(cloth)
    cloth.parent = rig
    hips = cloth.vertex_groups.new(name='hips')
    hips.add(list(range(len(vertices))), 1, 'REPLACE')
    pins = cloth.vertex_groups.new(name='Pinned beneath knot')
    pins.add(list(range(columns)), 1, 'REPLACE')
    pins.add(list(range(columns, columns * 2)), .82, 'REPLACE')
    pins.add(list(range(columns * 2, columns * 3)), .24, 'REPLACE')

    armature = cloth.modifiers.new('Waist attachment', 'ARMATURE')
    armature.object = rig
    simulation = cloth.modifiers.new('Cotton cloth', 'CLOTH')
    settings = simulation.settings
    settings.vertex_group_mass = pins.name
    settings.quality = 10
    settings.mass = .025
    settings.air_damping = 2
    settings.tension_stiffness = 29
    settings.compression_stiffness = 19
    settings.shear_stiffness = 8
    settings.bending_stiffness = .13
    settings.effector_weights.wind = 22
    collisions = simulation.collision_settings
    collisions.use_collision = True
    collisions.distance_min = .004
    collisions.collision_quality = 5
    collisions.use_self_collision = True
    collisions.self_distance_min = .003
    simulation.point_cache.frame_start = 1
    simulation.point_cache.frame_end = MOTION_END
    simulation.point_cache.use_disk_cache = False

    smooth = cloth.modifiers.new('Soft fold contours', 'SUBSURF')
    smooth.levels = smooth.render_levels = 1
    thickness = cloth.modifiers.new('Woven edge thickness', 'SOLIDIFY')
    thickness.thickness = .0012
    cloth['Motion'] = 'Pinned sash tail, with an animated wind and collisions against the dhoti and waist wrap.'
    return cloth


def _wind():
    bpy.ops.object.effector_add(type='WIND', location=(-.82, .53, .39))
    wind = bpy.context.object
    wind.name = 'Gust • across sash'
    wind.rotation_euler = (Vector((.23, -.18, .92)) - wind.location).to_track_quat('Z', 'Y').to_euler()
    wind.field.flow = .8
    wind.field.wind_factor = .11
    for frame, strength in ((1, 0), (10, 0), (19, 22), (29, 180), (40, 57),
                            (47, 5), (56, 123), (66, 22), (MOTION_END, 0)):
        wind.field.strength = strength
        wind.field.keyframe_insert(data_path='strength', frame=frame)
    return wind


def attach_motion(scene, character, rig, clones=None):
    """Replace the posed scene's static sash tail with a draped cloth test."""
    bpy.context.window.scene = scene
    scene.frame_start = 1
    scene.frame_end = MOTION_END
    scene.render.fps = 24
    scene.sync_mode = 'NONE'
    clones = tuple(rig.children if clones is None else clones)
    tail = next(part for part in clones if 'Shawl | uneven sash tail' in part.name)
    colliders = [part for part in clones if 'Dhoti | pleated leg' in part.name
                 or 'Sash | folded waist wrap' in part.name]
    if len(colliders) != 3:
        raise ValueError('Cloth scene needs the two visible dhoti legs and the waist wrap')
    cloth = _sewn_panel(scene, character, rig, tail)
    bpy.data.objects.remove(tail, do_unlink=True)
    for part in colliders:
        part.modifiers.new('Sash collision surface', 'COLLISION')
        part.collision.thickness_outer = .003
        part.collision.cloth_friction = 4
    _wind()
    for frame, name in ((1, 'At rest'), (10, 'Air picks up'), (29, 'First gust'),
                        (47, 'Easing'), (56, 'Second gust'), (72, 'Gust easing')):
        scene.timeline_markers.new(name, frame=frame)
    scene.frame_set(1)
    return cloth


def _positions(scene, cloth, frames):
    cache = {}
    for frame in frames:
        scene.frame_set(frame)
        mesh = cloth.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        cache[frame] = [vertex.co.copy() for vertex in mesh.vertices]
    return cache


def bake_and_verify(scene, cloth):
    """Bake into the .blend and measure the displacement at the same vertex indices."""
    bpy.context.window.scene = scene
    cache = cloth.modifiers['Cotton cloth'].point_cache
    bpy.ops.object.select_all(action='DESELECT')
    cloth.select_set(True)
    bpy.context.view_layer.objects.active = cloth
    scene.frame_set(scene.frame_start)
    with bpy.context.temp_override(point_cache=cache):
        status = bpy.ops.ptcache.bake(bake=True)
    if 'FINISHED' not in status or not cache.is_baked:
        raise RuntimeError('Could not bake the sash wind test')
    positions = _positions(scene, cloth, PROBE_FRAMES)
    displacements = {frame: max((point - rest).length for point, rest in zip(points, positions[1]))
                     for frame, points in positions.items()}
    peak = max(displacements, key=displacements.get)
    if not .035 <= displacements[peak] <= .48:
        raise RuntimeError(f'Unexpected sash displacement: {displacements[peak]:.3f}m')
    cloth['Peak sampled displacement (m)'] = round(displacements[peak], 4)
    cloth['Peak sampled frame'] = peak
    print('Betal sash travel by frame (cm): ' + ', '.join(
        f'{frame}={travel * 100:.1f}' for frame, travel in displacements.items()), flush=True)
    scene.frame_set(1)
    return displacements
