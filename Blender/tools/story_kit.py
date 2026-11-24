"""Shared geometry and material helpers for the story prop library (metres, Z up).

Each prop accumulates into a MeshBuilder so it becomes one object with material slots.
Smoothing uses a modifier that is baked into plain geometry, so the FBX export (which ignores
modifiers in this project) matches the Blender view.
"""

from __future__ import annotations

import math

import bpy
import bmesh
from mathutils import Euler, Vector

TAU = math.tau


def mat(name, rgb, rough=.8, metal=0., bump=0., scale=40., variation=0., detail=8., emit=0., coat=0.):
    """Procedural material: noise tints the colour (variation) and perturbs the normal (bump)."""
    existing = bpy.data.materials.get(name)
    if existing:
        return existing
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True  # deprecated in Blender 5.2; removed in 6.0, so keep it in this one helper
    nodes, links = m.node_tree.nodes, m.node_tree.links
    shader = nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*rgb, 1)
    shader.inputs['Roughness'].default_value = rough
    shader.inputs['Metallic'].default_value = metal
    if coat:
        shader.inputs['Coat Weight'].default_value = coat
    if emit:
        shader.inputs['Emission Color'].default_value = (*rgb, 1)
        shader.inputs['Emission Strength'].default_value = emit
    if bump or variation:
        coord = nodes.new('ShaderNodeTexCoord')
        noise = nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = scale
        noise.inputs['Detail'].default_value = detail
        noise.inputs['Roughness'].default_value = .62
        links.new(coord.outputs['Object'], noise.inputs['Vector'])
        if variation:
            mix = nodes.new('ShaderNodeMix')
            mix.data_type = 'RGBA'
            mix.inputs['A'].default_value = (*rgb, 1)
            mix.inputs['B'].default_value = (rgb[0]*(1-variation), rgb[1]*(1-variation),
                                             rgb[2]*(1-variation), 1)
            links.new(noise.outputs['Fac'], mix.inputs['Factor'])
            links.new(mix.outputs['Result'], shader.inputs['Base Color'])
        if bump:
            node = nodes.new('ShaderNodeBump')
            node.inputs['Strength'].default_value = bump
            node.inputs['Distance'].default_value = .004
            links.new(noise.outputs['Fac'], node.inputs['Height'])
            links.new(node.outputs['Normal'], shader.inputs['Normal'])
    return m


