"""Add natural acting layers and restrained facial/costume artwork to v0.2."""

from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0,str(Path(__file__).resolve().parent))
import betal
import court_clerk
import facial_controls as face
import gopal
import vikram
from build_sc04_performance import envelope,pose
from character import Character


ROOT=Path(__file__).resolve().parents[2]
EPISODE=ROOT/'Production/E01'
OUTPUT=EPISODE/'Performance'
SCENE_FILE=OUTPUT/'E01_SC04_Performance_v0_3.blend'
DRAPED_PANELS=('shoulder cloth','diagonal teal court sash','sash across back',
               'tucked sash end','shawl | across','shawl | loose','shawl | continuous')


def adapter(module):
    character=Character.__new__(Character)
    character.spec=module.SPEC
    character.name=module.SPEC['name']
    character.scale=module.SPEC['height']
    character.rig=bpy.data.objects[f'{character.name}_Rig']
    character.collection=bpy.data.collections[f'CH_{character.name}']
    character.parts=[obj for obj in character.collection.objects if obj.type=='MESH']
    return character


def noise_layer(material,cloth):
    nodes,links=material.node_tree.nodes,material.node_tree.links
    shader=nodes.get('Principled BSDF')
    colour=shader.inputs['Base Color']
    rough=shader.inputs['Roughness']
    normal=shader.inputs['Normal']
    if all(socket.is_linked for socket in (colour,rough,normal)):
        return False

    coordinates=nodes.new('ShaderNodeTexCoord')
    if not normal.is_linked or not rough.is_linked:
        fine=nodes.new('ShaderNodeTexNoise')
        fine.inputs['Scale'].default_value=175 if cloth else 210
        fine.inputs['Detail'].default_value=1.5
        links.new(coordinates.outputs['Generated'],fine.inputs['Vector'])

    if not normal.is_linked:
        height=fine.outputs['Fac']
        if cloth:
            weave=nodes.new('ShaderNodeTexWave')
            weave.wave_type='BANDS'
            weave.bands_direction='X'
            weave.inputs['Scale'].default_value=120
            weave.inputs['Distortion'].default_value=.12
            links.new(coordinates.outputs['Generated'],weave.inputs['Vector'])
            product=nodes.new('ShaderNodeMath')
            product.operation='MULTIPLY'
            links.new(weave.outputs['Fac'],product.inputs[0])
            links.new(height,product.inputs[1])
            height=product.outputs[0]
        bump=nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value=.17 if cloth else .075
        bump.inputs['Distance'].default_value=.00075 if cloth else .00030
        links.new(height,bump.inputs['Height'])
        links.new(bump.outputs['Normal'],normal)

    if not colour.is_linked:
        original=colour.default_value[:]
        variation=nodes.new('ShaderNodeTexNoise')
        variation.inputs['Scale'].default_value=9 if cloth else 5
        variation.inputs['Detail'].default_value=1
        links.new(coordinates.outputs['Generated'],variation.inputs['Vector'])
        ramp=nodes.new('ShaderNodeValToRGB')
        low,high=ramp.color_ramp.elements
        low.color=tuple(min(1,value*.94) for value in original[:3])+(1,)
        high.color=tuple(min(1,value*1.035) for value in original[:3])+(1,)
        links.new(variation.outputs['Fac'],ramp.inputs['Fac'])
        links.new(ramp.outputs['Color'],colour)

    if not rough.is_linked:
        roughness=nodes.new('ShaderNodeMapRange')
        roughness.inputs['To Min'].default_value=.73 if cloth else .51
        roughness.inputs['To Max'].default_value=.94 if cloth else .65
        links.new(fine.outputs['Fac'],roughness.inputs['Value'])
        links.new(roughness.outputs['Result'],rough)
    material['Detail pass']='Subtle woven surface/colour variation' if cloth else 'Subtle skin roughness/colour variation; original base palette retained'
    return True


