"""Vikram's journey: horse, bridle and reins, tether rope, riding gear and the statement satchel.

Metres, Z up, ground at Z = 0. The horse faces -Y like the characters and stands about 1.50 m at
the withers (a 14.3-hand country horse). Its origin is on the ground between the hooves.
Loft cross sections: along a body run (tangent on Y) rx is lateral and ry vertical; along a leg
(tangent on Z) rx is front-to-back and ry is lateral.
"""

from __future__ import annotations

import math

from mathutils import Vector

import story_kit as K


def materials():
    return dict(
        coat=K.mat('Horse • Bay coat', (.30, .15, .075), .62, bump=.05, scale=180, variation=.35, detail=10),
        dark=K.mat('Horse • Black points', (.045, .035, .03), .7, bump=.04, scale=120),
        hoof=K.mat('Horse • Hoof horn', (.085, .07, .06), .45, bump=.12, scale=90, coat=.2),
        eye=K.mat('Horse • Eye', (.018, .010, .006), .08, coat=1.),
        leather=K.mat('Tack • Oiled leather', (.17, .085, .04), .55, bump=.18, scale=140,
                      variation=.4, coat=.15),
        dark_leather=K.mat('Tack • Dark strap leather', (.07, .035, .02), .6, bump=.15, scale=140),
        brass=K.mat('Tack • Worn brass', (.62, .44, .16), .38, metal=1.),
        iron=K.mat('Tack • Forged iron', (.13, .12, .115), .5, metal=1., bump=.1, scale=80),
        rope=K.mat('Tack • Jute rope', (.40, .30, .15), .95, bump=.5, scale=300, variation=.45),
        cloth=K.mat('Tack • Saddle cloth', (.46, .12, .07), .92, bump=.3, scale=420, variation=.3),
        cotton=K.mat('Satchel • Unbleached cotton', (.55, .47, .34), .94, bump=.35, scale=500,
                     variation=.2),
        pink=K.mat('Horse • Muzzle skin', (.11, .075, .065), .5),
    )


def leg(b, m, x, y, front, hind_bend=0.):
    """One leg as lofted pieces, ending in a hoof. Returns the hoof contact point."""
    if front:
        pts = [(x, y, 1.12), (x, y-.01, .86), (x, y-.02, .62), (x, y-.02, .50), (x, y-.01, .30),
               (x, y, .12), (x, y-.05, .06)]
        radii = [(.075, .06), (.058, .052), (.05, .05), (.042, .046), (.034, .034), (.034, .036),
                 (.045, .04)]
    else:
        pts = [(x, y, 1.10), (x, y+.10, .84), (x, y+.18+hind_bend, .56), (x, y+.15, .38),
               (x, y+.16, .28), (x, y+.15, .12), (x, y+.10, .06)]
        radii = [(.11, .08), (.085, .066), (.052, .05), (.045, .046), (.036, .036), (.034, .036),
                 (.045, .04)]
    stations = [(p, r[0], r[1]) for p, r in zip(pts, radii)]
    b.loft(stations, m['coat'], sides=14)
    low = [(p, r[0]*1.012, r[1]*1.012) for p, r in list(zip(pts, radii))[3:]]
    b.loft(low, m['dark'], sides=14)  # dark stocking on the lower limb
    kz = .62 if front else .56
    b.ellipsoid((x, pts[2][1], kz), (.056, .05, .062), m['dark'], rings=8, sides=12)  # knee or hock
    b.ellipsoid((x, pts[5][1]+.012, .12), (.04, .04, .036), m['dark'], rings=8, sides=12)  # fetlock
    hy = pts[-1][1]
    b.lathe([(.060, 0), (.055, .012), (.050, .045), (.046, .068)], m['hoof'], sides=20,
            centre=(x, hy-.012, 0))
    return (x, hy, 0)


