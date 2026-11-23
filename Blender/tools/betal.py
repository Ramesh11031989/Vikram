"""Wardrobe and head details for Shyam Munshi, called Betal."""

from math import cos, hypot, pi, sin


SPEC = dict(
    name="Betal",
    height=0.96,
    skin=(0.365, 0.187, 0.101),
    hair=(0.061, 0.054, 0.049),
    iris=(0.112, 0.066, 0.032),
    face_width=0.93,
    nose_width=0.94,
)


def _shaft(c, name, rings, material, bone):
    """A short sleeve whose cross sections run along the arm."""
    segments = 24
    vertices = []
    for x, depth, height in rings:
        for step in range(segments):
            angle = 2 * pi * step / segments
            fold = 1 + 0.035 * cos(5 * angle + 4 * x)
            vertices.append((x, depth * cos(angle) * fold, 1.375 + height * sin(angle) * fold))

    faces = []
    for row in range(len(rings) - 1):
        for step in range(segments):
            start = row * segments + step
            end = row * segments + (step + 1) % segments
            faces.append((start, end, end + segments, start + segments))

    if rings[-1][0] < rings[0][0]:
        faces = [face[::-1] for face in faces]
    weights = bone if isinstance(bone, str) else [weight for weight in bone for _ in range(segments)]
    c.mesh(name, vertices, faces, material, weights)


def _dhoti_leg(c, side, sign, cloth, seam):
    """Longitudinal woven folds with blended knee and hip weights."""
    rings = [
        (0.215, 0.134, 0.071, 0.072, 0.008, f"shin.{side}"),
        (0.240, 0.137, 0.079, 0.081, 0.011, f"shin.{side}"),
        (0.415, 0.139, 0.095, 0.098, 0.008, f"shin.{side}"),
        (0.525, 0.139, 0.106, 0.112, 0.007, {f"thigh.{side}": 0.5, f"shin.{side}": 0.5}),
        (0.665, 0.130, 0.126, 0.124, -0.007, f"thigh.{side}"),
        (0.805, 0.123, 0.134, 0.13, -0.011, f"thigh.{side}"),
        (0.925, 0.105, 0.124, 0.122, -0.003, {"hips": 0.76, f"thigh.{side}": 0.24}),
        (0.997, 0.090, 0.106, 0.107, 0, "hips"),
    ]
    segments = 40
    vertices = []
    weights = []
    for row, (z, x, sx, sy, y, weight) in enumerate(rings):
        for step in range(segments):
            angle = 2 * pi * step / segments
            fold = 1 + 0.068 * cos(7 * angle + sign * (0.55 * row + 0.5))
            hem = 0.011 * sin(3 * angle + sign) / (row + 1)
            vertices.append((sign * x + sx * cos(angle) * fold, y + sy * sin(angle) * fold, z + hem))
            weights.append(weight)

    faces = []
    for row in range(len(rings) - 1):
        for step in range(segments):
            start = row * segments + step
            end = row * segments + (step + 1) % segments
            faces.append((start, end, end + segments, start + segments))
    c.mesh(f"Dhoti | pleated leg {side}", vertices, faces, cloth, weights)
    c.tube(f"Dhoti | woven hem {side}", vertices[:segments], 0.003, seam, f"shin.{side}", cyclic=True)


def _panel(c, name, rows, material, front):
    """Soft widthwise folds across an offset rectangular drape."""
    width_steps = 12
    vertices = []
    weights = []
    for left, right, weight in rows:
        for step in range(width_steps + 1):
            u = step / width_steps
            x, y, z = (a + (b - a) * u for a, b in zip(left, right))
            y += (-1 if front else 1) * 0.008 * sin(pi * u) * cos(7 * pi * u + 2 * z)
            vertices.append((x, y, z))
            weights.append(weight)

    stride = width_steps + 1
    faces = []
    for row in range(len(rows) - 1):
        for step in range(width_steps):
            start = row * stride + step
            face = (start, start + 1, start + stride + 1, start + stride)
            faces.append(face[::-1] if front else face)
    c.mesh(name, vertices, faces, material, weights)


