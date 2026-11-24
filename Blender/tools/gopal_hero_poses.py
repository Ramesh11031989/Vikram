"""Gopal’s Chapter 1 blocking poses and reusable boat and chalk props."""

import math
from pathlib import Path
from random import Random

import bpy
from mathutils import Matrix, Vector

from betal_hero_poses import action, aim_local, hand, material, mesh, panel, place_hip, prop, reach, tube, world_bone
from build_cast import light, setup_stage, stage_camera, turn
from build_vikram_hero import copy_model


def stage(label, filename, dimensions, camera, target, width, river=False):
    scene = bpy.data.scenes.new(f'Gopal | {label}')
    setup_stage(scene, *dimensions, 24, .19 if river else .24)
    stage_camera(scene, f'{label} review camera', camera, target, width)
    if river:
        light(scene, 'Warm light from the riverbank', (-3.1,-4.7,4.1), target, (1,.79,.60), 490, 2.6)
        light(scene, 'River bounce', (2.2,-2.0,2.8), target, (.44,.69,1), 163, 2.9)
        light(scene, 'Cool sky off the water', (1.0,2.4,3.1), target, (.52,.75,1), 405, 2.8)
    else:
        light(scene, 'Sunlight across the court', (-3.2,-3.7,4.7), target, (1,.82,.62), 535, 2.5)
        light(scene, 'Light from adjoining courtyard', (3.5,-2.1,3.5), target, (.72,.82,1), 166, 2.8)
        light(scene, 'Soft sandstone bounce', (2.6,2.7,3.5), target, (1,.71,.47), 220, 2.1)
    scene.render.filepath = f'//{filename}'
    return scene


def reusable(collection, description):
    collection.asset_mark()
    collection.asset_data.description = description


