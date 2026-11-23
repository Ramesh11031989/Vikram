"""Vikram's fitted royal head wrap and anatomically placed mesh groom."""

import math
import random

from mathutils import Vector
from mathutils.bvhtree import BVHTree

from groom import FiberGroup


FRONT = Vector((0, -1, 0))
UP = Vector((0, 0, 1))


def smoothstep(edge_a, edge_b, value):
    t = min(1.0, max(0.0, (value - edge_a) / (edge_b - edge_a)))
    return t * t * (3 - 2 * t)


def wrap_material(character, name, color):
    material = character.mat(name, color, rough=.76)
    tree = material.node_tree
    shader = tree.nodes.get('Principled BSDF')
    shader.inputs['Specular IOR Level'].default_value = .19
    shader.inputs['Sheen Weight'].default_value = .16
    shader.inputs['Sheen Roughness'].default_value = .61
    coordinates = tree.nodes.new('ShaderNodeTexCoord')
    dye = tree.nodes.new('ShaderNodeTexNoise')
    dye.inputs['Scale'].default_value = 61
    dye.inputs['Detail'].default_value = 3
    tree.links.new(coordinates.outputs['Object'], dye.inputs['Vector'])
    dye_colors = tree.nodes.new('ShaderNodeValToRGB')
    dye_colors.color_ramp.elements[0].position = .17
    dye_colors.color_ramp.elements[0].color = (*(component*.70 for component in color), 1)
    dye_colors.color_ramp.elements[1].position = .83
    dye_colors.color_ramp.elements[1].color = (*(component*1.23 for component in color), 1)
    tree.links.new(dye.outputs['Fac'], dye_colors.inputs[0])
    tree.links.new(dye_colors.outputs['Color'], shader.inputs['Base Color'])

    fiber = tree.nodes.new('ShaderNodeTexNoise')
    fiber.inputs['Scale'].default_value = 1820
    fiber.inputs['Detail'].default_value = 1.25
    tree.links.new(coordinates.outputs['Object'], fiber.inputs['Vector'])
    relief = tree.nodes.new('ShaderNodeBump')
    relief.inputs['Strength'].default_value = .24
    relief.inputs['Distance'].default_value = .0011
    tree.links.new(fiber.outputs['Fac'], relief.inputs['Height'])
    tree.links.new(relief.outputs['Normal'], shader.inputs['Normal'])
    return material


