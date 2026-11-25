"""Build the back of the anonymous witness's head for the lamp shots."""

import math
import random

from mathutils import Vector

from character import profile_at
from groom import FiberGroup


def cranial_point(angle, height, extra=0):
    center, width, depth = profile_at(height)
    return Vector(((.93 * width + extra) * math.sin(angle),
                   center - (1.04 * depth + extra) * math.cos(angle), height))


def groom_point(angle, t, extra=0):
    back = (.5 - .5 * math.cos(angle)) ** .78
    nape = 1.723 - .163 * back + .014 * abs(math.sin(angle)) ** 7
    nape += .003 * math.sin(5 * angle + .36) + .0017 * math.sin(13 * angle)
    height = nape + (1.814 - nape) * t
    taper = math.sqrt(max(.007, 1 - t ** 10))
    body = .0025 + .0098 * math.sin(math.pi * t) ** .7
    flow = .0019 * math.sin(8 * angle + 4 * t) + .001 * math.cos(19 * angle - 7 * t)
    point = cranial_point(angle, height, (body + flow + extra) * taper)
    point.x += .010 * t * t
    point.z += .009 * t ** 4
    return point


def build_witness_head(character):
    """Preserve the rig and make the ears, neck silhouette and hair legible in profile."""
    count = 80
    angles = [math.tau * step / count for step in range(count)]
    skin = character.mat('Witness skin at nape', (.235, .113, .059), .69)
    ear_shadow = character.mat('Witness ear folds', (.164, .066, .035), .77)
    hair = character.mat('Witness hair undercoat', (.022, .014, .009), .53)
    character.collection.objects[f'{character.name}_Neck'].data.materials[0] = skin
    character.ring_mesh('Witness skull and nape',
                        [[cranial_point(angle, 1.497 + (1.812 - 1.497) * row / 52) for angle in angles]
                         for row in range(53)], skin, 'head')
    for side, sign in (('L', 1), ('R', -1)):
        character.ear(side, sign, .94, skin, ear_shadow)
    character.ring_mesh('Witness combed hair mass',
                        [[groom_point(angle, row / 32) for angle in angles] for row in range(33)],
                        hair, 'head', cap=False)

    rng = random.Random(4516)
    fibers = FiberGroup(character, (.018, .0105, .0068), (.069, .038, .020))
    for index in range(640):
        angle = math.tau * index / 640 + rng.uniform(-.18, .18)
        crest = rng.uniform(.20, .96)
        lower = max(.01, crest - rng.uniform(.13, .40))
        sweep = rng.uniform(.12, .44)
        lift = rng.uniform(.0016, .0060)
        strand = []
        for step in range(8):
            progress = step / 7
            t = crest + (lower - crest) * progress
            theta = angle + sweep * progress + .024 * math.sin(math.pi * progress)
            strand.append(groom_point(theta, t, lift * (.35 + .65 * math.sin(math.pi * progress))))
        shade = rng.randrange(0, 5)
        fibers.add(strand, rng.uniform(.00058, .00128), shade, min(shade + 1, 6))
    fibers.make_mesh('Witness swept hair strands')
