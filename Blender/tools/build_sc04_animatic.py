"""Stage the interrogation pilot without changing the original cast library.

Run with Blender --background --factory-startup --python-exit-code 1 --python ...
The generated scene contains shot cameras, pose keys, markers and scratch audio.
"""

import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_cast
import gopal
import vikram


ROOT = Path(__file__).resolve().parents[2]
EPISODE = ROOT / 'Production/E01'
OUTPUT = EPISODE / 'Animatic'
RIVER_X = 14


def material(name, color, roughness=0.8, emission=0):
    result = bpy.data.materials.new(name)
    result.diffuse_color = (*color, 1)
    result.use_nodes = True
    shader = result.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = roughness
    if emission:
        shader.inputs['Emission Color'].default_value = (*color, 1)
        shader.inputs['Emission Strength'].default_value = emission
    return result


def finish(obj, name, surface):
    obj.name = name
    obj.data.materials.append(surface)
    return obj


def box(name, location, scale, surface, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    finish(obj, name, surface)
    if bevel:
        modifier = obj.modifiers.new('Soft construction edges', 'BEVEL')
        modifier.width, modifier.segments = bevel, 2
        obj.modifiers.new('Weighted corner normals', 'WEIGHTED_NORMAL')
    return obj


def oval(name, location, scale, surface):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, location=location)
    obj = bpy.context.object
    obj.scale = scale
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return finish(obj, name, surface)


def line(name, points, thickness, surface):
    data = bpy.data.curves.new(name, 'CURVE')
    data.dimensions = '3D'
    data.bevel_depth, data.bevel_resolution = thickness, 2
    spline = data.splines.new('POLY')
    spline.points.add(len(points)-1)
    for item, point in zip(spline.points, points):
        item.co = (*point, 1)
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(surface)
    return obj


