"""Nandu, keeper of the river gate (फाटक का रखवाला), Chapter 1 supporting lead.

Look is written from the Chapter 1 modeling list and the coordinator's turnaround
prompt; no approved turnaround sheet exists yet. Values marked GUESS are
first-pass choices to revisit once the reference art is approved.
"""

from __future__ import annotations

from math import cos, pi, sin, tau
from typing import Sequence


# (z, center x, center y, radius x, radius y): a small, loosely tied cloth wrap.
HEAD_WRAP_RINGS: tuple[tuple[float, float, float, float, float], ...] = (
    (1.728, 0, .002, .128, .114), (1.743, 0, .001, .131, .116),
    (1.762, 0, .002, .126, .112), (1.779, 0, .004, .114, .102),
    (1.791, 0, .006, .096, .088),
)

# Height .94 gives roughly 170 cm against Gopal's 181 cm (both on the shared adult rig).
SPEC = dict(name='Nandu', height=.94, skin=(.300,.158,.082), hair=(.022,.016,.013),
            iris=(.062,.036,.019), face_width=.99, nose_width=1.04, brow_lift=-.003,
            head_wrap=HEAD_WRAP_RINGS)


Point = tuple[float, float, float]
Weight = str | dict[str, float]


def ellipse(z: float, cx: float, cy: float, rx: float, ry: float, segments: int,
            ripple: float = 0, folds: int = 7, phase: float = 0) -> list[Point]:
    ring: list[Point] = []
    for j in range(segments):
        angle = tau*j/segments
        wave = 1 + ripple*cos(folds*angle + phase)
        ring.append((cx + rx*cos(angle)*wave, cy + ry*sin(angle)*wave, z))
    return ring


def surface_patch(c, name: str, ring: tuple[float, float, float, float, float],
                  angle: float, span: float, height: float, material, bone: Weight,
                  offset: float = .0022) -> None:
    """A curved rectangle of cloth sewn onto an elliptical garment section."""
    z, cx, cy, rx, ry = ring
    columns, rows = 6, 5
    verts: list[Point] = []
    for row in range(rows):
        for column in range(columns):
            a = angle + span*(column/(columns-1) - .5)
            dz = height*(row/(rows-1) - .5)
            verts.append((cx + (rx+offset)*cos(a), cy + (ry+offset)*sin(a), z + dz))
    faces = [(r*columns+k, r*columns+k+1, (r+1)*columns+k+1, (r+1)*columns+k)
             for r in range(rows-1) for k in range(columns-1)]
    c.mesh(name, verts, faces, material, bone)
    border = [verts[k] for k in range(columns)] + [verts[r*columns+columns-1] for r in range(1, rows)]
    border += [verts[(rows-1)*columns+k] for k in range(columns-2, -1, -1)]
    border += [verts[r*columns] for r in range(rows-2, 0, -1)]
    c.tube(f'{name} stitching', border, .0012, c.m['seam'], bone, cyclic=True)


