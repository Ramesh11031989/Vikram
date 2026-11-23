import math

import bpy
from mathutils import Euler, Vector

from face_surface import lip_surface, pigment_material, skin_surface, vertex_pigment


HEAD_PROFILE = (
    (1.497,-.043,.012,.031), (1.508,-.029,.051,.068), (1.532,-.022,.079,.087),
    (1.557,-.014,.095,.102), (1.599,-.012,.112,.108), (1.638,-.01,.125,.110),
    (1.678,-.008,.119,.105), (1.726,-.003,.116,.102), (1.762,.003,.106,.093),
    (1.790,.005,.075,.068), (1.807,.006,.032,.034), (1.812,.006,.006,.007),
)


def gaussian(x, z, center_x, center_z, width, height):
    return math.exp(-(((x - center_x) / width)**2 + ((z - center_z) / height)**2))


def profile_at(z):
    """Cubic interpolation of the skull cross section at an actual height."""
    if z <= HEAD_PROFILE[0][0]:
        return HEAD_PROFILE[0][1:]
    if z >= HEAD_PROFILE[-1][0]:
        return HEAD_PROFILE[-1][1:]
    index = next(i for i in range(len(HEAD_PROFILE) - 1) if z <= HEAD_PROFILE[i+1][0])
    before, lower, upper, after = (HEAD_PROFILE[i] for i in
        (max(index-1,0), index, index+1, min(index+2,len(HEAD_PROFILE)-1)))
    gap = upper[0] - lower[0]
    t = (z - lower[0])/gap
    weights = (2*t**3-3*t*t+1, t**3-2*t*t+t, -2*t**3+3*t*t, t**3-t*t)
    return tuple(weights[0]*a + weights[1]*gap*(b-prev)/(upper[0]-before[0]) +
                 weights[2]*b + weights[3]*gap*(nxt-a)/(after[0]-lower[0])
                 for prev,a,b,nxt in zip(before[1:],lower[1:],upper[1:],after[1:]))


def face_relief(x, z, width, nose):
    side = abs(x)
    bridge = .031 * gaussian(x,z,0,1.652,.019*nose,.039)
    tip = .034 * gaussian(x,z,0,1.620,.024*nose,.012)
    wing = .016 * gaussian(side,z,.025*nose,1.612,.012*nose,.010)
    nostril = .0048 * gaussian(side,z,.019*nose,1.605,.008*nose,.003)
    socket = .0064 * gaussian(side,z,.053*width,1.678,.034,.015)
    cheek = .0064 * gaussian(side,z,.067*width,1.634,.030,.024)
    muzzle = .0053 * gaussian(x,z,0,1.567,.044,.026)
    philtrum = .0024 * gaussian(x,z,0,1.591,.007,.012)
    return socket + nostril + philtrum - bridge - tip - wing - cheek - muzzle