def _hair_cap(c, material):
    segments = 56
    levels = 12
    vertices = [(0, -0.011, 1.817)]
    for level in range(1, levels + 1):
        for step in range(segments):
            angle = 2 * pi * step / segments
            back = abs(sin(angle / 2)) ** 1.65
            edge = 0.98 + 1.36 * back + 0.07 * cos(5 * angle) + 0.065 * sin(angle)
            polar = edge * level / levels
            ripple = 1 + 0.04 * sin(8 * angle + polar * 4) * sin(polar)
            vertices.append((
                0.128 * sin(angle) * sin(polar) * ripple,
                -0.010 - 0.115 * cos(angle) * sin(polar) * ripple,
                1.646 + 0.171 * cos(polar),
            ))

    faces = [(0, 1 + step, 1 + (step + 1) % segments) for step in range(segments)]
    for level in range(levels - 1):
        for step in range(segments):
            start = 1 + level * segments + step
            end = 1 + level * segments + (step + 1) % segments
            faces.append((start, start + segments, end + segments, end))
    c.mesh("Hair | uneven swept cap", vertices, faces, material, "head")


def _lock(c, name, path, widths, material):
    """Low sculpted waves with the long edge following the silhouette."""
    segments = 10
    vertices = []
    for index, (x, y, z) in enumerate(path):
        before = path[max(0, index - 1)]
        after = path[min(len(path) - 1, index + 1)]
        dx, dz = after[0] - before[0], after[2] - before[2]
        length = hypot(dx, dz)
        across_x, across_z = dz / length, -dx / length
        width = widths[index]
        for step in range(segments):
            angle = 2 * pi * step / segments
            across = width * cos(angle)
            vertices.append((x + across_x * across, y + 0.58 * width * sin(angle), z + across_z * across))

    faces = [tuple(reversed(range(segments)))]
    for row in range(len(path) - 1):
        for step in range(segments):
            start = row * segments + step
            end = row * segments + (step + 1) % segments
            faces.append((start, end, end + segments, start + segments))
    faces.append(tuple(range(len(vertices) - segments, len(vertices))))
    c.mesh(name, vertices, faces, material, "head")


