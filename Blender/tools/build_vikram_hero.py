"""Build the adult Vikram model using Blender Studio's CC0 realistic male base."""

import argparse
import math
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_cast import aim, light, setup_stage, stage_camera, studio_material, turn
from character import Character


OUTPUT = Path(__file__).resolve().parents[1] / 'Characters' / 'Vikram'
BODY = 'GEO-body_male_realistic'
HERO = dict(name='VikramHero', skin=(.384,.179,.100), hair=(.033,.022,.016), iris=(.089,.042,.019))

TORSO = [(.88,.197,-.137,.113),(.93,.180,-.139,.118),(.98,.177,-.137,.111),
         (1.03,.174,-.145,.083),(1.08,.164,-.148,.072),(1.13,.161,-.147,.072),
         (1.18,.163,-.151,.083),(1.23,.174,-.155,.095),(1.28,.188,-.147,.100),
         (1.33,.210,-.157,.115),(1.38,.210,-.149,.121),(1.43,.202,-.121,.118),
         (1.46,.210,-.105,.114),(1.49,.107,-.087,.103)]

LIMB = {'shoulder':(.195,.006,1.439), 'elbow':(.320,0,1.193),
        'wrist':(.409,-.069,.966), 'palm':(.439,-.101,.887),
        'hip':(.107,-.013,.881), 'knee':(.151,.012,.501),
        'ankle':(.187,.060,.100), 'ball':(.247,-.057,.030), 'toes':(.268,-.104,.023),
        'eye':(.0358,-.1326,1.720)}

FINGERS = (((.447,-.142,.883),(.460,-.182,.819)),
           ((.457,-.120,.872),(.474,-.159,.796)),
           ((.456,-.096,.865),(.469,-.123,.788)),
           ((.447,-.072,.862),(.467,-.068,.797)))
THUMB = ((.403,-.127,.924),(.402,-.190,.893))


def mirrored(point, sign):
    return (point[0]*sign, point[1], point[2])


def bvh(mesh):
    return BVHTree.FromPolygons([vertex.co for vertex in mesh.vertices],
                                [face.vertices[:] for face in mesh.polygons])


def gaussian(value, center, width):
    return math.exp(-((value-center)/width)**2)


