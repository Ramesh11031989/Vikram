"""Chapter 1 staging poses and Shyam Munshi's oilcloth record bundle."""

import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

from build_cast import light, setup_stage, stage_camera, studio_material, turn
from build_vikram_hero import copy_model


def material(name, color, roughness=.78, grain=0):
    existing = bpy.data.materials.get(name)
    if existing is not None:
        return existing
    result = studio_material(name, color, roughness)
    if grain:
        nodes, links = result.node_tree.nodes, result.node_tree.links
        noise = nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = grain
        noise.inputs['Detail'].default_value = 3.2
        coordinates = nodes.new('ShaderNodeTexCoord')
        links.new(coordinates.outputs['Object'], noise.inputs['Vector'])
        dye = nodes.new('ShaderNodeValToRGB')
        dye.color_ramp.elements[0].position = .22
        dye.color_ramp.elements[0].color = (*(channel*.48 for channel in color), 1)
        dye.color_ramp.elements[1].position = .79
        dye.color_ramp.elements[1].color = (*(channel*1.30 for channel in color), 1)
        links.new(noise.outputs['Fac'], dye.inputs['Fac'])
        surface = nodes.get('Principled BSDF')
        links.new(dye.outputs['Color'], surface.inputs['Base Color'])
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .40
        bump.inputs['Distance'].default_value = .0022 if grain<80 else .00065
        links.new(noise.outputs['Fac'], bump.inputs['Height'])
        links.new(bump.outputs['Normal'], surface.inputs['Normal'])
    return result


def mesh(collection, name, vertices, faces, surface, parent=None, smooth=True):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    obj.parent = parent
    data.materials.append(surface)
    for face in data.polygons:
        face.use_smooth = smooth
    return obj


def tube(collection, name, stations, surface, parent=None, sides=14, bark=False):
    """Freeform thickened rings supporting both rough wood and slender ties."""
    points = [Vector(point) for point, _ in stations]
    vertices = []
    for index, ((_, radius), point) in enumerate(zip(stations, points)):
        direction = (points[min(index+1,len(points)-1)]-points[max(0,index-1)]).normalized()
        helper = Vector((0,1,0)) if abs(direction.y)<.82 else Vector((0,0,1))
        u = direction.cross(helper).normalized()
        v = direction.cross(u).normalized()
        for side in range(sides):
            angle = math.tau*side/sides
            detail = 1 + (.079*math.sin(angle*9+.42*index)+.045*math.cos(angle*5-.36*index) if bark else 0)
            vertices.append(point + radius*detail*(u*math.cos(angle)+v*math.sin(angle)))
    faces = [(j+sides*i,(j+1)%sides+sides*i,(j+1)%sides+sides*(i+1),j+sides*(i+1))
             for i in range(len(points)-1) for j in range(sides)]
    faces.extend((tuple(reversed(range(sides))), tuple(range(len(vertices)-sides,len(vertices)))))
    return mesh(collection,name,vertices,faces,surface,parent)


def panel(collection, name, points, surface, parent=None, thickness=0):
    rows, columns = len(points), len(points[0])
    faces = [(r*columns+c,r*columns+c+1,(r+1)*columns+c+1,(r+1)*columns+c)
             for r in range(rows-1) for c in range(columns-1)]
    obj = mesh(collection,name,[point for row in points for point in row],faces,surface,parent)
    if thickness:
        shell = obj.modifiers.new('Material thickness','SOLIDIFY')
        shell.thickness = thickness
        shell.offset = -.6
    return obj


def prop(scene, name, location):
    collection = bpy.data.collections.new(name)
    scene.collection.children.link(collection)
    anchor = bpy.data.objects.new(f'{name} | placement',None)
    collection.objects.link(anchor)
    anchor.location = location
    anchor.empty_display_type = 'PLAIN_AXES'
    anchor.empty_display_size = .035
    return collection, anchor


