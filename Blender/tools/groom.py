"""Fine, tapered mesh fibers that skin with the character on FBX export."""

import math
import random

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


STYLES = {
    'Vikram': (891, 1050, 890, 210, (.020,.011,.008), (.063,.033,.019)),
    'Betal': (907, 2160, 480, 0, (.025,.024,.023), (.220,.203,.182)),
    'Gopal': (946, 1670, 0, 195, (.016,.010,.008), (.069,.037,.023)),
}


def mix(a, b, t):
    return (1-t)*a + t*b


def separate_surface(character):
    head = next(part.data for part in character.parts if part.name == f'{character.name}_Head')
    coords = [v.co / character.scale for v in head.vertices]
    polygons = [tuple(face.vertices) for face in head.polygons]
    return BVHTree.FromPolygons(coords, polygons)


def surface(head, angle, z):
    radial = Vector((math.sin(angle), -math.cos(angle), 0))
    center = Vector((0,.005,z))
    point, normal, _, _ = head.ray_cast(center + radial*.27, -radial, .28)
    if point is None:
        return center, radial
    if normal.dot(radial) < 0:
        normal.negate()
    return point, normal


def clean_previous_groom(character):
    prefix = character.name + '_'
    terms = ('hair |', 'beard |', 'rear hair', 'sideburn', 'beard jaw shell',
             'beard cut groove', 'moustache', 'brushed hair', 'cropped hair')
    for obj in list(character.parts):
        basename = obj.name.removeprefix(prefix).lower()
        if any(term in basename for term in terms):
            character.parts.remove(obj)
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)


class FiberGroup:
    def __init__(self, character, root, highlights):
        self.character = character
        self.verts, self.faces, self.indices, self.uv = [], [], [], []
        shades = (0,.11,.21,.37,.50,.72,1)
        self.materials = []
        for index, value in enumerate(shades):
            color = tuple(mix(a,b,value) for a,b in zip(root,highlights))
            material = character.mat(f'Hair fiber {index+1}', color, rough=.47+index*.016)
            nodes = material.node_tree.nodes
            shader = nodes.get('Principled BSDF')
            tangent = nodes.new('ShaderNodeTangent')
            tangent.direction_type = 'UV_MAP'
            tangent.uv_map = 'FiberUV'
            material.node_tree.links.new(tangent.outputs['Tangent'], shader.inputs['Tangent'])
            anisotropy = shader.inputs.get('Anisotropic IOR Level') or shader.inputs.get('Anisotropic')
            if anisotropy is not None:
                anisotropy.default_value = .53
            shader.inputs['Specular IOR Level'].default_value = .33
            shader.inputs['Sheen Weight'].default_value = .08
            self.materials.append(material)

    def add(self, strand, width, shade, tip):
        sides = 3
        count = len(strand)
        tangents = [strand[min(row+1,count-1)]-strand[max(row-1,0)] for row in range(count)]
        if any(tangent.length < .0000001 for tangent in tangents):
            return
        start = len(self.verts)
        for row, (point,tangent) in enumerate(zip(strand,tangents)):
            tangent.normalize()
            u = tangent.cross(Vector((0,0,1)))
            if u.length < .01:
                u = tangent.cross(Vector((1,0,0)))
            u.normalize()
            v = tangent.cross(u)
            t = row/(count-1)
            radius = width*(.12+.88*(1-t)**.7)
            for side in range(sides):
                angle = math.tau*side/sides
                self.verts.append(point + radius*(math.cos(angle)*u + math.sin(angle)*v))
                self.uv.append((t,side/sides))
        for row in range(count-1):
            for side in range(sides):
                a, b = start+row*sides, start+(row+1)*sides
                nxt = (side+1) % sides
                self.faces.append((a+side, a+nxt, b+nxt, b+side))
                self.indices.append(tip if row == count-2 else shade)

    def make_mesh(self, name):
        if not self.faces:
            return
        obj = self.character.mesh(name,self.verts,self.faces,self.materials[0],'head')
        for material in self.materials[1:]:
            obj.data.materials.append(material)
        uv = obj.data.uv_layers.new(name='FiberUV')
        for polygon, index in zip(obj.data.polygons,self.indices):
            polygon.material_index = index
            for loop in polygon.loop_indices:
                uv.data[loop].uv = self.uv[obj.data.loops[loop].vertex_index]
        obj['Groom'] = 'Tapered strands. Head bone deformation and FiberUV retained for interchange.'
        for collection in (self.verts,self.faces,self.indices,self.uv):
            collection.clear()


