"""Seating terrace (families and sailors), list board and trees for SET_Sharan."""

import math
import random

import ghat_kit as k
import sharan_detail as D
import town_props
import sharan_layout as L
from smashan_world import collection, tube


def _mat(name, x, y, z, yaw, m):
    return D.mat(name, x, y, z, yaw, m, int(abs(x * 7 + y * 3)))


def seating(m):
    collection('Sharan | Seating')
    rng = random.Random(21)
    for s in L.seats():
        n = s['n']
        gopal = n == L.GOPAL_SEAT
        _mat(f'Mat | seat {n:02d}', s['x'], s['y'], s['z'], s['yaw'], m)
        k.empty(f'SEAT {n:02d} | {L.seat_label(n)}', (s['x'], s['y'], s['z'] + .04),
                'SPHERE' if gopal else 'PLAIN_AXES', .22 if gopal else .15)
        a = math.radians(s['angle'])
        if n % 2 == 0:  # a water pot beside the mat, on the side away from the board
            px, py = s['x'] + math.cos(a) * .75, s['y'] + math.sin(a) * .75
            pot_mats = dict(clay_pot=m['clay'], clay_dark=m['wood'])
            town_props.pot(f'Prop | water pot {n:02d}', (px, py, L.ground_z(px, py)), .7, pot_mats)
        elif n > 6:  # a bundle of belongings
            a2 = math.radians(s['angle'] + 12)
            px, py = s['x'] + math.cos(a2) * .7, s['y'] + math.sin(a2) * .7
            D.bundle(f'Prop | cloth bundle {n:02d}', (px, py, L.ground_z(px, py)), m, n)
    ms = L.mausi()
    _mat('Mat | Mausi beside Gopal', ms['x'], ms['y'], ms['z'], ms['yaw'], m)
    k.empty('MARK | Mausi sits beside Gopal', (ms['x'], ms['y'], ms['z'] + .04), 'PLAIN_AXES', .3)
    for i, o in enumerate(L.overflow_mats(), start=1):
        _mat(f'Mat | family {i} (east of the path)', o['x'], o['y'], o['z'], o['yaw'], m)
        D.bundle(f'Prop | family {i} bundle', (o['x'] + .7, o['y'], L.ground_z(o['x'] + .7, o['y'])), m, 50 + i)
    cx, cy = L.SEAT_CENTRE
    bz = L.ground_z(cx, cy)
    bw, bd, bh = L.BOARD_SIZE
    k.box('Board | sailors list writing plank', (cx, cy, bz + bh / 2), (bw, bd, bh), m['wood'], bevel=.015)
    for i in range(4):
        k.box(f'Board | list paper {i + 1}', (cx + rng.uniform(-.1, .1), cy - .4 + i * .27, bz + bh + .004),
              (.25, .2, .006), m['paper'], yaw=rng.uniform(-.3, .3))
    marks = L.board_marks()
    for key, label in (('betal', 'Betal writes the list'), ('sailor_a', 'Sailor A writes the list'),
                       ('sailor_b', 'Sailor B writes the list')):
        x, y, z = marks[key]
        _mat(f'Mat | {key}', x, y, z, L.facing_yaw(x, y, cx, cy), m)
        k.empty(f'MARK | {label}', (x, y, z + .04), 'PLAIN_AXES', .3)
    k.empty('MARK | Nandu stands and tells everyone', L.nandu_mark(), 'PLAIN_AXES', .4)


def trees(m):
    collection('Sharan | Trees and scatter')
    rng = random.Random(9)
    for i, (x, y) in enumerate(L.TREES, start=1):
        z = L.ground_z(x, y)
        D.tree(i, x, y, z - .05, m, 100 + i)
    seat_points = [(s['x'], s['y']) for s in L.seats()] + [(o['x'], o['y']) for o in L.overflow_mats()]

    def free(x, y):
        if abs(x - L.path_x(y)) < 2.0 and L.PATH_Y[0] - 1 < y < L.PATH_Y[1] + 1:
            return False
        if (x - L.SEAT_CENTRE[0]) ** 2 + (y - L.SEAT_CENTRE[1]) ** 2 < 7.5 ** 2:
            return False
        if any(math.hypot(x - sx, y - sy) < 2.0 for sx, sy in seat_points):
            return False
        if L.veranda_front_y() - 3 < y < L.HUT['cy'] + 4 and abs(x - L.HUT['cx']) < 6.5:
            return False
        if L.WALL_Y - 1 < y < L.WALL_Y + 1:
            return False
        return not any(math.hypot(x - tx, y - ty) < 2.0 for tx, ty in L.TREES)

    placed = 0
    while placed < 20:
        x, y = rng.uniform(-20, 20), rng.uniform(-6, 50)
        if free(x, y):
            placed += 1
            D.rock(f'Rock {placed:02d}', (x, y, L.ground_z(x, y) + .02),
                   (.2 + rng.random() * .25, .18 + rng.random() * .2, .13 + rng.random() * .12), m, placed)
    placed = 0
    while placed < 80:
        x, y = rng.uniform(-21, 21), rng.uniform(-6, 50)
        if free(x, y):
            placed += 1
            D.grass(f'Grass tuft {placed:02d}', (x, y, L.ground_z(x, y)), m, placed)