def kurta(c, cloth, patch, dark_patch) -> None:
    # Knee-length, coarse and lean: about 7% narrower than Gopal's vest.
    sections = ((.600,0,.006,.232,.162,.035),(.700,0,.005,.218,.150,.028),
                (.820,0,.004,.204,.138,.018),(.914,0,.003,.186,.118,.012),
                (.980,0,.004,.168,.113,.006),(1.091,0,.008,.156,.108,.004),
                (1.191,0,.005,.182,.114,.004),(1.283,0,.001,.204,.111,.003),
                (1.358,0,.003,.204,.088,.002),(1.411,0,.007,.094,.064,0),
                (1.425,0,.008,.058,.050,0))
    rings = [ellipse(z, x, y, rx, ry, 40, ripple, 7, index*.4)
             for index, (z, x, y, rx, ry, ripple) in enumerate(sections)]
    c.ring_mesh('Coarse kurta', rings, cloth,
                ['hips','hips','hips','hips','hips','spine',{'spine':.45,'chest':.55},
                 'chest','chest','chest','chest'])
    hem = [(x, y, z+.006) for x, y, z in rings[0]]
    c.tube('Kurta hem', hem, .004, c.m['seam'], 'hips', cyclic=True)
    c.tube('Kurta neck placket', [(0,-.050,1.420),(0,-.083,1.385),(0,-.104,1.338),
           (0,-.112,1.282)], .0032, c.m['seam'], 'chest')
    for index, z in enumerate((1.372, 1.322)):
        c.ovoid(f'Kurta wooden toggle {index+1}', (.008,-.100-.006*index,z), (.009,.005,.004),
                c.m['wood'], 'chest', (0,0,.2))

    # Mended patches. GUESS: positions only, chosen to read in the turnaround.
    surface_patch(c, 'Kurta patch | right hip', (.80,0,.004,.205,.140), -1.95, .42, .085, patch, 'hips')
    surface_patch(c, 'Kurta patch | left back', (1.16,0,.006,.176,.113), .95, .5, .07, dark_patch, 'spine')
    surface_patch(c, 'Kurta patch | front hem', (.66,0,.006,.224,.158), -1.3, .32, .06, dark_patch, 'hips')

    for sign, side in ((1,'L'),(-1,'R')):
        upper, lower = f'upper_arm.{side}', f'forearm.{side}'
        # Sleeves follow the arm's own rings and weights, rolled up to mid-forearm.
        form = ((.183,.051),(.239,.061),(.312,.06),(.397,.048),(.46,.042),(.49,.044),(.545,.049))
        sleeve = [[(sign*x, sign*(r*1.20+.006)*cos(tau*i/24),
                    1.375+(r*1.18+.006)*sin(tau*i/24) - .004*max(0,-sin(tau*i/24)))
                   for i in range(24)] for x, r in form]
        c.ring_mesh(f'Kurta sleeve {side}', sleeve, cloth,
                    ['chest',{'chest':.40,upper:.60},upper,upper,{upper:.72,lower:.28},
                     {upper:.26,lower:.74},lower], cap=False)
        # Shoulder yoke: half chest, half upper arm, so the shoulder never shows through
        # where the arm skin rotates out of the sleeve's first ring.
        yoke = c.ovoid(f'Kurta shoulder yoke {side}', (sign*.200,.002,1.388), (.072,.080,.060), cloth, 'chest')
        group = yoke.vertex_groups['chest']
        indices = list(range(len(yoke.data.vertices)))
        group.add(indices, .55, 'REPLACE')
        yoke.vertex_groups.new(name=upper).add(indices, .45, 'REPLACE')
        for x, r, extra in ((.528,.047,.010),(.547,.049,.012)):
            radius = r*1.20 + .006 + extra*.5
            c.tube(f'Rolled sleeve fold {side} {x}',
                   [(sign*x, radius*cos(tau*i/24), 1.375+radius*sin(tau*i/24)) for i in range(24)],
                   extra, cloth, lower, cyclic=True)


def dhoti(c, cloth, mud) -> None:
    for sign, side in ((1,'L'),(-1,'R')):
        thigh, shin = f'thigh.{side}', f'shin.{side}'
        # Tucked up under the kurta: the top ring stays inside the kurta hem.
        shapes = ((.415,.135,.072,.074),(.460,.135,.078,.079),(.530,.134,.084,.086),
                  (.600,.128,.080,.090),(.680,.120,.072,.090))
        rings = [ellipse(z, sign*x, 0, rx, ry, 36, .07, 6, index*.5*sign)
                 for index, (z, x, rx, ry) in enumerate(shapes)]
        c.ring_mesh(f'Tucked ochre dhoti {side}', rings, cloth,
                    [shin,shin,{shin:.5,thigh:.5},thigh,thigh], cap=False)
        c.tube(f'Dhoti hem fold {side}', rings[0], .0045, cloth, shin, cyclic=True)
        for i in range(9):
            angle = -pi/2 + sign*(i-4)*.33
            z = .43 + .012*sin(i*2.1)
            c.ovoid(f'Dhoti hem mud {side} {i+1}',
                    (sign*.135+.077*cos(angle), .080*sin(angle), z),
                    (.009+.002*(i%3), .0018, .011+.003*(i%2)), mud, shin, (0,0,angle+pi/2))
        for i in range(10):
            angle = -pi/2 + 2.4*i
            c.ovoid(f'Shin river mud {side} {i+1}',
                    (sign*.135+.046*cos(angle), .046*sin(angle), .12+.022*i),
                    (.007, .0012, .010), mud, shin, (0,0,angle+pi/2))


