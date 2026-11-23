"""The tether, the sickle and the peg for the Halwai's neighbour scene.

The row in Ramesh's list: "रस्सी काटते समय हाथ, रस्सी और गाय का आकार आपस में मेल खाएँ"
(when she cuts the rope, her hands, the rope and the cow must match in scale).
Everything here is built at real size in metres against the sculpted cow
(cattle.py) and her 1.54 m rig:

* Rope: 3-strand twisted jute, 14 mm across (a guess: common village tether
  rope is 12 to 16 mm), a loop around the cow's neck closed with a knot, and a
  lead to the peg with two turns and a hitch. A cut version splits the lead a
  hand's width from the knot, with frayed, splayed strand ends.
* Sickle (हँसिया): a serrated crescent blade about 27 cm along the chord on a
  turned wooden handle, the field sickle used for fodder.
* Peg (खूँटा): a rough split-wood stake, 6 cm across, standing 45 cm proud.
"""

from __future__ import annotations

import math
import random
from typing import List, Optional, Sequence, Tuple

import bpy
from mathutils import Quaternion, Vector

ROPE_DIAMETER = .014
PITCH = ROPE_DIAMETER*3.6          # lay length of one strand turn
STRAND_R = ROPE_DIAMETER*.232      # three strands packed in the rope circle
STRAND_OFFSET = ROPE_DIAMETER*.268
PEG_TOP = .45
PEG_RADIUS = .030
PEG_AT = Vector((.42, -1.95, 0))    # in front of the cow, to her left
CUT_FROM_KNOT = .11                # where the sickle parts the lead (a hand's width from the knot)

Point = Tuple[float, float, float]


# ------------------------------------------------------------------ materials

