"""Export the validated ghat sightline scene to FBX geometry and a Unity timeline manifest.

Open Production/E01/Sightlines/E01_Ghat_Sightlines.blend with Blender before
running this script. The source file is read only. Geometry is grouped by set
section, with separate rigid assets and motion tracks for the moving pieces.
"""

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
import sys

import bpy
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'Unity/Assets/Art/E01/GhatSightlines'
SCENE_NAME = 'E01 Ghat Sightlines'
SET_FRAME = 145
UNITY_BASIS = Matrix(((1, 0, 0), (0, 0, 1), (0, 1, 0)))
GEOMETRY_TYPES = {'MESH', 'CURVE', 'SURFACE', 'FONT', 'META'}


@dataclass
class Geometry:
    name: str
    collections: tuple
    objects: tuple
    pivot: object = None
    animated: bool = False
    active_from: int = 1

    @property
    def file_name(self):
        return f'Ghat_{self.name}.fbx'


def vector(value):
    return dict(zip(('x', 'y', 'z'), (round(float(component), 7) for component in value)))


def quaternion(value):
    return dict(zip(('x', 'y', 'z', 'w'), (round(float(getattr(value, component)), 7)
                                          for component in ('x', 'y', 'z', 'w'))))


def color(value):
    components = tuple(value)
    return dict(zip(('r', 'g', 'b', 'a'), components if len(components) == 4 else (*components, 1.0)))


def camera_orientation(matrix):
    forward = (UNITY_BASIS @ (matrix.to_3x3() @ Vector((0, 0, -1)))).normalized()
    approx_up = (UNITY_BASIS @ (matrix.to_3x3() @ Vector((0, 1, 0)))).normalized()
    right = approx_up.cross(forward).normalized()
    up = forward.cross(right)
    return Matrix((right, up, forward)).transposed().to_quaternion()


def pose(frame, obj, camera=False):
    matrix = obj.matrix_world
    if camera:
        rotation = camera_orientation(matrix)
    else:
        rotation = (UNITY_BASIS @ matrix.to_quaternion().to_matrix() @ UNITY_BASIS.transposed()).to_quaternion()
    return dict(frame=frame, position=vector(UNITY_BASIS @ matrix.translation), rotation=quaternion(rotation))


def collection_starting_with(collections, prefix):
    return next(collection for collection in collections if collection.name.startswith(prefix))


def object_starting_with(scene, prefix):
    return next(obj for obj in scene.objects if obj.name.startswith(prefix))


def renderable(obj):
    return obj.type in GEOMETRY_TYPES and not obj.hide_render


def geometry_groups(scene):
    groups = scene.collection.children
    palace = groups['SET_Palace']
    town = collection_starting_with(groups, 'SET_Town |')
    ghat = collection_starting_with(groups, 'SET_Ghat |')
    terrain = groups['Sightlines | Distant terrain']
    boat = scene.objects['Boat | hull rock']
    gate = object_starting_with(scene, 'Gate | grille root')
    river = scene.objects['River water surface']
    actor = scene.objects['AnonymousRedCloth_Rig']
    figure = ghat.children['CH_AnonymousRedCloth']
    actor_objects = tuple(figure.all_objects)
    # Each moving group has one rigid local frame in Blender. The cloth figure
    # is already posed and uses its evaluated skin at the testimony frame.
    dynamic = (*boat.children_recursive, *gate.children_recursive, river, *actor_objects)
    return [Geometry('Palace', tuple(palace.children), tuple(palace.all_objects)),
            Geometry('Environment', tuple(ghat.children), tuple(obj for obj in ghat.all_objects if obj not in dynamic)),
            Geometry('Town', tuple(town.children), tuple(town.all_objects)),
            Geometry('Distant_Terrain', (terrain,), tuple(terrain.all_objects)),
            Geometry('Boat', (), tuple(boat.children_recursive), boat, True),
            Geometry('Gate', (), tuple(gate.children_recursive), gate, True),
            Geometry('River', (), (river,), river, True),
            Geometry('Red_Cloth', (), actor_objects, actor, False, SET_FRAME)]


def camera_settings(scene, obj):
    tangent = max(abs(corner.y / corner.z) for corner in obj.data.view_frame(scene=scene))
    return dict(name=obj.name, verticalFovDegrees=2 * math.degrees(math.atan(tangent)),
                nearClipPlane=obj.data.clip_start, farClipPlane=obj.data.clip_end, poses=[])


