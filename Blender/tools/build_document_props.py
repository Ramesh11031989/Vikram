"""Build the evidence props: seven statements, arrival list, order (two states), death tally,
royal decree, oil-cloth bundle (tied / open / in hand) and the royal ledger.

Python3 first (Pillow, WSL ok):  python3 Blender/tools/document_textures.py
blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_document_props.py
"""

import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_cast import light, review_floor, setup_stage, stage_camera, studio_material
import document_props as D

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Props' / 'Documents'
BLEND = OUT / 'Documents.blend'
SHEETS = [f'statement_{n}' for n in range(1, 8)] + [
    'arrival_list', 'order_original', 'order_returned', 'death_tally', 'royal_decree']


def image_material(name, image_name, rough=.85):
    mat = bpy.data.materials.new(f'Doc \u2022 {name}')
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value = rough
    tex = nodes.new('ShaderNodeTexImage')
    path = D.TEX / f'{image_name}.png'
    if not path.exists():
        raise FileNotFoundError(f'{path} (run document_textures.py first)')
    tex.image = bpy.data.images.load(str(path))
    tex.image.colorspace_settings.name = 'sRGB'
    tex.image.pack()
    links.new(tex.outputs['Color'], shader.inputs['Base Color'])
    return mat


def link(collection, obj):
    collection.objects.link(obj)
    return obj