def closed_bundle(scene, location, rotation=0, asset=False):
    group, anchor = prop(scene,'Oiled cloth bundle | Tied',location)
    anchor.rotation_euler.z = math.radians(rotation)
    cloth = material('Bundle | Warm umber oilcloth',(.116,.067,.028),.48,92)
    fold = material('Bundle | Dark edge and folded overlap',(.073,.042,.017),.61,118)
    cord = material('Bundle | Flax binding',(.226,.147,.066),.85,150)
    sections = [(-.046,.095,.056),(-.035,.114,.071),(-.016,.123,.078),
                (.012,.118,.077),(.035,.099,.062),(.041,.077,.049)]
    count = 48
    vertices = []
    for level,(z,rx,ry) in enumerate(sections):
        for face in range(count):
            a = math.tau*face/count
            sx = math.copysign(abs(math.cos(a))**.71,math.cos(a))
            sy = math.copysign(abs(math.sin(a))**.71,math.sin(a))
            edge = 1 + .033*math.sin(5*a+.7*level)+.024*math.cos(9*a-.8*level)
            vertices.append((rx*sx*edge,ry*sy*edge,z+.0026*math.sin(4*a+.65*level)))
    faces = [(r*count+s,r*count+(s+1)%count,(r+1)*count+(s+1)%count,(r+1)*count+s)
             for r in range(len(sections)-1) for s in range(count)]
    faces.extend((tuple(reversed(range(count))),tuple(range(len(vertices)-count,len(vertices)))))
    mesh(group,'Bundle | Folded oilcloth',vertices,faces,cloth,anchor)
    overlap = [[(u*.211-.105,v+.019*math.sin(math.pi*u),.041-.019*(2*u-1)**4-.018*(v/.072)**4)
                for u in (i/20 for i in range(21))] for v in (-.063,-.038,-.025,-.014)]
    panel(group,'Bundle | Cloth tucked under binding',overlap,fold,anchor,.0018)
    for x in (-.021,.020):
        points = [((x+.011*math.sin(a),.080*math.sin(a),.050*math.cos(a)-.001),.0026)
                  for a in (math.tau*j/32 for j in range(33))]
        tube(group,'Bundle | Rope around folds',points,cord,anchor,8)
    tube(group,'Bundle | Tied tail', [((-.026,.004,.054),.0035),((-.009,0,.061),.0036),
         ((.007,-.019,.052),.0032),((.036,-.047,.045),.00285),((.064,-.062,.036),.0023)],cord,anchor,9)
    tube(group,'Bundle | Loose tail', [((-.015,.004,.059),.0032),((-.030,.019,.070),.0032),
         ((-.067,.031,.057),.0028),((-.086,.043,.037),.0024)],cord,anchor,9)
    if asset:
        group.asset_mark()
        group.instance_offset = anchor.location
        group.asset_data.description = 'Shyam Munshi’s tied, oiled cloth bundle. Move the placement empty to position it.'
    return group


