"""सहायक पहरेदार (the assistant guard). Spec and two costumes on one rig.

He stands at the palace door, reports the search of Shyam's old house and takes
the order to ready the horse (Chapter 1). The same body, face and skeleton wear
a second, court costume when he brings Nandu to the durbar.

DUTY  - plain ivory-khaki tunic, leather belt, pagri and a long spear.
COURT - clean maroon angarkha with a sash and a plumed turban, no spear.
"""

from math import cos, sin, tau


SPEC = dict(name='SahayakPahredar', height=1.0, skin=(.40,.215,.115),
            hair=(.022,.016,.012), iris=(.07,.036,.016), face_width=1.02,
            nose_width=1.0, brow_lift=.002)

VARIANTS = ('duty', 'court')


def spec_for(variant):
    """Same body and face for every costume; only the asset name differs."""
    if variant not in VARIANTS:
        raise ValueError(f'unknown costume {variant!r}; use one of {VARIANTS}')
    result = dict(SPEC)
    result['name'] = 'SahayakPahredar' if variant == 'duty' else 'SahayakPahredar_Court'
    return result


def _sleeves(c, cloth, edge):
    for side in ('L', 'R'):
        source = next(part for part in c.parts if part.name == f'{c.name}_Arm.{side}')
        sleeve = source.copy()
        sleeve.data = source.data.copy()
        sleeve.name = f'{c.name}_Tunic sleeve {side}'
        sleeve.data.materials.clear()
        sleeve.data.materials.append(cloth)
        # Same deformation weights as the arm, so the sleeve follows the elbow.
        for vertex in sleeve.data.vertices:
            vertex.co.y *= 1.30
            vertex.co.z = 1.375*c.scale + (vertex.co.z - 1.375*c.scale)*1.30
        c.collection.objects.link(sleeve)
        c.parts.append(sleeve)
        cuff = [tuple(vertex.co/c.scale) for vertex in sleeve.data.vertices[-24:]]
        c.tube(f'Sleeve cuff {side}', cuff, .0035, edge, f'hand.{side}', cyclic=True)


def _legs(c, trousers, leather, wrap):
    for side, sign in (('L', 1), ('R', -1)):
        c.loft(f'Trouser {side}', [(.13,sign*.135,0,.058,.054),(.5,sign*.135,0,.084,.080),
               (.72,sign*.125,0,.090,.088),(.84,sign*.118,0,.082,.084)], trousers,
               [f'shin.{side}',{f'shin.{side}':.5,f'thigh.{side}':.5},f'thigh.{side}','hips'])
        c.loft(f'Leg wrap {side}', [(.17,sign*.135,0,.062,.058),(.30,sign*.135,.005,.066,.062),
               (.43,sign*.135,0,.071,.066)], wrap, f'shin.{side}')
        c.ovoid(f'Boot {side}', (sign*.135,-.057,.052), (.064,.125,.050), leather, f'foot.{side}')
        c.loft(f'Boot shaft {side}', [(.06,sign*.135,0,.058,.056),(.17,sign*.135,0,.060,.058)],
               leather, f'foot.{side}')


def _turban(c, cloth, edge, wraps):
    for index in range(wraps):
        z = 1.735 + index*.019
        rx, ry = .130 - index*.004, .116 - index*.004
        ring = [(rx*cos(tau*j/36), .004 + ry*sin(tau*j/36), z + .010*sin(2*tau*j/36 + index))
                for j in range(36)]
        c.tube(f'Turban wrap {index+1}', ring, .0125, cloth, 'head', cyclic=True)
    c.ovoid('Turban crown', (0, .004, 1.80), (.108, .100, .045), cloth, 'head')
    c.tube('Turban tail', [(.07,.115,1.74),(.09,.145,1.66),(.085,.150,1.58),(.075,.142,1.52)],
           [.016,.018,.016,.012], edge, 'head')


def _moustache(c, hair):
    for sign, side in ((1, 'L'), (-1, 'R')):
        points = [(sign*.004, c.face_y(sign*.004, 1.592)-.006, 1.592),
                  (sign*.022, c.face_y(sign*.022, 1.590)-.006, 1.590),
                  (sign*.040, c.face_y(sign*.040, 1.584)-.004, 1.582),
                  (sign*.050, c.face_y(sign*.050, 1.572)-.003, 1.568)]
        c.tube(f'Moustache {side}', points, [.0045,.0075,.0060,.0022], hair, 'head')


def _spear(c, wood, steel, cord):
    # Planted beside the right hand as posed by build_guard.standing_pose (hand hangs
    # at about x=-.41, z=.83). Weighted to root so the shaft stays vertical.
    x, y = -.41, -.045
    c.tube('Spear shaft', [(x,y,.02),(x,y,1.2),(x,y,2.08)], .0155, wood, 'root')
    c.ovoid('Spear blade', (x,y,2.16), (.026,.007,.095), steel, 'root')
    c.ovoid('Spear socket', (x,y,2.075), (.021,.021,.020), steel, 'root')
    c.tube('Spear tassel cord', [(x,y,2.05),(x+.012,y-.01,2.0),(x+.014,y-.012,1.95)],
           .006, cord, 'root')


