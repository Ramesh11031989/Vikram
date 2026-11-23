"""Realistic head for the Halwai's neighbour, sculpted as a volume.

The shared cast face is a revolved profile with eyes and lips laid on it like
decals, which reads as stylized. Here the head is a signed-distance sculpt
(skull, brow, cheekbones, jaw, chin, a nose with open nostrils, full lips with a
parted mouth line) meshed with surface nets, plus:

* real eyeballs (sclera, a recessed iris with a pupil, a clear corneal bulge),
* eyelids that wrap the eyeball with a real margin, crease and fold, merging
  tangentially into the skin so there is no seam,
* lash lines, tear lines and caruncles, brows of fibres, teeth and a tongue.

Design values are in final metres (after the character's height scale);
c.mesh() takes unscaled coordinates, so everything is divided by c.scale on the
way in. Object names match the shared facial-controls contract (Head, Eye.X,
Iris.X, Eyelids.X, Brow.X, Mouth).
"""

from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from sdf_sculpt import Sculpt, capsule, ellipsoid, sphere, surface_nets, taubin

Array = np.ndarray

# ----------------------------------------------------------- landmarks (m)
TOP = 1.540            # vertex of the skull (matches the body's head top)
EYE_Z = 1.4370         # pupil height
EYE_X = .0310          # half the interpupillary distance (6.2 cm)
EYE_Y = -.0555         # eyeball centre depth
EYE_R = .0121          # eyeball radius
MOUTH_Z = 1.3742       # stomion at the centre
ARCH = 1/(2*.027)      # lips and teeth follow the dental arch: y += ARCH*x²
STEP = .00062          # voxel size of the head sculpt

# Lip volumes (centre, radii, arch bend) shared by the sculpt and the lip colour mask
UPPER_LIP = ((0, -.0799, 1.3790), (.0200, .0056, .0055), ARCH)
TUBERCLE = ((0, -.0838, 1.3772), (.0056, .0029, .0029), 0.0)
LOWER_LIP = ((0, -.0797, 1.3678), (.0185, .0074, .0062), ARCH)

# Palpebral fissure in eye-centred angles (degrees): azimuth is lateral-positive.
A_IN, B_IN = -74.0, -1.5
A_OUT, B_OUT = 70.0, 4.5
H_UP, PEAK_UP, ROUND_UP = 20.3, .44, .85
H_LOW, PEAK_LOW, ROUND_LOW = 28.1, .57, 1.0
CENTRE_A, CENTRE_B = -2.0, -2.0


def smooth(a: float, b: float, x):
    t = np.clip((x - a)/(b - a), 0, 1)
    return t*t*(3 - 2*t)


def eye_centre(sign: int) -> Vector:
    return Vector((sign*EYE_X, EYE_Y, EYE_Z))


# ------------------------------------------------------------- eye shape

def _bump(t, peak: float, roundness: float):
    a = math.log(.5)/math.log(peak)
    return np.maximum(np.sin(math.pi*np.clip(t, 0, 1)**a), 0)**roundness


def lid_upper(alpha):
    t = (alpha - A_IN)/(A_OUT - A_IN)
    return B_IN + (B_OUT - B_IN)*np.clip(t, 0, 1) + H_UP*_bump(t, PEAK_UP, ROUND_UP)


def lid_lower(alpha):
    t = (alpha - A_IN)/(A_OUT - A_IN)
    return B_IN + (B_OUT - B_IN)*np.clip(t, 0, 1) - H_LOW*_bump(t, PEAK_LOW, ROUND_LOW)


def support_radius(alpha):
    """Where the lid margin rests: on the eyeball, lifted at the corners."""
    return EYE_R + .00035 + .0012*smooth(-50, -74, alpha) + .0004*smooth(45, 70, alpha)


def eye_direction(alpha, beta, sign: int) -> Array:
    a, b = np.radians(alpha), np.radians(beta)
    return np.stack([sign*np.sin(a)*np.cos(b), -np.cos(a)*np.cos(b), np.sin(b)], axis=-1)


def eye_angles(x, y, z, sign: int):
    dx, dy, dz = x - sign*EYE_X, y - EYE_Y, z - EYE_Z
    alpha = np.degrees(np.arctan2(sign*dx, -dy))
    beta = np.degrees(np.arctan2(dz, np.sqrt(dx*dx + dy*dy)))
    return alpha, beta, np.sqrt(dx*dx + dy*dy + dz*dz)