def open_bundle(scene, location):
    group, anchor = prop(scene,'Oiled cloth bundle | Open',location)
    cloth = material('Bundle | Warm umber oilcloth',(.116,.067,.028),.48,92)
    fiber = material('Ledger | Unbleached paper',(.63,.48,.26),.94,340)
    edge = material('Ledger | Worn paper edges',(.32,.22,.105),.96,260)
    stain = material('Ledger | Brown oil stains',(.27,.147,.062),.93,195)
    ink = material('Ledger | Dry brown-black ink',(.050,.030,.013),.96)

    def height(u,v):
        sides = .073*abs(u)**3.4*(.77+.21*math.cos(2.5*v))
        curl = .021*max(0,v)**4+.0045*math.sin(12*u+3.6*v)+.0035*math.sin(9*v-4*u)
        return sides+curl

    cloth_points = []
    for row,v in enumerate(-1+2*j/26 for j in range(27)):
        cloth_points.append([(.198*u+.013*v**2*math.sin(4*v),.160*v+.018*u**3,
                              height(u,v)+.003*math.cos(row*.65))
                             for u in (-1+2*j/30 for j in range(31))])
    panel(group,'Bundle | Spread stitched oilcloth',cloth_points,cloth,anchor,.0023)

    def page(u,v,z=.018):
        crumple = .0037*u**2 + .0051*max(0,v)**3*(.6+.4*u)
        crumple += .0008*math.sin(7*u-4*v)
        return (.132*u+.009*v,.089*v-.004+.0013*math.cos(18*u+v),z+crumple)

    for page_index in range(5):
        row_count, column_count = 12, 16
        angle = math.radians((page_index-4)*1.7)
        points = []
        for j in range(row_count):
            row = []
            for i in range(column_count):
                u,v = -1+2*i/(column_count-1),-1+2*j/(row_count-1)
                x,y,z = page(u,v,.008+page_index*.0025)
                row.append((x*math.cos(angle)-y*math.sin(angle)-.002*(4-page_index),
                            x*math.sin(angle)+y*math.cos(angle),z))
            points.append(row)
        panel(group,'Ledger | Refuge register' if page_index==4 else f'Ledger | Older leaf {page_index+1}',
              points,fiber if page_index==4 else edge,anchor,.0010)
    for cx,cy,rx,ry in ((-.59,.57,.27,.16),(.59,-.64,.22,.18),(-.77,-.65,.14,.17)):
        rim = [(cx+rx*math.cos(a)*(1+.18*math.sin(5*a)),cy+ry*math.sin(a)*(1+.14*math.cos(7*a)))
               for a in (math.tau*j/18 for j in range(18))]
        vertices = [page(cx,cy,.0185),*[page(x,y,.0185) for x,y in rim]]
        mesh(group,'Ledger | Irregular oil blot',vertices,[(0,j+1,(j+1)%len(rim)+1) for j in range(len(rim))],
             stain,anchor,False)
    for v in (-.60,-.40,-.20,0,.20,.40,.60):
        for start,end in ((-.72,-.58),(-.40,.63),(.76,.84)):
            points = [(page(start+(end-start)*j/15,v,.0192),.00062) for j in range(16)]
            tube(group,'Ledger | Account row',points,ink,anchor,6)
    for u in (-.49,.70):
        tube(group,'Ledger | Column rule',[(page(u,-.73+1.47*j/20,.0191),.00051) for j in range(21)],ink,anchor,6)
    group.asset_mark()
    group.instance_offset = anchor.location
    group.asset_data.description = 'Shyam Munshi’s opened oilcloth bundle with oil-stained account sheets.'
    return group


def world_bone(rig, name):
    return rig.matrix_world @ rig.pose.bones[name].head


def place_hip(rig, target):
    bpy.context.view_layer.update()
    rig.location += Vector(target)-world_bone(rig,'hips')
    bpy.context.view_layer.update()


def aim_local(rig, name, direction):
    joint = rig.pose.bones[name]
    direction = Vector(direction)
    if direction.length_squared < 1e-10:
        raise ValueError(f'No direction for {rig.name}/{name}')
    joint.rotation_mode = 'QUATERNION'
    current = joint.matrix.to_quaternion()
    rotation = (current @ Vector((0,1,0))).rotation_difference(direction.normalized()) @ current
    joint.matrix = Matrix.LocRotScale(joint.head,rotation,joint.matrix.to_scale())
    bpy.context.view_layer.update()


def aim_world(rig, name, direction):
    aim_local(rig,name,rig.matrix_world.to_3x3().inverted() @ Vector(direction))