def jute_material(name: str = 'Jute rope'):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nodes, links = m.node_tree.nodes, m.node_tree.links
    shader = nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value = .86
    shader.inputs['Sheen Weight'].default_value = .25
    shader.inputs['Sheen Roughness'].default_value = .45
    shader.inputs['Sheen Tint'].default_value = (.85, .70, .48, 1)   # fuzz takes the jute colour, not white
    uv = nodes.new('ShaderNodeUVMap')
    uv.uv_map = 'RopeUV'
    fibres = nodes.new('ShaderNodeTexWave')
    fibres.label = 'Fibres along the strand'
    fibres.wave_type = 'BANDS'
    fibres.bands_direction = 'Y'
    fibres.inputs['Scale'].default_value = 42
    fibres.inputs['Distortion'].default_value = 6
    fibres.inputs['Detail'].default_value = 4
    links.new(uv.outputs['UV'], fibres.inputs['Vector'])
    dirt = nodes.new('ShaderNodeTexNoise')
    dirt.inputs['Scale'].default_value = 60
    colour = nodes.new('ShaderNodeValToRGB')
    colour.color_ramp.elements[0].color = (.20, .135, .065, 1)
    colour.color_ramp.elements[1].color = (.47, .345, .18, 1)
    mix = nodes.new('ShaderNodeMix')
    mix.data_type = 'FLOAT'
    mix.inputs['Factor'].default_value = .35
    links.new(fibres.outputs['Fac'], mix.inputs['A'])
    links.new(dirt.outputs['Fac'], mix.inputs['B'])
    links.new(mix.outputs['Result'], colour.inputs['Fac'])
    links.new(colour.outputs['Color'], shader.inputs['Base Color'])
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .55
    bump.inputs['Distance'].default_value = .0004
    links.new(fibres.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    m.diffuse_color = (.40, .29, .15, 1)
    return m


def principled(name: str, rgb, rough: float, metal: float = 0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    shader = m.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*rgb, 1)
    shader.inputs['Roughness'].default_value = rough
    shader.inputs['Metallic'].default_value = metal
    m.diffuse_color = (*rgb, 1)
    return m


def wood_material(name: str, light, dark, scale: float = 1.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nodes, links = m.node_tree.nodes, m.node_tree.links
    shader = nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value = .72
    coords = nodes.new('ShaderNodeTexCoord')
    stretch = nodes.new('ShaderNodeMapping')
    stretch.inputs['Scale'].default_value = (30*scale, 30*scale, 2.2*scale)
    links.new(coords.outputs['Object'], stretch.inputs['Vector'])
    grain = nodes.new('ShaderNodeTexWave')
    grain.wave_type = 'RINGS'
    grain.inputs['Scale'].default_value = 3
    grain.inputs['Distortion'].default_value = 9
    grain.inputs['Detail'].default_value = 6
    links.new(stretch.outputs['Vector'], grain.inputs['Vector'])
    ramp = nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*dark, 1)
    ramp.color_ramp.elements[1].color = (*light, 1)
    links.new(grain.outputs['Fac'], ramp.inputs['Fac'])
    links.new(ramp.outputs['Color'], shader.inputs['Base Color'])
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .35
    bump.inputs['Distance'].default_value = .0006
    links.new(grain.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    m.diffuse_color = (*light, 1)
    return m


def steel_material():
    m = bpy.data.materials.get('Sickle steel')
    if m:
        return m
    m = bpy.data.materials.new('Sickle steel')
    m.use_nodes = True
    nodes, links = m.node_tree.nodes, m.node_tree.links
    shader = nodes.get('Principled BSDF')
    shader.inputs['Metallic'].default_value = 1
    attribute = nodes.new('ShaderNodeAttribute')
    attribute.attribute_name = 'Edge wear'          # 1 on the sharpened, bright edge
    rust = nodes.new('ShaderNodeTexNoise')
    rust.inputs['Scale'].default_value = 90
    rust.inputs['Detail'].default_value = 8
    patina = nodes.new('ShaderNodeValToRGB')
    patina.color_ramp.elements[0].color = (.06, .05, .045, 1)
    patina.color_ramp.elements[1].color = (.20, .17, .14, 1)
    links.new(rust.outputs['Fac'], patina.inputs['Fac'])
    colour = nodes.new('ShaderNodeMix')
    colour.data_type = 'RGBA'
    colour.inputs['B'].default_value = (.62, .62, .60, 1)
    links.new(attribute.outputs['Fac'], colour.inputs['Factor'])
    links.new(patina.outputs['Color'], colour.inputs['A'])
    links.new(colour.outputs['Result'], shader.inputs['Base Color'])
    rough = nodes.new('ShaderNodeMix')
    rough.data_type = 'FLOAT'
    rough.inputs['A'].default_value = .62
    rough.inputs['B'].default_value = .22
    links.new(attribute.outputs['Fac'], rough.inputs['Factor'])
    links.new(rough.outputs['Result'], shader.inputs['Roughness'])
    m.diffuse_color = (.2, .18, .16, 1)
    return m


# ------------------------------------------------------------------ geometry helpers

def resample(path: Sequence[Vector], step: float) -> List[Vector]:
    """Evenly spaced points along a polyline (Catmull-Rom smoothed)."""
    pts = [Vector(p) for p in path]
    dense: List[Vector] = []
    for i in range(len(pts) - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, len(pts) - 1)]
        for k in range(8):
            t = k/8
            dense.append(.5*((2*p1) + (-p0 + p2)*t + (2*p0 - 5*p1 + 4*p2 - p3)*t*t + (-p0 + 3*p1 - 3*p2 + p3)*t**3))
    dense.append(pts[-1])
    out = [dense[0]]
    carry = 0.0
    for a, b in zip(dense, dense[1:]):
        seg = (b - a).length
        while carry + seg >= step and seg > 0:
            t = (step - carry)/seg
            a = a + (b - a)*t
            seg = (b - a).length
            out.append(a.copy())
            carry = 0.0
        carry += seg
    if (out[-1] - dense[-1]).length > step*.3:
        out.append(dense[-1])
    return out


def frames(points: Sequence[Vector]) -> List[Tuple[Vector, Vector, Vector]]:
    """Parallel-transport frames (tangent, normal, binormal) along a path."""
    result = []
    tangent = (points[1] - points[0]).normalized()
    normal = tangent.orthogonal().normalized()
    for i in range(len(points)):
        nxt = points[min(i + 1, len(points) - 1)]
        prv = points[max(i - 1, 0)]
        new_t = (nxt - prv).normalized()
        rot = tangent.rotation_difference(new_t)
        normal = (rot @ normal)
        normal = (normal - new_t*normal.dot(new_t)).normalized()
        tangent = new_t
        result.append((tangent, normal, tangent.cross(normal)))
    return result


def new_object(name: str, verts, faces, material, collection, uv: Optional[List[Tuple[float, float]]] = None,
               uv_name: str = 'UVMap'):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(v) for v in verts], [], faces)
    mesh.update()
    mesh.materials.append(material)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    if uv is not None:
        layer = mesh.uv_layers.new(name=uv_name)
        for loop in mesh.loops:
            layer.data[loop.index].uv = uv[loop.vertex_index]
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


