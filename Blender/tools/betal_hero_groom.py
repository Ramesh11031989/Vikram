"""Fitted strand groom for Shyam Munshi, known as Betal."""

import math
import random

from mathutils import Vector

from groom import FiberGroup
from hero_groom import HeadSurface, smoothstep, traced_face_strand


PART = -.43


def hairline(angle):
    """Receded temples, an uneven front and a longer nape."""
    angle = math.atan2(math.sin(angle), math.cos(angle))
    back = ((1-math.cos(angle))*.5)**.72
    temple = math.exp(-((abs(angle)-.69)/.27)**2)
    ear = math.exp(-((abs(angle)-1.46)/.22)**2)
    return 1.39 + 1.04*back - .19*temple - .20*ear + .034*math.sin(angle*7+.6)


class Scalp:
    def __init__(self, surface):
        self.surface = surface
        self.center = Vector((0, -.036, surface.character.landmarks['eye.L'][2]+.027))

    def ray(self, theta, phi):
        direction = Vector((.083*math.sin(theta)*math.sin(phi),
                            -.104*math.cos(theta)*math.sin(phi),
                            .093*math.cos(phi))).normalized()
        point, normal, _, _ = self.surface.bvh.ray_cast(self.center+direction*.205, -direction, .215)
        if point is None:
            point = self.center + direction*.076
            normal = direction
        elif normal.dot(direction)<0:
            normal.negate()
        return point, normal

    def contour(self, theta, phi):
        point, normal = self.ray(theta,phi)
        edge = hairline(theta)
        edge_weight = smoothstep(edge+.012,edge-.25,phi)
        # Low, flowing ridges beneath the fibers give volume to separate locks.
        spread = math.sin(phi)**.85
        sweep = .0029*math.sin(5*theta+4.6*phi+.45)
        sweep += .0011*math.sin(11*theta-4.0*phi)
        offset = -.0017 + (.0096 + sweep*spread)*edge_weight
        return point+normal*offset, normal


def fit_scalp(character, scalp):
    around, rings = 124, 38
    pole, _ = scalp.contour(0,0)
    verts = [pole]
    for ring in range(1,rings+1):
        for index in range(around):
            theta = math.tau*index/around
            verts.append(scalp.contour(theta,hairline(theta)*ring/rings)[0])
    faces = [(0,1+index,1+(index+1)%around) for index in range(around)]
    for ring in range(rings-1):
        start = 1+ring*around
        for index in range(around):
            other = (index+1)%around
            faces.append((start+index,start+index+around,start+other+around,start+other))

    material = character.mat('Hair • matte salt-and-pepper roots',(.018,.014,.013),rough=.73)
    character.mesh('Hair • fitted natural hairline',verts,faces,material,'head')


def hair_fibers(scalp, fibers, rng):
    for _ in range(6800):
        theta = rng.uniform(-math.pi,math.pi)
        phi = .065+(hairline(theta)-.091)*rng.random()**.62
        side = 1 if theta>PART else -1
        flyaway = rng.random()<.055
        sweep = side*rng.uniform(.27,.83)*(1.16 if flyaway else 1)
        descent = rng.uniform(.13,.38)*smoothstep(.12,1.16,phi)
        bend = rng.uniform(-.12,.14)
        lift = rng.uniform(.0015,.0050) if not flyaway else rng.uniform(.005,.011)
        strand=[]
        for index in range(8):
            t = index/7
            across = theta+sweep*t+bend*math.sin(math.pi*t)
            edge = hairline(across)
            pitch = min(edge-.009,phi+descent*t)
            point, normal = scalp.contour(across,pitch)
            overflow = max(0,phi+descent*t-pitch)
            height = .00045+lift*(.78*math.sin(math.pi*t)+.24*t)
            droop = overflow*.074*(1 if abs(across)>1.05 else .25)
            strand.append(point + normal*(height+min(.003,overflow*.019)) - Vector((0,0,droop)))
        temple = .8<abs(theta)<1.73 and phi>1.0
        silver = rng.random() < (.28 if temple else .105)
        shade = rng.choice((4,5,5,6)) if silver else rng.choice((0,0,1,1,1,2,3))
        fibers.add(strand,rng.uniform(.000074,.000171)*(1.1 if flyaway else 1),shade,
                   min(6,shade+rng.randrange(2)))
    fibers.make_mesh('Hair • loosely swept dark and silver strands')


