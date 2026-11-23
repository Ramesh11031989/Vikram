"""Vikram's tailored court costume, fitted to the measured hero rest pose."""

import bisect
import math

from mathutils import Vector
from textile import finish_fabric, store_rest_positions


PROFILE = [
    (.88, .197, -.137, .113), (.93, .180, -.139, .118), (.98, .177, -.137, .111),
    (1.03, .174, -.145, .083), (1.08, .164, -.148, .072), (1.13, .161, -.147, .072),
    (1.18, .163, -.151, .083), (1.23, .174, -.155, .095), (1.28, .188, -.147, .100),
    (1.33, .210, -.157, .115), (1.38, .210, -.149, .121), (1.43, .202, -.121, .118),
    (1.46, .210, -.105, .114), (1.49, .107, -.087, .103),
]
FITTING = [(z, 0, (front+back)/2, radius, (back-front)/2) for z, radius, front, back in PROFILE]
JOINTS = {
    'shoulder': (.214,.009,1.461), 'elbow': (.343,-.011,1.155), 'wrist': (.406,-.057,.975),
    'hip': (.119,-.007,.866), 'knee': (.139,-.011,.55), 'ankle': (.188,.057,.117),
}


def mix(a, b, t):
    return a+(b-a)*t


def smooth(t):
    t = min(1, max(0, t))
    return t*t*(3-2*t)


def weights(a, b, t):
    return {a: 1-t, b: t}


def profile_at(rings, z):
    upper = bisect.bisect_right([ring[0] for ring in rings], z)
    if not upper:
        return rings[0][1:]
    if upper == len(rings):
        return rings[-1][1:]
    low, high = rings[upper-1], rings[upper]
    t = (z-low[0])/(high[0]-low[0])
    return [mix(a,b,t) for a,b in zip(low[1:],high[1:])]


def joint(c, name, side):
    sign = 1 if side == 'L' else -1
    x,y,z = JOINTS[name]
    return Vector(c.landmarks.get(f'{name}.{side}', (sign*x,y,z)))


def body_weights(z):
    if z < 1.15:
        return weights('hips','spine',smooth((z-.96)/.19))
    return weights('spine','chest',smooth((z-1.15)/.20))


def make_uv(obj, lookup):
    uv = obj.data.uv_layers.new(name='GarmentUV')
    for polygon in obj.data.polygons:
        coordinates = lookup(polygon)
        for loop, point in zip(polygon.loop_indices, coordinates):
            uv.data[loop].uv = point


def patch(c, label, rows, row_weights, material, closed=False, flip=False):
    """Raised fabric patch. The edge rows form the garment's sewn silhouette."""
    width, length = len(rows[0]), len(rows)
    faces = []
    faces_per_row = width if closed else width-1
    for i in range(length-1):
        for j in range(faces_per_row):
            nxt = (j+1) % width
            face = (i*width+j, i*width+nxt, (i+1)*width+nxt, (i+1)*width+j)
            faces.append(face[::-1] if flip else face)
    obj = c.mesh(label, [point for row in rows for point in row], faces, material,
                 [weight for weight in row_weights for _ in range(width)])

    def uv(face):
        i,j = divmod(face.index, faces_per_row)
        coords = ((j,i),(j+1,i),(j+1,i+1),(j,i+1))
        return [(s/faces_per_row,t/(length-1)) for s,t in (coords[::-1] if flip else coords)]

    make_uv(obj, uv)
    return obj


def fabric(c, name, color, pitch, contrast, relief, fine=True):
    material = c.mat(name,color,.80)
    finish_fabric(material,fine=fine)
    group = next(node for node in material.node_tree.nodes if node.type == 'GROUP')
    group.inputs['Thread pitch (mm)'].default_value=pitch
    group.inputs['Yarn contrast'].default_value=contrast
    group.inputs['Relief (mm)'].default_value=relief
    return material