# ------------------------------------------------------------------ rope

def strand_tubes(points: Sequence[Vector], fray_start: Optional[float] = None, fray_end: Optional[float] = None,
                 sides: int = 10, phase: float = 0.0):
    """Three twisted strands along a path. fray_*: length over which an end unlays and splays apart."""
    verts: List[Vector] = []
    faces: List[Tuple[int, int, int, int]] = []
    uvs: List[Tuple[float, float]] = []
    fr = frames(points)
    lengths = [0.0]
    for a, b in zip(points, points[1:]):
        lengths.append(lengths[-1] + (b - a).length)
    total = lengths[-1]
    ends = []
    for k in range(3):
        start = len(verts)
        tip_centres = []
        for i, (p, (t, n, b)) in enumerate(zip(points, fr)):
            s = lengths[i]
            loosen = 0.0
            if fray_start is not None and s < fray_start:
                loosen = max(loosen, 1 - s/fray_start)
            if fray_end is not None and total - s < fray_end:
                loosen = max(loosen, 1 - (total - s)/fray_end)
            angle = math.tau*s/PITCH + math.tau*k/3 + phase
            angle -= loosen*loosen*1.8                        # the lay opens toward a cut end
            offset = STRAND_OFFSET*(1 + 1.6*loosen**1.5)
            centre = p + (n*math.cos(angle) + b*math.sin(angle))*offset
            radius = STRAND_R*(1 - .25*loosen)
            # strand axis tilts with the lay: rings face along the helix
            for j in range(sides):
                a = math.tau*j/sides
                verts.append(centre + (n*math.cos(a) + b*math.sin(a))*radius)
                uvs.append((j/sides, s/.03))
            tip_centres.append(centre)
        rows = len(points)
        for i in range(rows - 1):
            for j in range(sides):
                q = (j + 1) % sides
                faces.append((start + i*sides + j, start + i*sides + q, start + (i + 1)*sides + q, start + (i + 1)*sides + j))
        faces.append(tuple(range(start + sides - 1, start - 1, -1)))
        faces.append(tuple(range(start + (rows - 1)*sides, start + rows*sides)))
        ends.append((tip_centres[0], tip_centres[-1]))
    return verts, faces, uvs, ends


def fray_fibres(collection, material, tip: Vector, direction: Vector, rand: random.Random, count: int = 70,
                name: str = 'Rope fray') -> None:
    """Loose jute fibres splaying out of a cut strand end (thin triangular ribbons)."""
    verts, faces = [], []
    direction = direction.normalized()
    side = direction.orthogonal().normalized()
    for _ in range(count):
        spread = Quaternion(direction, rand.uniform(0, math.tau)) @ side
        bend = rand.uniform(.15, .65)
        length = rand.uniform(.010, .032)
        root = tip + spread*rand.uniform(0, STRAND_R*.9)
        path = [root + (direction*(1 - bend*t) + spread*bend*t)*length*t
                + Vector((0, 0, -.004*t*t*rand.random())) for t in (0, .33, .66, 1)]
        width = rand.uniform(.00012, .00022)
        base = len(verts)
        for i, p in enumerate(path):
            w = width*(1 - i/len(path))
            verts += [p + spread.cross(direction)*w, p - spread.cross(direction)*w]
        for i in range(len(path) - 1):
            a = base + 2*i
            faces.append((a, a + 1, a + 3, a + 2))
    new_object(name, verts, faces, material, collection)


