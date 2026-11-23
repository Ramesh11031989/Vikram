"""Court, water and insert details for the interrogation performance pass."""

from __future__ import annotations

import math

import bpy
from mathutils import Vector


def remove_objects(prefixes):
    for obj in list(bpy.context.scene.objects):
        if any(obj.name.startswith(prefix) for prefix in prefixes):
            bpy.data.objects.remove(obj,do_unlink=True)


def wood_grain(material):
    material.use_nodes=True
    nodes=material.node_tree.nodes
    shader=nodes.get('Principled BSDF')
    texture=nodes.new('ShaderNodeTexNoise')
    texture.inputs['Scale'].default_value=5
    texture.inputs['Detail'].default_value=1
    mapping=nodes.new('ShaderNodeVectorMath')
    mapping.operation='MULTIPLY'
    mapping.inputs[1].default_value=(2,38,3)
    coordinates=nodes.new('ShaderNodeTexCoord')
    material.node_tree.links.new(coordinates.outputs['Generated'],mapping.inputs[0])
    material.node_tree.links.new(mapping.outputs[0],texture.inputs['Vector'])
    bump=nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value=.16
    bump.inputs['Distance'].default_value=.012
    material.node_tree.links.new(texture.outputs['Fac'],bump.inputs['Height'])
    material.node_tree.links.new(bump.outputs['Normal'],shader.inputs['Normal'])


def detail_court(base, timeline):
    remove_objects(('Court clerk |','Clerk writing desk |','Desk leg','Reed pen','Evidence sheet'))
    plaster=base.material('Court | arch plaster',(.32,.24,.17))
    wood=base.material('Court | polished teak',(.15,.069,.026),.64)
    wood_grain(wood)
    paper=base.material('Court | ledger parchment',(.69,.59,.40),.92)
    ink=base.material('Court | ink',(.018,.016,.012),.7)
    brass=base.material('Court | brass paper weight',(.30,.19,.07),.42)
    for center in (-2.25,-.75,.75,2.25):
        points=[(center-.49,2.215,.35),(center-.49,2.215,1.95)]
        points.extend((center+.49*math.cos(math.pi-index*math.pi/24),2.215,
                       1.95+.49*math.sin(math.pi-index*math.pi/24)) for index in range(25))
        points.append((center+.49,2.215,.35))
        base.line('Court arch relief',points,.025,plaster)
    for obj in bpy.context.scene.objects:
        if obj.name.startswith('Chalk'):
            obj.data.bevel_depth=.006
            obj.scale.z=.07
    base.box('Court clerk writing desk',(2.13,.74,.91),(1.0,.56,.08),wood,.025)
    for x in (1.73,2.53):
        for y in (.54,.94):
            base.box('Writing desk turned leg',(x,y,.45),(.055,.055,.90),wood,.012)
    base.box('Writing desk apron',(2.13,.73,.79),(.90,.46,.16),wood,.015)
    page=base.box('Open court ledger',(2.13,.69,.961),(.58,.35,.015),paper,.003)
    base.line('Ledger spine',[(2.13,.51,.974),(2.13,.86,.974)],.003,wood)
    base.oval('Court inkpot',(2.44,.84,1.001),(.045,.043,.045),wood)
    base.oval('Court ink surface',(2.44,.84,1.041),(.032,.030,.003),ink)
    base.oval('Ledger paperweight',(1.85,.84,.991),(.032,.026,.018),brass)
    shot=timeline['shots'][-1]
    for row in range(5):
        y=.77-row*.043
        points=[(1.91+index*.009,y+.002*math.sin(index*2.1+row),.973) for index in range(24)]
        stroke=base.line('Written observation',points,.0008,ink)
        stroke.data.bevel_factor_end=0
        start=shot['start_frame']+32+row*48
        stroke.data.keyframe_insert('bevel_factor_end',frame=start)
        stroke.data.bevel_factor_end=1
        stroke.data.keyframe_insert('bevel_factor_end',frame=start+40)


def wave_height(x,y,frame):
    a=.5+.5*math.sin(frame*.065)
    b=.5+.5*math.sin(frame*.047+1.2)
    return .007*math.sin(x*1.7+y*3.1)*a+.005*math.cos(x*3.7-y*1.3)*b


