from math import cos, pi, sin


SPEC = dict(
    name="Vikram",
    height=1.06,
    skin=(0.49, 0.251, 0.131),
    hair=(0.040, 0.021, 0.016),
    iris=(0.132, 0.064, 0.028),
    face_width=1.025,
    nose_width=0.95,
)


def band(c, name, center_x, z, width, radii, material, bone, center_y=0):
    radius_x, radius_y = radii
    c.loft(name, [
        (z - width / 2, center_x, center_y, radius_x * 0.988, radius_y * 0.985),
        (z, center_x, center_y, radius_x, radius_y),
        (z + width / 2, center_x, center_y, radius_x * 0.988, radius_y * 0.985),
    ], material, bone, cap=False)


def arm_loft(c, name, rings, sign, material, bone):
    segments = 24
    vertices = [
        (sign * x, radius_y * cos(a * 2 * pi / segments), z + radius_z * sin(a * 2 * pi / segments))
        for x, z, radius_y, radius_z in rings for a in range(segments)
    ]
    faces = [
        (index * segments + a, index * segments + (a + 1) % segments,
         (index + 1) * segments + (a + 1) % segments, (index + 1) * segments + a)
        for index in range(len(rings) - 1) for a in range(segments)
    ]
    faces.append(tuple(range(segments - 1, -1, -1)))
    faces.append(tuple(range(len(vertices) - segments, len(vertices))))
    if sign < 0:
        faces = [tuple(reversed(face)) for face in faces]
    weights = bone if isinstance(bone, str) else [weight for weight in bone for _ in range(segments)]
    c.mesh(name, vertices, faces, material, weights)


def cloth_strip(c, name, rows, material, edge):
    vertices = []
    weights = []
    for (x, y, z), width, bone in rows:
        vertices.extend((
            (x - width / 2, y + 0.007, z + width * 0.25),
            (x - width * 0.20, y - 0.003, z + width * 0.1),
            (x + width * 0.20, y - 0.008, z - width * 0.1),
            (x + width / 2, y + 0.004, z - width * 0.25),
        ))
        weights.extend([bone] * 4)
    faces = [(i + j, i + j + 4, i + j + 5, i + j + 1)
             for i in range(0, len(vertices) - 4, 4) for j in range(3)]
    c.mesh(name, vertices, faces, material, weights)
    for index, side in ((0, "outer"), (3, "inner")):
        ridge = []
        ridge_weights = []
        for row_index, (_, _, bone) in enumerate(rows):
            x, y, z = vertices[row_index * 4 + index]
            ridge.extend([(x - 0.003, y - 0.001, z), (x + 0.003, y - 0.001, z)])
            ridge_weights.extend([bone, bone])
        c.mesh(f"{name} {side} braid", ridge,
               [(i, i + 2, i + 3, i + 1) for i in range(0, len(ridge) - 2, 2)],
               edge, ridge_weights)


def medallion(c, name, center, radius, body, rim, gem, bone):
    x, y, z = center
    c.ovoid(f"{name} cast fitting", center, (radius, radius * 0.24, radius), body, bone)
    c.tube(f"{name} beaded rim", [
        (x + radius * 0.83 * cos(2 * pi * a / 32), y - radius * 0.145,
         z + radius * 0.83 * sin(2 * pi * a / 32)) for a in range(32)
    ], radius * 0.064, rim, bone, cyclic=True)
    for index in range(6):
        angle = index * pi / 3
        c.ovoid(f"{name} petal {index + 1}",
                (x + radius * 0.44 * sin(angle), y - radius * 0.22, z + radius * 0.44 * cos(angle)),
                (radius * 0.105, radius * 0.055, radius * 0.265), rim, bone, (0, angle, 0))
    c.ovoid(f"{name} stone", (x, y - radius * 0.30, z),
            (radius * 0.24, radius * 0.14, radius * 0.24), gem, bone)