def knot_path(at: Vector, along: Vector, up: Vector, size: float) -> List[Vector]:
    """An overhand knot (trefoil) centred at `at`, entering and leaving along `along`."""
    along = along.normalized()
    up = (up - along*up.dot(along)).normalized()
    side = along.cross(up)
    points = []
    for k in range(73):
        t = -math.pi + math.tau*k/72
        x = math.sin(t) + 2*math.sin(2*t)
        y = math.cos(t) - 2*math.cos(2*t)
        z = -math.sin(3*t)
        points.append(at + (along*y*.55 + side*x*.55 + up*z*.6)*size)
    return points


def lead_path(start: Vector, peg: Vector, sag: float = .10) -> List[Vector]:
    """The lead from the knot to the peg: a catenary-like sag, then two turns and a hitch round the peg."""
    top = peg + Vector((0, 0, PEG_TOP - .10))
    points = []
    for k in range(25):
        t = k/24
        p = start.lerp(top, t)
        p.z -= sag*4*t*(1 - t)
        points.append(p)
    r = PEG_RADIUS + ROPE_DIAMETER*.5
    a0 = math.atan2((start - top).y, (start - top).x)
    for k in range(1, 49):
        a = a0 + math.tau*2*k/48
        points.append(peg + Vector((r*math.cos(a), r*math.sin(a), PEG_TOP - .10 - .018*k/48*2)))
    end = points[-1]
    points.append(end + Vector((math.cos(a0)*.03, math.sin(a0)*.03, -.01)))
    points.append(end + Vector((math.cos(a0)*.06, math.sin(a0)*.05, -.07)))
    return points


def build_tether(cow, collection, cut: bool = False, peg: Vector = PEG_AT) -> dict:
    """The tether on the sculpted cow. Returns the parts and the cut point (for her hands and the blade)."""
    import cattle
    rand = random.Random(7)
    jute = jute_material()
    loop = cattle.neck_loop(cow, slack=ROPE_DIAMETER*.55)
    lowest = min(range(len(loop)), key=lambda i: loop[i].z - .3*loop[i].x)   # under the throat, toward the peg (cow's left)
    loop = loop[lowest:] + loop[:lowest]
    knot_at = loop[0] + Vector((.010, -.006, -.020))
    out = (peg - knot_at)
    out.z = 0
    knot = knot_path(knot_at, out, Vector((0, 0, 1)), ROPE_DIAMETER*1.5)   # turns just touch (1.5 cm apart), about 6 cm across
    loop_path = loop + [loop[0]] + knot
    lead = lead_path(knot[-1], peg)
    whole = resample(loop_path + lead[1:], .0025)
    # where the sickle parts the lead: CUT_FROM_KNOT along the lead from the knot
    lengths = [0.0]
    for a, b in zip(whole, whole[1:]):
        lengths.append(lengths[-1] + (b - a).length)
    knot_end = len(resample(loop_path, .0025))
    target = lengths[min(knot_end, len(lengths) - 1)] + CUT_FROM_KNOT
    cut_index = next(i for i, s in enumerate(lengths) if s >= target)
    cut_point = whole[cut_index]
    cut_dir = (whole[cut_index + 1] - whole[cut_index - 1]).normalized()
    parts = {}
    if not cut:
        v, f, uv, _ = strand_tubes(whole)
        parts['rope'] = new_object('Tether rope', v, f, jute, collection, uv, 'RopeUV')
    else:
        gap = .006
        a_pts = [p for p, s in zip(whole, lengths) if s <= target - gap]
        b_pts = [p for p, s in zip(whole, lengths) if s >= target + gap]
        # the cut lead falls a little: the freed end drops toward the ground
        drop = []
        for i, p in enumerate(b_pts):
            t = max(0.0, 1 - i/120)
            drop.append(p + Vector((0, 0, -.05*t*t)))
        va, fa, uva, ends_a = strand_tubes(a_pts, fray_end=.035)
        vb, fb, uvb, ends_b = strand_tubes(drop, fray_start=.035)
        parts['loop'] = new_object('Tether loop (cut)', va, fa, jute, collection, uva, 'RopeUV')
        parts['lead'] = new_object('Tether lead (cut)', vb, fb, jute, collection, uvb, 'RopeUV')
        for k, (_, tip) in enumerate(ends_a):
            fray_fibres(collection, jute, tip, cut_dir, rand, name=f'Rope fray loop {k+1}')
        for k, (tip, _) in enumerate(ends_b):
            fray_fibres(collection, jute, tip, -cut_dir, rand, name=f'Rope fray lead {k+1}')
    parts['cut_point'] = cut_point
    parts['cut_direction'] = cut_dir
    parts['knot'] = knot_at
    return parts