def aperture_distance(alpha, beta, grow: float = 0.0):
    """Angular distance (degrees) outside the lid opening; negative inside."""
    lids = np.maximum(lid_lower(alpha) - grow - beta, beta - lid_upper(alpha) - grow)
    return np.maximum(lids, np.maximum(A_IN - grow - alpha, alpha - A_OUT - grow))


def aperture_radius(theta: float) -> float:
    """Angular distance from the opening's centre to the lid margin along theta."""
    lo, hi = 0.0, 90.0
    for _ in range(40):
        mid = (lo + hi)/2
        a = CENTRE_A + mid*math.cos(theta)
        b = CENTRE_B + mid*math.sin(theta)
        if float(aperture_distance(np.array(a), np.array(b))) < 0:
            lo = mid
        else:
            hi = mid
    return lo


UPPER_LID_T = .00135   # lid thickness beyond the support sphere
LOWER_LID_T = .00118


def lid_shell_field(sign: int):
    """Both lids as one shell over the eyeball, out to ~40 degrees past the opening."""
    def field(x, y, z):
        alpha, beta, r = eye_angles(x, y, z, sign)
        upper = smooth(CENTRE_B - 6, CENTRE_B + 6, beta)
        outer = support_radius(alpha) + LOWER_LID_T + (UPPER_LID_T - LOWER_LID_T)*upper
        zone = np.radians(aperture_distance(alpha, beta) - 40)*np.maximum(r, .004)
        return np.maximum(r - outer, zone)
    reach = EYE_R + .006
    c = eye_centre(sign)
    return field, ((c.x - reach, c.y - reach, c.z - reach), (c.x + reach, c.y + .002, c.z + reach))


def eye_socket_field(sign: int):
    """The lid opening, carved through the lid shell in front of the eyeball."""
    def field(x, y, z):
        alpha, beta, r = eye_angles(x, y, z, sign)
        angular = np.radians(aperture_distance(alpha, beta))*np.maximum(r, .004)
        return np.maximum(angular, r - (EYE_R + .008))
    reach = EYE_R + .012
    c = eye_centre(sign)
    return field, ((c.x - reach, c.y - reach, c.z - reach), (c.x + reach, c.y + .004, c.z + reach))


# ----------------------------------------------------------- head sculpt

