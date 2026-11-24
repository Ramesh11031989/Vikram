"""Build Gopal the boatman and the three Chapter 1 poses."""

import argparse
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.noise import noise_vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_cast import light, setup_stage, stage_camera, studio_material, turn
from build_vikram_hero import AdultHero, copy_model, export_fbx, gaussian, lighting


OUTPUT = Path(__file__).resolve().parents[1] / 'Characters' / 'Gopal'
SILT_MASK = 'Dry silt coverage'
EXPORT_COLOR = 'Skin and river sediment'
SILT_COLOR = (.258, .193, .125)


class GopalHero(AdultHero):
    display_name = 'Gopal'
    appearance = dict(name='GopalHero', skin=(.402, .205, .113), hair=(.041, .025, .016),
                      iris=(.085, .048, .024))
    description = 'गोपाल, नाविक। Chapter 1 boatman and witness.'

    def __init__(self, source):
        super().__init__(source)
        self.rig.scale = (1.78 / 1.84,) * 3
        self.rig['Identity'] = 'गोपाल, नाविक'
        self.rig['Face reference'] = 'Gopal in Blender/Previews/Cast_Detail.png'

    def sculpt_anatomy(self, body):
        for vertex in body.data.vertices:
            x, y, z = vertex.co
            side = abs(x)
            jaw = gaussian(z, 1.619, .031) * gaussian(side, .061, .029)
            cheek = gaussian(z, 1.675, .021) * gaussian(side, .064, .024) * gaussian(y, -.112, .054)
            chin = gaussian(z, 1.605, .014) * gaussian(x, 0, .034) * gaussian(y, -.126, .042)
            # The older reference has a softly squared jaw and a broad, low nose.
            vertex.co.x += x * (.16 * jaw + .085 * cheek)
            vertex.co.y -= .0048 * cheek + .0030 * chin
            vertex.co.z -= .0020 * chin
            wing = gaussian(z, 1.674, .010) * gaussian(side, .018, .011) * gaussian(y, -.163, .024)
            bridge = gaussian(z, 1.695, .022) * gaussian(x, 0, .014) * gaussian(y, -.160, .025)
            vertex.co.x += math.copysign(.0028 * wing, x)
            vertex.co.y += .0037 * bridge

    def add_weathering(self):
        body = self.skin_mesh.data
        pigments = body.color_attributes['Skin pigment']
        mask = body.color_attributes.new(name=SILT_MASK, type='FLOAT_COLOR', domain='POINT')
        export = body.color_attributes.new(name=EXPORT_COLOR, type='FLOAT_COLOR', domain='POINT')
        covered = 0
        for vertex, source, coverage, color in zip(body.vertices, pigments.data, mask.data, export.data):
            x, y, z = vertex.co
            warm = gaussian(z, 1.685, .023) * gaussian(abs(x), .062, .022) * gaussian(y, -.116, .041)
            skin = tuple(component * (1 - warm * .045) + delta * warm
                         for component, delta in zip(source.color[:3], (.022, .005, -.002)))
            source.color = (*skin, 1)
            wetline = 0
            if z < .23 and abs(x) > .095:
                # Both feet retain sediment at the toes and heel. Uneven wetting leaves islands at the ankles.
                noise, grit, _ = noise_vector(Vector((x * 60, y * 56, z * 53)), noise_basis='PERLIN_ORIGINAL')
                crest = (.132 if x < 0 else .104) + .032 * noise + .035 * math.sin(y * 39 + x * 16)
                sole = min(1, max(0, (z - .002) / .017))
                taper = min(1, max(0, .5 + (crest - z) / .049))
                islands = min(1, max(0, (z - .035) / .084))
                wetline = sole * taper * (.95 - .31 * islands + .18 * grit * islands)
                covered += wetline > .35
            coverage.color = (wetline, wetline, wetline, 1)
            color.color = tuple(a + (b - a) * wetline for a, b in zip(skin, SILT_COLOR)) + (1,)

        clean = self.m['skin']
        silt = clean.copy()
        silt.name = 'GopalHero • Skin with dry river silt'
        add_silt_shader(silt)
        body.materials.append(silt)
        foot_slot = len(body.materials) - 1
        for face in body.polygons:
            if all(body.vertices[index].co.z < .24 for index in face.vertices):
                face.material_index = foot_slot
        body.color_attributes.active_color = export
        body.color_attributes.render_color_index = list(body.color_attributes).index(export)
        if covered < 30:
            raise RuntimeError('The dry silt mask did not cover both feet')
        self.skin_mesh['Sediment'] = 'Swap foot material to GopalHero • Skin for a clean-foot variant.'
        return foot_slot