def parent_loop_to_neck(cow, obj) -> None:
    """The neck loop rides the cow's neck bone, so it stays on her when she moves her head."""
    world = obj.matrix_world.copy()
    obj.parent = cow.rig
    obj.parent_type = 'BONE'
    obj.parent_bone = 'neck_2'
    bpy.context.view_layer.update()
    obj.matrix_world = world                     # keeps it where it was, now riding the bone


# ------------------------------------------------------------------ sickle

def build_sickle(collection, name: str = 'Sickle') -> bpy.types.Object:
    """A हँसिया in its own frame: handle along -y from the origin (the grip centre), blade curving forward.

    Origin: the centre of the grip; the blade lies in the x-y plane, cutting edge on the inside of the curve.
    """
    steel = steel_material()
    handle_m = wood_material('Sickle handle sheesham', (.30, .16, .08), (.12, .055, .025), 3.0)
    ferrule_m = principled('Sickle ferrule iron', (.22, .20, .18), .45, 1.0)
    # blade: a crescent of 125 degrees, outer radius 13 cm, width 3.2 cm at the heel tapering to the point
    centre = Vector((-.105, .065, 0))
    outer_r = .135
    verts, faces, wear = [], [], []
    columns, rows = 60, 5
    a0, a1 = math.radians(-35), math.radians(92)
    for i in range(columns + 1):
        t = i/columns
        a = a0 + (a1 - a0)*t
        width = (.032*(1 - t)**.65 + .002)*(.30 + .70*smooth01(0.0, .09, t))   # narrows to a neck at the heel
        for j in range(rows):
            u = j/(rows - 1)
            r = outer_r - width*u
            # serrations on the inner (cutting) edge
            if j == rows - 1:
                r += .0005*(1 if i % 2 else -1)*(1 - t*.5)
            thickness = .0022*(1 - u*.85)
            for side in (1, -1):
                verts.append(centre + Vector((math.cos(a)*r, math.sin(a)*r, side*thickness*.5)))
                wear.append(smooth01(.55, 1.0, u))
    stride = rows*2
    for i in range(columns):
        for j in range(rows - 1):
            for side in (0, 1):
                a = i*stride + j*2 + side
                b = a + 2
                c = b + stride
                d = a + stride
                faces.append((a, b, c, d) if side == 0 else (a, d, c, b))
        # outer back and inner edge walls
        a = i*stride
        faces.append((a, a + stride, a + stride + 1, a + 1))
        e = i*stride + (rows - 1)*2
        faces.append((e, e + 1, e + stride + 1, e + stride))
    blade = new_object(f'{name} blade', verts, faces, steel, collection)
    layer = blade.data.color_attributes.new('Edge wear', 'FLOAT_COLOR', 'POINT')
    for k, w in enumerate(wear):
        layer.data[k].color = (w, w, w, 1)
    # ferrule on the handle, the blade's heel neck driven into it
    grip_top = Vector((0, .010, 0))
    handle_verts, handle_faces = lathe([(0.0, .010), (.0125, .010), (.0135, .0), (.0150, -.030), (.0145, -.070),
                                        (.0130, -.100), (.0142, -.108), (.0090, -.112), (0.0, -.112)], 18)
    handle = new_object(f'{name} handle', handle_verts, handle_faces, handle_m, collection)
    ferrule_verts, ferrule_faces = lathe([(0.0, .022), (.0105, .022), (.0128, .016), (.0128, .008),
                                          (.0118, .006), (0.0, .006)], 18)
    ferrule = new_object(f'{name} ferrule', ferrule_verts, ferrule_faces, ferrule_m, collection)
    heel = centre + Vector((math.cos(a0)*(outer_r - .005), math.sin(a0)*(outer_r - .005), 0))
    shift = grip_top + Vector((0, .004, 0)) - heel   # the heel neck goes into the ferrule
    for v in blade.data.vertices:
        v.co += shift
    tang_verts, tang_faces = lathe([(0.0, .004), (.0034, .004), (.0034, .024), (0.0, .024)], 8)   # hidden in the ferrule
    tang = new_object(f'{name} tang', tang_verts, tang_faces, steel, collection)
    root = bpy.data.objects.new(name, None)
    root.empty_display_type = 'ARROWS'
    root.empty_display_size = .05
    collection.objects.link(root)
    for obj in (blade, handle, ferrule, tang):
        obj.parent = root
    root['Usage'] = 'Origin at the centre of the grip; parent to the hand bone and rotate to taste.'
    return root


