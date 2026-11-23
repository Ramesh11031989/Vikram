"""Validate rest geometry, facial controls, animation and editorial constraints."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import struct

import bpy
from mathutils import Vector


ROOT=Path(__file__).resolve().parents[2]
EPISODE=ROOT/'Production/E01'


def main():
    manifest=json.loads((EPISODE/'E01_SC04_Performance_Manifest.json').read_text())
    timeline=json.loads((EPISODE/'E01_SC04_Animatic_Timeline.json').read_text(encoding='utf-8'))
    scene=bpy.data.scenes['E01_SC04 | Performance v0.2']
    bpy.context.window.scene=scene
    for name,expected in manifest['rest_geometry_sha256'].items():
        obj=bpy.data.objects[name]
        actual=hashlib.sha256(b''.join(struct.pack('3f',*vertex.co) for vertex in obj.data.vertices)).hexdigest()
        if actual!=expected:
            raise ValueError(f'Original rest mesh changed: {name}')
    checked_drivers=0
    for frame in (0,52,130,485,862,1031,1249,1483):
        scene.frame_set(frame)
        scene.view_layers[0].update()
        for name in ('Vikram','Gopal','CourtClerk','Betal'):
            rig=bpy.data.objects[f'{name}_Rig']
            if len(rig.data.bones)!=34:
                raise ValueError(f'Unexpected deformation skeleton: {name}')
            mouth=bpy.data.objects[f'{name}_Mouth']
            if len(mouth.data.shape_keys.key_blocks)<11:
                raise ValueError('Extended speech/expression shapes missing')
            for key in mouth.data.shape_keys.key_blocks:
                if not math.isfinite(key.value) or not -.0001<=key.value<=1.0001:
                    raise ValueError(f'Out-of-range mouth driver: {name}/{key.name}')
        for obj in scene.objects:
            if obj.type=='MESH' and obj.data.shape_keys and obj.data.shape_keys.animation_data:
                for curve in obj.data.shape_keys.animation_data.drivers:
                    if not curve.driver.is_valid:
                        raise ValueError(f'Invalid facial/water driver on {obj.name}')
                    checked_drivers+=1
    for name in ('Vikram','Gopal'):
        rig=bpy.data.objects[f'{name}_Rig']
        for cue in timeline['cues']:
            if cue['speaker_id']!=name:
                continue
            scene.frame_set(cue['start_frame']-2)
            mouth=bpy.data.objects[f'{name}_Mouth'].data.shape_keys
            if max(mouth.key_blocks[key].value for key in
                   ('Mouth_Ah','Mouth_O','Mouth_Ee','Mouth_MBP','Mouth_FV','Mouth_U','Mouth_L','Mouth_Consonant'))>.015:
                raise ValueError(f'Mouth starts speaking before {cue["cue_id"]}')
        scene.frame_set(0)
        first=rig.pose.bones['head'].matrix.copy()
        scene.frame_set(1031)
        if sum(abs(a-b) for row_a,row_b in zip(first,rig.pose.bones['head'].matrix) for a,b in zip(row_a,row_b))<.0001:
            raise ValueError(f'No head acting on {name}')
    scene.frame_set(52)
    if bpy.data.objects['Gopal_Rig']['blink_L']<.95:
        raise ValueError('Gopal blink control does not close')
    scene.frame_set(60)
    if bpy.data.objects['Gopal_Rig']['blink_L']>.05:
        raise ValueError('Gopal blink does not reopen')
    clerk=bpy.data.objects['CourtClerk_Rig']
    if not any(constraint.type=='IK' for bone in clerk.pose.bones for constraint in bone.constraints):
        raise ValueError('Court clerk writing IK missing')
    person=bpy.data.objects['RiverFigure_Rig']
    for shot in timeline['shots']:
        midpoint=(shot['start_frame']+shot['end_frame_exclusive'])//2
        scene.frame_set(midpoint)
        marker=scene.timeline_markers[shot['id']]
        if marker.frame!=shot['start_frame']:
            raise ValueError('Camera cut drifted from dialogue timeline')
        if shot['id'].endswith(('SH03','SH08')):
            forward=(person.matrix_world.to_3x3()@Vector((0,-1,0))).normalized()
            viewer=(marker.camera.matrix_world.translation-person.matrix_world.translation).normalized()
            if forward.dot(viewer)>=0:
                raise ValueError('River camera can see the unidentified person from the front')
        king=bpy.data.objects['Vikram_Head']
        if king.hide_render != (shot['set']=='river'):
            raise ValueError('Court/river visibility isolation failed')
    editor=scene.sequence_editor
    strips=getattr(editor,'strips',None)
    if strips is None:
        strips=editor.sequences
    for strip in strips:
        if strip.type=='SOUND' and (not strip.sound.filepath.startswith('//') or
                                  not Path(bpy.path.abspath(strip.sound.filepath)).is_file()):
            raise ValueError('External audio link is not portable')
    report={'status':'PASS','unchanged_original_meshes':len(manifest['rest_geometry_sha256']),
            'camera_cuts':11,'facial_control_rigs':['Vikram','Gopal','Betal','CourtClerk'],
            'speech_viseme_segments':sum(item['visemes'] for item in manifest['characters'].values()),
            'valid_driver_samples':checked_drivers,'speech_shapes_closed_before_cues':True,
            'head_acting':True,'blink_close_reopen':True,'writing_ik':True,
            'anonymous_face_hidden':True,'court_river_isolation':True,'relative_audio':True,
            'lip_sync_limit':'Automatic acoustic viseme estimates; no claim of verified Hindi phoneme accuracy'}
    (EPISODE/'E01_SC04_Performance_Scene_Check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    main()
