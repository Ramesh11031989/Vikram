"""Materials and the modular house kit for set 3 (निचली बस्ती और अनाज मंडी).

Every house is built from 3 m wall bays (solid, door, window), a plinth, floor slabs and one roof
type (flat with parapet, thatch or tile). Parts are parented to one root empty at the house centre,
so a house can be moved or turned as one object.
"""

import math

import bpy

import ghat_kit as k
import town_layout as T
import town_art
import town_walls as W
from town_hard import Hard
from town_roofs import thatch_hip, tile_gable


def materials():
    tx, mt = k.textured, k.material
    return town_art.upgrade(dict(
        lime=tx('Town | lime-washed plaster', (.62, .58, .50), .92, 4, .25, .25),
        ochre=tx('Town | ochre plaster', (.55, .38, .18), .92, 4, .3, .3),
        mud=tx('Town | mud wall', (.30, .20, .12), .98, 3, .35, .45),
        thatch=tx('Town | thatch', (.36, .27, .12), .98, 40, .5, .7),
        tile=tx('Town | clay tile', (.42, .17, .09), .85, 18, .35, .4),
        wood=tx('Town | seasoned wood', (.16, .09, .045), .8, 14, .4, .2),
        stone=tx('Town | plinth stone', (.30, .28, .25), .85, 3, .4, .35),
        earth=tx('Town | trodden earth', (.22, .165, .105), .98, 2.5, .35, .4),
        lane=tx('Town | lane earth', (.31, .245, .165), .98, 6, .3, .3),
        refuge=tx('Town | refuge flagstone', (.46, .42, .35), .9, 5, .2, .2),
        joint=mt('Town | flagstone joint', (.19, .17, .14), .95),
        grain=mt('Town | wheat', (.60, .43, .14), .9),
        sack=tx('Town | grain sack', (.52, .42, .26), .98, 30, .3, .3),
        hay=tx('Town | hay', (.52, .42, .16), .98, 50, .4, .5),
        cow_a=mt('Town | cow, white', (.72, .67, .58), .85),
        cow_b=mt('Town | cow, brown', (.33, .17, .075), .85),
        horn=mt('Town | horn', (.62, .58, .48), .5),
        rope=mt('Town | rope', (.42, .31, .15), .95),
        leaf=mt('Town | neem leaf', (.06, .15, .045), .95),
        bark=tx('Town | bark', (.12, .08, .05), .95, 8, .4, .5),
        clay=mt('Town | clay pot', (.40, .16, .07), .9),
        brass=mt('Town | brass tray', (.55, .38, .10), .35, 1),
        soot=mt('Town | soot', (.03, .028, .026), .98),
        cloth=mt('Town | awning cloth', (.55, .12, .06), .95),
        damp=tx('Town | damp plaster band', (.24, .20, .15), .98, 9, .5, .5),
        patch=tx('Town | lime-wash patch', (.70, .66, .58), .95, 12, .3, .3),
        wood_dark=tx('Town | dark batten', (.08, .045, .025), .8, 14, .4, .2),
        tile_ridge=mt('Town | ridge tile', (.34, .13, .07), .8),
        iron=mt('Town | wrought iron', (.07, .066, .062), .5, 1),
        dark=mt('Town | dark interior', (.01, .008, .007), 1.),
        cow_dark=mt('Town | cow, dark points', (.06, .045, .04), .85),
        cow_hoof=mt('Town | cow, hoof', (.07, .06, .052), .5),
        cow_muzzle=mt('Town | cow, muzzle', (.30, .20, .18), .55),
        cow_eye=mt('Town | cow, eye', (.02, .012, .008), .1),
        leaf_light=mt('Town | neem leaf, young', (.12, .24, .07), .95),
        clay_pot=tx('Town | matka clay', (.46, .20, .09), .86, 22, .3, .3),
        clay_dark=mt('Town | pot slip band', (.20, .08, .04), .9),
        clay_glaze=tx('Town | glazed jar', (.20, .11, .05), .38, 14, .35, .2),
        sack_dark=mt('Town | sack crease', (.30, .24, .14), .98),
        grain_dark=mt('Town | wheat, shadow', (.40, .27, .08), .9),
        oil=mt('Town | frying oil', (.33, .20, .03), .12),
        jalebi=mt('Town | jalebi', (.75, .32, .03), .3)))


def collection_named(name):
    found = bpy.data.collections.get(name)
    return found if found else k.collection(name)


def add(root, obj):
    obj.parent = root
    return obj


def bay_pieces(kind, height):
    """Wall rectangles (along0, along1, z0, z1) for one 3 m bay, along-axis centred on the bay."""
    h = T.BAY / 2
    if kind == 'door':
        w = T.DOOR_W / 2
        return [(-h, -w, 0, height), (w, h, 0, height), (-w, w, T.DOOR_H, height)]
    if kind == 'window':
        w, s = T.WINDOW_W / 2, T.WINDOW_SILL
        return [(-h, -w, 0, height), (w, h, 0, height), (-w, w, 0, s), (-w, w, s + T.WINDOW_H, height)]
    return [(-h, h, 0, height)]


def wall_bay(root, axis, along, fixed, kind, z0, height, m, plaster, side=-1):
    return W.wall_bay(root, axis, along, fixed, kind, z0, height, m, plaster, side)