def hairline(role, angle):
    back = (.5-.5*math.cos(angle))**.8
    if role == 'Betal':
        return .92+1.28*back+.075*math.sin(3*angle+.4)+.04*math.sin(8*angle)
    if role == 'Vikram':
        return .82+1.36*back-.10*math.cos(2*angle)
    return .94+1.18*back+.034*math.sin(7*angle-.5)


def scalp_point(head, role, angle, phi):
    z = 1.638 + .1735*math.cos(phi)
    point, normal = surface(head, angle, z)
    extent = (.008 if role == 'Vikram' else .012 if role == 'Gopal' else .017)
    edge = hairline(role,angle)
    taper = max(0,min(1,(edge-phi)*4))
    sweep = math.sin(6*angle+4.6*phi) + .5*math.sin(13*angle-3.8*phi)
    lift = .0017 + (extent+.0013*sweep)*taper
    return point+normal*lift, normal


def fitted_wrap(point, rings):
    if not rings:
        return point
    bottom, top = rings[0][0], rings[-1][0]
    cutoff = .009
    outside = max(bottom-point.z, point.z-top, 0)
    if outside >= cutoff:
        return point

    z = max(bottom,min(top,point.z))
    low, high = next((a,b) for a,b in zip(rings,rings[1:]) if a[0] <= z <= b[0])
    ratio = (z-low[0]) / (high[0]-low[0])
    x,y,rx,ry = (mix(a,b,ratio) for a,b in zip(low[1:],high[1:]))
    dx,dy = point.x-x, point.y-y
    radius = math.hypot(dx/(rx-.0018),dy/(ry-.0018))
    if radius <= 1:
        return point
    ramp = outside/cutoff
    scale = mix(1/radius,1,ramp*ramp*(3-2*ramp))
    return Vector((x+dx*scale,y+dy*scale,point.z))


def scalp(character, head, rand, fibers, count):
    role = character.name
    wrap = character.spec.get('head_wrap')
    # A little shadow at the roots keeps the widely separated tips legible.
    dark = tuple(a*.8 for a in STYLES[role][4])
    foundation = character.mat('Scalp beneath the fibers',dark,rough=.9)
    meridians, rows = 80,24
    vertices = [(0,.005,1.813+(.012 if role == 'Vikram' else .023 if role == 'Betal' else .018))]
    for row in range(1,rows+1):
        for col in range(meridians):
            angle = math.tau*col/meridians
            phi = hairline(role,angle)*row/rows
            point,_ = scalp_point(head,role,angle,phi)
            vertices.append(fitted_wrap(point,wrap))
    faces = [(0,1+i,1+(i+1)%meridians) for i in range(meridians)]
    for index in range(rows-1):
        start = 1+index*meridians
        for i in range(meridians):
            j = (i+1)%meridians
            faces.append((start+i,start+i+meridians,start+j+meridians,start+j))
    character.mesh('Scalp undercoat',vertices,faces,foundation,'head')

    for _ in range(count):
        angle = rand.uniform(-math.pi,math.pi)
        edge = hairline(role,angle)
        phi = mix(.085,edge*.98,rand.random()**.61)
        side = 1 if angle > -.53 else -1
        flyaway = rand.random() < .09
        length = rand.uniform(.40,1.1)*(1.23 if flyaway else 1)
        if role == 'Betal':
            drift = rand.uniform(.37,.82)*side*length
            down = (rand.uniform(-.32,-.12) if abs(angle)<1.05 else rand.uniform(.12,.34))*length
            max_lift = rand.uniform(.002,.007) if flyaway else rand.uniform(.0013,.003)
            shades = (0,1,1,2,2,3,3,4,4,4,5,6)
        else:
            drift = rand.uniform(.16,.45)*side*length
            down = (rand.uniform(-.24,-.06) if abs(angle)<.9 else rand.uniform(.06,.24))*length
            max_lift = rand.uniform(.0016,.004) if flyaway else rand.uniform(.00055,.0021)
            shades = (0,1,1,2,2,2,3,3,4,5)
        path = []
        wave = rand.uniform(-.1,.1)
        for i in range(8):
            t = i/7
            theta = angle+drift*t+wave*math.sin(math.pi*t)
            pitch = max(.06,min(hairline(role,theta)+(.055 if flyaway else -.002),phi+down*t))
            point, normal = scalp_point(head,role,theta,pitch)
            lift = .00035 + max_lift*(math.sin(math.pi*t)*.75+t*.34)
            path.append(fitted_wrap(point+normal*lift,wrap))
        shade = rand.choice(shades)
        fibers.add(path,rand.uniform(.000115,.00029)*(1.1 if flyaway else 1),shade,min(6,shade+rand.randrange(2)))