def _groom(c):
    hair = c.m["hair"]
    salt = c.mat("Ash gray hair", (0.187, 0.173, 0.154), rough=0.89)
    mid = c.mat("Umber gray hair", (0.102, 0.090, 0.080), rough=0.92)
    _hair_cap(c, hair)

    locks = [
        ([(-0.075, -0.026, 1.779), (-0.041, -0.061, 1.803), (-0.004, -0.086, 1.791), (0.026, -0.105, 1.767), (0.058, -0.118, 1.744)], [0.006, 0.027, 0.024, 0.017, 0.002], mid),
        ([(-0.053, 0.018, 1.792), (-0.016, -0.029, 1.814), (0.041, -0.059, 1.802), (0.075, -0.083, 1.773), (0.093, -0.089, 1.733)], [0.004, 0.024, 0.025, 0.018, 0.002], hair),
        ([(0.001, 0.026, 1.808), (0.047, 0.009, 1.813), (0.089, -0.028, 1.787), (0.107, -0.047, 1.752), (0.118, -0.051, 1.716)], [0.003, 0.019, 0.023, 0.014, 0.002], mid),
        ([(-0.018, -0.089, 1.787), (-0.063, -0.094, 1.777), (-0.103, -0.082, 1.755), (-0.119, -0.060, 1.709), (-0.114, -0.063, 1.666)], [0.004, 0.022, 0.023, 0.018, 0.002], mid),
        ([(-0.065, 0.023, 1.789), (-0.103, 0.016, 1.766), (-0.126, -0.021, 1.730), (-0.133, -0.034, 1.671), (-0.111, -0.047, 1.632)], [0.005, 0.023, 0.023, 0.013, 0.002], salt),
        ([(0.075, 0.024, 1.779), (0.106, 0.019, 1.747), (0.127, -0.007, 1.703), (0.125, -0.024, 1.663), (0.105, -0.053, 1.625)], [0.005, 0.023, 0.026, 0.015, 0.002], mid),
        ([(0.094, 0.058, 1.735), (0.121, 0.053, 1.693), (0.128, 0.044, 1.635), (0.101, 0.071, 1.579)], [0.007, 0.025, 0.022, 0.003], hair),
        ([(-0.080, 0.073, 1.739), (-0.109, 0.067, 1.691), (-0.113, 0.069, 1.636), (-0.082, 0.078, 1.563)], [0.005, 0.024, 0.022, 0.002], hair),
    ]
    for index, (path, widths, material) in enumerate(locks, 1):
        _lock(c, f"Hair | swept lock {index:02}", path, widths, material)

    for name, path in [
        ("crown", [(-0.040, -0.063, 1.815), (-0.003, -0.089, 1.803), (0.027, -0.109, 1.775), (0.054, -0.122, 1.748)]),
        ("temple L", [(0.084, -0.041, 1.791), (0.108, -0.055, 1.758), (0.123, -0.056, 1.727), (0.126, -0.051, 1.692)]),
        ("temple R", [(-0.075, -0.095, 1.774), (-0.104, -0.094, 1.750), (-0.125, -0.072, 1.720), (-0.129, -0.067, 1.677)]),
    ]:
        c.tube(f"Hair | silver at {name}", path, 0.0026, salt, "head")

    for side, sign in (("L", 1), ("R", -1)):
        _lock(c, f"Beard | weathered cheek {side}", [
            (sign * 0.104, -0.061, 1.665), (sign * 0.101, -0.077, 1.619),
            (sign * 0.084, -0.082, 1.572), (sign * 0.058, -0.090, 1.526),
            (sign * 0.022, -0.088, 1.503),
        ], [0.003, 0.016, 0.017, 0.020, 0.004], mid)
        c.tube(f"Beard | gray wisp {side}", [
            (sign * 0.097, -0.089, 1.609), (sign * 0.082, -0.094, 1.564),
            (sign * 0.057, -0.104, 1.527), (sign * 0.027, -0.099, 1.504),
        ], 0.0020, salt, "head")
    c.ovoid("Beard | chin", (0, -0.060, 1.509), (0.052, 0.039, 0.038), mid, "head")