class Character:
    def __init__(self, spec):
        self.spec = spec
        self.name = spec['name']
        self.scale = spec.get('height', 1.0)
        self.scene = bpy.data.scenes.new(self.name)
        self.scene.render.fps = 24
        self.scene.unit_settings.system = 'METRIC'
        bpy.context.window.scene = self.scene
        self.collection = bpy.data.collections.new(f'CH_{self.name}')
        self.scene.collection.children.link(self.collection)
        self.collection.asset_mark()
        self.collection.asset_data.description = f'{self.name} | Vikram–Betal character, 24 fps'
        self.parts = []
        self.rig = self.make_rig()
        self.m = {key: self.mat(key.title(), spec[key], .62 if key == 'skin' else .73)
                  for key in ('skin', 'hair', 'iris')}
        skin_surface(self.m['skin'], spec['skin'])

    def mat(self, label, rgb, rough=.72, metal=0):
        material = bpy.data.materials.new(f'{self.name} • {label}')
        material.diffuse_color = (*rgb[:3], 1)
        material.use_nodes = True
        shader = material.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value = (*rgb[:3], 1)
        shader.inputs['Roughness'].default_value = rough
        shader.inputs['Metallic'].default_value = metal
        return material

    def make_rig(self):
        armature = bpy.data.armatures.new(f'{self.name}_Skeleton')
        rig = bpy.data.objects.new(f'{self.name}_Rig', armature)
        self.collection.objects.link(rig)
        rig.show_in_front = True
        armature.display_type = 'STICK'
        bpy.context.view_layer.objects.active = rig
        rig.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')

        def bone(name, start, end, parent=None, deform=True):
            item = armature.edit_bones.new(name)
            item.head = Vector(start) * self.scale
            item.tail = Vector(end) * self.scale
            item.use_deform = deform
            if parent:
                item.parent = armature.edit_bones[parent]
            return item

        bone('root', (0, 0, 0), (0, 0, .19), deform=False)
        bone('hips', (0, 0, .91), (0, 0, 1.04), 'root')
        bone('spine', (0, 0, 1.04), (0, 0, 1.22), 'hips')
        bone('chest', (0, 0, 1.22), (0, 0, 1.39), 'spine')
        bone('neck', (0, 0, 1.39), (0, -.013, 1.5), 'chest')
        bone('head', (0, -.013, 1.5), (0, -.013, 1.801), 'neck')
        for side, sign in (('L', 1), ('R', -1)):
            arm = lambda distance: (sign * distance, 0, 1.375)
            bone(f'clavicle.{side}', (sign * .045, 0, 1.37), arm(.235), 'chest')
            bone(f'upper_arm.{side}', arm(.235), arm(.48), f'clavicle.{side}')
            bone(f'forearm.{side}', arm(.48), arm(.70), f'upper_arm.{side}')
            bone(f'hand.{side}', arm(.70), arm(.81), f'forearm.{side}')
            for digit, (y, length) in enumerate(((-.035, .055), (-.012, .072), (.01, .071), (.033, .05)), 1):
                bone(f'finger_{digit:02d}.{side}', (sign * .773, y, 1.37),
                     (sign * (.773 + length), y, 1.364), f'hand.{side}')
            bone(f'thumb.{side}', (sign * .72, -.026, 1.375), (sign * .765, -.072, 1.354), f'hand.{side}')
            hip = (sign * .125, 0, .91)
            knee = (sign * .135, -.014, .52)
            ankle = (sign * .135, 0, .14)
            ball = (sign * .135, -.122, .045)
            bone(f'thigh.{side}', hip, knee, 'hips')
            bone(f'shin.{side}', knee, ankle, f'thigh.{side}')
            bone(f'foot.{side}', ankle, ball, f'shin.{side}')
            bone(f'toes.{side}', ball, (sign * .135, -.18, .045), f'foot.{side}')
            eye_x = sign * .054 * self.spec.get('face_width', 1)
            bone(f'eye.{side}', (eye_x, -.09, 1.675), (eye_x, -.144, 1.675), 'head')
        bpy.ops.object.mode_set(mode='OBJECT')
        rig['Usage'] = 'FK skeleton. Select the Mouth mesh for phoneme shape keys.'
        return rig

    def mesh(self, name, verts, faces, material, bone, smooth=True):
        data = bpy.data.meshes.new(f'{self.name}_{name}')
        data.from_pydata([Vector(p) * self.scale for p in verts], [], faces)
        data.update()
        obj = bpy.data.objects.new(data.name, data)
        self.collection.objects.link(obj)
        obj.parent = self.rig
        if material:
            data.materials.append(material)
        for face in data.polygons:
            face.use_smooth = smooth
        if isinstance(bone, str):
            obj.vertex_groups.new(name=bone).add(list(range(len(verts))), 1, 'REPLACE')
        else:
            groups = {}
            for index, weights in enumerate(bone):
                weights = {weights: 1} if isinstance(weights, str) else weights
                for joint, weight in weights.items():
                    if weight > 0:
                        groups.setdefault(joint, []).append((index, weight))
            for joint, entries in groups.items():
                group = obj.vertex_groups.new(name=joint)
                for index, weight in entries:
                    group.add([index], weight, 'REPLACE')
        deform = obj.modifiers.new('Character Skinning', 'ARMATURE')
        deform.object = self.rig
        deform.use_deform_preserve_volume = True
        self.parts.append(obj)
        return obj

    def ovoid(self, name, loc, scale, material, bone, rotation=None):
        center = Vector(loc)
        transform = Euler(rotation or (0, 0, 0)).to_matrix()
        count = 28
        rows = 16
        def point(x, y, z):
            return center + transform @ Vector((x * scale[0], y * scale[1], z * scale[2]))
        verts = [point(0, 0, 1)]
        for row in range(1, rows):
            phi = math.pi * row / rows
            for column in range(count):
                theta = math.tau * column / count
                verts.append(point(math.sin(phi) * math.cos(theta), math.sin(phi) * math.sin(theta), math.cos(phi)))
        verts.append(point(0, 0, -1))
        faces = []
        for col in range(count):
            nxt = (col + 1) % count
            faces.append((0, 1 + col, 1 + nxt))
            for row in range(rows - 2):
                a = 1 + row * count
                faces.append((a + col, a + count + col, a + count + nxt, a + nxt))
            a = 1 + (rows - 2) * count
            faces.append((a + col, len(verts) - 1, a + nxt))
        return self.mesh(name, verts, faces, material, bone)

    def ring_mesh(self, name, rings, material, bone, cap=True, cyclic=False):
        segments = len(rings[0])
        verts = [point for ring in rings for point in ring]
        total = len(rings)
        faces = []
        for i in range(total if cyclic else total - 1):
            next_ring = (i + 1) % total
            for j in range(segments):
                nxt = (j + 1) % segments
                faces.append((i*segments+j, i*segments+nxt, next_ring*segments+nxt, next_ring*segments+j))
        if cap and not cyclic:
            faces.append(tuple(reversed(range(segments))))
            faces.append(tuple(range((total-1)*segments, total*segments)))
        weights = bone if isinstance(bone, str) else [weight for weight in bone for _ in range(segments)]
        return self.mesh(name, verts, faces, material, weights)

    def loft(self, name, rings, material, bone, segments=32, cap=True):
        coordinates = []
        for z, x, y, wx, wy in rings:
            coordinates.append([(x + wx * math.cos(math.tau * i / segments),
                                 y + wy * math.sin(math.tau * i / segments), z)
                                for i in range(segments)])
        return self.ring_mesh(name, coordinates, material, bone, cap)

    def tube(self, name, points, radius, material, bone, cyclic=False):
        points = list(map(Vector, points))
        rings = []
        for i, point in enumerate(points):
            previous = points[i-1] if cyclic or i > 0 else point
            following = points[(i+1) % len(points)] if cyclic or i < len(points)-1 else point
            tangent = (following-previous).normalized()
            helper = Vector((0, 1, 0)) if abs(tangent.y) < .96 else Vector((0, 0, 1))
            u = helper.cross(tangent).normalized()
            v = tangent.cross(u)
            width = radius if isinstance(radius, (float, int)) else radius[i]
            rings.append([point + width * (u * math.cos(math.tau*j/10) + v * math.sin(math.tau*j/10))
                          for j in range(10)])
        return self.ring_mesh(name, rings, material, bone, cyclic=cyclic)

    def body(self):
        skin = self.m['skin']
        self.loft('Neck', [(1.353,0,0,.069,.059),(1.402,0,-.005,.055,.052),
                          (1.46,0,-.01,.052,.05),(1.534,0,-.013,.07,.062)], skin,
                  ['chest',{'chest':.26,'neck':.74},'neck','head'])
        for side, sign in (('L', 1), ('R', -1)):
            upper, lower, hand = (f'{bone}.{side}' for bone in ('upper_arm','forearm','hand'))
            form = [(.183,.051),(.239,.061),(.312,.06),(.397,.048),(.46,.042),(.49,.044),
                    (.545,.049),(.61,.039),(.678,.028),(.717,.026)]
            rings = [[(sign*x, sign*radius*math.cos(math.tau*i/24), 1.375+radius*math.sin(math.tau*i/24))
                      for i in range(24)] for x,radius in form]
            self.ring_mesh(f'Arm.{side}', rings, skin,
                           ['chest',{'chest':.40,upper:.60},upper,upper,
                            {upper:.72,lower:.28},{upper:.26,lower:.74}]+[lower]*3+[hand])
            self.ovoid(f'Palm.{side}', (sign*.746,-.003,1.374), (.054,.052,.027), skin, hand)
            for digit, (y, length) in enumerate(((-.035,.055),(-.012,.072),(.01,.071),(.033,.05)),1):
                self.ovoid(f'Finger_{digit}.{side}', (sign*(.773+length*.46),y,1.366),
                           (length*.58,.011,.014), skin, f'finger_{digit:02d}.{side}', (0, sign*.11, 0))
            self.tube(f'Thumb.{side}', [(sign*.72,-.026,1.374),(sign*.739,-.049,1.36),(sign*.763,-.071,1.352)],
                      [.019,.014,.009], skin, f'thumb.{side}')
            thigh, shin, foot = (f'{bone}.{side}' for bone in ('thigh','shin','foot'))
            swelling = .012 if self.name == 'Betal' and side == 'R' else 0
            self.loft(f'Leg.{side}', [(.071,sign*.135,-.010,.041,.038),
                      (.128,sign*(.135+swelling/3),0,.042+swelling,.042+swelling*.75),
                      (.158,sign*(.135+swelling/3),-.002,.042+swelling,.043+swelling*.81),
                      (.185,sign*.135,0,.041+swelling*.35,.045+swelling*.32),
                      (.323,sign*.134,.011,.052,.057),(.445,sign*.135,-.008,.051,.053),
                      (.52,sign*.135,-.014,.057,.054),(.599,sign*.131,-.002,.062,.063),
                      (.754,sign*.125,.003,.076,.078),(.898,sign*.109,0,.083,.088)], skin,
                      [foot,foot,{foot:.5,shin:.5},shin,shin,shin,{shin:.52,thigh:.48},thigh,thigh,thigh])
            if self.name != 'Vikram':
                self.ovoid(f'Foot.{side}', (sign*.135,-.058,.044), (.058,.111,.041), skin, foot)
                self.ovoid(f'Instep.{side}', (sign*.137,-.013,.063), (.045,.065,.041), skin, foot, (-.38,0,0))
                for digit in range(5):
                    x = sign * (.092 + digit*.021)
                    self.ovoid(f'Toe_{digit}.{side}', (x,-.158+digit*.008,.026),
                               (.0145-digit*.0009,.032-digit*.003,.019-digit*.0018), skin, f'toes.{side}')

    def face(self):
        width = self.spec.get('face_width', 1)
        nose = self.spec.get('nose_width', 1)
        skin = self.m['skin']
        rings = []
        for level in range(125):
            z = 1.497 + level/124 * (1.812-1.497)
            center, radius, depth = profile_at(z)
            ring = []
            for step in range(120):
                angle = math.tau*step/120
                facing = math.sin(angle)
                x = width*radius*math.cos(angle)
                y = center + depth*facing
                y += max(-facing,0)**2 * face_relief(x,z,width,nose)
                ring.append((x,y,z))
            rings.append(ring)
        self.ring_mesh('Head', rings, skin, 'head')
        base = self.spec['skin']
        lips = self.mat('Lips', tuple(a*f for a,f in zip(base,(.74,.52,.52))), .57)
        lip_surface(lips)
        inner = self.mat('Mouth interior', (.035,.008,.007), .63)
        inner_ear = self.mat('Inner ear', tuple(a*f for a,f in zip(base,(.82,.67,.63))))
        sclera = self.mat('Eye white', (.43,.40,.36), .38)
        sclera.node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value = .21
        eye_rim = self.mat('Eyelid edge', tuple(a*f for a,f in zip(base,(.82,.66,.58))), .65)
        nostril = self.mat('Nostril shadow', tuple(a*f for a,f in zip(base,(.20,.125,.125))), .81)
        iris = self.m['iris']
        iris.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value = .41
        pigment_material(iris, 'Iris pigment')
        for side, sign in (('L',1),('R',-1)):
            x = sign*.053*width
            self.ear(side,sign,width,skin,inner_ear)
            self.nostril(side,sign,nose,nostril)
            self.eye(side,sign,width,sclera,eye_rim,iris)
            brow_lift = self.spec.get('brow_lift', .0)
            brow_points = [(x-sign*.031,1.706),(x-sign*.016,1.716+brow_lift),
                           (x+sign*.005,1.719+brow_lift),(x+sign*.024,1.714+brow_lift),
                           (x+sign*.036,1.707)]
            self.tube(f'Brow.{side}',[(bx,self.face_y(bx,bz)+.0005,bz) for bx,bz in brow_points],
                      [.0025,.004,.0037,.0025,.0009], self.m['hair'],'head')
        self.mouth(lips, inner)

    def face_y(self, x, z):
        center, radius, depth = profile_at(z)
        width, nose = self.spec.get('face_width',1), self.spec.get('nose_width',1)
        frontal = math.sqrt(max(0,1-(x/(radius*width))**2))
        return center - depth*frontal + frontal**2*face_relief(x,z,width,nose)

    def ear(self, side, sign, width, skin, inner):
        angles = tuple(math.tau*i/48 for i in range(48))
        rings = []
        for size, depth, offset in ((.38,.023,0),(.85,.016,0),(1,.002,0),(.94,-.013,0),
                                    (.78,-.026,0),(.56,-.019,-.001),(.39,-.009,-.002),(.05,-.01,-.005)):
            ring = []
            for angle in angles:
                u,w = math.cos(angle), math.sin(angle)
                horizontal = .021*u*(.88+.15*max(w,0)-.22*max(-w,0)) + .004*w
                x = sign*(.121*width + size*horizontal + offset)
                z = 1.639 + .042*size*w + .001*u
                y = depth + .007*u*size + .002*w
                ring.append((x,y,z))
            rings.append(ring if sign == 1 else ring[::-1])
        ear = self.ring_mesh(f'Ear.{side}',rings,skin,'head')
        ear.data.materials.append(inner)
        for face in ear.data.polygons[6*len(angles):7*len(angles)]:
            face.material_index = 1
        crest = [(sign*(.123*width+x),y,z) for x,y,z in
                 ((-.010,-.022,1.624),(-.006,-.024,1.635),(.001,-.025,1.649),(.005,-.022,1.658))]
        self.tube(f'Ear inner fold.{side}',crest,[.0023,.004,.0034,.001],skin,'head')

    def nostril(self, side, sign, nose, material):
        rings = []
        for size in (1,.67,.08):
            ring = []
            for step in range(24):
                angle = math.tau*step/24
                u,w = math.cos(angle)*size, math.sin(angle)*size
                x = sign*(.020*u*.39 + .020)*nose
                z = 1.605 + .0024*w + .0018*u
                ring.append((x,self.face_y(x,z)-.00025,z))
            rings.append(ring if sign == 1 else ring[::-1])
        self.ring_mesh(f'Nostril.{side}',rings,material,'head',cap=False)

    def eye(self, side, sign, width, sclera, rim, iris):
        cx = sign*.053*width
        cz = 1.675
        eye_bone = f'eye.{side}'
        eye_radius = .030
        upper_lid = {'Vikram': .0109, 'Betal': .0097, 'Gopal': .0104}.get(self.name,.0105) + sign*.0003
        lower_lid = .0087 + sign*.0002
        angles = tuple(math.tau*i/64 for i in range(64))

        def eyelid(angle, size):
            u,w = math.cos(angle), math.sin(angle)
            x = cx + eye_radius*size*u
            lid_height = upper_lid if w > 0 else lower_lid
            z = cz + size*(w*lid_height*(1-.21*abs(u)) + sign*.0019*u)
            return x,z

        def surface(x, z):
            # The sclera's curved plane follows the socket at its corners.
            horizontal, vertical = (x-cx)/eye_radius, (z-cz)/.0113
            dome = max(0,1-horizontal**2-(vertical-sign*.17*horizontal)**2)
            return self.face_y(x,z) - .0017 - .0076*dome**.7

        eye_rings = []
        for size in (1,.85,.68,.52,.35,.13,.015):
            ring = []
            for angle in angles:
                x,z = eyelid(angle,size)
                ring.append((x,surface(x,z)+size**5*.0008,z))
            eye_rings.append(ring)
        self.ring_mesh(f'Eye.{side}', eye_rings, sclera, 'head', cap=False)

        lid_rings = []
        for size, depth in ((1,.0009),(1.105,.0021),(1.25,-.00025),(1.48,-.0011)):
            ring = []
            for angle in angles:
                x,z = eyelid(angle,size)
                y = self.face_y(x,z)-depth-.0012*max(0,math.sin(angle))
                ring.append((x,y,z))
            lid_rings.append(ring)
        lid = self.ring_mesh(f'Eyelids.{side}', lid_rings[::-1], self.m['skin'], 'head', cap=False)
        lid.data.materials.append(rim)
        for face in list(lid.data.polygons)[-len(angles):]:
            face.material_index = 1

        iris_rings = []
        colors = []
        for radius, shade in ((.0105,.49),(.0097,.74),(.0088,1.1),(.0073,1.02),(.0054,1.23),
                              (.0045,1.17),(.0041,.42),(.00395,.07),(.002,.062),(.00009,.063)):
            ring = []
            for angle in angles:
                x = cx + radius*math.cos(angle)
                z = cz + .81*radius*math.sin(angle)
                ring.append((x,surface(x,z)-.0007,z))
                streak = (.76+.24*math.sin(19*angle+180*radius)**2 + .19*math.sin(29*angle-465*radius)**2)
                strength = shade*(streak if radius > .0042 else 1)
                colors.append(tuple(channel*strength for channel in self.spec['iris']))
            iris_rings.append(ring)
        pigment = self.ring_mesh(f'Iris.{side}',iris_rings,iris,eye_bone,cap=False)
        vertex_pigment(pigment,'Iris pigment',colors)

    def mouth(self, lip, inner):
        segments = 64
        angles = [math.tau*i/segments for i in range(segments)]
        middle = 1.566

        def outline(width, opening, roundness):
            points = []
            for ring, (rx, rz, depth) in enumerate(((width+.0038,opening+.007,0),
                    (width+.0015,opening+.0048,.0025),(width,opening,.0044),(.0015,.00065,.0012))):
                for angle in angles:
                    u, w = math.cos(angle), math.sin(angle)
                    x = rx*u
                    z = rz*w*(1 - (1-roundness)*abs(u))
                    if ring < 3 and w > 0:
                        z = z*.86 - .00145*math.exp(-(u/.23)**2)*w
                    z += middle + .0011*u-.0014*u*u
                    y = self.face_y(x,z) - depth*(1-.6*abs(u)**2)
                    if ring in (0,3):
                        y += .00035 if ring == 0 else -.0009
                    points.append((x,y,z))
            return points

        faces = []
        for ring in range(3):
            a, b = ring*segments, (ring+1)*segments
            faces.extend((a+i,a+(i+1)%segments,b+(i+1)%segments,b+i) for i in range(segments))
        faces.append(tuple(range(3*segments,4*segments)))
        obj = self.mesh('Mouth', outline(.033,.00125,.66), faces, lip, 'head')
        obj.data.materials.append(inner)
        for face in obj.data.polygons[segments*2:]:
            face.material_index = 1
        base = self.spec['skin']
        factors = ((1.0,.945,.91),(.84,.63,.60),(.73,.50,.48),(.6,.43,.43))
        color_samples = []
        for ring, tint in enumerate(factors):
            for angle in angles:
                darker_upper = 1-.13*max(math.sin(angle),0) if ring else 1
                color_samples.append(tuple(value*gain*darker_upper for value,gain in zip(base,tint)))
        vertex_pigment(obj,'Lip pigment',color_samples)
        obj.shape_key_add(name='Basis', from_mix=False)
        obj.data.shape_keys.use_relative = True
        for key, shape in {'Mouth_Ah':(.033,.024,.83),'Mouth_O':(.019,.022,1),
                           'Mouth_Ee':(.047,.009,.7),'Mouth_MBP':(.034,.0004,.66),
                           'Mouth_FV':(.039,.004,.73)}.items():
            blend = obj.shape_key_add(name=key, from_mix=False)
            for vertex, coordinate in zip(blend.data, outline(*shape)):
                vertex.co = Vector(coordinate) * self.scale
            blend.value = 0
        obj['Usage'] = 'Use one primary phoneme at a time. Basis is the relaxed mouth.'

    def validate(self):
        names = set(self.rig.data.bones.keys())
        for obj in self.parts:
            if not len(obj.data.vertices):
                raise ValueError(f'Empty mesh {obj.name}')
            for group in obj.vertex_groups:
                if group.name not in names:
                    raise ValueError(f'{obj.name} refers to nonexistent bone {group.name}')
            for vertex in obj.data.vertices:
                if abs(sum(item.weight for item in vertex.groups) - 1) > .0001:
                    raise ValueError(f'{obj.name} has invalid weights at vertex {vertex.index}')