class MeshBuilder:
    def __init__(self):
        self.verts: list[Vector] = []
        self.faces: list[tuple] = []
        self.face_mat: list[int] = []
        self.materials: list = []

    def slot(self, material) -> int:
        if material not in self.materials:
            self.materials.append(material)
        return self.materials.index(material)

    def add(self, verts, faces, material):
        base, index = len(self.verts), self.slot(material)
        self.verts.extend(Vector(v) for v in verts)
        for face in faces:
            self.faces.append(tuple(base + i for i in face))
            self.face_mat.append(index)

    def loft(self, stations, material, sides=16, cap=True, rotation=0.):
        """stations: [(centre, rx, ry)] swept along the polyline; rx and ry are half axes."""
        pts = [Vector(s[0]) for s in stations]
        rings = []
        for i, (centre, rx, ry) in enumerate(stations):
            before, after = pts[max(i-1, 0)], pts[min(i+1, len(pts)-1)]
            t = (after-before).normalized()
            helper = Vector((0, 0, 1)) if abs(t.z) < .92 else Vector((1, 0, 0))
            u = helper.cross(t).normalized()
            v = t.cross(u)
            rings.append([Vector(centre) + u*rx*math.cos(TAU*j/sides + rotation)
                          + v*ry*math.sin(TAU*j/sides + rotation) for j in range(sides)])
        verts = [p for ring in rings for p in ring]
        faces = []
        for i in range(len(rings)-1):
            for j in range(sides):
                k = (j+1) % sides
                faces.append((i*sides+j, i*sides+k, (i+1)*sides+k, (i+1)*sides+j))
        if cap:
            for ring_index, flip in ((0, True), (len(rings)-1, False)):
                centre_index = len(verts)
                verts.append(pts[ring_index])
                for j in range(sides):
                    a, b = ring_index*sides+j, ring_index*sides+(j+1) % sides
                    faces.append((centre_index, b, a) if flip else (centre_index, a, b))
        self.add(verts, faces, material)

    def tube(self, points, radius, material, sides=8, taper=0., cap=True):
        n = len(points)
        stations = []
        for i, p in enumerate(points):
            r = radius(i/(n-1)) if callable(radius) else radius*(1-taper*i/(n-1))
            stations.append((p, r, r))
        self.loft(stations, material, sides, cap)

    def lathe(self, profile, material, sides=32, centre=(0, 0, 0), closed_bottom=True):
        """profile: [(radius, z)] from the bottom upward."""
        cx, cy, cz = centre
        rings = [[Vector((cx+r*math.cos(TAU*j/sides), cy+r*math.sin(TAU*j/sides), cz+z))
                  for j in range(sides)] for r, z in profile]
        verts = [p for ring in rings for p in ring]
        faces = []
        for i in range(len(rings)-1):
            for j in range(sides):
                k = (j+1) % sides
                faces.append((i*sides+j, i*sides+k, (i+1)*sides+k, (i+1)*sides+j))
        if closed_bottom and profile[0][0] > 1e-6:
            c = len(verts)
            verts.append(Vector((cx, cy, cz+profile[0][1])))
            faces.extend((c, (j+1) % sides, j) for j in range(sides))
        self.add(verts, faces, material)

    def box(self, size, centre, material, yaw=0., tilt=(0, 0)):
        sx, sy, sz = (s/2 for s in size)
        rot = Euler((tilt[0], tilt[1], yaw)).to_matrix()
        verts = [Vector(centre) + rot @ Vector((x*sx, y*sy, z*sz))
                 for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
        faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        self.add(verts, faces, material)

    def ellipsoid(self, centre, radii, material, rot=(0, 0, 0), rings=10, sides=16):
        r = Euler(rot).to_matrix()
        verts, faces = [], []
        for i in range(rings+1):
            s, c = math.sin(math.pi*i/rings), -math.cos(math.pi*i/rings)
            for j in range(sides):
                a = TAU*j/sides
                verts.append(Vector(centre) + r @ Vector((radii[0]*s*math.cos(a), radii[1]*s*math.sin(a), radii[2]*c)))
        for i in range(rings):
            for j in range(sides):
                k = (j+1) % sides
                faces.append((i*sides+j, i*sides+k, (i+1)*sides+k, (i+1)*sides+j))
        self.add(verts, faces, material)

    def surface(self, nx, ny, fn, material):
        """Parametric sheet: fn(u, v) -> point, u and v in 0..1."""
        verts = [Vector(fn(i/nx, j/ny)) for j in range(ny+1) for i in range(nx+1)]
        faces = [(j*(nx+1)+i, j*(nx+1)+i+1, (j+1)*(nx+1)+i+1, (j+1)*(nx+1)+i)
                 for j in range(ny) for i in range(nx)]
        self.add(verts, faces, material)

    def build(self, name, collection, smooth=0, solidify=0., location=(0, 0, 0)):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata([tuple(v) for v in self.verts], [], self.faces)
        for m in self.materials:
            mesh.materials.append(m)
        mesh.update()
        for poly, index in zip(mesh.polygons, self.face_mat):
            poly.material_index = index
            poly.use_smooth = True
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        obj.location = location
        if solidify:
            mod = obj.modifiers.new('Thickness', 'SOLIDIFY')
            mod.thickness, mod.offset = solidify, 0
        if smooth:
            mod = obj.modifiers.new('Smooth', 'SUBSURF')
            mod.levels = mod.render_levels = smooth
        if obj.modifiers:
            bake(obj)
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(obj.data)
        bm.free()
        return obj


def bake(obj):
    """Replace modifiers with their evaluated geometry, keeping material slots."""
    graph = bpy.context.evaluated_depsgraph_get()
    baked = bpy.data.meshes.new_from_object(obj.evaluated_get(graph))
    old = obj.data
    obj.modifiers.clear()
    obj.data = baked
    baked.name = old.name
    for poly in baked.polygons:
        poly.use_smooth = True
    bpy.data.meshes.remove(old)


def collection(parent, name):
    c = bpy.data.collections.new(name)
    parent.children.link(c)
    return c


def empty(coll, name, location=(0, 0, 0), size=.05, parent=None):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type, e.empty_display_size = 'PLAIN_AXES', size
    e.location = location
    coll.objects.link(e)
    if parent:
        e.parent = parent
    return e


def spline(points, steps=10):
    """Catmull-Rom curve through the points as a dense list of Vectors."""
    p = [Vector(x) for x in points]
    p = [p[0]*2-p[1]] + p + [p[-1]*2-p[-2]]
    out = []
    for i in range(1, len(p)-2):
        for s in range(steps):
            t = s/steps
            out.append(.5*((2*p[i]) + (-p[i-1]+p[i+1])*t + (2*p[i-1]-5*p[i]+4*p[i+1]-p[i+2])*t*t
                           + (-p[i-1]+3*p[i]-3*p[i+1]+p[i+2])*t**3))
    out.append(p[-2])
    return out


def drive(owner, data_path, source, prop, expression, index=-1):
    """Driver: owner.<data_path> = expression(v), where v reads source[prop]."""
    fc = owner.driver_add(data_path, index) if index >= 0 else owner.driver_add(data_path)
    d = fc.driver
    d.type = 'SCRIPTED'
    var = d.variables.new()
    var.name = 'v'
    var.targets[0].id = source
    var.targets[0].data_path = f'["{prop}"]'
    d.expression = expression
    return fc


def table(rows, t):
    """Piecewise-linear lookup. rows: [(t, v)] or [(t, (v1, v2, ...))]; returns the interpolated value."""
    if t <= rows[0][0]:
        return rows[0][1]
    for (t0, a), (t1, b) in zip(rows, rows[1:]):
        if t <= t1:
            f = (t-t0)/(t1-t0)
            if isinstance(a, (tuple, list)):
                return tuple(x+(y-x)*f for x, y in zip(a, b))
            return a+(b-a)*f
    return rows[-1][1]


def stage(scene, width=1500, height=1000, samples=48, strength=.7):
    """Review lighting and Cycles settings for still renders."""
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100
    scene.render.fps = 24
    scene.unit_settings.system = 'METRIC'
    scene.view_settings.view_transform = 'AgX'
    scene.world = bpy.data.worlds.new(f'{scene.name} ambient')
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value = (.36, .42, .50, 1)
    bg.inputs['Strength'].default_value = strength


def aim(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z', 'Y').to_euler()


def lamp(scene, name, location, target, energy, color=(1, .9, .78), size=2.5):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy, data.color, data.size = energy, color, size
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = location
    aim(obj, target)
    return obj


def camera(scene, name, location, target, lens=50):
    data = bpy.data.cameras.new(name)
    data.lens = lens
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = location
    aim(obj, target)
    scene.camera = obj
    return obj


def ground(scene, size=30., rgb=(.22, .19, .15), z=0.):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, z))
    obj = bpy.context.object
    obj.name = 'Review ground'
    obj.data.materials.append(mat('Review ground', rgb, .95, bump=.2, scale=60))
    return obj