def worn_hardware(c, name, color, metallic, roughness, grain):
    material=c.mat(name,color,roughness,metallic)
    tree=material.node_tree
    bsdf=tree.nodes.get('Principled BSDF')
    coordinate=tree.nodes.new('ShaderNodeTexCoord')
    noise=tree.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value=grain
    noise.inputs['Detail'].default_value=2.3
    tree.links.new(coordinate.outputs['Object'],noise.inputs['Vector'])
    color_map=tree.nodes.new('ShaderNodeValToRGB')
    for item,position,value in zip(color_map.color_ramp.elements,(.18,.80),(.46,1.15)):
        item.position=position
        item.color=(*(channel*value for channel in color),1)
    tree.links.new(noise.outputs['Fac'],color_map.inputs[0])
    tree.links.new(color_map.outputs[0],bsdf.inputs['Base Color'])
    bump=tree.nodes.new('ShaderNodeBump')
    bump.inputs['Distance'].default_value=.00032
    bump.inputs['Strength'].default_value=.29
    tree.links.new(noise.outputs['Fac'],bump.inputs['Height'])
    tree.links.new(bump.outputs['Normal'],bsdf.inputs['Normal'])
    return material


def coat_point(profile, z, angle, extra=0):
    cx,cy,rx,ry=profile_at(profile,z)
    center=.92+.048*math.sin(angle+.4)
    gathers=math.exp(-((z-center)/.14)**2)
    underarm=math.exp(-((z-1.32)/.095)**2)*abs(math.cos(angle))**3
    fold=gathers*(.0045*math.cos(8*angle+(z-.97)*25)+.002*math.sin(15*angle-z*18))
    fold+=underarm*.0027*math.cos(angle*11+(z-1.34)*50)
    return Vector((cx+(rx+.010+fold+extra)*math.cos(angle),
                   cy+(ry+.015+fold+extra)*math.sin(angle),z))


def torso_face(profile, z, x, side, extra):
    cx,_,rx,_=profile_at(profile,z)
    angle=math.acos(min(.982,max(-.982,(x-cx)/(rx+.01))))*side
    point=coat_point(profile,z,angle)
    point.x=x
    point.y+=side*extra
    return point


def arm_geometry(c, side):
    shoulder, elbow, wrist=(joint(c,label,side) for label in ('shoulder','elbow','wrist'))
    to_elbow, to_wrist=elbow-shoulder,wrist-elbow
    upper_length, lower_length=to_elbow.length,to_wrist.length
    upper,lower=to_elbow.normalized(),to_wrist.normalized()
    sign=1 if side=='L' else -1

    def station(distance):
        center=shoulder+upper*distance if distance<upper_length else elbow+lower*(distance-upper_length)
        turn=smooth((distance-upper_length+.042)/.084)
        tangent=upper.lerp(lower,turn).normalized()
        across=Vector((0,sign,0))
        across=(across-across.dot(tangent)*tangent).normalized()
        outer=tangent.cross(across).normalized()
        return center, tangent, across, outer

    return station,upper_length,upper_length+lower_length


def limb_radii(points, center, tangent, basis, span, cutoff, fallback):
    """Small rest-mesh slices keep sleeve ease above local anatomy."""
    cloud=[]
    for point in points:
        delta=point-center
        if delta.length_squared>cutoff*cutoff or abs(delta.dot(tangent))>span:
            continue
        cloud.append(delta)
    if len(cloud)<8:
        return fallback
    return tuple(max(radius, sorted(abs(delta.dot(axis)) for delta in cloud)[int(.93*(len(cloud)-1))]+.009)
                 for axis,radius in zip(basis,fallback))


