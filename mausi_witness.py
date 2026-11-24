"""
गवाह: लड़के की मौसी (Witness - the boy's maternal aunt)

Usage (Blender 3.x / 4.x):
  blender --background --python mausi_witness.py -- slope
  blender --background --python mausi_witness.py -- interrogation
  blender --background --python mausi_witness.py -- both

Scenes:
  slope          - शरण की ढलान पर गोपाल के पास बैठी हुई मौसी
  interrogation  - पूछताछ में खड़ी मौसी
  both           - दोनों एक ही फ़ाइल में, अगल-बगल

IMPORTANT: दोनों दृश्यों में मौसी की पोशाक (COSTUME) बिल्कुल एक जैसी है,
ताकि दर्शक उसे पहचान सके। पोशाक के रंग सिर्फ़ COSTUME में बदलें।
"""
import math
import os
import sys

import bpy
from mathutils import Vector

# ---------------------------------------------------------------- costume
COSTUME = {
    "saree": (0.60, 0.06, 0.10, 1.0),         # गहरी लाल साड़ी
    "saree_border": (0.95, 0.75, 0.15, 1.0),  # सुनहरा किनारा
    "blouse": (0.10, 0.25, 0.55, 1.0),        # नीला ब्लाउज़
    "dupatta": (0.95, 0.60, 0.10, 1.0),       # केसरिया दुपट्टा
    "bangles": (0.90, 0.80, 0.20, 1.0),       # चूड़ियाँ
    "skin": (0.55, 0.36, 0.25, 1.0),
    "hair": (0.40, 0.40, 0.42, 1.0),          # अधेड़ उम्र: सफ़ेद-काले बाल
    "dark": (0.03, 0.03, 0.03, 1.0),          # आँखें
    "bindi": (0.70, 0.0, 0.0, 1.0),
}

_mat_cache = {}


def mat(name, color=None, rough=0.7):
    if name in _mat_cache:
        return _mat_cache[name]
    color = color or COSTUME[name]
    m = bpy.data.materials.new("M_" + name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = rough
    m.diffuse_color = color
    _mat_cache[name] = m
    return m


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mat_cache.clear()


# ---------------------------------------------------------------- helpers
def _finish(obj, material, parent, smooth=True):
    obj.data.materials.append(material)
    if smooth:
        for p in obj.data.polygons:
            p.use_smooth = True
    if parent:
        obj.parent = parent
    return obj


def sphere(name, loc, scale, material, parent):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    return _finish(o, material, parent)


def cyl(name, loc, radius, depth, material, parent, r2=None):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=radius, depth=depth, location=loc)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=radius, radius2=r2, depth=depth, location=loc)
    o = bpy.context.object
    o.name = name
    return _finish(o, material, parent)


def box(name, loc, size, material, parent):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    return _finish(o, material, parent, smooth=False)


def limb(name, p1, p2, radius, material, parent):
    """दो बिंदुओं के बीच बेलन (parent के local निर्देशांक)।"""
    a, b = Vector(p1), Vector(p2)
    d = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=radius, depth=d.length, location=(a + b) / 2)
    o = bpy.context.object
    o.name = name
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    return _finish(o, material, parent)


