"""Cloth appearance based on the rest mesh, so fibers follow the rig and cloth solver."""

import math

import bpy


REST_ATTRIBUTE = 'TextileRest'

LINEN = {
    'Undyed collar', 'Sand-coloured cotton trousers', 'Shadowed cotton folds',
    'Unbleached cotton', 'Faded ivory shawl', 'Flax woven edge', 'Woodsmoke tunic',
    'Earth gray sash', 'Faded river blue', 'Sun-bleached binding', 'Hemp trouser cloth',
    'Dark umber waist wrap', 'Cinnamon shoulder cloth', 'Oat thread',
    'Unbleached handloom kurta', 'Kurta patch cloth', 'Kurta dark patch cloth',
    'Faded ochre dhoti', 'Faded head wrap', 'Madder red gamchha',
}
FINE_WEAVE = {
    'Indigo handloom jacket', 'Dark indigo border', 'Kingfisher court sash', 'Muted green silk folds',
    'Deep teal turban cloth', 'Deep teal wrap seams', 'Teal wrap highlights',
}


def store_rest_positions(mesh):
    """Store the undeformed metric coordinates that drive the procedural weave."""
    attr = mesh.attributes.get(REST_ATTRIBUTE)
    if attr is None:
        attr = mesh.attributes.new(REST_ATTRIBUTE, 'FLOAT_VECTOR', 'POINT')
    attr.data.foreach_set('vector', [value for vertex in mesh.vertices for value in vertex.co])


def fabric_group():
    name = 'Textile • Dyed yarn and woven fibers'
    existing = bpy.data.node_groups.get(name)
    if existing:
        return existing
    tree = bpy.data.node_groups.new(name, 'ShaderNodeTree')
    settings = (('Dye', 'NodeSocketColor'), ('Thread pitch (mm)', 'NodeSocketFloat'),
                ('Yarn contrast', 'NodeSocketFloat'), ('Relief (mm)', 'NodeSocketFloat'))
    for label, kind in settings:
        tree.interface.new_socket(name=label, in_out='INPUT', socket_type=kind)
    for label, kind in (('Color', 'NodeSocketColor'), ('Normal', 'NodeSocketVector'),
                        ('Roughness', 'NodeSocketFloat')):
        tree.interface.new_socket(name=label, in_out='OUTPUT', socket_type=kind)

    nodes, links = tree.nodes, tree.links

    def node(kind, label, x, y):
        item = nodes.new(kind)
        item.label = label
        item.location = (x,y)
        return item

    def math_node(operation, label, x, y, a, b=0):
        item = node('ShaderNodeMath', label, x, y)
        item.operation = operation
        for index, value in enumerate((a,b)):
            if isinstance(value, (float,int)):
                item.inputs[index].default_value = value
            else:
                links.new(value, item.inputs[index])
        return item.outputs[0]

    inputs = node('NodeGroupInput', 'Fabric settings', -1220, 320).outputs
    source = node('ShaderNodeAttribute', 'Undeformed garment coordinates (m)', -1220, -30)
    source.attribute_name = REST_ATTRIBUTE
    coordinates = source.outputs['Vector']
    fibers = node('ShaderNodeSeparateXYZ', 'Warp / weft axes', -980, 20)
    links.new(coordinates, fibers.inputs[0])
    thread_frequency = math_node('DIVIDE', 'Radians per meter', -980, 330,
                                 math.pi * 1000, inputs['Thread pitch (mm)'])
    ridges = []
    for index, axis in enumerate('XYZ'):
        y = 310-index*230
        phase = math_node('MULTIPLY', f'{axis} yarn spacing', -760, y,
                          fibers.outputs[axis], thread_frequency)
        short_wave = math_node('SINE', 'Individual yarns', -560, y, phase)
        ridges.append(math_node('MULTIPLY', 'Yarn crest', -370, y, short_wave, short_wave))
    warp = math_node('MAXIMUM', 'Crossing warp and weft', -150, 305, ridges[0], ridges[2])
    weft = math_node('MULTIPLY', 'Overlapping yarn', -150, 80, ridges[1], .38)
    weave = math_node('ADD', 'Fabric height', 60, 305, warp, weft)
    dyed = node('ShaderNodeTexNoise', 'Uneven hand-dyed thread', -710, -500)
    dyed.inputs['Scale'].default_value = 22
    dyed.inputs['Detail'].default_value = 3.2
    links.new(coordinates, dyed.inputs['Vector'])
    yarn_value = math_node('MULTIPLY', 'Visible weave', 275, 290, warp, inputs['Yarn contrast'])
    mottling = math_node('MULTIPLY', 'Yarn dye variation', -155, -175, dyed.outputs['Fac'], .23)
    value = math_node('ADD', 'Thread and dye', 470, 290, yarn_value, mottling)
    value = math_node('ADD', 'Retain deep dye color', 660, 290, value, .74)
    color = node('ShaderNodeMixRGB', 'Apply yarn color', 870, 370)
    color.blend_type = 'MULTIPLY'
    color.inputs[0].default_value = 1
    links.new(inputs['Dye'], color.inputs[1])
    links.new(value, color.inputs[2])

    lint = node('ShaderNodeTexNoise', 'Short surface fibers', -500, -510)
    lint.inputs['Scale'].default_value = 1080
    lint.inputs['Detail'].default_value = 1.0
    links.new(coordinates, lint.inputs['Vector'])
    micro = math_node('MULTIPLY', 'Fiber height', -170, -478, lint.outputs['Fac'], .25)
    height = math_node('ADD', 'Weave + fibers', 270, 10, weave, micro)
    distance = math_node('MULTIPLY', 'Relief in meters', 470, -195, inputs['Relief (mm)'], .001)
    bump = node('ShaderNodeBump', 'Tactile microrelief', 860, 70)
    bump.inputs['Strength'].default_value = .64
    links.new(height, bump.inputs['Height'])
    links.new(distance, bump.inputs['Distance'])
    roughness = math_node('MULTIPLY_ADD', 'Yarn roughness', 650, -280, dyed.outputs['Fac'], .22)
    roughness.node.inputs[2].default_value = .62

    output = node('NodeGroupOutput', 'Textile surface', 1120, 280)
    links.new(color.outputs['Color'], output.inputs['Color'])
    links.new(bump.outputs['Normal'], output.inputs['Normal'])
    links.new(roughness, output.inputs['Roughness'])
    return tree


