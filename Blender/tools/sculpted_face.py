"""Realistic sculpted heads for the cast, built as a volume.

The shared cast face is a revolved profile with eyes and lips laid on it like
decals, which reads as stylized. Here the head is a signed-distance sculpt
(skull, brow, cheekbones, jaw, chin, a nose with open nostrils, full lips with a
parted mouth line) meshed with surface nets, plus:

* real eyeballs (sclera, a recessed iris with a pupil, a clear corneal bulge),
* eyelids that are part of the head shell, with a real margin, crease and fold,
* lash lines, tear lines and caruncles, a brow band, teeth and a tongue,
* blink shape keys on the head itself.

Usage::

    face = SculptedFace(c, FaceSpec())          # or ADULT_MAN, or your own FaceSpec
    head = face.head_mesh(c.m['skin'])
    face.build_eyes(head)
    skin_shading(c)
    face.paint_head(head)
    face.brow_strips(brow_material)
    face.mouth_lining(mouth_material)
    ...                                          # facial_controls.add_facial_controls(c)
    face.eyelid_blinks(); face.head_blinks(head); face.teeth_and_tongue()

Sizes. Every design value is in *canonical* metres: the Halwai's neighbour, a
1.54 m woman (Character height factor CANON_HEIGHT). A SculptedFace scales the
whole head by size = c.scale / CANON_HEIGHT on the way out, so a 1.70 m
character of the same 7.3-head proportions gets a head 10 % larger whose neck
lands on his body. Every position the class hands back (eye_centre,
margin_curve, brow_curve, on_skin, tree hits) is canonical; multiply by
face.size, and divide by c.scale for c.mesh(), to place things in the scene.

Shapes. FaceSpec holds how a head differs from hers. All defaults reproduce
her face exactly; ADULT_MAN is a starting point for grown men.

Object names match the shared facial-controls contract (Head, Eye.X, Iris.X,
Eyelids.X, Brow.X, Mouth).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from sdf_sculpt import Sculpt, capsule, ellipsoid, sphere, surface_nets, taubin

Array = np.ndarray
Point = Tuple[float, float, float]
RGB = Tuple[float, float, float]
Volume = Tuple[Point, Point, float]          # ellipsoid centre, radii, dental-arch bend

# ------------------------------------------------- canonical landmarks (m)
CANON_HEIGHT = .868    # Character height factor of the head these values describe (1.54 m)
TOP = 1.540            # vertex of the skull
EYE_Z = 1.4370         # pupil height
EYE_X = .0310          # half the interpupillary distance (6.2 cm)
EYE_Y = -.0555         # eyeball centre depth
EYE_R = .0121          # eyeball radius
MOUTH_Z = 1.3742       # stomion at the centre
MOUTH_HALF = .0226     # half the width of the mouth opening
NASION = (0.0, -.0728, 1.4440)
ARCH = 1/(2*.027)      # lips and teeth follow the dental arch: y += ARCH*x²
STEP = .00062          # voxel size of the head sculpt

# Palpebral fissure in eye-centred angles (degrees): azimuth is lateral-positive.
A_IN, B_IN = -74.0, -1.5
A_OUT, B_OUT = 70.0, 4.5
H_UP, PEAK_UP, ROUND_UP = 20.3, .44, .85
H_LOW, PEAK_LOW, ROUND_LOW = 28.1, .57, 1.0
CENTRE_A, CENTRE_B = -2.0, -2.0

UPPER_LID_T = .00135   # lid thickness beyond the support sphere
LOWER_LID_T = .00118
LIMBUS = .0059
PUPIL = .0019
CORNEA_R = .0078

BROW = ((.0135, 1.4500), (.0225, 1.4560), (.0325, 1.4597), (.0425, 1.4597), (.0515, 1.4566), (.0575, 1.4522))


@dataclass(frozen=True)
class FaceSpec:
    """How a sculpted head differs from the neighbour's. Defaults reproduce her face.

    Factors scale a feature (1.0 = hers); offsets are canonical metres; 0..1
    amounts blend in a feature she does not have.
    """
    eye_size: float = 1.0          # eyeball radius. Adult eyes barely grow with stature: use <1 on taller cast
    eye_spacing: float = 1.0       # interpupillary width
    eye_depth: float = 0.0         # metres deeper set (+)
    eye_open: float = 1.0          # height of the lid opening (lower reads hooded)
    brow_ridge: float = 0.0        # 0 soft; 1 a male supraorbital bar with lower, straighter brows
    forehead_slope: float = 0.0    # 0 upright; 1 sloped back
    cheek_fat: float = 1.0         # malar and buccal fullness (youth)
    jaw_width: float = 1.0
    jaw_mass: float = 1.0          # thickness of the mandible
    chin: float = 1.0              # chin height and forward projection
    chin_width: float = 1.0
    nose_length: float = 1.0
    nose_width: float = 1.0
    nose_projection: float = 1.0
    lip_fullness: float = 1.0
    mouth_width: float = 1.0
    neck: float = 1.0              # neck thickness
    adams_apple: float = 0.0
    lip_colour: RGB = (.315, .125, .098)
    beard_shadow: float = 0.0      # stubble tint on jaw, chin and upper lip


NEIGHBOUR = FaceSpec()

# A starting point for grown men of about 1.65 to 1.75 m. A guess, to be tuned against the reference.
ADULT_MAN = FaceSpec(eye_size=.91, eye_spacing=.94, eye_depth=.0012, eye_open=.88, brow_ridge=1.0,
                     forehead_slope=.6, cheek_fat=.55, jaw_width=1.10, jaw_mass=1.22, chin=1.15,
                     chin_width=1.30, nose_length=1.03, nose_width=1.10, nose_projection=1.02,
                     lip_fullness=.80, mouth_width=1.0, neck=1.20, adams_apple=1.0,
                     lip_colour=(.255, .118, .092), beard_shadow=.55)


# ----------------------------------------------------------------- helpers

def smooth(a: float, b: float, x):
    t = np.clip((x - a)/(b - a), 0, 1)
    return t*t*(3 - 2*t)


def _bump(t, peak: float, roundness: float):
    a = math.log(.5)/math.log(peak)
    return np.maximum(np.sin(math.pi*np.clip(t, 0, 1)**a), 0)**roundness


def eye_direction(alpha, beta, sign: int) -> Array:
    a, b = np.radians(alpha), np.radians(beta)
    return np.stack([sign*np.sin(a)*np.cos(b), -np.cos(a)*np.cos(b), np.sin(b)], axis=-1)


def _sign_frame(sign: int) -> Tuple[Array, Array, Array]:
    return np.array([sign, 0., 0.]), np.array([0., -1., 0.]), np.array([0., 0., 1.])


def _gauss(p: Array, centre: Sequence[float], radii: Sequence[float]) -> Array:
    d = sum(((p[:, i] - centre[i])/radii[i])**2 for i in range(3))
    return np.exp(-d)


def face_away(obj, centre: Sequence[float]) -> None:
    """Make the winding consistent and the normals point away from a centre (scene coordinates)."""
    mesh = obj.data
    centre = Vector(centre)
    votes = sum((p.center - centre).dot(p.normal)*p.area for p in mesh.polygons)
    if votes < 0:
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()


def set_weights(obj, weights: Dict[str, Array]) -> None:
    """Replace vertex groups with per-vertex weight arrays, batched by value."""
    obj.vertex_groups.clear()
    for name, values in weights.items():
        group = obj.vertex_groups.new(name=name)
        q = np.round(np.asarray(values)*64).astype(int)
        for level in np.unique(q):
            if level <= 0:
                continue
            group.add(np.nonzero(q == level)[0].tolist(), float(level)/64, 'REPLACE')


def mesh_coords(mesh) -> Array:
    co = np.empty(len(mesh.vertices)*3)
    mesh.vertices.foreach_get('co', co)
    return co.reshape(-1, 3)


def face_detail(co: Array) -> Array:
    """1 on the face (kept at full density), 0 on the skull, nape and neck. Canonical coordinates."""
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    return smooth(.000, -.030, y)*smooth(1.318, 1.335, z)*smooth(1.500, 1.480, z)*smooth(.068, .056, np.abs(x))


def decimate_away_from_face(obj, size: float, ratio: float = .38) -> None:
    """Thin out the skull, nape and neck (under hair and cloth) and keep the face at full density."""
    keep = face_detail(mesh_coords(obj.data)/size)
    group = obj.vertex_groups.new(name='Face detail')
    q = np.round(keep*32).astype(int)
    for level in np.unique(q):
        if level > 0:
            group.add(np.nonzero(q == level)[0].tolist(), float(level)/32, 'REPLACE')
    skin = obj.modifiers.get('Character Skinning')
    if skin:
        skin.show_viewport = False
    modifier = obj.modifiers.new('Decimate away from face', 'DECIMATE')
    modifier.ratio = ratio
    modifier.vertex_group = group.name
    modifier.vertex_group_factor = 200
    modifier.invert_vertex_group = True     # weight 1 = keep; Blender collapses high weights first
    modifier.use_symmetry = True
    modifier.symmetry_axis = 'X'
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
    old = obj.data
    obj.modifiers.remove(modifier)
    obj.data = mesh
    mesh.name = old.name
    bpy.data.meshes.remove(old)
    if skin:
        skin.show_viewport = True
    obj.vertex_groups.remove(obj.vertex_groups['Face detail'])
    relax_decimated(mesh, size)
    for polygon in mesh.polygons:
        polygon.use_smooth = True


def _folded(bm: bmesh.types.BMesh) -> List[bmesh.types.BMFace]:
    """Faces turned against their own corner normals: folds left by edge collapse."""
    bm.normal_update()
    return [f for f in bm.faces
            if f.normal.dot(sum((v.normal for v in f.verts), Vector())) < 0]


def relax_decimated(mesh, size: float) -> None:
    """Even out the collapsed region and merge any triangle that folded over, so SSS shows no dark specks."""
    bm = bmesh.new()
    bm.from_mesh(mesh)
    keep = face_detail(np.array([v.co for v in bm.verts])/size)
    loose = [v for v, k in zip(bm.verts, keep) if k < .5 and not v.is_boundary]
    for _ in range(4):
        bmesh.ops.smooth_vert(bm, verts=loose, factor=.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    for _ in range(6):
        folds = _folded(bm)
        if not folds:
            break
        for face in folds:
            if face.is_valid:
                corners = list(face.verts)
                centre = sum((v.co for v in corners), Vector())/len(corners)
                bmesh.ops.pointmerge(bm, verts=corners, merge_co=centre)
        bmesh.ops.dissolve_degenerate(bm, dist=1e-7, edges=bm.edges)
    folds = _folded(bm)
    if folds:                       # a sliver around a fan hub: turning it is enough for shading
        bmesh.ops.reverse_faces(bm, faces=folds)
    bm.to_mesh(mesh)
    bm.free()


# ------------------------------------------------------------- materials

def principled(name: str, rgb: RGB, rough: float, **inputs: float):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    shader = material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*rgb, 1)
    shader.inputs['Roughness'].default_value = rough
    for key, value in inputs.items():
        shader.inputs[key.replace('_', ' ')].default_value = value
    material.diffuse_color = (*rgb, 1)
    return material


def color_from_attribute(material, attribute: str) -> None:
    tree = material.node_tree
    node = tree.nodes.new('ShaderNodeAttribute')
    node.attribute_name = attribute
    node.location = (-300, 300)
    tree.links.new(node.outputs['Color'], tree.nodes.get('Principled BSDF').inputs['Base Color'])


def write_colors(obj, name: str, colors: Array) -> None:
    layer = obj.data.color_attributes.new(name, 'FLOAT_COLOR', 'POINT')
    rgba = np.ones((len(colors), 4), dtype=np.float32)
    rgba[:, :3] = colors
    layer.data.foreach_set('color', rgba.ravel())


def grid_faces(rows: int, columns: int, cyclic: bool = True) -> List[Tuple[int, int, int, int]]:
    faces = []
    for r in range(rows - 1):
        for k in range(columns if cyclic else columns - 1):
            n = (k + 1) % columns
            faces.append((r*columns + k, r*columns + n, (r + 1)*columns + n, (r + 1)*columns + k))
    return faces


def _ovoid_into(verts: List[Point], faces: List[Tuple[int, int, int, int]], centre: Sequence[float],
                radii: Sequence[float], columns: int = 16, rows: int = 10) -> None:
    start = len(verts)
    for r in range(rows + 1):
        v = -math.pi/2 + math.pi*r/rows
        for k in range(columns):
            u = math.tau*k/columns
            verts.append((centre[0] + radii[0]*math.cos(v)*math.cos(u),
                          centre[1] + radii[1]*math.cos(v)*math.sin(u),
                          centre[2] + radii[2]*math.sin(v)))
    for r in range(rows):
        for k in range(columns):
            n = (k + 1) % columns
            faces.append((start + r*columns + k, start + r*columns + n,
                          start + (r + 1)*columns + n, start + (r + 1)*columns + k))


def skin_shading(c) -> None:
    """Skin with real subsurface depth, finer pores, tint and glossier lips (shared by all skin parts)."""
    material = c.m['skin']
    tree = material.node_tree
    shader = tree.nodes.get('Principled BSDF')
    shader.inputs['Subsurface Weight'].default_value = 1.0
    shader.inputs['Subsurface Radius'].default_value = (1.0, .40, .22)
    shader.inputs['Subsurface Scale'].default_value = .0032
    shader.inputs['Specular IOR Level'].default_value = .42
    shader.inputs['Coat Weight'].default_value = .0
    try:
        shader.subsurface_method = 'RANDOM_WALK_SKIN'
    except TypeError:
        pass
    for node in tree.nodes:
        if node.type == 'BUMP':
            node.inputs['Strength'].default_value = .16
            node.inputs['Distance'].default_value = .00018
        if node.type == 'TEX_VORONOI':
            node.inputs['Scale'].default_value = 1700
    if not any(n.label == 'Regional skin tint' for n in tree.nodes):
        source = shader.inputs['Base Color'].links[0].from_socket
        tint = tree.nodes.new('ShaderNodeAttribute')
        tint.attribute_name = 'Skin tint'
        tint.label = 'Regional skin tint'
        tint.location = (200, 520)
        add = tree.nodes.new('ShaderNodeVectorMath')
        add.operation = 'MULTIPLY_ADD'
        add.location = (420, 480)
        tree.links.new(source, add.inputs[0])
        tree.links.new(tint.outputs['Color'], add.inputs[1])
        tree.links.new(source, add.inputs[2])
        tree.links.new(add.outputs[0], shader.inputs['Base Color'])
    if not any(n.label == 'Lip and mouth gloss' for n in tree.nodes):
        gloss = tree.nodes.new('ShaderNodeAttribute')
        gloss.attribute_name = 'Skin gloss'
        gloss.label = 'Lip and mouth gloss'
        gloss.location = (200, -40)
        mix = tree.nodes.new('ShaderNodeMix')
        mix.data_type = 'FLOAT'
        mix.location = (420, -20)
        rough = shader.inputs['Roughness']
        source = rough.links[0].from_socket if rough.links else None
        if source:
            tree.links.new(source, mix.inputs['A'])
        else:
            mix.inputs['A'].default_value = rough.default_value
        mix.inputs['B'].default_value = .46
        tree.links.new(gloss.outputs['Fac'], mix.inputs['Factor'])
        tree.links.new(mix.outputs['Result'], rough)
        coat = tree.nodes.new('ShaderNodeMath')
        coat.operation = 'MULTIPLY'
        coat.inputs[1].default_value = .14
        coat.location = (420, -200)
        tree.links.new(gloss.outputs['Fac'], coat.inputs[0])
        tree.links.new(coat.outputs[0], shader.inputs['Coat Weight'])
        shader.inputs['Coat Roughness'].default_value = .25


# ------------------------------------------------------------ the head

class SculptedFace:
    """One character's sculpted head: canonical design, scaled by `size` into the scene."""

    def __init__(self, c, spec: FaceSpec = NEIGHBOUR) -> None:
        self.c = c
        self.spec = spec
        self.size: float = c.scale/CANON_HEIGHT
        self.eye_x = EYE_X*spec.eye_spacing
        self.eye_y = EYE_Y + spec.eye_depth
        self.eye_z = EYE_Z
        self.eye_r = EYE_R*spec.eye_size
        self.h_up = H_UP*spec.eye_open
        self.h_low = H_LOW*(.5 + .5*spec.eye_open)
        self.mouth_half = MOUTH_HALF*spec.mouth_width
        lf, mw = spec.lip_fullness, spec.mouth_width
        self.upper_lip: Volume = ((0, -.0799, MOUTH_Z + .0048*lf), (.0200*mw, .0056*lf, .0055*lf), ARCH)
        self.tubercle: Volume = ((0, -.0838 + .0056*(1 - lf), MOUTH_Z + .0030*lf), (.0056*mw, .0029*lf, .0029*lf), 0.0)
        self.lower_lip: Volume = ((0, -.0797, MOUTH_Z - .0064*lf), (.0185*mw, .0074*lf, .0062*lf), ARCH)
        self.tree: Optional[BVHTree] = None

    # ---------------------------------------------------------- frames

    @property
    def to_scene(self) -> float:
        """Factor from canonical metres to the unscaled coordinates c.mesh() expects."""
        return self.size/self.c.scale

    def final(self, p: Sequence[float]) -> Vector:
        """Canonical point to scene metres."""
        return Vector(p)*self.size

    def canonical(self, mesh) -> Array:
        return mesh_coords(mesh)/self.size

    def to_mesh(self, name: str, verts: Array, faces, material, bone: str = 'head'):
        return self.c.mesh(name, [tuple(v) for v in np.asarray(verts)*self.to_scene], faces, material, bone)

    def nose(self, p: Sequence[float]) -> Point:
        """A point of her nose, stretched about the nasion by the nose factors."""
        s = self.spec
        return (p[0]*s.nose_width, NASION[1] + (p[1] - NASION[1])*s.nose_projection,
                NASION[2] + (p[2] - NASION[2])*s.nose_length)

    def nose_radii(self, r: Sequence[float]) -> Point:
        s = self.spec
        return (r[0]*s.nose_width, r[1]*s.nose_projection, r[2]*s.nose_length)

    def nose_radius(self, r: float) -> float:
        return r*(self.spec.nose_width + self.spec.nose_projection)/2

    # ------------------------------------------------------- eye shape

    def eye_centre(self, sign: int) -> Vector:
        return Vector((sign*self.eye_x, self.eye_y, self.eye_z))

    def lid_upper(self, alpha):
        t = (alpha - A_IN)/(A_OUT - A_IN)
        return B_IN + (B_OUT - B_IN)*np.clip(t, 0, 1) + self.h_up*_bump(t, PEAK_UP, ROUND_UP)

    def lid_lower(self, alpha):
        t = (alpha - A_IN)/(A_OUT - A_IN)
        return B_IN + (B_OUT - B_IN)*np.clip(t, 0, 1) - self.h_low*_bump(t, PEAK_LOW, ROUND_LOW)

    def support_radius(self, alpha):
        """Where the lid margin rests: on the eyeball, lifted at the corners."""
        return self.eye_r + .00035 + .0012*smooth(-50, -74, alpha) + .0004*smooth(45, 70, alpha)

    def eye_angles(self, x, y, z, sign: int):
        dx, dy, dz = x - sign*self.eye_x, y - self.eye_y, z - self.eye_z
        alpha = np.degrees(np.arctan2(sign*dx, -dy))
        beta = np.degrees(np.arctan2(dz, np.sqrt(dx*dx + dy*dy)))
        return alpha, beta, np.sqrt(dx*dx + dy*dy + dz*dz)

    def aperture_distance(self, alpha, beta, grow: float = 0.0):
        """Angular distance (degrees) outside the lid opening; negative inside."""
        lids = np.maximum(self.lid_lower(alpha) - grow - beta, beta - self.lid_upper(alpha) - grow)
        return np.maximum(lids, np.maximum(A_IN - grow - alpha, alpha - A_OUT - grow))

    def lid_shell_field(self, sign: int):
        """Both lids as one shell over the eyeball, out to ~40 degrees past the opening."""
        def field(x, y, z):
            alpha, beta, r = self.eye_angles(x, y, z, sign)
            upper = smooth(CENTRE_B - 6, CENTRE_B + 6, beta)
            outer = self.support_radius(alpha) + LOWER_LID_T + (UPPER_LID_T - LOWER_LID_T)*upper
            zone = np.radians(self.aperture_distance(alpha, beta) - 40)*np.maximum(r, .004)
            return np.maximum(r - outer, zone)
        reach = self.eye_r + .006
        c = self.eye_centre(sign)
        return field, ((c.x - reach, c.y - reach, c.z - reach), (c.x + reach, c.y + .002, c.z + reach))

    def eye_socket_field(self, sign: int):
        """The lid opening, carved through the lid shell in front of the eyeball."""
        def field(x, y, z):
            alpha, beta, r = self.eye_angles(x, y, z, sign)
            angular = np.radians(self.aperture_distance(alpha, beta))*np.maximum(r, .004)
            return np.maximum(angular, r - (self.eye_r + .008))
        reach = self.eye_r + .012
        c = self.eye_centre(sign)
        return field, ((c.x - reach, c.y - reach, c.z - reach), (c.x + reach, c.y + .004, c.z + reach))

    # ------------------------------------------------------ head sculpt

    def sculpt(self) -> Sculpt:
        sp = self.spec
        s = Sculpt()
        # Cranium, forehead and the occiput running into the nape
        slope = sp.forehead_slope
        s.union(ellipsoid((0, .007, 1.452), (.0700, .087, .088)))
        s.union(ellipsoid((0, -.040 + .006*slope, 1.482 - .004*slope), (.050, .042, .040)), .02)   # forehead
        s.union(ellipsoid((0, .040, 1.400), (.046, .036, .034)), .022)          # occiput
        # Neck, leaning forward from the skull to the chest
        thick = sp.neck

        def neck(x, y, z):
            cy = .002 + (z - 1.26)*.09
            flare = smooth(1.322, 1.272, z)
            ax, ay = (.0480 + .0190*flare)*thick, (.0445 + .0060*flare)*thick
            column = (np.sqrt((x/ax)**2 + ((y - cy)/ay)**2) - 1)*ay
            return np.maximum(column, z - 1.43)      # capped inside the skull, so a thick neck leaves no seam
        s.union((neck, ((-.05*thick, -.05*thick, 1.236), (.05*thick, .06*thick, 1.40))), .028)
        for sign in (1, -1):
            s.union(capsule((sign*.041*thick, .020, 1.400), (sign*.013*thick, -.036, 1.262),
                            .0095*thick, .0075*thick), .018)                       # sternomastoid
        if sp.adams_apple > 0:
            front = .0072 - .0446*thick
            a = sp.adams_apple
            s.union(ellipsoid((0, front + .0030, 1.3180), (.0062*a, .0058*a, .0095*a), (-18, 0, 0)), .008)
        # Soft face mass: cheeks and jaw under the fat layer
        fat = sp.cheek_fat
        s.union(ellipsoid((0, -.032, 1.398), (.049, .045, .044)), .020)
        s.union(ellipsoid((0, -.048, 1.392), (.036, .032, .032)), .014)
        for sign in (1, -1):
            s.union(ellipsoid((sign*.042, -.051, 1.417), (.014, .017, .012), (0, 0, sign*-32)), .020)   # zygoma
            malar = .75 + .25*fat
            s.union(ellipsoid((sign*.032, -.0555, 1.4045), (.020*malar, .017*malar, .018*malar)), .018)
            # buccal fat pad: fills the lower cheek between the malar fat and the jaw (no dent or dimple)
            pad = .70 + .30*fat
            s.union(ellipsoid((sign*.0415, -.0445, 1.3825), (.0085*pad, .0145*pad, .0145*pad)), .020)
            s.subtract(ellipsoid((sign*.070, -.034, 1.456), (.006, .018, .015)), .022)             # temple
        # Jaw and chin
        jw, jm, chin, cw = sp.jaw_width, sp.jaw_mass, sp.chin, sp.chin_width
        for sign in (1, -1):
            gonion = (sign*.0352*jw, -.004, 1.3700 - .002*(jm - 1))
            s.union(capsule(gonion, (sign*.0140*cw, -.0605 - .002*(chin - 1), 1.3470 - .004*(chin - 1)),
                            .0110*jm, .0095*jm), .022)
            s.union(capsule(gonion, (sign*.0450*(.5 + .5*jw), .0080, 1.4150), .0100*jm, .0095*jm), .022)
        s.union(ellipsoid((0, -.0650 - .0025*(chin - 1), 1.3500 - .004*(chin - 1)),
                          (.0172*cw, .0128, .0130*(.6 + .4*chin))), .020)
        for sign in (1, -1):            # soft tissue over the chin-jaw junction, so no crease runs from the mouth
            s.union(ellipsoid((sign*.0330*(.5 + .5*jw), -.0480, 1.3600 - .002*(chin - 1)), (.0110, .0130, .0130)), .020)
        # Brow ridge: soft on her, a bar over the eyes on a man
        ridge = sp.brow_ridge
        for sign in (1, -1):
            inner = (sign*.010, -.0728 - .0024*ridge, 1.4545 - .0010*ridge)
            middle = (sign*.040, -.0650 - .0022*ridge, 1.4580 - .0012*ridge)
            outer = (sign*.054, -.0548 - .0010*ridge, 1.4515)
            s.union(capsule(inner, middle, .0050 + .0016*ridge, .0046 + .0016*ridge), .014)
            s.union(capsule(middle, outer, .0046 + .0016*ridge, .0040 + .0008*ridge), .014)
        if ridge > 0:
            s.union(ellipsoid((0, -.0750 - .0012*ridge, 1.4545), (.0110, .0010 + .0035*ridge, .0065)), .010)  # glabella
        # Orbits: hollow out the socket the lids will lie over
        for sign in (1, -1):
            s.subtract(ellipsoid((sign*(self.eye_x + .0002), -.0690 + sp.eye_depth, 1.4378), (.0168, .0098, .0100)), .010)
        # Muzzle and lips (they follow the dental arch)
        mw, lf = sp.mouth_width, sp.lip_fullness
        s.union(ellipsoid((0, -.0615, 1.3785), (.030*(.5 + .5*mw), .0180, .025), bend=ARCH), .010)
        for (centre, radii, bend), k in ((self.upper_lip, .0024), (self.tubercle, .0020), (self.lower_lip, .0026)):
            s.union(ellipsoid(centre, radii, bend=bend), k)
        for sign in (1, -1):
            s.union(capsule((sign*.0036, -.0848, 1.3918), (sign*.0050, -.0852, MOUTH_Z + .0106*lf), .0012, .0014),
                    .0022)                                                                 # philtral columns
            s.subtract(ellipsoid((sign*(self.mouth_half - .0002), -.0712, MOUTH_Z), (.0016, .0024, .0014)), .0022)
            s.subtract(capsule((sign*.0200*sp.nose_width, -.0790, 1.3985), (sign*.0280*mw, -.0718, 1.3720),
                               .0006, .0005), .0040)                                      # nasolabial
        s.subtract(ellipsoid((0, -.0860, 1.3880), (.0028, .0015, .0036)), .0018)            # philtrum
        s.subtract(ellipsoid((0, -.0830, MOUTH_Z - .0164*(.5 + .5*lf)), (.0145*mw, .0040, .0030), bend=ARCH),
                   .0050)                                                                  # mentolabial sulcus
        # Nose, stretched about the nasion by the nose factors
        n, nr, r1 = self.nose, self.nose_radii, self.nose_radius
        s.union(capsule(n((0, -.0728, 1.4440)), n((0, -.0938, 1.4065)), r1(.0058), r1(.0058)), .0060)   # dorsum
        s.union(ellipsoid(n((0, -.0805, 1.4150)), nr((.0108, .0102, .0230)), (-26, 0, 0)), .0070)     # sidewalls
        s.union(ellipsoid(n((0, -.0936, 1.4010)), nr((.0080, .0072, .0066))), .0032)                  # lobule
        for sign in (1, -1):
            s.union(sphere(n((sign*.0034, -.0965, 1.4016)), r1(.0045)), .0022)                          # domes
            s.union(ellipsoid(n((sign*.0106, -.0856, 1.3980)), nr((.0050, .0076, .0055)), (0, 0, sign*22)),
                    .0034)                                                                       # alae
            s.subtract(capsule(n((sign*.0154, -.0842, 1.4050)), n((sign*.0164, -.0822, 1.3938)), .0008, .0008),
                       .0014)                                                                    # alar groove
        s.union(capsule(n((0, -.0946, 1.3950)), n((0, -.0866, 1.3928)), r1(.0030), r1(.0033)), .0022)  # columella
        for sign in (1, -1):
            s.subtract(ellipsoid(n((sign*.0057, -.0884, 1.3890)), nr((.0026, .0046, .0015)), (8, 0, sign*16)),
                       .0007)                                                                    # nostrils
        # Mouth: parted line and an interior
        half = self.mouth_half

        def mouth_line(x, y, z):
            u = np.clip(np.abs(x)/half, 0, 1)
            centre = MOUTH_Z - .0010*u*u
            gap = .00085*np.sqrt(np.maximum(0, 1 - u**1.6))
            yy = y - ARCH*x*x
            depth = np.maximum(-.090 - yy, yy + .062)
            return np.maximum(np.maximum(np.abs(z - centre) - gap, np.abs(x) - half), depth)
        s.subtract((mouth_line, ((-half - .0034, -.095, 1.368), (half + .0034, -.040, 1.380))), .0004)
        s.subtract(ellipsoid((0, -.0560, MOUTH_Z - .0002), (.0215*mw, .0130, .0095), bend=ARCH*.6), .003)
        # Eyes: lids over the eyeball, hollow behind them, and the opening between them
        for sign in (1, -1):
            s.union(self.lid_shell_field(sign), .0018)
            s.subtract(sphere(tuple(self.eye_centre(sign)), self.eye_r + .00025), .0002)
            s.subtract(self.eye_socket_field(sign), .00035)
        return s

    def soft_tissue_mask(self, x, y, z) -> Array:
        """How much of the soft-tissue blur applies: little on the lids, nose tip and lips."""
        keep = np.zeros(np.broadcast(x, y, z).shape, dtype=np.float32)
        regions = (((self.eye_x, self.eye_y - .0125, self.eye_z), (.020, .016, .014), 1.0),
                   ((-self.eye_x, self.eye_y - .0125, self.eye_z), (.020, .016, .014), 1.0),
                   (self.nose((0, -.090, 1.398)), (.022, .014, .010), .75),
                   ((0, -.082, MOUTH_Z - .0022), (.028*self.spec.mouth_width, .012, .012), .80))
        for centre, radii, amount in regions:
            d = ((x - centre[0])/radii[0])**2 + ((y - centre[1])/radii[1])**2 + ((z - centre[2])/radii[2])**2
            keep = np.maximum(keep, amount*np.exp(-d*d))
        return 1 - keep

    def blur_field(self, values: Array, origin: Array, sigma: float) -> Array:
        """Gaussian-blurred copy of the field, mixed back in by soft_tissue_mask (rounds the forms like fat)."""
        radius = int(math.ceil(2.5*sigma/STEP))
        offsets = np.arange(-radius, radius + 1)
        kernel = np.exp(-.5*(offsets*STEP/sigma)**2)
        kernel /= kernel.sum()
        blurred = values
        for axis in range(3):
            padded = np.pad(blurred, [(radius, radius) if a == axis else (0, 0) for a in range(3)], mode='edge')
            out = np.zeros_like(values)
            n = values.shape[axis]
            for offset, weight in zip(range(2*radius + 1), kernel):
                index = [slice(None)]*3
                index[axis] = slice(offset, offset + n)
                out += weight*padded[tuple(index)]
            blurred = out
        nx, ny, nz = values.shape
        x = (origin[0] + STEP*np.arange(nx))[:, None, None]
        y = (origin[1] + STEP*np.arange(ny))[None, :, None]
        z = (origin[2] + STEP*np.arange(nz))[None, None, :]
        return values + (blurred - values)*self.soft_tissue_mask(x, y, z)

    def head_mesh(self, material):
        """Head: the meshed sculpt, cut below the collar, thinned away from the face and skinned."""
        width = .078*max(1.0, self.spec.neck, self.spec.jaw_width)
        values, origin = self.sculpt().grid((-width, -.112, 1.238), (width, .104, 1.548), STEP)
        values = self.blur_field(values, origin, .0018)
        verts, quads = surface_nets(values, origin, STEP)
        del values
        verts = taubin(verts, quads, rounds=4)
        obj = self.to_mesh('Head', verts, [tuple(q) for q in quads.tolist()], material)
        cut = 1.246*self.size
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bottom = [f for f in bm.faces if all(v.co.z < cut for v in f.verts)]
        bmesh.ops.delete(bm, geom=bottom, context='FACES')
        bm.to_mesh(obj.data)
        bm.free()
        decimate_away_from_face(obj, self.size)
        co = self.canonical(obj.data)
        z, y = co[:, 2], co[:, 1]
        head = smooth(1.300, 1.352, z + .25*np.maximum(0, -y - .03))
        chest = smooth(1.282, 1.250, z)*(1 - head)
        set_weights(obj, {'head': head, 'neck': (1 - head)*(1 - chest), 'chest': chest})
        self.tree = BVHTree.FromPolygons([Vector(p) for p in co], [tuple(p.vertices) for p in obj.data.polygons])
        return obj

    # ------------------------------------------------------------ eyes

    def eyeball(self, sign: int, side: str, sclera, wet) -> None:
        """Sclera sphere open at the limbus, closed by a clear corneal cap."""
        centre = np.array(self.eye_centre(sign))
        radius = self.eye_r
        lateral, forward, up = _sign_frame(sign)
        limbus_angle = math.asin(LIMBUS/radius)
        cornea_back = radius*math.cos(limbus_angle) - math.sqrt(CORNEA_R**2 - LIMBUS**2)
        columns = 96
        psi = np.linspace(0, math.tau, columns, endpoint=False)
        ring_dir = lateral[None, :]*np.cos(psi)[:, None] + up[None, :]*np.sin(psi)[:, None]
        verts, colors = [], []
        gammas = np.concatenate([np.linspace(limbus_angle, limbus_angle + .10, 4),
                                 np.linspace(limbus_angle + .16, math.radians(176), 24)])
        for g in gammas:
            ring = centre + radius*(forward*math.cos(g) + ring_dir*math.sin(g))
            verts.append(ring)
            corner = np.abs(np.cos(psi))**6*smooth(.9, 1.5, g)
            limbal = 1 - .22*np.exp(-((g - limbus_angle)/.06)**2)
            base = np.array([.50, .455, .415])[None, :]*limbal
            pink = np.array([.50, .30, .27])
            colors.append(base*(1 - .55*corner[:, None]) + pink*.55*corner[:, None])
        sclera_rows = len(gammas)
        rhos = np.linspace(LIMBUS, 0, 12)
        for rho in rhos:
            axial = cornea_back + math.sqrt(CORNEA_R**2 - rho**2)
            verts.append(centre + forward*axial + ring_dir*max(rho, 1e-6))
            colors.append(np.ones((columns, 3)))
        verts = np.concatenate(verts)
        faces = grid_faces(sclera_rows, columns)
        offset = sclera_rows*columns
        faces += [tuple(i + offset for i in f) for f in grid_faces(len(rhos), columns)]
        eye = self.to_mesh(f'Eye.{side}', verts, [f[::-1] for f in faces], sclera, f'eye.{side}')
        eye.data.materials.append(wet)
        for polygon in eye.data.polygons[(sclera_rows - 1)*columns:]:
            polygon.material_index = 1
        write_colors(eye, 'Sclera pigment', np.concatenate(colors))

    def iris(self, sign: int, side: str, material, seed: int) -> None:
        centre = np.array(self.eye_centre(sign))
        lateral, forward, up = _sign_frame(sign)
        rand = np.random.default_rng(seed)
        columns = 160
        psi = np.linspace(0, math.tau, columns, endpoint=False)
        ring_dir = lateral[None, :]*np.cos(psi)[:, None] + up[None, :]*np.sin(psi)[:, None]
        limbus_axial = math.sqrt(self.eye_r**2 - LIMBUS**2)
        # radial fibres: smooth random brightness around the ring at a few frequencies
        fibres = np.zeros(columns)
        for frequency, amount in ((7, .10), (23, .12), (61, .14)):
            phases = rand.uniform(0, math.tau, 3)
            fibres += amount*np.sin(frequency*psi + phases[0])*np.sin(3*psi + phases[1])
        fibres += .10*rand.standard_normal(columns)
        fibres = np.convolve(np.concatenate([fibres[-2:], fibres, fibres[:2]]), np.ones(5)/5, 'valid')
        base = np.array(self.c.spec['iris'])
        verts, colors = [], []
        profile = ((LIMBUS*1.02, -.00010, .28), (LIMBUS*.96, .00000, .45), (LIMBUS*.88, .00010, .80),
                   (LIMBUS*.76, .00022, 1.00), (LIMBUS*.62, .00032, 1.10), (LIMBUS*.52, .00036, 1.35),
                   (LIMBUS*.47, .00036, 1.55), (LIMBUS*.43, .00034, 1.25), (PUPIL*1.25, .00028, .95),
                   (PUPIL*1.06, .00022, .40), (PUPIL, .00016, .03), (PUPIL*.6, -.0002, .012),
                   (.00005, -.0004, .01))
        for rho, lift, shade in profile:
            axial = limbus_axial - .00025 + lift
            verts.append(centre + forward*axial + ring_dir*rho)
            streak = 1 + fibres*(1 if PUPIL*1.1 < rho < LIMBUS*.9 else .3)
            tone = base*shade
            if .45*LIMBUS < rho < .56*LIMBUS:      # warm collarette
                tone = tone*np.array([1.15, 1.08, .95])
            colors.append(np.clip(tone[None, :]*streak[:, None], 0, 1))
        obj = self.to_mesh(f'Iris.{side}', np.concatenate(verts),
                           [f[::-1] for f in grid_faces(len(profile), columns)], material, f'eye.{side}')
        write_colors(obj, 'Iris pigment', np.concatenate(colors))

    def margin_curve(self, sign: int, lid: str, offset: float, radius_lift: float, count: int = 48) -> Array:
        """Canonical points along a lid margin: offset in degrees outward from the opening, radius above the support."""
        alpha = np.linspace(A_IN + 2.5, A_OUT - 1.5, count)
        beta = self.lid_upper(alpha) + offset if lid == 'upper' else self.lid_lower(alpha) - offset
        r = self.support_radius(alpha) + radius_lift
        return np.array(self.eye_centre(sign))[None, :] + eye_direction(alpha, beta, sign)*r[:, None]

    def lash_lines(self, sign: int, side: str, line, wet):
        """The Eyelids part: pigmented lash lines on both lids and a tear line along the lower lid."""
        pieces = []
        for lid, lift, offset, radius in (('upper', UPPER_LID_T*.80, .40, .00042),
                                          ('lower', LOWER_LID_T*.78, .35, .00026)):
            pieces.append((self.margin_curve(sign, lid, offset, lift), radius, line))
        pieces.append((self.margin_curve(sign, 'lower', .05, .00012), .00016, wet))
        centre = np.array(self.eye_centre(sign))
        verts, faces, materials = [], [], []
        for points, radius, material in pieces:
            start = len(verts)
            n = len(points)
            for i, p in enumerate(points):
                tangent = points[min(i + 1, n - 1)] - points[max(i - 1, 0)]
                tangent /= np.linalg.norm(tangent)
                u = np.cross(tangent, p - centre)
                u /= np.linalg.norm(u)
                v = np.cross(tangent, u)
                taper = radius*(.35 + .65*math.sin(math.pi*i/(n - 1))**.5)
                for k in range(6):
                    a = math.tau*k/6
                    verts.append(p + taper*(u*math.cos(a) + v*math.sin(a)))
            for i in range(n - 1):
                for k in range(6):
                    q = (k + 1) % 6
                    faces.append((start + i*6 + k, start + i*6 + q, start + (i + 1)*6 + q, start + (i + 1)*6 + k))
                    materials.append(0 if material is line else 1)
        obj = self.to_mesh(f'Eyelids.{side}', np.array(verts), faces, line)
        obj.data.materials.append(wet)
        for polygon, index in zip(obj.data.polygons, materials):
            polygon.material_index = index
        return obj

    def skin_distance(self, origin: Array, ray: Array, reach: float = .08) -> float:
        """Distance from origin along ray to the outer skin (cast inward from outside). Canonical."""
        start = Vector(origin + ray*reach)
        hit, _, _, _ = self.tree.ray_cast(start, Vector(-ray), reach)
        if hit is None:
            return float('nan')
        return reach - (hit - start).length

    def caruncle(self, sign: int, side: str, material) -> None:
        direction = eye_direction(np.array(A_IN + 4.0), np.array(B_IN - .8), sign)
        position = np.array(self.eye_centre(sign)) + direction*(self.eye_r + .0012)
        k = self.to_scene
        self.c.ovoid(f'Caruncle.{side}', tuple(position*k), (.0016*k, .0013*k, .0023*k),
                     material, 'head', (0, 0, sign*.6))

    def place_eye_bones(self) -> None:
        rig = self.c.rig
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode='EDIT')
        for sign, side in ((1, 'L'), (-1, 'R')):
            bone = rig.data.edit_bones[f'eye.{side}']
            centre = self.final(self.eye_centre(sign))
            bone.head = centre
            bone.tail = centre + Vector((0, -.04, 0))
        bpy.ops.object.mode_set(mode='OBJECT')

    def build_eyes(self, head) -> Dict[str, object]:
        c = self.c
        self.place_eye_bones()
        sclera = principled(f'{c.name} • Sclera', (.5, .46, .42), .18, Subsurface_Weight=.35,
                            Subsurface_Scale=.002, Coat_Weight=.4, Coat_Roughness=.05)
        color_from_attribute(sclera, 'Sclera pigment')
        wet = c.wet_material()
        iris_mat = principled(f'{c.name} • Iris stroma', tuple(c.spec['iris']), .38, Subsurface_Weight=.2,
                              Subsurface_Scale=.0008)
        color_from_attribute(iris_mat, 'Iris pigment')
        pink = principled(f'{c.name} • Caruncle', (.42, .16, .13), .22, Subsurface_Weight=.6,
                          Subsurface_Scale=.002, Coat_Weight=.6, Coat_Roughness=.08)
        line = principled(f'{c.name} • Kajal lash line', (.016, .011, .009), .40)
        lids = {}
        for sign, side in ((1, 'L'), (-1, 'R')):
            self.eyeball(sign, side, sclera, wet)
            self.iris(sign, side, iris_mat, 31 + sign)
            lids[side] = self.lash_lines(sign, side, line, wet)
            self.caruncle(sign, side, pink)
            for label in ('Eye', 'Iris', 'Eyelids'):
                face_away(bpy.data.objects[f'{c.name}_{label}.{side}'], self.final(self.eye_centre(sign)))
        return lids

    # --------------------------------------------------------- shading

    def lip_mask(self, p: Array) -> Array:
        d = np.full(len(p), 1.0)
        for centre, radii, bend in (self.upper_lip, self.tubercle, self.lower_lip):
            field, _ = ellipsoid(centre, radii, bend=bend)
            d = np.minimum(d, field(p[:, 0], p[:, 1], p[:, 2]))
        mw = self.spec.mouth_width
        return smooth(.0011, .0003, d)*smooth(.0262*mw, .0236*mw, np.abs(p[:, 0]))

    def mouth_mask(self, p: Array) -> Array:
        """Inside the parted lips only: behind the lip fronts and close to the mouth line."""
        mw = self.spec.mouth_width
        x = p[:, 0]
        yy = p[:, 1] - ARCH*x**2
        u = np.clip(np.abs(x)/(.0242*mw), 0, 1)
        line = MOUTH_Z - .0010*u*u
        return (smooth(-.0815, -.0785, yy)*smooth(.025*mw, .022*mw, np.abs(x))
                *smooth(.0030, .0012, np.abs(p[:, 2] - line)))

    def beard_mask(self, p: Array) -> Array:
        """Where stubble grows: jaw, chin, upper lip and lower cheeks, not the lips or the throat."""
        x, y, z = p[:, 0], p[:, 1], p[:, 2]
        ax = np.abs(x)
        cheek_line = 1.392 - .30*np.maximum(0, ax - .020)          # falls from beside the nose toward the ear
        upper = smooth(cheek_line + .004, cheek_line - .003, z)
        front = smooth(.012, -.004, y)                              # in front of the ear and the nape
        throat = smooth(1.318, 1.336, z + .4*np.maximum(0, y + .03))
        return upper*front*throat          # the lips themselves are masked out by the caller

    def paint_head(self, head) -> None:
        """Regional colour on the sculpted head: lips, flush, shadowed sockets, dark mouth, stubble."""
        sp = self.spec
        p = self.canonical(head.data)
        base = np.array(self.c.spec['skin'])
        tint = np.zeros((len(p), 3))
        ex, ey, ez = self.eye_x, self.eye_y, self.eye_z
        for sign in (1, -1):
            tint += np.outer(_gauss(p, (sign*.040, -.060, 1.404), (.019, .030, .016)), (.07, -.015, -.02))
            tint += np.outer(_gauss(p, (sign*ex, ey - .0085, ez), (.024, .030, .016)), (-.13, -.15, -.11))
            tint += np.outer(_gauss(p, (sign*(ex - .002), ey - .0115, ez - .0135), (.018, .030, .006)),
                             (-.05, -.07, -.04))
        tint += np.outer(_gauss(p, self.nose((0, -.095, 1.400)), (.016, .020, .010)), (.06, -.01, -.015))
        tint += np.outer(_gauss(p, (0, -.085, 1.387), (.020, .020, .006)), (-.05, -.07, -.04))
        tint += np.outer(_gauss(p, (0, -.070, 1.485), (.060, .050, .030)), (-.02, -.03, -.03))
        lips = self.lip_mask(p)
        if sp.beard_shadow > 0:
            stubble = self.beard_mask(p)*(1 - lips)*sp.beard_shadow
            tint += np.outer(stubble, (-.30, -.25, -.15))
        tint = tint*(1 - lips[:, None]) + (np.array(sp.lip_colour)/base - 1)[None, :]*lips[:, None]
        margin_gloss = np.zeros(len(p))
        for sign in (1, -1):
            alpha, beta, r = self.eye_angles(p[:, 0], p[:, 1], p[:, 2], sign)
            near = smooth(1.6, .4, self.aperture_distance(alpha, beta))*smooth(self.eye_r + .0024, self.eye_r + .0016, r)
            margin_gloss = np.maximum(margin_gloss, near)
            lid = smooth(14, 2, self.aperture_distance(alpha, beta))*smooth(self.eye_r + .006, self.eye_r + .003, r)
            tint += np.outer(lid*(1 - near), (-.08, -.10, -.07))
        tint = tint*(1 - margin_gloss[:, None]) + (np.array([.30, .125, .10])/base - 1)[None, :]*margin_gloss[:, None]
        dark = self.mouth_mask(p)
        tint = tint*(1 - dark[:, None]) + (np.array([.07, .018, .016])/base - 1)[None, :]*dark[:, None]
        write_colors(head, 'Skin tint', tint)
        gloss = np.maximum(np.maximum(lips, dark), margin_gloss)
        write_colors(head, 'Skin gloss', np.repeat(gloss[:, None], 3, 1))

    # ---------------------------------------------------- brows, mouth

    def on_skin(self, x: float, z: float, lift: float = 0.0) -> Tuple[Vector, Vector]:
        """Front-facing skin point at canonical (x, z), lifted along the normal. Canonical result."""
        hit, normal, _, _ = self.tree.ray_cast(Vector((x, -.25, z)), Vector((0, 1, 0)), .4)
        if hit is None:
            return Vector((x, -.07, z)), Vector((0, -1, 0))
        if normal.y > 0:
            normal = -normal
        return hit + normal*lift, normal

    def brow_curve(self, u: float, sign: int) -> Tuple[float, float]:
        """Canonical (x, z) along the brow from its head (u=0) to its tail (u=1)."""
        t = u*(len(BROW) - 1)
        i = min(int(t), len(BROW) - 2)
        f = t - i
        x = BROW[i][0] + (BROW[i + 1][0] - BROW[i][0])*f
        z = BROW[i][1] + (BROW[i + 1][1] - BROW[i][1])*f
        ridge = self.spec.brow_ridge
        z = 1.4500 + (z - 1.4500)*(1 - .4*ridge) - .0012*ridge      # lower and straighter over a ridge
        return sign*x*(.5 + .5*self.spec.eye_spacing), z

    def brow_strips(self, material) -> None:
        """Brow.X: a faint darker band under the brow fibres (it carries the brow shape keys)."""
        k = self.to_scene
        for sign, side in ((1, 'L'), (-1, 'R')):
            points, radii = [], []
            for step in range(10):
                u = step/9
                x, z = self.brow_curve(u, sign)
                point, _ = self.on_skin(x, z, .0003)
                points.append(tuple(point*k))
                radii.append((.0011*math.sin(math.pi*(.12 + .8*u))**.6 + .0002)*k)
            obj = self.c.tube(f'Brow.{side}', points, radii, material, 'head')
            mesh = obj.data
            for r in range(len(mesh.vertices)//10):
                ring = mesh.vertices[r*10:(r + 1)*10]
                centre = sum((v.co for v in ring), Vector())/10
                for v in ring:
                    offset = v.co - centre
                    v.co = centre + Vector((offset.x, offset.y*.25, offset.z))

    def mouth_lining(self, material):
        """Mouth: the dark inner lining behind the lips, with the shared speech shape keys."""
        rows, columns = 12, 48
        mw = self.spec.mouth_width
        verts = []
        for r in range(rows):
            v = -math.pi/2 + math.pi*r/(rows - 1)
            for k in range(columns):
                u = math.tau*k/columns
                x = .0195*mw*math.cos(v)*math.cos(u)
                y = -.0585 + .0105*math.cos(v)*math.sin(u) + ARCH*.6*x*x
                z = MOUTH_Z + .0072*math.sin(v)
                verts.append((x, y, z))
        obj = self.to_mesh('Mouth', np.array(verts), grid_faces(rows, columns), material)
        obj.shape_key_add(name='Basis', from_mix=False)
        obj.data.shape_keys.use_relative = True
        for name, (drop, width) in {'Mouth_Ah': (.0110, 1.0), 'Mouth_O': (.0075, .78), 'Mouth_Ee': (.0030, 1.12),
                                    'Mouth_MBP': (-.0004, 1.0), 'Mouth_FV': (.0018, 1.04)}.items():
            key = obj.shape_key_add(name=name, from_mix=False)
            for item, (x, y, z) in zip(key.data, verts):
                lower = max(0.0, MOUTH_Z - z)/.0072
                item.co = self.final((x*width, y, z - drop*lower))
            key.value = 0
        obj['Usage'] = 'Use one primary phoneme at a time. Basis is the relaxed mouth.'
        return obj

    def teeth_and_tongue(self) -> None:
        """Upper teeth just behind the parted lips and a tongue on the mouth floor."""
        c = self.c
        enamel = principled(f'{c.name} • Teeth', (.62, .56, .46), .25, Subsurface_Weight=.3, Subsurface_Scale=.001)
        flesh = principled(f'{c.name} • Tongue', (.30, .075, .065), .45, Subsurface_Weight=.4, Subsurface_Scale=.002)
        verts: List[Point] = []
        faces: List[Tuple[int, int, int, int]] = []
        widths = (.0043, .0035, .0040, .0036, .0034)       # central and lateral incisors, canine, premolars
        x = 0.0
        for i, w in enumerate(widths):
            cx = x + w/2
            for sign in (1, -1):
                px = sign*cx
                py = -.0758 + ARCH*1.15*px*px + .0008*i
                _ovoid_into(verts, faces, (px, py, MOUTH_Z + .0040 - .0002*i),
                            (w*.52, .0028 - .0002*i, .0052 - .0003*i))
            x += w
        teeth = self.to_mesh('Upper teeth', np.array(verts), faces, enamel)
        face_away(teeth, self.final((0, -.050, MOUTH_Z + .004)))
        verts, faces = [], []
        x = 0.0
        for i, w in enumerate((.0036, .0031, .0037, .0035, .0034)):   # lower incisors are narrower
            cx = x + w/2
            for sign in (1, -1):
                px = sign*cx
                py = -.0738 + ARCH*1.15*px*px + .0008*i
                _ovoid_into(verts, faces, (px, py, MOUTH_Z - .0046 + .0002*i),
                            (w*.52, .0025 - .0002*i, .0046 - .0003*i))
            x += w
        lower = self.to_mesh('Lower teeth', np.array(verts), faces, enamel)
        face_away(lower, self.final((0, -.050, MOUTH_Z - .004)))
        verts, faces = [], []
        _ovoid_into(verts, faces, (0, -.0600, MOUTH_Z - .0052), (.0160, .0140, .0040), 24, 12)
        tongue = self.to_mesh('Tongue', np.array(verts), faces, flesh)
        face_away(tongue, self.final((0, -.0600, MOUTH_Z - .0052)))

    # ---------------------------------------------------------- blinks

    def rotate_lids(self, points: Array, sign: int, amount: float = 1.0) -> Array:
        """Close the lids (canonical points): slide the upper lid down over the eyeball, lift the lower a little."""
        centre = np.array(self.eye_centre(sign))
        alpha, beta, r = self.eye_angles(points[:, 0], points[:, 1], points[:, 2], sign)
        a = np.clip(alpha, A_IN, A_OUT)
        up, low = self.lid_upper(a), self.lid_lower(a)
        closed = low + 2.5 + .3
        above = beta - up
        below = low - beta
        near = (smooth(self.eye_r + .0065, self.eye_r + .0035, r)*smooth(A_IN - 12, A_IN - 3, alpha)
                *smooth(A_OUT + 12, A_OUT + 3, alpha))
        upper_w = np.where(beta >= CENTRE_B, smooth(17, 5, above), 0)*near
        lower_w = np.where(beta < CENTRE_B, smooth(11, 2, below), 0)*near
        new_beta = beta - (up - closed)*upper_w*amount + 2.5*lower_w*amount
        return centre[None, :] + eye_direction(alpha, new_beta, sign)*r[:, None]

    def head_blinks(self, head) -> None:
        import facial_controls
        co = self.canonical(head.data)
        if head.data.shape_keys is None:
            head.shape_key_add(name='Basis', from_mix=False)
        for sign, side in ((1, 'L'), (-1, 'R')):
            moved = self.rotate_lids(co, sign)*self.size
            key = head.shape_key_add(name=f'Blink_{side}', from_mix=False)
            key.data.foreach_set('co', moved.astype(np.float32).ravel())
            key.value = 0
            facial_controls.driver_from_property(key, self.c.rig, f'blink_{side}')

    def eyelid_blinks(self) -> None:
        """Point the shared Blink keys at the new lids: lash lines close with the skin, eyeballs stay round."""
        for sign, side in ((1, 'L'), (-1, 'R')):
            for label in ('Eye', 'Iris', 'Eyelids'):
                obj = bpy.data.objects[f'{self.c.name}_{label}.{side}']
                keys = obj.data.shape_keys.key_blocks
                basis = np.array([v.co for v in keys['Basis'].data])
                target = self.rotate_lids(basis/self.size, sign)*self.size if label == 'Eyelids' else basis
                keys['Blink'].data.foreach_set('co', target.astype(np.float32).ravel())

    # ---------------------------------------------------------- speech

    HINGE = (.0050, 1.4150)        # (y, z) of the jaw hinge, canonical

    def jaw_weight(self, p: Array) -> Array:
        """How much of each point rides on the jaw: lower lip, chin and jaw. The upper face stays."""
        x, y, z = p[:, 0], p[:, 1], p[:, 2]
        ax = np.abs(x)
        lateral = np.maximum(0.0, ax - self.mouth_half*.85)
        split = MOUTH_Z - .0010*np.clip(ax/self.mouth_half, 0, 1)**2 + .55*lateral    # rises toward the ear
        width = .0012 + .45*lateral
        below = smooth(split + width, split - width, z)
        behind = smooth(.010, -.012, y)                                              # the nape stays
        throat = smooth(1.300, 1.342, z + .5*np.maximum(0, -.035 - y))               # chin skin goes, neck stays
        w = below*behind*throat
        # The corners stay closed: toward each corner both lips share the jaw, so the gape is an oval
        front = smooth(-.044, -.060, y - ARCH*x*x)
        corner = (smooth(self.mouth_half*.35, self.mouth_half*1.05, ax)*np.exp(-((z - MOUTH_Z)/.010)**2)
                  *smooth(self.mouth_half*1.9, self.mouth_half*1.3, ax)*front)
        return w + (.42 - w)*corner

    def lip_regions(self, p: Array) -> Tuple[Array, Array, Array]:
        """Soft masks of the upper lip, the lower lip and the mouth corners."""
        x, y, z = p[:, 0], p[:, 1], p[:, 2]
        ax = np.abs(x)
        front = smooth(self.mouth_half + .010, self.mouth_half + .002, ax)*smooth(-.058, -.070, y - ARCH*x*x)
        upper = front*smooth(MOUTH_Z - .0005, MOUTH_Z + .0015, z)*smooth(MOUTH_Z + .016, MOUTH_Z + .010, z)
        lower = front*smooth(MOUTH_Z + .0005, MOUTH_Z - .0015, z)*smooth(MOUTH_Z - .018, MOUTH_Z - .011, z)
        corner = (np.exp(-(((ax - self.mouth_half)/.010)**2 + ((z - MOUTH_Z)/.010)**2))
                  *smooth(-.045, -.062, y))
        return upper, lower, corner

    def open_jaw(self, p: Array, degrees: float, weight: Array) -> Array:
        hy, hz = self.HINGE
        a = math.radians(degrees)
        dy, dz = p[:, 1] - hy, p[:, 2] - hz
        turned = p.copy()
        turned[:, 1] = hy + dy*math.cos(a) - dz*math.sin(a)
        turned[:, 2] = hz + dy*math.sin(a) + dz*math.cos(a)
        return p + (turned - p)*weight[:, None]

    def speech_pose(self, p: Array, name: str, rigid: bool = False) -> Array:
        """Canonical points in a speech or expression pose. rigid: the part rides the jaw whole (tongue, lower teeth)."""
        jaw = {'Mouth_Ah': 13.0, 'Mouth_O': 8.0, 'Mouth_U': 4.0, 'Mouth_Ee': 4.0, 'Mouth_MBP': -.4,
               'Mouth_FV': 2.5, 'Mouth_L': 9.0, 'Mouth_Consonant': 3.0}.get(name, 0.0)
        w = np.ones(len(p)) if rigid else self.jaw_weight(p)
        q = self.open_jaw(p, jaw, w)
        if rigid:
            if name == 'Mouth_L':                        # tongue tip up behind the upper teeth
                tip = smooth(-.050, -.070, p[:, 1])
                q[:, 2] += .004*tip
            return q
        upper, lower, corner = self.lip_regions(p)
        lips = np.clip(upper + lower, 0, 1)
        x = q[:, 0]
        if name in ('Mouth_O', 'Mouth_U'):              # rounded and pushed forward
            pucker = .32 if name == 'Mouth_O' else .42
            ax, z = np.abs(p[:, 0]), p[:, 2]
            gather = (np.exp(-((ax/(self.mouth_half*1.15))**2 + ((z - MOUTH_Z)/.014)**2))
                      *smooth(-.048, -.064, p[:, 1] - ARCH*p[:, 0]**2))   # smooth all round: no ridge above the lip
            q[:, 0] = x*(1 - pucker*gather)
            q[:, 1] -= (.0045 if name == 'Mouth_O' else .0060)*gather
        elif name in ('Mouth_Ee', 'Mouth_Consonant'):   # stretched wide and thin
            amount = 1.0 if name == 'Mouth_Ee' else .35
            q[:, 0] = x*(1 + .10*corner*amount)
            q[:, 1] += .0020*corner*amount
            q[:, 2] += .0008*corner*amount
        elif name == 'Mouth_MBP':                       # lips pressed together
            q[:, 2] -= .0006*upper*smooth(MOUTH_Z + .006, MOUTH_Z, p[:, 2])
            q[:, 2] += .0007*lower*smooth(MOUTH_Z - .006, MOUTH_Z, p[:, 2])
            q[:, 1] += .0008*lips
        elif name == 'Mouth_FV':                        # lower lip tucked up under the upper teeth
            q[:, 2] += .0025*lower
            q[:, 1] += .0030*lower
        elif name == 'Smile':
            q[:, 0] = x*(1 + .06*corner)
            q[:, 1] += .0025*corner
            q[:, 2] += .0045*corner
            for sign in (1, -1):                        # cheeks lift with the smile
                q[:, 2] += .0015*_gauss(p, (sign*.034, -.058, 1.398), (.016, .020, .014))
        elif name == 'Worry':
            q[:, 2] -= .0035*corner
            q[:, 0] = x*(1 - .03*corner)
        return q

    def speech_shapes(self, head) -> None:
        """Speech and expression keys on the head, tongue and lower teeth, driven by the shared rig controls."""
        import facial_controls
        rig = self.c.rig
        controls = [(name, name) for name in facial_controls.MOUTH_KEYS] + [('Smile', 'mouth_smile'),
                                                                            ('Worry', 'mouth_worry')]
        parts = [(head, False)]
        for label in ('Tongue', 'Lower teeth'):
            obj = bpy.data.objects.get(f'{self.c.name}_{label}')
            if obj is not None:
                parts.append((obj, True))
        for obj, rigid in parts:
            if obj.data.shape_keys is None:
                obj.shape_key_add(name='Basis', from_mix=False)
            basis = self.canonical(obj.data)
            for name, control in controls:
                if rigid and name in ('Smile', 'Worry'):
                    continue
                key = obj.shape_key_add(name=name, from_mix=False)
                key.data.foreach_set('co', (self.speech_pose(basis, name, rigid)*self.size).astype(np.float32).ravel())
                key.value = 0
                facial_controls.driver_from_property(key, rig, control)
