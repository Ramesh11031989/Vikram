"""Shared layout numbers for set 3: निचली बस्ती और अनाज मंडी (lower settlement and grain market).
Pure Python, no Blender needed.

Same world map as SET_Palace and SET_Ghat: metres, +X east, +Y north, Z up, Z = 0 at the ghat's
top quay, origin at the top step centre. The Halwai roof eye and the market ridge come from
`map_anchors` in SET_Palace_Manifest.json; the gate comes from `ghat_layout.py`.
"""

import ghat_layout as G

HALWAI_EYE = (-60.0, 78.0, 6.2)           # palace map anchor: Halwai roof eye (roof floor 4.5 + 1.7 standing)
RIDGE = (-38.0, 34.0, 9.0)                # palace map anchor: grain-market thatched roof ridge
GATE = (G.GATE_X, G.GATE_Y, 0.0)          # from the ghat set
GROUND_X = (-90.0, 90.0)                  # same X extent as the ghat quay ground
TOWN_Y = (34.0, 130.0)                    # this set's ground; the ghat quay ground covers y < 34 up to the river bank
EYE_HEIGHT = 1.7

BAY = 3.0                                 # module bay width; every house is a whole number of bays
WALL_T, PLINTH, PARAPET = .30, .35, .70
DOOR_W, DOOR_H = 1.10, 2.10
WINDOW_W, WINDOW_H, WINDOW_SILL = 1.00, 1.00, .95

# One spec per house. Front faces local -Y; yaw turns it (180 = faces north, 0 = faces south, 90 = faces east).
HALWAI_NAME, FRONT_NAME, NEIGHBOUR_NAME = 'Halwai house', 'Front house', 'Neighbour house'
HALWAI = dict(name=HALWAI_NAME, center=(-60.0, 79.5), bays=(3, 2), floors=1, story=4.15, roof='flat', yaw=0,
              wall='lime', collection='Town | Halwai house & roof (हलवाई की छत)')
FRONT = dict(name=FRONT_NAME, center=(-58.0, 65.5), bays=(3, 2), floors=1, story=3.0, roof='flat', yaw=180,
             wall='ochre', collection='Town | Front house roof (सामने की छत)')
NEIGHBOUR = dict(name=NEIGHBOUR_NAME, center=(-78.0, 79.5), bays=(2, 2), floors=1, story=3.0, roof='thatch', yaw=0,
                 wall='mud', collection='Town | Neighbour house & cattle place (पड़ोसन का मवेशी बाँधने का स्थान)')
HALWAI_ROOF_Z = PLINTH + HALWAI['story']              # 4.5
FRONT_ROOF_Z = PLINTH + FRONT['story']                # 3.35

# Halwai roof: a solid stair on the east wall climbs north and lands at the roof through a gap in the parapet.
STAIR = dict(x=(-55.5, -54.5), y0=76.5, steps=20, tread=.25, landing_to=82.5, parapet_gap=(81.0, 82.5))
STAIR['y_top'] = STAIR['y0'] + STAIR['steps'] * STAIR['tread']
WEST_STANCE = (-63.8, 78.5, HALWAI_ROOF_Z + EYE_HEIGHT)   # at the west parapet, looking down into the cattle place
FRONT_BOY = (-58.0, 65.5, FRONT_ROOF_Z + EYE_HEIGHT)      # the boy who shouted, standing on the front roof

# Neighbour's cattle place: open yard between her house and the Halwai's west wall.
CATTLE = dict(center=(-69.75, 80.5), size=(10.5, 8.0))
CATTLE_SAMPLES = [(-70.0, 80.0, .06), (-72.0, 82.0, 1.0), (-68.0, 82.0, 1.0)]

# Grain market: tall thatched shed on a raised veranda platform. Ridge along X.
MANDI = dict(roof_x=(-44.15, -31.85), roof_half_y=5.6, ridge_z=RIDGE[2], eave_z=2.7, thick=.35,
             platform=(11.6, 9.0), platform_z=.6)

# Open refuge floor (शरण के लिए खुला फ़र्श): flat, nothing on it, nothing over it.
REFUGE = dict(center=(-10.0, 46.0), size=(18.0, 14.0), top=.20)

# Lanes (x0, y0, x1, y1): A runs west-east between the two house rows; B runs from the ghat up to lane A.
LANES = dict(A=(-90.0, 69.0, -8.0, 76.5), B=(-22.8, -1.3, -19.2, 69.0))

