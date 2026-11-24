"""भीड़-किट (crowd kit): बस्ती के परिवार, दीये लिए परिजन, दरबार के लोग.

One shared kit of four bodies for background crowds.  Nothing here fixes a
named person or a relationship, so the kit stays reusable for any family,
lamp-bearer or courtier in the background:

* CrowdMan   - adult: cream kurta, undyed dhoti trousers, shoulder cloth, head cloth.
* CrowdWoman - adult: saree wrap with pallu, blouse, low hair bun.
* CrowdElder - older adult, stooped by the pose: long kurta, grey hair, shawl over the head.
* CrowdChild - child on the shared child rig (1.05 m): kurta and shorts.

The adults use the standard `Character` skeleton and the child the shared child
rig; both keep the 34 shared cast bone names, so one pose set fits all four
(finger and thumb segments exist on the child only and are skipped on adults).

Poses (armature space, the front is -Y): Stand in court, Hold diya, Spread mat,
Wait on steps.  The kneeling and seated poses solve hip height and thigh angle
from each rig's own leg lengths.  Props come from `crowd_props`.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
import math

import bpy
from mathutils import Vector

from child import ChildFace, ChildProportions, Pose, apply_pose
from child_hair import BraidStyle, braided_groom
from citizen_witnesses import sleeves, trousers


SPEC_MAN = dict(name='CrowdMan', height=.97, skin=(.45, .245, .13), hair=(.025, .017, .013),
                iris=(.07, .036, .016), face_width=1.0, nose_width=1.0, brow_lift=.001)
SPEC_WOMAN = dict(name='CrowdWoman', height=.90, skin=(.40, .21, .11), hair=(.02, .014, .011),
                  iris=(.06, .03, .014), face_width=.97, nose_width=.92, brow_lift=.003)
SPEC_ELDER = dict(name='CrowdElder', height=.92, skin=(.36, .19, .10), hair=(.50, .49, .46),
                  iris=(.08, .045, .022), face_width=.98, nose_width=1.04, brow_lift=-.002)
SPEC_CHILD = dict(name='CrowdChild', skin=(.44, .23, .125), hair=(.02, .014, .011),
                  iris=(.05, .027, .013), face_width=1.04, nose_width=.9, brow_lift=.002,
                  proportions=ChildProportions(height=1.05), child_face=ChildFace())

CHILD_HAIR = BraidStyle(seed=2207, root=(.014, .010, .008), highlight=(.060, .036, .022), braid_length=.09)

SPECS = (SPEC_MAN, SPEC_WOMAN, SPEC_ELDER, SPEC_CHILD)
CHILD_NAME = SPEC_CHILD['name']
STOOP = {'CrowdMan': 0., 'CrowdWoman': 0., 'CrowdElder': 22., 'CrowdChild': 0.}  # degrees through the spine


# ---------------------------------------------------------------- costumes
def _sandals(c, leather) -> None:
    for sign, side in ((1, 'L'), (-1, 'R')):
        c.ovoid(f'Sandal sole {side}', (sign * .135, -.06, .024), (.066, .132, .026), leather, f'foot.{side}')
        c.tube(f'Sandal strap {side}', [(sign * .09, -.02, .04), (sign * .135, -.05, .092), (sign * .18, -.02, .04)],
               .007, leather, f'foot.{side}')


def dress_man(c) -> None:
    kurta = c.mat('Cream cotton kurta', (.62, .55, .40), .91)
    seam = c.mat('Kurta tan seam', (.30, .22, .12), .91)
    dhoti = c.mat('Undyed dhoti', (.66, .62, .52), .93)
    cloth = c.mat('Madder shoulder cloth', (.36, .11, .07), .90)
    wrap = c.mat('Saffron head cloth', (.62, .30, .06), .90)
    leather = c.mat('Worn brown sandals', (.18, .10, .055), .82)
    c.loft('Kurta', [(.78, 0, .004, .212, .146), (.92, 0, .006, .222, .150), (1.08, 0, .004, .21, .14),
                     (1.23, 0, 0, .225, .133), (1.36, 0, 0, .24, .115), (1.44, 0, 0, .09, .07)], kurta,
           ['hips', 'hips', 'spine', {'spine': .4, 'chest': .6}, 'chest', 'chest'])
    c.tube('Kurta placket', [(0, -.148, .78), (0, -.155, .92), (0, -.146, 1.08), (0, -.134, 1.23),
                             (0, -.118, 1.36), (0, -.10, 1.42)], .005, seam, 'spine')
    sleeves(c, kurta, seam, 1.18, 6)
    trousers(c, dhoti, seam, 1.18, .14)
    _sandals(c, leather)
    c.tube('Shoulder cloth', [(.19, .012, 1.45), (.12, -.12, 1.38), (.02, -.17, 1.24), (-.10, -.16, 1.06),
                              (-.17, -.13, .92)], [.03, .034, .036, .034, .03], cloth, 'chest')
    c.ovoid('Short hair', (0, .018, 1.735), (.118, .104, .09), c.m['hair'], 'head')
    for index, (z, rx, ry) in enumerate(((1.742, .126, .112), (1.772, .122, .108), (1.80, .106, .095))):
        c.ovoid(f'Head cloth band {index + 1}', (0, .008, z), (rx, ry, .028), wrap, 'head')


def dress_woman(c) -> None:
    saree = c.mat('Teal saree cloth', (.04, .20, .20), .90)
    border = c.mat('Saree gold border', (.55, .38, .08), .86)
    blouse = c.mat('Ochre blouse', (.50, .30, .06), .90)
    band = c.mat('Hair cord', (.21, .05, .10), .85)
    leather = c.mat('Worn tan sandals', (.20, .115, .06), .82)
    # Saree skirt: a wide draped leg on each side so the cloth follows kneeling and sitting,
    # closed at the waist by a short wrapped band on the hips.
    trousers(c, saree, border, 1.5, .06)
    c.loft('Saree waist wrap', [(.84, 0, 0, .215, .15), (.95, 0, 0, .195, .138), (1.04, 0, 0, .19, .13)],
           saree, ['hips'] * 3)
    c.loft('Blouse', [(1.00, 0, .002, .19, .13), (1.16, 0, 0, .19, .12), (1.30, 0, 0, .21, .115),
                      (1.38, 0, 0, .21, .10), (1.44, 0, 0, .09, .07)], blouse,
           ['hips', 'spine', {'spine': .4, 'chest': .6}, 'chest', 'chest'])
    sleeves(c, blouse, border, 1.12, 4)
    for sign, side in ((1, 'L'), (-1, 'R')):
        c.ovoid(f'Sandal sole {side}', (sign * .135, -.06, .024), (.062, .126, .026), leather, f'foot.{side}')
    # Pallu: over the left shoulder, across the chest, tucked at the right hip.
    c.tube('Pallu across chest', [(.19, .012, 1.45), (.12, -.125, 1.37), (.02, -.17, 1.22), (-.08, -.166, 1.05),
                                  (-.17, -.135, .90)], [.031, .035, .037, .035, .03], saree, 'chest')
    c.tube('Pallu over shoulder', [(.19, .012, 1.45), (.2, .07, 1.36), (.19, .125, 1.18), (.16, .14, .98)],
           [.031, .03, .028, .024], saree, 'chest')
    c.tube('Pallu border', [(.19, .012, 1.481), (.12, -.125, 1.405), (.02, -.17, 1.256), (-.08, -.166, 1.086),
                            (-.17, -.135, .935)], .004, border, 'chest')
    c.ovoid('Hair cap', (0, .012, 1.745), (.123, .108, .075), c.m['hair'], 'head')
    c.ovoid('Hair back', (0, .03, 1.69), (.116, .1, .085), c.m['hair'], 'head')
    c.ovoid('Hair bun', (0, .118, 1.64), (.058, .054, .06), c.m['hair'], 'head')
    c.tube('Hair cord', [(-.05 + .1 * i / 11, .098 + .012 * math.sin(math.pi * i / 11), 1.675) for i in range(12)],
           .006, band, 'head')


def dress_elder(c) -> None:
    kurta = c.mat('Undyed elder kurta', (.66, .62, .52), .93)
    seam = c.mat('Elder kurta seam', (.34, .30, .22), .93)
    dhoti = c.mat('Faded elder dhoti', (.58, .55, .46), .94)
    shawl = c.mat('Grey wool shawl', (.22, .21, .20), .96)
    edge = c.mat('Shawl dark edge', (.07, .065, .06), .96)
    leather = c.mat('Cracked brown sandals', (.16, .10, .06), .85)
    c.loft('Long kurta', [(.62, 0, .004, .205, .146), (.82, 0, .006, .215, .150), (1.00, 0, .004, .205, .14),
                          (1.20, 0, 0, .222, .133), (1.36, 0, 0, .238, .115), (1.44, 0, 0, .09, .07)], kurta,
           [{'hips': .5, 'thigh.L': .25, 'thigh.R': .25}, 'hips', 'hips', 'spine', 'chest', 'chest'])
    c.tube('Kurta placket', [(0, -.148, .62), (0, -.155, .82), (0, -.146, 1.0), (0, -.134, 1.2),
                             (0, -.118, 1.36), (0, -.10, 1.42)], .005, seam, 'spine')
    sleeves(c, kurta, seam, 1.18, 8)
    trousers(c, dhoti, seam, 1.12, .12)
    _sandals(c, leather)
    c.tube('Shawl across back', [(.20, .02, 1.46), (.12, .09, 1.40), (0, .12, 1.36), (-.12, .09, 1.40),
                                 (-.20, .02, 1.46)], .036, shawl, 'chest')
    for sign in (1, -1):
        c.tube(f'Shawl front fall {sign}', [(sign * .19, .0, 1.46), (sign * .17, -.1, 1.34), (sign * .13, -.16, 1.14),
                                            (sign * .10, -.15, .96)], [.03, .034, .036, .03], shawl, 'chest')
        c.tube(f'Shawl edge {sign}', [(sign * .19, .0, 1.495), (sign * .17, -.1, 1.375), (sign * .13, -.16, 1.175),
                                      (sign * .10, -.15, .995)], .004, edge, 'chest')
    c.ovoid('Grey hair', (0, .018, 1.73), (.12, .106, .088), c.m['hair'], 'head')
    c.ovoid('Head cloth', (0, .022, 1.755), (.134, .118, .082), shawl, 'head')
    for sign, side in ((1, 'L'), (-1, 'R')):
        c.tube(f'Head cloth drape {side}', [(sign * .115, -.02, 1.72), (sign * .14, .02, 1.58), (sign * .18, .02, 1.47)],
               [.026, .026, .022], shawl, 'head')


def dress_child(c) -> None:
    kurta = c.mat('Indigo child kurta', (.07, .11, .22), .90)
    seam = c.mat('Child kurta seam', (.58, .50, .34), .90)
    shorts = c.mat('Sand cotton shorts', (.50, .42, .29), .92)
    c.loft('Short kurta', [(.80, 0, .004, .215, .145), (.93, 0, .006, .225, .150), (1.08, 0, .004, .21, .14),
                           (1.23, 0, 0, .225, .133), (1.36, 0, 0, .24, .115), (1.44, 0, 0, .09, .07)], kurta,
           ['hips', 'hips', 'spine', {'spine': .4, 'chest': .6}, 'chest', 'chest'])
    c.tube('Kurta collar', [(-.075, -.05, 1.44), (-.07, -.09, 1.41), (-.038, -.11, 1.38), (0, -.118, 1.365),
                            (.038, -.11, 1.38), (.07, -.09, 1.41), (.075, -.05, 1.44)], .0065, seam, 'chest')
    sleeves(c, kurta, seam, 1.2, 5)
    trousers(c, shorts, seam, 1.15, .52)
    tie = c.mat('Child hair thread', (.40, .08, .10), .85)
    braided_groom(c, CHILD_HAIR, tie)  # also draws the brow fibres the facial controls drive


DRESS: dict[str, Callable] = {'CrowdMan': dress_man, 'CrowdWoman': dress_woman, 'CrowdElder': dress_elder,
                              'CrowdChild': dress_child}



# ------------------------------------------------------------------- poses
Aim = tuple[tuple[float, float, float], tuple[float, float, float] | None]
Turns = dict[str, list[tuple[tuple[float, float, float], float]]]

POSE_NAMES = ('Stand in court', 'Hold diya', 'Spread mat', 'Wait on steps')
SEAT_RISE = .20  # height of the stone step the seated pose sits on, metres


def _unit(x: float, y: float, z: float) -> tuple[float, float, float]:
    v = Vector((x, y, z)).normalized()
    return v.x, v.y, v.z


def _mirror(aims: dict[str, Aim]) -> dict[str, Aim]:
    """Copy every `.L` aim to `.R`, mirrored across the body's centre plane."""
    mirrored = dict(aims)
    for name, ((x, y, z), palm) in aims.items():
        if name.endswith('.L'):
            mirrored[name[:-2] + '.R'] = ((-x, y, z), None if palm is None else (-palm[0], palm[1], palm[2]))
    return mirrored