def build_coat(c, cloth, trim, gold, cream, teal, dark_teal, garnet, bronze):
    c.loft("Tailored indigo jacket", [
        (0.920, 0, 0, .156, .099), (1.010, 0, 0, .145, .105),
        (1.094, 0, 0, .159, .113), (1.188, 0, 0, .197, .122),
        (1.290, 0, 0, .225, .112), (1.365, 0, 0, .211, .085),
        (1.407, 0, 0.002, .105, .061), (1.426, 0, 0.001, .067, .058),
    ], cloth, ["hips", {"hips": .70, "spine": .30}, "spine", {"spine": .45, "chest": .55},
               "chest", "chest", "chest", "chest"])
    c.loft("Undyed stand collar", [
        (1.392, 0, -.002, .081, .064), (1.414, 0, -.003, .070, .062),
        (1.441, 0, -.002, .060, .055),
    ], cream, "chest")
    band(c, "Collar gold border", 0, 1.439, .008, (.063, .057), gold, "chest", -.002)
    for sign, side in ((1, "L"), (-1, "R")):
        upper_arm = f"upper_arm.{side}"
        forearm = f"forearm.{side}"
        arm_loft(c, f"{side} jacket sleeve", [
            (.107, 1.338, .061, .052), (.156, 1.350, .075, .062),
            (.202, 1.360, .084, .074), (.243, 1.368, .087, .082),
            (.286, 1.373, .084, .079), (.346, 1.375, .077, .073),
            (.407, 1.375, .070, .066), (.425, 1.375, .070, .063),
        ], sign, cloth, ["chest", "chest", {"chest": .84, upper_arm: .16},
                         {"chest": .55, upper_arm: .45}, {"chest": .14, upper_arm: .86},
                         upper_arm, upper_arm, upper_arm])
        arm_loft(c, f"{side} sleeve woven cuff", [
            (.397, 1.375, .0715, .070), (.405, 1.375, .073, .071),
            (.428, 1.375, .072, .066),
        ], sign, trim, upper_arm)
        for x in (.406, .426):
            arm_loft(c, f"{side} sleeve gold border {x}", [
                (x - .003, 1.375, .074, .071), (x + .003, 1.375, .074, .071),
            ], sign, gold, upper_arm)
        arm_loft(c, f"{side} wrist leather wrap", [
            (.641, 1.375, .043, .043), (.650, 1.375, .046, .048),
            (.678, 1.375, .043, .046), (.688, 1.375, .042, .043),
        ], sign, bronze, forearm)
        for x in (.651, .681):
            arm_loft(c, f"{side} wrist brass edge {x}", [
                (x - .003, 1.375, .046, .049), (x + .003, 1.375, .046, .049),
            ], sign, gold, forearm)

    sash_rows = [
        ((-.176, -.074, 1.392), .092, "chest"), ((-.143, -.111, 1.349), .098, "chest"),
        ((-.087, -.134, 1.290), .093, "chest"), ((-.027, -.138, 1.227), .091, "chest"),
        ((.028, -.131, 1.162), .087, {"chest": .49, "spine": .51}),
        ((.079, -.119, 1.099), .079, "spine"), ((.123, -.100, 1.040), .077, {"spine": .33, "hips": .67}),
        ((.136, -.083, 1.008), .072, "hips"),
    ]
    cloth_strip(c, "Diagonal teal court sash", sash_rows, teal, gold)
    cloth_strip(c, "Sash fold", [((x + .010, y - .008, z), width * .22, bone)
                                for (x, y, z), width, bone in sash_rows], dark_teal, teal)
    rear_sash = [
        ((-.176, .065, 1.392), .092, "chest"), ((-.148, .102, 1.340), .099, "chest"),
        ((-.098, .125, 1.265), .094, "chest"), ((-.034, .132, 1.200), .090, "chest"),
        ((.028, .124, 1.147), .085, {"chest": .46, "spine": .54}),
        ((.083, .114, 1.082), .080, "spine"), ((.136, .081, 1.008), .072, "hips"),
    ]
    cloth_strip(c, "Sash across back", rear_sash, teal, gold)
    c.ovoid("Sash over shoulder", (-.174, 0, 1.419), (.055, .085, .019), teal, "chest")
    medallion(c, "Shoulder clasp", (-.149, -.125, 1.355), .025, bronze, gold, garnet, "chest")
    for index, z in enumerate((1.363, 1.331, 1.299)):
        c.ovoid(f"Collar button {index + 1}", (.050, -.110 - index * .004, z),
                (.008, .004, .008), gold, "chest")