def sample_timeline(scene, groups):
    names = {}
    shots = []
    for marker in sorted(scene.timeline_markers, key=lambda item: item.frame):
        if marker.camera:
            names.setdefault(marker.camera.name, marker.camera)
            shots.append(dict(frame=marker.frame, label=marker.name, camera=marker.camera.name))
    if len(names) != 3 or len(shots) != 5:
        raise ValueError('The sightline scene must contain three cameras and five camera markers.')

    cameras = [camera_settings(scene, obj) for obj in names.values()]
    tracks = [dict(fileName=group.file_name, name=group.name, animated=group.animated,
                   activeFromFrame=group.active_from, poses=[]) for group in groups]
    lamp = object_starting_with(scene, 'Lamp spot')
    sun = object_starting_with(scene, 'LIGHT | Sun')
    ambient_by_frame = {1: (.24, .27, .32), 49: (.24, .18, .15), SET_FRAME: (.025, .036, .064)}
    lighting = []
    for frame in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(frame)
        for row, camera in zip(cameras, names.values()):
            current = pose(frame, camera, camera=True)
            if not row['poses'] or any(current[key] != row['poses'][-1][key] for key in ('position', 'rotation')):
                row['poses'].append(current)
        for track, group in zip(tracks, groups):
            if group.pivot and (group.animated or not track['poses']):
                track['poses'].append(pose(frame, group.pivot))
        if frame in ambient_by_frame:
            lighting.append(dict(frame=frame, ambientColor=color(ambient_by_frame[frame]), sunColor=color(sun.data.color),
                                 sunRotation=quaternion(camera_orientation(sun.matrix_world)),
                                 sunIntensity=sun.data.energy * .45, lampIntensity=lamp.data.energy / 12.0))
    scene.frame_set(SET_FRAME)
    lamp_settings = dict(position=vector(UNITY_BASIS @ lamp.matrix_world.translation),
                         rotation=quaternion(camera_orientation(lamp.matrix_world)), color=color(lamp.data.color),
                         spotAngle=math.degrees(lamp.data.spot_size), range=7.0)
    fps = scene.render.fps / scene.render.fps_base
    return dict(schemaVersion=1, fps=fps, startFrame=scene.frame_start, endFrame=scene.frame_end,
                geometry=tracks, cameras=cameras, shots=shots, lighting=lighting, lamp=lamp_settings,
                verification=dict(waterTrack='River', boatTrack='Boat', gateTrack='Gate'))


def slug(name):
    return re.sub('[^A-Za-z0-9]+', '_', name).strip('_')


class ExportMaterials:
    def __init__(self):
        self.by_source = {}
        self.values = []

    def get(self, source):
        if source in self.by_source:
            return self.by_source[source]
        original_name = source.name if source else 'Unassigned surface'
        base_color = tuple(source.diffuse_color) if source else (.5, .5, .5, 1.0)
        roughness, metallic, emission, brightness = .8, 0, (0, 0, 0, 1), 0
        shader = next((node for node in source.node_tree.nodes if node.type == 'BSDF_PRINCIPLED'), None) \
            if source and source.node_tree else None
        if shader:
            roughness = shader.inputs['Roughness'].default_value
            metallic = shader.inputs['Metallic'].default_value
            emission = tuple(shader.inputs['Emission Color'].default_value)
            brightness = shader.inputs['Emission Strength'].default_value
        if original_name == 'River | silty flood water':
            base_color, roughness, metallic = (.075, .135, .16, 1.0), .24, .13
        result = bpy.data.materials.new(f'E01_{slug(original_name)}')
        result.diffuse_color, result.roughness, result.metallic = base_color, roughness, metallic
        self.values.append(dict(name=result.name, sourceName=original_name, color=color(base_color),
                                roughness=roughness, metallic=metallic, emissionColor=color(emission),
                                emissionIntensity=brightness))
        self.by_source[source] = result
        return result


