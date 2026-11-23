import math

import bpy
from mathutils import Euler, Vector


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
        self.m = {key: self.mat(key.title(), spec[key], 0.58 if key == 'skin' else 0.73)
                  for key in ('skin', 'hair', 'iris')}

    def mat(self, label, rgb, rough=.72, metal=0):
        material = bpy.data.materials.new(f'{self.name} • {label}')
        material.diffuse_color = (*rgb[:3], 1)
        material.use_nodes = True
        shader = material.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value = (*rgb[:3], 1)
        shader.inputs['Roughness'].default_value = rough
        shader.inputs['Metallic'].default_value = metal
        if label == 'Skin':
            shader.inputs['Subsurface Weight'].default_value = .07
            shader.inputs['Subsurface Scale'].default_value = .045
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
        raw = [(1.497,-.043,.012,.031),(1.508,-.029,.051,.068),(1.532,-.022,.079,.087),
               (1.557,-.014,.095,.102),(1.599,-.012,.112,.108),(1.638,-.01,.125,.110),
               (1.678,-.008,.119,.105),(1.726,-.003,.116,.102),(1.762,.003,.106,.093),
               (1.790,.005,.075,.068),(1.807,.006,.032,.034),(1.812,.006,.006,.007)]
        self.loft('Head', [(z,0,y,x*width,depth) for z,y,x,depth in raw], skin, 'head', segments=64)
        lips = self.mat('Lips', tuple(a*f for a,f in zip(self.spec['skin'],(.65,.49,.47))), .63)
        inner = self.mat('Mouth interior', (.046,.013,.011), .68)
        inner_ear = self.mat('Inner ear', tuple(a*f for a,f in zip(self.spec['skin'],(.77,.66,.63))))
        porcelain = self.mat('Eye white', (.67,.62,.51), .35)
        dark = self.mat('Pupil', (.014,.009,.006), .32)
        gleam = self.mat('Eye glint', (.86,.84,.72), .32)
        self.ovoid('Nose bridge',(0,-.112,1.642),(.022*nose,.035,.044),skin,'head',(-.24,0,0))
        self.ovoid('Nose tip',(0,-.147,1.619),(.029*nose,.027,.019),skin,'head')
        for side, sign in (('L',1),('R',-1)):
            x = sign*.053*width
            self.ovoid(f'Ear.{side}',(sign*.122*width,.001,1.637),(.022,.029,.043),skin,'head',(0,sign*.14,0))
            self.ovoid(f'Ear fold.{side}',(sign*.128*width,-.024,1.638),(.011,.007,.024),inner_ear,'head',(0,sign*.14,0))
            self.ovoid(f'Nose wing.{side}',(sign*.022*nose,-.13,1.614),(.019,.023,.013),skin,'head')
            self.ovoid(f'Nostril.{side}',(sign*.018*nose,-.151,1.606),(.009,.007,.004),inner,'head')
            tilt = sign*.055
            self.ovoid(f'Eye.{side}',(x,-.100,1.675),(.035,.018,.014),porcelain,'head',(0,tilt,0))
            self.ovoid(f'Iris.{side}',(x,-.1168,1.675),(.0128,.004,.012),self.m['iris'],f'eye.{side}')
            self.ovoid(f'Pupil.{side}',(x,-.120,1.675),(.0068,.0025,.0073),dark,f'eye.{side}')
            self.ovoid(f'Eye glint.{side}',(x-.0041,-.1228,1.6806),(.003,.0015,.003),gleam,f'eye.{side}')
            self.tube(f'Upper lid.{side}',[(x-.036,-.095,1.674),(x-.022,-.107,1.685),(x,-.111,1.689),
                      (x+.022,-.108,1.685),(x+.036,-.095,1.675)], [.003,.004,.0045,.004,.0025], inner_ear, 'head')
            brow_lift = self.spec.get('brow_lift', .0)
            self.tube(f'Brow.{side}',[(x-sign*.031,-.106,1.706),(x-sign*.016,-.109,1.716+brow_lift),
                      (x+sign*.005,-.102,1.719+brow_lift),(x+sign*.024,-.092,1.714+brow_lift),
                      (x+sign*.036,-.082,1.707)], [.005,.008,.007,.005,.0015], self.m['hair'],'head')
        self.mouth(lips, inner)

    def mouth(self, lip, inner):
        segments = 32
        angles = [math.tau*i/segments for i in range(segments)]
        middle = 1.566
        def outline(width, opening, roundness):
            points = []
            for rx, rz, depth in ((width+.009,opening+.008,-.120),(width,opening,-.132),(.003,.001,-.124)):
                for angle in angles:
                    x = rx*math.cos(angle)
                    z = rz * math.sin(angle) * (1 - (1-roundness)*abs(math.cos(angle)))
                    cupids_bow = .0027*math.sin(2*angle)**2 if z > 0 and abs(x) > .003 else 0
                    points.append((x, depth + 2.5*x*x, middle + z + cupids_bow))
            return points
        faces = []
        for ring in range(2):
            a, b = ring*segments, (ring+1)*segments
            faces.extend((a+i,a+(i+1)%segments,b+(i+1)%segments,b+i) for i in range(segments))
        faces.append(tuple(range(2*segments,3*segments)))
        obj = self.mesh('Mouth', outline(.034,.0028,.65), faces, lip, 'head')
        obj.data.materials.append(inner)
        for face in obj.data.polygons[segments:]:
            face.material_index = 1
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
