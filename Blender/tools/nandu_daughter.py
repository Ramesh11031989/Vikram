"""Nandu's daughter (नंदू की बेटी): a small village girl on the shared child rig.

Story needs (Chapter 1): small enough to slip between the legs of the crowd in
the open court; the reed toy boat passes from her hand to Nandu's and back.
She wears no red: Nandu's red shoulder cloth is evidence in the story and must
stay the only red on the gatekeeper's family.

Guesses, to confirm with the director: age 5-6 (1.10 m), centre-parted hair
in two plaits tied with turmeric thread, a turmeric cotton kurti over an
indigo ghagra with an ochre border, barefoot, black protective threads on the
left wrist and right ankle, and a small kala teeka (protective kajal dot) on her
left cheek.  Face direction from Ramesh: realistic child proportions that read
clearly as a cute 5-6 year old.
"""

from __future__ import annotations

from collections.abc import Sequence
import math

import bpy

from child import ChildCharacter, ChildFace, ChildProportions, Pose
from child_hair import BraidStyle, braided_groom
from textile import finish_fabric, store_rest_positions


SPEC = dict(name='NanduDaughter', skin=(.42, .215, .118), hair=(.024, .015, .011),
            iris=(.046, .025, .012), face_width=1.05, nose_width=.88, brow_lift=.002,
            proportions=ChildProportions(height=1.10), child_face=ChildFace())

HAIR = BraidStyle(seed=1305, root=(.016, .010, .008), highlight=(.072, .043, .027))

# Label -> fine weave?  Labels are the text after "NanduDaughter • ".
FABRICS = {'Turmeric cotton kurti': False, 'Indigo ghagra': False, 'Ochre woven border': True,
           'Undyed border stripe': True, 'Indigo binding': False, 'Turmeric cotton thread': False}


def _rippled(z: float, rx: float, ry: float, segments: int, folds: int, depth: float,
             phase: float, x: float = 0) -> list[tuple[float, float, float]]:
    ring = []
    for j in range(segments):
        angle = math.tau * j / segments
        ripple = 1 + depth * math.cos(folds * angle + phase)
        ring.append((x + rx * math.cos(angle) * ripple, ry * math.sin(angle) * ripple, z))
    return ring


def kurti(c: ChildCharacter, cloth, binding) -> None:
    # The hem stays outside the ghagra beneath it: compare `ghagra` rows .80-1.00.
    rows = ((.80, .246, .186), (.86, .232, .174), (.95, .210, .156), (1.05, .193, .147),
            (1.16, .190, .138), (1.26, .200, .126), (1.33, .204, .114), (1.37, .196, .099),
            (1.392, .174, .086), (1.410, .118, .071), (1.425, .066, .057))
    weights = ['hips', 'hips', 'hips', {'hips': .35, 'spine': .65}, 'spine',
               {'spine': .3, 'chest': .7}, 'chest', 'chest', 'chest', 'chest', {'chest': .55, 'neck': .45}]
    rings = []
    for index, (z, rx, ry) in enumerate(rows):
        fold = .045 * max(0, 1 - index / 4) ** 1.4  # soft A-line folds toward the hem
        rings.append(_rippled(z, rx, ry, 64, 9, fold, .4 + index * .25))
    c.ring_mesh('Turmeric cotton kurti', rings, cloth, weights, cap=False)
    c.tube('Kurti hem binding', rings[0], .0042, binding, 'hips', cyclic=True)
    c.tube('Kurti neckline binding', rings[-1], .0036, binding, [weights[-1]] * len(rings[-1]), cyclic=True)

    def front(z: float) -> float:
        for (z0, _, a), (z1, _, b) in zip(rows, rows[1:]):
            if z0 <= z <= z1:
                return -(a + (b - a) * (z - z0) / (z1 - z0))
        return -rows[-1][2]
    placket = [(0, front(z) - .0016, z) for z in (1.424, 1.41, 1.39, 1.37, 1.35, 1.335)]
    c.tube('Kurti front opening', placket, .0027, binding, 'chest')
    for side, sign in (('L', 1), ('R', -1)):
        c.tube(f'Kurti neck tie {side}', [(sign * .006, front(1.40) - .003, 1.40),
                                          (sign * .016, front(1.40) - .006, 1.388),
                                          (sign * .019, front(1.37) - .006, 1.355)],
               [.0018, .0016, .0011], binding, 'chest')
        upper = f'upper_arm.{side}'
        # Short cap sleeve weighted like the arm beneath it, so it follows the
        # arm down instead of standing up as a shoulder pad.
        sections = ((.15, 1.362, .054, .038), (.175, 1.366, .060, .050), (.205, 1.370, .065, .060),
                    (.235, 1.374, .071, .070), (.265, 1.375, .070, .069), (.29, 1.375, .068, .067),
                    (.305, 1.375, .066, .065))
        sleeve = []
        for index, (x, z, depth, height) in enumerate(sections):
            puff = .025 * math.sin(math.pi * index / (len(sections) - 1))
            sleeve.append([(sign * x, sign * depth * math.cos(a) * (1 + puff * math.cos(10 * a)),
                            z + height * math.sin(a) * (1 + puff * math.cos(10 * a)))
                           for a in (math.tau * j / 40 for j in range(40))])
        c.ring_mesh(f'Kurti puff sleeve {side}', sleeve, cloth,
                    ['chest', {'chest': .7, upper: .3}, {'chest': .45, upper: .55}, {'chest': .2, upper: .8},
                     upper, upper, upper], cap=False)
        c.tube(f'Kurti sleeve binding {side}', sleeve[-1], .0034, binding, upper, cyclic=True)