def build_lower(c, pants, pants_dark, cloth, trim, gold, dark_teal, garnet, bronze):
    c.loft("Jacket skirt", [
        (.813, 0, -.003, .227, .141), (.833, 0, -.003, .231, .141),
        (.883, 0, -.002, .205, .132), (.934, 0, 0, .173, .120),
        (1.018, 0, 0, .149, .105),
    ], cloth, "hips", cap=False)
    band(c, "Jacket hem broad piping", 0, .822, .021, (.236, .146), trim, "hips", -.003)
    band(c, "Jacket hem metallic thread", 0, .813, .007, (.232, .144), gold, "hips", -.003)
    band(c, "Belt embossed leather", 0, .982, .080, (.167, .119), bronze, "hips")
    for z in (.949, 1.015):
        band(c, f"Belt brass rim {z}", 0, z, .008, (.170, .120), gold, "hips")
    medallion(c, "Belt seal-motif clasp", (0, -.125, .980), .041, bronze, gold, garnet, "hips")
    garment_folds = [
        ((.148, -.106, .971), .073, "hips"), ((.160, -.130, .913), .068, "hips"),
        ((.163, -.133, .853), .063, "hips"), ((.159, -.127, .796), .059, {"hips": .62, "thigh.L": .38}),
        ((.153, -.119, .742), .056, "thigh.L"),
    ]
    cloth_strip(c, "Tucked sash end", garment_folds, dark_teal, gold)
    for sign, side in ((1, "L"), (-1, "R")):
        thigh, shin, foot = f"thigh.{side}", f"shin.{side}", f"foot.{side}"
        c.loft(f"{side} pleated trousers", [
            (.146, sign * .137, 0, .044, .053), (.206, sign * .137, .003, .055, .063),
            (.326, sign * .137, .006, .066, .061), (.493, sign * .139, -.004, .073, .072),
            (.569, sign * .135, -.004, .082, .086), (.704, sign * .129, 0, .093, .100),
            (.861, sign * .105, 0, .083, .080), (.928, sign * .087, 0, .064, .068),
        ], pants, [shin, shin, shin, {shin: .80, thigh: .20}, {shin: .13, thigh: .87},
                   thigh, {thigh: .65, "hips": .35}, "hips"], segments=40)
        for fold in (-1, 0, 1):
            points = [(sign * .128 + fold * .042, -.102 + abs(fold) * .011, .776),
                      (sign * .131 + fold * .039, -.100 + abs(fold) * .012, .705),
                      (sign * .138 + fold * .031, -.094 + abs(fold) * .009, .628),
                      (sign * .140 + fold * .021, -.084 + abs(fold) * .006, .568)]
            c.tube(f"{side} trouser pleat {fold}", points, .0039, pants_dark, thigh)
        band(c, f"{side} trouser binding", sign * .137, .174, .025, (.052, .059), trim, shin)
        c.ovoid(f"{side} sole", (sign * .137, -.057, .038), (.067, .140, .032), bronze, foot)
        c.ovoid(f"{side} pointed court shoe", (sign * .137, -.056, .063),
                (.063, .127, .046), dark_teal, foot, (-.04, 0, 0))
        c.ovoid(f"{side} pointed toe", (sign * .137, -.161, .060),
                (.049, .061, .030), dark_teal, foot, (-.17, 0, 0))
        c.tube(f"{side} shoe gold seam", [
            (sign * .137 - .047, -.063, .073), (sign * .137 - .023, -.107, .091),
            (sign * .137, -.137, .091), (sign * .137 + .023, -.107, .091),
            (sign * .137 + .047, -.063, .073),
        ], .004, gold, foot)


def build_headwear(c, wrap, wrap_dark, wrap_light, gold, garnet, bronze):
    hair = c.m["hair"]
    c.ovoid("Short groomed rear hair", (0, .023, 1.672), (.121, .099, .115), hair, "head")
    for sign, side in ((1, "L"), (-1, "R")):
        c.ovoid(f"{side} sideburn", (sign * .110, -.019, 1.650),
                (.018, .040, .056), hair, "head", (0, sign * .13, 0))
        c.ovoid(f"{side} earring stud", (sign * .129, -.036, 1.613), (.016, .013, .016), gold, "head")

    c.loft("Wrapped imperial turban", [
        (1.742, -.006, .004, .116, .100), (1.769, -.007, .003, .138, .116),
        (1.809, -.009, .004, .148, .119), (1.851, -.013, .011, .128, .104),
        (1.878, -.020, .020, .081, .071), (1.889, -.022, .025, .039, .037),
    ], wrap, "head", segments=48)

    for index, z in enumerate((1.763, 1.793, 1.822, 1.850)):
        rz = (.120, .139, .145, .115)[index]
        ry = (.107, .118, .116, .097)[index]
        points = [(-.011 + rz * cos(2 * pi * a / 48), .007 + ry * sin(2 * pi * a / 48),
                   z + (.011 + index * .002) * cos(2 * pi * a / 48 + .25)) for a in range(48)]
        c.tube(f"Turban wrap ridge {index + 1}", points, .0075 if index in (1, 2) else .0055,
               wrap_dark if index % 2 == 0 else wrap_light, "head", cyclic=True)
    c.tube("Turban leading gold cord", [
        (-.008 + .137 * cos(2 * pi * a / 64), .004 + .116 * sin(2 * pi * a / 64),
         1.777 + .017 * cos(2 * pi * a / 64 - .4)) for a in range(64)
    ], .0030, gold, "head", cyclic=True)
    medallion(c, "Turban jewel", (-.023, -.115, 1.807), .030, bronze, gold, garnet, "head")
    c.ovoid("Turban tucked fold", (.097, .011, 1.843), (.047, .084, .034),
            wrap_light, "head", (0, -.25, -.14))


