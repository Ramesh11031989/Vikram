"""Group 1: विक्रम की यात्रा — horse, bridle, tether, riding gear, statement satchel."""

import bpy

import props_horse as H
import story_kit as K

NAME = 'Vikram_Journey'


def build(scene, root):
    m = H.materials()
    body, legs = H.horse(root, m)
    H.hair(root, m)
    H.bridle(root, m)
    H.tether(root, m)
    H.riding_gear(root, m)
    bag = H.satchel(root, m, location=(1.4, -.4, 0))
    # tether post and rail, as used on the Smashan set (rail height 1.1 m)
    post = K.MeshBuilder()
    wood = K.mat('Post • Seasoned wood', (.22, .14, .08), .85, bump=.5, scale=60, variation=.4)
    post.box((.13, .13, 1.45), (-.72, -1.55, .725), wood)
    post.box((.10, .10, .09), (-.72, -1.55, 1.12), wood)
    post.build('Tether post', root)
    for o in root.all_objects:
        o.select_set(False)
    K.stage(scene, 1600, 1000, 48, .8)
    K.ground(scene, 14, (.20, .17, .12))
    K.lamp(scene, 'Key', (-3.5, -4.5, 4.5), (0, -.3, 1.0), 900, (1, .9, .78), 3)
    K.lamp(scene, 'Fill', (4.5, 2.5, 2.5), (0, 0, 1.0), 260, (.7, .8, 1), 4)
    side = K.camera(scene, 'Side', (4.2, -.2, 1.5), (0, -.2, .95), 45)
    head = K.camera(scene, 'Head', (-1.9, -2.7, 1.55), (0, -1.15, 1.35), 70)
    bagcam = K.camera(scene, 'Satchel', (1.4, -1.5, .5), (1.4, -.4, .22), 60)
    return [('Side', side), ('Head_and_tack', head), ('Satchel', bagcam)]