def reach(rig, upper, lower, end, target, pole):
    inverse = rig.matrix_world.inverted()
    tip = inverse @ Vector(target)
    pivot = rig.pose.bones[upper].head.copy()
    a = rig.data.bones[upper].length
    b = rig.data.bones[lower].length
    delta = tip-pivot
    axis = delta.normalized()
    distance = min(a+b-.001, max(abs(a-b)+.001,delta.length))
    pole_delta = inverse @ Vector(pole)-pivot
    bend = (pole_delta-pole_delta.dot(axis)*axis).normalized()
    along = (a*a-b*b+distance*distance)/(2*distance)
    middle = pivot+axis*along+bend*math.sqrt(max(0,a*a-along*along))
    aim_local(rig,upper,middle-pivot)
    aim_local(rig,lower,pivot+axis*distance-rig.pose.bones[lower].head)
    error = (world_bone(rig,end)-Vector(target)).length
    rig[f'{end} target distance (m)'] = round(error,4)
    if error>.025:
        raise ValueError(f'{rig.name}/{end} is {error:.3f} m short of its stage contact')


def hand(rig, side, target, pole, direction, curl=0):
    reach(rig,f'upper_arm.{side}',f'forearm.{side}',f'hand.{side}',target,pole)
    aim_world(rig,f'hand.{side}',direction)
    if curl:
        bend = curl if side=='L' else -curl
        for finger in range(1,5):
            turn(rig,f'finger_{finger:02d}.{side}',(1,0,0),bend*(.86+.04*finger))
        turn(rig,f'thumb.{side}',(1,0,0),bend*.43)
        bpy.context.view_layer.update()


def leg(rig, side, target, pole, toes=(0,-1,-.23)):
    reach(rig,f'thigh.{side}',f'shin.{side}',f'foot.{side}',target,pole)
    aim_world(rig,f'foot.{side}',toes)


def action(rig, title, description):
    for joint in rig.pose.bones:
        joint.rotation_mode = 'QUATERNION'
        joint.keyframe_insert(data_path='rotation_quaternion',frame=1,group=joint.name)
    clip = rig.animation_data.action
    clip.name = title
    clip.asset_mark()
    clip.asset_data.description = description
    clip.asset_data.tags.new('Pose')
    rig['Pose use'] = description


def stage(label, filename, dimensions, camera, target, scale):
    result = bpy.data.scenes.new(f'Betal | {label}')
    setup_stage(result,*dimensions,18,.18)
    stage_camera(result,f'{label} review camera',camera,target,scale)
    light(result,'Late light through canopy',(-3.4,-4.3,4.6),target,(1,.81,.64),465,2.45)
    light(result,'Cool open sky',(3.2,-2.7,3.1),target,(.64,.79,1),193,2.6)
    light(result,'Warm outline',(1.2,2.9,4.0),target,(1,.64,.37),310,1.75)
    result.render.filepath = f'//{filename}'
    return result


def ground(scene):
    surface = material('Cremation ground | Quiet charcoal earth',(.092,.071,.048),.94,21)
    mesh(scene.collection,'Ground | Earth stage',[(-50,-50,.003),(50,-50,.003),(50,50,.003),(-50,50,.003)],
         [(0,1,2,3)],surface,smooth=False)


def banyan(scene):
    bark = material('Banyan | Age-darkened bark',(.117,.074,.039),.95,35)
    roots = material('Banyan | Umber aerial roots',(.081,.051,.028),.93,48)
    group,_ = prop(scene,'Banyan | Seating branch',(0,0,0))
    tube(group,'Banyan | Main trunk', [((-1.00,.32,-.12),.29),((-.96,.43,.49),.30),
         ((-1.03,.46,1.04),.295),((-1.13,.50,1.70),.257),((-1.04,.53,2.70),.227)],bark,sides=32,bark=True)
    tube(group,'Banyan | Low lateral branch', [((-1.04,.43,1.016),.201),((-.65,.245,1.042),.183),
         ((-.25,.090,1.068),.155),((.08,.052,1.063),.155),((.42,.077,1.127),.136),
         ((.81,.148,1.211),.109),((1.15,.295,1.414),.070),((1.52,.35,1.47),.047)],bark,sides=38,bark=True)
    tube(group,'Banyan | Lower fork', [((-.94,.33,.61),.15),((-.59,.08,.68),.10),
         ((-.27,-.27,.75),.082),((.08,-.40,.745),.068),((.48,-.37,.76),.047),((.78,-.24,.80),.015)],
         bark,sides=28,bark=True)
    for i in range(8):
        x = -.83+i*.295
        y = .37+.078*math.cos(i*6)
        upper = 2.81-.028*i
        low = 1.43+.14*math.sin(i*3.2) if i in (3,4,5) else .47+.093*i
        tube(group,f'Banyan | Hanging aerial strand {i+1}',
             [((x,y,upper),.012),((x+.016,y-.010,upper*.66+low*.34),.0091),
              ((x-.016,y+.027,upper*.27+low*.73),.0065),((x+.014,y+.069,low),.0034)],roots,sides=9)


