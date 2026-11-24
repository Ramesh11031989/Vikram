"""Node-material helpers and weathered plaster for the town set (Blender 5.2)."""

import ghat_kit as k


def base(name, color, rough):
    surface = k.material(name, color, rough)
    tree = surface.node_tree
    return surface, tree.nodes, tree.links, tree.nodes.get('Principled BSDF')


def coords(nodes, links, seed=0., scale=(1, 1, 1), world=True):
    """(raw coordinates, offset and scaled coordinates).

    World position varies from house to house and gives world height above the ground;
    object coordinates (world=False) stay glued to a moving object such as a cow."""
    mapping = nodes.new('ShaderNodeMapping')
    mapping.inputs['Location'].default_value = (seed, seed * .7, seed * 1.3)
    mapping.inputs['Scale'].default_value = scale
    if world:
        raw = nodes.new('ShaderNodeNewGeometry').outputs['Position']
    else:
        raw = nodes.new('ShaderNodeTexCoord').outputs['Object']
    links.new(raw, mapping.inputs['Vector'])
    return raw, mapping.outputs['Vector']


def noise(nodes, links, vector, scale, detail=6, rough=.55):
    item = nodes.new('ShaderNodeTexNoise')
    item.inputs['Scale'].default_value = scale
    item.inputs['Detail'].default_value = detail
    item.inputs['Roughness'].default_value = rough
    links.new(vector, item.inputs['Vector'])
    return item.outputs['Fac']


def calc(nodes, links, operation, a, b=None, clamp=False):
    item = nodes.new('ShaderNodeMath')
    item.operation, item.use_clamp = operation, clamp
    for index, value in enumerate((a, b)):
        if value is None:
            continue
        if isinstance(value, (int, float)):
            item.inputs[index].default_value = value
        else:
            links.new(value, item.inputs[index])
    return item.outputs[0]


def ramp(nodes, links, fac, stops):
    item = nodes.new('ShaderNodeValToRGB')
    elements = item.color_ramp.elements
    elements[0].position, elements[0].color = stops[0]
    elements[1].position, elements[1].color = stops[1]
    for position, color in stops[2:]:
        elements.new(position).color = color
    links.new(fac, item.inputs['Fac'])
    return item.outputs['Color']


def mix(nodes, links, fac, a, b, blend='MIX'):
    item = nodes.new('ShaderNodeMix')
    item.data_type, item.blend_type = 'RGBA', blend
    for socket, value in (('Factor', fac), ('A', a), ('B', b)):
        if isinstance(value, (int, float)):
            item.inputs[socket].default_value = value
        elif isinstance(value, tuple):
            item.inputs[socket].default_value = (*value, 1)
        else:
            links.new(value, item.inputs[socket])
    return item.outputs['Result']


def bump(nodes, links, shader, height, strength, distance):
    item = nodes.new('ShaderNodeBump')
    item.inputs['Strength'].default_value = strength
    item.inputs['Distance'].default_value = distance
    links.new(height, item.inputs['Height'])
    links.new(item.outputs['Normal'], shader.inputs['Normal'])


def plaster(name, color, substrate, seed=0., damage=.5, scale=1.7):
    """Plaster with broken patches (worst near the ground) showing the substrate, rain streaks and grain."""
    surface, n, l, shader = base(name, color, .93)
    raw, vec = coords(n, l, seed)
    split = n.new('ShaderNodeSeparateXYZ')
    l.new(raw, split.inputs[0])
    rise = calc(n, l, 'ADD', calc(n, l, 'MULTIPLY', split.outputs['Z'], -.22), .32, clamp=True)
    total = calc(n, l, 'ADD', noise(n, l, vec, scale, 9, .62), rise)
    cut = .64 - .07 * damage
    mask = ramp(n, l, total, [(cut, (0, 0, 0, 1)), (cut + .035, (1, 1, 1, 1))])
    stretch = n.new('ShaderNodeMapping')
    stretch.inputs['Scale'].default_value = (7, 7, .9)
    l.new(vec, stretch.inputs['Vector'])
    streak = ramp(n, l, noise(n, l, stretch.outputs['Vector'], 1., 4, .5),
                  [(.40, (1, 1, 1, 1)), (.72, (.60, .58, .55, 1))])
    tinted = mix(n, l, 1., color, streak, 'MULTIPLY')
    l.new(mix(n, l, mask, tinted, substrate), shader.inputs['Base Color'])
    height = calc(n, l, 'ADD', noise(n, l, vec, 38, 5, .6), calc(n, l, 'MULTIPLY', mask, -.7))
    bump(n, l, shader, height, .55, .03)
    return surface
