"""Procedural materials, sky and grading for the town set (art passes).

`upgrade(m)` swaps the flat-colour town materials for detailed node materials and adds the cow
coat-patch materials.  `sky(scene)` builds the sky and grading.  Blender 5.2 safe: no use_nodes.
"""

import math

import bpy

import ghat_kit as k
import town_surface as S


def _scaled(color, f):
    return tuple(min(1., c * f) for c in color)


def thatch(name, color):
    """Straw: stretched fibre noise, tier banding with darker gaps, sun-bleached tips."""
    surface, n, l, shader = S.base(name, color, .96)
    raw, vec = S.coords(n, l, scale=(26, 11, 11))
    z = n.new('ShaderNodeSeparateXYZ')
    l.new(raw, z.inputs[0])
    tier = S.calc(n, l, 'SINE', S.calc(n, l, 'MULTIPLY', z.outputs['Z'], 15.))
    tier = S.calc(n, l, 'ADD', S.calc(n, l, 'MULTIPLY', tier, .22), .5)
    fibre = S.noise(n, l, vec, 3.2, 8, .65)
    value = S.calc(n, l, 'MULTIPLY', S.calc(n, l, 'ADD', fibre, S.noise(n, l, vec, 18, 4, .5)), .5)
    value = S.calc(n, l, 'MULTIPLY', value, tier)
    l.new(S.ramp(n, l, value, [(.12, (*_scaled(color, .28), 1)), (.62, (*color, 1)),
                               (.95, (*_scaled(color, 1.75), 1))]), shader.inputs['Base Color'])
    S.bump(n, l, shader, fibre, .9, .02)
    return surface


def tile(name, color):
    """Clay tiles: per-tile tint (Voronoi cell colour), soot, and green moss in damp low spots."""
    surface, n, l, shader = S.base(name, color, .62)
    raw, vec = S.coords(n, l, scale=(1, 1, 1))
    cell = n.new('ShaderNodeTexVoronoi')
    cell.feature, cell.inputs['Scale'].default_value = 'F1', 6.5
    l.new(vec, cell.inputs['Vector'])
    split = n.new('ShaderNodeSeparateColor')
    l.new(cell.outputs['Color'], split.inputs['Color'])
    per_tile = S.ramp(n, l, split.outputs['Red'], [(0., (*_scaled(color, .55), 1)), (1., (*_scaled(color, 1.35), 1))])
    soot = S.ramp(n, l, S.noise(n, l, vec, 2.1, 7), [(.3, (1, 1, 1, 1)), (.75, (.38, .36, .34, 1))])
    tinted = S.mix(n, l, 1., per_tile, soot, 'MULTIPLY')
    moss = S.ramp(n, l, S.noise(n, l, vec, 3.7, 6), [(.60, (0, 0, 0, 1)), (.72, (1, 1, 1, 1))])
    l.new(S.mix(n, l, S.calc(n, l, 'MULTIPLY', moss, .8), tinted, (.07, .13, .04)), shader.inputs['Base Color'])
    S.bump(n, l, shader, split.outputs['Red'], .45, .015)
    return surface


def wood(name, color, aged=1.):
    """Seasoned timber: warped grain bands, cracks, and grey weathering."""
    surface, n, l, shader = S.base(name, color, .78)
    raw, vec = S.coords(n, l, scale=(1.6, 1.6, 1.6))
    grain = n.new('ShaderNodeTexWave')
    grain.wave_type, grain.bands_direction = 'BANDS', 'DIAGONAL'
    grain.inputs['Scale'].default_value = 16
    grain.inputs['Distortion'].default_value = 5
    grain.inputs['Detail'].default_value = 3
    l.new(vec, grain.inputs['Vector'])
    base = S.ramp(n, l, grain.outputs['Fac'], [(.2, (*_scaled(color, .45), 1)), (.8, (*_scaled(color, 1.25), 1))])
    grey = S.ramp(n, l, S.noise(n, l, vec, 4, 5), [(.45, (0, 0, 0, 1)), (.8, (1, 1, 1, 1))])
    base = S.mix(n, l, S.calc(n, l, 'MULTIPLY', grey, .45 * aged), base, (.34, .31, .28))
    l.new(base, shader.inputs['Base Color'])
    S.bump(n, l, shader, grain.outputs['Fac'], .5, .01)
    return surface