def _curl(side: str, fingers: Sequence[float], thumb: tuple[float, float, float]) -> Turns:
    """Finger curls (base, middle, tip degrees) and thumb turns as rest-frame turns."""
    sign = 1 if side == 'L' else -1
    turns: Turns = {}
    for digit in range(1, 5):
        base, middle, tip = (value * (1 + .06 * (digit - 1)) for value in fingers)
        turns[f'finger_{digit:02d}.{side}'] = [((0, sign, 0), base)]
        turns[f'finger_{digit:02d}_mid.{side}'] = [((0, sign, 0), middle)]
        turns[f'finger_{digit:02d}_tip.{side}'] = [((0, sign, 0), tip)]
    oppose, bend, tip = thumb
    across = (.8, .6 * sign, 0)
    turns[f'thumb.{side}'] = [((0, 0, sign), oppose * .5), (across, oppose)]
    turns[f'thumb_mid.{side}'] = [(across, bend)]
    turns[f'thumb_tip.{side}'] = [(across, tip)]
    return turns


def _hands(fingers: Sequence[float], thumb: tuple[float, float, float] = (6, 8, 6)) -> Turns:
    return {**_curl('L', fingers, thumb), **_curl('R', fingers, thumb)}


def _lean(stoop: float, spine: float, chest: float, head: float) -> Turns:
    """Forward bend about the rest-frame X axis; `stoop` adds an elder's rounded back."""
    return {'spine': [((1, 0, 0), spine + stoop * .4)], 'chest': [((1, 0, 0), chest + stoop * .35)],
            'neck': [((1, 0, 0), stoop * .25)], 'head': [((1, 0, 0), head - stoop * .3)]}


