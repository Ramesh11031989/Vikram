"""Procedural surface library for the Chapter 1 sets.

All materials are node-based and resolution independent, so the set files stay
small in plain git. Wall paint and floor slabs use object-space coordinates; set
objects keep their origin at the set's local origin so painted bands line up
from room to room.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import bpy


RGB = tuple[float, float, float]
Socket = bpy.types.NodeSocket


class Graph:
    """Small helper around a material node tree."""

    def __init__(self, material: bpy.types.Material) -> None:
        self.tree = material.node_tree
        self.nodes = self.tree.nodes
        self.links = self.tree.links
        self.nodes.clear()
        self.output = self.node('ShaderNodeOutputMaterial', 900, 0)
        self.shader = self.node('ShaderNodeBsdfPrincipled', 600, 0)
        self.link(self.shader.outputs['BSDF'], self.output.inputs['Surface'])

    def node(self, kind: str, x: float = 0, y: float = 0, **values: float) -> bpy.types.Node:
        item = self.nodes.new(kind)
        item.location = (x, y)
        for key, value in values.items():
            setattr(item, key, value)
        return item

    def link(self, a: Socket, b: Socket) -> None:
        self.links.new(a, b)

    def set(self, socket: Socket, value: float | RGB | Socket) -> None:
        if isinstance(value, bpy.types.NodeSocket):
            self.link(value, socket)
        elif isinstance(value, tuple) and len(value) == 3 and socket.type == 'RGBA':
            socket.default_value = (*value, 1.0)
        else:
            socket.default_value = value

    def math(self, op: str, a: float | Socket, b: float | Socket = 0.0, clamp: bool = False) -> Socket:
        item = self.node('ShaderNodeMath')
        item.operation = op
        item.use_clamp = clamp
        self.set(item.inputs[0], a)
        self.set(item.inputs[1], b)
        return item.outputs[0]

    def mix(self, factor: float | Socket, a: RGB | Socket, b: RGB | Socket,
            blend: str = 'MIX') -> Socket:
        item = self.node('ShaderNodeMix')
        item.data_type = 'RGBA'
        item.blend_type = blend
        self.set(item.inputs['Factor'], factor)
        self.set(item.inputs[6], a)
        self.set(item.inputs[7], b)
        return item.outputs[2]

    def mixf(self, factor: float | Socket, a: float | Socket, b: float | Socket) -> Socket:
        item = self.node('ShaderNodeMix')
        item.data_type = 'FLOAT'
        self.set(item.inputs['Factor'], factor)
        self.set(item.inputs[2], a)
        self.set(item.inputs[3], b)
        return item.outputs[0]

    def ramp(self, factor: Socket, stops: Iterable[tuple[float, RGB]]) -> Socket:
        item = self.node('ShaderNodeValToRGB')
        self.link(factor, item.inputs['Fac'])
        elements = item.color_ramp.elements
        stops = list(stops)
        elements[0].position, elements[0].color = stops[0][0], (*stops[0][1], 1)
        elements[1].position, elements[1].color = stops[-1][0], (*stops[-1][1], 1)
        for position, color in stops[1:-1]:
            element = elements.new(position)
            element.color = (*color, 1)
        return item.outputs['Color']

    def noise(self, vector: Socket | None, scale: float, detail: float = 4.0,
              roughness: float = 0.55, distortion: float = 0.0, dims: str = '3D') -> bpy.types.Node:
        item = self.node('ShaderNodeTexNoise')
        item.noise_dimensions = dims
        item.inputs['Scale'].default_value = scale
        item.inputs['Detail'].default_value = detail
        item.inputs['Roughness'].default_value = roughness
        item.inputs['Distortion'].default_value = distortion
        if vector is not None:
            self.link(vector, item.inputs['Vector'])
        return item

    def voronoi(self, vector: Socket | None, scale: float, feature: str = 'F1',
                randomness: float = 1.0) -> bpy.types.Node:
        item = self.node('ShaderNodeTexVoronoi')
        item.feature = feature
        item.inputs['Scale'].default_value = scale
        item.inputs['Randomness'].default_value = randomness
        if vector is not None:
            self.link(vector, item.inputs['Vector'])
        return item

    def coords(self, space: str = 'Object', randomize: float = 0.0) -> Socket:
        texcoord = self.node('ShaderNodeTexCoord', -1400, 0)
        socket = texcoord.outputs[space]
        if randomize:
            info = self.node('ShaderNodeObjectInfo', -1400, -250)
            offset = self.node('ShaderNodeVectorMath', -1200, -150)
            offset.operation = 'MULTIPLY_ADD'
            self.link(info.outputs['Random'], offset.inputs[0])
            offset.inputs[1].default_value = (randomize * 97.3, randomize * 41.1, randomize * 13.7)
            self.link(socket, offset.inputs[2])
            return offset.outputs[0]
        return socket

    def scale_vector(self, vector: Socket, scale: tuple[float, float, float]) -> Socket:
        item = self.node('ShaderNodeVectorMath')
        item.operation = 'MULTIPLY'
        self.link(vector, item.inputs[0])
        item.inputs[1].default_value = scale
        return item.outputs[0]

    def separate(self, vector: Socket) -> bpy.types.Node:
        item = self.node('ShaderNodeSeparateXYZ')
        self.link(vector, item.inputs[0])
        return item

    def bump(self, height: Socket, strength: float, distance: float,
             normal: Socket | None = None) -> Socket:
        item = self.node('ShaderNodeBump')
        item.inputs['Strength'].default_value = strength
        item.inputs['Distance'].default_value = distance
        self.link(height, item.inputs['Height'])
        if normal is not None:
            self.link(normal, item.inputs['Normal'])
        return item.outputs['Normal']

    def ao(self, distance: float, samples: int = 4) -> Socket:
        item = self.node('ShaderNodeAmbientOcclusion')
        item.samples = samples
        item.inputs['Distance'].default_value = distance
        return item.outputs['AO']

    def band(self, value: Socket, low: float, high: float, soft: float = 0.004) -> Socket:
        """1 inside [low, high] with soft edges, else 0."""
        a = self.math('MULTIPLY', self.math('SUBTRACT', value, low), 1.0 / soft, clamp=True)
        b = self.math('MULTIPLY', self.math('SUBTRACT', high, value), 1.0 / soft, clamp=True)
        return self.math('MULTIPLY', a, b)

    def finish(self, color: Socket | RGB, roughness: Socket | float,
               normal: Socket | None = None, metallic: float = 0.0) -> None:
        self.set(self.shader.inputs['Base Color'], color)
        self.set(self.shader.inputs['Roughness'], roughness)
        self.shader.inputs['Metallic'].default_value = metallic
        if normal is not None:
            self.link(normal, self.shader.inputs['Normal'])


def _new(name: str, preview: RGB) -> tuple[bpy.types.Material, Graph] | tuple[bpy.types.Material, None]:
    existing = bpy.data.materials.get(name)
    if existing is not None:
        return existing, None
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*preview, 1.0)
    material.use_nodes = True
    return material, Graph(material)


# ---------------------------------------------------------------------------
# Stone
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StoneLook:
    light: RGB
    mid: RGB
    dark: RGB
    stain: RGB
    grain: float = 1.0
    roughness: float = 0.86
    crevice: float = 0.45


SANDSTONE = StoneLook((0.62, 0.47, 0.32), (0.50, 0.36, 0.23), (0.34, 0.23, 0.14), (0.22, 0.16, 0.11))
RED_SANDSTONE = StoneLook((0.52, 0.30, 0.21), (0.42, 0.23, 0.16), (0.28, 0.15, 0.10), (0.17, 0.11, 0.08))
CARVED_SANDSTONE = StoneLook((0.66, 0.51, 0.35), (0.54, 0.40, 0.26), (0.36, 0.25, 0.16), (0.20, 0.15, 0.10),
                             grain=1.4, crevice=0.6)
GHAT_STONE = StoneLook((0.44, 0.40, 0.34), (0.34, 0.31, 0.26), (0.21, 0.19, 0.16), (0.14, 0.13, 0.10),
                       grain=1.2, roughness=0.8)
BASALT = StoneLook((0.13, 0.13, 0.12), (0.095, 0.092, 0.085), (0.06, 0.058, 0.054), (0.04, 0.04, 0.036),
                   grain=0.8, roughness=0.55, crevice=0.3)


def stone(name: str, look: StoneLook = SANDSTONE) -> bpy.types.Material:
    material, g = _new(name, look.mid)
    if g is None:
        return material
    co = g.coords('Object', randomize=1.0)
    broad = g.noise(co, 0.35 * look.grain, 5, 0.6)
    beds = g.noise(g.scale_vector(co, (0.6, 0.6, 5.5)), 0.9 * look.grain, 3, 0.5)
    tone = g.math('ADD', g.math('MULTIPLY', broad.outputs['Fac'], 0.75),
                  g.math('MULTIPLY', beds.outputs['Fac'], 0.35))
    base = g.ramp(g.math('SUBTRACT', tone, 0.12),
                  ((0.30, look.dark), (0.48, look.mid), (0.64, look.light), (0.82, look.mid)))
    speck = g.voronoi(co, 140 * look.grain)
    specks = g.math('LESS_THAN', speck.outputs['Distance'], 0.11)
    base = g.mix(g.math('MULTIPLY', specks, 0.35), base, look.dark)
    streak = g.noise(g.scale_vector(co, (3.0, 3.0, 0.22)), 1.6, 3, 0.5)
    streaks = g.math('POWER', g.math('MAXIMUM', g.math('SUBTRACT', streak.outputs['Fac'], 0.5), 0.0), 1.4)
    base = g.mix(g.math('MULTIPLY', streaks, 1.6, True), base, look.stain, 'MULTIPLY')
    occlusion = g.ao(0.35, 4)
    dirt = g.math('SUBTRACT', 1.0, occlusion)
    base = g.mix(g.math('MULTIPLY', dirt, look.crevice * 1.6, True), base, look.stain)
    fine = g.noise(co, 38 * look.grain, 8, 0.7)
    chips = g.voronoi(co, 9 * look.grain, 'DISTANCE_TO_EDGE')
    chip_mask = g.math('MINIMUM', g.math('MULTIPLY', chips.outputs['Distance'], 9.0), 1.0)
    height = g.math('ADD', g.math('MULTIPLY', fine.outputs['Fac'], 0.6), g.math('MULTIPLY', chip_mask, 0.4))
    normal = g.bump(height, 0.35, 0.004)
    roughness = g.math('ADD', look.roughness - 0.08, g.math('MULTIPLY', fine.outputs['Fac'], 0.16))
    g.finish(base, roughness, normal)
    return material


def wet_ghat_stone(name: str, water_level: float, flood_mark: float) -> bpy.types.Material:
    """Ghat stone that darkens just above the waterline and carries a silt stain.

    The `Water level` value node is keyed with the water object, so the wet band
    follows the river between the morning and evening states.
    """
    look = GHAT_STONE
    material, g = _new(name, look.mid)
    if g is None:
        return material
    co = g.coords('Object', randomize=1.0)
    broad = g.noise(co, 0.45, 5, 0.6)
    base = g.ramp(broad.outputs['Fac'], ((0.32, look.dark), (0.5, look.mid), (0.68, look.light)))
    occlusion = g.ao(0.3, 4)
    base = g.mix(g.math('MULTIPLY', g.math('SUBTRACT', 1.0, occlusion), 0.8, True), base, look.stain)
    position = g.node('ShaderNodeNewGeometry').outputs['Position']
    z = g.separate(position).outputs['Z']
    level = g.node('ShaderNodeValue')
    level.name = level.label = 'Water level'
    level.outputs[0].default_value = water_level
    wobble = g.noise(position, 0.9, 2).outputs['Fac']
    silt_line = g.math('ADD', flood_mark, g.math('MULTIPLY', g.math('SUBTRACT', wobble, 0.5), 0.12))
    silt = g.math('LESS_THAN', z, silt_line)
    silt_color = g.mix(g.math('MULTIPLY', wobble, 0.6), (0.33, 0.28, 0.20), (0.24, 0.20, 0.14))
    base = g.mix(g.math('MULTIPLY', silt, 0.55), base, silt_color)
    height_above = g.math('SUBTRACT', z, level.outputs[0])
    wet = g.math('SUBTRACT', 1.0, g.math('MULTIPLY', height_above, 4.0), True)
    wet = g.math('MULTIPLY', wet, g.math('GREATER_THAN', height_above, -0.6))
    base = g.mix(g.math('MULTIPLY', wet, 0.55), base, (0.05, 0.045, 0.035), 'MULTIPLY')
    fine = g.noise(co, 30, 8, 0.7)
    normal = g.bump(fine.outputs['Fac'], 0.3, 0.004)
    roughness = g.mixf(wet, 0.86, 0.18)
    g.finish(base, roughness, normal)
    return material


# ---------------------------------------------------------------------------
# Plaster and paint
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PaintScheme:
    field: RGB = (0.72, 0.62, 0.47)
    dado: RGB = (0.42, 0.13, 0.07)
    dado_line: RGB = (0.62, 0.44, 0.16)
    frieze: RGB = (0.36, 0.11, 0.06)
    motif: RGB = (0.70, 0.50, 0.20)
    motif_core: RGB = (0.10, 0.14, 0.22)
    floor_z: float = 0.6
    dado_height: float = 0.95
    frieze_low: float = 3.95
    frieze_high: float = 4.45
    motif_period: float = 0.5


def painted_plaster(name: str, scheme: PaintScheme = PaintScheme()) -> bpy.types.Material:
    """Lime plaster with an earth-red dado and a rosette frieze, aged and patchy."""
    material, g = _new(name, scheme.field)
    if g is None:
        return material
    co = g.coords('Object')
    parts = g.separate(co)
    z = parts.outputs['Z']
    run = g.math('ADD', parts.outputs['X'], parts.outputs['Y'])
    mottling = g.noise(co, 1.4, 6, 0.62)
    field = g.ramp(mottling.outputs['Fac'], ((0.3, tuple(c * 0.86 for c in scheme.field)),
                                             (0.55, scheme.field),
                                             (0.75, tuple(min(1.0, c * 1.06) for c in scheme.field))))
    dado_top = scheme.floor_z + scheme.dado_height
    dado = g.band(z, -100.0, dado_top)
    line = g.band(z, dado_top, dado_top + 0.045)
    field = g.mix(dado, field, scheme.dado)
    field = g.mix(line, field, scheme.dado_line)
    frieze = g.band(z, scheme.frieze_low, scheme.frieze_high)
    rims = g.math('ADD', g.band(z, scheme.frieze_low, scheme.frieze_low + 0.03),
                  g.band(z, scheme.frieze_high - 0.03, scheme.frieze_high))
    # Rosettes: one per period along the wall, eight petals each.
    period = scheme.motif_period
    centre_z = (scheme.frieze_low + scheme.frieze_high) * 0.5
    u = g.math('SUBTRACT', g.math('FRACT', g.math('DIVIDE', run, period)), 0.5)
    v = g.math('DIVIDE', g.math('SUBTRACT', z, centre_z), period)
    radius = g.math('SQRT', g.math('ADD', g.math('MULTIPLY', u, u), g.math('MULTIPLY', v, v)))
    angle = g.math('ARCTAN2', v, u)
    petals = g.math('ADD', 0.62, g.math('MULTIPLY', g.math('COSINE', g.math('MULTIPLY', angle, 8.0)), 0.38))
    flower = g.math('LESS_THAN', radius, g.math('MULTIPLY', petals, 0.36))
    core = g.math('LESS_THAN', radius, 0.11)
    paint = g.mix(flower, scheme.frieze, scheme.motif)
    paint = g.mix(core, paint, scheme.motif_core)
    paint = g.mix(rims, paint, scheme.dado_line)
    field = g.mix(frieze, field, paint)
    # Wear: patches where the paint has flaked to the plaster below.
    wear = g.noise(co, 3.5, 8, 0.7)
    flaked = g.math('GREATER_THAN', wear.outputs['Fac'], 0.64)
    painted = g.math('MAXIMUM', g.math('MAXIMUM', dado, frieze), line)
    field = g.mix(g.math('MULTIPLY', flaked, g.math('MULTIPLY', painted, 0.7)), field,
                  tuple(c * 0.95 for c in scheme.field))
    occlusion = g.ao(0.4, 4)
    field = g.mix(g.math('MULTIPLY', g.math('SUBTRACT', 1.0, occlusion), 0.55, True), field,
                  (0.18, 0.13, 0.09), 'MULTIPLY')
    soot = g.noise(g.scale_vector(co, (1.0, 1.0, 0.3)), 2.0, 3)
    soot_mask = g.math('MULTIPLY', g.math('GREATER_THAN', z, scheme.frieze_high + 0.1),
                       g.math('MULTIPLY', soot.outputs['Fac'], 0.4))
    field = g.mix(soot_mask, field, (0.25, 0.2, 0.15), 'MULTIPLY')
    fine = g.noise(co, 22, 8, 0.65)
    normal = g.bump(g.math('ADD', fine.outputs['Fac'], g.math('MULTIPLY', flaked, 0.5)), 0.18, 0.003)
    g.finish(field, 0.9, normal)
    return material


def whitewash(name: str, tint: RGB) -> bpy.types.Material:
    material, g = _new(name, tint)
    if g is None:
        return material
    co = g.coords('Object', randomize=1.0)
    mottling = g.noise(co, 0.9, 6, 0.65)
    color = g.ramp(mottling.outputs['Fac'], ((0.3, tuple(c * 0.7 for c in tint)), (0.6, tint)))
    stain = g.noise(g.scale_vector(co, (1.0, 1.0, 0.25)), 1.4, 3)
    color = g.mix(g.math('MULTIPLY', stain.outputs['Fac'], 0.45), color, (0.35, 0.28, 0.2), 'MULTIPLY')
    occlusion = g.ao(0.5, 3)
    color = g.mix(g.math('MULTIPLY', g.math('SUBTRACT', 1.0, occlusion), 0.7, True), color, (0.12, 0.1, 0.08))
    normal = g.bump(g.noise(co, 14, 6).outputs['Fac'], 0.2, 0.004)
    g.finish(color, 0.92, normal)
    return material


# ---------------------------------------------------------------------------
# Floors
# ---------------------------------------------------------------------------

def slab_floor(name: str, look: StoneLook, slab: tuple[float, float] = (1.2, 0.8),
               polish: float = 0.0, border: RGB | None = None) -> bpy.types.Material:
    material, g = _new(name, look.mid)
    if g is None:
        return material
    co = g.coords('Object')
    brick = g.node('ShaderNodeTexBrick')
    brick.offset = 0.5
    brick.inputs['Scale'].default_value = 1.0
    brick.inputs['Brick Width'].default_value = slab[0]
    brick.inputs['Row Height'].default_value = slab[1]
    brick.inputs['Mortar Size'].default_value = 0.006
    brick.inputs['Mortar Smooth'].default_value = 0.4
    brick.inputs['Bias'].default_value = 0.0
    brick.inputs['Color1'].default_value = (*look.mid, 1)
    brick.inputs['Color2'].default_value = (*look.light, 1)
    brick.inputs['Mortar'].default_value = (*look.stain, 1)
    g.link(co, brick.inputs['Vector'])
    broad = g.noise(co, 0.5, 5, 0.6)
    color = g.mix(g.math('MULTIPLY', broad.outputs['Fac'], 0.6), brick.outputs['Color'], look.dark)
    occlusion = g.ao(0.4, 4)
    color = g.mix(g.math('MULTIPLY', g.math('SUBTRACT', 1.0, occlusion), look.crevice * 1.4, True),
                  color, look.stain)
    wear = g.noise(co, 2.2, 4)
    fine = g.noise(co, 30, 8, 0.7)
    height = g.math('SUBTRACT', g.math('MULTIPLY', fine.outputs['Fac'], 0.2),
                    g.math('MULTIPLY', brick.outputs['Fac'], 1.0))
    normal = g.bump(height, 0.4, 0.004)
    rough = g.math('ADD', look.roughness - polish, g.math('MULTIPLY', wear.outputs['Fac'], 0.2))
    g.finish(color, rough, normal)
    return material


# ---------------------------------------------------------------------------
# Wood, metal, cloth, clay
# ---------------------------------------------------------------------------

def teak(name: str, tone: RGB = (0.20, 0.10, 0.045)) -> bpy.types.Material:
    material, g = _new(name, tone)
    if g is None:
        return material
    co = g.coords('Object', randomize=1.0)
    stretched = g.scale_vector(co, (1.0, 1.0, 0.08))
    grain = g.node('ShaderNodeTexWave')
    grain.wave_type = 'RINGS'
    grain.inputs['Scale'].default_value = 7.0
    grain.inputs['Distortion'].default_value = 6.0
    grain.inputs['Detail'].default_value = 3.0
    g.link(stretched, grain.inputs['Vector'])
    color = g.ramp(grain.outputs['Fac'], ((0.2, tuple(c * 0.55 for c in tone)), (0.7, tone),
                                          (1.0, tuple(min(1, c * 1.35) for c in tone))))
    occlusion = g.ao(0.2, 3)
    color = g.mix(g.math('MULTIPLY', g.math('SUBTRACT', 1.0, occlusion), 0.8, True), color, (0.03, 0.015, 0.008))
    normal = g.bump(grain.outputs['Fac'], 0.12, 0.002)
    g.finish(color, g.math('ADD', 0.48, g.math('MULTIPLY', grain.outputs['Fac'], 0.15)), normal)
    return material


def metal(name: str, tint: RGB, roughness: float = 0.32, tarnish: RGB = (0.12, 0.09, 0.05)) -> bpy.types.Material:
    material, g = _new(name, tint)
    if g is None:
        return material
    co = g.coords('Object', randomize=1.0)
    patina = g.noise(co, 6.0, 6, 0.6)
    occlusion = g.ao(0.08, 3)
    dirty = g.math('ADD', g.math('MULTIPLY', patina.outputs['Fac'], 0.5),
                   g.math('MULTIPLY', g.math('SUBTRACT', 1.0, occlusion), 0.8))
    color = g.mix(g.math('MINIMUM', dirty, 0.85), tint, tarnish)
    rough = g.math('ADD', roughness, g.math('MULTIPLY', dirty, 0.3))
    g.finish(color, rough, None, metallic=1.0)
    return material


def cloth(name: str, base: RGB, stripe: RGB, accent: RGB, stripe_scale: float = 9.0,
          axis: str = 'X') -> bpy.types.Material:
    """Hand-loomed cotton or silk with woven stripes and a soft sheen."""
    material, g = _new(name, base)
    if g is None:
        return material
    co = g.coords('Object')
    parts = g.separate(co)
    run = parts.outputs[axis]
    phase = g.math('FRACT', g.math('MULTIPLY', run, stripe_scale / 6.283))
    stripe_mask = g.math('LESS_THAN', phase, 0.18)
    accent_mask = g.math('MULTIPLY', g.math('GREATER_THAN', phase, 0.24), g.math('LESS_THAN', phase, 0.29))
    color = g.mix(stripe_mask, base, stripe)
    color = g.mix(accent_mask, color, accent)
    weave = g.noise(co, 220, 2, 0.5)
    slub = g.noise(g.scale_vector(co, (1, 1, 6)), 7, 3)
    color = g.mix(g.math('MULTIPLY', slub.outputs['Fac'], 0.3), color, tuple(c * 0.75 for c in base))
    normal = g.bump(weave.outputs['Fac'], 0.25, 0.0015)
    g.finish(color, 0.82, normal)
    g.shader.inputs['Sheen Weight'].default_value = 0.35
    g.shader.inputs['Sheen Tint'].default_value = (*stripe, 1)
    return material


def terracotta(name: str, tone: RGB = (0.42, 0.20, 0.10)) -> bpy.types.Material:
    material, g = _new(name, tone)
    if g is None:
        return material
    co = g.coords('Object', randomize=1.0)
    mottle = g.noise(co, 3.0, 6, 0.6)
    color = g.ramp(mottle.outputs['Fac'], ((0.3, tuple(c * 0.7 for c in tone)), (0.65, tone),
                                           (0.9, (0.55, 0.42, 0.30))))
    normal = g.bump(g.noise(co, 40, 6).outputs['Fac'], 0.2, 0.002)
    g.finish(color, 0.88, normal)
    return material


def flame(name: str, strength: float = 22.0) -> bpy.types.Material:
    """Lamp flame. Its `Lamps lit` value (0 or 1) is keyed per time of day."""
    material, g = _new(name, (1.0, 0.5, 0.1))
    if g is None:
        return material
    g.nodes.remove(g.shader)
    emission = g.node('ShaderNodeEmission', 400, 100)
    emission.inputs['Color'].default_value = (1.0, 0.46, 0.12, 1)
    emission.inputs['Strength'].default_value = strength
    clear = g.node('ShaderNodeBsdfTransparent', 400, -100)
    lit = g.node('ShaderNodeValue', 200, 250)
    lit.name = lit.label = 'Lamps lit'
    lit.outputs[0].default_value = 1.0
    mix = g.node('ShaderNodeMixShader', 650, 0)
    g.link(lit.outputs[0], mix.inputs['Fac'])
    g.link(clear.outputs[0], mix.inputs[1])
    g.link(emission.outputs[0], mix.inputs[2])
    g.link(mix.outputs[0], g.output.inputs['Surface'])
    return material


def flat(name: str, color: RGB, roughness: float = 0.85) -> bpy.types.Material:
    material, g = _new(name, color)
    if g is None:
        return material
    g.finish(color, roughness)
    return material


# ---------------------------------------------------------------------------
# Landscape and water
# ---------------------------------------------------------------------------

def river_water(name: str) -> bpy.types.Material:
    """Silty flood water: opaque body, glossy rippled surface."""
    material, g = _new(name, (0.12, 0.10, 0.07))
    if g is None:
        return material
    position = g.node('ShaderNodeNewGeometry').outputs['Position']
    flow = g.scale_vector(position, (0.35, 1.0, 1.0))
    ripples = g.noise(flow, 1.3, 6, 0.55, distortion=0.6)
    swell = g.node('ShaderNodeTexWave')
    swell.bands_direction = 'DIAGONAL'
    swell.inputs['Scale'].default_value = 0.08
    swell.inputs['Distortion'].default_value = 4.0
    swell.inputs['Detail'].default_value = 4.0
    g.link(position, swell.inputs['Vector'])
    height = g.math('ADD', ripples.outputs['Fac'], g.math('MULTIPLY', swell.outputs['Fac'], 0.4))
    normal = g.bump(height, 0.22, 0.05)
    silt = g.noise(g.scale_vector(position, (0.08, 0.2, 1.0)), 1.0, 3)
    color = g.mix(silt.outputs['Fac'], (0.075, 0.063, 0.042), (0.15, 0.12, 0.08))
    g.finish(color, 0.04, normal)
    g.shader.inputs['IOR'].default_value = 1.333
    g.shader.inputs['Specular IOR Level'].default_value = 0.5
    return material


def terrain(name: str) -> bpy.types.Material:
    """Dry earth with grass on gentle ground and silt on low ground."""
    material, g = _new(name, (0.32, 0.26, 0.17))
    if g is None:
        return material
    geometry = g.node('ShaderNodeNewGeometry')
    position = geometry.outputs['Position']
    slope = g.separate(geometry.outputs['Normal']).outputs['Z']
    z = g.separate(position).outputs['Z']
    patches = g.noise(position, 0.018, 4, 0.55)
    detail = g.noise(position, 0.8, 6, 0.6)
    earth = g.ramp(detail.outputs['Fac'], ((0.3, (0.27, 0.20, 0.13)), (0.7, (0.40, 0.31, 0.20))))
    grass = g.ramp(detail.outputs['Fac'], ((0.3, (0.14, 0.13, 0.06)), (0.7, (0.24, 0.21, 0.10))))
    flat_ground = g.math('MULTIPLY', g.math('SUBTRACT', slope, 0.86), 8.0, True)
    grassy = g.math('MULTIPLY', g.math('SUBTRACT', patches.outputs['Fac'], 0.42), 6.0, True)
    grass_mask = g.math('MULTIPLY', flat_ground, grassy)
    color = g.mix(grass_mask, earth, grass)
    silt = g.math('LESS_THAN', z, 0.4)
    color = g.mix(g.math('MULTIPLY', silt, 0.75), color, (0.26, 0.22, 0.16))
    rock = g.math('LESS_THAN', slope, 0.55)
    color = g.mix(rock, color, (0.36, 0.28, 0.19))
    normal = g.bump(detail.outputs['Fac'], 0.5, 0.05)
    g.finish(color, 0.95, normal)
    return material


def foliage(name: str, tone: RGB = (0.07, 0.10, 0.035), leaf_scale: float = 16.0) -> bpy.types.Material:
    """Leaf canopy: small voronoi leaves with sun-bleached and shaded clumps, thin-leaf translucency."""
    material, g = _new(name, tone)
    if g is None:
        return material
    co = g.coords('Object', randomize=1.0)
    leaves = g.voronoi(co, leaf_scale)
    clumps = g.noise(co, leaf_scale * 0.12, 3.0)
    light = tuple(min(1.0, c * 1.9 + 0.012) for c in (tone[0] * 1.3, tone[1], tone[2] * 0.7))
    variation = g.ramp(clumps.outputs['Fac'], ((0.3, tuple(c * 0.55 for c in tone)), (0.5, tone), (0.72, light)))
    edge = g.ramp(leaves.outputs['Distance'], ((0.0, (1.0, 1.0, 1.0)), (0.55, (0.85, 0.85, 0.85)),
                                                (1.0, (0.35, 0.35, 0.35))))
    color = g.mix(1.0, variation, edge, 'MULTIPLY')
    normal = g.bump(leaves.outputs['Distance'], 1.0, 0.04)
    g.finish(color, 0.62, normal)
    g.shader.inputs['Subsurface Weight'].default_value = 0.2
    if 'Transmission Weight' in g.shader.inputs:
        g.shader.inputs['Transmission Weight'].default_value = 0.0
    return material
    co = g.coords('Object', randomize=1.0)
    leaves = g.voronoi(co, 9.0)
    color = g.ramp(leaves.outputs['Distance'], ((0.0, tuple(c * 1.6 for c in tone)), (0.6, tone),
                                                (1.0, tuple(c * 0.4 for c in tone))))
    normal = g.bump(leaves.outputs['Distance'], 0.8, 0.05)
    g.finish(color, 0.7, normal)
    g.shader.inputs['Subsurface Weight'].default_value = 0.15
    return material