def ghagra(c: ChildCharacter, cloth, border, stripe, binding) -> None:
    """Gathered ankle-length skirt; the hem follows the legs part of the way."""
    rows = ((1.00, .172, .128), (.95, .186, .138), (.85, .204, .151), (.70, .238, .176),
            (.55, .276, .199), (.40, .296, .213), (.29, .309, .222), (.272, .310, .223),
            (.255, .311, .224), (.24, .312, .225), (.20, .316, .228), (.165, .318, .229))
    segments, folds = 120, 17
    rings, weights = [], []
    top, hem = rows[0][0], rows[-1][0]
    for index, (z, rx, ry) in enumerate(rows):
        t = (top - z) / (top - hem)
        ring = _rippled(z, rx, ry, segments, folds, .008 + .034 * t ** 1.3, .35 * t)
        # Uneven hand gathers: vary each fold's depth so the pleats are not machine-regular.
        def gathers(j: int) -> float:
            a = math.tau * j / segments
            return (1 + .014 * (.3 + t) * math.sin(29 * a + 2.1 * t + .5)
                    + .022 * t * math.sin(7 * a + 1.1) + .012 * t * math.sin(11 * a - .7 + t))
        rings.append([(x * gathers(j), y * gathers(j), zz) for j, (x, y, zz) in enumerate(ring)])
        follow = .5 * t ** 1.2
        for x, _, _ in rings[-1]:
            left = min(1., max(0., .5 + x / .24))
            weights.append({'hips': 1 - follow, 'thigh.L': follow * left, 'thigh.R': follow * (1 - left)})
    verts = [point for ring in rings for point in ring]
    faces = [(i * segments + j, i * segments + (j + 1) % segments,
              (i + 1) * segments + (j + 1) % segments, (i + 1) * segments + j)
             for i in range(len(rings) - 1) for j in range(segments)]
    skirt = c.mesh('Indigo ghagra', verts, faces, cloth, weights)
    for material in (border, stripe):
        skirt.data.materials.append(material)
    for index, face in enumerate(skirt.data.polygons):
        row = index // segments
        z = (rows[row][0] + rows[row + 1][0]) / 2
        face.material_index = 1 if z < .24 else 2 if .255 < z < .272 else 0
    hem_weights = weights[-segments:]
    c.tube('Ghagra hem binding', rings[-1], .0045, binding, hem_weights, cyclic=True)