def smooth01(a: float, b: float, x: float) -> float:
    t = max(0.0, min(1.0, (x - a)/(b - a)))
    return t*t*(3 - 2*t)


def lathe(profile: Sequence[Tuple[float, float]], sides: int) -> Tuple[List[Vector], List[Tuple[int, ...]]]:
    """A turned part along y from (radius, y) pairs."""
    verts, faces = [], []
    for r, y in profile:
        for k in range(sides):
            a = math.tau*k/sides
            verts.append(Vector((r*math.cos(a), y, r*math.sin(a))))
    for i in range(len(profile) - 1):
        for k in range(sides):
            n = (k + 1) % sides
            faces.append((i*sides + k, i*sides + n, (i + 1)*sides + n, (i + 1)*sides + k))
    return verts, faces


# ------------------------------------------------------------------ peg

def build_peg(collection, at: Vector = PEG_AT, name: str = 'Peg') -> bpy.types.Object:
    """A खूँटा: a split-wood stake driven into packed earth, worn smooth where the rope rubs."""
    rand = random.Random(11)
    wood = wood_material('Weathered peg wood', (.36, .29, .21), (.16, .12, .085), 1.4)
    rows, sides = 40, 20
    bumps = [(rand.uniform(0, math.tau), rand.uniform(.08, .2), rand.randint(2, 5)) for _ in range(4)]
    verts, faces = [], []
    for i in range(rows + 1):
        z = -.05 + (PEG_TOP + .05)*i/rows
        top = z > PEG_TOP - .03
        for k in range(sides):
            a = math.tau*k/sides
            r = PEG_RADIUS
            for phase, amount, freq in bumps:
                r *= 1 + amount*.18*math.sin(freq*a + phase + z*7)
            if top:                                         # split, battered top
                r *= 1 - .25*smooth01(PEG_TOP - .03, PEG_TOP, z)
            verts.append(at + Vector((r*math.cos(a), r*math.sin(a), z + (.006*math.sin(3*a) if i == rows else 0))))
    for i in range(rows):
        for k in range(sides):
            n = (k + 1) % sides
            faces.append((i*sides + k, i*sides + n, (i + 1)*sides + n, (i + 1)*sides + k))
    faces.append(tuple(range(rows*sides, (rows + 1)*sides)))
    peg = new_object(name, verts, faces, wood, collection)
    # a mound of packed earth around the foot
    earth = principled('Packed earth', (.20, .15, .10), .95)
    mound_v, mound_f = [], []
    for i in range(9):
        r = PEG_RADIUS + .12*i/8
        for k in range(24):
            a = math.tau*k/24
            h = .022*(1 - i/8)**2 - .010*(i/8)**2 + .002*rand.random()   # sinks into the ground at its rim
            mound_v.append(at + Vector((r*math.cos(a), r*math.sin(a), h)))
    for i in range(8):
        for k in range(24):
            n = (k + 1) % 24
            mound_f.append((i*24 + k, i*24 + n, (i + 1)*24 + n, (i + 1)*24 + k))
    mound = new_object(f'{name} earth', mound_v, mound_f, earth, collection)
    mound.parent = peg
    return peg
