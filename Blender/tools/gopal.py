from math import cos, pi, sin, tau


HEAD_WRAP_RINGS = (
    (1.727,0,.001,.133,.113), (1.737,0,.001,.140,.117),
    (1.756,0,.001,.140,.117), (1.767,0,.001,.136,.112),
)

SPEC = dict(name='Gopal', height=1.0, skin=(.402,.205,.103), hair=(.048,.027,.016),
            iris=(.085,.048,.024), face_width=1.11, nose_width=1.15, brow_lift=-.002,
            head_wrap=HEAD_WRAP_RINGS)


def vest(c, cloth, edge):
    c.loft('River-blue sleeveless vest', [(.914,0,.003,.191,.116),(.98,0,.004,.173,.115),
           (1.091,0,.008,.161,.111),(1.191,0,.005,.189,.118),(1.283,0,.001,.217,.115),
           (1.358,0,.003,.217,.090),(1.411,0,.007,.099,.067),(1.425,0,.008,.059,.051)], cloth,
           ['hips','hips','spine',{'spine':.45,'chest':.55},'chest','chest','chest','chest'])
    c.tube('Open-neck stitching', [(-.061,-.048,1.422),(-.063,-.086,1.381),(-.04,-.101,1.341),
           (0,-.119,1.296),(.04,-.101,1.341),(.063,-.086,1.381),(.061,-.048,1.422)],
           .005,edge,'chest')
    c.tube('Vest closing seam', [(0,-.120,1.291),(.016,-.125,1.241),(.044,-.119,1.187),
           (.063,-.113,1.13),(.064,-.106,1.075)], .0035,edge,
           ['chest','chest',{'chest':.6,'spine':.4},'spine','spine'])
    for index, z in enumerate((1.277,1.237,1.197)):
        c.ovoid(f'Tied vest closure {index+1}', (.012+index*.019,-.121,z),(.013,.008,.008),edge,'chest')
    for sign, side in ((1,'L'),(-1,'R')):
        upper = f'upper_arm.{side}'
        sections = ((.140,1.365,.055,.037),(.165,1.366,.067,.068),
                    (.197,1.369,.074,.076),(.222,1.372,.076,.074),
                    (.252,1.374,.072,.068),(.280,1.375,.068,.066))
        rings = [[(sign*x, sign*depth*cos(tau*j/28), z+height*sin(tau*j/28)) for j in range(28)]
                 for x,z,depth,height in sections]
        c.ring_mesh(f'Vest arm gusset {side}',rings,cloth,
                    ['chest','chest',{'chest':.73,upper:.27},{'chest':.44,upper:.56},upper,upper])
        c.tube(f'Woven shoulder binding {side}', rings[-1],.005,edge,upper,cyclic=True)


def trousers(c, cotton, edge, mud):
    for sign, side in ((1,'L'),(-1,'R')):
        thigh = f'thigh.{side}'
        shin = f'shin.{side}'
        shapes = [(.284,.134,.065,.067),(.305,.134,.075,.079),(.445,.135,.084,.09),
                  (.528,.134,.09,.092),(.661,.127,.105,.105),(.785,.124,.113,.117),
                  (.913,.110,.113,.12),(.986,.095,.111,.12)]
        rings = []
        for idx, (z,x,rx,ry) in enumerate(shapes):
            ring = []
            for j in range(36):
                angle = tau*j/36
                ripple = 1 + .085*cos(7*angle + idx*.36*sign)
                ring.append((sign*x+rx*cos(angle)*ripple,ry*sin(angle)*ripple,
                             z+.008*cos(angle*3)/(idx+1)))
            rings.append(ring)
        c.ring_mesh(f'Rolled cotton trouser {side}',rings,cotton,
                    [shin,shin,shin,{shin:.47,thigh:.53},thigh,thigh,{thigh:.64,'hips':.36},'hips'])
        c.tube(f'Rolled trouser stitching {side}',rings[1],.006,edge,shin,cyclic=True)
        for i in range(12):
            angle = i*2.399
            c.ovoid(f'Dried silt {side} {i+1}', (sign*.135+cos(angle)*(.042+i*.00054),
                    .0007*i+sin(angle)*(.043+i*.00062), .185+i*.0079),
                    (.005+i*.0003,.0013,.007-i*.00017), mud, shin, (0,.11*i,angle-pi/2))