def append_vikram(scene, path):
    with bpy.data.libraries.load(str(path),link=False) as (source, destination):
        if 'CH_VikramHero' not in source.collections:
            raise ValueError('The approved Vikram Blender file has no CH_VikramHero asset collection')
        destination.collections = ['CH_VikramHero']
    group = destination.collections[0]
    group.name = 'Approved Vikram | Carry support'
    if group.asset_data:
        group.asset_clear()
    scene.collection.children.link(group)
    for part in list(group.all_objects):
        if part.type not in {'MESH','ARMATURE'}:
            continue
        imported = part.data
        part.data = imported.copy()
        bank = bpy.data.meshes if part.type=='MESH' else bpy.data.armatures
        if imported.users==0:
            bank.remove(imported)
    rig, = [part for part in group.all_objects if part.type=='ARMATURE']
    rig.name = 'Approved Vikram | Carry rig'
    return rig


def ease_vikram_coat(rig):
    """Fit the two costume layers on Vikram’s carry copy."""
    panels = ('Angarkha • long','Angarkha • folded hem','Angarkha • side opening piping',
              'Angarkha • bound lower hem')
    for obj in rig.children:
        if obj.type != 'MESH' or not any(label in obj.name for label in panels):
            continue
        for vertex in obj.data.vertices:
            x,y,z = vertex.co
            height = min(1,max(0,(.885-z)/.29))
            front = min(1,max(0,(.075-y)/.22))
            vertex.co.y -= (.183 if x>=0 else .103)*height*front
            vertex.co.x += math.copysign(.032*height*(.42+.58*front),x)
        obj.data.update()
    for obj in rig.children:
        if obj.type!='MESH' or 'gathered dhoti leg' not in obj.name:
            continue
        side = 1 if 'thigh.L' in obj.vertex_groups else -1
        for vertex in obj.data.vertices:
            x,y,z = vertex.co
            t = min(1,max(0,(z-.54)/.20))
            center_x = side*(.151-.041*t)
            center_y = .012-.025*t
            fit = 1-.46*t*t*(3-2*t)
            vertex.co.x = center_x+(x-center_x)*fit
            vertex.co.y = center_y+(y-center_y)*fit
        obj.data.update()


def branch_pose(hero):
    scene = stage('On the banyan branch','Betal_On_Branch.png',(730,760),
                  (3.22,-5.8,2.45),(0,0,1.39),2.02)
    ground(scene)
    banyan(scene)
    rig = copy_model(scene,hero,'Shyam Munshi | Banyan pose',0,1)
    hero.set_ankle(rig,swollen=True,wrapped=False)
    place_hip(rig,(.03,.048,1.278))
    turn(rig,'chest',(0,0,1),8)
    turn(rig,'spine',(1,0,0),9)
    turn(rig,'head',(1,0,0),16)
    bpy.context.view_layer.update()
    leg(rig,'L',(.24,-.413,.913),(.26,-.64,1.24),(.10,-1,-.18))
    leg(rig,'R',(-.179,-.424,.798),(-.18,-.59,1.20),(-.13,-.77,-.47))
    hand(rig,'L',(.383,.041,1.319),(.62,.04,1.54),(-.17,.02,-.98),19)
    hand(rig,'R',(-.292,-.301,1.388),(-.43,-.036,1.49),(.22,-.53,-.81),23)
    closed_bundle(scene,(-.271,-.350,1.278),-13,asset=True)
    action(rig,'Shyam Munshi | On the banyan branch','Seated on the banyan, left foot supported and injured right ankle hanging free.')
    return scene