def head_sculpt() -> Sculpt:
    s = Sculpt()
    # Cranium, forehead and the occiput running into the nape
    s.union(ellipsoid((0, .007, 1.452), (.0700, .087, .088)))
    s.union(ellipsoid((0, -.040, 1.482), (.050, .042, .040)), .02)          # fuller, upright forehead
    s.union(ellipsoid((0, .040, 1.400), (.046, .036, .034)), .022)          # occiput
    # Neck, leaning forward from the skull to the chest
    def neck(x, y, z):
        cy = .002 + (z - 1.26)*.09
        flare = smooth(1.322, 1.272, z)
        ax, ay = .0480 + .0190*flare, .0445 + .0060*flare
        return (np.sqrt((x/ax)**2 + ((y - cy)/ay)**2) - 1)*ay
    s.union((neck, ((-.05, -.05, 1.236), (.05, .06, 1.40))), .028)
    for sign in (1, -1):
        s.union(capsule((sign*.041, .020, 1.400), (sign*.013, -.036, 1.262), .0095, .0075), .018)  # sternomastoid
    # Soft face mass: cheeks and jaw under a youthful fat layer
    s.union(ellipsoid((0, -.032, 1.398), (.049, .045, .044)), .020)
    s.union(ellipsoid((0, -.048, 1.392), (.036, .032, .032)), .014)
    for sign in (1, -1):
        s.union(ellipsoid((sign*.042, -.051, 1.417), (.014, .017, .012), (0, 0, sign*-32)), .020)   # zygoma
        s.union(ellipsoid((sign*.032, -.0555, 1.4045), (.020, .017, .018)), .018)                 # malar fat
        s.subtract(ellipsoid((sign*.052, -.030, 1.378), (.008, .016, .012)), .020)             # buccal hollow
        s.subtract(ellipsoid((sign*.070, -.034, 1.456), (.006, .018, .015)), .022)             # temple
    # Jaw and chin
    for sign in (1, -1):
        gonion = (sign*.0372, -.004, 1.3690)
        s.union(capsule(gonion, (sign*.0140, -.0605, 1.3470), .0110, .0095), .022)
        s.union(capsule(gonion, (sign*.0450, .0080, 1.4150), .0100, .0095), .022)
    s.union(ellipsoid((0, -.0650, 1.3500), (.0155, .0128, .0130)), .012)
    # Brow ridge, soft
    for sign in (1, -1):
        s.union(capsule((sign*.010, -.0728, 1.4545), (sign*.040, -.0650, 1.4580), .0050, .0046), .014)
        s.union(capsule((sign*.040, -.0650, 1.4580), (sign*.054, -.0548, 1.4515), .0046, .0040), .014)
    # Orbits: hollow out the socket the lids will lie over
    for sign in (1, -1):
        s.subtract(ellipsoid((sign*.0312, -.0690, 1.4378), (.0168, .0098, .0100)), .010)
    # Muzzle and lips (they follow the dental arch)
    s.union(ellipsoid((0, -.0615, 1.3785), (.030, .0180, .025), bend=ARCH), .010)
    for (centre, radii, bend), k in ((UPPER_LIP, .0024), (TUBERCLE, .0020), (LOWER_LIP, .0026)):
        s.union(ellipsoid(centre, radii, bend=bend), k)
    for sign in (1, -1):
        s.union(capsule((sign*.0036, -.0848, 1.3918), (sign*.0050, -.0852, 1.3848), .0012, .0014), .0022)  # philtral columns
        s.subtract(ellipsoid((sign*.0224, -.0712, 1.3742), (.0024, .0034, .0020)), .0025)  # mouth corners
        s.subtract(capsule((sign*.0200, -.0790, 1.3985), (sign*.0280, -.0718, 1.3720), .0006, .0005), .0040)  # nasolabial
    s.subtract(ellipsoid((0, -.0860, 1.3880), (.0028, .0015, .0036)), .0018)            # philtrum
    s.subtract(ellipsoid((0, -.0830, 1.3578), (.0145, .0040, .0030), bend=ARCH), .0050)  # mentolabial sulcus
    # Nose
    s.union(capsule((0, -.0728, 1.4440), (0, -.0938, 1.4065), .0058, .0058), .0060)     # dorsum
    s.union(ellipsoid((0, -.0805, 1.4150), (.0108, .0102, .0230), (-26, 0, 0)), .0070)  # sidewalls
    s.union(ellipsoid((0, -.0936, 1.4010), (.0080, .0072, .0066)), .0032)               # lobule
    for sign in (1, -1):
        s.union(sphere((sign*.0034, -.0965, 1.4016), .0045), .0022)                       # domes
        s.union(ellipsoid((sign*.0106, -.0856, 1.3980), (.0050, .0076, .0055), (0, 0, sign*22)), .0034)  # alae
        s.subtract(capsule((sign*.0154, -.0842, 1.4050), (sign*.0164, -.0822, 1.3938), .0008, .0008), .0014)  # alar groove
    s.union(capsule((0, -.0946, 1.3950), (0, -.0866, 1.3928), .0030, .0033), .0022)     # columella
    for sign in (1, -1):
        s.subtract(ellipsoid((sign*.0057, -.0884, 1.3890), (.0026, .0046, .0015), (8, 0, sign*16)), .0007)  # nostrils
    # Mouth: parted line and an interior
    def mouth_line(x, y, z):
        u = np.clip(np.abs(x)/.0226, 0, 1)
        centre = MOUTH_Z - .0010*u*u
        gap = .00085*np.sqrt(np.maximum(0, 1 - u**1.6))
        yy = y - ARCH*x*x
        depth = np.maximum(-.090 - yy, yy + .062)
        return np.maximum(np.maximum(np.abs(z - centre) - gap, np.abs(x) - .0226), depth)
    s.subtract((mouth_line, ((-.026, -.095, 1.368), (.026, -.040, 1.380))), .0004)
    s.subtract(ellipsoid((0, -.0560, 1.3740), (.0215, .0130, .0095), bend=ARCH*.6), .003)
    # Eyes: lids over the eyeball, hollow behind them, and the opening between them
    for sign in (1, -1):
        s.union(lid_shell_field(sign), .0018)
        s.subtract(sphere(tuple(eye_centre(sign)), EYE_R + .00025), .0002)
        s.subtract(eye_socket_field(sign), .00035)
    return s


