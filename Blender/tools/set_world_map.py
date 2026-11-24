"""Shared spatial map for the Chapter 1 sets.

Every set generator builds in these world coordinates, so the palace, the ghat,
the market and the boat can be linked into one Blender file and line up.
Units are metres. +X is east, +Y is north, +Z is up. Z = 0 is the ghat's upper
quay, which is also the level of the lower settlement.

This module has no Blender imports, so validation scripts and other set builders
can read the map without starting Blender.

Values marked GUESS are placeholders that the ghat / market set (sets 2 and 3)
is free to move. The palace only depends on the ghat steps and the water levels.
"""

from __future__ import annotations

from dataclasses import dataclass
import math


Vec2 = tuple[float, float]
Vec3 = tuple[float, float, float]


# ---------------------------------------------------------------------------
# Ghat steps and flood levels (story-critical)
# ---------------------------------------------------------------------------

QUAY_Z: float = 0.0
STEP_RISE: float = 0.40
STEP_TREAD: float = 0.70
STEP_COUNT: int = 14
GHAT_HALF_WIDTH: float = 16.0
GHAT_TOP_EDGE_Y: float = 0.0
GHAT_CENTER_X: float = 0.0
QUAY_DEPTH: float = 9.0

MORNING_VISIBLE_STEPS: int = 5
EVENING_VISIBLE_STEPS: int = 3


def step_top_z(step: int) -> float:
    """Top of tread `step`, counted from 1 directly below the quay."""
    return QUAY_Z - STEP_RISE * step


def step_front_y(step: int) -> float:
    """Front (river-side) edge of tread `step`."""
    return GHAT_TOP_EDGE_Y - STEP_TREAD * step


def water_level_for_visible_steps(visible: int) -> float:
    """Water surface that leaves exactly `visible` treads dry.

    The next tread down sits half a riser under the water, which keeps the
    count readable even with ripples.
    """
    return step_top_z(visible) - STEP_RISE * 0.5


MORNING_WATER_Z: float = water_level_for_visible_steps(MORNING_VISIBLE_STEPS)
EVENING_WATER_Z: float = water_level_for_visible_steps(EVENING_VISIBLE_STEPS)
# The night flood topped the quay. Silt and the high-water stain reach this height.
NIGHT_FLOOD_MARK_Z: float = 0.35


# ---------------------------------------------------------------------------
# River (placeholder course until set 2 is built)
# ---------------------------------------------------------------------------

RIVERBED_Z: float = -6.5
RIVER_HALF_WIDTH: float = 21.0
RIVER_BANK_WIDTH: float = 9.0
# The river runs east along the ghat, then bends south around the palace bluff.
RIVER_CENTERLINE: tuple[Vec2, ...] = (
    (-420.0, -36.0), (-160.0, -33.0), (-60.0, -31.0), (0.0, -31.0),
    (22.0, -38.0), (33.0, -58.0), (38.0, -110.0), (40.0, -200.0), (36.0, -420.0),
)


# ---------------------------------------------------------------------------
# Palace (set 1)
# ---------------------------------------------------------------------------

BLUFF_Z: float = 8.0
PALACE_FLOOR_Z: float = 10.0
"""World height of the palace plinth top, the palace's local Z = 0."""

PALACE_YAW_DEG: float = 54.0
"""Palace local +Y (the river façade with the ghat window) faces the ghat."""

JHAROKHA_LOCAL: Vec3 = (-27.0, 24.6, 0.0)
"""Front of the private chamber's ghat window bay, in palace local space."""

JHAROKHA_WORLD_TARGET: Vec2 = (48.0, -38.0)
"""Where that bay sits in the world: about 60 m from the ghat steps."""


def palace_rotate(local: Vec2) -> Vec2:
    yaw = math.radians(PALACE_YAW_DEG)
    x, y = local
    return (x * math.cos(yaw) - y * math.sin(yaw), x * math.sin(yaw) + y * math.cos(yaw))


def _palace_anchor() -> Vec3:
    rx, ry = palace_rotate((JHAROKHA_LOCAL[0], JHAROKHA_LOCAL[1]))
    return (JHAROKHA_WORLD_TARGET[0] - rx, JHAROKHA_WORLD_TARGET[1] - ry, PALACE_FLOOR_Z)


PALACE_ANCHOR: Vec3 = _palace_anchor()
"""World position of the palace's local origin (centre of the darbar floor)."""

PALACE_PLINTH_LOCAL: tuple[float, float, float, float] = (-34.0, 50.0, -24.0, 24.0)
"""Plinth top rectangle in palace local space: x_min, x_max, y_min, y_max."""


def palace_to_world(local: Vec3) -> Vec3:
    rx, ry = palace_rotate((local[0], local[1]))
    return (PALACE_ANCHOR[0] + rx, PALACE_ANCHOR[1] + ry, PALACE_ANCHOR[2] + local[2])


def world_to_palace(world: Vec3) -> Vec3:
    yaw = -math.radians(PALACE_YAW_DEG)
    x, y = world[0] - PALACE_ANCHOR[0], world[1] - PALACE_ANCHOR[1]
    return (x * math.cos(yaw) - y * math.sin(yaw), x * math.sin(yaw) + y * math.cos(yaw),
            world[2] - PALACE_ANCHOR[2])


# ---------------------------------------------------------------------------
# Story anchors for later sets
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MapAnchor:
    name: str
    location: Vec3
    certainty: str  # 'FIXED' when a built set depends on it, 'GUESS' otherwise
    note: str


ANCHORS: tuple[MapAnchor, ...] = (
    MapAnchor('Ghat | top step centre', (GHAT_CENTER_X, GHAT_TOP_EDGE_Y, QUAY_Z), 'FIXED',
              'Palace window camera counts treads below this edge.'),
    MapAnchor('Ghat | lifting gate (फाटक)', (-21.0, -1.0, 0.0), 'GUESS',
              'West end of the ghat, set into the low riverside wall.'),
    MapAnchor('Ghat | chowki lamp', (-18.6, 0.4, 2.1), 'GUESS',
              'Lamp ledge beside the gate; Gopal sees it from the boat.'),
    MapAnchor('Market | tall thatched roof ridge', (-38.0, 34.0, 9.0), 'GUESS',
              'Must hide the gate from the Halwai roof; check in set 3.'),
    MapAnchor('Settlement | Halwai roof eye', (-60.0, 78.0, 6.2), 'GUESS',
              'Sees the ghat over the market; the market roof must block the gate.'),
    MapAnchor('Palace | ghat window bay', (*JHAROKHA_WORLD_TARGET, PALACE_FLOOR_Z), 'FIXED',
              'Private chamber jharokha; fixed camera shows 5 then 3 treads.'),
)


def river_distance(x: float, y: float) -> float:
    """Horizontal distance from (x, y) to the river centreline."""
    best = math.inf
    points = RIVER_CENTERLINE
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        dx, dy = bx - ax, by - ay
        length_sq = dx * dx + dy * dy
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / length_sq))
        px, py = ax + t * dx, ay + t * dy
        best = min(best, math.hypot(x - px, y - py))
    return best
