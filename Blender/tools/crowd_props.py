"""Shared diya (clay oil lamp) for the crowd kit.

Origin: centre of the base, Z up.  About 9 cm across and 5 cm tall with the
flame, small enough to sit on a child's palm.  The flame is emissive.
"""

from __future__ import annotations

import bmesh
import bpy
from mathutils import Vector


RADIUS = .045
OBJECT_NAME = 'Prop_Diya'


def _material(name: str, rgb: tuple[float, float, float], rough: float, glow: float = 0.):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.diffuse_color = (*rgb, 1)
    material.use_nodes = True
    shader = material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*rgb, 1)
    shader.inputs['Roughness'].default_value = rough
    if glow:
        shader.inputs['Emission Color'].default_value = (*rgb, 1)
        shader.inputs['Emission Strength'].default_value = glow
    return material


def _ellipsoid(name: str, scale: tuple[float, float, float], center: tuple[float, float, float],
               material, keep_below: float | None = None) -> bpy.types.Object:
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=1.)
    if keep_below is not None:
        doomed = [face for face in bm.faces if face.calc_center_median().z > keep_below]
        bmesh.ops.delete(bm, geom=doomed, context='FACES')
    for vertex in bm.verts:
        vertex.co = Vector((vertex.co.x * scale[0], vertex.co.y * scale[1], vertex.co.z * scale[2])) \
            + Vector(center)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    mesh.materials.append(material)
    return bpy.data.objects.new(name, mesh)


def build(collection: bpy.types.Collection) -> bpy.types.Object:
    """Create the diya in `collection`; returns the parent empty (origin = base centre)."""
    clay = _material('Prop • Diya clay', (.30, .13, .06), .86)
    oil = _material('Prop • Diya oil', (.14, .08, .02), .18)
    flame = _material('Prop • Diya flame', (1., .55, .12), .5, glow=18.)
    root = bpy.data.objects.new(OBJECT_NAME, None)
    root.empty_display_type = 'PLAIN_AXES'
    root.empty_display_size = .03
    collection.objects.link(root)
    rim = .022 + .022 * .25
    parts = (
        _ellipsoid('Diya bowl', (RADIUS, RADIUS, .022), (0, 0, .022), clay, keep_below=.25),
        _ellipsoid('Diya lip', (RADIUS * .72, RADIUS * .72, .004), (0, 0, rim - .002), clay),
        _ellipsoid('Diya oil', (RADIUS * .86, RADIUS * .86, .0025), (0, 0, rim - .006), oil),
        _ellipsoid('Diya wick', (.0025, .0025, .006), (RADIUS * .55, 0, rim + .002), clay),
        _ellipsoid('Diya flame', (.0055, .0055, .016), (RADIUS * .55, 0, rim + .017), flame),
    )
    for part in parts:
        collection.objects.link(part)
        part.parent = root
    return root


def _box(name: str, size: tuple[float, float, float], center: tuple[float, float, float], material,
         collection: bpy.types.Collection, parent: bpy.types.Object) -> bpy.types.Object:
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.)
    for vertex in bm.verts:
        vertex.co = Vector((vertex.co.x * size[0], vertex.co.y * size[1], vertex.co.z * size[2])) + Vector(center)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.parent = parent
    return obj


def mat(collection: bpy.types.Collection, length: float = 1.7, width: float = .9) -> bpy.types.Object:
    """A woven reed floor mat (chatai).  Origin: centre of the mat on the floor; length runs along Y."""
    weave = _material('Prop • Chatai reed', (.52, .38, .18), .94)
    border = _material('Prop • Chatai border', (.30, .10, .06), .92)
    root = bpy.data.objects.new('Prop_Chatai mat', None)
    root.empty_display_type = 'PLAIN_AXES'
    root.empty_display_size = .1
    collection.objects.link(root)
    thick = .008
    _box('Chatai body', (width, length, thick), (0, 0, thick / 2), weave, collection, root)
    for x in (-1, 1):
        _box(f'Chatai edge {x}', (.03, length, thick * 1.4), (x * (width / 2 - .015), 0, thick * .7),
             border, collection, root)
    for y in (-1, 1):
        _box(f'Chatai end {y}', (width, .03, thick * 1.4), (0, y * (length / 2 - .015), thick * .7),
             border, collection, root)
    for index in range(1, 12):  # woven bands across the mat
        y = -length / 2 + length * index / 12
        _box(f'Chatai band {index}', (width - .06, .012, thick * 1.15), (0, y, thick * .6),
             border if index % 3 == 0 else weave, collection, root)
    return root


def stairs(collection: bpy.types.Collection, rise: float, steps: int = 3, run: float = .42,
           width: float = 1.2) -> bpy.types.Object:
    """Stone temple steps rising toward +Y.  Origin: floor level at the front edge, centred in X."""
    stone = _material('Prop • Sandstone step', (.36, .30, .22), .93)
    root = bpy.data.objects.new('Prop_Stone steps', None)
    root.empty_display_type = 'PLAIN_AXES'
    root.empty_display_size = .1
    collection.objects.link(root)
    for index in range(steps):
        top = rise * (index + 1)
        _box(f'Step {index + 1}', (width, run * (steps - index), top),
             (0, run * (steps - index) / 2 + run * index, top / 2), stone, collection, root)
    return root