def soft_tissue_mask(x, y, z) -> Array:
    """How much of the soft-tissue blur applies: little on the lids, nose tip and lips."""
    keep = np.zeros(np.broadcast(x, y, z).shape, dtype=np.float32)
    for centre, radii, amount in (((.031, -.068, EYE_Z), (.020, .016, .014), 1.0),
                                  ((-.031, -.068, EYE_Z), (.020, .016, .014), 1.0),
                                  ((0, -.090, 1.398), (.022, .014, .010), .75),
                                  ((0, -.082, 1.372), (.028, .012, .012), .80)):
        d = ((x - centre[0])/radii[0])**2 + ((y - centre[1])/radii[1])**2 + ((z - centre[2])/radii[2])**2
        keep = np.maximum(keep, amount*np.exp(-d*d))
    return 1 - keep


def blur_field(values: Array, origin: Array, sigma: float) -> Array:
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
    mask = soft_tissue_mask(x, y, z)
    return values + (blurred - values)*mask


# ----------------------------------------------------------- mesh helpers

def to_mesh(c, name: str, verts: Array, faces, material, bone: str = 'head'):
    return c.mesh(name, [tuple(v) for v in (np.asarray(verts)/c.scale)], faces, material, bone)


def face_away(obj, centre: Sequence[float]) -> None:
    """Make the winding consistent and the normals point away from a centre."""
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


def head_mesh(c, sculpt: Sculpt, material):
    values, origin = sculpt.grid((-.078, -.112, 1.238), (.078, .104, 1.548), STEP)
    values = blur_field(values, origin, .0018)
    verts, quads = surface_nets(values, origin, STEP)
    del values
    verts = taubin(verts, quads, rounds=4)
    obj = to_mesh(c, 'Head', verts, [tuple(q) for q in quads.tolist()], material)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bottom = [f for f in bm.faces if all(v.co.z < 1.246 for v in f.verts)]
    bmesh.ops.delete(bm, geom=bottom, context='FACES')
    bm.to_mesh(obj.data)
    bm.free()
    co = np.array([v.co for v in obj.data.vertices])
    z, y = co[:, 2], co[:, 1]
    head = smooth(1.300, 1.352, z + .25*np.maximum(0, -y - .03))
    chest = smooth(1.282, 1.250, z)*(1 - head)
    set_weights(obj, {'head': head, 'neck': (1 - head)*(1 - chest), 'chest': chest})
    return obj


# ------------------------------------------------------------- materials

def principled(name: str, rgb, rough: float, **inputs):
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


# ----------------------------------------------------------------- eyes

LIMBUS = .0059
PUPIL = .0019
CORNEA_R = .0078


def _sign_frame(sign: int) -> Tuple[Array, Array, Array]:
    lateral = np.array([sign, 0., 0.])
    forward = np.array([0., -1., 0.])
    up = np.array([0., 0., 1.])
    return lateral, forward, up


def eyeball(c, sign: int, side: str, sclera, wet) -> None:
    """Sclera sphere open at the limbus, closed by a clear corneal cap."""
    centre = np.array(eye_centre(sign))
    lateral, forward, up = _sign_frame(sign)
    limbus_angle = math.asin(LIMBUS/EYE_R)
    cornea_back = EYE_R*math.cos(limbus_angle) - math.sqrt(CORNEA_R**2 - LIMBUS**2)
    columns = 96
    psi = np.linspace(0, math.tau, columns, endpoint=False)
    ring_dir = lateral[None, :]*np.cos(psi)[:, None] + up[None, :]*np.sin(psi)[:, None]
    verts, colors = [], []
    gammas = np.concatenate([np.linspace(limbus_angle, limbus_angle + .10, 4),
                             np.linspace(limbus_angle + .16, math.radians(176), 24)])
    for g in gammas:
        ring = centre + EYE_R*(forward*math.cos(g) + ring_dir*math.sin(g))
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
        r = max(rho, 1e-6)
        verts.append(centre + forward*axial + ring_dir*r)
        colors.append(np.ones((columns, 3)))
    verts = np.concatenate(verts)
    faces = grid_faces(sclera_rows, columns)
    offset = sclera_rows*columns
    cornea_faces = grid_faces(len(rhos), columns)
    faces += [tuple(i + offset for i in f) for f in cornea_faces]
    eye = to_mesh(c, f'Eye.{side}', verts, [f[::-1] for f in faces], sclera, f'eye.{side}')
    eye.data.materials.append(wet)
    for polygon in eye.data.polygons[(sclera_rows - 1)*columns:]:
        polygon.material_index = 1
    write_colors(eye, 'Sclera pigment', np.concatenate(colors))