def front_kinds(bays, floor):
    if floor > 0:
        return ['window'] * bays
    return ['window'] * (bays // 2) + ['door'] + ['window'] * (bays - bays // 2 - 1)


def hip_roof(root, w, d, z, rise, overhang, surface, ridge_len, name, m=None):
    """Tiered straw thatch hip roof with ridge roll and bamboo battens (ridge along local x)."""
    b = Hard()
    thatch_hip(b, w, d, z, rise, overhang, ridge_len, (surface, m['wood']), seed=int(abs(w * 7 + d)))
    return add(root, b.build(name, k._current))


def gable_roof(root, w, d, z, rise, overhang, surface, name, m=None, plaster=None):
    """Corrugated clay-tile gable with ridge cap tiles, fascia boards and plastered gable ends."""
    b = Hard()
    tile_gable(b, w, d, z, rise, overhang, surface, m['tile_ridge'], m['wood'], plaster)
    return add(root, b.build(name, k._current))


def parapet(root, w, d, z, m, plaster, gap=None):
    """Low wall round a flat roof. `gap` = (side, lo, hi) leaves an opening on the 'E' side, lo..hi along local y."""
    t, h = .22, T.PARAPET
    zc = z + h / 2
    k_box = lambda n, c, s: add(root, k.box(n, c, s, plaster, .01))
    k_box('Parapet south', (0, -d / 2 + t / 2, zc), (w, t, h))
    k_box('Parapet north', (0, d / 2 - t / 2, zc), (w, t, h))
    k_box('Parapet west', (-w / 2 + t / 2, 0, zc), (t, d - 2 * t, h))
    if gap is None:
        k_box('Parapet east', (w / 2 - t / 2, 0, zc), (t, d - 2 * t, h))
    else:
        _, lo, hi = gap
        lo, hi = max(lo, -d / 2 + t), min(hi, d / 2 - t)
        if lo - (-d / 2 + t) > .05:
            k_box('Parapet east, south part', (w / 2 - t / 2, (lo - d / 2 + t) / 2, zc), (t, lo + d / 2 - t, h))
        if (d / 2 - t) - hi > .05:
            k_box('Parapet east, north part', (w / 2 - t / 2, (hi + d / 2 - t) / 2, zc), (t, d / 2 - t - hi, h))
    k_box('Parapet coping', (0, 0, z + h + .03), (w + .04, d + .04, .06)).hide_viewport = False


def house(spec, m, gap=None):
    """Build one modular house. Returns its root empty (at the house centre, turned by `yaw`)."""
    k.use(collection_named(spec['collection']))
    bx, by, floors, story = spec['bays'][0], spec['bays'][1], spec['floors'], spec['story']
    w, d = T.BAY * bx, T.BAY * by
    plaster = m[spec['wall']]
    root = k.empty(f"{spec['name']} | root", (*spec['center'], 0), 'ARROWS', 1.0)
    root.rotation_euler.z = math.radians(spec['yaw'])
    W.plinth(root, w, d, m, seed=int(abs(w * 13 + d * 3 + spec['center'][0])))
    add(root, k.box('Plinth core', (0, 0, T.PLINTH / 2), (w + .2, d + .2, T.PLINTH), m['stone']))
    add(root, k.box('Ground floor slab', (0, 0, T.PLINTH + .04), (w, d, .08), m['earth']))
    for floor in range(floors):
        z0 = T.PLINTH + floor * story
        for i in range(bx):
            x = -w / 2 + T.BAY * (i + .5)
            wall_bay(root, 'x', x, -d / 2, front_kinds(bx, floor)[i], z0, story, m, plaster)
            wall_bay(root, 'x', x, d / 2, 'solid', z0, story, m, plaster, 1)
        for j in range(by):
            y = -d / 2 + T.BAY * (j + .5)
            side = 'window' if (floor > 0 and j == 0) else 'solid'
            wall_bay(root, 'y', y, -w / 2, side, z0, story, m, plaster, -1)
            wall_bay(root, 'y', y, w / 2, side, z0, story, m, plaster, 1)
        if floor > 0:
            add(root, k.box('Upper floor slab', (0, 0, z0 - .08), (w, d, .16), m['wood']))
            add(root, k.box('Balcony ledge', (0, -d / 2 - .22, z0 + .05), (w * .8, .45, .1), m['wood'], .01))
    top = T.PLINTH + floors * story
    roof = spec['roof']
    add(root, k.box('Roof slab' if roof == 'flat' else 'Ceiling slab', (0, 0, top - .08), (w + .1, d + .1, .16), m['wood'] if roof != 'flat' else m['stone'], .01))
    if roof == 'flat':
        parapet(root, w, d, top, m, plaster, gap)
    elif roof == 'thatch':
        hip_roof(root, w, d, top, 1.7, .6, m['thatch'], max(.4, w - 2.2), 'Thatch hip roof', m)
    else:
        gable_roof(root, w, d, top, 1.5, .5, m['tile'], 'Tile gable roof', m, plaster)
    return root


def modular_kit_row(m):
    """Three loose wall modules (solid, door, window) at the kit anchor, so a bay can be copied by hand."""
    k.use(collection_named(T.MODULE_COLLECTION))
    x0, y0 = T.KIT_ROW['origin']
    root = k.empty('Kit row | wall modules (copy these)', (x0, y0, 0), 'PLAIN_AXES', .5)
    for i, kind in enumerate(T.KIT_ROW['kinds']):
        wall_bay(root, 'x', i * (T.BAY + 1.0), 0, kind, 0, 3.0, m, m['lime'])
    return root