def export_section(collection, objects, parent_inverse, materials, source_name):
    view_layer = bpy.context.view_layer
    graph = bpy.context.evaluated_depsgraph_get()
    clones = []
    for obj in objects:
        evaluated = obj.evaluated_get(graph)
        mesh = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True, depsgraph=graph)
        if not mesh or not mesh.polygons:
            if mesh:
                bpy.data.meshes.remove(mesh)
            continue
        transform = parent_inverse @ evaluated.matrix_world
        mesh.transform(transform)
        if transform.to_3x3().determinant() < 0:
            mesh.flip_normals()
        for index, material in enumerate(tuple(mesh.materials)):
            mesh.materials[index] = materials.get(material)
        if not mesh.materials:
            mesh.materials.append(materials.get(None))
        clone = bpy.data.objects.new('E01 Part', mesh)
        collection.objects.link(clone)
        clones.append(clone)
    if not clones:
        return None

    bpy.ops.object.select_all(action='DESELECT')
    for clone in clones:
        clone.select_set(True)
    view_layer.objects.active = clones[0]
    input_meshes = [clone.data for clone in clones[1:]]
    if len(clones) > 1:
        bpy.ops.object.join()
    for mesh in input_meshes:
        if not mesh.users:
            bpy.data.meshes.remove(mesh)
    result = view_layer.objects.active
    result.name = source_name
    return result


def add_calibration(collection):
    markers = {'Origin': (0, 0, 0), 'X': (1, 0, 0), 'Y': (0, 0, 1), 'Z': (0, 1, 0)}
    for key, position in markers.items():
        marker = bpy.data.objects.new(f'E01_Axis_{key}', None)
        marker.location = position
        collection.objects.link(marker)


def write_geometry(scene, group, output, materials):
    collection = bpy.data.collections.new('Temporary Unity export')
    scene.collection.children.link(collection)
    inverse = group.pivot.matrix_world.inverted() if group.pivot else Matrix.Identity(4)
    remaining = {obj for obj in group.objects if renderable(obj)}
    for source in group.collections:
        section = remaining.intersection(source.objects)
        if section:
            label = source.name.split(' | ')[-1].split(' (')[0]
            export_section(collection, sorted(section, key=lambda item: item.name), inverse, materials, slug(label))
            remaining.difference_update(section)
    if remaining:
        export_section(collection, sorted(remaining, key=lambda item: item.name), inverse, materials, group.name)
    meshes = [obj for obj in collection.objects if obj.type == 'MESH']
    if not meshes:
        raise ValueError(f'No renderable meshes for {group.name}')

    add_calibration(collection)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in collection.objects:
        obj.select_set(True)
    path = output / group.file_name
    # Use Blender's triangulation for the evaluated architecture so Unity does
    # not need to interpret the complex n-gons on its own.
    result = bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True,
                                     object_types={'MESH', 'EMPTY'}, use_mesh_modifiers=False,
                                     use_triangles=True, bake_anim=False, add_leaf_bones=False,
                                     mesh_smooth_type='FACE', apply_unit_scale=True,
                                     apply_scale_options='FBX_SCALE_UNITS', axis_forward='-Z', axis_up='Y')
    if result != {'FINISHED'} or not path.is_file():
        raise RuntimeError(f'FBX export failed for {group.name}: {result}')
    triangles = sum(sum(len(face.vertices) - 2 for face in obj.data.polygons) for obj in meshes)
    print(f'UNITY FBX {group.name}: {len(meshes)} sections, {triangles} triangles, '
          f'{path.stat().st_size:,} bytes', flush=True)
    mesh_data = [obj.data for obj in meshes]
    for obj in list(collection.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in mesh_data:
        bpy.data.meshes.remove(mesh)
    bpy.data.collections.remove(collection)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    scene = bpy.context.scene
    if scene.name != SCENE_NAME:
        raise ValueError(f'Open the {SCENE_NAME!r} scene before running this exporter.')

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    groups = geometry_groups(scene)
    timeline = sample_timeline(scene, groups)
    materials = ExportMaterials()
    for group in groups:
        write_geometry(scene, group, output, materials)
    timeline['materials'] = sorted(materials.values, key=lambda item: item['name'])
    manifest = output / 'GhatSightlines.json'
    manifest.write_text(json.dumps(timeline, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    print(f'UNITY EXPORT {output}: {len(groups)} geometry assets, {len(timeline["cameras"])} cameras, '
          f'{len(timeline["materials"])} materials; {manifest.stat().st_size:,} manifest bytes', flush=True)


if __name__ == '__main__':
    main()
