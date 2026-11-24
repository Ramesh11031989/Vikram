"""अनाम रिग पर लाल कपड़ा: the unidentified figure beside the chowki lamp.

SH03 of E01_SC04 shows only a turned back and a patch of red cloth. Gopal never
saw a face, so this model has none: no eyes, brows, nostrils, mouth or ears are
built, and the head is a blank form under a hair cap. It is not Nandu and carries
no Nandu likeness; the red cloth is the only clue the story allows. It shares the
standard Character rig so shots can reuse clips.
"""

from math import cos, sin, sqrt, tau

from mathutils import Vector

from textile import finish_fabric, store_rest_positions


SPEC = dict(name='AnonymousRedCloth', height=.94, skin=(.20,.115,.065),
            hair=(.022,.016,.012), iris=(.05,.03,.015))

RED = (.36,.032,.018)
COLUMNS = 25
HANG_STEPS = 5


def tunic_depth(x):
    """Rear surface of the plain tunic behind the spine at lateral offset x."""
    return .125*sqrt(max(.04, 1-(x/.225)**2))


def drape_grid():
    """Cloth points grid[i][j] -> (x, y, z), from chest over shoulder to the hem.

    The left side hangs a little longer than the right, so the cloth reads as
    worn over the shoulders and pulled to one side.
    """
    grid = []
    for i in range(COLUMNS):
        x = -.21 + .42*i/(COLUMNS-1)
        top = 1.395 + .035*max(0, min(1, (.2-abs(x))/.14))
        back = tunic_depth(x) + .012
        front = -(back*.9)
        column = [(x, front, top-.13), (x, front*.5, top-.04), (x, 0, top+.012),
                  (x, back*.55, top+.002), (x, back, top-.05)]
        hem = 1.13 - .20*(x+.21)/.42 + .012*sin(x*37)
        start = top - .05
        for k in range(1, HANG_STEPS+1):
            t = k/HANG_STEPS
            fold = .011*sin(x*41+.6) + .006*sin(x*83+1.9)
            column.append((x, back + .016*t**1.5 + fold*(.35+.65*t),
                           start + (hem-start)*t))
        grid.append(column)
    return grid


def thick_sheet(grid, thickness):
    """Vertices and faces of a closed two-layer cloth sheet.

    The outer layer faces away from the wearer; the inner layer sits
    `thickness` closer to the body and the four borders close the sheet.
    """
    columns, rows = len(grid), len(grid[0])
    outer = [Vector(point) for column in grid for point in column]
    at = lambda i, j: i*rows + j
    inner = []
    for i in range(columns):
        for j in range(rows):
            along = outer[at(min(i+1,columns-1),j)] - outer[at(max(i-1,0),j)]
            down = outer[at(i,min(j+1,rows-1))] - outer[at(i,max(j-1,0))]
            normal = along.cross(down).normalized()
            if normal.y < 0:
                normal.negate()
            inner.append(outer[at(i,j)] - normal*thickness)
    shift = len(outer)
    faces = []
    for i in range(columns-1):
        for j in range(rows-1):
            a, b, c, d = at(i,j), at(i+1,j), at(i+1,j+1), at(i,j+1)
            faces.append((a, b, c, d))
            faces.append((d+shift, c+shift, b+shift, a+shift))
    for j in range(rows-1):
        faces.append((at(0,j+1), at(0,j), at(0,j)+shift, at(0,j+1)+shift))
        end = columns-1
        faces.append((at(end,j), at(end,j+1), at(end,j+1)+shift, at(end,j)+shift))
    for i in range(columns-1):
        faces.append((at(i,0), at(i+1,0), at(i+1,0)+shift, at(i,0)+shift))
        last = rows-1
        faces.append((at(i+1,last), at(i,last), at(i,last)+shift, at(i+1,last)+shift))
    return [tuple(point) for point in outer+inner], faces


def drape_weights(rows):
    """Chest carries the shoulder; the hang follows the spine progressively."""
    result = []
    for _ in range(COLUMNS):
        for j in range(rows):
            spine = min(.75, max(0, j-4)/HANG_STEPS*.75)
            result.append('chest' if spine <= 0 else {'chest':1-spine, 'spine':spine})
    return result


