"""Primitives and procedural materials for the ghat set."""

import math

import bmesh
import bpy
from mathutils import Vector

_current = None


def collection(name):
    result = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(result)
    return result


def use(col):
    global _current
    _current = col


def place(obj):
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    _current.objects.link(obj)
    return obj


def finish(obj, name, surface, smooth=False):
    obj.name = name
    if surface:
        obj.data.materials.append(surface)
    if smooth:
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    return place(obj)


def box(name, center, size, surface, bevel=0.0, yaw=0.0, tilt=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.object
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.rotation_euler = (0, tilt, yaw)
    if bevel:
        modifier = obj.modifiers.new('Soft construction edges', 'BEVEL')
        modifier.width, modifier.segments = bevel, 2
    return finish(obj, name, surface)


def sphere(name, center, scale, surface):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=center)
    obj = bpy.context.object
    obj.scale = scale
    return finish(obj, name, surface, smooth=True)


def rod(name, a, b, radius, surface, vertices=10):
    a, b = Vector(a), Vector(b)
    direction = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius,
                                        depth=direction.length, location=(a + b) / 2)
    obj = bpy.context.object
    obj.rotation_euler = direction.to_track_quat('Z', 'Y').to_euler()
    return finish(obj, name, surface, smooth=True)


def cone(name, center, radius, depth, surface, vertices=4, yaw=0.0):
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius, radius2=0,
                                    depth=depth, location=center)
    obj = bpy.context.object
    obj.rotation_euler.z = yaw
    return finish(obj, name, surface)


def empty(name, location, kind='PLAIN_AXES', size=.4):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type, obj.empty_display_size = kind, size
    obj.location = location
    _current.objects.link(obj)
    return obj


def mesh_object(name, verts, faces, surface, smooth=False):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    _current.objects.link(obj)
    if surface:
        mesh.materials.append(surface)
    for polygon in mesh.polygons:
        polygon.use_smooth = smooth
    return obj


def _ccw(points):
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1]))
    return points if area > 0 else points[::-1]


def flat_polygon(name, points, z, surface):
    points = _ccw(list(points))
    return mesh_object(name, [(x, y, z) for x, y in points], [list(range(len(points)))], surface)


def prism(name, points, z_top, z_bottom, surface):
    """Closed vertical-sided slab from a 2D outline (used for banks)."""
    points = _ccw(list(points))
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    top = [bm.verts.new((x, y, z_top)) for x, y in points]
    low = [bm.verts.new((x, y, z_bottom)) for x, y in points]
    bm.faces.new(top)
    bm.faces.new(low[::-1])
    for i in range(len(points)):
        j = (i + 1) % len(points)
        bm.faces.new((top[i], low[i], low[j], top[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    _current.objects.link(obj)
    mesh.materials.append(surface)
    return obj


def material(name, color, roughness=.8, metal=0, emission=0):
    surface = bpy.data.materials.new(name)
    surface.diffuse_color = (*color, 1)
    if surface.node_tree is None:  # use_nodes is deprecated in Blender 5.2 and removed in 6.0
        surface.use_nodes = True
    shader = surface.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metal
    if emission:
        shader.inputs['Emission Color'].default_value = (*color, 1)
        shader.inputs['Emission Strength'].default_value = emission
    return surface


def textured(name, color, roughness=.85, scale=6.0, contrast=.45, bump=.25):
    """Noise-varied stone, earth or plank material with a matching bump."""
    surface = material(name, color, roughness)
    tree = surface.node_tree
    shader = tree.nodes.get('Principled BSDF')
    coords = tree.nodes.new('ShaderNodeTexCoord')
    noise = tree.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = scale
    noise.inputs['Detail'].default_value = 8
    ramp = tree.nodes.new('ShaderNodeValToRGB')
    dark = [c * (1 - contrast) for c in color]
    light = [min(1, c * (1 + contrast * .5)) for c in color]
    ramp.color_ramp.elements[0].color = (*dark, 1)
    ramp.color_ramp.elements[1].color = (*light, 1)
    height = tree.nodes.new('ShaderNodeBump')
    height.inputs['Strength'].default_value = bump
    tree.links.new(coords.outputs['Object'], noise.inputs['Vector'])
    tree.links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
    tree.links.new(ramp.outputs['Color'], shader.inputs['Base Color'])
    tree.links.new(noise.outputs['Fac'], height.inputs['Height'])
    tree.links.new(height.outputs['Normal'], shader.inputs['Normal'])
    return surface


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()
