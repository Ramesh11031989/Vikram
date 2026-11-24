"""Gopal's fitted turquoise work band and short, brushed dark groom."""

import math
import random

from mathutils import Vector

from groom import FiberGroup
from hero_groom import HeadSurface, smoothstep, traced_face_strand
from textile import finish_fabric, store_rest_positions


def cloth_dye(character, name, color, pitch):
    material = character.mat(name, color, rough=.80)
    finish_fabric(material, fine=True)
    weave = next(node for node in material.node_tree.nodes if node.type == 'GROUP')
    weave.inputs['Thread pitch (mm)'].default_value = pitch
    weave.inputs['Relief (mm)'].default_value = .064
    return material


class WorkBand:
    def __init__(self, surface):
        self.surface = surface
        self.character = surface.character
        self.brow = self.character.landmarks['eye.L'][2]

    def low(self, angle):
        return self.brow+.022+.015*(.5+.5*math.cos(angle+.10))-.004*math.sin(angle+.48)

    def height(self, angle):
        return .0265+.0024*math.cos(angle-.36)+.0017*math.sin(2*angle+.30)

    def point(self, angle, height, extra=0):
        z = self.low(angle)+self.height(angle)*height
        radial = Vector((math.sin(angle),-math.cos(angle),0))
        point, _ = self.surface.radial(angle,z)
        if point is None:
            raise RuntimeError('Gopal’s headband reached outside the head surface.')
        fold = .0010*math.sin(4*angle+height*5.3)+.00055*math.sin(11*angle-height*4.7)
        bulge = .0020*math.sin(math.pi*height)**1.4
        return point+radial*(.0036+fold+bulge+extra)

    def make(self):
        character = self.character
        fabric = cloth_dye(character,'Headband • hand-dyed turquoise canvas',(.027,.270,.292),1.12)
        tucked = cloth_dye(character,'Headband • shadowed turquoise fold',(.019,.190,.205),1.12)
        edge = cloth_dye(character,'Headband • pale hand-finished piping',(.205,.410,.379),.91)
        angles = [math.tau*index/144 for index in range(144)]
        profile = [(0,-.0034),(0,-.0007),(.02,.0006)]
        profile += [(step/24,0) for step in range(1,24)]
        profile += [(.98,.0007),(1,-.0007),(1,-.0034)]
        rings = [[self.point(angle,height,offset) for angle in angles] for height,offset in profile]
        band = character.ring_mesh('Headband • folded turquoise cotton',rings,fabric,'head',cyclic=True)
        store_rest_positions(band.data)
        for label,height in (('lower',.043),('upper',.958)):
            seam = character.tube(f'Headband • rolled {label} piping',
                                  [self.point(angle,height,.0012) for angle in angles],
                                  .00115,edge,'head',cyclic=True)
            store_rest_positions(seam.data)
        self.make_knot(fabric,tucked,edge)

    def make_knot(self, fabric, tucked, edge):
        angle = 2.53
        anchor = self.point(angle,.47)
        radial = Vector((math.sin(angle),-math.cos(angle),0))
        tangent = Vector((math.cos(angle),math.sin(angle),0))
        up = Vector((0,0,1))
        character = self.character
        profiles = (
            ('long tucked end',tucked,((-.011,.000,.001,.009,.002),(.001,.003,-.004,.010,.004),
                                      (.015,.006,-.010,.010,.003),(.030,.005,-.021,.008,.0015),
                                      (.039,.004,-.024,.006,.0011))),
            ('short folded end',fabric,((-.016,.000,.003,.007,.002),(-.003,.006,.004,.012,.004),
                                       (.013,.010,.005,.010,.003),(.026,.009,.009,.007,.0015))),
            ('cinched cross-tuck',fabric,((-.015,.001,-.005,.006,.003),(-.010,.008,-.001,.011,.005),
                                         (-.003,.011,.003,.012,.007),(.006,.009,.005,.009,.006),
                                         (.013,.004,.006,.007,.003))),
        )
        for label,material,profile in profiles:
            rings = []
            for along,depth,z,width,thickness in profile:
                center = anchor+tangent*along+radial*depth+up*z
                rings.append([center + up*(width*math.cos(phase)) +
                              radial*(thickness*math.sin(phase)*(.85+.15*math.cos(phase*3)))
                              for phase in (math.tau*index/24 for index in range(24))])
            surface = character.ring_mesh(f'Headband • {label}',rings,material,'head')
            store_rest_positions(surface.data)
            if label != 'cinched cross-tuck':
                hem = character.tube(f'Headband • selvedge on {label}',rings[-1],.00058,edge,'head',cyclic=True)
                store_rest_positions(hem.data)