def _duty(c):
    tunic = c.mat('Ivory-khaki guard tunic', (.50,.43,.29), .92)
    seam = c.mat('Tunic seam', (.28,.23,.15), .92)
    trousers = c.mat('Dusty brown trousers', (.19,.145,.095), .94)
    leather = c.mat('Worn leather', (.085,.046,.022), .78)
    wrap = c.mat('Ankle wrap cloth', (.40,.34,.24), .93)
    brass = c.mat('Belt buckle brass', (.33,.20,.07), .45, .5)
    steel = c.mat('Dull spear steel', (.42,.42,.43), .38, .85)
    wood = c.mat('Spear shaft wood', (.20,.115,.055), .82)
    cord = c.mat('Faded red cord', (.30,.055,.04), .9)
    pagri = c.mat('Faded saffron pagri', (.62,.30,.07), .9)

    c.loft('Tunic body', [(.64,0,0,.235,.150),(.78,0,0,.225,.145),(.92,0,0,.215,.137),
           (1.08,0,0,.180,.115),(1.23,0,0,.205,.125),(1.38,0,0,.230,.108),
           (1.44,0,0,.078,.062)], tunic,
           ['hips','hips','hips','spine','chest','chest','chest'])
    _sleeves(c, tunic, seam)
    c.tube('Tunic collar', [(-.066,-.052,1.44),(-.068,-.088,1.405),(-.042,-.106,1.368),
           (0,-.120,1.340),(.042,-.106,1.368),(.068,-.088,1.405),(.066,-.052,1.44)],
           .006, seam, 'chest')
    for index, z in enumerate((1.31, 1.25, 1.19)):
        c.ovoid(f'Tunic button {index+1}', (0,-.126,z), (.008,.005,.008), brass, 'chest')
    c.loft('Leather belt', [(.97,0,0,.222,.142),(1.02,0,0,.220,.140)], leather, 'hips')
    c.ovoid('Belt buckle', (0,-.142,.995), (.026,.008,.020), brass, 'hips')
    _legs(c, trousers, leather, wrap)
    _turban(c, pagri, c.mat('Pagri tail cloth', (.50,.24,.06), .9), 4)
    _moustache(c, c.m['hair'])
    _spear(c, wood, steel, cord)


def _court(c):
    tunic = c.mat('Court maroon angarkha', (.30,.055,.045), .88)
    border = c.mat('Court brass-gold border', (.46,.31,.10), .55, .35)
    sash = c.mat('Court ivory sash', (.66,.60,.46), .9)
    trousers = c.mat('Court ivory churidar', (.58,.52,.39), .92)
    leather = c.mat('Polished court shoes', (.07,.04,.02), .55)
    wrap = c.mat('Court churidar fold', (.52,.46,.34), .92)
    brass = c.mat('Court brass', (.38,.24,.08), .38, .6)
    pagri = c.mat('Court maroon pagri', (.34,.06,.05), .88)
    tail = c.mat('Court pagri plume cloth', (.70,.58,.30), .85)

    c.loft('Angarkha body', [(.60,0,0,.250,.160),(.76,0,0,.238,.152),(.92,0,0,.222,.140),
           (1.08,0,0,.182,.116),(1.23,0,0,.208,.127),(1.38,0,0,.232,.110),
           (1.44,0,0,.080,.064)], tunic,
           ['hips','hips','hips','spine','chest','chest','chest'])
    _sleeves(c, tunic, border)
    c.tube('Angarkha diagonal border', [(-.070,-.052,1.44),(-.060,-.115,1.36),(-.030,-.130,1.25),
           (.010,-.138,1.14),(.050,-.142,1.03),(.085,-.150,.90),(.100,-.152,.70),(.108,-.150,.61)],
           .006, border, 'chest')
    c.loft('Angarkha hem border', [(.60,0,0,.253,.163),(.625,0,0,.252,.162)], border, 'hips')
    c.loft('Court sash', [(.93,0,0,.228,.146),(1.00,0,0,.226,.144),(1.05,0,0,.220,.140)],
           sash, 'hips')
    c.tube('Sash knot tail', [(.12,-.150,1.0),(.15,-.158,.88),(.145,-.162,.72),(.14,-.160,.62)],
           [.020,.024,.022,.016], sash, 'hips')
    for index, z in enumerate((1.33, 1.27, 1.21)):
        c.ovoid(f'Angarkha button {index+1}', (-.05+index*.012,-.134,z), (.008,.005,.008), brass, 'chest')
    _legs(c, trousers, leather, wrap)
    _turban(c, pagri, tail, 5)
    c.ovoid('Turban brooch', (-.012,-.116,1.77), (.014,.007,.020), brass, 'head')
    c.tube('Turban plume', [(-.012,-.12,1.78),(-.01,-.12,1.86),(.02,-.10,1.94),(.05,-.08,1.99)],
           [.007,.011,.009,.002], tail, 'head')
    _moustache(c, c.m['hair'])
    for sign, side in ((1, 'L'), (-1, 'R')):
        c.tube(f'Wrist bangle {side}', [(sign*.700, .028*cos(tau*j/20), 1.375 + .028*sin(tau*j/20))
               for j in range(20)], .0045, brass, f'hand.{side}', cyclic=True)


def dress(c, variant='duty'):
    """Dress an already built body and face in the chosen costume."""
    if variant == 'duty':
        _duty(c)
    elif variant == 'court':
        _court(c)
    else:
        raise ValueError(f'unknown costume {variant!r}; use one of {VARIANTS}')