def beard_outline(angle, role):
    distance = min(1,abs(angle)/1.40)
    low = 1.501+.045*distance**2
    high = 1.543+.125*distance**1.7
    if role == 'Betal':
        high -= .004 + .005*math.cos(4*angle)
    elif role == 'Vikram':
        high += .0013*math.sin(31*angle)+.0023*math.sin(9*angle)
    return low,high


def beard(character, head, rand, fibers, count):
    if not count:
        return
    role = character.name
    limit = 1.46
    if role == 'Vikram':
        color = (.032,.017,.012)
        undercoat = character.mat('Close-cut beard root shadow',color,rough=.87)
        verts = []
        cols, rows = 48,10
        for col in range(cols+1):
            angle = mix(-limit,limit,col/cols)
            low,high = beard_outline(angle,role)
            for row in range(rows+1):
                t = row/rows
                point,normal = surface(head,angle,mix(low,high,t))
                taper = .0025*math.sin(math.pi*t)**.64-.0011
                verts.append(point+normal*taper)
        stride = rows+1
        faces = [(i*stride+j,(i+1)*stride+j,(i+1)*stride+j+1,i*stride+j+1)
                 for i in range(cols) for j in range(rows)]
        character.mesh('Tapered jaw beard roots',verts,faces,undercoat,'head')

    for _ in range(count):
        angle = rand.uniform(-limit,limit)
        low,high = beard_outline(angle,role)
        z = rand.uniform(low,high)
        length = rand.uniform(.002,.009 if role == 'Vikram' else .017)
        curl = rand.uniform(-.045,.045)
        path = []
        for i in range(5):
            t = i/4
            point,normal = surface(head,angle+curl*t*t,max(1.498,z-length*t*.75))
            path.append(point+normal*(.0012+length*(.57*t+.16*math.sin(math.pi*t))))
        shade = rand.randrange(1,6 if role == 'Vikram' else 7)
        fibers.add(path,rand.uniform(.000095,.00023),shade,min(6,shade+1))


def moustache(character, fibers, rand, count):
    role = character.name
    for index in range(count):
        side = 1 if index%2 else -1
        u = rand.random()
        x = .004+.048*u
        z = 1.591-.009*u**1.3+rand.uniform(-.003,.006)
        drop = rand.uniform(.003,.010 if role == 'Gopal' else .006)
        dx = rand.uniform(.006,.016)*(1-.34*u)
        path = []
        for item in range(6):
            t = item/5
            hair_x = side*(x+dx*t)
            hair_z = z-drop*t+(.004 if role == 'Vikram' else 0)*(t*u)**3
            lift = .0008+.0025*math.sin(math.pi*t)+.0009*t
            path.append(Vector((hair_x,character.face_y(hair_x,hair_z)-lift,hair_z)))
        shade = rand.randrange(1,6)
        fibers.add(path,rand.uniform(.00012,.00026),shade, max(1,shade-1))


def eyebrows(character, fibers, rand):
    width = character.spec.get('face_width',1)
    outer = character.spec.get('brow_lift',0)
    for sign in (-1,1):
        for _ in range(63):
            position = rand.random()
            x = .053*width+mix(-.030,.030,position)
            z = 1.7065 + (outer+.012)*math.sin(position*math.pi)**1.4+rand.uniform(-.002,.001)
            path = []
            for i in range(4):
                t = i/3
                hair_x = sign*(x+.006*t)
                hair_z = z+.0046*(.74-position)*t
                lift = .001+(.0026+.0012*math.sin(math.pi*position))*math.sin(math.pi*t)**.5
                path.append(Vector((hair_x,character.face_y(hair_x,hair_z)-lift,hair_z)))
            shade = rand.randrange(1,6)
            fibers.add(path,rand.uniform(.000105,.00018),shade,min(shade+1,6))


def groom(character):
    # Supporting characters keep the hair authored by their dress module until
    # an explicit strand style is defined for them.
    style = STYLES.get(character.name)
    if style is None:
        return
    head = separate_surface(character)
    clean_previous_groom(character)
    seed, scalp_count, beard_count, moustache_count, dark, highlights = style
    rand = random.Random(seed)
    fibers = FiberGroup(character,dark,highlights)
    scalp(character,head,rand,fibers,scalp_count)
    fibers.make_mesh('Scalp groom fibers')
    beard(character,head,rand,fibers,beard_count)
    moustache(character,fibers,rand,moustache_count)
    eyebrows(character,fibers,rand)
    fibers.make_mesh('Facial groom fibers')
