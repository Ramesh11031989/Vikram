"""Build Shyam Munshi, called Betal, and the poses from Chapter 1."""

import argparse
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_cast import light, setup_stage, stage_camera, studio_material, turn
from build_vikram_hero import AdultHero, copy_model, export_fbx, gaussian, lighting
from hero_wardrobe import fabric, patch
from textile import store_rest_positions


CHARACTERS = Path(__file__).resolve().parents[1] / 'Characters'
OUTPUT = CHARACTERS / 'Betal'
VIKRAM = CHARACTERS / 'Vikram' / 'Vikram_Hero.blend'
SWELL = 'Right ankle swelling'
STATE = 'Right ankle state'


def smooth(t):
    t = max(0, min(1, t))
    return t*t*(3-2*t)


class BetalHero(AdultHero):
    display_name = 'Betal'
    appearance = dict(name='BetalHero', skin=(.342,.155,.095), hair=(.029,.024,.021), iris=(.089,.042,.019))
    description = 'श्याम मुंशी उर्फ़ बेताल। Former royal clerk and keeper of the oiled-paper bundle.'

    def __init__(self, source):
        super().__init__(source)
        self.rig['Identity'] = 'श्याम मुंशी उर्फ़ बेताल'
        self.rig['Role'] = 'Former royal clerk. Shyam Munshi and Betal are the same person.'
        self.rig.scale = (1.75/1.84,)*3

    def sculpt_anatomy(self, body):
        for vertex in body.data.vertices:
            x,y,z = vertex.co
            jaw = gaussian(z,1.616,.029)*gaussian(abs(x),.065,.029)
            hollow = gaussian(z,1.671,.019)*gaussian(abs(x),.067,.019)*gaussian(y,-.088,.058)
            vertex.co.x -= x*.092*jaw
            vertex.co.y += .008*hollow
            nose = gaussian(z,1.683,.024)*gaussian(y,-.158,.026)*gaussian(x,0,.027)
            vertex.co.y -= .0055*nose
            vertex.co.x -= .0028*nose
            lower_lid = gaussian(z,1.701,.006)*gaussian(abs(x),.039,.018)*gaussian(y,-.116,.030)
            vertex.co.y -= .0019*lower_lid
            lip_corner = gaussian(z,1.647,.007)*gaussian(x,-.025,.008)*gaussian(y,-.137,.027)
            vertex.co.z += .0016*lip_corner

    def fit_clerk_skin(self):
        right_hem, left_hem = .259, .210

        def visible(point):
            x,_,z = point
            return (z>=1.525 or abs(x)>.363 and z<.985 or
                    x<-.090 and z<right_hem or x>.090 and z<left_hem)

        def refine(point):
            if 1.524<=point.z<1.578:
                taper = .50+.50*smooth((point.z-1.524)/.054)
                point.x *= taper
                point.y = -.025+(point.y+.025)*taper

        self.fit_covered_skin((left_hem,right_hem,.985,1.525),visible,refine)

    def build_ankle(self):
        body = self.skin_mesh
        body.shape_key_add(name='Basis')
        swollen = body.shape_key_add(name=SWELL,from_mix=False)
        swollen.value = 0
        center = Vector((-.186,.056,.129))
        affected = 0
        pigments = body.data.color_attributes['Skin pigment'].data
        for index,(source,target) in enumerate(zip(body.data.vertices,swollen.data)):
            p = source.co
            if p.x>=-.105 or not .071<p.z<.210:
                continue
            delta = p-center
            envelope = gaussian(p.z,.127,.033)*gaussian(p.y,.055,.059)
            bulge = .013*envelope*(.68+.32*smooth(-delta.x/.036))
            radial = Vector((delta.x,delta.y,0))
            if radial.length>.0001:
                target.co = p+radial.normalized()*bulge
                affected += 1
            tint = min(.12,bulge*9)
            r,g,b,_ = pigments[index].color
            pigments[index].color = (r*(1+tint*.22),g*(1-tint),b*(1-tint*.55),1)
        if affected<25:
            raise RuntimeError('The right ankle target has too few affected vertices')

        surface = BVHTree.FromPolygons([vertex.co for vertex in swollen.data],
                                      [face.vertices[:] for face in body.data.polygons])
        cloth = fabric(self,'Unbleached linen ankle wrap',(.52,.434,.310),1.38,.16,.17,fine=False)
        rows,weights = [],[]
        for row in range(156):
            t = row/155
            angle = .12+t*math.tau*2.80
            direction = Vector((math.cos(angle),math.sin(angle),0))
            level = .091+.083*t+.004*math.sin(angle+1.1)
            points = []
            for edge in range(8):
                z = level+(edge/7-.5)*(.033-.004*t)+.0014*math.sin(edge*2.25+angle)
                location = Vector((center.x,center.y,z))
                hit = surface.ray_cast(location+direction*.14,-direction,.14)[0]
                folded = .0038+.0021*(math.sin(math.pi*edge/7)**2)+.0009*math.sin(angle*3)
                points.append((hit if hit is not None else location+direction*.043)+direction*folded)
            rows.append(points)
            shin = smooth((level-.094)/.065)
            weights.append({'foot.R':1-shin,'shin.R':shin})
        self.wrap = patch(self,'Right ankle • wound linen wrap',rows,weights,cloth,flip=True)
        store_rest_positions(self.wrap.data)
        tip = rows[-1][4]
        edge_path = [tip,tip+Vector((-.015,-.006,.009)),tip+Vector((-.022,-.016,.003)),tip+Vector((-.015,-.028,-.009))]
        self.tail = self.tube('Right ankle • tucked linen end',edge_path,[.007,.008,.005,.002],cloth,'shin.R')
        store_rest_positions(self.tail.data)
        self.wrap_parts = (self.wrap,self.tail)
        self.wrap['Use'] = 'Optional fitted linen wrap for the closing banyan scene. Right ankle only.'

    def set_ankle(self, rig, swollen=True, wrapped=False):
        """Set a scene instance without changing shared geometry or the source rig."""
        for part in rig.children:
            if part.type!='MESH':
                continue
            if part.data is self.skin_mesh.data:
                part.data = part.data.copy()
                part.data.shape_keys.animation_data_clear()
                part.data.shape_keys.key_blocks[SWELL].value = float(swollen)
            if any(part.data is source.data for source in self.wrap_parts):
                part.animation_data_clear()
                part.hide_render = not wrapped
                part.hide_viewport = not wrapped
        rig[STATE] = 2 if wrapped else int(swollen)

    def control_ankle(self):
        rig = self.rig
        rig[STATE] = 1
        rig.id_properties_ui(STATE).update(min=0,max=2,description='0 neutral, 1 swollen, 2 bandaged')

        def link(target,path,expression):
            driver = target.driver_add(path).driver
            value = driver.variables.new()
            value.name = 'phase'
            value.type = 'SINGLE_PROP'
            value.targets[0].id = rig
            value.targets[0].data_path = f'["{STATE}"]'
            driver.expression = expression

        link(self.skin_mesh.data.shape_keys.key_blocks[SWELL],'value','phase > 0.5')
        for part in self.wrap_parts:
            link(part,'hide_render','phase < 1.5')
            link(part,'hide_viewport','phase < 1.5')