def horse(coll, m):
    b = K.MeshBuilder()
    run = [(.86, 1.05, .20, .27), (.62, 1.10, .22, .31), (.30, 1.10, .22, .34), (.0, 1.10, .22, .35),
           (-.30, 1.12, .21, .34), (-.55, 1.12, .19, .31), (-.68, 1.10, .15, .25)]
    b.loft([((0, y, z), rx, ry) for y, z, rx, ry in run], m['coat'], sides=20)
    neck = [((0, -.50, 1.22), .14, .21), ((0, -.66, 1.34), .115, .19), ((0, -.82, 1.48), .095, .16),
            ((0, -.93, 1.58), .085, .13)]
    b.loft(neck, m['coat'], sides=16)
    head = [((0, -.93, 1.60), .085, .10), ((0, -1.03, 1.52), .092, .13), ((0, -1.17, 1.38), .06, .13),
            ((0, -1.27, 1.31), .05, .07), ((0, -1.31, 1.285), .052, .055)]
    b.loft(head, m['coat'], sides=16)
    b.ellipsoid((0, -1.325, 1.285), (.056, .05, .05), m['pink'], rings=8, sides=14)
    for sx in (-1, 1):
        b.ellipsoid((sx*.05, -1.34, 1.29), (.014, .02, .012), m['dark'], rings=6, sides=10)  # nostril
        b.ellipsoid((sx*.075, -1.07, 1.60), (.032, .028, .036), m['coat'], rings=8, sides=12)
        b.ellipsoid((sx*.082, -1.07, 1.605), (.017, .014, .019), m['eye'], rings=8, sides=12)
        b.loft([((sx*.05, -.93, 1.66), .018, .028), ((sx*.058, -.935, 1.72), .014, .022),
                ((sx*.06, -.945, 1.78), .004, .004)], m['coat'], sides=8)  # ear
    legs = {}
    for name, x, y, front in (('front_L', .15, -.42, True), ('front_R', -.15, -.42, True),
                              ('hind_L', .16, .70, False), ('hind_R', -.16, .70, False)):
        legs[name] = leg(b, m, x, y, front, hind_bend=.03 if name.endswith('R') else 0.)

    return b.build('Horse • body', coll, smooth=1), legs


def hair(coll, m):
    """Mane along the crest, forelock and tail, all from tapered strands."""
    b = K.MeshBuilder()
    crest = K.spline([(0, -.95, 1.66), (0, -.84, 1.56), (0, -.70, 1.42), (0, -.55, 1.28)], 6)
    for i in range(46):
        p = crest[int(i/45*(len(crest)-1))]
        end = p + Vector((.035*math.sin(i*1.7), .01*math.cos(i), -.17 - .06*math.sin(i*.9)))
        mid = (p+end)/2 + Vector((.015, 0, .012))
        b.tube([p, mid, end], lambda s: .0026*(1-.7*s), m['dark'], sides=4)
    for i in range(7):
        a = (i-3)*.012
        p = Vector((a, -.97, 1.665))
        b.tube([p, p+Vector((a, -.03, -.04)), p+Vector((a*1.4, -.04, -.12))],
               lambda s: .0024*(1-.6*s), m['dark'], sides=4)
    for i in range(60):
        a = (i/59-.5)*.07
        root = Vector((a, .90, 1.05+.012*math.sin(i*2)))
        pts = [root, root+Vector((a*.4, .09, -.07)), root+Vector((a, .15+.02*math.sin(i), -.38)),
               root+Vector((a*1.3, .12, -.74-.03*math.sin(i*1.3)))]
        b.tube(K.spline(pts, 4), lambda s: .0028*(1-.6*s), m['dark'], sides=4)
    return b.build('Horse • mane and tail', coll)