class VikramHero(Character):
    def __init__(self, source):
        self.landmarks = {'head_top':1.84, 'chin':(0,-.129,1.592),
                          'mouth':(0,-.149,1.648), 'nose_tip':(0,-.179,1.677),
                          'torso_profile':[(z,0,(front+back)/2,width,(back-front)/2)
                                           for z,width,front,back in TORSO]}
        for side, sign in (('L',1),('R',-1)):
            self.landmarks.update({f'{name}.{side}':mirrored(point,sign) for name,point in LIMB.items()})
        super().__init__(HERO)
        self.scene.name = 'Vikram | Model and rig'
        self.collection.asset_data.description = 'Adult Vikram. Original court costume on Blender Studio CC0 anatomy.'
        self.load_anatomy(source)

    def make_rig(self):
        bones = bpy.data.armatures.new('VikramHero_Skeleton')
        rig = bpy.data.objects.new('VikramHero_Rig', bones)
        self.collection.objects.link(rig)
        bones.display_type = 'STICK'
        bpy.context.view_layer.objects.active = rig
        rig.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')

        def add(name, head, tail, parent=None, deform=True):
            joint = bones.edit_bones.new(name)
            joint.head, joint.tail = head, tail
            joint.use_deform = deform
            if parent:
                joint.parent = bones.edit_bones[parent]

        add('root',(0,0,0),(0,0,.17),deform=False)
        add('hips',(0,.006,.887),(0,-.018,1.048),'root')
        add('spine',(0,-.018,1.048),(0,-.037,1.251),'hips')
        add('chest',(0,-.037,1.251),(0,.004,1.463),'spine')
        add('neck',(0,.004,1.463),(0,-.022,1.583),'chest')
        add('head',(0,-.022,1.583),(0,-.028,1.830),'neck')
        for side, sign in (('L',1),('R',-1)):
            def at(name):
                return self.landmarks[f'{name}.{side}']

            add(f'clavicle.{side}',mirrored((.042,-.014,1.435),sign),at('shoulder'),'chest')
            add(f'upper_arm.{side}',at('shoulder'),at('elbow'),f'clavicle.{side}')
            add(f'forearm.{side}',at('elbow'),at('wrist'),f'upper_arm.{side}')
            add(f'hand.{side}',at('wrist'),at('palm'),f'forearm.{side}')
            for index,(start,end) in enumerate(FINGERS,1):
                add(f'finger_{index:02d}.{side}',mirrored(start,sign),mirrored(end,sign),f'hand.{side}')
            add(f'thumb.{side}',mirrored(THUMB[0],sign),mirrored(THUMB[1],sign),f'hand.{side}')
            add(f'thigh.{side}',at('hip'),at('knee'),'hips')
            add(f'shin.{side}',at('knee'),at('ankle'),f'thigh.{side}')
            add(f'foot.{side}',at('ankle'),at('ball'),f'shin.{side}')
            add(f'toes.{side}',at('ball'),at('toes'),f'foot.{side}')
            eye = at('eye')
            add(f'eye.{side}',eye,(eye[0],eye[1]-.023,eye[2]),'head')
        bpy.ops.object.mode_set(mode='OBJECT')
        rig['Purpose'] = 'FK model deformation rig. Facial acting will use the dedicated facial-rig pass.'
        return rig

    def load_anatomy(self, source):
        requested = [BODY, BODY+'.eye.L', BODY+'.eye.R']
        with bpy.data.libraries.load(str(source), link=False) as (available, chosen):
            if not set(requested).issubset(available.objects):
                raise ValueError('Select Blender Studio Human Base Meshes v1.4.1.')
            chosen.objects = requested
        body, *eyes = chosen.objects
        for obj in chosen.objects:
            self.collection.objects.link(obj)
        bpy.context.view_layer.update()
        bounds = [body.matrix_world @ Vector(corner) for corner in body.bound_box]
        minimum_z, maximum_z = min(p.z for p in bounds), max(p.z for p in bounds)
        center_x = (min(p.x for p in bounds)+max(p.x for p in bounds))/2
        fit = Matrix.Scale(1.84/(maximum_z-minimum_z), 4) @ Matrix.Translation((-center_x,0,-minimum_z))
        source_matrices = [obj.matrix_world.copy() for obj in chosen.objects]
        for obj, matrix in zip(chosen.objects, source_matrices):
            appended_mesh = obj.data
            obj.data = appended_mesh.copy()
            if appended_mesh.users == 0:
                bpy.data.meshes.remove(appended_mesh)
            obj.parent = None
            obj.matrix_world = Matrix.Identity(4)
            obj.modifiers.clear()
            obj.data.transform(fit @ matrix)
            obj.data.update()
            for polygon in obj.data.polygons:
                polygon.use_smooth = True
            obj.data.materials.clear()

        body.name = 'VikramHero_Anatomy'
        body.data.name = 'VikramHero_AnatomyMesh'
        for vertex in body.data.vertices:
            x,y,z = vertex.co
            # Localized tweaks preserve the eyelid seam and modeled mouth cavity.
            jaw = gaussian(z,1.621,.031)*gaussian(abs(x),.066,.035)
            vertex.co.x += x*.055*jaw
            ridge = gaussian(z,1.682,.017)*gaussian(y,-.169,.022)*gaussian(x,0,.024)
            vertex.co.x += .0016*ridge
            vertex.co.y -= .004*ridge*gaussian(abs(x),.013,.017)
        body.data.update()
        self.skin_mesh = body
        self.skin_bvh = bvh(body.data)
        self.m['skin'] = self.skin_material()
        body.data.materials.append(self.m['skin'])
        self.bind_body(body)
        for eye,side in zip(eyes,('L','R')):
            self.make_eye(eye,side)

    def skin_surface(self, x, z):
        point = self.skin_bvh.ray_cast(Vector((x,-1,z)),Vector((0,1,0)),2)[0]
        return point.y if point is not None else None

    def skin_material(self):
        mat = self.m['skin']
        mesh = self.skin_mesh.data
        pigment = mesh.color_attributes.new(name='Skin pigment',type='FLOAT_COLOR',domain='POINT')
        rest = mesh.attributes.new(name='Skin rest coordinates',type='FLOAT_VECTOR',domain='POINT')
        rest.data.foreach_set('vector',[component for vertex in mesh.vertices for component in vertex.co])
        for index,vertex in enumerate(mesh.vertices):
            x,y,z = vertex.co
            frontal = min(1, max(0,(-y-.065)/.052))
            cheeks = gaussian(abs(x),.054,.030)*gaussian(z,1.694,.023)*frontal
            temple = gaussian(abs(x),.067,.017)*gaussian(z,1.750,.024)*frontal
            socket = gaussian(abs(x),.037,.019)*gaussian(z,1.702,.009)*frontal
            lip_pitch = self.landmarks['mouth'][2]+.0016*math.cos(min(1,abs(x)/.034)*math.pi)
            lips = gaussian(x,0,.020)*gaussian(z,lip_pitch,.0067)*frontal
            chin = gaussian(z,1.621,.027)*frontal
            tone = 1 + .023*math.sin(53*x+18*z)*math.cos(33*y-24*z) - .15*socket - .07*temple - .07*chin
            pigment.data[index].color = (.384*tone+.029*cheeks-.041*lips,
                                         .179*tone-.009*cheeks-.040*lips,
                                         .100*tone-.004*cheeks-.019*lips,1)
        nodes,links = mat.node_tree.nodes,mat.node_tree.links
        shader = nodes.get('Principled BSDF')
        shader.inputs['Subsurface Weight'].default_value = .10
        shader.inputs['Subsurface Scale'].default_value = .024
        shader.inputs['Specular IOR Level'].default_value = .26
        color = nodes.new('ShaderNodeVertexColor')
        color.layer_name = pigment.name
        color.location = (-620,350)
        coords = nodes.new('ShaderNodeAttribute')
        coords.attribute_name = rest.name
        coords.location = (-820,0)
        tint = nodes.new('ShaderNodeTexNoise')
        tint.label = 'Subtle pigmentation in rest space'
        tint.location = (-590,100)
        tint.inputs['Scale'].default_value = 76
        tint.inputs['Detail'].default_value = 3.0
        links.new(coords.outputs['Vector'],tint.inputs['Vector'])
        value = nodes.new('ShaderNodeMapRange')
        value.location = (-360,125)
        value.inputs['To Min'].default_value = .87
        value.inputs['To Max'].default_value = 1.08
        links.new(tint.outputs['Fac'],value.inputs['Value'])
        tone = nodes.new('ShaderNodeMixRGB')
        tone.blend_type = 'MULTIPLY'
        tone.location = (-115,315)
        tone.inputs[0].default_value = 1
        links.new(color.outputs['Color'],tone.inputs[1])
        links.new(value.outputs['Result'],tone.inputs[2])
        links.new(tone.outputs['Color'],shader.inputs['Base Color'])
        pores = nodes.new('ShaderNodeTexNoise')
        pores.label = 'Fine pores in rest space'
        pores.location = (-590,-200)
        pores.inputs['Scale'].default_value = 970
        pores.inputs['Detail'].default_value = 2.2
        links.new(coords.outputs['Vector'],pores.inputs['Vector'])
        bump = nodes.new('ShaderNodeBump')
        bump.location = (-135,-240)
        bump.inputs['Strength'].default_value = .30
        bump.inputs['Distance'].default_value = .00051
        links.new(pores.outputs['Fac'],bump.inputs['Height'])
        links.new(bump.outputs['Normal'],shader.inputs['Normal'])
        rough = nodes.new('ShaderNodeMapRange')
        rough.location = (-355,-200)
        rough.inputs['To Min'].default_value = .41
        rough.inputs['To Max'].default_value = .56
        links.new(pores.outputs['Fac'],rough.inputs['Value'])
        links.new(rough.outputs['Result'],shader.inputs['Roughness'])
        return mat

    def bind_body(self, body):
        bpy.ops.object.select_all(action='DESELECT')
        body.select_set(True)
        self.rig.select_set(True)
        bpy.context.view_layer.objects.active = self.rig
        for side in ('L','R'):
            self.rig.data.bones[f'eye.{side}'].use_deform = False
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
        for side in ('L','R'):
            self.rig.data.bones[f'eye.{side}'].use_deform = True
        groups = body.vertex_groups
        empty = 0
        for vertex in body.data.vertices:
            weights = [(item.group,item.weight) for item in vertex.groups if item.weight>1e-5]
            if not weights:
                empty += 1
                continue
            total = sum(weight for _,weight in weights)
            for item in list(vertex.groups):
                groups[item.group].remove([vertex.index])
            for index,weight in weights:
                groups[index].add([vertex.index],weight/total,'REPLACE')
        if empty:
            raise RuntimeError(f'Anatomy skinning failed on {empty} vertices')
        modifier = next(mod for mod in body.modifiers if mod.type=='ARMATURE')
        modifier.name = 'Character Skinning'
        modifier.use_deform_preserve_volume = True
        smooth = body.modifiers.new('Review subdivision','SUBSURF')
        smooth.levels = 1
        smooth.render_levels = 2
        self.parts.append(body)

    def fit_dressed_skin(self):
        """Keep a full sculpt backup and remove hidden skin from the export mesh."""
        body = self.skin_mesh
        reference = body.copy()
        reference.name = 'VikramHero_FullAnatomy'
        anatomy = bpy.data.collections.new('Vikram | Full anatomy reference')
        self.scene.collection.children.link(anatomy)
        anatomy.objects.link(reference)
        anatomy.hide_render = True
        anatomy.hide_viewport = True
        body.data = body.data.copy()
        body.data.name = 'VikramHero_DressedSkinMesh'

        editable = bmesh.new()
        editable.from_mesh(body.data)
        for height in (.064,.150,.985,1.525):
            bmesh.ops.bisect_plane(editable,geom=[*editable.verts,*editable.edges,*editable.faces],
                                  dist=1e-5,plane_co=(0,0,height),plane_no=(0,0,1))
        hidden = []
        for face in editable.faces:
            x,_,z = face.calc_center_median()
            collar = z >= 1.525
            hands = abs(x)>.363 and z<.985
            ankles = abs(x)>.11 and .064<z<.150
            if not (collar or hands or ankles):
                hidden.append(face)
        bmesh.ops.delete(editable,geom=hidden,context='FACES')
        for vertex in editable.verts:
            z = vertex.co.z
            if 1.524 <= z < 1.578:
                t = min(1,(z-1.524)/.054)
                taper = .50+.50*t*t*(3-2*t)
                vertex.co.x *= taper
                vertex.co.y = -.025+(vertex.co.y+.025)*taper
        editable.to_mesh(body.data)
        editable.free()
        body.data.update()
        body['Garment coverage'] = 'Only exposed skin is included in the dressed mesh. Full rigged anatomy is in the hidden reference collection.'

    def make_eye(self, obj, side):
        eye_bone = f'eye.{side}'
        obj.name = f'VikramHero_Eyeball.{side}'
        obj.parent = self.rig
        mesh = obj.data
        sclera = self.mat('Warm sclera',(.57,.46,.40),.27)
        mesh.materials.append(sclera)
        obj.vertex_groups.new(name=eye_bone).add(list(range(len(mesh.vertices))),1,'REPLACE')
        modifier = obj.modifiers.new('Character Skinning','ARMATURE')
        modifier.object = self.rig
        self.parts.append(obj)
        center = self.landmarks[eye_bone]
        eye_bvh = bvh(mesh)
        vertices,colors,faces = [],[],[]
        rings,segments = (.00022,.00212,.00243,.00323,.00447,.00565,.00615),92
        for ring,radius in enumerate(rings):
            for index in range(segments):
                angle = index*math.tau/segments
                x = center[0]+radius*math.cos(angle)
                z = center[2]+radius*math.sin(angle)
                point = eye_bvh.ray_cast(Vector((x,-1,z)),Vector((0,1,0)),2)[0]
                if point is None:
                    raise RuntimeError(f'Iris outside {side} eyeball')
                vertices.append((x,point.y-.00018,z))
                ray = .76+.15*math.sin(37*angle+ring*.21)+.10*math.sin(57*angle-ring*.52)
                tint = (.004,.0025,.002) if ring<2 else (.043,.018,.008) if ring==6 else (.153*ray,.065*ray,.028*ray)
                colors.append((*tint,1))
        faces.append(tuple(reversed(range(segments))))
        for ring in range(len(rings)-1):
            for index in range(segments):
                next_index = (index+1)%segments
                a,b = ring*segments,(ring+1)*segments
                faces.append((a+index,b+index,b+next_index,a+next_index))
        material = self.mat('Brown iris and pupil',(.09,.037,.018),.25)
        iris = self.mesh(f'Iris.{side}',vertices,faces,material,eye_bone)
        pigment = iris.data.color_attributes.new(name='Iris pigment',type='FLOAT_COLOR',domain='POINT')
        for sample,color in zip(pigment.data,colors):
            sample.color = color
        node = material.node_tree.nodes.new('ShaderNodeVertexColor')
        node.layer_name = pigment.name
        material.node_tree.links.new(node.outputs['Color'],material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])