def iris(c, sign: int, side: str, material, seed: int) -> None:
    centre = np.array(eye_centre(sign))
    lateral, forward, up = _sign_frame(sign)
    rand = np.random.default_rng(seed)
    columns = 160
    psi = np.linspace(0, math.tau, columns, endpoint=False)
    ring_dir = lateral[None, :]*np.cos(psi)[:, None] + up[None, :]*np.sin(psi)[:, None]
    limbus_axial = math.sqrt(EYE_R**2 - LIMBUS**2)
    # radial fibres: smooth random brightness around the ring at two frequencies
    fibres = np.zeros(columns)
    for frequency, amount in ((7, .10), (23, .12), (61, .14)):
        phases = rand.uniform(0, math.tau, 3)
        fibres += amount*np.sin(frequency*psi + phases[0])*np.sin(3*psi + phases[1])
    fibres += .10*rand.standard_normal(columns)
    fibres = np.convolve(np.concatenate([fibres[-2:], fibres, fibres[:2]]), np.ones(5)/5, 'valid')
    base = np.array(c.spec['iris'])
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
    obj = to_mesh(c, f'Iris.{side}', np.concatenate(verts), [f[::-1] for f in grid_faces(len(profile), columns)],
                  material, f'eye.{side}')
    write_colors(obj, 'Iris pigment', np.concatenate(colors))


def margin_curve(sign: int, lid: str, offset: float, radius_lift: float, count: int = 48) -> Array:
    """Points along a lid margin: offset in degrees outward from the opening, radius above the support."""
    alpha = np.linspace(A_IN + 2.5, A_OUT - 1.5, count)
    beta = lid_upper(alpha) + offset if lid == 'upper' else lid_lower(alpha) - offset
    r = support_radius(alpha) + radius_lift
    return np.array(eye_centre(sign))[None, :] + eye_direction(alpha, beta, sign)*r[:, None]


def lash_lines(c, sign: int, side: str, line, wet):
    """The Eyelids part: pigmented lash lines on both lids and a tear line along the lower lid."""
    pieces = []
    for lid, lift, offset, radius in (('upper', UPPER_LID_T*.80, .40, .00042),
                                      ('lower', LOWER_LID_T*.78, .35, .00026)):
        pieces.append((margin_curve(sign, lid, offset, lift), radius, line))
    pieces.append((margin_curve(sign, 'lower', .05, .00012), .00016, wet))
    verts, faces, materials = [], [], []
    for points, radius, material in pieces:
        start = len(verts)
        n = len(points)
        for i, p in enumerate(points):
            tangent = points[min(i + 1, n - 1)] - points[max(i - 1, 0)]
            tangent /= np.linalg.norm(tangent)
            u = np.cross(tangent, p - np.array(eye_centre(sign)))
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
    obj = to_mesh(c, f'Eyelids.{side}', np.array(verts), faces, line)
    obj.data.materials.append(wet)
    for polygon, index in zip(obj.data.polygons, materials):
        polygon.material_index = index
    return obj


def head_tree(head) -> BVHTree:
    mesh = head.data
    return BVHTree.FromPolygons([v.co.copy() for v in mesh.vertices], [tuple(p.vertices) for p in mesh.polygons])


def skin_distance(tree: BVHTree, origin: Array, ray: Array, reach: float = .08) -> float:
    """Distance from origin along ray to the outer skin (cast inward from outside)."""
    start = Vector(origin + ray*reach)
    hit, _, _, _ = tree.ray_cast(start, Vector(-ray), reach)
    if hit is None:
        return float('nan')
    return reach - (hit - start).length


