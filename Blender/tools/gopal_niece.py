"""Gopal's niece (गोपाल की भतीजी): the girl seated in the river boat, one hand in the water.

Story needs (Chapter 1, E01_SC04_SH09): in Gopal's night account the niece sits
in the boat and "her hand was touching the water".  She is a different
character from Nandu's daughter but shares the child rig (`child.py`): the same
34 bone names, finger bones, `prop.L` / `prop.R` sockets, facial controls and
pose tools.  Her face, hair and clothes are her own.

Guesses, to confirm with the director: age 4-5 (1.00 m, a little smaller than
Nandu's daughter), a rounder face with a small upturned nose and wide eyes,
lighter wheat-brown skin, soft brown hair in two short plaits tied with ivory
ribbon, a sage-green cotton frock with a cream hem band, pale-teal glass
bangles on the left wrist only (the right hand is bare for the water) and bare
feet.  No red anywhere on her: the red cloth is evidence in the story.
"""

from __future__ import annotations

import math

import bpy

from child import ChildCharacter, ChildFace, ChildProportions, Pose
from child_hair import BraidStyle, braided_groom
from nandu_daughter import RELAXED, STAND_ARMS, _curl, _merge, _mirror, _rippled
from textile import finish_fabric, store_rest_positions


SPEC = dict(name='GopalNiece', skin=(.50, .285, .165), hair=(.060, .034, .018),
            iris=(.075, .040, .018), face_width=.97, nose_width=.80, brow_lift=.003,
            proportions=ChildProportions(height=1.00, head=(.62, .75, .65), body_width=.50),
            child_face=ChildFace(eye_size=.15, eye_open=.16, cheek_fill=.0055, jaw_narrow=.26,
                                 lower_face=.72, tip_lift=.0034, bridge=.74, smile=.0030,
                                 forehead=.014, iris_size=1.38))

HAIR = BraidStyle(seed=2207, root=(.040, .022, .011), highlight=(.150, .085, .042),
                  scalp_fibers=2400, part_gap=.0030, anchor=(2.12, 1.70), braid_length=.130,
                  braid_width=.022, braid_pitch=.019, tuft=.020, fibers_per_strand=64)

# Label -> fine weave?  Labels are the text after "GopalNiece • ".
FABRICS = {'Sage cotton frock': False, 'Cream hem band': True, 'Cream frock binding': False,
           'Ivory hair ribbon': False}


def frock(c: ChildCharacter, cloth, band, binding) -> None:
    """Fitted yoke, then a flared skirt that follows the thighs, with cap sleeves."""
    rows = ((1.425, .066, .057), (1.410, .118, .071), (1.392, .174, .086), (1.37, .196, .099),
            (1.33, .204, .114), (1.26, .200, .126), (1.16, .190, .138), (1.08, .200, .146),
            (1.00, .232, .170), (.90, .260, .190), (.80, .282, .204), (.72, .298, .214),
            (.66, .306, .219))
    segments = 96
    rings, weights = [], []
    hem = rows[-1][0]
    for z, rx, ry in rows:
        t = max(0., (1.08 - z) / (1.08 - hem))
        ring = _rippled(z, rx, ry, segments, 13, .006 + .030 * t ** 1.2, .3 * t)
        rings.append(ring)
        for x, _, _ in ring:
            if z > 1.30:
                weights.append({'chest': .55, 'neck': .45} if z > 1.41 else 'chest')
            elif z > 1.08:
                weights.append({'chest': .35, 'spine': .65} if z > 1.2 else {'spine': .6, 'hips': .4})
            else:
                follow = min(.30, .95 * t ** .8)  # the hem lifts a little with the lap but never folds into a bowl
                left = min(1., max(0., .5 + x / .26))
                weights.append({'hips': 1 - follow, 'thigh.L': follow * left, 'thigh.R': follow * (1 - left)})
    verts = [point for ring in rings for point in ring]
    faces = [(i * segments + j, i * segments + (j + 1) % segments,
              (i + 1) * segments + (j + 1) % segments, (i + 1) * segments + j)
             for i in range(len(rings) - 1) for j in range(segments)]
    garment = c.mesh('Sage cotton frock', verts, faces, cloth, weights)
    garment.data.materials.append(band)
    for index, face in enumerate(garment.data.polygons):
        row = index // segments
        face.material_index = 1 if (rows[row][0] + rows[row + 1][0]) / 2 < .75 else 0
    c.tube('Frock hem binding', rings[-1], .0042, binding, weights[-segments:], cyclic=True)
    c.tube('Frock neckline binding', rings[0], .0034, binding, weights[:segments], cyclic=True)
    for side, sign in (('L', 1), ('R', -1)):
        upper = f'upper_arm.{side}'
        sections = ((.15, 1.360, .052, .036), (.18, 1.364, .058, .047), (.215, 1.368, .062, .056),
                    (.25, 1.371, .064, .060), (.275, 1.372, .062, .058))
        sleeve = []
        for index, (x, z, depth, height) in enumerate(sections):
            puff = .020 * math.sin(math.pi * index / (len(sections) - 1))
            sleeve.append([(sign * x, sign * depth * math.cos(a) * (1 + puff * math.cos(8 * a)),
                            z + height * math.sin(a) * (1 + puff * math.cos(8 * a)))
                           for a in (math.tau * j / 36 for j in range(36))])
        c.ring_mesh(f'Frock cap sleeve {side}', sleeve, cloth,
                    ['chest', {'chest': .6, upper: .4}, {'chest': .3, upper: .7}, upper, upper], cap=False)
        c.tube(f'Frock sleeve binding {side}', sleeve[-1], .0032, binding, upper, cyclic=True)


