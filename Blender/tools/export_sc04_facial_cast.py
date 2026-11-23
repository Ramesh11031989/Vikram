"""Export neutral facial-rig assets; Blender-only control drivers stay in .blend."""

from __future__ import annotations

import json
from pathlib import Path

import bpy
from mathutils import Matrix


ROOT=Path(__file__).resolve().parents[2]
EPISODE=ROOT/'Production/E01'
OUTPUT=EPISODE/'Performance/Exports'


def main():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    exports=[]
    for name in ('Vikram','Gopal','Betal','CourtClerk'):
        scene=bpy.data.scenes[f'Library | {name}']
        bpy.context.window.scene=scene
        rig=bpy.data.objects[f'{name}_Rig']
        rig.animation_data_clear()
        rig.location=(0,0,0)
        rig.rotation_euler=(0,0,0)
        for key in list(rig.keys()):
            if isinstance(rig[key],float):
                rig[key]=0.0
        for bone in rig.pose.bones:
            bone.matrix_basis=Matrix.Identity(4)
            for constraint in bone.constraints:
                constraint.mute=True
        scene.view_layers[0].update()
        bpy.ops.object.select_all(action='DESELECT')
        for obj in scene.objects:
            if obj.type in ('MESH','ARMATURE'):
                obj.hide_render=False
                obj.select_set(True)
                if obj.type=='MESH' and obj.data.shape_keys:
                    obj.data.shape_keys.animation_data_clear()
                    for key in obj.data.shape_keys.key_blocks:
                        key.value=0
        bpy.context.view_layer.objects.active=rig
        version='0_3' if bpy.data.scenes.get('E01_SC04 | Performance v0.3') else '0_2'
        output=OUTPUT/f'CHR_{name}_Facial_v{version}.fbx'
        result=bpy.ops.export_scene.fbx(filepath=str(output),use_selection=True,
            object_types={'ARMATURE','MESH'},axis_forward='-Z',axis_up='Y',
            apply_scale_options='FBX_SCALE_UNITS',use_mesh_modifiers=False,
            add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_custom_props=True)
        if 'FINISHED' not in result:
            raise RuntimeError(f'Failed export: {name}')
        exports.append({'character':name,'file':output.name,'bytes':output.stat().st_size,
                        'deform_bones':len(rig.data.bones),
                        'shape_meshes':{obj.name:list(obj.data.shape_keys.key_blocks.keys()) for obj in scene.objects
                                        if obj.type=='MESH' and obj.data.shape_keys}})
    report={'status':'PASS','version':version.replace('_','.'),'mode':'Neutral rest pose, no baked performance clips',
            'exports':exports,'limits':'FBX retains the deformation rig, mesh details and blend shapes. Blender custom-property drivers and IK require rebinding or baking. Procedural woven/skin materials must be recreated or baked in the destination.'}
    (OUTPUT/'Facial_Cast_Manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    for item in exports:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(OUTPUT/item['file']))
        rigs=[obj for obj in bpy.context.scene.objects if obj.type=='ARMATURE']
        if len(rigs)!=1 or len(rigs[0].data.bones)!=34:
            raise ValueError(f"Round-trip skeleton mismatch: {item['character']}")
        mouth=next(obj for obj in bpy.context.scene.objects if obj.type=='MESH' and obj.name.endswith('_Mouth'))
        if len(mouth.data.shape_keys.key_blocks)<11:
            raise ValueError(f"Missing exported facial shapes: {item['character']}")
        item['round_trip_import']='PASS'
    (EPISODE/'E01_SC04_Cast_Export_Check.json').write_text(json.dumps(report,indent=2)+'\n')
    print('FOUR_FACIAL_CAST_EXPORTS_PASS',flush=True)


if __name__=='__main__':
    main()
