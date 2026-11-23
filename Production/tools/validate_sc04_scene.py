"""Validate the generated .blend using Blender's own data model."""

import json
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
EPISODE = ROOT/'Production/E01'


def main():
    timeline=json.loads((EPISODE/'E01_SC04_Animatic_Timeline.json').read_text(encoding='utf-8'))
    scene=bpy.data.scenes['E01_SC04 | Interrogation animatic']
    bpy.context.window.scene=scene
    if scene.frame_end != timeline['total_frames']-1 or scene.render.fps != 24:
        raise ValueError('Scene range differs from the measured edit')
    markers={marker.name:marker for marker in scene.timeline_markers}
    for shot in timeline['shots']:
        marker=markers[shot['id']]
        if marker.frame != shot['start_frame'] or marker.camera is None:
            raise ValueError(f"Missing camera cut: {shot['id']}")
    for name in ('Vikram','Gopal'):
        rig=bpy.data.objects[f'{name}_Rig']
        if len(rig.data.bones) != 34 or rig.animation_data is None:
            raise ValueError(f'Character rig/pose animation missing: {name}')
        mouth=bpy.data.objects[f'{name}_Mouth']
        if len(mouth.data.shape_keys.key_blocks) != 6 or mouth.data.shape_keys.animation_data is None:
            raise ValueError(f'Mouth blocking keys missing: {name}')
    editor=scene.sequence_editor
    strips=getattr(editor,'strips',None)
    if strips is None:
        strips=editor.sequences
    sounds=[strip.sound for strip in strips if strip.type=='SOUND']
    if len(sounds) != 1 or not sounds[0].filepath.startswith('//'):
        raise ValueError('Scratch audio must use a portable relative path')
    if not Path(bpy.path.abspath(sounds[0].filepath)).is_file():
        raise ValueError('Relative scratch audio path is broken')
    water=bpy.data.objects['Night river surface']
    shot4=next(shot for shot in timeline['shots'] if shot['id'].endswith('SH04'))
    scene.frame_set(shot4['start_frame']+1)
    water_top=max((water.matrix_world@Vector(point)).z for point in water.bound_box)
    if not .225 < water_top < .235:
        raise ValueError('The flooded-steps insert must cover the first step')
    shot9=next(shot for shot in timeline['shots'] if shot['id'].endswith('SH09'))
    scene.frame_set(shot9['start_frame']+1)
    water_top=max((water.matrix_world@Vector(point)).z for point in water.bound_box)
    fingers=[obj for obj in scene.objects if obj.name.startswith('Niece fingertip at water')]
    for finger in fingers:
        fingertip=min((finger.matrix_world@Vector(point)).z for point in finger.bound_box)
        if abs(fingertip-water_top)>.006:
            raise ValueError('The niece fingertip must meet the water surface')
    print('SCENE VALIDATION PASS: 11 camera cuts, two animated original rigs, mouth blocking, relative audio, flooded step and four fingertip contacts')


if __name__=='__main__':
    main()
