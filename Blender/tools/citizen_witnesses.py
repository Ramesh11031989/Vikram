"""गवाह: दो अन्य नगरवासी (two other townsfolk witnesses). Specs and costumes.

The story fixes neither their trade, gender nor relationship, so nothing here
implies one. Both share the citizen rig (the standard Character skeleton and
face) and differ in outline and dress:

* Citizen A: tall and lean, long indigo tunic, wound rust turban.
* Citizen B: shorter and sturdier, short ochre kurta, draped shawl, low hair knot.
"""

from math import cos, sin, tau


SPEC_A = dict(name='CitizenA', height=.99, skin=(.40,.215,.115), hair=(.03,.021,.016),
              iris=(.07,.036,.016), face_width=.92, nose_width=.94, brow_lift=.002)
SPEC_B = dict(name='CitizenB', height=.90, skin=(.50,.28,.155), hair=(.02,.014,.011),
              iris=(.09,.048,.022), face_width=1.06, nose_width=1.02, brow_lift=.0)

SPECS = (SPEC_A, SPEC_B)


def sleeves(c, cloth, edge, bulk, count):
    """Sleeves that follow the arm weights; `count` rings sets the length."""
    form = ((.17,.050),(.21,.057),(.25,.062),(.312,.064),(.397,.062),
            (.49,.055),(.60,.048),(.68,.041))[:count]
    for sign, side in ((1,'L'),(-1,'R')):
        upper, lower = f'upper_arm.{side}', f'forearm.{side}'
        weights = ['chest','chest',{'chest':.40,upper:.60},upper,upper,
                   {upper:.30,lower:.70},lower,lower][:count]
        rings = [[(sign*x, sign*radius*bulk*cos(tau*j/24), 1.375+radius*bulk*sin(tau*j/24))
                  for j in range(24)] for x,radius in form]
        c.ring_mesh(f'Sleeve {side}', rings, cloth, weights)
        c.tube(f'Sleeve hem {side}', rings[-1], .0045, edge, lower if count > 5 else upper,
               cyclic=True)


def trousers(c, cloth, edge, width, hem_z):
    for sign, side in ((1,'L'),(-1,'R')):
        shin, thigh = f'shin.{side}', f'thigh.{side}'
        rings = [(hem_z,sign*.135,0,.058*width,.054*width),(.5,sign*.135,0,.08*width,.075*width),
                 (.75,sign*.125,0,.105*width,.10*width),(.95,sign*.10,0,.118*width,.122*width)]
        c.loft(f'Trouser {side}', rings, cloth, [shin,{shin:.5,thigh:.5},thigh,'hips'])
        ring = [(sign*.135+.058*width*cos(tau*j/24), .054*width*sin(tau*j/24), hem_z)
                for j in range(24)]
        c.tube(f'Trouser hem {side}', ring, .0045, edge, shin, cyclic=True)


def dress_a(c):
    """Citizen A: long indigo tunic over plain trousers, wound turban."""
    cloth = c.mat('Indigo tunic cloth', (.075,.10,.205), .90)
    lining = c.mat('Tunic undyed edge', (.60,.54,.42), .88)
    pants = c.mat('Faded sand trousers', (.50,.42,.29), .92)
    wrap = c.mat('Rust turban cloth', (.43,.145,.055), .90)
    leather = c.mat('Worn tan sandals', (.20,.115,.06), .82)
    legs = {'hips':.5,'thigh.L':.25,'thigh.R':.25}
    c.loft('Long tunic', [(.45,0,.004,.19,.14),(.78,0,.004,.205,.14),(.95,0,.002,.19,.128),
           (1.10,0,0,.168,.108),(1.24,0,0,.19,.115),(1.37,0,0,.205,.10),(1.44,0,0,.085,.066)],
           cloth, [legs,legs,'hips','spine',{'spine':.4,'chest':.6},'chest','chest'])
    c.tube('Tunic front edge', [(0,-.145,.62),(0,-.146,.80),(0,-.131,.98),(0,-.118,1.16),
           (0,-.116,1.30),(0,-.114,1.37)], .0065, lining, 'spine')
    c.tube('Tunic collar', [(-.07,-.05,1.44),(-.068,-.088,1.40),(-.036,-.108,1.365),(0,-.116,1.35),
           (.036,-.108,1.365),(.068,-.088,1.40),(.07,-.05,1.44)], .006, lining, 'chest')
    c.loft('Tunic waist cloth', [(.97,0,0,.202,.139),(1.03,0,0,.198,.136)], wrap, 'hips')
    sleeves(c, cloth, lining, 1.14, 8)
    trousers(c, pants, lining, 1.08, .15)
    for sign, side in ((1,'L'),(-1,'R')):
        c.ovoid(f'Sandal sole {side}', (sign*.135,-.06,.024), (.066,.132,.026), leather, f'foot.{side}')
        c.tube(f'Sandal strap {side}', [(sign*.09,-.02,.04),(sign*.135,-.05,.092),(sign*.18,-.02,.04)],
               .007, leather, f'foot.{side}')
    c.ovoid('Short hair', (0,.018,1.735), (.118,.104,.09), c.m['hair'], 'head')
    for index, (z, rx, ry, tilt) in enumerate(((1.738,.128,.114,0),(1.766,.126,.112,.07),
                                              (1.793,.118,.105,-.06),(1.82,.09,.082,.05))):
        c.ovoid(f'Turban band {index+1}', (0,.008,z), (rx,ry,.03), wrap, 'head', (0,tilt,0))
    c.ovoid('Turban crown', (0,.008,1.845), (.074,.07,.03), wrap, 'head')
    c.tube('Turban tail', [(.1,.085,1.78),(.13,.1,1.69),(.136,.092,1.60),(.13,.07,1.53)],
           [.014,.02,.022,.016], wrap, 'head')