def bangles(c: ChildCharacter, glass) -> None:
    for index, offset in enumerate((.652, .664, .676)):
        ring = [(offset, .0315 * math.cos(a), 1.375 + .0315 * math.sin(a)) for a in
                (math.tau * j / 28 for j in range(28))]
        c.tube(f'Glass bangle L {index + 1}', ring, .0020, glass, 'forearm.L', cyclic=True)


def face_details(c: ChildCharacter) -> None:
    edge = bpy.data.materials[f'{c.name} • Eyelid edge']
    shader = edge.node_tree.nodes.get('Principled BSDF')
    margin = (*[v * f for v, f in zip(c.spec['skin'], (.62, .43, .41))], 1)  # soft, rosy lid margin
    shader.inputs['Base Color'].default_value = margin
    edge.diffuse_color = margin


def weave(c: ChildCharacter) -> None:
    finished = set()
    for part in c.parts:
        fabric = False
        for material in part.data.materials:
            label = material.name.partition(' • ')[2]
            if label in FABRICS:
                fabric = True
                if material not in finished:
                    finish_fabric(material, FABRICS[label])
                    weave_node = next(n for n in material.node_tree.nodes if n.type == 'GROUP')
                    weave_node.inputs['Thread pitch (mm)'].default_value = 2.2 if FABRICS[label] else 2.8
                    weave_node.inputs['Yarn contrast'].default_value = .12 if FABRICS[label] else .16
                    finished.add(material)
        if fabric:
            store_rest_positions(part.data)


def dress(c: ChildCharacter) -> None:
    cloth = c.mat('Sage cotton frock', (.115, .205, .130), .9)
    band = c.mat('Cream hem band', (.62, .56, .42), .86)
    binding = c.mat('Cream frock binding', (.50, .45, .34), .9)
    ribbon = c.mat('Ivory hair ribbon', (.70, .66, .55), .8)
    glass = c.mat('Pale teal glass', (.10, .33, .31), .25)
    frock(c, cloth, band, binding)
    bangles(c, glass)
    face_details(c)
    braided_groom(c, HAIR, ribbon)
    weave(c)
    c.smooth_render(('Frock', 'Arm', 'Leg', 'Neck', 'Palm', 'Finger', 'Thumb', 'Foot', 'Instep', 'Toe', 'Ear'))


# ------------------------------------------------------------------- poses
# Sitting on the boat's floor boards: knees raised in front, feet drawn back under them.
SEATED_LEGS = _mirror({'thigh.L': ((.16, -.98, .10), None), 'shin.L': ((.16, -.98, -.06), None)})
# The left hand rests loosely in her lap.
LAP_ARM = {'upper_arm.L': ((.28, -.05, -.96), None), 'forearm.L': ((.05, -.80, -.60), (-1, 0, 0)),
           'hand.L': ((-.10, -.88, -.46), (-.3, 0, -1))}

POSES = (
    Pose('Stand', aims=STAND_ARMS,
         turns=_merge(_curl('L', RELAXED, (8, 8, 6)), _curl('R', RELAXED, (8, 8, 6))),
         note='Relaxed standing pose for lineups.'),
    Pose('Sit in boat', aims=_merge(SEATED_LEGS, STAND_ARMS, LAP_ARM,
                                    _mirror({'upper_arm.L': LAP_ARM['upper_arm.L'],
                                             'forearm.L': LAP_ARM['forearm.L'], 'hand.L': LAP_ARM['hand.L']})),
         turns=_merge(_curl('L', RELAXED, (8, 8, 6)), _curl('R', RELAXED, (8, 8, 6)),
                      {'head': [((1, 0, 0), -6)]}),
         note='Sitting on the boat floor boards, knees up, hands loosely in her lap.'),
    Pose('Hand in water', aims=_merge(SEATED_LEGS, STAND_ARMS, LAP_ARM, {
            'clavicle.R': ((-.93, -.04, -.36), None),
            'upper_arm.R': ((-.55, -.10, -.83), None), 'forearm.R': ((-.35, -.12, -.93), (1, 0, 0)),
            'hand.R': ((-.20, -.10, -.98), (1, -.2, 0))}),
         turns=_merge(_curl('L', RELAXED, (8, 8, 6)), _curl('R', (5, 8, 4), (-4, 4, 2), spread=5),
                      {'spine': [((0, 1, 0), -28)], 'chest': [((0, 1, 0), -22)],
                       'head': [((1, 0, 0), 12), ((0, 0, 1), -30), ((0, 1, 0), 40)]}),
         note='Sitting on the boat floor boards, leaning far over the right gunwale, fingertips of the right hand touching the water.'),
)