def carry_pose(hero, path):
    scene = stage('On Vikram’s back','Betal_On_Vikrams_Back.png',(750,800),
                  (4.10,-4.55,2.19),(.03,.05,1.03),2.25)
    ground(scene)
    vikram = append_vikram(scene, path)
    ease_vikram_coat(vikram)
    place_hip(vikram,(0,.006,.849))
    turn(vikram,'hips',(1,0,0),7)
    turn(vikram,'spine',(1,0,0),11)
    turn(vikram,'head',(1,0,0),-12)
    bpy.context.view_layer.update()
    leg(vikram,'L',(.209,-.136,.103),(.29,-.34,.56),(.09,-1,-.19))
    leg(vikram,'R',(-.168,.157,.105),(-.166,-.176,.43),(-.11,-1,-.19))

    rig = copy_model(scene,hero,'Shyam Munshi | Carry pose',0,0)
    hero.set_ankle(rig,swollen=True,wrapped=False)
    place_hip(rig,(.083,.294,1.049))
    turn(rig,'hips',(1,0,0),20)
    turn(rig,'spine',(1,0,0),8)
    turn(rig,'chest',(0,0,1),9)
    turn(rig,'head',(1,0,0),-11)
    turn(rig,'neck',(0,0,1),-8)
    bpy.context.view_layer.update()
    leg(rig,'L',(.386,.126,.678),(.45,-.146,1.023),(.02,-1,-.33))
    leg(rig,'R',(-.316,.154,.687),(-.36,-.14,1.04),(-.15,-1,-.32))
    shoulder = world_bone(vikram,'upper_arm.L')
    hand(rig,'L',shoulder+Vector((.045,-.025,.100)),(.52,.207,1.54),(-.32,-.91,-.26),28)
    hand(rig,'R',(-.328,-.255,1.310),(-.47,.036,1.46),(-.14,-.68,-.72),25)
    hand(vikram,'L',(.380,-.031,.885),(.48,-.09,1.05),(.02,.95,.18),25)
    hand(vikram,'R',(-.382,-.005,.897),(-.48,-.075,1.092),(.04,.95,.17),26)
    closed_bundle(scene,(-.335,-.335,1.207),-21)
    action(rig,'Shyam Munshi | On Vikram’s back','A close piggyback lean. Vikram supports both thighs, and the rider braces one hand at his shoulder.')
    action(vikram,'Vikram | Supporting Shyam Munshi','Companion carry stance for the Shyam Munshi piggyback pose.')
    return scene


def stone(scene, name, radius, height, center):
    rock = material('Chabutra | Worn warm basalt',(.117,.100,.076),.92,48)
    x,y,z = center
    outline = [(x+radius*math.cos(a)*(1+.034*math.cos(5*a)),
                y+radius*.73*math.sin(a)*(1+.037*math.sin(7*a)))
               for a in (math.tau*j/12 for j in range(12))]
    rows = [([(x0,y0,z+h) for x0,y0 in outline]) for h in (0,height-.029,height)]
    vertices = [p for row in rows for p in row]
    faces = [(r*12+j,r*12+(j+1)%12,(r+1)*12+(j+1)%12,(r+1)*12+j)
             for r in range(len(rows)-1) for j in range(12)]
    faces.extend((tuple(reversed(range(12))),tuple(range(len(vertices)-12,len(vertices)))))
    obj = mesh(scene.collection,name,vertices,faces,rock,smooth=False)
    edit = obj.modifiers.new('Weathered stone rims','BEVEL')
    edit.width, edit.segments = .016, 2
    return obj