def build_angarkha(c, profile, skin, navy, liner, braid):
    height=(joint(c,'shoulder','L').z+joint(c,'shoulder','R').z)/2
    armhole_low,armhole_high=height-.135,height+.015
    levels=sorted({.88, .895, .915, .94, .975, 1.015, 1.055, 1.095, 1.13,
                   1.16, 1.19, 1.22, 1.255, 1.28, 1.31, 1.49, 1.502, 1.516,
                   *(mix(armhole_low,armhole_high,i/9) for i in range(10))})
    low,high=levels.index(armhole_low),levels.index(armhole_high)
    segments,span=72,7
    vertices=[coat_point(profile,z,math.tau*j/segments) for z in levels for j in range(segments)]
    skinning=[body_weights(z) for z in levels for _ in range(segments)]
    faces=[]
    uvs=[]
    for i in range(len(levels)-1):
        for j in range(segments):
            if low<=i<high and any((j-center)%segments<span or (center-j)%segments<=span
                                    for center in (0,segments//2)):
                continue
            nxt=(j+1)%segments
            faces.append((i*segments+j,i*segments+nxt,(i+1)*segments+nxt,(i+1)*segments+j))
            uvs.append([(s/segments,t/(len(levels)-1)) for s,t in ((j,i),(j+1,i),(j+1,i+1),(j,i+1))])

    for side,center_index in (('L',0),('R',segments//2)):
        edge=[(low,j) for j in range(-span,span+1)]
        edge += [(i,span) for i in range(low+1,high+1)]
        edge += [(high,j) for j in range(span-1,-span-1,-1)]
        edge += [(i,-span) for i in range(high-1,low,-1)]
        previous=[i*segments+(j+center_index)%segments for i,j in edge]
        station,elbow,length=arm_geometry(c,side)
        first=.095
        center,tangent,across,outer=station(first)
        # Spread the armhole's upper and lower seam across a regular sleeve ring.
        delta=vertices[previous[0]]-center
        start=math.atan2(delta.dot(outer),delta.dot(across))
        regular=[start+math.tau*j/len(previous) for j in range(len(previous))]
        upper, forearm, clavicle=(f'{name}.{side}' for name in ('upper_arm','forearm','clavicle'))
        for index in previous:
            z=vertices[index].z
            lift=.13*smooth((z-armhole_low)/(armhole_high-armhole_low))
            skinning[index]=weights('chest',clavicle,lift)

        radii=[]
        section_count=23
        for i in range(section_count):
            t=i/(section_count-1)
            distance=mix(first,length-.011,t)
            center,tangent,across,outer=station(distance)
            base_radius=mix(.062,.032,smooth(t))
            if i>2:
                radius_y,radius_o=limb_radii(skin,center,tangent,(across,outer),.020,.10,
                                            (base_radius,base_radius*.91))
                radius_y=min(radius_y,base_radius+.019)
                radius_o=min(radius_o,base_radius+.020)
            else:
                radius_y,radius_o=base_radius,base_radius*.94
            radii.append((distance,radius_y,radius_o))
            ring=[]
            for angle in regular:
                bend=math.exp(-((distance-elbow)/.08)**2)
                ripple=(.0015+.0040*bend)*math.sin(7*angle-39*distance)
                ripple+=.0022*(1-t)*math.cos(3*angle+distance*45)
                ring.append(center+(radius_y+ripple)*math.cos(angle)*across+
                            (radius_o+ripple)*math.sin(angle)*outer)
            if not i:
                middle=[vertices[a].lerp(b,.49)+tangent*.010 for a,b in zip(previous,ring)]
                midpoint=len(vertices)
                vertices.extend(middle)
                skinning.extend([{'chest':.48,clavicle:.14,upper:.38}]*len(middle))
                following=list(range(midpoint,midpoint+len(middle)))
                for j in range(len(previous)):
                    nxt=(j+1)%len(previous)
                    faces.append((previous[j],previous[nxt],following[nxt],following[j]))
                    uvs.append([(j/len(previous),0),((j+1)/len(previous),0),
                                ((j+1)/len(previous),.035),(j/len(previous),.035)])
                previous=following
            end=len(vertices)
            vertices.extend(ring)
            bend=smooth((distance-elbow+.052)/.104)
            assignment=weights(upper,forearm,bend) if i>3 else weights('chest',upper,mix(.76,.98,i/3))
            skinning.extend([assignment]*len(ring))
            next_ring=list(range(end,end+len(ring)))
            low_uv=.035 if not i else .07+.93*(i-1)/(section_count-1)
            high_uv=.07+.93*t
            for j in range(len(previous)):
                nxt=(j+1)%len(previous)
                faces.append((previous[j],previous[nxt],next_ring[nxt],next_ring[j]))
                uvs.append([(j/len(previous),low_uv),((j+1)/len(previous),low_uv),
                            ((j+1)/len(previous),high_uv),(j/len(previous),high_uv)])
            previous=next_ring
        cuff_rings=[]
        for distance in (length-.071,length-.063,length-.048,length-.030,length-.015,length-.013):
            center,_,across,outer=station(distance)
            _,ry,ro=min(radii,key=lambda row: abs(row[0]-distance))
            shoulder_ease=.0044+(.0022 if length-.068<distance<length-.016 else 0)
            cuff_rings.append([center+(ry+shoulder_ease)*math.cos(angle)*across+
                (ro+shoulder_ease)*math.sin(angle)*outer for angle in regular])
        patch(c,f'{side} turned-back indigo cuff',cuff_rings,[forearm]*len(cuff_rings),liner,closed=True)
        for index in (1,4):
            c.tube(f'{side} cuff coutil edge {index}',cuff_rings[index],.0015,braid,forearm,cyclic=True)

    # The omitted armhole interior vertices are removed before UV assignment.
    used=sorted(set(index for face in faces for index in face))
    indexes={old:new for new,old in enumerate(used)}
    garment=c.mesh('Angarkha • continuous shoulders and body', [vertices[i] for i in used],
                   [tuple(indexes[i] for i in face) for face in faces],navy,[skinning[i] for i in used])
    make_uv(garment,lambda face: uvs[face.index])


def lapels(c, profile, lining, band, cord, closure):
    opening_rows=[]
    for i in range(32):
        t=i/31
        z=mix(1.511,.975,t)
        center=mix(.017,.147,math.sin(t*math.pi/2))+.009*math.sin(math.tau*t)
        width=mix(.020,.027,t)
        opening_rows.append([torso_face(profile,z,center+(s-.5)*width,-1,.012+.004*math.sin(math.pi*s))
                             for s in (0,.22,.50,.76,1)])
    binding_weights=[body_weights(row[0].z) for row in opening_rows]
    patch(c,'Angarkha • right crossover binding',opening_rows,binding_weights,lining,flip=True)
    c.tube('Angarkha • raised hand-set crossover seam',[row[0] for row in opening_rows],.0017,cord,binding_weights)
    for i in (13,18,23,26):
        point=opening_rows[i][1]
        bone=max(binding_weights[i],key=binding_weights[i].get)
        c.ovoid(f'Seated coat closure {i}',point+Vector((.010,-.003,0)),(.0056,.0039,.0062),closure,bone)
    collar=[]
    for i in range(6):
        t=i/5
        z=mix(1.485,1.568,t)
        _,cy,radius,depth=profile_at(profile,z)
        collar.append([(mix(.105,.081,t)*math.cos(angle),cy-.014*t+mix(depth+.006,.104,t)*math.sin(angle),
                        z-.017*t*max(0,-math.sin(angle))**7)
                       for angle in [math.tau*j/56 for j in range(56)]])
    patch(c,'Angarkha • sewn stand collar',collar,['chest']*len(collar),band,closed=True)
    c.tube('Collar • aged gilt cord',collar[-1],.00145,cord,'chest',cyclic=True)


def skirt(c, profile, navy, lining, cord):
    left,right=-math.pi/2-.105,-math.pi/2+.09
    for title,start,end,side in (('left overlap',right,math.pi/2+.03,'L'),
                                  ('right underlap',math.pi/2-.03,left+math.tau,'R')):
        rows=[]
        skinning=[]
        for i in range(33):
            t=i/32
            row=[]
            for j in range(49):
                u=j/48
                angle=mix(start,end,u)
                near_front=max(-math.sin(angle),0)
                bias=.035 if side=='L' else 0
                length=.327+bias-.089*near_front**6+.011*math.sin(angle*3+.5)
                z=.925-length*t
                cx,cy,rx,ry=profile_at(profile,.925)
                opening= (.047*t*t*.85 if side=='L' else -.027*t*t)*near_front**5
                angle+=opening
                fold=(.006+.004*t)*math.cos(8*angle+1.8*t)+.0038*math.cos(13*angle-4*t)
                radius_x=rx+.023+.083*t+fold
                radius_y=ry+.026+.062*t+fold
                row.append(Vector((cx+radius_x*math.cos(angle),cy+radius_y*math.sin(angle),z)))
            rows.append(row)
            skinning.append(weights('hips',f'thigh.{side}',.38*smooth(t)))
        patch(c,f'Angarkha • long {title}',rows,skinning,navy,flip=True)
        patch(c,f'Angarkha • folded hem {side}',[[p+Vector((0,0,-.001)) for p in row] for row in rows[-4:]],
              skinning[-4:],lining,flip=True)
        c.tube(f'Angarkha • side opening piping {side}',[row[0 if side=='L' else -1] for row in rows],
               .0018,cord,skinning)
        c.tube(f'Angarkha • bound lower hem {side}',rows[-1],.0015,cord,[skinning[-1]]*len(rows[-1]))


def sash(c, profile, ochre, edging, thread):
    rows=[]
    for i in range(36):
        t=i/35
        z=mix(.952,1.462,t)
        x=mix(.139,-.145,t)+.018*math.sin(math.pi*t)
        width=mix(.089,.132,smooth(t+.08))
        row=[]
        for j in range(17):
            u=j/16-.5
            zz=z+.038*u
            p=torso_face(profile,zz,x+width*u,-1,.024)
            p.y-=.0044*math.cos(3*math.tau*u+5*t)+.0021*math.sin(6*math.tau*u+3*t)
            row.append(p)
        rows.append(row)
    edge=rows[-1]
    for i in range(1,14):
        t=i/13
        row=[]
        for p in edge:
            z=p.z+.051*math.sin(math.pi*t)+.009*t
            y=mix(p.y,-p.y+.015,t)
            row.append(Vector((p.x-.013*math.sin(math.pi*t),y,z)))
        rows.append(row)
    for i in range(1,32):
        t=i/31
        z=mix(1.471,.996,t)
        center=mix(-.145,.135,t)+.007*math.sin(math.pi*t)
        row=[]
        for j in range(17):
            u=j/16-.5
            width=mix(.130,.085,t)
            p=torso_face(profile,z+.027*u,center+width*u,1,.025)
            p.y+=.005*math.sin(3*math.tau*u+t*7)
            row.append(p)
        rows.append(row)
    skinning=[body_weights(row[8].z) for row in rows]
    patch(c,'Sash • one continuous shoulder panel',rows,skinning,ochre)
    for name,start,end in (('outer',0,2),('inner',14,16)):
        border=[]
        for row in rows:
            side=-1 if row[8].y<0 else 1
            border.append([p+Vector((0,.0012*side,.0006)) for p in row[start:end+1]])
        patch(c,f'Sash • {name} woven border',border,skinning,edging)
        c.tube(f'Sash • {name} raised braid',[row[1] for row in border],.00135,thread,skinning)

    for r in range(5,34,4):
        for j in (5,8,11):
            lift=Vector((0,-.0019,0))
            motif=[rows[r-1][j],rows[r][j+1],rows[r+1][j],rows[r][j-1]]
            c.tube(f'Sash • diamond stitch {r}.{j}',[p+lift for p in motif],.00075,thread,
                   [skinning[r-1],skinning[r],skinning[r+1],skinning[r]],cyclic=True)


def belt(c, profile, leather, bronze, patina, thread):
    rows=[]
    for z,ease in ((.932,.016),(.935,.017),(.958,.019),(.988,.017),(.991,.015)):
        rows.append([coat_point(profile,z,math.tau*j/72,ease) for j in range(72)])
    patch(c,'Contoured leather waist belt',rows,['hips']*len(rows),leather,closed=True)
    for i in (1,3):
        c.tube(f'Belt • saddle stitching {i}',rows[i],.00165,thread,'hips',cyclic=True)
    z=.961
    y=coat_point(profile,z,-math.pi/2,.018).y-.004
    x=.072
    c.ovoid('Antique bronze buckle • low oval casting',(x,y,z),(.038,.011,.030),patina,'hips')
    c.ovoid('Buckle • raised inset bronze',(x,y-.0085,z),(.029,.005,.022),bronze,'hips')
    for n in (0,1):
        points=[(x+(.033-.006*n)*math.cos(t),y-.0094-.005*n,z+(.025-.004*n)*math.sin(t))
                for t in [math.tau*i/48 for i in range(48)]]
        c.tube(f'Buckle • deep set wire rim {n}',points,.0019 if not n else .0012,bronze,'hips',cyclic=True)
    for i in range(8):
        angle=math.tau*i/8
        endpoints=[(x+.006*math.cos(angle),y-.0148,z+.006*math.sin(angle)),
                   (x+.016*math.cos(angle+.20),y-.0148,z+.015*math.sin(angle+.20)),
                   (x+.021*math.cos(angle),y-.0135,z+.020*math.sin(angle))]
        c.tube(f'Buckle • chased petal {i+1}',endpoints,.0011,patina,'hips')
    c.ovoid('Buckle • dark central rivet',(x,y-.0148,z),(.0051,.0029,.0051),patina,'hips')


def dhoti(c, skin, cream, weave, antique):
    for side in ('L','R'):
        hip,knee,ankle=(joint(c,name,side) for name in ('hip','knee','ankle'))
        thigh,shin=(f'{name}.{side}' for name in ('thigh','shin'))
        rows=[]
        skinning=[]
        for i in range(33):
            t=i/32
            z=mix(ankle.z+.031,hip.z+.065,t)
            center=ankle.lerp(knee,min(1,(z-ankle.z)/(knee.z-ankle.z)))
            if z>knee.z:
                center=knee.lerp(hip,min(1,(z-knee.z)/(hip.z-knee.z)))
            center.z=z
            actual=limb_radii(skin,center,Vector((0,0,1)),(Vector((1,0,0)),Vector((0,1,0))),.024,
                              .14,(.041+.035*t,.044+.057*t))
            width=min(actual[0],.054+.046*t)+.016*math.sin(math.pi*t)+.003
            depth=min(actual[1],.056+.050*t)+.018*math.sin(math.pi*t)+.003
            tucked=smooth((t-.70)/.30)
            center.x*=1-.22*tucked
            width*=1-.32*tucked
            depth*=1-.23*tucked
            row=[]
            for j in range(72):
                angle=math.tau*j/72
                fall=.0055*math.cos(11*angle+1.5*t)+.0038*math.cos(19*angle-3.7*t)
                fall*=.68+.32*math.sin(math.pi*t)
                ankle_folds=.0055*math.exp(-((t-.09)/.085)**2)*math.cos(t*95+angle*2)
                radius=fall+ankle_folds+.0030*math.sin(5*angle-7*t)
                row.append(Vector((center.x+(width+radius)*math.cos(angle),
                                   center.y+(depth+radius)*math.sin(angle),z)))
            rows.append(row)
            knee_mix=smooth((z-knee.z+.095)/.18)
            skinning.append(weights(thigh,'hips',smooth((t-.81)/.28)) if t>.81 else weights(shin,thigh,knee_mix))
        patch(c,f'{side} gathered dhoti leg',rows,skinning,cream,closed=True)
        c.tube(f'{side} gathered ankle binding',rows[1],.0029,weave,shin,cyclic=True)
        c.tube(f'{side} antique thread at hem',rows[2],.00115,antique,shin,cyclic=True)


def jutti(c, skin, side, leather, sole, cord):
    ankle=joint(c,'ankle',side)
    bone=f'foot.{side}'
    sign=1 if side=='L' else -1
    points=[p for p in skin if .055<sign*p.x<.34 and -.012<p.z<.094]
    front=min((p.y for p in points),default=ankle.y-.212)-.018
    heel=max((p.y for p in points),default=ankle.y+.055)+.014
    cx=ankle.x+sign*.004
    rx=max((abs(p.x-cx) for p in points),default=.057)+.007
    rx=min(.084,rx)
    cy=(front+heel)/2
    length=(heel-front)/2
    outline=[]
    for j in range(72):
        angle=math.tau*j/72
        longitudinal=math.sin(angle)
        forepart=max(0,-longitudinal)
        contour=(.94+.13*forepart-.21*max(longitudinal,0)**2)
        x=cx+sign*forepart*.012+rx*math.cos(angle)*contour
        y=cy+length*longitudinal
        z=.007+.011*forepart**5
        outline.append((x,y,z,forepart))
    sole_rows=[[(x,y,z+height) for x,y,z,_ in outline] for height in (0,.005,.014,.018)]
    patch(c,f'{side} shaped jutti outsole',sole_rows,[bone]*4,sole,closed=True)
    upper=[]
    for i in range(21):
        t=i/21
        row=[]
        for x,y,z,forepart in outline:
            at_heel=max(0,(y-cy)/length)
            rise=.045+.019*at_heel-.010*forepart
            vz=z+.016+rise*(1-(1-t)**2)+.016*t**2
            row.append((mix(x,cx,t*.92),mix(y,ankle.y,t*.66),vz))
        upper.append(row)
    patch(c,f'{side} hand-lasted jutti upper',upper,[bone]*len(upper),leather,closed=True)
    c.tube(f'{side} jutti welt seam',sole_rows[-1],.0019,cord,bone,cyclic=True)
    vamp=[(cx+rx*math.cos(math.pi*j/26)*.75,
           front+.068-.022*math.sin(math.pi*j/26),.051+.025*math.sin(math.pi*j/26)) for j in range(27)]
    c.tube(f'{side} embroidered jutti vamp',vamp,.0016,cord,bone)


def dress(c):
    """Build the original hero wardrobe on the supplied weighted rest rig."""
    profile=list(c.landmarks.get('torso_profile',FITTING))
    profile.sort(key=lambda ring:ring[0])
    if profile[-1][0]<1.512:
        _,cx,cy,_,_=profile[-1]
        profile.append((1.518,cx,cy,.062,.071))
    skin_mesh=getattr(c,'skin_mesh',None)
    skin=[vertex.co.copy() for vertex in skin_mesh.data.vertices] if skin_mesh is not None else ()
    navy=fabric(c,'Midnight indigo angarkha',(.022,.044,.080),1.13,.094,.082)
    lining=fabric(c,'Faded indigo coat bindings',(.033,.055,.084),.92,.13,.067)
    collar=fabric(c,'Dark indigo stand collar',(.014,.028,.051),1.08,.11,.073)
    ochre=fabric(c,'Oxidized ochre brocade sash',(.238,.101,.032),1.21,.21,.106)
    edging=fabric(c,'Umber and ochre sash borders',(.113,.046,.019),.91,.14,.084)
    cream=fabric(c,'Ivory handloom dhoti',(.69,.604,.437),1.27,.108,.084,fine=False)
    washed=fabric(c,'Unbleached dhoti binding',(.49,.387,.242),1.02,.14,.067,fine=False)
    bronze=worn_hardware(c,'Aged bronze buckle',(.27,.137,.050),.72,.49,164)
    patina=worn_hardware(c,'Oxidized bronze recesses',(.067,.035,.017),.53,.62,202)
    leather=worn_hardware(c,'Dark saddle leather',(.056,.028,.016),0,.61,270)
    sole=worn_hardware(c,'Compressed leather sole',(.027,.014,.008),0,.79,197)
    gilt=c.mat('Dulled antique couching thread',(.305,.163,.055),.62,.32)
    thread=c.mat('Brown embroidery thread',(.38,.225,.087),.71,.12)

    first=len(c.parts)
    build_angarkha(c,profile,skin,navy,lining,gilt)
    lapels(c,profile,lining,collar,gilt,patina)
    skirt(c,profile,navy,lining,gilt)
    sash(c,profile,ochre,edging,thread)
    belt(c,profile,leather,bronze,patina,thread)
    dhoti(c,skin,cream,washed,gilt)
    for side in ('L','R'):
        jutti(c,skin,side,leather,sole,gilt)
    cloth={navy,lining,collar,ochre,edging,cream,washed}
    for part in c.parts[first:]:
        if any(material in cloth for material in part.data.materials):
            store_rest_positions(part.data)