def hairline(angle):
    angle = math.atan2(math.sin(angle),math.cos(angle))
    side = abs(angle)
    back = ((1-math.cos(angle))*.5)**.77
    temple = math.exp(-((side-1.02)/.32)**2)
    ear = math.exp(-((side-1.55)/.21)**2)
    return 1.48+.78*back+.22*temple-.21*ear+.029*math.sin(6*angle+.45)


class BrushedScalp:
    def __init__(self, surface, band):
        self.surface = surface
        self.band = band
        self.center = Vector((0,-.036,band.brow+.027))

    def contour(self, angle, pitch):
        ray = Vector((.084*math.sin(angle)*math.sin(pitch),
                      -.104*math.cos(angle)*math.sin(pitch),
                      .091*math.cos(pitch))).normalized()
        point, normal, _, _ = self.surface.bvh.ray_cast(self.center+ray*.218,-ray,.218)
        if point is None:
            raise RuntimeError('Gopal’s groom reached outside the head surface.')
        if normal.dot(ray)<0:
            normal.negate()
        edge = hairline(angle)
        taper = smoothstep(edge+.009,edge-.29,pitch)
        low = self.band.low(angle)
        high = low+self.band.height(angle)
        band_pressure = (smoothstep(low-.009,low-.002,point.z)*
                         smoothstep(high+.0038,high-.0006,point.z))
        ridge = .00165*math.sin(7*angle+4.8*pitch)+.0008*math.sin(12*angle-5*pitch)
        bulk = .0092-.0035*smoothstep(1.18,1.76,pitch)
        lift = -.0015+taper*(bulk+ridge)*(1-.91*band_pressure)
        return point+normal*lift, normal, band_pressure

    def make(self, fibers, rng):
        character = self.surface.character
        segments, count = 120, 34
        vertices = [self.contour(0,0)[0]]
        for row in range(1,count+1):
            for column in range(segments):
                angle = math.tau*column/segments
                vertices.append(self.contour(angle,hairline(angle)*row/count)[0])
        faces = [(0,1+column,1+(column+1)%segments) for column in range(segments)]
        for row in range(count-1):
            first = 1+row*segments
            for column in range(segments):
                nxt = (column+1)%segments
                faces.append((first+column,first+column+segments,first+nxt+segments,first+nxt))
        roots = character.mat('Hair • close dark roots',(.016,.010,.007),rough=.77)
        character.mesh('Hair • close fitted root surface',vertices,faces,roots,'head')

        for _ in range(7500):
            angle = rng.uniform(-math.pi,math.pi)
            pitch = .076+(hairline(angle)-.104)*rng.random()**.65
            flyaway = rng.random()<.055
            sweep = rng.uniform(.22,.60)*(1 if angle>-.62 else -1)
            downstream = rng.uniform(.11,.28)*math.sin(pitch)-.055*math.cos(angle)
            lift = rng.uniform(.0012,.0045) if not flyaway else rng.uniform(.0048,.0082)
            bend = rng.uniform(-.080,.12)
            strand = []
            for step in range(8):
                t = step/7
                theta = angle+sweep*t+bend*math.sin(math.pi*t)
                phi = max(.04,min(hairline(theta)-.006,pitch+downstream*t))
                point,normal,pressure = self.contour(theta,phi)
                separation = .00038+lift*(.80*math.sin(math.pi*t)+.27*t)
                strand.append(point+normal*(separation*(1-.89*pressure)))
            shade = rng.choice((0,1,1,1,2,2,3,3,4,5,6))
            fibers.add(strand,rng.uniform(.000073,.000165),shade,min(shade+1,6))
        fibers.make_mesh('Hair • short brushed strands')