def finish_fabric(material, fine):
    tree = material.node_tree
    shader = tree.nodes.get('Principled BSDF')
    textile = tree.nodes.new('ShaderNodeGroup')
    textile.node_tree = fabric_group()
    textile.label = 'Twill / silk weave' if fine else 'Open cotton / linen weave'
    textile.location = (-300,150)
    textile.inputs['Dye'].default_value = shader.inputs['Base Color'].default_value
    textile.inputs['Thread pitch (mm)'].default_value = 3.0 if fine else 4.4
    textile.inputs['Yarn contrast'].default_value = .17 if fine else .28
    textile.inputs['Relief (mm)'].default_value = .11 if fine else .17
    shader.inputs['Specular IOR Level'].default_value = .29 if fine else .22
    shader.inputs['Sheen Weight'].default_value = .27 if fine else .38
    shader.inputs['Sheen Roughness'].default_value = .7
    shader.inputs['Sheen Tint'].default_value = (.48,.39,.30,1) if fine else (.51,.43,.35,1)
    for output, target in (('Color','Base Color'),('Normal','Normal'),('Roughness','Roughness')):
        tree.links.new(textile.outputs[output], shader.inputs[target])


def apply_textiles(character):
    fabrics = set()
    for part in character.parts:
        uses_fabric = False
        for material in part.data.materials:
            label = material.name.partition(' • ')[2]
            if label in LINEN or label in FINE_WEAVE:
                uses_fabric = True
                if material not in fabrics:
                    finish_fabric(material, fine=label in FINE_WEAVE)
                    fabrics.add(material)
        if uses_fabric:
            store_rest_positions(part.data)