def protective_threads(c: ChildCharacter, black) -> None:
    wrist = [(.676, .0298 * math.cos(a), 1.375 + .0298 * math.sin(a)) for a in
             (math.tau * j / 24 for j in range(24))]
    c.tube('Black thread on wrist L', wrist, .0013, black, 'forearm.L', cyclic=True)
    c.ovoid('Black thread knot L', (.676, -.003, 1.346), (.0024, .0024, .0022), black, 'forearm.L')
    ankle = [(-.135 + .0446 * math.cos(a), .0446 * math.sin(a), .192) for a in
             (math.tau * j / 28 for j in range(28))]
    c.tube('Black thread on ankle R', ankle, .0014, black, 'shin.R', cyclic=True)


def face_details(c: ChildCharacter, black) -> None:
    edge = bpy.data.materials[f'{c.name} • Eyelid edge']
    shader = edge.node_tree.nodes.get('Principled BSDF')
    margin = (*[v * f for v, f in zip(c.spec['skin'], (.60, .41, .39))], 1)  # soft, rosy lid margin
    shader.inputs['Base Color'].default_value = margin
    edge.diffuse_color = margin
    # Kala teeka: a small protective kajal dot on the left cheek.
    x, z = .076, 1.626
    slope = (c.face_y(x + .002, z) - c.face_y(x - .002, z)) / .004
    c.ovoid('Kala teeka', (x, c.face_y(x, z) - .0006, z), (.0026, .0007, .0026), black, 'head',
            (0, 0, math.atan(slope)))


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
                    # Finer, softer weave than the adults' homespun at a child's scale.
                    weave_node = next(n for n in material.node_tree.nodes if n.type == 'GROUP')
                    weave_node.inputs['Thread pitch (mm)'].default_value = 2.2 if FABRICS[label] else 2.8
                    weave_node.inputs['Yarn contrast'].default_value = .12 if FABRICS[label] else .16
                    finished.add(material)
        if fabric:
            store_rest_positions(part.data)


def dress(c: ChildCharacter) -> None:
    kurti_cloth = c.mat('Turmeric cotton kurti', (.50, .315, .072), .9)
    skirt = c.mat('Indigo ghagra', (.042, .072, .155), .92)
    border = c.mat('Ochre woven border', (.40, .25, .07), .86)
    stripe = c.mat('Undyed border stripe', (.60, .53, .40), .88)
    binding = c.mat('Indigo binding', (.026, .040, .085), .9)
    thread = c.mat('Turmeric cotton thread', (.52, .33, .06), .85)
    black = c.mat('Black cotton thread', (.012, .010, .010), .8)
    kurti(c, kurti_cloth, binding)
    ghagra(c, skirt, border, stripe, binding)
    protective_threads(c, black)
    face_details(c, black)
    braided_groom(c, HAIR, thread)
    weave(c)
    c.smooth_render(('Kurti', 'Indigo ghagra', 'Ghagra', 'Arm', 'Leg', 'Neck', 'Palm', 'Finger', 'Thumb',
                     'Foot', 'Instep', 'Toe', 'Ear'))


# ------------------------------------------------------------------- poses
Aim = tuple[tuple[float, float, float], tuple[float, float, float] | None]
Turns = dict[str, list[tuple[tuple[float, float, float], float]]]


def _mirror(aims: dict[str, Aim]) -> dict[str, Aim]:
    """Copy every `.L` aim to `.R`, mirrored across the body's centre plane."""
    mirrored = dict(aims)
    for name, ((x, y, z), palm) in aims.items():
        if name.endswith('.L'):
            mirrored[name[:-2] + '.R'] = ((-x, y, z), None if palm is None else (-palm[0], palm[1], palm[2]))
    return mirrored


