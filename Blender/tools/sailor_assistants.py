"""सहायक: शरण-सूची बनाने वाले दो नाविक (two sailor assistants who keep the refuge list).

On the slope the two sailors write down the names of the people who came with
Betal. This is shown only if the previous night is staged, so both are built on
the citizen rig (standard Character skeleton and face) and dressed as boatmen.
The story fixes neither gender nor relationship, so nothing here implies one.
Neither is Gopal.

* Sailor A: lean, undyed short tunic, rope belt, rolled trousers, bare feet,
  tied head cloth, reed pen behind the ear.
* Sailor B: sturdier, teal sleeveless vest, knee wrap, neck cloth, low hair knot,
  a name list hanging at the waist.
"""

from math import cos, pi, sin, tau

from citizen_witnesses import sleeves, trousers


SPEC_A = dict(name='SailorA', height=.97, skin=(.37,.19,.10), hair=(.025,.018,.014),
              iris=(.075,.04,.018), face_width=.95, nose_width=.98, brow_lift=.001)
SPEC_B = dict(name='SailorB', height=.92, skin=(.45,.24,.13), hair=(.02,.014,.011),
              iris=(.085,.045,.02), face_width=1.04, nose_width=1.05, brow_lift=.0)

SPECS = (SPEC_A, SPEC_B)


def silt_dust(c, silt):
    """Barefoot boatmen: a dusting of dry silt on the lower legs."""
    for sign, side in ((1, 'L'), (-1, 'R')):
        for i in range(6):
            angle = i * 2.399
            c.ovoid(f'Dried silt {side} {i+1}', (sign*.135+cos(angle)*.04, sin(angle)*.04, .05+i*.018),
                    (.008, .002, .009), silt, f'shin.{side}', (0, .1*i, angle-pi/2))


def dress_a(c):
    """Sailor A: undyed short tunic, rope belt, rolled trousers, head cloth, reed pen."""
    cloth = c.mat('Undyed river cotton', (.50,.43,.30), .93)
    edge = c.mat('Tunic brown stitching', (.22,.14,.07), .90)
    pants = c.mat('Rolled hemp trousers', (.30,.235,.15), .95)
    rope = c.mat('Twisted jute rope', (.42,.30,.14), .92)
    wrap = c.mat('Faded madder head cloth', (.40,.12,.07), .90)
    silt = c.mat('Dried river silt', (.236,.162,.099), .95)
    reed = c.mat('Cut reed pen', (.55,.44,.22), .70)
    c.loft('Short boatman tunic', [(.80,0,.004,.20,.14),(.93,0,.005,.205,.145),(1.08,0,.003,.19,.135),
           (1.23,0,0,.205,.125),(1.36,0,0,.22,.108),(1.44,0,0,.085,.066)], cloth,
           ['hips','hips','spine',{'spine':.4,'chest':.6},'chest','chest'])
    c.tube('Tunic neck opening', [(-.07,-.05,1.44),(-.066,-.088,1.405),(-.034,-.108,1.365),(0,-.116,1.34),
           (.034,-.108,1.365),(.066,-.088,1.405),(.07,-.05,1.44)], .006, edge, 'chest')
    sleeves(c, cloth, edge, 1.15, 5)
    trousers(c, pants, edge, 1.05, .40)
    silt_dust(c, silt)
    c.tube('Rope belt', [(.205*cos(tau*j/40), .141*sin(tau*j/40), .955+.006*sin(tau*j*3/40))
                         for j in range(41)], .010, rope, 'hips', cyclic=True)
    c.tube('Rope belt tail', [(-.10,-.138,.955),(-.115,-.142,.88),(-.12,-.136,.80),(-.105,-.13,.74)],
           [.010,.009,.008,.006], rope, 'hips')
    c.ovoid('Short hair', (0,.018,1.735), (.118,.104,.09), c.m['hair'], 'head')
    for index, (z, rx, ry, tilt) in enumerate(((1.738,.127,.112,0),(1.762,.125,.11,.06),
                                               (1.786,.114,.102,-.05))):
        c.ovoid(f'Head cloth band {index+1}', (0,.008,z), (rx,ry,.027), wrap, 'head', (0,tilt,0))
    c.tube('Head cloth knot tail', [(-.09,.085,1.77),(-.12,.10,1.70),(-.125,.098,1.63)],
           [.014,.018,.012], wrap, 'head')
    c.tube('Reed pen behind ear', [(.118,.015,1.70),(.121,-.02,1.735),(.118,-.06,1.775)],
           .0045, reed, 'head')


