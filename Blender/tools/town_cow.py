"""An Indian zebu cow for the neighbour's cattle place (metres, Z up, ground at Z = 0).

Faces +Y, about 1.4 m at the hump.  Origin on the ground at mid-body.  Body runs are lofts
with lateral rx and vertical ry; legs are lofts with front-to-back rx and lateral ry
(the story_kit convention).  One mesh with several material slots, named `Cow N body`.
Pass 2: shoulder and rib muscle masses, a belly line, flank fold, hip and pin bones, a tapered
muzzle with a mouth line, and a coat-patch material split (see `patches`).
"""

import ghat_kit as k
import story_kit as SK


def _leg(b, x, y, front, coat, dark, hoof):
    if front:
        pts = [(x, y, .92), (x, y - .01, .70), (x, y, .46), (x, y, .25), (x, y + .005, .075)]
        radii = [(.100, .085), (.062, .056), (.040, .041), (.032, .033), (.038, .039)]
    else:
        pts = [(x, y + .06, .94), (x, y + .13, .68), (x, y + .07, .46), (x, y + .08, .25), (x, y + .05, .075)]
        radii = [(.130, .100), (.074, .064), (.042, .042), (.033, .034), (.039, .039)]
    b.loft([(p, r[0], r[1]) for p, r in zip(pts, radii)], coat, sides=14)
    b.loft([(p, r[0] * 1.02, r[1] * 1.02) for p, r in list(zip(pts, radii))[3:]], dark, sides=12)
    hy = pts[-1][1]
    for dx in (-.0125, .0125):  # cloven hoof
        b.ellipsoid((x + dx, hy + .005, .033), (.021, .044, .034), hoof, rings=8, sides=12)
    b.ellipsoid((x, pts[3][1], .17), (.034, .038, .042), dark, rings=8, sides=12)  # fetlock
    b.ellipsoid((x, pts[2][1], .46), (.047, .05, .055), dark, rings=8, sides=12)   # knee or hock


def build(name, location, coat, m, patches=None):
    """Build one cow. `patches` is an optional second coat material for flank and neck patches."""
    dark, hoof, pink, eye, horn = m['cow_dark'], m['cow_hoof'], m['cow_muzzle'], m['cow_eye'], m['horn']
    patch = patches or coat
    b = SK.MeshBuilder()
    run = [(-.84, 1.00, .17, .20), (-.68, 1.07, .25, .29), (-.40, 1.08, .275, .33), (-.05, 1.04, .275, .325),
           (.28, 1.08, .26, .34), (.52, 1.12, .225, .31), (.68, 1.13, .17, .25)]
    b.loft([((0, y, z), rx, ry) for y, z, rx, ry in run], coat, sides=24)
    b.ellipsoid((0, .36, 1.40), (.115, .21, .15), coat, rot=(-.25, 0, 0), rings=10, sides=16)   # hump
    b.ellipsoid((0, -.66, 1.31), (.19, .22, .09), coat, rot=(.3, 0, 0), rings=8, sides=14)      # hip
    b.ellipsoid((0, -.05, .78), (.22, .50, .17), coat, rings=10, sides=18)                      # belly
    for s in (-1, 1):
        b.ellipsoid((s * .18, .34, 1.02), (.12, .22, .22), patch, rot=(.1, 0, 0), rings=10, sides=14)   # shoulder
        b.ellipsoid((s * .20, -.12, 1.08), (.10, .30, .24), coat, rings=10, sides=14)                   # ribs
        b.ellipsoid((s * .21, -.55, 1.06), (.14, .24, .26), patch, rot=(-.2, 0, 0), rings=10, sides=14)  # haunch
        b.ellipsoid((s * .14, -.78, 1.22), (.025, .035, .03), coat, rings=6, sides=8)                   # pin bone
        b.ellipsoid((s * .20, -.40, .74), (.07, .13, .07), coat, rings=6, sides=10)                     # flank fold
    neck = [((0, .60, 1.12), .17, .22), ((0, .78, 1.07), .145, .19), ((0, .91, 1.00), .125, .16)]
    b.loft(neck, coat, sides=18)
    b.ellipsoid((0, .74, .84), (.05, .24, .11), coat, rot=(.16, 0, 0), rings=8, sides=12)       # dewlap
    head = [((0, .90, 1.00), .115, .14), ((0, 1.00, .94), .108, .145), ((0, 1.10, .84), .078, .13),
            ((0, 1.17, .765), .066, .085)]
    b.loft(head, coat, sides=16)
    b.ellipsoid((0, 1.185, .745), (.074, .06, .056), pink, rings=8, sides=14)                   # muzzle
    b.tube([(-.05, 1.236, .722), (0, 1.243, .718), (.05, 1.236, .722)], .004, dark, sides=4)    # mouth line
    b.ellipsoid((0, .985, 1.075), (.095, .07, .05), coat, rings=8, sides=12)                    # poll
    for s in (-1, 1):
        b.ellipsoid((s * .032, 1.235, .75), (.014, .018, .011), dark, rings=6, sides=10)
        b.ellipsoid((s * .098, 1.02, .995), (.025, .03, .022), coat, rings=8, sides=12)
        b.ellipsoid((s * .105, 1.03, .995), (.015, .017, .015), eye, rings=8, sides=12)
        b.ellipsoid((s * .185, .93, 1.04), (.075, .035, .045), coat, rot=(0, s * .2, s * -.5), rings=8, sides=12)
        b.ellipsoid((s * .175, .935, 1.035), (.055, .02, .03), pink, rot=(0, s * .2, s * -.5), rings=6, sides=10)
        curve = SK.spline([(s * .07, .93, 1.11), (s * .16, .90, 1.17), (s * .25, .915, 1.27),
                           (s * .27, .975, 1.38), (s * .24, 1.03, 1.45)], 6)
        b.tube(curve, lambda t: .026 * (1 - .88 * t), horn, sides=8)
    for x, y, front in ((.17, .42, True), (-.17, .42, True), (.185, -.56, False), (-.185, -.56, False)):
        _leg(b, x, y, front, coat, dark, hoof)
    tail = SK.spline([(0, -.83, 1.06), (0, -.91, .98), (0, -.93, .70), (0, -.91, .38), (0, -.90, .22)], 6)
    b.tube(tail, lambda t: .017 * (1 - .65 * t), coat, sides=8)
    b.ellipsoid((0, -.90, .15), (.032, .035, .115), dark, rings=8, sides=12)                    # tail switch
    return b.build(name, k._current, smooth=0, location=location)