def export_fbx(hero):
    bpy.context.window.scene = hero.scene
    bpy.ops.object.select_all(action='DESELECT')
    hero.rig.select_set(True)
    bpy.context.view_layer.objects.active = hero.rig
    for obj in hero.parts:
        obj.select_set(True)
    result = bpy.ops.export_scene.fbx(filepath=str(OUTPUT/'Vikram_Hero.fbx'), use_selection=True,
        object_types={'ARMATURE','MESH'}, axis_forward='-Z', axis_up='Y',
        apply_scale_options='FBX_SCALE_UNITS', use_mesh_modifiers=False, add_leaf_bones=False,
        bake_anim=False, mesh_smooth_type='FACE')
    if 'FINISHED' not in result:
        raise RuntimeError('Could not export Vikram hero')


def copy_model(scene, hero, label, x, yaw):
    cast = bpy.data.collections.new(label)
    scene.collection.children.link(cast)
    rig = hero.rig.copy()
    cast.objects.link(rig)
    rig.name = label
    rig.location.x = x
    rig.rotation_euler.z = math.radians(yaw)
    for source in hero.parts:
        obj = source.copy()
        cast.objects.link(obj)
        obj.parent = rig
        obj.modifiers['Character Skinning'].object = rig
    return rig


def lighting(scene, warm=True):
    light(scene,'Broad warm key',(-2.5,-3.7,4),(0,0,1.45),(1,.85,.71),410 if warm else 320,2.2)
    light(scene,'Soft neutral fill',(2.9,-1.6,2.1),(0,0,1.25),(.72,.83,1),95,2.3)
    light(scene,'Cool edge',(-2.2,1.3,3.2),(0,0,1.4),(.53,.73,1),290,1.7)
    light(scene,'Amber edge',(1.7,1.9,3.25),(0,0,1.4),(1,.65,.39),290,1.8)