def caruncle(c, sign: int, side: str, material) -> None:
    centre = np.array(eye_centre(sign))
    direction = eye_direction(np.array(A_IN + 4.0), np.array(B_IN - .8), sign)
    position = centre + direction*(EYE_R + .0012)
    c.ovoid(f'Caruncle.{side}', tuple(position/c.scale), (.0016/c.scale, .0013/c.scale, .0023/c.scale),
            material, 'head', (0, 0, sign*.6))


def place_eye_bones(c) -> None:
    rig = c.rig
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    for sign, side in ((1, 'L'), (-1, 'R')):
        bone = rig.data.edit_bones[f'eye.{side}']
        centre = eye_centre(sign)
        bone.head = centre
        bone.tail = centre + Vector((0, -.04, 0))
    bpy.ops.object.mode_set(mode='OBJECT')


def build_eyes(c, head) -> Dict[str, Dict[str, Array]]:
    place_eye_bones(c)
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
        eyeball(c, sign, side, sclera, wet)
        iris(c, sign, side, iris_mat, 31 + sign)
        lids[side] = lash_lines(c, sign, side, line, wet)
        caruncle(c, sign, side, pink)
        for label in ('Eye', 'Iris', 'Eyelids'):
            face_away(bpy.data.objects[f'{c.name}_{label}.{side}'], eye_centre(sign))
    return lids



# --------------------------------------------------------------- shading

def _gauss(p: Array, centre, radii) -> Array:
    d = sum(((p[:, i] - centre[i])/radii[i])**2 for i in range(3))
    return np.exp(-d)


def lip_mask(p: Array) -> Array:
    d = np.full(len(p), 1.0)
    for centre, radii, bend in (UPPER_LIP, TUBERCLE, LOWER_LIP):
        field, _ = ellipsoid(centre, radii, bend=bend)
        d = np.minimum(d, field(p[:, 0], p[:, 1], p[:, 2]))
    return smooth(.0011, .0003, d)*smooth(.0262, .0236, np.abs(p[:, 0]))


def mouth_mask(p: Array) -> Array:
    """Inside the parted lips only: behind the lip fronts and close to the mouth line."""
    x = p[:, 0]
    yy = p[:, 1] - ARCH*x**2
    u = np.clip(np.abs(x)/.0242, 0, 1)
    line = MOUTH_Z - .0010*u*u
    return (smooth(-.0815, -.0785, yy)*smooth(.025, .022, np.abs(x))
            *smooth(.0030, .0012, np.abs(p[:, 2] - line)))


def paint_head(c, head) -> None:
    """Regional colour on the sculpted head: lips, flush, shadowed sockets, dark mouth."""
    p = np.array([v.co for v in head.data.vertices])
    base = np.array(c.spec['skin'])
    tint = np.zeros((len(p), 3))
    for sign in (1, -1):
        tint += np.outer(_gauss(p, (sign*.040, -.060, 1.404), (.019, .030, .016)), (.07, -.015, -.02))
        tint += np.outer(_gauss(p, (sign*.031, -.064, EYE_Z), (.024, .030, .016)), (-.13, -.15, -.11))
        tint += np.outer(_gauss(p, (sign*.029, -.067, 1.4235), (.018, .030, .006)), (-.05, -.07, -.04))
    tint += np.outer(_gauss(p, (0, -.095, 1.400), (.016, .020, .010)), (.06, -.01, -.015))
    tint += np.outer(_gauss(p, (0, -.085, 1.387), (.020, .020, .006)), (-.05, -.07, -.04))
    tint += np.outer(_gauss(p, (0, -.070, 1.485), (.060, .050, .030)), (-.02, -.03, -.03))
    lips = lip_mask(p)
    lip_color = np.array([.315, .125, .098])
    tint = tint*(1 - lips[:, None]) + (lip_color/base - 1)[None, :]*lips[:, None]
    margin_gloss = np.zeros(len(p))
    for sign in (1, -1):
        alpha, beta, r = eye_angles(p[:, 0], p[:, 1], p[:, 2], sign)
        near = smooth(1.6, .4, aperture_distance(alpha, beta))*smooth(EYE_R + .0024, EYE_R + .0016, r)
        margin_gloss = np.maximum(margin_gloss, near)
        lid = smooth(14, 2, aperture_distance(alpha, beta))*smooth(EYE_R + .006, EYE_R + .003, r)
        tint += np.outer(lid*(1 - near), (-.08, -.10, -.07))
    tint = tint*(1 - margin_gloss[:, None]) + (np.array([.30, .125, .10])/base - 1)[None, :]*margin_gloss[:, None]
    dark = mouth_mask(p)
    tint = tint*(1 - dark[:, None]) + (np.array([.07, .018, .016])/base - 1)[None, :]*dark[:, None]
    write_colors(head, 'Skin tint', tint)
    gloss = np.maximum(np.maximum(lips, dark), margin_gloss)
    write_colors(head, 'Skin gloss', np.repeat(gloss[:, None], 3, 1))


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