def facial_hair(surface, fibers, rng):
    landmarks = surface.character.landmarks
    mouth = landmarks['mouth'][2]
    start = min(landmarks['nose_tip'][2]-.013,mouth+.017)
    for _ in range(1580):
        side = rng.choice((-1,1))
        t = rng.random()
        taper = smoothstep(0,.12,t)*smoothstep(1,.70,t)
        if rng.random()>taper:
            continue
        x = side*(.0031+.0315*t)
        z = start+.0012*math.sin(math.pi*t)-.0088*t**1.46+side*.00035
        z += rng.uniform(-.0023,.0028)*taper
        strand = traced_face_strand(surface,x,z,side*rng.uniform(.0034,.0077),
                                   -rng.uniform(.0021,.0059),rng.uniform(.00075,.0019))
        if strand:
            shade = rng.choice((0,0,1,1,1,2,2,3,4,5))
            fibers.add(strand,rng.uniform(.000079,.000144),shade,max(0,shade-1))
    fibers.make_mesh('Moustache • narrow parted dark strands')

    for side, sign in (('L',1),('R',-1)):
        eye_x, _, eye_z = landmarks[f'eye.{side}']
        for _ in range(415):
            t = rng.random()
            x = sign*(abs(eye_x)-.0215+.050*t)
            arc = math.sin(math.pi*(.11+.86*t))
            z = eye_z+.0145+.0083*arc-.0024*t+sign*.00063
            z += rng.uniform(-.0028,.00225)*(.24+.76*arc)
            strand = traced_face_strand(surface,x,z,sign*rng.uniform(.0025,.0072),
                                       rng.uniform(.0013,.0038)*(1-1.68*t),rng.uniform(.00050,.00145))
            if strand:
                shade = rng.choice((0,1,1,2,2,3,3,4,5))
                fibers.add(strand,rng.uniform(.000056,.000116),shade,min(shade+1,6))
        fibers.make_mesh(f'Brow.{side} • tapered dark fibers')


def brass_stud(surface):
    character = surface.character
    convex, _ = surface.radial(-1.52,1.674)
    direction = Vector((-.59,-.81,0)).normalized()
    across = Vector((.81,-.59,0)).normalized()
    up = Vector((0,0,1))
    # Seat the visible face on the ear's front surface and retain a shallow bezel.
    seat, _, _, _ = surface.bvh.ray_cast(convex+direction*.025,-direction,.036)
    if seat is None:
        seat = convex
    brass = character.mat('Earring • worn river brass',(.389,.222,.076),rough=.41,metal=.71)
    dark = character.mat('Earring • darkened brass at bezel',(.142,.083,.029),rough=.48,metal=.67)
    profile = ((.0022,-.0010),(.0036,-.0002),(.0041,.0009),(.0039,.0017),
               (.0028,.0027),(.00155,.00315),(.00045,.00325))
    rings = [[seat+depth*direction+radius*(math.cos(angle)*across+1.17*math.sin(angle)*up)
              for angle in (math.tau*step/40 for step in range(40))] for radius,depth in profile]
    obj = character.ring_mesh('Earring.R • small hammered brass stud',rings,brass,'head')
    obj.data.materials.append(dark)
    for polygon in list(obj.data.polygons)[:40]:
        polygon.material_index = 1


def dress_head(character):
    """Build the fitted mesh groom and woven band in the adult bind pose."""
    surface = HeadSurface(character)
    band = WorkBand(surface)
    band.make()
    rng = random.Random(140924)
    fibers = FiberGroup(character,(.015,.009,.006),(.100,.067,.046))
    BrushedScalp(surface,band).make(fibers,rng)
    facial_hair(surface,fibers,rng)
    brass_stud(surface)