def beveled_box(collection, name, center, size, surface, radius=.012, parent=None):
    x, y, z = center
    w, d, h = (value/2 for value in size)
    vertices = [(x+a*w,y+b*d,z+c*h) for c in (-1,1) for a,b in ((-1,-1),(1,-1),(1,1),(-1,1))]
    faces = [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    box = mesh(collection, name, vertices, faces, surface, parent, smooth=False)
    bevel = box.modifiers.new('Eased edges', 'BEVEL')
    bevel.width, bevel.segments = radius, 3
    return box


def grain_mat(name, color, roughness):
    surface = material(name, color, roughness)
    nodes, links = surface.node_tree.nodes, surface.node_tree.links
    if nodes.get('Teak grain') is not None:
        return surface
    coords = nodes.new('ShaderNodeTexCoord')
    stretch = nodes.new('ShaderNodeVectorMath')
    stretch.operation = 'MULTIPLY'
    stretch.inputs[1].default_value = (87,4.2,74)
    noise = nodes.new('ShaderNodeTexNoise')
    noise.name = 'Teak grain'
    noise.inputs['Scale'].default_value = 1.0
    noise.inputs['Detail'].default_value = 3.1
    links.new(coords.outputs['Object'], stretch.inputs[0])
    links.new(stretch.outputs['Vector'], noise.inputs['Vector'])
    ramp = nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = .20
    ramp.color_ramp.elements[0].color = (*(value*.44 for value in color),1)
    ramp.color_ramp.elements[1].position = .79
    ramp.color_ramp.elements[1].color = (*(value*1.23 for value in color),1)
    links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
    bsdf = nodes.get('Principled BSDF')
    links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .24
    bump.inputs['Distance'].default_value = .0018
    links.new(noise.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    return surface


def river_skiff(scene):
    group, anchor = prop(scene, 'Gopal | River skiff', (0,0,0))
    planks = [grain_mat(f'Skiff | {name} teak', color, .68) for name,color in (
        ('Keel',(.106,.060,.031)), ('Lower',(.155,.084,.044)), ('Strake',(.122,.067,.038)),
        ('Upper',(.170,.097,.051)), ('Sheer',(.143,.074,.036)))]
    edge = grain_mat('Skiff | Oiled gunwale and ribs', (.138,.077,.038), .53)
    deck = grain_mat('Skiff | Worn foot boards and seat', (.203,.122,.063), .68)
    peg = material('Skiff | Dark hand-cut pegs', (.057,.035,.020), .88, 99)

    def hull_point(u, height, sign):
        y = -1.56+3.10*u
        fullness = math.sin(math.pi*u)**.68
        beam = .020+.567*fullness*(1+.071*math.sin(2*math.pi*u))
        end_rise = .178*abs(2*u-1)**5
        sheer = .408+.166*abs(2*u-1)**3.5
        flare = .55+.45*math.sin(height*math.pi*.49)
        return (sign*beam*flare, y, .045+end_rise+height*(sheer-end_rise))

    stations = [index/40 for index in range(41)]
    panel(group, 'Skiff | Broad river-keel bottom',
          [[hull_point(u,0,sign) for u in stations] for sign in (-1,1)], planks[0], anchor, .018)
    for sign in (-1,1):
        for index, surface in enumerate(planks):
            bottom, top = index/len(planks), (index+1)/len(planks)-.007
            levels = (bottom,(2*bottom+top)/3,(bottom+2*top)/3,top)
            ordered_levels = levels if sign>0 else tuple(reversed(levels))
            rows = [[hull_point(u,h,sign) for u in stations] for h in ordered_levels]
            panel(group, f'Skiff | {"Starboard" if sign>0 else "Port"} plank {index+1}', rows, surface, anchor, .016)
        tube(group, 'Skiff | Rounded sheer rail', [(hull_point(u,1,sign),.019) for u in stations], edge, anchor, 12)

    for end in (0,1):
        tube(group, 'Skiff | Curved stem', [(hull_point(end,n/12,0),.013+.003*n/12) for n in range(13)], edge, anchor, 10)
    for u in (.19,.31,.43,.61,.72,.83):
        cross = [hull_point(u,n/9,-1) for n in range(9,0,-1)]
        cross.extend([hull_point(u,n/9,1) for n in range(10)])
        tube(group, 'Skiff | Curved internal frame', [((x*.953,y,z+.011),.0125) for x,y,z in cross], edge, anchor, 10)
    for index in range(7):
        x = (index-3)*.094
        beveled_box(group, 'Skiff | Foot board', (x,-.065,.129), (.089,1.92-.230*abs(index-3),.033), deck, .008, anchor)
    beveled_box(group, 'Skiff | Rowing thwart', (0,.164,.467), (1.067,.275,.048), deck, .017, anchor)
    beveled_box(group, 'Skiff | Forward thwart', (0,-.850,.407), (.892,.180,.040), edge, .014, anchor)
    beveled_box(group, 'Skiff | Aft thwart', (0,.983,.435), (.834,.151,.040), edge, .014, anchor)
    for y, z, width in ((.164,.493,.472),(-.850,.429,.379),(.983,.457,.352)):
        for sign in (-1,1):
            for offset in (-.048,.045):
                tube(group, 'Skiff | Hardwood seat peg', [((sign*width,y+offset,z-.002),.0061),
                     ((sign*width,y+offset,z+.002),.0055)], peg, anchor, 8)

    reusable(group, 'Planked river skiff with separate gunwales, pegged thwarts and floor boards. Move the placement empty to stage it.')
    return group


def water(scene):
    surface = material('River | Floodwater', (.034,.066,.087), .285)
    nodes, links = surface.node_tree.nodes, surface.node_tree.links
    coords = nodes.new('ShaderNodeTexCoord')
    vector = nodes.new('ShaderNodeVectorMath')
    vector.operation = 'MULTIPLY'
    vector.inputs[1].default_value = (8.2,2.1,1)
    ripples = nodes.new('ShaderNodeTexNoise')
    ripples.inputs['Scale'].default_value = 1.7
    ripples.inputs['Detail'].default_value = 2.4
    links.new(coords.outputs['Object'], vector.inputs[0])
    links.new(vector.outputs['Vector'], ripples.inputs['Vector'])
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .24
    bump.inputs['Distance'].default_value = .0034
    links.new(ripples.outputs['Fac'], bump.inputs['Height'])
    shader = nodes.get('Principled BSDF')
    shader.inputs['IOR'].default_value = 1.333
    links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    def wave(x,y):
        return .091+.0056*math.sin(7.6*x+2.4*y)+.0038*math.sin(12*x-7*y)+.0031*math.cos(9.3*y+5.1*x)

    values = [(-14+28*i/108) for i in range(109)]
    panel(scene.collection,'River | Rippled water surface', [[(x,y,wave(x,y)) for x in values] for y in values],surface)


def carved_oar(scene, grip, shaft_direction):
    group, anchor = prop(scene, 'Gopal | Carved river oar', grip)
    axis = Vector(shaft_direction)
    anchor.rotation_euler = Vector((0,1,0)).rotation_difference(axis).to_euler()
    ash = grain_mat('Oar | Weathered pale heartwood', (.235,.152,.081), .64)
    tip = grain_mat('Oar | River-darkened blade edge', (.119,.073,.036), .58)
    shaft = [(-.155,.021),(-.139,.022),(-.115,.018),(-.079,.0158),(.00,.0165),(.29,.018),
             (.54,.0178),(.86,.0195),(1.00,.0195),(1.07,.0180)]
    tube(group, 'Oar | Turned grip, loom and throat', [((0,y,0),radius) for y,radius in shaft], ash, anchor, 22)
    blade = [(1.00,.019,.010),(1.065,.031,.009),(1.14,.068,.0079),(1.25,.087,.0064),
             (1.42,.094,.0055),(1.54,.087,.005),(1.60,.066,.0045),(1.633,.037,.0042),(1.643,.009,.0040)]
    count = 24
    rings = []
    for y, width, depth in blade:
        ring = []
        for i in range(count):
            angle = math.tau*i/count
            ring.append((width*math.cos(angle),y+.006*math.sin(angle)**2,.015*(y-1)**2+depth*math.sin(angle)))
        rings.append(ring)
    vertices = [vertex for ring in rings for vertex in ring]
    faces = [(level*count+i,(level+1)*count+i,(level+1)*count+(i+1)%count,level*count+(i+1)%count)
             for level in range(len(rings)-1) for i in range(count)]
    faces.extend((tuple(range(count)),tuple(reversed(range(len(vertices)-count,len(vertices))))))
    obj = mesh(group,'Oar | Carved blade with raised spine',vertices,faces,ash,anchor)
    obj.data.materials.append(tip)
    for polygon in obj.data.polygons:
        if polygon.index >= count*6:
            polygon.material_index = 1
    reusable(group, 'One-piece hand-carved river oar. The upper hand placement is the collection origin.')
    group.instance_offset = grip
    return group


def actor_frame(rig, direction):
    return Matrix.Rotation(rig.rotation_euler.z,3,'Z') @ Vector(direction)


def pose_point(rig, x, y, z):
    hip = world_bone(rig,'hips')
    offset = actor_frame(rig,(x,y,0))
    return Vector((hip.x+offset.x,hip.y+offset.y,z))


def planted_foot(rig, side, target, pole, turnout, pitch=0):
    name = f'foot.{side}'
    reach(rig,f'thigh.{side}',f'shin.{side}',name,target,pole)
    joint = rig.pose.bones[name]
    spin = Matrix.Rotation(math.radians(turnout),3,'Z')
    roll = Matrix.Rotation(math.radians(pitch),3,'X')
    rotation = (spin @ roll @ joint.bone.matrix_local.to_3x3()).to_quaternion()
    joint.matrix = Matrix.LocRotScale(joint.head,rotation,joint.matrix.to_scale())
    bpy.context.view_layer.update()


def hand_basis(distal, radial):
    along = Vector(distal).normalized()
    across = Vector(radial)-Vector(radial).dot(along)*along
    across.normalize()
    return Matrix((across,along,across.cross(along))).transposed()


def grip_oar(rig, side, center, shaft_direction, palm_direction, pole):
    """Lay the palm against the shaft with its knuckles along the grain."""
    name = f'hand.{side}'
    joint = rig.pose.bones[name]
    bind = rig.data.bones
    fingers = [bind[f'finger_{index:02d}.{side}'].head_local for index in range(1,5)]
    rest_frame = hand_basis(joint.bone.tail_local-joint.bone.head_local,fingers[0]-fingers[-1])
    posed_frame = hand_basis(palm_direction,Vector(shaft_direction)*(-1 if side=='R' else 1))
    rotation = posed_frame @ rest_frame.transposed()
    knuckles = sum(fingers,Vector())/len(fingers)
    inward = posed_frame.col[2]*(1 if side=='R' else -1)
    scale = rig.matrix_world.to_scale().x
    wrist_to_knuckles = rotation @ (knuckles-joint.bone.head_local)*scale
    wrist = Vector(center)-inward*.024-wrist_to_knuckles+posed_frame.col[1]*.010
    reach(rig,f'upper_arm.{side}',f'forearm.{side}',name,wrist,pole)
    armature_rotation = rig.matrix_world.to_quaternion().inverted().to_matrix()
    hand_rotation = (armature_rotation @ rotation @ joint.bone.matrix_local.to_3x3()).to_quaternion()
    joint.matrix = Matrix.LocRotScale(joint.head,hand_rotation,joint.matrix.to_scale())
    bpy.context.view_layer.update()
    for index in range(1,5):
        digit = f'finger_{index:02d}.{side}'
        wrap = posed_frame.col[1]*.55+inward*.83-posed_frame.col[0]*.06
        aim_local(rig,digit,armature_rotation @ wrap)
    aim_local(rig,f'thumb.{side}',armature_rotation @ (posed_frame.col[1]*.31-posed_frame.col[0]*.78+inward*.45))

    observed = sum([world_bone(rig,f'finger_{index:02d}.{side}') for index in range(1,5)],Vector())/4
    offset = observed-Vector(center)
    radial_gap = (offset-offset.dot(Vector(shaft_direction))*Vector(shaft_direction)).length
    rig[f'{name} knuckles to oar axis (m)'] = round(radial_gap,4)
    if not .014 <= radial_gap <= .042:
        raise ValueError(f'{rig.name}/{name} palm is outside the usable oar grip')


def oar_pose(hero):
    scene = stage('At the oar','Gopal_At_The_Oar.png',(1000,820),(-3.55,-5.35,2.54),(-.10,.035,.60),2.92,river=True)
    river_skiff(scene)
    water(scene)
    rig = copy_model(scene,hero,'Gopal | Rowing pose',0,0)
    place_hip(rig,(.014,.168,.563))
    turn(rig,'hips',(0,1,0),-4)
    turn(rig,'spine',(1,0,0),13)
    turn(rig,'chest',(0,0,1),-8)
    turn(rig,'neck',(0,0,1),-5)
    turn(rig,'head',(1,0,0),-7)
    bpy.context.view_layer.update()
    planted_foot(rig,'R',(-.208,-.273,.242),(-.260,-.392,.588),-10)
    planted_foot(rig,'L',(.206,-.365,.244),(.298,-.438,.620),7)
    upper_grip = Vector((.190,-.276,1.033))
    shaft_direction = Vector((-.796,-.160,-.585)).normalized()
    guide_grip = upper_grip+shaft_direction*.445
    grip_oar(rig,'L',upper_grip,shaft_direction,(.18,-1,-.28),(.50,.041,1.098))
    grip_oar(rig,'R',guide_grip,shaft_direction,(.03,-1,.24),(-.51,-.095,1.003))
    carved_oar(scene,upper_grip,shaft_direction)
    action(rig,'Gopal | At the oar','Seated forward on the thwart with two hands on the oar and weight through both bare feet.')
    return scene


def chalk_mark(group, name, points, width, surface, seed):
    rng = Random(seed)
    rows = []
    for index,point in enumerate(points):
        tangent = (Vector(points[min(index+1,len(points)-1)])-Vector(points[max(index-1,0)])).normalized()
        perpendicular = Vector((-tangent.y,tangent.x,0))
        jitter = width*rng.uniform(-.37,.37)
        center = Vector(point)+perpendicular*jitter
        rows.append([center+perpendicular*width*spread*rng.uniform(.59,1.17) for spread in (-.5,0,.5)])
    return panel(group,name,rows,surface)


def court(scene):
    stone = material('Court pose stage | Warm sandstone',(.208,.151,.102),.94,46)
    seams = material('Court pose stage | Joints in floor',(.125,.093,.063),.94,53)
    group = bpy.data.collections.new('Court | Sandstone testimony stage')
    scene.collection.children.link(group)
    mesh(group,'Court | Floor joint bed',[(-20,-20,-.007),(20,-20,-.007),(20,20,-.007),(-20,20,-.007)],
         [(0,1,2,3)],seams,smooth=False)
    for row in range(-4,5):
        for col in range(-4,5):
            center = (col*1.29+.64*(row%2),row*.83,-.0275)
            beveled_box(group,'Court | Dressed sandstone floor slab',center,(1.283,.825,.055),stone,.003)
    shaded = material('Court pose stage | Worn umber wall',(.161,.117,.077),.94,31)
    trim = material('Court pose stage | Sandstone pillars',(.259,.183,.114),.89,51)
    beveled_box(group,'Court | Shaded colonnade wall',(0,3.651,1.467),(15,.172,2.94),shaded,.038)
    for x in (-4.45,-2.23,-.02,2.19,4.40):
        beveled_box(group,'Court | Column plinth',(x,2.862,.110),(.403,.389,.220),trim,.023)
        beveled_box(group,'Court | Column base',(x,2.862,.245),(.329,.316,.099),trim,.020)
        beveled_box(group,'Court | Column shaft',(x,2.862,1.558),(.261,.237,2.65),trim,.046)
    chalk_group, _ = prop(scene,'Court | Chalk river, market and gate',(0,0,0))
    chalk = material('Court pose stage | Powdered lime',(.63,.564,.432),.97,296)
    for index, x0 in enumerate((-.91,-.20)):
        points = [(x0+.097*math.sin(y*2.5)+.016*math.sin(y*8+index),y,.0024)
                  for y in (-1.35+2.67*i/78 for i in range(79))]
        chalk_mark(chalk_group,'Chalk | River bank',points,.024,chalk,index)
    marks = [((.22,-.49),(.78,-.49),(.78,.21),(.22,.21),(.22,-.49)),
             ((1.04,-.64),(1.04,.17),(1.39,.17),(1.39,-.64))]
    for index, vertices in enumerate(marks):
        for i,(begin,end) in enumerate(zip(vertices,vertices[1:])):
            points = [(*Vector(begin).lerp(Vector(end),t/28),.0025) for t in range(29)]
            chalk_mark(chalk_group,('Chalk | Market' if index==0 else 'Chalk | Gate'),points,.030,chalk,10*index+i)
    reusable(chalk_group, 'Floor-level Chapter 1 lime diagram. Gopal stands in the river with the market and gate to his right.')
    return group, chalk_group


def court_feet(rig):
    planted_foot(rig,'L',pose_point(rig,.153,-.114,.098),pose_point(rig,.240,-.345,.51),11)
    planted_foot(rig,'R',pose_point(rig,-.180,.153,.098),pose_point(rig,-.223,-.180,.54),-18)


def oblique_pose(hero):
    scene = stage('Oblique testimony','Gopal_Oblique_Testimony.png',(890,900),(-2.44,-5.5,2.51),(-.225,-.060,.87),2.43)
    court_groups = court(scene)
    rig = copy_model(scene,hero,'Gopal | Oblique court stance',-.55,63)
    place_hip(rig,(-.55,.037,.850))
    turn(rig,'hips',(0,1,0),-5)
    turn(rig,'spine',(1,0,0),6)
    turn(rig,'chest',(0,0,1),10)
    turn(rig,'neck',(0,0,1),-12)
    turn(rig,'head',(0,0,1),-26)
    bpy.context.view_layer.update()
    court_feet(rig)
    hand(rig,'R',pose_point(rig,-.263,.034,.937),pose_point(rig,-.38,-.012,1.145),actor_frame(rig,(.05,.04,-1)),10)
    hand(rig,'L',pose_point(rig,.268,-.176,.969),pose_point(rig,.43,.004,1.151),actor_frame(rig,(.02,-.38,-.92)),13)
    action(rig,'Gopal | Oblique testimony','Turns to show Vikram the oblique view of the cloth-covered back, with weight mostly on the front foot.')
    return scene, court_groups


def memory_pose(hero, court_groups):
    scene = stage('Reaching for his niece','Gopal_Reaching_For_His_Niece.png',(940,860),(-4.28,-3.85,2.22),(-.64,-.242,1.075),1.82)
    for group in court_groups:
        scene.collection.children.link(group)
    rig = copy_model(scene,hero,'Gopal | Right-hand memory reach',-.54,13)
    place_hip(rig,(-.54,.063,.851))
    turn(rig,'hips',(0,1,0),-3)
    turn(rig,'spine',(1,0,0),9)
    turn(rig,'chest',(0,0,1),-10)
    turn(rig,'neck',(1,0,0),12)
    turn(rig,'head',(0,0,1),-23)
    bpy.context.view_layer.update()
    court_feet(rig)
    shoulder = world_bone(rig,'upper_arm.R')
    wrist = shoulder+actor_frame(rig,(-.097,-.403,-.241))
    hand(rig,'R',wrist,pose_point(rig,-.465,.010,1.095),actor_frame(rig,(-.08,-.91,-.42)),6)
    hand(rig,'L',pose_point(rig,.219,.080,.936),pose_point(rig,.42,.059,1.135),actor_frame(rig,(-.08,-.05,-1)),14)
    for eye in ('L','R'):
        turn(rig,f'eye.{eye}',(1,0,0),18)
    action(rig,'Gopal | Right hand reaches in memory','Still in court, lowers his gaze and extends his right palm toward the remembered position of his niece.')
    return scene


def make_story_scenes(hero, output):
    """Create the three editable poses with review renders beside the model file."""
    Path(output).mkdir(parents=True,exist_ok=True)
    boat = oar_pose(hero)
    testimony, court_groups = oblique_pose(hero)
    return [boat,testimony,memory_pose(hero,court_groups)]