# ---------------------------------------------------------- brows, mouth

BROW = ((.0135, 1.4500), (.0225, 1.4560), (.0325, 1.4597), (.0425, 1.4597), (.0515, 1.4566), (.0575, 1.4522))


def on_skin(tree: BVHTree, x: float, z: float, lift: float = 0.0) -> Tuple[Vector, Vector]:
    """Front-facing skin point at (x, z), lifted along the normal."""
    hit, normal, _, _ = tree.ray_cast(Vector((x, -.25, z)), Vector((0, 1, 0)), .4)
    if hit is None:
        return Vector((x, -.07, z)), Vector((0, -1, 0))
    if normal.y > 0:
        normal = -normal
    return hit + normal*lift, normal


def brow_curve(u: float, sign: int) -> Tuple[float, float]:
    """Point along the brow from its head (u=0) to its tail (u=1)."""
    xs = [p[0] for p in BROW]
    zs = [p[1] for p in BROW]
    t = u*(len(BROW) - 1)
    i = min(int(t), len(BROW) - 2)
    f = t - i
    return sign*(xs[i] + (xs[i + 1] - xs[i])*f), zs[i] + (zs[i + 1] - zs[i])*f


def brow_strips(c, tree: BVHTree, material) -> None:
    """Brow.X: a faint darker band under the brow fibres (it carries the brow shape keys)."""
    for sign, side in ((1, 'L'), (-1, 'R')):
        points, radii = [], []
        for k in range(10):
            u = k/9
            x, z = brow_curve(u, sign)
            point, _ = on_skin(tree, x, z, .0003)
            points.append(tuple(point/c.scale))
            radii.append((.0011*math.sin(math.pi*(.12 + .8*u))**.6 + .0002)/c.scale)
        obj = c.tube(f'Brow.{side}', points, radii, material, 'head')
        mesh = obj.data
        for r in range(len(mesh.vertices)//10):
            ring = mesh.vertices[r*10:(r + 1)*10]
            centre = sum((v.co for v in ring), Vector())/10
            for v in ring:
                offset = v.co - centre
                v.co = centre + Vector((offset.x, offset.y*.25, offset.z))


def mouth_lining(c, material):
    """Mouth: the dark inner lining behind the lips, with the shared speech shape keys."""
    rows, columns = 12, 48
    verts = []
    for r in range(rows):
        v = -math.pi/2 + math.pi*r/(rows - 1)
        for k in range(columns):
            u = math.tau*k/columns
            x = .0195*math.cos(v)*math.cos(u)
            y = -.0585 + .0105*math.cos(v)*math.sin(u) + ARCH*.6*x*x
            z = MOUTH_Z + .0072*math.sin(v)
            verts.append((x, y, z))
    faces = grid_faces(rows, columns)
    obj = to_mesh(c, 'Mouth', np.array(verts), faces, material)
    obj.shape_key_add(name='Basis', from_mix=False)
    obj.data.shape_keys.use_relative = True
    for name, (drop, width) in {'Mouth_Ah': (.0110, 1.0), 'Mouth_O': (.0075, .78), 'Mouth_Ee': (.0030, 1.12),
                                'Mouth_MBP': (-.0004, 1.0), 'Mouth_FV': (.0018, 1.04)}.items():
        key = obj.shape_key_add(name=name, from_mix=False)
        for item, (x, y, z) in zip(key.data, verts):
            lower = max(0.0, MOUTH_Z - z)/.0072
            item.co = Vector((x*width, y, z - drop*lower))
        key.value = 0
    obj['Usage'] = 'Use one primary phoneme at a time. Basis is the relaxed mouth.'
    return obj


def _ovoid_into(verts: List, faces: List, centre, radii, columns: int = 16, rows: int = 10) -> None:
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


def teeth_and_tongue(c) -> None:
    """Upper teeth just behind the parted lips and a tongue on the mouth floor."""
    enamel = principled(f'{c.name} • Teeth', (.62, .56, .46), .25, Subsurface_Weight=.3, Subsurface_Scale=.001)
    flesh = principled(f'{c.name} • Tongue', (.30, .075, .065), .45, Subsurface_Weight=.4, Subsurface_Scale=.002)
    verts, faces = [], []
    widths = (.0043, .0035, .0040, .0036, .0034)       # central and lateral incisors, canine, premolars
    x = 0.0
    for i, w in enumerate(widths):
        cx = x + w/2
        for sign in (1, -1):
            px = sign*cx
            py = -.0758 + ARCH*1.15*px*px + .0008*i
            _ovoid_into(verts, faces, (px, py, MOUTH_Z + .0040 - .0002*i), (w*.52, .0028 - .0002*i, .0052 - .0003*i))
        x += w
    teeth = to_mesh(c, 'Upper teeth', np.array(verts), faces, enamel)
    face_away(teeth, (0, -.050, MOUTH_Z + .004))
    verts, faces = [], []
    _ovoid_into(verts, faces, (0, -.0600, MOUTH_Z - .0052), (.0160, .0140, .0040), 24, 12)
    tongue = to_mesh(c, 'Tongue', np.array(verts), faces, flesh)
    face_away(tongue, (0, -.0600, MOUTH_Z - .0052))


def _rotate_lids(points: Array, sign: int, amount: float = 1.0) -> Array:
    """Close the lids: slide the upper lid down over the eyeball and lift the lower one a little."""
    centre = np.array(eye_centre(sign))
    alpha, beta, r = eye_angles(points[:, 0], points[:, 1], points[:, 2], sign)
    a = np.clip(alpha, A_IN, A_OUT)
    up, low = lid_upper(a), lid_lower(a)
    closed = low + 2.5 + .3
    above = beta - up
    below = low - beta
    near = smooth(EYE_R + .0065, EYE_R + .0035, r)*smooth(A_IN - 12, A_IN - 3, alpha)*smooth(A_OUT + 12, A_OUT + 3, alpha)
    upper_w = np.where(beta >= CENTRE_B, smooth(17, 5, above), 0)*near
    lower_w = np.where(beta < CENTRE_B, smooth(11, 2, below), 0)*near
    new_beta = beta - (up - closed)*upper_w*amount + 2.5*lower_w*amount
    return centre[None, :] + eye_direction(alpha, new_beta, sign)*r[:, None]


def head_blinks(c, head) -> None:
    import facial_controls
    co = np.array([v.co for v in head.data.vertices])
    if head.data.shape_keys is None:
        head.shape_key_add(name='Basis', from_mix=False)
    for sign, side in ((1, 'L'), (-1, 'R')):
        moved = _rotate_lids(co, sign)
        key = head.shape_key_add(name=f'Blink_{side}', from_mix=False)
        key.data.foreach_set('co', moved.astype(np.float32).ravel())
        key.value = 0
        facial_controls.driver_from_property(key, c.rig, f'blink_{side}')


def eyelid_blinks(c) -> None:
    """Point the shared Blink keys at the new lids: lash lines close with the skin, eyeballs stay round."""
    for sign, side in ((1, 'L'), (-1, 'R')):
        for label in ('Eye', 'Iris', 'Eyelids'):
            obj = bpy.data.objects[f'{c.name}_{label}.{side}']
            keys = obj.data.shape_keys.key_blocks
            basis = np.array([v.co for v in keys['Basis'].data])
            target = _rotate_lids(basis, sign) if label == 'Eyelids' else basis
            keys['Blink'].data.foreach_set('co', target.astype(np.float32).ravel())