def beard(surface, fibers, rng):
    landmarks = surface.character.landmarks
    lip = landmarks['mouth'][2]
    jaw = landmarks['chin'][2]
    # Most of the cheek stays clear. Short, scattered hairs follow the jaw.
    for _ in range(4400):
        x = rng.uniform(-.070,.070)
        side = abs(x)/.070
        bottom = jaw-.006+.041*side**2.9
        top = lip-.015+.039*side**2.7
        z = rng.uniform(bottom-.002,top+.003)
        edge = smoothstep(bottom-.002,bottom+.008,z)*smoothstep(top+.003,top-.006,z)
        cheek = .78-.51*smoothstep(.33,.92,side)
        patch = .77+.22*math.sin(x*162+z*116)*math.cos(x*91-z*41)
        if rng.random()>edge*cheek*patch:
            continue
        length = rng.uniform(.0027,.0122)*(1-.34*side)
        flow = (1 if x>=0 else -1)*length*rng.uniform(.04,.32)
        strand = traced_face_strand(surface,x,z,flow,-length*.80,length*.30,
                                    rng.uniform(-.00065,.00068))
        if strand:
            silver = rng.random()<.18+.32*side
            shade = rng.choice((4,5,6)) if silver else rng.choice((0,1,1,2,3))
            fibers.add(strand,rng.uniform(.000058,.000135),shade,min(6,shade+1))
    fibers.make_mesh('Beard • sparse cheek and chin strands')


def moustache(surface, fibers, rng):
    mouth = surface.character.landmarks['mouth'][2]
    nose = surface.character.landmarks['nose_tip'][2]
    center_z = min(nose-.014,mouth+.016)
    for _ in range(940):
        sign = rng.choice((-1,1))
        sweep = rng.random()
        density = smoothstep(.02,.22,sweep)*smoothstep(1,.72,sweep)
        if rng.random()>density:
            continue
        x = sign*(.0028+.031*sweep)
        z = center_z-.0085*sweep**1.65 + .0014*math.sin(math.pi*sweep)
        z += rng.uniform(-.0025,.0030)*math.sin(math.pi*(.14+.79*sweep))
        strand = traced_face_strand(surface,x,z,sign*rng.uniform(.0026,.0075),
                                    -rng.uniform(.0023,.0070),rng.uniform(.00065,.0017))
        if strand:
            shade = rng.choice((0,1,1,2,2,3,4,4,5,6))
            fibers.add(strand,rng.uniform(.000062,.000126),shade,min(6,shade+1))
    fibers.make_mesh('Moustache • soft salt-and-pepper sweep')


def brows(surface, fibers, rng):
    for sign, side in ((1,'L'),(-1,'R')):
        eye = surface.character.landmarks[f'eye.{side}']
        for _ in range(380):
            t = rng.random()
            x = sign*(abs(eye[0])-.024+.052*t)
            z = eye[2]+.0160+.0064*math.sin(math.pi*(t*.88+.05))-.0042*t
            z += (sign*.00085 + rng.uniform(-.00265,.0025))*(.26+.74*math.sin(math.pi*t))
            strand = traced_face_strand(surface,x,z,sign*rng.uniform(.0026,.0066),
                                        rng.uniform(.001,.004)*(1-1.55*t),rng.uniform(.0005,.0013))
            if strand:
                shade = rng.choice((0,1,1,2,2,3,3,4,5))
                fibers.add(strand,rng.uniform(.000057,.000120),shade,min(6,shade+1))
        fibers.make_mesh(f'Brow.{side} • individual mature eyebrow strands')


def dress_head(character):
    """Fit the groom to skin in the adult bind pose and weight it to the head."""
    rng = random.Random(41491)
    surface = HeadSurface(character)
    scalp = Scalp(surface)
    fibers = FiberGroup(character,(.016,.012,.011),(.255,.235,.204))
    fit_scalp(character,scalp)
    hair_fibers(scalp,fibers,rng)
    beard(surface,fibers,rng)
    moustache(surface,fibers,rng)
    brows(surface,fibers,rng)