def floor(color):
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,.006))
    bpy.context.object.name = 'Studio floor'
    bpy.context.object.data.materials.append(studio_material('Warm charcoal sweep',color,.92))


def lookdev(preview, hero):
    bpy.context.window.scene = preview
    for obj in list(preview.objects):
        bpy.data.objects.remove(obj,do_unlink=True)
    preview.name = 'Vikram | Turnaround'
    setup_stage(preview,1600,1060,28,.21)
    floor((.059,.047,.038))
    stage_camera(preview,'Adult silhouette camera',(0,-7,1.42),(0,0,.95),3.56)
    lighting(preview)
    for x,yaw,label in ((-1.00,5,'Front'),(0,49,'Three-quarter pose'),(1.00,177,'Back')):
        rig = copy_model(preview,hero,label,x,yaw)
        if label=='Three-quarter pose':
            turn(rig,'head',(0,0,1),-15)
            turn(rig,'chest',(0,0,1),-4)
            turn(rig,'forearm.R',(1,0,0),-25)
    preview.render.filepath = '//Vikram_Turnaround.png'

    portrait = bpy.data.scenes.new('Vikram | Portrait and pose')
    setup_stage(portrait,1040,1200,38,.16)
    floor((.036,.031,.027))
    camera = stage_camera(portrait,'Close-up pose camera',(1.20,-4.10,1.72),(0,-.025,1.57),.69)
    aim(camera,(0,-.025,1.57))
    lighting(portrait,False)
    rig = copy_model(portrait,hero,'Portrait pose',0,9)
    turn(rig,'head',(0,0,1),-11)
    turn(rig,'neck',(1,0,0),3)
    turn(rig,'chest',(0,0,1),-6)
    turn(rig,'forearm.R',(1,0,0),-25)
    turn(rig,'upper_arm.R',(1,0,0),-9)
    portrait.render.filepath = '//Vikram_Portrait.png'
    return portrait


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',type=Path,required=True)
    parser.add_argument('--anatomy-only',action='store_true',help='Fit and check the rig without writing output files')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    preview = bpy.context.scene
    hero = VikramHero(args.base)
    hero.validate()
    print(f'ANATOMY PASS: {len(hero.skin_mesh.data.vertices)} vertices, {len(hero.rig.data.bones)} bones, '
          f'{len(hero.skin_mesh.data.uv_layers)} UV layers',flush=True)
    if args.anatomy_only:
        return
    from hero_groom import dress_head
    from hero_wardrobe import dress
    dress(hero)
    dress_head(hero)
    hero.fit_dressed_skin()
    hero.validate()
    OUTPUT.mkdir(parents=True,exist_ok=True)
    export_fbx(hero)
    portrait = lookdev(preview,hero)
    bpy.context.window.scene = portrait
    bpy.ops.object.select_all(action='DESELECT')
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                viewer = area.spaces.active
                viewer.overlay.show_overlays = False
                viewer.shading.color_type = 'MATERIAL'
                viewer.region_3d.view_perspective = 'CAMERA'
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT/'Vikram_Hero.blend'),compress=True)
    bpy.ops.render.render(write_still=True)
    bpy.context.window.scene = preview
    bpy.ops.render.render(write_still=True)


if __name__=='__main__':
    main()