class Crown:
    """A fitted textile shell. Each wrap overlaps the one below it."""

    def __init__(self, character, surface):
        self.character = character
        self.surface = surface
        self.brow = character.landmarks['eye.L'][2]
        self.top = character.landmarks['head_top'] + .050
        self.center_y = -.033
        self.fabric = wrap_material(character, 'Turban • indigo teal dyed cotton', (.012, .041, .046))
        self.tucked = wrap_material(character, 'Turban • outer fold with worn dye', (.019, .058, .061))
        self.edge = wrap_material(character, 'Turban • folded selvedge', (.026, .066, .065))

    def bottom(self, theta):
        return self.brow + .020 + .026 * ((1 + math.cos(theta-.27))*.5) + .006*math.sin(theta-.45)

    def fold(self, theta, index):
        return .14 + .164*index + .058*math.sin(theta+.68+index*.38) + .024*math.sin(2*theta-index*.29)

    def coordinates(self, theta, height, extra=0):
        bottom = self.bottom(theta)
        z = bottom + (self.top-bottom)*height
        taper = max(0, (height-.73)/.27)
        section = math.sqrt(max(.002, 1 - taper*taper))
        shape = (.87 + .15*math.sin(math.pi*min(1, height*1.18))**.85)*section
        compression = .0014*math.cos(3*theta+.6)*(1-height)
        compression += .0009*math.sin(7*theta+height*7)
        for index in range(4):
            valley = (height-self.fold(theta,index))/.030
            turnover = (height-self.fold(theta,index)-.040)/.046
            compression += .0045*math.exp(-turnover**2) - .0029*math.exp(-valley**2)
        radial = compression + extra
        lean = -.012*height**1.7
        x = lean + (.106*shape+radial)*math.sin(theta)
        y = self.center_y + .012*height - (.123*shape+radial)*math.cos(theta)
        tilt = height*(1-smoothstep(.87,1,height))
        z += tilt*(.007*math.sin(theta-.15) + .005*math.cos(2*theta+.2))
        point = Vector((x,y,z))
        if height < .14:
            contact, normal = self.surface.radial(theta,z)
            if contact is not None:
                fitted = contact + normal*(.012+extra)
                fitted.z = z
                point = fitted.lerp(point,smoothstep(0,.14,height))
        return point

    def fitted_cloth(self):
        count = 120
        layers = 84
        rings = [[self.coordinates(math.tau*step/count, row/layers) for step in range(count)]
                 for row in range(layers+1)]
        self.character.ring_mesh('Turban • continuous folded crown', rings, self.fabric, 'head', cap=True)

        # Two asymmetric passes describe a handed wrapping pattern at the front.
        for layer, (theta_start, theta_end) in enumerate(((-1.71, 1.77), (-1.44, 1.35))):
            rows = []
            ridge = []
            for index in range(113):
                s = index/112
                theta = theta_start+(theta_end-theta_start)*s
                ease = smoothstep(0,.14,s)*smoothstep(1,.86,s)
                slope = ((s-.5)*.48 if layer == 0 else (.5-s)*.35)
                middle = .33 + layer*.33 + slope + .035*math.sin(math.tau*s+.5)
                half = (.089 if layer == 0 else .100)*(ease*.68+.32)
                points = []
                for section in range(13):
                    u = section/12
                    swell = math.sin(math.pi*u)**.60
                    wrinkle = .0006*math.sin(3*math.tau*u+s*2)
                    extra = ease*(.0015+.0045*swell+wrinkle)-.0020*(1-ease)
                    points.append(self.coordinates(theta,middle+(u*2-1)*half,extra))
                rows.append(points)
                ridge.append(points[1])
            vertices = [point for row in rows for point in row]
            faces = [(13*i+j,13*(i+1)+j,13*(i+1)+j+1,13*i+j+1)
                     for i in range(len(rows)-1) for j in range(12)]
            self.character.mesh(f'Turban • diagonal woven pass {layer+1}',vertices,faces,
                                self.tucked if layer == 0 else self.fabric,'head')
            seam = [point for i,point in enumerate(ridge) if 7 <= i <= 105]
            self.character.tube(f'Turban • tucked diagonal hem {layer+1}',seam,.00063,self.edge,'head')

        lip = [self.coordinates(math.tau*step/104,.029,.0009) for step in range(104)]
        self.character.tube('Turban • folded lower seam', lip, .0018, self.edge, 'head', cyclic=True)

    def seal(self):
        character = self.character
        theta = -.29
        normal = Vector((math.sin(theta),-math.cos(theta),0))
        across = Vector((math.cos(theta),math.sin(theta),0))
        center = self.coordinates(theta,.527,.0064)
        bronze = character.mat('Seal • warm hand-worked bronze', (.30,.144,.055), rough=.40, metal=.74)
        inset = character.mat('Seal • dark oxide recess', (.063,.040,.018), rough=.55, metal=.58)
        bright = character.mat('Seal • engraved bronze relief', (.42,.218,.085), rough=.33, metal=.74)

        def point(angle, radius, depth):
            return center + radius*(math.cos(angle)*across + math.sin(angle)*UP) + depth*normal

        count = 64
        rings = [[point(math.tau*i/count,radius,depth) for i in range(count)]
                 for radius,depth in ((.0196,-.0024),(.0201,-.0015),(.0198,.0008),(.0181,.0022),
                                      (.0168,.0031),(.0157,.0026),(.0151,.0017))]
        character.ring_mesh('Bronze seal • raised stamped rim',rings,bronze,'head',cap=True)
        disk = [point(math.tau*i/count,.0154,.0019) for i in range(count)]
        character.mesh('Bronze seal • recessed face',disk,[tuple(range(count))],inset,'head',smooth=False)
        character.tube('Bronze seal • inner beaded ring', [point(math.tau*i/76,.0145,.0024) for i in range(76)],
                       .00042,bright,'head',cyclic=True)

        for petal in range(6):
            direction = math.tau*petal/6 + .02
            petal_path = [point(direction+math.sin(math.tau*i/22)*.25,
                                .0065 + .0038*(1-math.cos(math.tau*i/22)), .0028)
                          for i in range(22)]
            character.tube(f'Bronze seal • stamped floral petal {petal+1}',petal_path,.0006,bright,'head',cyclic=True)
        nucleus = [point(math.tau*i/32,.0028,.0037) for i in range(32)]
        character.mesh('Bronze seal • raised seed',nucleus,[tuple(range(32))],bright,'head',smooth=False)


