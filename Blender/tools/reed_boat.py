"""Shared reed toy boat for Nandu and his daughter (one prop for both branches).

Sized to the daughter's palm first: about 6 cm palm width, 11 cm wrist to middle
fingertip, so the hull sits across her palm with the fingers curled over it.
Origin and grip point: centre of the hull bottom. Length runs along X.
"""

from __future__ import annotations

import math

import bpy
from mathutils import Vector


LENGTH = .130
BEAM = .045
HEIGHT = .035  # including the folded reed ends
STRANDS = 7
OBJECT_NAME = 'Prop_Reed toy boat'

Quad = tuple[int, int, int, int]


def _material(name: str, rgb: tuple[float, float, float], rough: float):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.diffuse_color = (*rgb, 1)
    material.use_nodes = True
    shader = material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*rgb, 1)
    shader.inputs['Roughness'].default_value = rough
    return material


def _tube(points: list[Vector], radius: float, verts: list[Vector], faces: list[Quad],
          indices: list[int], material: int, cyclic: bool = False) -> None:
    base, count, sides = len(verts), len(points), 8
    for i, point in enumerate(points):
        before = points[i-1] if cyclic or i > 0 else point
        after = points[(i+1) % count] if cyclic or i < count-1 else point
        tangent = (after-before).normalized()
        helper = Vector((0, 0, 1)) if abs(tangent.z) < .9 else Vector((0, 1, 0))
        u = helper.cross(tangent).normalized()
        v = tangent.cross(u)
        taper = 1 if cyclic else .55 + .45*math.sin(math.pi*i/(count-1))
        verts.extend(point + radius*taper*(u*math.cos(math.tau*j/sides) + v*math.sin(math.tau*j/sides))
                     for j in range(sides))
    for i in range(count if cyclic else count-1):
        n = (i+1) % count
        for j in range(sides):
            k = (j+1) % sides
            faces.append((base+i*sides+j, base+i*sides+k, base+n*sides+k, base+n*sides+j))
            indices.append(material)


def build(collection) -> bpy.types.Object:
    """Create the boat in `collection`; returns the object with its origin at the hull bottom."""
    reed = _material('Prop • Dry reed', (.40, .32, .15), .78)
    tie = _material('Prop • Reed boat grass tie', (.20, .17, .07), .9)
    strand_radius = BEAM/(STRANDS*2.2)
    hull_depth = BEAM*.22
    verts: list[Vector] = []
    faces: list[Quad] = []
    indices: list[int] = []
    for strand in range(STRANDS):
        offset = (strand-(STRANDS-1)/2)/((STRANDS-1)/2)  # -1 .. 1 across the beam
        points = []
        for i in range(21):
            t = i/20
            x = (t-.5)*LENGTH*(1-.06*abs(offset))
            belly = math.sin(math.pi*t)
            y = offset*(BEAM/2-strand_radius)*belly**.6
            # Hull is lowest along the keel; the ends fold up to the full height.
            z = (hull_depth*(1-offset*offset)*(1-belly)
                 + (HEIGHT-strand_radius*2-hull_depth)*abs(2*t-1)**2.6 + hull_depth*abs(offset)*belly)
            points.append(Vector((x, y, z)))
        _tube(points, strand_radius, verts, faces, indices, 0)
    for x in (-.32*LENGTH, 0, .32*LENGTH):
        ring = [Vector((x, (BEAM/2+.0006)*math.cos(math.tau*j/16),
                        hull_depth*.8+(hull_depth*.9+.0006)*math.sin(math.tau*j/16))) for j in range(16)]
        _tube(ring, .0009, verts, faces, indices, 1, cyclic=True)
    bottom = min(v.z for v in verts)
    for v in verts:
        v.z -= bottom
    mesh = bpy.data.meshes.new('Reed toy boat')
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(reed)
    mesh.materials.append(tie)
    for face, material in zip(mesh.polygons, indices):
        face.use_smooth = True
        face.material_index = material
    boat = bpy.data.objects.new(OBJECT_NAME, mesh)
    collection.objects.link(boat)
    boat['Length (cm)'] = round(LENGTH*100, 1)
    boat['Grip point'] = 'Object origin: centre of the hull bottom'
    return boat