def make_sheets(coll):
    """Every sheet is a copy of ONE generated paper mesh (same UVs and shape keys);
    each copy owns its key values, so page 7 can be folded without touching page 1."""
    template = D.paper_mesh('Paper')
    probe = bpy.data.objects.new('probe', template)
    bpy.context.scene.collection.objects.link(probe)
    D.add_fold_keys(probe)
    bpy.data.objects.remove(probe)
    sheets = {}
    for i, name in enumerate(SHEETS):
        mesh = template.copy()
        mesh.name = f'Paper \u2022 {name}'
        obj = link(coll, bpy.data.objects.new(f'DOC \u2022 {name}', mesh))
        mesh.materials.append(image_material(name, name))
        obj.location = ((i % 6 - 2.5)*.30, -(i // 6)*.40, 0)
        sheets[name] = obj
    bpy.data.meshes.remove(template)
    return sheets


def set_keys(obj, **values):
    for key, value in values.items():
        obj.data.shape_keys.key_blocks[key].value = value


def cloth_material():
    mat = studio_material('Doc \u2022 Oil cloth', (.43, .33, .20), .45)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = nodes.get('Principled BSDF')
    noise = nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 5
    ramp = nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (.20, .13, .06, 1)
    ramp.color_ramp.elements[1].color = (.50, .40, .26, 1)
    links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
    links.new(ramp.outputs['Color'], shader.inputs['Base Color'])
    return mat


def make_bundles(coll, material):
    out = {}
    template = D.cloth_mesh('Cloth')
    probe = bpy.data.objects.new('probe', template)
    bpy.context.scene.collection.objects.link(probe)
    D.add_bundle_keys(probe)
    bpy.data.objects.remove(probe)
    for i, (label, key) in enumerate((('tied', 'Tied'), ('open', None), ('in_hand', 'In_Hand'))):
        mesh = template.copy()
        mesh.name = f'Cloth \u2022 {label}'
        mesh.materials.append(material)
        obj = link(coll, bpy.data.objects.new(f'DOC \u2022 potli_{label}', mesh))
        obj.location = (-.8 + i*.8, -1.6, 0)
        if key:
            set_keys(obj, **{key: 1.0})
        for poly in mesh.polygons:
            poly.use_smooth = True
        out[label] = obj
    bpy.data.meshes.remove(template)
    return out


def make_ledger(coll, scene):
    cover = studio_material('Doc \u2022 Ledger cloth', (.30, .06, .05), .7)
    brass = studio_material('Doc \u2022 Ledger brass', (.62, .46, .16), .35, 1)
    page = image_material('ledger_leaf', 'ledger_leaf')
    W, H, T = D.LEDGER_W, D.LEDGER_H, D.LEDGER_T
    base = Vector((.8, -1.6, 0))
    parts = [('back', (W, H, .006), (0, 0, .003), cover), ('front', (W, H, .006), (0, 0, T+.009), cover),
             ('spine', (.012, H, T+.012), (-W/2, 0, (T+.012)/2), cover),
             ('page block', (W-.012, H-.01, T), (.004, 0, .006+T/2), page)]
    for name in ('NE', 'NW', 'SE'):
        parts.append((f'brass corner {name}', (.03, .03, T+.016),
                      ((W/2-.015) * (1 if 'E' in name else -1), (H/2-.015) * (1 if 'N' in name else -1),
                       (T+.016)/2), brass))
    ledger = []
    for name, size, loc, mat in parts:
        obj = link(coll, D.box(f'DOC \u2022 ledger {name}', size, Vector(loc)+base, mat))
        ledger.append(obj)
    # torn pages: ragged stubs along the spine mark where the leaves were cut out
    for k in range(D.TORN_COUNT):
        z = .012 + k*.006
        stub = D.box(f'DOC \u2022 ledger torn stub {k+1}', (.022 + .004*(k % 3), H-.02, .0012),
                     (-W/2+.02 + .002*k, 0, z), page)
        stub.location += base
        link(coll, stub)
    return ledger


def validate(sheets, bundles):
    problems = []
    for name, obj in sheets.items():
        keys = {k.name for k in obj.data.shape_keys.key_blocks}
        if not {'Fold_Half', 'Fold_Third', 'Corner_Curl'} <= keys:
            problems.append(f'{name}: missing fold keys')
        if len(obj.data.uv_layers) != 1 or not obj.data.materials[0].node_tree.nodes.get('Image Texture'):
            problems.append(f'{name}: no texture')
    # the folded sheet must fit the tied pouch (inner diameter 2*BAG_R, wall height BAG_H)
    sheet = sheets['statement_7']
    key = sheet.data.shape_keys.key_blocks['Fold_Third']
    xs = [v.co.x for v in key.data]; ys = [v.co.y for v in key.data]; zs = [v.co.z for v in key.data]
    fw, fh = max(xs)-min(xs), max(ys)-min(ys)
    if fw > 2*D.BAG_R*.96 or fh > D.BAG_H*.98:
        problems.append(f'folded sheet {fw:.3f}x{fh:.3f} m does not fit the pouch')
    for n in (1, 7):
        a = sheets[f'statement_{n}']
        if a.dimensions.x < .2:
            problems.append(f'page {n} too small to read')
    tied = bundles['tied']
    top = max(v.co.z for v in tied.data.shape_keys.key_blocks['Tied'].data)
    if top < D.BAG_H:
        problems.append('pouch is too short for the papers')
    if problems:
        raise RuntimeError('; '.join(problems))
    print(f'folded statement {fw:.3f} x {fh:.3f} m fits pouch {2*D.BAG_R:.2f} x {D.BAG_H:.2f} m', flush=True)


def show_states(sheets):
    """Page 7 is shown in its folded state; the rest lie flat. Order and decree sit side by side."""
    set_keys(sheets['statement_7'], Fold_Third=1.0)
    set_keys(sheets['statement_1'], Corner_Curl=.35)


def camera_shot(scene, name, location, target, width):
    cam = stage_camera(scene, name, location, target, width)
    return cam


def render(scene, camera_name, path):
    scene.camera = bpy.data.objects[camera_name]
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def export_fbx(coll, path):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in coll.objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = coll.objects[0]
    result = bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={'MESH'},
        axis_forward='-Z', axis_up='Y', apply_scale_options='FBX_SCALE_UNITS',
        use_mesh_modifiers=False, bake_anim=False, mesh_smooth_type='FACE', path_mode='COPY',
        embed_textures=True)
    if 'FINISHED' not in result or path.stat().st_size < 1024:
        raise RuntimeError(f'FBX export failed: {path}')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.name = 'Documents'
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj)
    coll = bpy.data.collections.new('PROPS_Documents')
    scene.collection.children.link(coll)
    coll.asset_mark()
    coll.asset_data.description = 'Evidence papers, oil-cloth bundle and royal ledger | metres'
    sheets = make_sheets(coll)
    bundles = make_bundles(coll, cloth_material())
    make_ledger(coll, scene)
    show_states(sheets)
    validate(sheets, bundles)
    setup_stage(scene, 1600, 1100, 32, .5)
    review_floor((.12, .10, .08))
    light(scene, 'Key', (-1.5, -3.0, 3.0), (0, -.8, 0), (1, .88, .74), 260, 2.0)
    light(scene, 'Fill', (2.0, -2.0, 2.0), (0, -.8, 0), (.7, .8, 1), 90, 2.4)
    # top-down camera over everything
    camera_shot(scene, 'Overview', (0, -.55, 4), (0, -.55, 0), 3.0)
    # close-up of pages 1 and 7 side by side (statements)
    sheets['statement_1'].location = (-.14, 1.3, 0)
    sheets['statement_7'].location = (.14, 1.3, 0)
    camera_shot(scene, 'Pages 1 and 7', (0, 1.3, 1.2), (0, 1.3, 0), .62)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    export_fbx(coll, OUT / 'PROPS_Documents.fbx')
    render(scene, 'Overview', OUT / 'Documents_Overview.png')
    render(scene, 'Pages 1 and 7', OUT / 'Documents_Pages_1_and_7.png')
    print(f'{len(sheets)} sheets, 3 bundle states, ledger -> {BLEND}', flush=True)


main()