def add_silt_shader(material):
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = nodes.get('Principled BSDF')
    shader.location = (580, 300)
    nodes.get('Material Output').location = (870, 300)
    inputs = shader.inputs
    skin_color = inputs['Base Color'].links[0].from_socket
    skin_roughness = inputs['Roughness'].links[0].from_socket
    skin_normal = inputs['Normal'].links[0].from_socket
    rest = next(node for node in nodes if node.type == 'ATTRIBUTE').outputs['Vector']

    mask = nodes.new('ShaderNodeVertexColor')
    mask.layer_name = SILT_MASK
    mask.location = (-820, -730)
    powder = nodes.new('ShaderNodeTexNoise')
    powder.label = 'Fine dry sediment grains'
    powder.location = (-810, -450)
    powder.inputs['Scale'].default_value = 530
    powder.inputs['Detail'].default_value = 2.6
    links.new(rest, powder.inputs['Vector'])
    tint = nodes.new('ShaderNodeValToRGB')
    tint.location = (-550, -445)
    tint.color_ramp.elements[0].position = .24
    tint.color_ramp.elements[0].color = (.142, .100, .065, 1)
    tint.color_ramp.elements[1].position = .75
    tint.color_ramp.elements[1].color = (.471, .385, .248, 1)
    links.new(powder.outputs['Fac'], tint.inputs['Fac'])

    cracks = nodes.new('ShaderNodeTexVoronoi')
    cracks.label = 'Drying seams in compacted silt'
    cracks.feature = 'DISTANCE_TO_EDGE'
    cracks.location = (-820, -980)
    cracks.inputs['Scale'].default_value = 225
    links.new(rest, cracks.inputs['Vector'])
    crust = nodes.new('ShaderNodeMapRange')
    crust.location = (-550, -970)
    crust.inputs['From Max'].default_value = .086
    crust.inputs['To Min'].default_value = .09
    links.new(cracks.outputs['Distance'], crust.inputs['Value'])
    bump = nodes.new('ShaderNodeBump')
    bump.label = 'Dry crust normal over skin pores'
    bump.location = (270, -490)
    bump.inputs['Distance'].default_value = .0013
    links.new(mask.outputs['Color'], bump.inputs['Strength'])
    links.new(crust.outputs['Result'], bump.inputs['Height'])
    links.new(skin_normal, bump.inputs['Normal'])
    links.new(bump.outputs['Normal'], inputs['Normal'])

    def layer(label, y, underlying, surface, target):
        mix = nodes.new('ShaderNodeMixRGB')
        mix.label = label
        mix.location = (268, y)
        links.new(mask.outputs['Color'], mix.inputs[0])
        links.new(underlying, mix.inputs[1])
        if isinstance(surface, tuple):
            mix.inputs[2].default_value = surface
        else:
            links.new(surface, mix.inputs[2])
        links.new(mix.outputs['Color'], inputs[target])

    layer('Pigment through the broken silt edge', 280, skin_color, tint.outputs['Color'], 'Base Color')
    layer('Dry silt reflects as a matte surface', 20, skin_roughness, (.95, .95, .95, 1), 'Roughness')
    scatter = nodes.new('ShaderNodeMath')
    scatter.operation = 'MULTIPLY_ADD'
    scatter.location = (270, -245)
    scatter.inputs[1].default_value = -.083
    scatter.inputs[2].default_value = .10
    links.new(mask.outputs['Color'], scatter.inputs[0])
    links.new(scatter.outputs[0], inputs['Subsurface Weight'])


def review_floor():
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.002))
    obj = bpy.context.object
    obj.name = 'Studio floor'
    obj.data.materials.append(studio_material('Neutral charcoal stone', (.054, .057, .057), .93))


def portrait(scene, hero):
    bpy.context.window.scene = scene
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene.name = 'Gopal | Portrait'
    setup_stage(scene, 870, 1020, 32, .22)
    review_floor()
    stage_camera(scene, 'Portrait camera', (-.55, -4.3, 1.64), (0, -.018, 1.44), .72)
    lighting(scene, False)
    rig = copy_model(scene, hero, 'Gopal portrait', 0, 7)
    turn(rig, 'head', (0, 0, 1), -10)
    turn(rig, 'neck', (1, 0, 0), 2)
    scene.render.filepath = '//Gopal_Portrait.png'
    return scene


def soil_comparison(hero, foot_slot):
    scene = bpy.data.scenes.new('Gopal | Dry silt comparison')
    setup_stage(scene, 1080, 570, 32, .25)
    review_floor()
    stage_camera(scene, 'Foot and ankle camera', (0, -3.1, 1.31), (0, -.06, .145), 1.40)
    light(scene, 'Low raking key', (-1.6, -1.3, .9), (0, -.062, .095), (1, .92, .80), 177, .65)
    light(scene, 'Soft fill', (1.6, -1.4, 1.15), (0, -.042, .13), (.73, .83, 1), 132, 1.1)
    clean = copy_model(scene, hero, 'Clean-foot material comparison', -.34, -11)
    copy_model(scene, hero, 'Dry silt on both feet', .34, -11)
    skin = next(obj for obj in clean.children if obj.data == hero.skin_mesh.data)
    skin.material_slots[foot_slot].link = 'OBJECT'
    skin.material_slots[foot_slot].material = hero.m['skin']
    scene.render.filepath = '//Gopal_Dry_Silt.png'
    return scene


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--no-render', action='store_true', help='Save the model and scenes without rendering')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    from gopal_hero_costume import covered_skin, dress
    from gopal_hero_groom import dress_head
    from gopal_hero_poses import make_story_scenes

    preview = bpy.context.scene
    hero = GopalHero(args.base)
    dress(hero)
    dress_head(hero)
    covered_skin(hero)
    foot_slot = hero.add_weathering()
    hero.validate()
    print(f'GOPAL MODEL PASS: {len(hero.rig.data.bones)} bones, {len(hero.parts)} skinned meshes, '
          f'{len(hero.skin_mesh.data.vertices)} dressed skin vertices', flush=True)

    args.output.mkdir(parents=True, exist_ok=True)
    export_fbx(hero, args.output / 'Gopal_Hero.fbx', prioritize_active_color=True)
    scenes = [portrait(preview, hero), soil_comparison(hero, foot_slot)]
    scenes.extend(make_story_scenes(hero, args.output))
    bpy.context.window.scene = preview
    bpy.ops.object.select_all(action='DESELECT')
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                viewer = area.spaces.active
                viewer.overlay.show_overlays = False
                viewer.shading.color_type = 'MATERIAL'
                viewer.region_3d.view_perspective = 'CAMERA'
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output / 'Gopal_Hero.blend'), compress=True)
    if not args.no_render:
        for scene in scenes:
            bpy.context.window.scene = scene
            bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    main()