def bridle(coll, m):
    """Headstall, browband, throatlatch, snaffle bit with rings, and a pair of reins."""
    b = K.MeshBuilder()

    def strap(points, width=.011):
        b.loft([(p, width/2, .0018) for p in points], m['leather'], sides=6)

    for sx in (-1, 1):
        strap([(sx*.098, -1.045, 1.62), (sx*.102, -1.065, 1.52), (sx*.088, -1.12, 1.42)])
        strap([(sx*.088, -1.12, 1.42), (sx*.074, -1.19, 1.36)], .009)
        strap([(sx*.098, -1.045, 1.62), (sx*.07, -1.0, 1.655), (0, -.985, 1.665)])
        ring = [(sx*.07+.022*math.cos(a), -1.185, 1.355+.022*math.sin(a))
                for a in (math.tau*i/14 for i in range(14))]
        b.tube(ring + ring[:1], .0032, m['brass'], sides=6, cap=False)
    strap([(.098, -1.075, 1.585), (0, -1.095, 1.6), (-.098, -1.075, 1.585)], .014)
    strap([(.093, -1.105, 1.47), (0, -1.14, 1.455), (-.093, -1.105, 1.47)], .013)
    b.tube([(.068, -1.19, 1.355), (0, -1.19, 1.352), (-.068, -1.19, 1.355)], .0052, m['iron'], sides=8)
    b.ellipsoid((0, -1.19, 1.352), (.008, .008, .008), m['brass'], rings=6, sides=10)
    for sx in (-1, 1):
        rein = K.spline([(sx*.092, -1.19, 1.355), (sx*.10, -1.0, 1.30), (sx*.07, -.8, 1.40),
                         (sx*.06, -.6, 1.56), (sx*.04, -.42, 1.50)], 8)
        b.loft([(p, .0075, .0025) for p in rein], m['leather'], sides=6)
    return b.build('Horse • bridle and reins', coll)


def tether(coll, m):
    """Horse tether: halter loop on the head, a lead rope with a knot, tied to the post rail.
    The far end sits at the rail height used by the Smashan set (HORSE_RAIL_Z = 1.1)."""
    b = K.MeshBuilder()
    # halter loop around the muzzle (ellipse in the XZ plane)
    loop = [(.062*math.cos(math.tau*i/20), -1.21, 1.33+.052*math.sin(math.tau*i/20)) for i in range(20)]
    K.rope(b, loop + loop[:2], .0075, m['rope'], twist=40)
    lead = K.spline([(-.058, -1.21, 1.31), (-.10, -1.18, 1.14), (-.30, -1.30, .90), (-.52, -1.42, 1.05),
                     (-.72, -1.55, 1.10)], 10)
    K.rope(b, lead, .0095, m['rope'], twist=22)
    for i in range(4):  # a hitch knot at the rail: wrapped turns
        z = 1.10+.006*i
        turn = [(-.72+.034*math.cos(math.tau*j/14), -1.55+.034*math.sin(math.tau*j/14), z) for j in range(14)]
        b.tube(turn, .0092, m['rope'], sides=6, cap=False)
    b.ellipsoid((-.72, -1.55, 1.12), (.026, .026, .022), m['rope'], rings=6, sides=10)
    tail = K.spline([(-.72, -1.55, 1.12), (-.74, -1.54, .96), (-.70, -1.53, .80)], 6)
    K.rope(b, tail, .0090, m['rope'], twist=22)
    b.ellipsoid((-.70, -1.53, .79), (.014, .014, .02), m['rope'], rings=6, sides=8)
    return b.build('Horse • tether rope', coll)