def stitch_panels(character):
    vertices,faces,weights=[],[],[]
    for obj in list(character.parts):
        if not any(token in obj.name.lower() for token in DRAPED_PANELS):
            continue
        counts=Counter(tuple(sorted(edge)) for polygon in obj.data.polygons for edge in polygon.edge_keys)
        for (a,b),count in counts.items():
            if count!=1:
                continue
            first,second=obj.data.vertices[a],obj.data.vertices[b]
            direction=second.co-first.co
            length=direction.length
            if length<.012*character.scale:
                continue
            tangent=direction.normalized()
            normal=Vector((0,-1 if (first.co.y+second.co.y)<0 else 1,0))
            across=normal.cross(tangent).normalized()
            group={obj.vertex_groups[item.group].name:item.weight for item in first.groups}
            for index in range(max(1,round(length/(.022*character.scale)))):
                position=first.co+direction*((index+.5)/max(1,round(length/(.022*character.scale))))+normal*.0009*character.scale
                along=tangent*.0025*character.scale
                width=across*.00065*character.scale
                start=len(vertices)
                vertices.extend(tuple(point/character.scale) for point in (position-along-width,position+along-width,position+along+width,position-along+width))
                faces.append((start,start+1,start+2,start+3))
                weights.extend([group]*4)
    if vertices:
        colour=(.42,.28,.12) if character.name=='Vikram' else (.42,.34,.24)
        thread=character.mat('Detail pass seam stitches',colour,.86)
        character.mesh('Fine seam stitchwork',vertices,faces,thread,weights)
    return len(faces)


def face_art(character):
    head=bpy.data.objects[f'{character.name}_Head']
    tree=BVHTree.FromPolygons([vertex.co for vertex in head.data.vertices],
                             [tuple(polygon.vertices) for polygon in head.data.polygons])
    colour=character.spec['skin']
    crease=character.mat('Soft facial crease',tuple(value*.79 for value in colour),.83)
    def surface_points(points):
        result=[]
        for x,z in points:
            hit=tree.ray_cast(Vector((x*character.scale,-.6*character.scale,z*character.scale)),Vector((0,1,0)))
            if hit[0] is not None:
                point=hit[0].copy()/character.scale
                point.y-=.00065
                result.append(tuple(point))
        return result
    lines=0
    for sign,side in ((1,'L'),(-1,'R')):
        points=surface_points([(sign*.044,1.650),(sign*.057,1.647),(sign*.071,1.648),(sign*.085,1.653)])
        if len(points)>2:
            character.tube(f'Soft under-eye crease {side}',points,.00035,crease,'head')
            lines+=1
    points=surface_points([(-.031,1.732),(-.015,1.734),(0,1.735),(.015,1.734),(.031,1.732)])
    if len(points)>2:
        obj=character.tube('Expression forehead crease',points,.00038,crease,'head')
        for vertex in obj.data.vertices:
            vertex.co.y+=.003*character.scale
        key=face.shape_from_delta(obj,'Expression crease',lambda point:point-Vector((0,.003*character.scale,0)))
        face.driver_from_property(key,character.rig,'brow_frown','min(1,max(0,value*3))')
        lines+=1
    rig=character.rig
    rig['brow_asymmetry']=0.0
    rig.id_properties_ui('brow_asymmetry').update(min=-.15,max=.15,description='Small independent brow offset')
    for side,sign in (('L',1),('R',-1)):
        brow=bpy.data.objects[f'{character.name}_Brow.{side}']
        curve=next(curve for curve in brow.data.shape_keys.animation_data.drivers if 'Raise' in curve.data_path)
        variable=curve.driver.variables.new()
        variable.name='offset'
        variable.type='SINGLE_PROP'
        variable.targets[0].id=rig
        variable.targets[0].data_path='["brow_asymmetry"]'
        curve.driver.expression=f'min(1,max(0,value+{sign}*offset))'
    return lines


def sash_embroidery(character):
    if character.name!='Vikram':
        return 0
    obj=bpy.data.objects['Vikram_Diagonal teal court sash']
    vertices,faces,weights=[],[],[]
    motifs=0
    rows=len(obj.data.vertices)//4
    for row in range(rows-1):
        start=(obj.data.vertices[row*4+1].co+obj.data.vertices[row*4+2].co)/2
        end=(obj.data.vertices[(row+1)*4+1].co+obj.data.vertices[(row+1)*4+2].co)/2
        direction=end-start
        count=max(1,round(direction.length/(.037*character.scale)))
        tangent=direction.normalized()
        across=Vector((tangent.z,0,-tangent.x)).normalized()
        group={obj.vertex_groups[item.group].name:item.weight for item in obj.data.vertices[row*4+1].groups}
        for index in range(count):
            center=start+direction*((index+.5)/count)+Vector((0,-.0012*character.scale,0))
            diamond=[center+tangent*.008*character.scale,center+across*.0045*character.scale,
                     center-tangent*.008*character.scale,center-across*.0045*character.scale]
            for first,second in zip(diamond,diamond[1:]+diamond[:1]):
                normal=Vector((0,-1,0)).cross((second-first).normalized())*.00055*character.scale
                a=len(vertices)
                vertices.extend(tuple(point/character.scale) for point in
                                (first-normal,second-normal,second+normal,first+normal))
                faces.append((a,a+1,a+2,a+3))
                weights.extend([group]*4)
            motifs+=1
    thread=character.mat('Embroidered sash gold',(.45,.29,.10),.65,.25)
    character.mesh('Embroidered sash diamonds',vertices,faces,thread,weights)
    return motifs


