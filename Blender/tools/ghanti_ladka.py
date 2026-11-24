"""गवाह: घंटी सुनने वाला लड़का (the boy who heard the bell). Spec and costume.

He heard the bell himself and got Nandu's name from his aunt (मौसी).
A younger boy, about 10-11 years and 1.28 m: smaller than every adult in the
cast, with a rounder face, a short broad nose and a cropped haircut.

Costume: a washed sky-blue cotton kurta with a rippled body, rolled hem,
mandarin collar, button placket with thread-ringed bone buttons, patch pocket,
a mended ochre chest patch, turned sleeve cuffs and dashed hand-stitching;
earth-brown knee shorts with folds, rolled cuffs, a stitched knee patch and a
gathered waistband; a strand-fibre cropped haircut and fibre eyebrows.  Every
fabric uses the shared woven textile shader.  The patches, pocket and stitching
are guesses for the director to confirm.
"""

import random

import bpy
from mathutils import Vector

from ghanti_hair import crop_hair
from ghanti_kurta import body as kurta_body
from ghanti_kurta_details import collar, placket
from ghanti_kurta_extras import pockets_and_patch, sleeves
from ghanti_shorts import knee_patch, legs, waistband
from textile import finish_fabric, store_rest_positions


SPEC = dict(name='GhantiLadka', height=.67, skin=(.43,.225,.118), hair=(.024,.016,.012),
            iris=(.075,.04,.02), face_width=.93, nose_width=.82, brow_lift=.003)

HEAD_SCALE = 1.32
HEAD_BONES = {'head', 'eye.L', 'eye.R'}

# Label (the text after "GhantiLadka • ") -> fine weave?
FABRICS = {'Washed sky-blue cotton': False, 'Undyed cotton edge': False,
           'Earth-brown shorts cloth': False, 'Mended ochre patch': False}


def weave(c):
    finished = set()
    for part in c.parts:
        fabric = False
        for material in part.data.materials:
            label = material.name.partition(' • ')[2]
            if label in FABRICS:
                fabric = True
                if material not in finished:
                    finish_fabric(material, FABRICS[label])
                    node = next(n for n in material.node_tree.nodes if n.type == 'GROUP')
                    node.inputs['Thread pitch (mm)'].default_value = 3.1
                    node.inputs['Yarn contrast'].default_value = .20
                    finished.add(material)
        if fabric:
            store_rest_positions(part.data)


def childlike_head(c):
    """Enlarge the head about the neck joint so he has child proportions.

    The shared body is an adult shape; a uniform scale would only make a small
    adult. Meshes weighted only to head/eye bones, their shape keys and the head
    and eye bones are scaled together, so skinning and phoneme shapes stay valid.
    """
    pivot = Vector((0, -.013, 1.5)) * c.scale
    for obj in c.parts:
        if {group.name for group in obj.vertex_groups} <= HEAD_BONES:
            for vertex in obj.data.vertices:
                vertex.co = pivot + (vertex.co - pivot) * HEAD_SCALE
            keys = obj.data.shape_keys
            if keys:
                for block in keys.key_blocks:
                    for point in block.data:
                        point.co = pivot + (point.co - pivot) * HEAD_SCALE
            obj.data.update()
    bpy.context.view_layer.objects.active = c.rig
    bpy.ops.object.mode_set(mode='EDIT')
    for name in HEAD_BONES:
        bone = c.rig.data.edit_bones[name]
        bone.head = pivot + (bone.head - pivot) * HEAD_SCALE
        bone.tail = pivot + (bone.tail - pivot) * HEAD_SCALE
    bpy.ops.object.mode_set(mode='OBJECT')


def dress(c):
    m = dict(
        cloth=c.mat('Washed sky-blue cotton', (.235, .355, .43), .90),
        trim=c.mat('Undyed cotton edge', (.62, .55, .42), .88),
        shorts=c.mat('Earth-brown shorts cloth', (.22, .145, .085), .93),
        patch=c.mat('Mended ochre patch', (.50, .33, .085), .92),
        thread=c.mat('Cream cotton thread', (.74, .68, .55), .75),
        button=c.mat('Bone button', (.68, .62, .50), .45),
    )
    kurta_body(c, m)
    placket(c, m)
    collar(c, m)
    pockets_and_patch(c, m)
    sleeves(c, m)
    legs(c, m)
    knee_patch(c, m)
    waistband(c, m)
    crop_hair(c, random.Random(1129))
    weave(c)