def _curl(side: str, fingers: Sequence[float], thumb: tuple[float, float, float] = (0, 0, 0),
          spread: float = 0) -> Turns:
    """Finger curls (base, middle, tip degrees) and thumb (opposition, bend, tip) as rest-frame turns."""
    sign = 1 if side == 'L' else -1
    turns: Turns = {}
    for digit in range(1, 5):
        base, middle, tip = (value * (1 + .06 * (digit - 1)) for value in fingers)
        fan = spread * (digit - 2.5) * sign
        turns[f'finger_{digit:02d}.{side}'] = [((0, 0, 1), fan), ((0, sign, 0), base)]
        turns[f'finger_{digit:02d}_mid.{side}'] = [((0, sign, 0), middle)]
        turns[f'finger_{digit:02d}_tip.{side}'] = [((0, sign, 0), tip)]
    oppose, bend, tip = thumb
    across = (.8, .6 * sign, 0)  # tips the thumb toward the palm
    turns[f'thumb.{side}'] = [((0, 0, sign), oppose * .5), (across, oppose)]
    turns[f'thumb_mid.{side}'] = [(across, bend)]
    turns[f'thumb_tip.{side}'] = [(across, tip)]
    return turns


def _merge(*parts: dict) -> dict:
    merged: dict = {}
    for part in parts:
        merged.update(part)
    return merged


RELAXED = (14, 20, 10)
# Arms hang with the collarbones dropped a little, so the shoulders stay soft.
STAND_ARMS = _mirror({'clavicle.L': ((.97, .02, -.24), None),
                      'upper_arm.L': ((.30, .02, -.95), None), 'forearm.L': ((.16, -.14, -.98), (-1, 0, 0)),
                      'hand.L': ((.08, -.10, -.99), (-1, .15, 0))})

POSES = (
    Pose('Stand', aims=STAND_ARMS,
         turns=_merge(_curl('L', RELAXED, (8, 8, 6)), _curl('R', RELAXED, (8, 8, 6))),
         note='Relaxed standing pose for lineups and crowd shots.'),
    Pose('Carry boat', aims=_merge(STAND_ARMS, {
            'upper_arm.L': ((.26, -.10, -.96), None), 'forearm.L': ((.10, -.32, -.94), (-1, 0, 0)),
            'upper_arm.R': ((-.16, -.22, -.96), None), 'forearm.R': ((.62, -.78, .10), (0, 0, 1)),
            'hand.R': ((.86, -.50, .08), (0, 0, 1))}),
         turns=_merge(_curl('L', RELAXED, (8, 8, 6)), _curl('R', (16, 14, 8), (10, 14, 8)),
                      {'head': [((1, 0, 0), 9)]}),
         note='Carries the reed boat lengthwise on her cupped right palm, bow along her fingers (boat on prop.R).'),
    Pose('Offer boat', aims=_mirror({
            'upper_arm.L': ((.05, -.45, -.89), None), 'forearm.L': ((-.39, -.74, .54), (0, 0, 1)),
            'hand.L': ((-.20, -.97, .05), (0, 0, 1))}),
         turns=_merge(_curl('L', (18, 16, 8), (6, 12, 8)), _curl('R', (18, 16, 8), (6, 12, 8)),
                      {'spine': [((1, 0, 0), 4)], 'chest': [((1, 0, 0), 3)], 'head': [((1, 0, 0), -14)]}),
         note='Holds the boat out to Nandu across both palms, side by side at chest height.'),
    Pose('Reach to take back', aims=_mirror({
            'upper_arm.L': ((.01, -.97, -.23), None), 'forearm.L': ((-.29, -.54, .79), (0, .5, .87)),
            'hand.L': ((-.15, -.92, .36), (0, .36, .93))}),
         turns=_merge(_curl('L', (8, 8, 4), (-6, 4, 2), spread=7), _curl('R', (8, 8, 4), (-6, 4, 2), spread=7),
                      {'chest': [((1, 0, 0), -3)], 'head': [((1, 0, 0), -22)]}),
         note='Reaches up with open hands as Nandu returns the boat.'),
)