def dress(c):
    """Plain dark tunic and trousers, a blank head, and the red cloth."""
    dark = c.mat('Plain dark tunic', (.026,.030,.034), .91)
    cloth = c.mat('Observed red cloth', RED, .9)
    hem_dye = c.mat('Red cloth deep hem', (.17,.014,.010), .9)
    c.loft('Plain tunic', [(.85,0,0,.20,.13),(1.15,0,0,.20,.12),
           (1.38,0,0,.22,.12),(1.45,0,0,.07,.06)], dark, ['hips','spine','chest','chest'])
    for side, sign in (('L',1),('R',-1)):
        upper, lower = f'upper_arm.{side}', f'forearm.{side}'
        rings = [[(sign*x, r*cos(tau*j/24), 1.375+r*sin(tau*j/24)) for j in range(24)]
                 for x,r in ((.21,.056),(.25,.066),(.40,.055),(.50,.047),(.66,.034))]
        c.ring_mesh(f'Plain sleeve {side}', rings, dark,
                    ['chest', upper, upper, {upper:.3,lower:.7}, lower])
        c.loft(f'Plain trouser {side}', [(.14,sign*.135,0,.055,.05),(.5,sign*.135,0,.075,.07),
               (.75,sign*.125,0,.10,.10),(.92,sign*.1,0,.115,.12)], dark,
               [f'shin.{side}',{f'shin.{side}':.5,f'thigh.{side}':.5},f'thigh.{side}','hips'])
    # Blank head: skin-toned form and hair cap only. No facial geometry exists.
    c.ovoid('Featureless head', (0,-.005,1.655), (.108,.105,.155), c.m['skin'], 'head')
    c.ovoid('Hair cap and nape', (0,.014,1.700), (.119,.109,.122), c.m['hair'], 'head')

    grid = drape_grid()
    vertices, faces = thick_sheet(grid, .0045)
    rows = len(grid[0])
    sheet = c.mesh('Red cloth over shoulders', vertices, faces, cloth, drape_weights(rows)*2)
    finish_fabric(cloth, fine=False)
    store_rest_positions(sheet.data)
    hem = [(column[-1][0], column[-1][1]+.004, column[-1][2]) for column in grid]
    c.tube('Red cloth hem band', hem, .0052, hem_dye, 'spine')


def chowki_props(scene, wood, clay, flame):
    """A low wooden chowki with a clay lamp, in world metres, in its own collection."""
    import bpy
    collection = bpy.data.collections.new('Chowki and lamp')
    scene.collection.children.link(collection)

    def place(obj, surface):
        for owner in list(obj.users_collection):
            owner.objects.unlink(obj)
        collection.objects.link(obj)
        obj.data.materials.append(surface)
        return obj

    def box(name, location, size, surface, bevel=.012):
        bpy.ops.mesh.primitive_cube_add(size=1, location=location)
        obj = bpy.context.object
        obj.scale = size
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        obj.name = name
        modifier = obj.modifiers.new('Soft construction edges', 'BEVEL')
        modifier.width, modifier.segments = bevel, 2
        return place(obj, surface)

    def oval(name, location, size, surface):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=location)
        obj = bpy.context.object
        obj.scale = size
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
        obj.name = name
        return place(obj, surface)

    x, y, top = .62, .06, .80
    box('Chowki top slab', (x,y,top-.03), (.56,.44,.06), wood)
    for dx in (-.23,.23):
        for dy in (-.17,.17):
            box('Chowki turned leg', (x+dx,y+dy,(top-.06)/2), (.06,.06,top-.06), wood, .01)
    box('Chowki front rail', (x,y-.17,.52), (.40,.025,.05), wood, .006)
    box('Chowki side rail', (x-.23,y,.52), (.025,.30,.05), wood, .006)
    oval('Clay lamp bowl', (x-.06,y-.04,top+.022), (.062,.055,.026), clay)
    oval('Lamp flame', (x-.06,y-.04,top+.075), (.011,.011,.032), flame)
    data = bpy.data.lights.new('Chowki lamp light', 'POINT')
    data.energy, data.color, data.shadow_soft_size = 7, (1,.40,.10), .015
    lamp = bpy.data.objects.new('Chowki lamp light', data)
    collection.objects.link(lamp)
    lamp.location = (x-.06, y-.04, top+.09)
    return collection