def dress_b(c):
    """Citizen B: short ochre kurta, draped shawl, loose trousers, low knot."""
    cloth = c.mat('Ochre cotton kurta', (.46,.30,.075), .91)
    seam = c.mat('Kurta brown seam', (.20,.12,.05), .91)
    pants = c.mat('Charcoal loose trousers', (.105,.10,.095), .94)
    shawl = c.mat('Moss green shawl', (.12,.21,.115), .93)
    border = c.mat('Shawl cream border', (.66,.60,.46), .9)
    band = c.mat('Plum hair cord', (.21,.05,.10), .85)
    c.loft('Short kurta', [(.80,0,.004,.215,.145),(.93,0,.006,.225,.150),(1.08,0,.004,.21,.14),
           (1.23,0,0,.225,.133),(1.36,0,0,.24,.115),(1.44,0,0,.09,.07)], cloth,
           ['hips','hips','spine',{'spine':.4,'chest':.6},'chest','chest'])
    c.tube('Kurta placket', [(0,-.150,.80),(0,-.157,.93),(0,-.146,1.08),(0,-.134,1.23),
           (0,-.118,1.36),(0,-.10,1.42)], .005, seam, 'spine')
    for index, z in enumerate((1.34,1.27,1.20,1.13)):
        c.ovoid(f'Kurta button {index+1}', (0,-.139,z), (.008,.005,.008), seam, 'chest')
    c.tube('Kurta collar', [(-.075,-.05,1.44),(-.07,-.09,1.41),(-.038,-.11,1.38),(0,-.118,1.365),
           (.038,-.11,1.38),(.07,-.09,1.41),(.075,-.05,1.44)], .0065, seam, 'chest')
    sleeves(c, cloth, seam, 1.22, 5)
    trousers(c, pants, seam, 1.3, .12)
    for sign, side in ((1,'L'),(-1,'R')):
        c.ovoid(f'Cloth shoe {side}', (sign*.135,-.06,.047), (.064,.122,.047), seam, f'foot.{side}')
    # Shawl: over the left shoulder, falling across the chest toward the right hip.
    c.tube('Shawl across chest', [(.19,.012,1.45),(.12,-.125,1.37),(.02,-.17,1.22),(-.08,-.166,1.05),
           (-.17,-.135,.90)], [.031,.035,.037,.035,.03], shawl, 'chest')
    c.tube('Shawl over shoulder', [(.19,.012,1.45),(.2,.07,1.36),(.19,.125,1.18),(.16,.14,.98)],
           [.031,.03,.028,.024], shawl, 'chest')
    c.tube('Shawl border', [(.19,.012,1.481),(.12,-.125,1.405),(.02,-.17,1.256),(-.08,-.166,1.086),
           (-.17,-.135,.935)], .004, border, 'chest')
    # Hair gathered into a low knot with a cord.
    c.ovoid('Hair cap', (0,.012,1.745), (.123,.108,.075), c.m['hair'], 'head')
    c.ovoid('Hair back', (0,.03,1.69), (.116,.1,.085), c.m['hair'], 'head')
    c.ovoid('Hair knot', (0,.118,1.62), (.052,.05,.058), c.m['hair'], 'head')
    c.tube('Hair cord', [(-.05+.1*i/11, .096+.012*sin(3.1416*i/11), 1.66) for i in range(12)],
           .006, band, 'head')
    for sign, side in ((1,'L'),(-1,'R')):
        c.ovoid(f'Temple hair {side}', (sign*.112,-.02,1.715), (.012,.03,.03), c.m['hair'], 'head')


DRESS = {'CitizenA': dress_a, 'CitizenB': dress_b}

