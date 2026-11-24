"""Build the story prop library, one .blend + FBX + review render per group.

blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_story_props.py -- horse
Without arguments, build every group implemented in group_*.py.
"""

import importlib
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import story_kit as K

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Props' / 'Story'


def fresh(name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = name
    root = bpy.data.collections.new(f'PROPS_{name}')
    scene.collection.children.link(root)
    root.asset_mark()
    return scene, root


def export_fbx(root, path):
    bpy.ops.object.select_all(action='DESELECT')
    objs = [o for o in root.all_objects if o.type in {'MESH', 'ARMATURE'}]
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    result = bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True,
        object_types={'MESH', 'ARMATURE'}, axis_forward='-Z', axis_up='Y',
        apply_scale_options='FBX_SCALE_UNITS', use_mesh_modifiers=False, bake_anim=False,
        mesh_smooth_type='FACE', path_mode='COPY', embed_textures=False, add_leaf_bones=False)
    if 'FINISHED' not in result or path.stat().st_size < 1024:
        raise RuntimeError(f'FBX export failed: {path}')


def finish(scene, root, name, shots):
    """Save the .blend, export the FBX and render every (label, camera) shot."""
    OUT.mkdir(parents=True, exist_ok=True)
    problems = []
    for o in root.all_objects:
        if o.type == 'MESH':
            if not o.data.polygons:
                problems.append(f'{o.name}: empty mesh')
            if not o.data.materials:
                problems.append(f'{o.name}: no material')
            if max(o.dimensions) > 60:
                problems.append(f'{o.name}: bigger than 60 m')
    if problems:
        raise RuntimeError('; '.join(problems))
    tris = sum(len(o.data.polygons) for o in root.all_objects if o.type == 'MESH')
    print(f'{name}: {len(root.all_objects)} objects, {tris} faces', flush=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / f'{name}.blend'), compress=True)
    export_fbx(root, OUT / f'PROPS_{name}.fbx')
    for label, cam in shots:
        K.render(scene, cam, OUT / f'{name}_{label}.png')


def main():
    names = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    available = sorted(path.stem.removeprefix('group_') for path in Path(__file__).parent.glob('group_*.py'))
    missing = set(names) - set(available)
    if missing:
        raise ValueError(f'Unimplemented prop groups {", ".join(sorted(missing))}. Available: {", ".join(available)}')
    names = names or available
    for name in names:
        module = importlib.import_module(f'group_{name}')
        scene, root = fresh(module.NAME)
        shots = module.build(scene, root)
        finish(scene, root, module.NAME, shots)


main()