def riding_gear(coll, m):
    """Woven saddle cloth, wood-tree saddle, girth and two stirrups on leathers.
    Everything follows the barrel ellipse at y = 0 (centre z 1.10, half axes 0.22 x 0.35)."""
    b = K.MeshBuilder()

    def cloth(u, v):
        a = math.radians(78)*(2*u-1)
        y = -.10 + (v-.5)*.62
        return (.232*math.sin(a), y, 1.10 + .362*math.cos(a) - .05*(v-.5)**2)

    K.cloth_sheet(b, 18, 14, cloth, m['cloth'], .008)
    seat = [((0, y, z), rx, ry) for y, z, rx, ry in
            ((-.30, 1.50, .085, .035), (-.15, 1.485, .13, .040), (.0, 1.475, .15, .042),
             (.18, 1.485, .14, .045), (.30, 1.52, .09, .06))]
    b.loft(seat, m['leather'], sides=16)
    for sx in (-1, 1):
        panel = [((sx*.17, y, z), .026, .11) for y, z in ((-.26, 1.40), (-.1, 1.385), (.1, 1.385), (.24, 1.41))]
        b.loft(panel, m['dark_leather'], sides=10)
    b.ellipsoid((0, -.32, 1.545), (.05, .035, .05), m['leather'], rings=8, sides=14)   # pommel
    b.ellipsoid((0, .33, 1.57), (.075, .035, .07), m['leather'], rings=8, sides=14)    # cantle
    for sx in (-1, 1):
        belt = K.spline([(sx*.13, -.02, 1.395), (sx*.238, -.02, 1.20), (sx*.218, -.02, .95)], 8)
        b.loft([(p, .0275, .004) for p in belt], m['dark_leather'], sides=6)
        b.box((.03, .03, .008), (sx*.218, -.02, .945), m['brass'])
        lea = K.spline([(sx*.17, .0, 1.36), (sx*.265, .0, 1.15), (sx*.30, .0, .84)], 8)
        b.loft([(p, .0095, .003) for p in lea], m['leather'], sides=6)
        b.box((.022, .018, .018), (sx*.17, .0, 1.365), m['brass'])
        iron = [(sx*.30+.065*math.cos(a), 0, .78+.052*math.sin(a)) for a in (math.tau*i/16 for i in range(17))]
        b.tube(iron, .0085, m['iron'], sides=6, cap=False)
        b.box((.125, .045, .008), (sx*.30, 0, .728), m['iron'])
    return b.build('Horse • saddle, cloth, girth and stirrups', coll)


def satchel(coll, m, location=(0, 0, 0)):
    """Cotton statement satchel: roomy sack with a folded flap, tie cord and a carrying strap.
    Sized to hold the folded 24 x 32 cm sheets (flat 25 x 18 cm opening); origin at the base."""
    b = K.MeshBuilder()
    w, d, h = .30, .09, .26
    def sack(u, v):
        a = math.tau*u
        belly = 1 + .10*math.sin(math.pi*v)
        r = (.5*w*math.cos(a), .5*d*belly*math.sin(a))
        return (r[0]*(1-.05*v), r[1], h*v)
    # thick fabric body from a closed loft
    stations = [((0, 0, z), .5*w*(1-.04*z/h)*(.92 if z < .02 else 1), .5*d*(1+.35*math.sin(math.pi*z/h)))
                for z in (0.0, .03, .08, .14, .20, .25)]
    b.loft(stations, m['cotton'], sides=28, cap=True)
    def flap(u, v):
        return ((u-.5)*w*.97, -.5*d*1.18 + .006*math.sin(v*5) + 0*v, h*.98 - v*h*.52 + .04*math.sin(math.pi*u)*(1-v))
    K.cloth_sheet(b, 14, 8, flap, m['cotton'], .005)
    for sx in (-1, 1):
        b.ellipsoid((sx*.075, -.058, h*.50), (.012, .008, .012), m['brass'], rings=6, sides=10)
    cord = K.spline([(-.06, -.062, h*.53), (-.02, -.07, h*.50), (.03, -.068, h*.46), (.06, -.063, h*.30)], 6)
    K.rope(b, cord, .0032, m['rope'], strands=2, twist=60, sides=5)
    strap = K.spline([(-.15, 0, h*.95), (-.17, .01, h*1.35), (-.0, .02, h*1.55), (.17, .01, h*1.35), (.15, 0, h*.95)], 8)
    b.loft([(p, .0125, .0035) for p in strap], m['dark_leather'], sides=6)
    obj = b.build('Satchel • statement bag', coll, smooth=0, location=location)
    obj['Inner width (m)'] = w - .02
    obj['Holds'] = 'Seven folded statement sheets (see Documents props); 0.30 m wide'
    return obj