class HeadSurface:
    def __init__(self, character):
        self.character = character
        mesh = character.skin_mesh.data
        points = [vertex.co.copy() for vertex in mesh.vertices]
        self.bvh = BVHTree.FromPolygons(points,[tuple(poly.vertices) for poly in mesh.polygons])
        self.origin_y = -.036

    def front(self, x, z):
        point, normal, _, _ = self.bvh.ray_cast(Vector((x,-.48,z)),-FRONT,.72)
        if point is None:
            return None, None
        if normal.dot(FRONT) < 0:
            normal.negate()
        return point, normal

    def radial(self, angle, z):
        direction = Vector((math.sin(angle),-math.cos(angle),0))
        origin = Vector((0,self.origin_y,z))
        point, normal, _, _ = self.bvh.ray_cast(origin+.29*direction,-direction,.29)
        if point is not None and normal.dot(direction) < 0:
            normal.negate()
        return point, normal


def scalp_hair(surface, crown, fibers, rng):
    def lower(angle):
        a = min(math.tau-abs(angle),abs(angle))
        temple = smoothstep(.42,1.00,a)
        nape = smoothstep(1.65,2.62,a)
        return crown.brow + .051 - .036*temple - .046*nape + .002*math.sin(angle*7)

    directions, rows = 120, 15
    vertices = []
    for row in range(rows+1):
        t = row/rows
        for index in range(directions):
            angle = math.tau*index/directions
            start = lower(angle)
            z = start + (min(crown.top-.049,crown.bottom(angle)+.020)-start)*t
            point, normal = surface.radial(angle,z)
            if point is None:
                point = Vector((.070*math.sin(angle),-.036-.086*math.cos(angle),z))
                normal = Vector((math.sin(angle),-math.cos(angle),0))
            # Recede into the real scalp at the bottom to avoid a wig-like lip.
            vertices.append(point+normal*(-.0019+.0035*smoothstep(0,.28,t)))
    faces = [(row*directions+col,row*directions+(col+1)%directions,
              (row+1)*directions+(col+1)%directions,(row+1)*directions+col)
             for row in range(rows) for col in range(directions)]
    dark = surface.character.mat('Scalp • temple root mass',(.016,.010,.008),rough=.72)
    surface.character.mesh('Scalp • fitted temple and nape undercoat',vertices,faces,dark,'head')

    for _ in range(4500):
        angle = rng.uniform(-math.pi,math.pi)
        if rng.random() > smoothstep(.58,.90,abs(angle)):
            continue
        low, high = lower(angle)-.003, crown.bottom(angle)+.007
        if high <= low:
            continue
        z = rng.uniform(low,high)
        growth = rng.uniform(.006,.019)
        flow = (.081 if angle >= 0 else -.081)*rng.uniform(.75,2.2)
        lift = rng.uniform(.0007,.0018)
        strand = []
        for i in range(6):
            t = i/5
            point, normal = surface.radial(angle+flow*t, z-growth*t)
            if point is None:
                break
            strand.append(point+normal*(.00065+.0013*smoothstep(low,low+.013,z)+lift*math.sin(math.pi*t)))
        if len(strand) == 6:
            shade = rng.choices((0,1,2,3,4,5,6),(10,20,25,20,15,7,3))[0]
            fibers.add(strand,rng.uniform(.000066,.000145),shade,min(6,shade+1))
    fibers.make_mesh('Scalp • swept temple and nape fibers')


def traced_face_strand(surface, x, z, growth_x, growth_z, lift, bend=0):
    strand = []
    anchor, normal = surface.front(x,z)
    if anchor is None:
        return strand
    for i in range(6):
        t = i/5
        offset_x = growth_x*t + bend*math.sin(math.pi*t)
        offset_z = growth_z*t
        point, direction = surface.front(x+offset_x,z+offset_z)
        if point is None or (point-anchor).length > .028:
            point, direction = anchor+Vector((offset_x,0,offset_z)), normal
        height = .00025 + lift*(.72*math.sin(math.pi*t)+.48*t*t)
        strand.append(point+direction*height)
    return strand