def render(scene, camera_obj, path):
    scene.camera = camera_obj
    scene.render.filepath = str(path)
    scene.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(write_still=True)



def rope(builder, path, radius, material, strands=3, twist=5.0, sides=6):
    """Laid rope: `strands` helical tubes around the path, `twist` turns per metre."""
    pts = [Vector(p) for p in path]
    run = 0.
    frames = []
    for i, p in enumerate(pts):
        if i:
            run += (p-pts[i-1]).length
        t = (pts[min(i+1, len(pts)-1)]-pts[max(i-1, 0)]).normalized()
        helper = Vector((0, 0, 1)) if abs(t.z) < .92 else Vector((1, 0, 0))
        u = helper.cross(t).normalized()
        frames.append((p, u, t.cross(u), run))
    lay = radius*.52
    for s in range(strands):
        phase = TAU*s/strands
        line = [p + lay*(u*math.cos(phase+TAU*twist*r) + v*math.sin(phase+TAU*twist*r))
                for p, u, v, r in frames]
        builder.tube(line, radius*.62, material, sides=sides)
    return run


def cloth_sheet(builder, nx, ny, fn, material, thickness=.0012):
    """Two-sided cloth: the parametric surface plus an offset copy, joined at the border."""
    top = [[Vector(fn(i/nx, j/ny)) for i in range(nx+1)] for j in range(ny+1)]
    verts, faces = [], []
    for sign in (1, -1):
        for j in range(ny+1):
            for i in range(nx+1):
                du = top[j][min(i+1, nx)] - top[j][max(i-1, 0)]
                dv = top[min(j+1, ny)][i] - top[max(j-1, 0)][i]
                n = du.cross(dv)
                n = n.normalized() if n.length > 1e-9 else Vector((0, 0, 1))
                verts.append(top[j][i] + n*thickness*.5*sign)
    stride = (nx+1)*(ny+1)
    for j in range(ny):
        for i in range(nx):
            a = j*(nx+1)+i
            faces.append((a, a+1, a+nx+2, a+nx+1))
            faces.append((stride+a, stride+a+nx+1, stride+a+nx+2, stride+a+1))
    for i in range(nx):
        faces.append((i, stride+i, stride+i+1, i+1))
        b = ny*(nx+1)+i
        faces.append((b, b+1, stride+b+1, stride+b))
    for j in range(ny):
        a = j*(nx+1)
        faces.append((a, a+nx+1, stride+a+nx+1, stride+a))
        b = j*(nx+1)+nx
        faces.append((b, stride+b, stride+b+nx+1, b+nx+1))
    builder.add(verts, faces, material)