def cloth_secondary(character):
    count=0
    secondary_panels=DRAPED_PANELS+('shawl | uneven','fine seam stitchwork','embroidered sash')
    for obj in list(character.parts):
        if not any(token in obj.name.lower() for token in secondary_panels):
            continue
        def settle(point):
            weight=max(0,min(1,(1.22*character.scale-point.z)/(.55*character.scale)))
            point.y+=.0035*character.scale*weight*math.cos(point.x*24)
            point.x+=.0015*character.scale*weight
            return point
        key=face.shape_from_delta(obj,'Cloth settle',settle)
        driver=key.driver_add('value').driver
        driver.expression='.5+.5*sin(frame*.037+1)'
        count+=1
    return count


def foot_controls(character,scene,timeline):
    rig=character.rig
    scene.frame_set(60)
    targets={}
    for side in ('L','R'):
        foot=rig.pose.bones[f'foot.{side}']
        anchor=rig.matrix_world@foot.matrix.translation
        target=bpy.data.objects.new(f'{character.name}_Foot_{side}_Control',None)
        scene.collection.objects.link(target)
        target.location=anchor
        target.rotation_mode='QUATERNION'
        target.rotation_quaternion=rig.matrix_world.to_quaternion()@foot.bone.matrix_local.to_quaternion()
        target.empty_display_size=.045
        pole=bpy.data.objects.new(f'{character.name}_Knee_{side}_Control',None)
        scene.collection.objects.link(pole)
        pole.location=anchor+(rig.matrix_world.to_quaternion()@Vector((0,-.6,.4)))
        ik=rig.pose.bones[f'shin.{side}'].constraints.new('IK')
        ik.name='Ground contact IK'
        ik.target=target
        ik.pole_target=pole
        ik.chain_count=2
        ik.use_stretch=False
        # Calibrate pole roll against the approved resting thigh orientation.
        # A planted foot alone does not detect a 90/180-degree leg twist.
        rest=rig.pose.bones[f'thigh.{side}'].bone.matrix_local.to_quaternion()
        candidates=[]
        for index in range(32):
            angle=-math.pi+index*math.tau/32
            ik.pole_angle=angle
            scene.view_layers[0].update()
            current=rig.pose.bones[f'thigh.{side}'].matrix.to_quaternion()
            error=current.rotation_difference(rest).angle
            candidates.append((min(error,abs(math.tau-error)),angle))
        ik.pole_angle=min(candidates)[1]
        scene.view_layers[0].update()
        rotation=foot.constraints.new('COPY_ROTATION')
        rotation.target=target
        rotation.owner_space='WORLD'
        rotation.target_space='WORLD'
        targets[side]=(target,anchor.copy())
    return targets


