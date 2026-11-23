"""A distinct court clerk; this supporting character is not Shyam/Betal."""

from math import cos, sin, tau


SPEC = dict(name='CourtClerk', height=.96, skin=(.37,.20,.11),
            hair=(.027,.019,.014), iris=(.07,.034,.014), face_width=.97,
            nose_width=1.05, brow_lift=.001)


def dress(c):
    cotton=c.mat('Warm ivory court kurta',(.57,.50,.38),.91)
    trim=c.mat('Kurta seam',(.30,.25,.17),.91)
    trousers=c.mat('Muted umber trousers',(.22,.18,.13),.94)
    sash=c.mat('Clerk maroon waist cloth',(.19,.046,.036),.89)
    leather=c.mat('Simple leather shoes',(.078,.042,.021),.8)
    brass=c.mat('Spectacle brass',(.31,.19,.07),.45,.45)
    c.loft('Court kurta torso',[(.82,0,0,.21,.13),(.94,0,0,.21,.13),
        (1.08,0,0,.17,.11),(1.23,0,0,.20,.12),(1.38,0,0,.22,.10),
        (1.44,0,0,.075,.06)],cotton,['hips','hips','spine','chest','chest','chest'])
    for side,sign in (('L',1),('R',-1)):
        upper,lower=f'upper_arm.{side}',f'forearm.{side}'
        # Copy the arm's exact deformation weights so the garment cannot split
        # away from its skin when the writing IK bends the elbow.
        source=next(part for part in c.parts if part.name==f'{c.name}_Arm.{side}')
        sleeve=source.copy()
        sleeve.data=source.data.copy()
        sleeve.name=f'{c.name}_Kurta sleeve {side}'
        sleeve.data.materials.clear()
        sleeve.data.materials.append(cotton)
        for vertex in sleeve.data.vertices:
            vertex.co.y*=1.28
            vertex.co.z=1.375*c.scale+(vertex.co.z-1.375*c.scale)*1.28
        c.collection.objects.link(sleeve)
        c.parts.append(sleeve)
        cuff=[tuple(vertex.co/c.scale) for vertex in sleeve.data.vertices[-24:]]
        c.tube(f'Kurta cuff {side}',cuff,.003,trim,f'hand.{side}',cyclic=True)
        c.loft(f'Clerk trouser {side}',[(.13,sign*.135,0,.055,.05),
            (.5,sign*.135,0,.08,.075),(.75,sign*.125,0,.105,.10),
            (.95,sign*.1,0,.115,.12)],trousers,
            [f'shin.{side}',{f'shin.{side}':.5,f'thigh.{side}':.5},f'thigh.{side}','hips'])
        c.ovoid(f'Clerk shoe {side}',(sign*.135,-.057,.049),(.062,.12,.047),leather,f'foot.{side}')
        x=sign*.053*SPEC['face_width']
        c.tube(f'Fine spectacle frame {side}',[(x+.04*cos(tau*j/40),-.124,1.675+.026*sin(tau*j/40))
               for j in range(40)],.0017,brass,'head',cyclic=True)
    c.tube('Spectacle bridge',[(-.013,-.125,1.677),(0,-.132,1.687),(.013,-.125,1.677)],.0017,brass,'head')
    c.loft('Clerk waist sash',[(.92,0,0,.215,.137),(.98,0,0,.20,.135)],sash,'hips')
    for z in (1.38,1.34,1.30):
        c.ovoid(f'Kurta button {z}',(0,-.119,z),(.005,.004,.005),trim,'chest')
    c.ovoid('Clerk cropped hair',(0,.018,1.739),(.12,.105,.084),c.m['hair'],'head')
    c.ovoid('Clerk cloth cap',(0,.004,1.799),(.121,.105,.033),cotton,'head')