def face_hair(surface, fibers, rng):
    face = surface.character.landmarks
    chin_z = face['chin'][2]
    mouth_z = face['mouth'][2]
    eyes = face['eye.L'][2]

    for _ in range(18600):
        x = rng.uniform(-.077,.077)
        side = min(1,abs(x)/.075)
        high = mouth_z-.008 + .062*side**1.9
        high += .006*smoothstep(.77,1,side)*math.sin(x*55-.1)
        low = chin_z-.009 + .042*side**2.40
        z = rng.uniform(low-.005,high+.007)
        density = smoothstep(low-.005,low+.010,z)
        density *= smoothstep(high+.007,high-.009,z)
        density *= smoothstep(.078,.064,abs(x))
        if abs(x) < .037:
            lip = ((x/.037)**2 + ((z-mouth_z)/.016)**2)
            density *= smoothstep(.77,1.37,lip)
        if rng.random() > density*.83:
            continue

        # Sensitive skin passes gradually from cropped upper cheeks into
        # longer hair under the jaw. There is no solid beard boundary.
        length = rng.uniform(.0035,.0105) * (1.06-.49*smoothstep(low,high,z)*side)
        if z < chin_z+.009:
            length *= .91
        outward = (1 if x >= 0 else -1) * length * rng.uniform(.12,.51)
        strand = traced_face_strand(surface,x,z,outward,-length*.72,
                                    length*.28,rng.uniform(-.0007,.0007))
        if strand:
            shade = rng.choices((0,1,2,3,4,5,6),(10,22,27,20,11,7,3))[0]
            fibers.add(strand, rng.uniform(.000058,.000132),shade,min(6,shade+1))
    fibers.make_mesh('Beard • graduated close-trim strands')

    moustache_z = min(face['nose_tip'][2]-.014,mouth_z+.021)
    for _ in range(1350):
        side = rng.choice((-1,1))
        s = rng.random()
        if rng.random() > smoothstep(0,.13,s)*smoothstep(1,.83,s):
            continue
        x = side*(.003+.029*s)
        z = moustache_z-.006*s + .0020*math.sin(math.pi*s) + side*.00045
        z += rng.uniform(-.0038,.0035)*math.sin(math.pi*(.08+.85*s))
        strand = traced_face_strand(surface,x,z,side*rng.uniform(.002,.0065),-rng.uniform(.002,.006),
                                    rng.uniform(.0011,.0024))
        if strand:
            shade = rng.choice((0,1,1,2,2,3,4,4,5,6))
            fibers.add(strand,rng.uniform(.000065,.000135),shade,max(0,shade-1))
    fibers.make_mesh('Moustache • brushed individual strands')

    for side, eye_side in ((1,'L'),(-1,'R')):
        x_eye = abs(face[f'eye.{eye_side}'][0])
        for _ in range(390):
            s = rng.random()
            x = side*(x_eye-.022+.048*s)
            z = eyes+.0155+.0094*math.sin(math.pi*(s*.91+.03))-.0017*s
            z += rng.uniform(-.0025,.0025)*(.20+.80*math.sin(math.pi*s)**.80)
            strand = traced_face_strand(surface,x,z,side*rng.uniform(.003,.007),
                                        rng.uniform(.0004,.0036)*(1-2*s),rng.uniform(.0006,.0013))
            if strand:
                shade = rng.randrange(1,5)
                fibers.add(strand,rng.uniform(.00006,.00012),shade,min(shade+1,6))
        fibers.make_mesh(f'Brow.{eye_side} • rooted groom fibers')


def dress_head(character):
    """Fit head-bone-weighted costume and individual hair geometry."""
    surface = HeadSurface(character)
    crown = Crown(character,surface)
    crown.fitted_cloth()
    crown.seal()
    rng = random.Random(73489)
    fibers = FiberGroup(character,(.017,.011,.008),(.121,.085,.060))
    scalp_hair(surface,crown,fibers,rng)
    face_hair(surface,fibers,rng)