# ---------------------------------------------------------------- character
def build_mausi(pose="standing", location=(0, 0, 0), rot=(0, 0, 0)):
    """
    pose: "standing" | "sitting"
    root का origin ज़मीन/बैठने की सतह पर है। खड़ी होने पर कद ~1.55 मी।
    पोशाक दोनों poses में वही materials इस्तेमाल करती है।
    """
    root = bpy.data.objects.new("Mausi_" + pose, None)
    bpy.context.collection.objects.link(root)

    skin, hair = mat("skin"), mat("hair")
    saree, border = mat("saree"), mat("saree_border")
    blouse, dupatta = mat("blouse"), mat("dupatta")
    bangles = mat("bangles", rough=0.3)

    if pose == "standing":
        waist_z, shoulder_z, head_z = 0.85, 1.27, 1.46
        cyl("Saree_Skirt", (0, 0, 0.45), 0.33, 0.90, saree, root, r2=0.20)
        cyl("Saree_Border", (0, 0, 0.03), 0.335, 0.06, border, root)
        sphere("Foot_L", (-0.09, 0.07, 0.03), (0.05, 0.10, 0.03), skin, root)
        sphere("Foot_R", (0.09, 0.07, 0.03), (0.05, 0.10, 0.03), skin, root)
        arm_l = [(-0.19, 0, shoulder_z - 0.02), (-0.27, 0.02, 0.95), (-0.24, 0.10, 0.80)]
        arm_r = [(0.19, 0, shoulder_z - 0.02), (0.27, 0.02, 0.95), (0.24, 0.10, 0.80)]
    else:
        waist_z, shoulder_z, head_z = 0.30, 0.60, 0.80
        sphere("Saree_Lap", (0, 0.12, 0.14), (0.34, 0.42, 0.14), saree, root)
        cyl("Saree_Hip", (0, 0, 0.17), 0.27, 0.34, saree, root, r2=0.22)
        limb("Leg_L", (-0.12, 0.10, 0.14), (-0.14, 0.55, 0.10), 0.12, saree, root)
        limb("Leg_R", (0.12, 0.10, 0.14), (0.14, 0.55, 0.10), 0.12, saree, root)
        sphere("Foot_L", (-0.14, 0.62, 0.09), (0.05, 0.09, 0.04), skin, root)
        sphere("Foot_R", (0.14, 0.62, 0.09), (0.05, 0.09, 0.04), skin, root)
        arm_l = [(-0.19, 0, shoulder_z - 0.02), (-0.24, 0.12, 0.38), (-0.14, 0.30, 0.28)]
        arm_r = [(0.19, 0, shoulder_z - 0.02), (0.24, 0.12, 0.38), (0.14, 0.30, 0.28)]

    # धड़ + ब्लाउज़
    torso_h = shoulder_z - waist_z
    torso_mid = (shoulder_z + waist_z) / 2
    cyl("Torso_Blouse", (0, 0, torso_mid), 0.19, torso_h, blouse, root, r2=0.16)
    sphere("Shoulders", (0, 0, shoulder_z - 0.03), (0.21, 0.12, 0.07), blouse, root)

    # साड़ी का पल्लू (पीठ पर लटकता) + सुनहरा किनारा
    box("Pallu", (0, -0.17, torso_mid - 0.02), (0.36, 0.03, torso_h + 0.25), saree, root)
    box("Pallu_Border", (0, -0.19, torso_mid - 0.10), (0.36, 0.035, 0.05), border, root)

    # गर्दन और सिर
    cyl("Neck", (0, 0, shoulder_z + 0.04), 0.045, 0.12, skin, root)
    sphere("Head", (0, 0, head_z), (0.105, 0.115, 0.13), skin, root)
    sphere("Nose", (0, 0.115, head_z - 0.01), (0.018, 0.03, 0.025), skin, root)
    sphere("Eye_L", (-0.04, 0.10, head_z + 0.025), (0.012, 0.01, 0.012), mat("dark"), root)
    sphere("Eye_R", (0.04, 0.10, head_z + 0.025), (0.012, 0.01, 0.012), mat("dark"), root)
    sphere("Bindi", (0, 0.113, head_z + 0.06), (0.011, 0.006, 0.011), mat("bindi"), root)
    sphere("Hair", (0, -0.02, head_z + 0.03), (0.11, 0.11, 0.115), hair, root)
    sphere("Bun", (0, -0.12, head_z), (0.06, 0.06, 0.06), hair, root)
    # सिर पर केसरिया दुपट्टा (पहचान का मुख्य रंग)
    sphere("Head_Cover", (0, -0.03, head_z + 0.045), (0.118, 0.12, 0.105), dupatta, root)
    box("Dupatta_Drape", (0, -0.11, (shoulder_z + head_z) / 2 - 0.02),
        (0.30, 0.05, (head_z - shoulder_z) + 0.25), dupatta, root)

    # हाथ + चूड़ियाँ
    for side, pts in (("L", arm_l), ("R", arm_r)):
        limb("UpperArm_" + side, pts[0], pts[1], 0.04, blouse, root)
        limb("ForeArm_" + side, pts[1], pts[2], 0.035, skin, root)
        sphere("Hand_" + side, pts[2], (0.04, 0.045, 0.04), skin, root)
        v = Vector(pts[2]) - Vector(pts[1])
        for i in range(4):
            p = Vector(pts[2]) - v.normalized() * (0.06 + i * 0.014)
            b = cyl("Bangle_%s_%d" % (side, i), tuple(p), 0.04, 0.008, bangles, root)
            b.rotation_mode = 'QUATERNION'
            b.rotation_quaternion = v.to_track_quat('Z', 'Y')

    root.location = location
    root.rotation_euler = rot
    return root