def detail_water(base, timeline):
    water=bpy.data.objects['Night river surface']
    count=72
    vertices=[(-5.5+11*x/count,-5.5+11*y/count,.06)
              for y in range(count+1) for x in range(count+1)]
    faces=[]
    for y in range(count):
        for x in range(count):
            start=y*(count+1)+x
            faces.append((start,start+1,start+count+2,start+count+1))
    surface=bpy.data.meshes.new('River wave surface')
    surface.from_pydata(vertices,[],faces)
    material=water.data.materials[0]
    water.data=surface
    surface.materials.append(material)
    material.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.25
    for polygon in surface.polygons:
        polygon.use_smooth=True
    water.shape_key_add(name='Basis')
    for name,expression,frequency,phase in (
        ('Long wave','sin(x*1.7+y*3.1)',.065,0),
        ('Cross wave','cos(x*3.7-y*1.3)',.047,1.2),
    ):
        key=water.shape_key_add(name=name)
        for item,(x,y,z) in zip(key.data,vertices):
            delta=.007*math.sin(x*1.7+y*3.1) if name=='Long wave' else .005*math.cos(x*3.7-y*1.3)
            item.co.z=z+delta
        driver=key.driver_add('value').driver
        driver.type='SCRIPTED'
        driver.expression=f'.5+.5*sin(frame*{frequency}+{phase})'
    water['Water method']='Animated analytic surface waves; no fluid simulation claim.'
    for material in list(bpy.data.materials):
        if material.name in ('River | boat wood',):
            wood_grain(material)
    for obj in bpy.context.scene.objects:
        if obj.name.startswith('Step waterline ripple'):
            obj.data.bevel_depth=.0008
            obj.data.materials[0].diffuse_color=(.055,.11,.12,1)
            shader=obj.data.materials[0].node_tree.nodes['Principled BSDF']
            shader.inputs['Base Color'].default_value=(.055,.11,.12,1)
    flame=bpy.data.objects['Small flame']
    lamp=bpy.data.objects['Lamp light']
    for frame in range(0,timeline['total_frames']+8,8):
        lamp.data.energy=62*(1+.09*math.sin(frame*.73)+.035*math.sin(frame*1.31))
        lamp.data.keyframe_insert('energy',frame=frame)
        flame.scale.z=.055*(1+.12*math.sin(frame*.48))
        flame.keyframe_insert('scale',frame=frame,index=2)
    return water


def detail_hand(base,timeline):
    remove_objects(('Niece ','Fingertip ripple'))
    skin=base.material('Niece | hand skin',(.43,.25,.14),.65)
    sleeve=base.material('Niece | cotton cuff',(.52,.46,.34),.9)
    root=bpy.data.objects.new('Niece_Hand_Control',None)
    bpy.context.scene.collection.objects.link(root)
    root.location=(base.RIVER_X+.75,-2.30,0)
    root.scale=(.75,.75,.75)
    objects=[]
    def part(obj):
        obj.parent=root
        objects.append(obj)
        return obj
    part(base.line('Niece forearm',[(-.19,0,.51),(-.08,0,.32),(0,0,.20)],.028,skin))
    part(base.oval('Niece cotton cuff',(-.19,0,.48),(.045,.036,.07),sleeve))
    part(base.oval('Niece palm',(0,0,.14),(.043,.025,.073),skin))
    for index,(x,end) in enumerate(((-.031,-.042),(-.010,-.05),(.012,-.045),(.032,-.018))):
        part(base.line(f'Niece articulated finger {index+1}',[(x,0,.105),(x,-.006,.040),
             (x+.002,-.009,end+.012),(x+.002,-.01,end)],.0085,skin))
        part(base.oval(f'Niece fingertip {index+1}',(x+.002,-.01,end+.005),(.0085,.0085,.009),skin))
    part(base.line('Niece connected thumb',[(-.022,0,.17),(-.052,-.006,.123),(-.061,-.01,.080)],.012,skin))
    shot=next(shot for shot in timeline['shots'] if shot['id'].endswith('SH09'))
    for frame in range(0,timeline['total_frames']+2,2):
        offset=0
        if frame<shot['start_frame']+28:
            offset=.10*max(0,min(1,(shot['start_frame']+28-frame)/28))
        root.location.z=-.0125+offset+wave_height(.75,-2.30,frame)
        root.keyframe_insert('location',frame=frame,index=2)
    ripple_material=base.material('Niece | water ripple',(.055,.13,.15),.3)
    for index in range(4):
        radius=.07+index*.047
        ripple=base.line('Contact ripple',[(base.RIVER_X+.75+radius*math.cos(j*math.tau/64),
            -2.30+radius*.65*math.sin(j*math.tau/64),-.044) for j in range(65)],.0009,ripple_material)
        center=Vector((base.RIVER_X+.75,-2.30,-.044))
        for spline in ripple.data.splines:
            for point in spline.points:
                point.co.xyz-=center
        ripple.location=center
        for frame in range(shot['start_frame'],shot['end_frame_exclusive']+1,4):
            factor=.55+.7*((frame-shot['start_frame']+index*11)%58)/58
            ripple.scale=(factor,factor,1)
            ripple.location.z=-.043+wave_height(.75,-2.30,frame)
            ripple.keyframe_insert('scale',frame=frame)
            ripple.keyframe_insert('location',frame=frame,index=2)
    return root