def hide(name, ground, patch, seed, patchy=.5):
    """Cow hide: short-hair grain, mottled patches, and a darker dirty belly and legs (object space)."""
    surface, n, l, shader = S.base(name, ground, .62)
    raw, vec = S.coords(n, l, seed, world=False)
    z = n.new('ShaderNodeSeparateXYZ')
    l.new(raw, z.inputs[0])
    spots = S.ramp(n, l, S.noise(n, l, vec, 2.6, 4, .5), [(.5 - .12 * patchy, (0, 0, 0, 1)), (.52 - .12 * patchy, (1, 1, 1, 1))])
    coat = S.mix(n, l, spots, ground, patch)
    low = S.ramp(n, l, z.outputs['Z'], [(.15, (1, 1, 1, 1)), (.85, (0, 0, 0, 1))])
    dirty = S.mix(n, l, S.calc(n, l, 'MULTIPLY', low, .55), coat, (.16, .12, .09))
    l.new(S.mix(n, l, S.noise(n, l, vec, 60, 3), dirty, _scaled(ground, .8)), shader.inputs['Base Color'])
    S.bump(n, l, shader, S.noise(n, l, vec, 260, 2, .7), .25, .002)
    return surface


def upgrade(m):
    """Replace flat town materials in `m` with detailed node materials (names unchanged where reused)."""
    m['thatch'] = thatch('Town | thatch', (.46, .34, .15))
    m['tile'] = tile('Town | clay tile', (.50, .20, .10))
    m['wood'] = wood('Town | seasoned wood', (.28, .165, .08))
    m['wood_dark'] = wood('Town | dark batten', (.12, .07, .04), .6)
    m['earth'] = earth('Town | trodden earth', (.30, .225, .145), .55)
    m['lane'] = earth('Town | lane earth', (.38, .30, .20), .35, 4.)
    m['lime'] = S.plaster('Town | lime-washed plaster', (.74, .70, .62), (.40, .30, .21), 1.0, .6)
    m['ochre'] = S.plaster('Town | ochre plaster', (.66, .46, .22), (.35, .24, .14), 2.3, .7)
    m['mud'] = S.plaster('Town | mud wall', (.36, .25, .15), (.26, .18, .11), 3.7, .35)
    m['cow_a'] = hide('Town | cow, white', (.80, .76, .68), (.52, .44, .34), 1.0, .35)
    m['cow_b'] = hide('Town | cow, brown', (.42, .22, .10), (.62, .50, .38), 4.0, .55)
    return m


def sky(scene):
    """Gradient sky with a warm horizon, a light haze and gentle grading."""
    world = scene.world
    tree = world.node_tree
    n, l = tree.nodes, tree.links
    background = n.get('Background')
    coord = n.new('ShaderNodeTexCoord')
    split = n.new('ShaderNodeSeparateXYZ')
    l.new(coord.outputs['Generated'], split.inputs[0])
    gradient = S.ramp(n, l, split.outputs['Z'], [(.38, (.78, .70, .58, 1)), (.52, (.50, .62, .80, 1)),
                                                (.9, (.20, .38, .72, 1))])
    l.new(gradient, background.inputs['Color'])
    background.inputs['Strength'].default_value = 1.15
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = -.2
    scene.cycles.use_denoising = True



def earth(name, color, pebbles=.5, scale=2.5):
    """Trodden earth: dry-crack mottling, scattered grey pebbles, darker damp hollows."""
    surface, n, l, shader = S.base(name, color, .98)
    raw, vec = S.coords(n, l, scale=(1, 1, 1))
    mottle = S.ramp(n, l, S.noise(n, l, vec, scale, 8, .6), [(.25, (*_scaled(color, .62), 1)), (.75, (*_scaled(color, 1.32), 1))])
    cell = n.new('ShaderNodeTexVoronoi')
    cell.feature, cell.inputs['Scale'].default_value = 'F1', 26
    l.new(vec, cell.inputs['Vector'])
    stones = S.ramp(n, l, cell.outputs['Distance'], [(.0, (1, 1, 1, 1)), (.22, (0, 0, 0, 1))])
    keep = S.ramp(n, l, S.noise(n, l, vec, .6, 2), [(.5, (0, 0, 0, 1)), (.62, (pebbles, pebbles, pebbles, 1))])
    bw = n.new('ShaderNodeRGBToBW')
    l.new(stones, bw.inputs['Color'])
    keep_bw = n.new('ShaderNodeRGBToBW')
    l.new(keep, keep_bw.inputs['Color'])
    mask = S.calc(n, l, 'MULTIPLY', bw.outputs[0], keep_bw.outputs[0])
    l.new(S.mix(n, l, mask, mottle, (.30, .28, .25)), shader.inputs['Base Color'])
    S.bump(n, l, shader, S.calc(n, l, 'ADD', S.noise(n, l, vec, 12, 6), S.calc(n, l, 'MULTIPLY', mask, .6)), .6, .05)
    return surface
