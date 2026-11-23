"""Build the fully keyed interrogation performance without overwriting v0.1."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Euler, Quaternion, Vector

sys.path.insert(0,str(Path(__file__).resolve().parent))
import betal
import build_cast
import build_sc04_animatic as base
import court_clerk
import facial_controls as face
import performance_props as props
from character import Character


ROOT=Path(__file__).resolve().parents[2]
EPISODE=ROOT/'Production/E01'
OUTPUT=EPISODE/'Performance'
SCENE_FILE=OUTPUT/'E01_SC04_Performance_v0_2.blend'


def pose(rig,joint,angles,frame):
    bone=rig.pose.bones[joint]
    rest=bone.bone.matrix_local.to_quaternion()
    bone.rotation_mode='QUATERNION'
    rotation=Euler(tuple(math.radians(value) for value in angles),'XYZ').to_quaternion()
    bone.rotation_quaternion=rest.inverted()@rotation@rest
    bone.keyframe_insert('rotation_quaternion',frame=frame)


def envelope(frame,start,end,fade=12):
    if frame<start or frame>end:
        return 0
    value=min(1,(frame-start)/fade,(end-frame)/fade)
    return max(0,value)*max(0,value)*(3-2*max(0,value))


def animate_actor(character,timeline):
    rig=character.rig
    rig.animation_data_clear()
    is_gopal=character.name=='Gopal'
    cues={cue['cue_id'][-3:]:cue for cue in timeline['cues']}
    location=rig.location.copy()
    for frame in range(0,timeline['total_frames']+2,2):
        breathing=math.sin(frame*.047)
        demonstration=envelope(frame,cues['L06']['start_frame']-9,cues['L06']['end_frame_exclusive']+12)
        admission=envelope(frame,cues['L10']['start_frame']-10,cues['L10']['end_frame_exclusive']+15)
        instruction=envelope(frame,cues['L11']['start_frame']-8,cues['L12']['end_frame_exclusive']+15)
        gate_look=envelope(frame,cues['L07']['start_frame']-6,cues['L07']['end_frame_exclusive']+5,8)
        rig.location=location
        if is_gopal and frame<45:
            rig.location.y-=.14*(1-frame/45)
        rig.keyframe_insert('location',frame=frame)
        pose(rig,'spine',(.35*breathing,0,.35*math.sin(frame*.027)),frame)
        pose(rig,'chest',(.25*breathing,0,-15*demonstration if is_gopal else 0),frame)
        pose(rig,'neck',(-.35*breathing,0,0),frame)
        nod=.65*math.sin(frame*.055)
        pose(rig,'head',(nod+2.5*admission if is_gopal else nod+7*gate_look,
                         0,24-7*demonstration if is_gopal else -24+32*instruction),frame)
        for side,sign in (('L',1),('R',-1)):
            lift=admission*18 if is_gopal and side=='R' else instruction*24 if side=='R' else 0
            pose(rig,f'upper_arm.{side}',(-lift,sign*(75-lift*.25),0),frame)
            pose(rig,f'forearm.{side}',(-lift*.8,0,-sign*7),frame)
            pose(rig,f'hand.{side}',(0,0,sign*lift*.15),frame)
            for digit in range(1,5):
                pose(rig,f'finger_{digit:02d}.{side}',(0,sign*(16-lift*.25),0),frame)
            if is_gopal:
                step=math.sin(math.pi*frame/45) if frame<45 else 0
                pose(rig,f'thigh.{side}',(-12*step if side=='L' else 0,0,0),frame)
                pose(rig,f'shin.{side}',(18*step if side=='L' else 0,0,0),frame)
            gaze=(6 if is_gopal else -6)+1.4*math.sin(frame*.033)+(-2*admission if is_gopal else 5*instruction)
            pose(rig,f'eye.{side}',(1.8*gate_look if not is_gopal else 1.3*admission,0,gaze),frame)
        face.key_property(rig,'brow_raise',frame,.10+.14*demonstration if is_gopal else .08+.16*gate_look)
        face.key_property(rig,'brow_frown',frame,.28*admission if is_gopal else .10*gate_look)
        face.key_property(rig,'mouth_worry',frame,.30*admission if is_gopal else 0)
        face.key_property(rig,'mouth_smile',frame,0 if is_gopal else .05*instruction)


def hand_ik(character,side,location):
    rig=character.rig
    target=bpy.data.objects.new(f'{character.name}_Hand_{side}_Control',None)
    bpy.context.scene.collection.objects.link(target)
    target.empty_display_type='SPHERE'
    target.empty_display_size=.045
    target.location=location
    rest=rig.pose.bones[f'hand.{side}'].bone.matrix_local.to_quaternion()
    target.rotation_mode='QUATERNION'
    angle=math.pi/2 if side=='R' else -math.pi/2
    target.rotation_quaternion=Quaternion((0,0,1),angle)@rest
    pole=bpy.data.objects.new(f'{character.name}_Elbow_{side}_Control',None)
    bpy.context.scene.collection.objects.link(pole)
    pole.location=(1.62 if side=='R' else 2.75,1.0,1.15)
    constraint=rig.pose.bones[f'forearm.{side}'].constraints.new('IK')
    constraint.name='Writing arm two-bone IK'
    constraint.target=target
    constraint.pole_target=pole
    constraint.chain_count=2
    constraint.use_stretch=False
    rotation=rig.pose.bones[f'hand.{side}'].constraints.new('COPY_ROTATION')
    rotation.target=target
    rotation.owner_space='WORLD'
    rotation.target_space='WORLD'
    return target


def add_clerk(scene,timeline):
    clerk=build_cast.make_character(court_clerk)
    face.add_facial_controls(clerk)
    scene.collection.children.link(clerk.collection)
    bpy.context.window.scene=scene
    clerk.rig.location=(2.20,1.15,0)
    for side,sign in (('L',1),('R',-1)):
        pose(clerk.rig,f'upper_arm.{side}',(0,sign*70,0),0)
    pose(clerk.rig,'chest',(-12,0,0),0)
    pose(clerk.rig,'spine',(-4,0,0),0)
    pose(clerk.rig,'head',(12,0,0),0)
    for digit,angle in enumerate((48,62,68,64),1):
        pose(clerk.rig,f'finger_{digit:02d}.R',(0,-angle,0),0)
    pose(clerk.rig,'thumb.R',(0,-32,-28),0)
    right=hand_ik(clerk,'R',(2.04,.80,1.02))
    hand_ik(clerk,'L',(2.35,.80,1.02))
    wood=bpy.data.materials['Court | polished teak']
    pen=base.line('Court clerk reed pen',[(0,0,0),(.045,.05,.09)],.0045,wood)
    pen.location=(1.96,.73,.974)
    shot=timeline['shots'][-1]
    for frame in range(0,timeline['total_frames']+2,2):
        active=shot['start_frame']+28<frame<shot['end_frame_exclusive']-8
        phase=(frame-shot['start_frame']-32)%48
        progress=max(0,min(1,phase/40)) if active else 0
        row=max(0,min(4,(frame-shot['start_frame']-32)//48)) if active else 0
        right.location=(2.00+progress*.14,.80-row*.014,1.02+.008*math.sin(frame*.7) if active else 1.04)
        right.keyframe_insert('location',frame=frame)
        pen.location=(1.93+progress*.19,.77-row*.043,.976+.002*math.sin(frame*.7) if active else 1.0)
        pen.keyframe_insert('location',frame=frame)
        pose(clerk.rig,'head',(11+.6*math.sin(frame*.04),0,0),frame)
    face.animate_blinks(clerk,timeline,20)
    return clerk


def anonymous_figure(scene,timeline):
    props.remove_objects(('Unidentified ','Red cloth across rear shoulder'))
    spec=dict(court_clerk.SPEC,name='RiverFigure',height=.94,skin=(.055,.045,.035))
    figure=Character(spec)
    figure.body()
    dark=figure.mat('Anonymous dark tunic',(.026,.030,.034),.91)
    cloth=figure.mat('Observed red cloth',(.36,.032,.018),.9)
    figure.loft('Unidentified tunic back',[(.85,0,0,.20,.13),(1.15,0,0,.20,.12),
        (1.38,0,0,.22,.12),(1.45,0,0,.07,.06)],dark,['hips','spine','chest','chest'])
    for side,sign in (('L',1),('R',-1)):
        upper,lower=f'upper_arm.{side}',f'forearm.{side}'
        rings=[[(sign*x,r*math.cos(math.tau*j/24),1.375+r*math.sin(math.tau*j/24)) for j in range(24)]
               for x,r in ((.21,.056),(.25,.066),(.40,.055),(.50,.047),(.66,.034))]
        figure.ring_mesh(f'Anonymous sleeve {side}',rings,dark,
                         ['chest',upper,upper,{upper:.3,lower:.7},lower])
        figure.loft(f'Anonymous trouser {side}',[(.14,sign*.135,0,.055,.05),(.5,sign*.135,0,.075,.07),
                     (.75,sign*.125,0,.10,.10),(.92,sign*.1,0,.115,.12)],dark,
                     [f'shin.{side}',{f'shin.{side}':.5,f'thigh.{side}':.5},f'thigh.{side}','hips'])
    figure.ovoid('Unidentified head without face',(0,0,1.67),(.12,.105,.15),dark,'head')
    rows=[(-.25,.14,1.38),(-.22,.15,1.31),(-.14,.16,1.27),(0,.16,1.25),(.14,.15,1.29),(.25,.12,1.38)]
    vertices=[]
    for x,y,z in rows:
        vertices.extend(((x,y,z),(x,y+.01,z-.20-.018*math.sin(x*28))))
    faces=[(2*i,2*i+1,2*i+3,2*i+2) for i in range(len(rows)-1)]
    figure.mesh('Unidentified red shoulder drape',vertices,faces,cloth,'chest')
    scene.collection.children.link(figure.collection)
    bpy.context.window.scene=scene
    figure.rig.location=(base.RIVER_X+.53,2.98,.86)
    figure.rig.rotation_euler.z=math.pi
    for frame in range(0,timeline['total_frames']+8,8):
        pose(figure.rig,'chest',(.3*math.sin(frame*.05),0,0),frame)
        for side,sign in (('L',1),('R',-1)):
            pose(figure.rig,f'upper_arm.{side}',(0,sign*77,0),frame)
    return figure


def animate_cameras(scene,timeline):
    cues={cue['cue_id'][-3:]:cue for cue in timeline['cues']}
    for shot in timeline['shots']:
        marker=scene.timeline_markers[shot['id']]
        cam=marker.camera
        start,end=shot['start_frame'],shot['end_frame_exclusive']
        initial_location=cam.location.copy()
        if shot['id'].endswith(('SH02','SH06')):
            cam.location=(.25,-3.40,1.91)
            base.aim(cam,(-1.01,-.06,1.32))
            initial_location=cam.location.copy()
        elif shot['id'].endswith(('SH05','SH07')):
            cam.location=(-.25,-2.90,1.85)
            base.aim(cam,(.88,.12,1.65))
            initial_location=cam.location.copy()
        initial_rotation=cam.rotation_euler.copy()
        for frame in range(start,end+1,2):
            progress=(frame-start)/max(1,end-start)
            cam.location=initial_location
            cam.rotation_euler=initial_rotation
            if shot['id'].endswith('SH03'):
                turn=max(0,min(1,(frame-cues['L03']['start_frame'])/max(1,end-cues['L03']['start_frame'])))
                cam.location.z+=.008*math.sin(frame*.11)
                base.aim(cam,(base.RIVER_X+.62-turn*1.45,2.87,2.0-turn*.3))
                cam.rotation_euler.y+=math.radians(.30*math.sin(frame*.09))
            elif shot['set']=='river':
                cam.location.z+=.006*math.sin(frame*.09)
                cam.rotation_euler.y+=math.radians(.16*math.sin(frame*.07))
            elif shot['id'].endswith(('SH10','SH11')):
                forward=cam.rotation_euler.to_quaternion()@Vector((0,0,-1))
                cam.location+=forward*(.055*progress)
            cam.keyframe_insert('location',frame=frame)
            cam.keyframe_insert('rotation_euler',frame=frame)


def isolate_sets(scene,timeline,court_objects,river_objects):
    for group,is_river in ((court_objects,False),(river_objects,True)):
        for name in group:
            obj=scene.objects.get(name)
            if obj is None:
                continue
            for shot in timeline['shots']:
                obj.hide_render=(shot['set']=='river') != is_river
                obj.keyframe_insert('hide_render',frame=shot['start_frame'])


def main():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    base.OUTPUT=OUTPUT
    scene,characters,timeline=base.main(render_panels=False,output_filename=SCENE_FILE.name)
    scene.name='E01_SC04 | Performance v0.2'
    court_objects=set(scene.objects.keys())
    initial_river={obj.name for obj in scene.objects if obj.name.startswith(('Night ','River ','Ghat ','Upper quay','Gate ','Lamp ',
        'Clay lamp','Small flame','Unidentified ','Red cloth','Boat ','Oar ','Niece ','Fingertip ','Step waterline'))}
    court_objects-=initial_river
    rest_hashes={obj.name:hashlib.sha256(b''.join(__import__('struct').pack('3f',*v.co) for v in obj.data.vertices)).hexdigest()
                 for character in characters for obj in character.parts}
    before=set(scene.objects.keys())
    props.detail_court(base,timeline)
    court_objects={name for name in court_objects if name in scene.objects}|(set(scene.objects.keys())-before)
    before=set(scene.objects.keys())
    props.detail_water(base,timeline)
    hand=props.detail_hand(base,timeline)
    river_objects={name for name in initial_river if name in scene.objects}|(set(scene.objects.keys())-before)
    stats={}
    for index,character in enumerate(characters):
        face.add_facial_controls(character)
        animate_actor(character,timeline)
        stats[character.name]={'visemes':face.animate_visemes(character,timeline,OUTPUT/'LipSync'),
                               'blinks':face.animate_blinks(character,timeline,index*13)}
    clerk=add_clerk(scene,timeline)
    court_objects.update(clerk.collection.objects.keys())
    court_objects.update(obj.name for obj in scene.objects if obj.name.startswith(('CourtClerk_Hand','CourtClerk_Elbow','Court clerk reed')))
    figure=anonymous_figure(scene,timeline)
    river_objects.update(figure.collection.objects.keys())
    # The supplementary Betal facial rig is included as a separate library scene.
    former_clerk=build_cast.make_character(betal)
    face.add_facial_controls(former_clerk)
    bpy.context.window.scene=scene
    for character in [*characters,clerk,former_clerk]:
        character.scene.name=f'Library | {character.name}'
    animate_cameras(scene,timeline)
    isolate_sets(scene,timeline,court_objects,river_objects)
    scene.render.engine='BLENDER_EEVEE_NEXT'
    scene.eevee.taa_render_samples=4
    scene.eevee.shadow_resolution_scale=.25
    scene.eevee.use_fast_gi=False
    scene.eevee.use_raytracing=False
    scene.eevee.use_gtao=True
    scene.eevee.gtao_distance=.20
    scene.render.resolution_x=960
    scene.render.resolution_y=540
    scene.render.resolution_percentage=100
    scene['Status']='PERFORMANCE v0.2 — fully keyed body, eyes, acoustic visemes and prop animation'
    scene['Review rendering']='Native 960x540; motion sampled on twos (12 samples/sec), delivered in a 24 fps edit. Scene keys remain at 24 fps.'
    scene['Voices']='Existing synthetic scratch readings retained; final voice approval remains editorial.'
    scene['Lip sync']='Rhubarb phonetic acoustic estimates; not a verified Hindi phoneme transcript.'
    scene['Animation_controls']='Select the character rig Custom Properties for speech shapes, blinks and expressions. Clerk has hand IK targets.'
    scene.camera=scene.timeline_markers[0].camera
    scene.frame_set(0)
    build_cast.configure_view(scene,camera=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(SCENE_FILE),compress=True)
    manifest={'version':'0.2','fps':24,'total_frames':timeline['total_frames'],
              'duration_seconds':timeline['duration_seconds'],'native_review_resolution':[960,540],
              'motion_sample_fps':12,'dialogue_unchanged':True,'characters':stats,
              'clerk':'Distinct rigged supporting character, hand IK and writing action',
              'Betal':'Supplementary facial controls in a separate library scene',
              'rest_geometry_sha256':rest_hashes,'lip_sync_method':'Rhubarb 1.14.0 phonetic automatic acoustic visemes',
              'limits':['Synthetic scratch voices','Automatic visemes need artistic review','Analytic water, no fluid simulation',
                        'CPU review rendering at 540p, on twos; editable scene supports higher render settings']}
    (EPISODE/'E01_SC04_Performance_Manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('PERFORMANCE_BUILD_COMPLETE',SCENE_FILE,flush=True)


if __name__=='__main__':
    main()