def build_gopal_stub(location, rot=(0, 0, 0)):
    """गोपाल का सरल placeholder (मौसी से अलग रंग, सिर्फ़ संदर्भ के लिए)।"""
    root = bpy.data.objects.new("Gopal_placeholder", None)
    bpy.context.collection.objects.link(root)
    shirt = mat("gopal_shirt", (0.15, 0.45, 0.20, 1.0))
    pants = mat("gopal_pants", (0.85, 0.85, 0.80, 1.0))
    skin = mat("skin")
    hairm = mat("gopal_hair", (0.03, 0.03, 0.03, 1.0))
    cyl("G_Torso", (0, 0, 0.45), 0.2, 0.5, shirt, root)
    limb("G_Leg_L", (-0.1, 0, 0.15), (-0.12, 0.55, 0.10), 0.1, pants, root)
    limb("G_Leg_R", (0.1, 0, 0.15), (0.12, 0.55, 0.10), 0.1, pants, root)
    cyl("G_Neck", (0, 0, 0.74), 0.045, 0.1, skin, root)
    sphere("G_Head", (0, 0, 0.85), (0.11, 0.12, 0.13), skin, root)
    sphere("G_Hair", (0, -0.02, 0.90), (0.115, 0.115, 0.10), hairm, root)
    root.location = location
    root.rotation_euler = rot
    return root


# ---------------------------------------------------------------- scenes
def add_light_and_world():
    bpy.ops.object.light_add(type='SUN', location=(4, -4, 8))
    sun = bpy.context.object
    sun.data.energy = 3.5
    sun.rotation_euler = (math.radians(50), 0, math.radians(35))
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.55, 0.70, 0.90, 1.0)
        bg.inputs[1].default_value = 1.0


def add_camera(loc, target):
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.object
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = cam
    return cam


def slope_scene(offset=(0, 0, 0)):
    """शरण की ढलान: झुकी घास; मौसी गोपाल के पास बैठी।
    ढलान x-अक्ष के गिर्द झुकी है (+y की ओर ऊपर)।"""
    ox, oy, oz = offset
    angle = math.radians(18)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(ox, oy, oz))
    ground = bpy.context.object
    ground.name = "Sharan_Slope"
    ground.scale = (8, 8, 1)
    ground.rotation_euler = (-angle, 0, 0)
    ground.data.materials.append(mat("grass", (0.20, 0.45, 0.15, 1.0), rough=0.95))

    # -angle घूर्णन पर plane का local +y ऊपर की ओर उठता है
    def on_slope(x, y):
        return (ox + x, oy + y * math.cos(angle), oz + y * math.sin(angle))

    # किरदार ढलान के नीचे (-y) की ओर मुँह करके बैठते हैं
    down = math.radians(180)
    build_mausi("sitting", location=on_slope(0.0, 0.0),
                rot=(-angle, 0, down + math.radians(20)))
    build_gopal_stub(on_slope(-0.85, 0.1), rot=(-angle, 0, down - math.radians(15)))


def interrogation_scene(offset=(0, 0, 0)):
    """पूछताछ: साधारण कमरा; मौसी (वही पोशाक) खड़ी होकर बयान देती हुई।"""
    ox, oy, oz = offset
    bpy.ops.mesh.primitive_plane_add(size=1, location=(ox, oy, oz))
    floor = bpy.context.object
    floor.name = "Interrogation_Floor"
    floor.scale = (6, 6, 1)
    floor.data.materials.append(mat("floor", (0.45, 0.35, 0.28, 1.0)))
    box("Interrogation_Wall", (ox, oy - 3, oz + 1.5), (6, 0.1, 3),
        mat("wall", (0.85, 0.82, 0.72, 1.0)), None)
    box("Table", (ox + 1.2, oy + 0.2, oz + 0.4), (0.9, 0.5, 0.8),
        mat("wood", (0.30, 0.18, 0.08, 1.0)), None)
    build_mausi("standing", location=(ox - 0.2, oy, oz), rot=(0, 0, math.radians(15)))


def main():
    argv = sys.argv
    mode = "both"
    if "--" in argv and len(argv) > argv.index("--") + 1:
        mode = argv[argv.index("--") + 1]
    out_dir = os.path.dirname(os.path.abspath(__file__))

    reset_scene()
    add_light_and_world()

    if mode == "slope":
        slope_scene()
        add_camera((-3.0, -3.5, 2.0), (0, 0, 0.5))
    elif mode == "interrogation":
        interrogation_scene()
        add_camera((2.5, 4.5, 1.6), (0, 0, 0.9))
    else:
        slope_scene(offset=(-5, 0, 0))
        interrogation_scene(offset=(5, 0, 0))
        add_camera((0, 14, 4), (0, 0, 0.8))

    blend_path = os.path.join(out_dir, "mausi_witness_%s.blend" % mode)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print("Saved:", blend_path)


if __name__ == "__main__":
    main()
