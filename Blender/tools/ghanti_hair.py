"""Strand-fibre cropped haircut and eyebrows for the bell-hearing boy."""

import math
from math import cos, tau

from mathutils import Vector

import groom
from ghanti_common import smooth


def edge(angle):
    """Hairline polar angle (from the crown) at a given heading."""
    back = (.5 - .5 * cos(angle)) ** .8
    return .93 + .95 * back


def crop_hair(c, rng):
    """Short crop with a forward fringe, rooted on the real scalp surface."""
    head = groom.separate_surface(c)
    fibers = groom.FiberGroup(c, (.021, .014, .010), (.078, .052, .036))

    def root(angle, phi, lift):
        point, normal = groom.surface(head, angle, 1.638 + .1735 * cos(phi))
        return point + normal * lift

    meridians, rows = 80, 20
    vertices = [Vector((0, .005, 1.8165))]
    for row in range(1, rows + 1):
        for col in range(meridians):
            angle = tau * col / meridians
            phi = edge(angle) * row / rows
            taper = max(0., min(1., (edge(angle) - phi) * 5))
            vertices.append(root(angle, phi, .0014 + .0030 * taper))
    faces = [(0, 1 + i, 1 + (i + 1) % meridians) for i in range(meridians)]
    for index in range(rows - 1):
        start = 1 + index * meridians
        for i in range(meridians):
            j = (i + 1) % meridians
            faces.append((start + i, start + i + meridians, start + j + meridians, start + j))
    shadow = c.mat('Scalp beneath the crop', (.017, .011, .008), rough=.9)
    c.mesh('Scalp undercoat', vertices, faces, shadow, 'head')

    front, down = Vector((0, -1, 0)), Vector((0, 0, -1))
    for _ in range(6400):
        angle = rng.uniform(-math.pi, math.pi)
        limit = edge(angle)
        phi = .07 + (limit * .985 - .07) * rng.random() ** .6
        point, normal = groom.surface(head, angle, 1.638 + .1735 * cos(phi))
        point = point + normal * .0008
        near_edge = smooth(.25, .9, phi / limit)
        fringe = smooth(.95, .0, abs(angle)) * smooth(.30, .80, phi / limit)
        direction = (normal * (.9 - .35 * near_edge) + down * (.55 * near_edge) + front * (.9 * fringe)
                     + Vector((rng.uniform(-.25, .25), rng.uniform(-.25, .25), rng.uniform(-.1, .2))))
        direction.normalize()
        length = rng.uniform(.016, .032) * (1 + .5 * fringe) * (1 - .45 * smooth(1.35, 1.95, phi))
        path = [point + direction * length * (i / 4) + down * length * .28 * (i / 4) ** 2
                for i in range(5)]
        shade = rng.choices((0, 1, 2, 3, 4, 5, 6), (8, 18, 24, 22, 15, 9, 4))[0]
        fibers.add(path, rng.uniform(.00032, .00055), shade, min(6, shade + 1))
    fibers.make_mesh('Crop hair fibers')
    groom.eyebrows(c, fibers, rng)
    fibers.make_mesh('Eyebrow fibers')