def aim(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z', 'Y').to_euler()


def light(name, location, target, color, energy, size):
    data = bpy.data.lights.new(name, 'AREA')
    data.color, data.energy, data.shape, data.size = color, energy, 'DISK', size
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    aim(obj, target)


def camera(name, location, target, lens=55, ortho=None):
    data = bpy.data.cameras.new(name)
    data.lens, data.clip_start, data.clip_end = lens, 0.03, 100
    if ortho:
        data.type, data.ortho_scale = 'ORTHO', ortho
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    aim(obj, target)
    return obj


def court():
    stone = material('Court | weathered sandstone', (.36, .27, .19))
    pale = material('Court | pale sandstone', (.50, .39, .27))
    dark = material('Court | recessed wall', (.13, .105, .085))
    chalk = material('Court | white chalk', (.87, .85, .74))
    wood = material('Court | writing desk', (.16, .082, .035))
    parchment = material('Court | paper', (.69, .59, .40))
    box('Court floor', (0, 0, -.12), (14, 8, .24), stone, .015)
    box('Back wall', (0, 2.4, 1.75), (11, .3, 3.5), dark)
    for x in (-3, -1.5, 0, 1.5, 3):
        box('Pavilion pillar', (x, 2, 1.5), (.24, .3, 3), pale, .025)
        box('Pillar plinth', (x, 2, .16), (.40, .45, .32), stone, .02)
        box('Pillar capital', (x, 2, 2.85), (.42, .45, .25), pale, .025)
    box('Pavilion lintel', (0, 2.05, 3), (7, .45, .3), stone, .035)
    for x in (-2.5, -1.1, .3, 1.7):
        line('Floor slab seam', [(x, -3, .006), (x, 2, .006)], .003, dark)
    for x in (-1.17, -.88):
        line('Chalk river bank', [(x + .04*math.sin(y*3), y, .012)
                                 for y in (-1.2, -.8, -.4, 0, .4, .8)], .012, chalk)
    line('Chalk market boundary', [(-.58,-.55,.014),(-.20,-.55,.014),
                                  (-.20,.15,.014),(-.58,.15,.014),(-.58,-.55,.014)], .011, chalk)
    line('Chalk gate mark', [(.03,-.72,.014),(.03,-.10,.014),(.26,-.10,.014),(.26,-.72,.014)], .013, chalk)
    box('Clerk writing desk | blocking prop', (1.85, .83, .88), (.85, .48, .08), wood, .02)
    for x in (1.5, 2.15):
        box('Desk leg', (x, .83, .44), (.055, .055, .88), wood)
    paper = box('Evidence sheet', (1.84, .76, .93), (.47, .30, .008), parchment)
    paper.rotation_euler.z = -.16
    # An anonymous neutral stand-in, never the named former clerk Betal.
    linen = material('Clerk stand-in | neutral linen', (.24, .23, .20))
    skin = material('Clerk stand-in | untextured clay', (.35, .25, .18))
    oval('Court clerk | blocking torso', (1.9, 1.22, 1.25), (.22,.13,.37), linen)
    oval('Court clerk | blocking head', (1.9, 1.20, 1.77), (.12,.105,.16), skin)
    for x in (1.79,2.0):
        oval('Court clerk | blocking leg', (x,1.22,.50), (.07,.09,.50), linen)
    line('Court clerk | writing arm', [(2.09,1.18,1.45),(2.15,.90,1.16),(1.96,.76,.98)], .045, linen)
    oval('Court clerk | writing hand', (1.96,.76,.98), (.046,.048,.025), skin)
    line('Reed pen', [(1.96,.76,.98),(1.88,.72,.94)], .007, wood)
    light('Court warm window key', (-3,-3,5), (0,0,1), (1,.79,.56), 950, 4)
    light('Court cool soft fill', (3,-2,3.5), (0,0,1), (.60,.75,1), 450, 3)
    light('Court rim', (0,2,4), (0,0,1.3), (1,.65,.36), 600, 2)


def river():
    def p(x,y,z):
        return (x+RIVER_X,y,z)

    stone = material('River | dark wet stone', (.045,.052,.060), .42)
    water = material('River | opaque night water', (.018,.060,.075), .20)
    wood = material('River | boat wood', (.105,.052,.021))
    iron = material('River | gate bars', (.018,.022,.026))
    red = material('River | observed red shoulder cloth', (.36,.032,.018))
    silhouette = material('River | unidentified person', (.027,.030,.034))
    amber = material('River | lamp flame', (1,.34,.045), .4, 7)
    foam = material('River | faint water highlights', (.15,.25,.27), .5)
    skin = material('River | niece hand stand-in', (.43,.25,.14))
    surface = box('Night river surface', p(0,0,-.11), (11,11,.12), water)
    surface['Note'] = 'Opaque stylized blocking water; fluid simulation is deferred.'
    for index in range(4):
        box('Ghat step', p(0,1.25+index*.35,.06+index*.16), (5.5,.50,.27), stone, .02)
    box('Upper quay', p(0,3.3,.51), (7,2,.70), stone, .02)
    for x in (-1.35,1.35):
        box('Gate stone post', p(x,3.25,1.65), (.35,.38,2.25), stone, .03)
    box('Gate lintel', p(0,3.25,2.85), (3,.4,.3), stone, .03)
    for x in (-1.05,-.70,-.35,0,.35,.70,1.05):
        box('Gate upright in shadow', p(x,3.27,1.72), (.045,.08,1.9), iron)
    for z in (.95,2.5):
        box('Gate cross brace', p(0,3.27,z), (2.3,.09,.055), iron)
    box('Lamp ledge', p(.95,2.90,2.08), (.35,.32,.12), stone, .02)
    oval('Clay lamp', p(.95,2.83,2.18), (.12,.075,.04), wood)
    oval('Small flame', p(.95,2.82,2.26), (.018,.018,.055), amber)
    data = bpy.data.lights.new('Lamp light','POINT')
    data.energy, data.color, data.shadow_soft_size = 62, (1,.33,.07), .1
    lamp = bpy.data.objects.new('Lamp light',data)
    bpy.context.scene.collection.objects.link(lamp)
    lamp.location = p(.95,2.64,2.34)
    # Back-only, no facial features: preserve the uncertainty in Gopal's testimony.
    oval('Unidentified back', p(.53,2.98,1.55), (.19,.13,.39), silhouette)
    oval('Unidentified head | back only', p(.53,3.02,2.05), (.11,.10,.15), silhouette)
    cloth = box('Red cloth across rear shoulder', p(.53,2.83,1.80), (.47,.055,.23), red, .03)
    cloth.rotation_euler.y = -.12
    for x in (.43,.64):
        oval('Unidentified legs',p(x,2.98,1.02),(.065,.08,.37),silhouette)
    for x in (-.58,.58):
        line('Boat gunwale', [p(x*.75,-3.5,.21),p(x,-2.7,.23),p(x,-1.8,.24),p(x*.75,-1.2,.28)], .055, wood)
    for y in (-3.2,-2.8,-2.4,-2,-1.6):
        box('Boat floor plank',p(0,y,.10), (1.12,.35,.055), wood, .01)
    line('Oar shaft', [p(.18,-2.8,.29),p(.80,-2.0,.08),p(1.35,-1.35,-.055)], .028, wood)
    blade=box('Oar blade', p(1.38,-1.31,-.06), (.19,.55,.04), wood,.015)
    blade.rotation_euler.z = -.55
    line('Niece forearm | framing stand-in',[p(.48,-2.30,.48),p(.69,-2.30,.25)],.045,skin)
    oval('Niece wrist | framing stand-in',p(.69,-2.30,.25),(.050,.052,.10),skin)
    palm=oval('Niece hand | framing stand-in',p(.75,-2.30,.14),(.045,.047,.085),skin)
    palm.rotation_euler.y=-.45
    for digit in range(4):
        oval('Niece fingertip at water',p(.75+(digit-1.5)*.021,-2.30,.015),(.010,.013,.065),skin)
    thumb=oval('Niece thumb',p(.725,-2.335,.115),(.015,.019,.049),skin)
    thumb.rotation_euler.y=-.45
    for radius in (.12,.20,.29):
        line('Fingertip ripple', [p(.76+radius*math.cos(i*math.tau/48),
                                   -2.30+radius*.5*math.sin(i*math.tau/48),-.038)
                                  for i in range(49)], .0022,foam)
    for row in range(6):
        y=-.7+row*.41
        line('Step waterline ripple', [p(-2.3+i*.20,y+.015*math.sin(i*1.5+row),-.037)
                                      for i in range(24)], .002,foam)
    light('Night river blue fill',p(-3,-1,5),p(0,1,0),(.26,.43,.72),180,5)
    light('Night hand bounce',p(1.5,-3.8,1.8),p(.75,-2.30,.12),(.53,.66,1),45,1.5)
    return surface


def pose_keys(character, timeline, is_gopal):
    rig = character.rig
    for side, sign in (('L',1),('R',-1)):
        build_cast.turn(rig,f'upper_arm.{side}',(0,1,0),sign*75)
        build_cast.turn(rig,f'forearm.{side}',(0,0,1),sign*-7)
        for digit in range(1,5):
            build_cast.turn(rig,f'finger_{digit:02d}.{side}',(0,1,0),sign*16)
    for bone in rig.pose.bones:
        bone.rotation_mode='QUATERNION'
        bone.keyframe_insert('rotation_quaternion',frame=0)
    cues={cue['cue_id'][-3:]:cue for cue in timeline['cues']}
    if is_gopal:
        actions=[('L06','chest',(0,0,1),-16),
                 ('L06','head',(0,0,1),-10),
                 ('L10','forearm.R',(0,1,0),-32)]
    else:
        actions=[('L07','head',(1,0,0),9),
                 ('L11','forearm.R',(0,1,0),-35)]
    for cue_id,joint,axis,degrees in actions:
        cue=cues[cue_id]
        bone=rig.pose.bones[joint]
        baseline=bone.rotation_quaternion.copy()
        start,end=int(cue['start_frame']),int(cue['end_frame_exclusive'])
        bone.rotation_quaternion=baseline
        bone.keyframe_insert('rotation_quaternion',frame=start-6)
        build_cast.turn(rig,joint,axis,degrees)
        bone.keyframe_insert('rotation_quaternion',frame=start+10)
        bone.keyframe_insert('rotation_quaternion',frame=end-8)
        bone.rotation_quaternion=baseline
        bone.keyframe_insert('rotation_quaternion',frame=end+12)
    # Mouth motion is amplitude-driven blocking, not phoneme-accurate lip sync.
    mouth=next(obj for obj in character.parts if obj.data.shape_keys)
    shape=mouth.data.shape_keys.key_blocks['Mouth_Ah']
    shape.value=0
    shape.keyframe_insert('value',frame=0)
    import wave
    import array
    for cue in timeline['cues']:
        if cue['speaker_id']!=character.name:
            continue
        with wave.open(str(EPISODE/cue['audio_file']),'rb') as stream:
            values=array.array('h',stream.readframes(stream.getnframes()))
        start,end=int(cue['start_frame']),int(cue['end_frame_exclusive'])
        shape.value=0
        shape.keyframe_insert('value',frame=start-1)
        for frame in range(start,end,3):
            index=round((frame-start)*timeline['sample_rate']/timeline['fps'])
            samples=values[index:index+1500]
            rms=math.sqrt(sum(sample*sample for sample in samples)/max(1,len(samples)))/32768
            shape.value=min(.68,rms*5.5)
            shape.keyframe_insert('value',frame=frame)
        shape.value=0
        shape.keyframe_insert('value',frame=end)


def main(selected_shots=None):
    OUTPUT.mkdir(parents=True,exist_ok=True)
    frames=OUTPUT/'Frames'
    frames.mkdir(exist_ok=True)
    timeline=json.loads((EPISODE/'E01_SC04_Animatic_Timeline.json').read_text(encoding='utf-8'))
    characters=[build_cast.make_character(module) for module in (vikram,gopal)]
    scene=bpy.data.scenes.new('E01_SC04 | Interrogation animatic')
    bpy.context.window.scene=scene
    for character in characters:
        scene.collection.children.link(character.collection)
    king,boatman=characters
    king.rig.location=(.88,.12,0)
    king.rig.rotation_euler.z=math.radians(-48)
    boatman.rig.location=(-1.01,-.06,0)
    boatman.rig.rotation_euler.z=math.radians(46)
    for character in characters:
        pose_keys(character,timeline,character.name=='Gopal')
    court()
    water=river()
    waterlines=[obj for obj in scene.objects if obj.name.startswith('Step waterline ripple')]
    for obj in [water,*waterlines]:
        baseline=obj.location.z
        previous=baseline
        for shot in timeline['shots']:
            height=baseline+(.28 if shot['id'].endswith('SH04') else 0)
            obj.location.z=previous
            obj.keyframe_insert('location',frame=max(0,shot['start_frame']-1),index=2)
            obj.location.z=height
            obj.keyframe_insert('location',frame=shot['start_frame'],index=2)
            previous=height
    scene.world=bpy.data.worlds.new('Pilot | low ambient')
    scene.world.use_nodes=True
    background=scene.world.node_tree.nodes['Background']
    background.inputs['Color'].default_value=(.15,.19,.24,1)
    background.inputs['Strength'].default_value=.14
    scene.render.engine='CYCLES'
    scene.cycles.samples=32
    # Some packaged Blender builds omit OpenImageDenoise entirely.
    scene.cycles.use_denoising=False
    scene.render.resolution_x=1280
    scene.render.resolution_y=720
    scene.render.resolution_percentage=100
    scene.render.fps=timeline['fps']
    scene.render.image_settings.file_format='PNG'
    scene.view_settings.view_transform='AgX'
    scene.frame_start=0
    scene.frame_end=timeline['total_frames']-1
    scene.unit_settings.system='METRIC'
    cameras=[
        camera('SH01 | Chalk geography',(-.52,-2.50,2.50),(-.52,-.1,0),ortho=2.8),
        camera('SH02 | Gopal testimony',(-2.55,-3.45,1.95),(-1.01,-.06,1.32),lens=66),
        camera('SH03 | Lamp and red cloth',(RIVER_X-.5,-2.15,1.0),(RIVER_X+.62,2.87,2.0),lens=62),
        camera('SH04 | Flooded steps',(RIVER_X-1,-.45,.95),(RIVER_X+.1,1.9,.35),lens=50),
        camera('SH05 | Vikram asks about face',(2.15,-2.85,1.85),(.88,.12,1.65),lens=78),
        camera('SH06 | Shoulder demonstration',(-2.50,-3.20,1.86),(-1.01,-.06,1.33),lens=64),
        camera('SH07 | Vikram asks about gate',(2.15,-2.85,1.85),(.88,.12,1.65),lens=78),
        camera('SH08 | Gate below lamp',(RIVER_X-.55,-1.0,.88),(RIVER_X+.48,3.00,1.88),lens=65),
        camera('SH09 | Attention on niece',(RIVER_X+1.35,-3.40,.70),(RIVER_X+.74,-2.30,.09),lens=58),
        camera('SH10 | Gopal admits uncertainty',(-.05,-2.80,1.77),(-1.01,-.06,1.56),lens=74),
        camera('SH11 | Record observations',(.15,-4.0,2.15),(1.40,.65,1.23),lens=62),
    ]
    for shot,cam in zip(timeline['shots'],cameras):
        marker=scene.timeline_markers.new(shot['id'],frame=shot['start_frame'])
        marker.camera=cam
        cam['Shot purpose']=shot['title']
    editor=scene.sequence_editor_create()
    # Blender 4.x and 5.x expose the sequence collection under different names.
    strips=getattr(editor,'strips',None)
    if strips is None:
        strips=editor.sequences
    sound=strips.new_sound('Synthetic Hindi scratch dialogue',str(EPISODE/'Audio/E01_SC04_Dialogue_Mix.wav'),channel=1,frame_start=0)
    sound.sound.filepath='//../Audio/E01_SC04_Dialogue_Mix.wav'
    scene.render.use_sequencer=False
    scene['Status']='ANIMATIC v0.1 — staged keyframes and synthetic scratch dialogue'
    scene['Limits']='Court clerk and river inserts are stand-ins. Mouth keys are amplitude blocking.'
    scene['Source cast']='Original character generator geometry preserved; original library is untouched.'
    scene.camera=cameras[0]
    scene.frame_set(0)
    build_cast.configure_view(scene,camera=True)
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT/'E01_SC04_Animatic.blend'),compress=True)
    # Render a composed panel per shot. The editable scene retains the pose keys.
    for shot,cam in zip(timeline['shots'],cameras):
        output=frames/f"{shot['id']}.png"
        if selected_shots and shot['id'][-4:] not in selected_shots:
            continue
        representative=round(shot['start_frame']+.36*(shot['end_frame_exclusive']-shot['start_frame']))
        scene.frame_set(representative)
        scene.camera=cam
        scene.render.filepath=str(output)
        bpy.ops.render.render(write_still=True)
        print(f'Rendered {output.name}',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shots',nargs='+',choices=[f'SH{index:02}' for index in range(1,12)])
    arguments=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    main(parser.parse_args(arguments).shots)