def _leg_lengths(rig) -> tuple[float, float, float, float]:
    """Thigh length, shin length, ankle height and hip height of a rig in its rest pose."""
    bones = rig.data.bones
    hip, knee, ankle = (bones[name].head_local for name in ('thigh.L', 'shin.L', 'foot.L'))
    return (knee - hip).length, (knee - ankle).length, ankle.z, hip.z


def make_pose(name: str, rig, stoop: float = 0.) -> tuple[Pose, float]:
    """The named crowd pose fitted to this rig, and how far the hips must drop (negative) or lift."""
    thigh, shin, ankle_z, hip_z = _leg_lengths(rig)
    scale = hip_z / .91
    arms = {'clavicle.L': ((.97, .02, -.24), None), 'upper_arm.L': ((.30, .02, -.95), None),
            'forearm.L': ((.16, -.14, -.98), (-1, 0, 0)), 'hand.L': ((.08, -.10, -.99), (-1, .15, 0))}
    legs: dict[str, Aim] = {}
    turns = {**_hands((14, 20, 10)), **_lean(stoop, 0, 0, 0)}
    hips = 0.
    note = 'Relaxed standing pose for the open court, a lineup or a crowd edge.'
    if name == 'Hold diya':
        arms = {'upper_arm.L': (_unit(.05, -.45, -.89), None), 'forearm.L': (_unit(-.39, -.74, .54), (0, 0, 1)),
                'hand.L': (_unit(-.20, -.97, .05), (0, 0, 1))}
        turns = {**_hands((22, 18, 10), (6, 12, 8)), **_lean(stoop, 3, 2, 6)}
        note = 'Both palms cupped side by side at chest height, carrying a diya (Prop_Diya on hand.R).'
    elif name == 'Spread mat':
        arms = {'clavicle.L': ((.97, -.05, -.20), None), 'upper_arm.L': (_unit(.20, -.45, -.87), None),
                'forearm.L': (_unit(.08, -.87, -.50), (-1, 0, 0)), 'hand.L': (_unit(.04, -.94, -.34), (0, 0, -1))}
        legs = {'thigh.L': (_unit(.08, -.16, -.98), None), 'shin.L': ((0, 1, .02), None),
                'foot.L': ((0, .98, -.15), None)}
        turns = {**_hands((4, 4, 2), (0, 4, 2)), **_lean(stoop, 24, 18, -14)}
        hips = .05 * scale + thigh * .98 - hip_z  # knees rest on the mat
        note = 'Kneels and leans forward, both palms pressing the mat flat across the floor.'
    elif name == 'Wait on steps':
        arms = {'clavicle.L': ((.97, .02, -.22), None), 'upper_arm.L': (_unit(.22, -.18, -.95), None),
                'forearm.L': (_unit(.05, -.90, -.38), (-1, 0, 0)), 'hand.L': (_unit(.02, -.92, -.30), (-1, 0, -.3))}
        seat = .09 * scale + SEAT_RISE  # hip joint above the soles
        sin = max(-.85, min(.85, (seat - shin - ankle_z) / thigh))
        legs = {'thigh.L': (_unit(.08, -math.sqrt(1 - sin * sin), -sin), None), 'shin.L': (_unit(0, .06, -1), None)}
        turns = {**_hands((14, 20, 10)), **_lean(stoop, 6, 4, -4)}
        hips = seat - hip_z
        note = 'Sits on a stone step, feet on the step below, forearms resting on the knees.'
    elif name != 'Stand in court':
        raise ValueError(f'unknown crowd pose {name}')
    aims = _mirror({**arms, **legs})
    names = set(rig.data.bones.keys())
    return (Pose(name, {k: v for k, v in aims.items() if k in names},
                 {k: v for k, v in turns.items() if k in names}, note), hips)


def apply_crowd_pose(rig, name: str, stoop: float = 0.) -> Pose:
    """Pose the rig, then move the hips to the height the pose needs."""
    pose, hips = make_pose(name, rig, stoop)
    apply_pose(rig, pose)
    if hips:
        bone = rig.pose.bones['hips']
        matrix = bone.matrix.copy()
        matrix.translation.z += hips
        bone.matrix = matrix
        bpy.context.view_layer.update()
    return pose