def natural_acting(character,scene,timeline):
    rig=character.rig
    is_gopal=character.name=='Gopal'
    phase=.7 if is_gopal else 2.1
    targets=foot_controls(character,scene,timeline)
    scene.frame_set(60)
    settled=rig.location.copy()
    cues={cue['cue_id'][-3:]:cue for cue in timeline['cues']}
    blink_times=[]
    for cue in timeline['cues']:
        if cue['speaker_id']==character.name:
            candidate=cue['end_frame_exclusive']+8
            if not blink_times or candidate-blink_times[-1]>60:
                blink_times.append(candidate)
    blink_times=[68,*blink_times]
    if not is_gopal:
        blink_times.extend([330,850,1099])
    for frame in range(timeline['total_frames']+2):
        for side,delay in (('L',0),('R',.45)):
            value=max((max(0,1-abs((frame-delay)-center)/3)**.65 for center in blink_times),default=0)
            face.key_property(rig,f'blink_{side}',frame,value)
        if frame%2:
            continue
        breath=.65*math.sin(frame*.044+phase)+.35*math.sin(frame*.021+phase*2)
        demonstration=envelope(frame,cues['L06']['start_frame']-5,cues['L06']['end_frame_exclusive']+14)
        admission=envelope(frame,cues['L10']['start_frame']-8,cues['L10']['end_frame_exclusive']+16)
        map_look=envelope(frame,cues['L07']['start_frame']-4,cues['L07']['end_frame_exclusive']+5)
        instruction=envelope(frame,cues['L11']['start_frame']-8,cues['L12']['end_frame_exclusive']+14)
        listening_nod=envelope(frame,cues['L10']['end_frame_exclusive']+3,cues['L10']['end_frame_exclusive']+32,10)
        drift=.16*math.sin(frame*.013+phase)+.08*math.sin(frame*.031+phase)
        pose(rig,'spine',(.28*breath,0,.13*math.sin(frame*.019+phase)),frame)
        pose(rig,'chest',(.20*breath,0,-15*demonstration if is_gopal else 0),frame)
        pitch=2.1*admission+drift if is_gopal else 6*map_look+1.1*listening_nod+drift
        yaw=24-6*demonstration if is_gopal else -24+30*instruction
        pose(rig,'head',(pitch,0,yaw),frame)
        pose(rig,'neck',(-.12*breath,0,0),frame)
        for side in ('L','R'):
            gaze_pitch=(1.9*admission if is_gopal else 2.5*map_look)
            gaze_yaw=(5.5-2*admission if is_gopal else -5.5+5*instruction)
            pose(rig,f'eye.{side}',(gaze_pitch,0,gaze_yaw+.16*math.sin(frame*.023+phase)),frame)
        face.key_property(rig,'brow_asymmetry',frame,.045*admission if is_gopal else .035*map_look)
        hips=rig.pose.bones['hips']
        hips.location=(.0035*math.sin(frame*.018+phase),.0015*breath,-.0015*(1+breath))
        hips.keyframe_insert('location',frame=frame)
        progress_values=[]
        for side,(target,anchor) in targets.items():
            start,end=(0,30) if side=='L' else (24,54)
            progress=max(0,min(1,(frame-start)/(end-start))) if is_gopal else 1
            progress=progress*progress*(3-2*progress)
            progress_values.append(progress)
            target.location=anchor
            if is_gopal:
                target.location.y-=.14*(1-progress)
                target.location.z+=.025*math.sin(math.pi*progress)
            target.keyframe_insert('location',frame=frame)
        rig.location=settled
        if is_gopal:
            rig.location.y-=.14*(1-sum(progress_values)/2)
        rig.keyframe_insert('location',frame=frame)
    return len(blink_times)


def main():
    scene=bpy.data.scenes['E01_SC04 | Performance v0.2']
    bpy.context.window.scene=scene
    timeline=json.loads((EPISODE/'E01_SC04_Animatic_Timeline.json').read_text(encoding='utf-8'))
    stats={'skin_materials':0,'cloth_materials':0,'characters':{}}
    words=('cloth','cotton','kurta','trouser','shawl','coat','sash','dhoti','vest','tunic','wrap','jacket','silk','handloom','river blue')
    for material in list(bpy.data.materials):
        if not material.use_nodes or ' • ' not in material.name:
            continue
        if material.name.endswith(' • Skin'):
            stats['skin_materials']+=int(noise_layer(material,False))
        elif any(word in material.name.lower() for word in words) and material.node_tree.nodes.get('Principled BSDF'):
            stats['cloth_materials']+=int(noise_layer(material,True))
    for module in (vikram,gopal,betal,court_clerk):
        character=adapter(module)
        stats['characters'][character.name]={'stitches':stitch_panels(character),
            'embroidered_motifs':sash_embroidery(character),
            'face_creases':face_art(character),'cloth_secondary_shapes':cloth_secondary(character)}
        if character.name in ('Vikram','Gopal'):
            stats['characters'][character.name]['phrase_aware_blinks']=natural_acting(character,scene,timeline)
    scene.name='E01_SC04 | Performance v0.3'
    scene['Performance_version']='0.3'
    scene['Status']='PERFORMANCE v0.3 — grounded acting, facial artwork and woven costume detail'
    scene['Art direction']='Original faces, silhouettes and palette preserved. Subtle surface artwork and seams added.'
    scene.frame_set(0)
    scene.camera=scene.timeline_markers[0].camera
    bpy.ops.wm.save_as_mainfile(filepath=str(SCENE_FILE),compress=True)
    (EPISODE/'E01_SC04_Polish_Manifest.json').write_text(json.dumps({
        'version':'0.3','art':stats,'natural_movement':['Ground-contact foot IK','Phrase-aware asymmetric blinks',
        'Less periodic head motion','Small independent gaze and brow offsets','Subtle secondary cloth settling'],
        'preserved':['Original head and body basis meshes','Original costume silhouettes and palette','Original Hindi dialogue and timing'],
        'review_render':'960x540, on twos; source animation remains 24 fps'},indent=2)+'\n')
    print('POLISH_BUILD_COMPLETE',json.dumps(stats),flush=True)


if __name__=='__main__':
    main()