def dress(c):
    cloth = c.mat("Unbleached cotton", (0.500, 0.421, 0.314), rough=0.94)
    shawl = c.mat("Faded ivory shawl", (0.640, 0.568, 0.450), rough=0.92)
    seam = c.mat("Flax woven edge", (0.315, 0.247, 0.161), rough=0.94)
    tunic = c.mat("Woodsmoke tunic", (0.130, 0.117, 0.102), rough=0.94)
    belt = c.mat("Earth gray sash", (0.231, 0.180, 0.127), rough=0.92)

    c.loft("Tunic | woven torso", [
        (0.926, 0, 0.002, 0.207, 0.128),
        (1.004, 0, 0.002, 0.175, 0.110),
        (1.081, 0, 0.003, 0.157, 0.102),
        (1.164, 0, 0.004, 0.188, 0.113),
        (1.246, 0, 0.003, 0.204, 0.123),
        (1.338, 0, 0.006, 0.222, 0.109),
        (1.405, 0, 0.008, 0.207, 0.102),
        (1.447, 0, 0.010, 0.082, 0.070),
    ], tunic, ["hips", "hips", "spine", {"spine": 0.45, "chest": 0.55}, "chest", "chest", "chest", "chest"])

    for side, sign in (("L", 1), ("R", -1)):
        upper = f"upper_arm.{side}"
        _shaft(c, f"Tunic | rolled sleeve {side}", [
            (sign * 0.134, 0.049, 0.041), (sign * 0.182, 0.069, 0.056),
            (sign * 0.229, 0.083, 0.074), (sign * 0.275, 0.079, 0.072),
            (sign * 0.326, 0.072, 0.063), (sign * 0.374, 0.063, 0.056),
        ], tunic, ["chest", {"chest": 0.84, upper: 0.16}, {"chest": 0.44, upper: 0.56},
                   {"chest": 0.1, upper: 0.9}, upper, upper])
        _shaft(c, f"Tunic | seam at sleeve {side}", [
            (sign * 0.363, 0.067, 0.060), (sign * 0.379, 0.065, 0.058),
        ], belt, upper)
        _dhoti_leg(c, side, sign, cloth, seam)

    c.tube("Tunic | cross stitched neckline", [
        (-0.081, -0.056, 1.448), (-0.057, -0.083, 1.425), (-0.021, -0.102, 1.394),
        (0.022, -0.103, 1.395), (0.061, -0.081, 1.428), (0.082, -0.056, 1.448),
    ], 0.0042, seam, "chest")

    c.loft("Sash | folded waist wrap", [
        (0.932, -0.002, -0.001, 0.211, 0.132),
        (0.945, -0.003, 0, 0.211, 0.135),
        (0.985, 0.002, 0, 0.204, 0.129),
        (1.004, 0.008, 0, 0.182, 0.118),
    ], belt, "hips")
    c.tube("Sash | offset fold", [
        (-0.199, -0.035, 0.970), (-0.128, -0.116, 0.981), (-0.029, -0.135, 0.970),
        (0.075, -0.128, 0.954), (0.177, -0.086, 0.953),
    ], 0.006, seam, "hips")

    _panel(c, "Shawl | across the chest", [
        ((-0.188, -0.080, 1.453), (-0.069, -0.071, 1.459), "chest"),
        ((-0.202, -0.113, 1.366), (-0.058, -0.120, 1.402), "chest"),
        ((-0.123, -0.129, 1.233), (0.019, -0.135, 1.301), "chest"),
        ((-0.068, -0.116, 1.146), (0.089, -0.124, 1.208), "spine"),
        ((-0.005, -0.123, 1.039), (0.143, -0.117, 1.120), {"spine": 0.54, "hips": 0.46}),
        ((0.093, -0.125, 0.961), (0.206, -0.068, 1.002), "hips"),
    ], shawl, front=True)
    _panel(c, "Shawl | loose cloth down the back", [
        ((-0.203, -0.085, 1.440), (-0.069, -0.073, 1.459), "chest"),
        ((-0.204, 0.014, 1.472), (-0.068, 0.014, 1.472), "chest"),
        ((-0.206, 0.111, 1.381), (-0.068, 0.118, 1.407), "chest"),
        ((-0.185, 0.139, 1.239), (-0.030, 0.142, 1.273), "chest"),
        ((-0.172, 0.133, 1.136), (-0.028, 0.131, 1.143), "spine"),
        ((-0.168, 0.155, 1.030), (-0.023, 0.143, 1.046), {"spine": 0.6, "hips": 0.4}),
        ((-0.156, 0.167, 0.936), (-0.043, 0.153, 0.963), "hips"),
    ], shawl, front=False)

    c.ovoid("Sash | cloth knot", (0.157, -0.126, 0.962), (0.055, 0.030, 0.038), shawl, "hips", (0.2, -0.25, -0.35))
    _panel(c, "Shawl | uneven sash tail", [
        ((0.118, -0.154, 0.960), (0.189, -0.145, 0.959), "hips"),
        ((0.123, -0.158, 0.897), (0.197, -0.146, 0.912), "hips"),
        ((0.109, -0.159, 0.814), (0.186, -0.160, 0.837), {"hips": 0.73, "thigh.L": 0.27}),
        ((0.091, -0.164, 0.782), (0.178, -0.170, 0.787), {"hips": 0.53, "thigh.L": 0.47}),
    ], shawl, front=True)

    _groom(c)