def dress_b(c):
    """Sailor B: teal sleeveless vest, knee wrap, neck cloth, low knot, name list."""
    vest = c.mat('Deep teal vest', (.04,.17,.17), .88)
    trim = c.mat('Vest bleached binding', (.58,.52,.38), .88)
    wrap_cloth = c.mat('Indigo knee wrap', (.07,.09,.19), .92)
    neck = c.mat('Saffron neck cloth', (.62,.34,.06), .88)
    band = c.mat('Plum hair cord', (.21,.05,.10), .85)
    silt = c.mat('Dried river silt', (.236,.162,.099), .95)
    leaf = c.mat('Oiled name-list paper', (.62,.55,.38), .85)
    cord = c.mat('Name-list cord', (.25,.16,.08), .9)
    c.loft('Boatman vest', [(.88,0,.004,.22,.15),(1.00,0,.006,.205,.145),(1.12,0,.004,.2,.138),
           (1.25,0,0,.222,.128),(1.36,0,0,.236,.112),(1.43,0,0,.10,.07)], vest,
           ['hips','hips','spine',{'spine':.4,'chest':.6},'chest','chest'])
    c.tube('Vest front binding', [(0,-.152,.88),(0,-.158,1.00),(0,-.146,1.12),(0,-.133,1.25),
           (0,-.118,1.36),(0,-.10,1.42)], .006, trim, 'spine')
    c.tube('Vest neck binding', [(-.08,-.05,1.43),(-.072,-.09,1.40),(-.04,-.11,1.37),(0,-.118,1.355),
           (.04,-.11,1.37),(.072,-.09,1.40),(.08,-.05,1.43)], .006, trim, 'chest')
    sleeves(c, vest, trim, 1.2, 3)
    legs = {'hips': .5, 'thigh.L': .25, 'thigh.R': .25}
    c.loft('Knee wrap', [(.50,0,0,.222,.138),(.70,0,0,.222,.136),(.80,0,0,.215,.134),
           (.87,0,0,.205,.13)], wrap_cloth, [legs, legs, 'hips', 'hips'])
    c.tube('Knee wrap hem', [(.222*cos(tau*j/40), .138*sin(tau*j/40), .50) for j in range(40)],
           .006, trim, 'hips', cyclic=True)
    silt_dust(c, silt)
    c.tube('Neck cloth', [(-.115,-.04,1.43),(-.10,-.115,1.40),(0,-.15,1.385),(.10,-.115,1.40),
           (.115,-.04,1.43)], .022, neck, 'chest')
    c.tube('Neck cloth ends', [(-.04,-.15,1.385),(-.05,-.17,1.28),(-.045,-.172,1.17)],
           [.022,.02,.016], neck, 'chest')
    c.tube('Name-list cord', [(.14,-.14,.98),(.19,-.15,.93),(.205,-.12,.90)], .004, cord, 'hips')
    c.ovoid('Name list', (.20,-.145,.84), (.045,.012,.07), leaf, 'hips', (0,.05,.1))
    c.ovoid('Hair cap', (0,.012,1.745), (.123,.108,.075), c.m['hair'], 'head')
    c.ovoid('Hair back', (0,.03,1.69), (.116,.1,.085), c.m['hair'], 'head')
    c.ovoid('Hair knot', (0,.118,1.63), (.05,.048,.055), c.m['hair'], 'head')
    c.tube('Hair cord', [(-.05+.1*i/11, .096+.012*sin(pi*i/11), 1.67) for i in range(12)],
           .006, band, 'head')


DRESS = {'SailorA': dress_a, 'SailorB': dress_b}