def bundle_pose(hero):
    scene = stage('Opening the bundle','Betal_Opening_Bundle.png',(730,740),
                  (2.7,-5.4,3.16),(0,-.278,.831),1.81)
    ground(scene)
    stone(scene,'Chabutra | Resting ledge',.66,.480,(0,.237,.008))
    rig = copy_model(scene,hero,'Shyam Munshi | Opening the oilcloth',0,0)
    hero.set_ankle(rig,swollen=True,wrapped=False)
    place_hip(rig,(0,.020,.594))
    turn(rig,'hips',(1,0,0),8)
    turn(rig,'spine',(1,0,0),15)
    turn(rig,'head',(1,0,0),10)
    bpy.context.view_layer.update()
    leg(rig,'L',(.238,-.430,.093),(.27,-.63,.526),(.08,-1,-.20))
    leg(rig,'R',(-.190,-.507,.122),(-.24,-.64,.513),(-.08,-1,-.34))
    hand(rig,'L',(.224,-.366,.657),(.48,-.142,.827),(-.31,-.26,-.92),26)
    hand(rig,'R',(-.232,-.354,.658),(-.47,-.121,.833),(.28,-.29,-.91),29)
    open_bundle(scene,(0,-.361,.545))
    action(rig,'Shyam Munshi | Opening the bundle','Seated on the chabutra, both hands spreading the stained oilcloth to reveal the relief register.')
    return scene


def ankle_pose(hero):
    scene = stage('Tying the right ankle','Betal_Tying_Ankle.png',(710,735),
                  (3.0,-5.4,2.11),(0,-.232,.706),1.58)
    ground(scene)
    bark = material('Banyan | Age-darkened bark',(.117,.074,.039),.95,35)
    tube(scene.collection,'Banyan | Root seat', [((-.94,.34,.19),.269),((-.56,.207,.19),.223),
         ((-.20,.071,.143),.167),((.16,.149,.112),.149),((.52,.31,.095),.124),((.74,.48,.072),.061)],
         bark,sides=29,bark=True)
    tube(scene.collection,'Banyan | Root trunk', [((-.81,.47,.001),.292),((-.94,.49,.28),.265),
         ((-.95,.57,.99),.266),((-1.0,.65,1.79),.237)],bark,sides=28,bark=True)
    rig = copy_model(scene,hero,'Shyam Munshi | Ankle binding pose',0,0)
    hero.set_ankle(rig,swollen=True,wrapped=True)
    place_hip(rig,(-.068,.052,.422))
    turn(rig,'hips',(1,0,0),31)
    turn(rig,'spine',(1,0,0),29)
    turn(rig,'chest',(0,0,1),-16)
    turn(rig,'head',(1,0,0),5)
    bpy.context.view_layer.update()
    leg(rig,'L',(.236,-.374,.096),(.241,-.48,.441),(.15,-1,-.29))
    leg(rig,'R',(-.232,-.493,.127),(-.312,-.58,.381),(-.20,-.92,-.33))
    hand(rig,'L',(-.093,-.382,.236),(.236,-.330,.38),(-.78,-.53,-.37),24)
    hand(rig,'R',(-.235,-.391,.278),(-.424,-.320,.37),(-.04,-.53,-.85),24)
    closed_bundle(scene,(.329,-.004,.058),35)
    action(rig,'Shyam Munshi | Tying the right ankle','At the banyan root at dusk, hands drawn toward the binding around his injured right ankle.')
    return scene


def make_story_scenes(hero, vikram_path, output):
    """Create the Chapter 1 pose assets, with renders relative to the final Blender file."""
    vikram_path = Path(vikram_path)
    if not vikram_path.is_file():
        raise FileNotFoundError(f'Approved Vikram carry support is missing at {vikram_path}')
    Path(output).mkdir(parents=True,exist_ok=True)
    return [branch_pose(hero),carry_pose(hero,vikram_path),bundle_pose(hero),ankle_pose(hero)]