# Modular houses on the 3 m bay grid (yaw: 180 faces north onto lane A, 0 faces south, 90 faces east).
MODULE_COLLECTION = 'Town | Modular houses (मॉड्यूलर मकान)'
MODULES = [
    dict(name='Module house 1', center=(-70.0, 65.5), bays=(2, 2), floors=1, story=3.0, roof='thatch', yaw=180, wall='mud'),
    dict(name='Module house 2', center=(-86.0, 65.5), bays=(2, 2), floors=2, story=3.0, roof='flat', yaw=180, wall='lime'),
    dict(name='Module house 3', center=(-38.0, 65.5), bays=(3, 2), floors=1, story=3.0, roof='tile', yaw=180, wall='ochre'),
    dict(name='Module house 4', center=(-14.0, 65.5), bays=(2, 2), floors=2, story=3.0, roof='flat', yaw=180, wall='lime'),
    dict(name='Module house 5', center=(-48.0, 79.5), bays=(3, 2), floors=1, story=3.0, roof='thatch', yaw=0, wall='mud'),
    dict(name='Module house 6', center=(-32.0, 79.5), bays=(2, 2), floors=2, story=3.0, roof='flat', yaw=0, wall='ochre'),
    dict(name='Module house 7', center=(-16.0, 79.5), bays=(3, 2), floors=1, story=3.0, roof='tile', yaw=0, wall='lime'),
    dict(name='Module house 8', center=(-12.0, 59.0), bays=(2, 2), floors=1, story=3.0, roof='thatch', yaw=90, wall='mud'),
    dict(name='Module house 9', center=(-34.0, 56.0), bays=(2, 2), floors=1, story=3.0, roof='tile', yaw=180, wall='lime'),
]
for _spec in MODULES:
    _spec['collection'] = MODULE_COLLECTION
HOUSES = [HALWAI, FRONT, NEIGHBOUR] + MODULES
TREES = [(-45.0, 88.0), (-6.0, 71.0), (-84.0, 90.0), (6.0, 60.0)]
KIT_ROW = dict(origin=(-86.0, 100.0), kinds=('solid', 'door', 'window'))

# Sight-line samples used by the checks.
# Gate samples sit just north of the grille, in the open air on the town side of the gate.
GATE_SAMPLES = [(x, G.GATE_Y + .45, z) for x in (-21.8, -21.0, -20.2) for z in (.4, 2.0, 4.0, 5.6)]
# The Halwai sees the middle and east of the ghat: the low riverside wall's coping, a mooring post and the
# east step cheek wall (the 0.75 m wall hides the quay ground behind it). The shed covers everything from
# x = -5 westward, which includes the gate.
GHAT_SAMPLES = ([(x, G.BANK_Y + .30, G.WALL_TOP + .09) for x in (10.0, 16.0)]
                + [(5.0, G.BANK_Y + .25, .85), (6.2, G.BANK_Y - .5, .6)])


def footprint(spec):
    """Axis-aligned footprint (x0, y0, x1, y1) of a house; `yaw` is a multiple of 90 degrees."""
    w, d = BAY * spec['bays'][0], BAY * spec['bays'][1]
    if int(round(spec['yaw'])) % 180 != 0:
        w, d = d, w
    cx, cy = spec['center']
    return (cx - w / 2, cy - d / 2, cx + w / 2, cy + d / 2)


def top_z(spec):
    return PLINTH + spec['floors'] * spec['story']


def footprints():
    """Every built footprint on the lower-town ground, as {name: (x0, y0, x1, y1)}."""
    cx, cy = REFUGE['center']
    px, py = RIDGE[0], RIDGE[1]
    cw, cd = CATTLE['size']
    result = {spec['name']: footprint(spec) for spec in HOUSES}
    result['Halwai roof stair'] = (STAIR['x'][0], STAIR['y0'], STAIR['x'][1], STAIR['landing_to'])
    result['Cattle place'] = (CATTLE['center'][0] - cw / 2, CATTLE['center'][1] - cd / 2,
                              CATTLE['center'][0] + cw / 2, CATTLE['center'][1] + cd / 2)
    result['Refuge floor'] = (cx - REFUGE['size'][0] / 2, cy - REFUGE['size'][1] / 2,
                              cx + REFUGE['size'][0] / 2, cy + REFUGE['size'][1] / 2)
    result['Mandi platform'] = (px - MANDI['platform'][0] / 2, py - MANDI['platform'][1] / 2,
                                px + MANDI['platform'][0] / 2, py + MANDI['platform'][1] / 2)
    result['Mandi roof'] = (MANDI['roof_x'][0], py - MANDI['roof_half_y'], MANDI['roof_x'][1], py + MANDI['roof_half_y'])
    return result


def overlaps(a, b):
    """True when two (x0, y0, x1, y1) rectangles share area. Touching edges do not count."""
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