def build_beard(c):
    hair = c.m["hair"]
    beard_glint = c.mat("Warm beard strands", (.061, .031, .021), .94)
    beard_rows = [
        (1.491, .049, -.049, .044), (1.506, .079, -.049, .055),
        (1.523, .093, -.047, .069), (1.543, .103, -.046, .072),
        (1.573, .112, -.030, .073), (1.608, .115, -.019, .079),
    ]
    steps = 28
    verts = []
    for row, (z, rx, cy, ry) in enumerate(beard_rows):
        for index in range(steps + 1):
            u = index / steps
            angle = (u - .5) * pi * 1.08
            center_dip = (max(0, cos(angle)) ** 1.6) * (.043 if row == 5 else .022 if row == 4 else 0)
            x = rx * sin(angle)
            y = cy - ry * cos(angle) - .006
            verts.append((x, y, z - center_dip))
    faces = [(r * (steps + 1) + i, r * (steps + 1) + i + 1,
              (r + 1) * (steps + 1) + i + 1, (r + 1) * (steps + 1) + i)
             for r in range(len(beard_rows) - 1) for i in range(steps)]
    c.mesh("Trim beard jaw shell", verts, faces, hair, "head")
    for index in range(15):
        a = index + 7
        start = verts[2 * (steps + 1) + a]
        end = verts[3 * (steps + 1) + a]
        c.tube(f"Beard cut groove {index + 1}", [(start[0], start[1] - .0015, start[2] + .003),
                                                 (end[0], end[1] - .0015, end[2] - .001)],
               .0012, beard_glint, "head")
    for sign, side in ((1, "L"), (-1, "R")):
        c.tube(f"{side} neat moustache", [(sign * .008, -.132, 1.590),
                                         (sign * .021, -.135, 1.587),
                                         (sign * .036, -.129, 1.585),
                                         (sign * .052, -.121, 1.587)], .0055, hair, "head")


def dress(c):
    indigo = c.mat("Indigo handloom jacket", (.043, .087, .161), .83)
    trim = c.mat("Dark indigo border", (.027, .044, .090), .81)
    gold = c.mat("Antique gilt thread", (.655, .368, .110), .40, .50)
    cream = c.mat("Undyed collar", (.765, .602, .385), .87)
    teal = c.mat("Kingfisher court sash", (.048, .247, .230), .80)
    dark_teal = c.mat("Muted green silk folds", (.028, .159, .134), .84)
    garnet = c.mat("Dark garnet setting", (.452, .049, .033), .37, .16)
    bronze = c.mat("Burnished brass and leather", (.257, .110, .044), .55, .27)
    pants = c.mat("Sand-coloured cotton trousers", (.530, .417, .263), .90)
    pants_dark = c.mat("Shadowed cotton folds", (.360, .273, .161), .90)
    wrap = c.mat("Deep teal turban cloth", (.033, .181, .185), .87)
    wrap_dark = c.mat("Deep teal wrap seams", (.025, .120, .127), .86)
    wrap_light = c.mat("Teal wrap highlights", (.065, .246, .235), .84)

    build_coat(c, indigo, trim, gold, cream, teal, dark_teal, garnet, bronze)
    build_lower(c, pants, pants_dark, indigo, trim, gold, dark_teal, garnet, bronze)
    build_headwear(c, wrap, wrap_dark, wrap_light, gold, garnet, bronze)
    build_beard(c)