def dress(c):
    river = c.mat('Faded river blue',(.045,.186,.209),.86)
    trim = c.mat('Sun-bleached binding',(.285,.335,.28),.87)
    cotton = c.mat('Hemp trouser cloth',(.303,.235,.142),.95)
    belt = c.mat('Dark umber waist wrap',(.138,.083,.054),.87)
    sash = c.mat('Cinnamon shoulder cloth',(.364,.155,.066),.87)
    thread = c.mat('Oat thread',(.58,.427,.251),.88)
    mud = c.mat('Dried river silt',(.236,.162,.099),.95)
    vest(c,river,trim)
    trousers(c,cotton,thread,mud)
    c.loft('Waist wrap',[(.916,0,0,.20,.127),(.948,0,0,.202,.13),(.991,0,0,.182,.124),
           (1.012,0,0,.169,.116)],belt,'hips')
    c.tube('Waist wrap fold', [(.189*cos(tau*j/40),.128*sin(tau*j/40),.954+.011*cos(tau*j/40))
           for j in range(40)],.005,cotton,'hips',cyclic=True)
    c.ovoid('Wrap knot',(-.101,-.12,.949),(.038,.028,.023),belt,'hips',(0,-.28,.1))
    rows = [(.683,.134,-.141,.041),(.799,.131,-.152,.047),(.952,.145,-.146,.046),
            (1.138,.158,-.119,.048),(1.29,.162,-.127,.055),(1.390,.148,-.108,.056),
            (1.449,.145,-.068,.056),(1.465,.142,.006,.055),(1.435,.144,.068,.058),
            (1.348,.151,.112,.06),(1.18,.139,.133,.06),(1.014,.134,.127,.054)]
    weights = ['thigh.L',{'thigh.L':.57,'hips':.43},'hips','spine','chest','chest',
               'chest','chest','chest','chest','spine','hips']
    verts = [(x+(t-.5)*width*2,y-.005*cos(t*tau*2),z + (t-.5)*.017)
             for z,x,y,width in rows for t in (0,.25,.5,.75,1)]
    faces = [(i+j,i+j+1,i+5+j+1,i+5+j) for i in range(0,len(verts)-5,5) for j in range(4)]
    c.mesh('Working shoulder cloth',verts,faces,sash,[w for w in weights for _ in range(5)])
    for side,index in (('inner',0),('outer',4)):
        c.tube(f'Shoulder cloth woven edge {side}',verts[index::5],.0027,thread,weights)

    hair = c.m['hair']
    c.ovoid('Cropped hair at back',(0,.029,1.689),(.135,.102,.118),hair,'head')
    c.ovoid('Brushed hair cap',(-.006,-.001,1.765),(.129,.106,.057),hair,'head',(0,.10,0))
    for k in range(8):
        x = -.103 + k*.026
        c.tube(f'Brushed hair ridge {k+1}',[(x,-.083,1.749+.015*sin(k*.52)),
               (x-.009,-.093,1.776+.012*sin(k*.55)),(x-.022,-.054,1.796+.017*sin(k*.55)),
               (x-.024,.016,1.801+.010*sin(k*.54))], [.004,.007,.009,.004],hair,'head')
    c.loft('Indigo head wrap',HEAD_WRAP_RINGS,river,'head',segments=48,cap=False)
    for z,x,y,rx,ry in (HEAD_WRAP_RINGS[0],HEAD_WRAP_RINGS[-1]):
        c.tube(f'Head wrap seam {z}',[(x+rx*cos(tau*j/48),y+ry*sin(tau*j/48),z)
               for j in range(48)],.0025,trim,'head',cyclic=True)
    c.ovoid('Head wrap rear knot',(.094,.100,1.745),(.038,.029,.022),river,'head',(0,.28,.15))
    for sign, side in ((1,'L'),(-1,'R')):
        c.tube(f'Weathered moustache {side}',[(sign*.008,-.130,1.59),(sign*.025,-.136,1.588),
               (sign*.041,-.131,1.581),(sign*.055,-.121,1.575)], [.004,.0065,.006,.0025],hair,'head')
        c.ovoid(f'Cropped sideburn {side}',(sign*.126,-.013,1.656),(.012,.024,.033),hair,'head')
    c.ovoid('Small river-brass earring',(-.139,-.019,1.606),(.011,.006,.014),
            c.mat('River brass',(.38,.221,.074),.46,.58),'head')