def stone_floor(z=-.005):
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,z))
    bpy.context.object.name = 'Ground'
    bpy.context.object.data.materials.append(studio_material('Warm grey stone sweep',(.079,.070,.058),.91))


def portrait_scene(scene, hero):
    bpy.context.window.scene = scene
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj,do_unlink=True)
    scene.name = 'Betal | Portrait'
    setup_stage(scene,880,1050,28,.19)
    stone_floor()
    stage_camera(scene,'Munshi portrait camera',(1.05,-4.2,1.60),(0,-.022,1.48),.68)
    lighting(scene,False)
    rig = copy_model(scene,hero,'Shyam Munshi portrait',0,11)
    turn(rig,'head',(0,0,1),-9)
    turn(rig,'neck',(1,0,0),4)
    turn(rig,'chest',(0,0,1),5)
    hero.set_ankle(rig)
    scene.render.filepath = '//Betal_Portrait.png'
    return scene


def ankle_scene(hero):
    scene = bpy.data.scenes.new('Betal | Right ankle comparison')
    setup_stage(scene,1064,438,24,.29)
    stone_floor()
    stage_camera(scene,'Right ankle coverage camera',(-.02,-3.6,.54),(0,0,.182),1.62)
    light(scene,'Soft ankle key',(-1.2,-1.7,2.15),(0,0,.16),(1,.88,.73),205,1.3)
    light(scene,'Cool edge',(.96,1.02,1.24),(0,0,.13),(.65,.78,1),126,1.05)
    for x,wrapped,label in ((-.414,False,'Swollen right ankle'),(.414,True,'Bandaged right ankle')):
        model = copy_model(scene,hero,label,x,-16)
        hero.set_ankle(model,swollen=True,wrapped=wrapped)
    scene.render.filepath = '//Betal_Right_Ankle.png'
    return scene


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    parser.add_argument('--vikram',type=Path,default=VIKRAM)
    parser.add_argument('--model-only',action='store_true',help='Build and verify costume and ankle states without adding story poses')
    parser.add_argument('--no-render',action='store_true',help='Save the editable scene and neutral FBX only')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    from betal_hero_costume import dress
    from betal_hero_groom import dress_head

    preview = bpy.context.scene
    hero = BetalHero(args.base)
    dress(hero)
    dress_head(hero)
    hero.fit_clerk_skin()
    hero.build_ankle()
    hero.validate()
    print(f'BETAL MODEL PASS: {len(hero.rig.data.bones)} bones, {len(hero.parts)} skinned parts, '
          f'{len(hero.skin_mesh.data.vertices)} exposed skin vertices',flush=True)
    args.output.mkdir(parents=True,exist_ok=True)
    export_fbx(hero,args.output/'Betal_Hero.fbx')
    hero.control_ankle()

    scenes = [portrait_scene(preview,hero),ankle_scene(hero)]
    if not args.model_only:
        from betal_hero_poses import make_story_scenes
        scenes.extend(make_story_scenes(hero,args.vikram,args.output))
    bpy.context.window.scene = preview
    bpy.ops.object.select_all(action='DESELECT')
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                viewer = area.spaces.active
                viewer.overlay.show_overlays = False
                viewer.shading.color_type = 'MATERIAL'
                viewer.region_3d.view_perspective = 'CAMERA'
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output/'Betal_Hero.blend'),compress=True)
    if not args.no_render:
        for scene in scenes:
            bpy.context.window.scene = scene
            bpy.ops.render.render(write_still=True)


if __name__=='__main__':
    main()