def rope_belt(c, rope) -> None:
    rx, ry, cy, z0 = .174, .119, .004, .975
    count = 120
    for ply in range(2):
        points: list[Point] = []
        for j in range(count):
            a = tau*j/count
            twist = a*38 + ply*pi
            nx, ny = cos(a), sin(a)
            points.append((rx*nx + .0036*cos(twist)*nx, cy + ry*ny + .0036*cos(twist)*ny,
                           z0 + .0036*sin(twist)))
        c.tube(f'Rope belt ply {ply+1}', points, .0041, rope, 'hips', cyclic=True)
    knot_angle = -pi/2 + .42
    kx, ky = rx*cos(knot_angle), cy + ry*sin(knot_angle)
    c.ovoid('Rope belt knot', (kx, ky-.006, z0), (.017,.012,.014), rope, 'hips', (0,.3,.2))
    for index, (dx, length) in enumerate(((-.006,.15),(.008,.12))):
        c.tube(f'Rope belt end {index+1}', [(kx+dx, ky-.010, z0-.005),
               (kx+dx*1.6, ky-.020, z0-length*.5), (kx+dx*2.2+.004, ky-.016, z0-length)],
               [.0055,.005,.0045], rope, 'hips')


def head_wrap(c, wrap, seam) -> None:
    c.loft('Faded head wrap', HEAD_WRAP_RINGS, wrap, 'head', segments=48, cap=False)
    # Loose folds where the cloth has slipped; tilted so the wrap sits a little unevenly.
    for index, (z, tilt, radius) in enumerate(((1.736,.008,.0055),(1.766,-.007,.006),(1.784,.005,.0045))):
        rx, ry = (.131, .117) if index < 2 else (.112, .101)
        c.tube(f'Head wrap loose fold {index+1}',
               [(rx*cos(tau*j/48), .002+ry*sin(tau*j/48), z+tilt*cos(tau*j/48))
                for j in range(48)], radius, wrap, 'head', cyclic=True)
    c.tube('Head wrap frayed edge', [(.096*cos(tau*j/48), .006+.088*sin(tau*j/48), 1.791)
           for j in range(48)], .0022, seam, 'head', cyclic=True)
    c.ovoid('Head wrap rear knot', (-.070,.106,1.752), (.030,.024,.020), wrap, 'head', (0,-.25,-.2))
    c.tube('Head wrap tail', [(-.074,.120,1.746),(-.080,.138,1.712),(-.072,.144,1.678)],
           [.012,.010,.007], wrap, 'head')


def dress(c) -> None:
    c.m['seam'] = c.mat('Coarse seam thread', (.30,.25,.17), .9)
    c.m['wood'] = c.mat('Worn wooden toggle', (.12,.07,.035), .7)
    cloth = c.mat('Unbleached handloom kurta', (.50,.44,.33), .93)
    patch = c.mat('Kurta patch cloth', (.41,.36,.27), .94)
    dark_patch = c.mat('Kurta dark patch cloth', (.25,.20,.14), .94)
    lower = c.mat('Faded ochre dhoti', (.40,.25,.075), .92)
    wrap = c.mat('Faded head wrap', (.27,.19,.12), .92)
    rope = c.mat('Twisted belt rope', (.23,.17,.10), .95)
    mud = c.mat('River mud', (.19,.13,.08), .96)
    kurta(c, cloth, patch, dark_patch)
    dhoti(c, lower, mud)
    rope_belt(c, rope)
    head_wrap(c, wrap, c.m['seam'])
