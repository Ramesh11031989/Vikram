"""Signed-distance sculpting for realistic cast heads.

A head is described as an ordered list of soft shapes (ellipsoids, tapered
capsules, custom fields) combined with smooth union and smooth subtraction,
evaluated on a voxel grid with numpy and meshed with surface nets. The same
operation list can be evaluated at arbitrary points, which lets other parts
(eyelids, brows, jewellery) sit exactly on the sculpted skin.

Only numpy and Blender's own modules are used, so the build runs inside a
stock Blender.
"""

from __future__ import annotations

import math
from typing import Callable, List, Sequence, Tuple

import numpy as np
from mathutils import Euler

Array = np.ndarray
Field = Callable[[Array, Array, Array], Array]
Bounds = Tuple[Sequence[float], Sequence[float]]


# ----------------------------------------------------------------- blending

def smin(a: Array, b: Array, k: float) -> Array:
    """Polynomial smooth minimum: a soft union whose fillet is about k wide."""
    if k <= 0:
        return np.minimum(a, b)
    h = np.clip(.5 + .5*(b - a)/k, 0, 1)
    return b + (a - b)*h - k*h*(1 - h)


def smax(a: Array, b: Array, k: float) -> Array:
    return -smin(-a, -b, k)


def rotation(degrees: Sequence[float]) -> Array:
    """3x3 matrix whose columns are the shape's local axes in world space."""
    return np.array(Euler(tuple(math.radians(v) for v in degrees), 'XYZ').to_matrix())


# --------------------------------------------------------------- primitives

def ellipsoid(centre: Sequence[float], radii: Sequence[float],
              turn: Sequence[float] | None = None, bend: float = 0.0) -> Tuple[Field, Bounds]:
    """Approximate ellipsoid distance (Quilez). `bend` curves the shape back along y by bend*x²."""
    cx, cy, cz = centre
    rx, ry, rz = radii
    m = rotation(turn) if turn else None

    def field(x: Array, y: Array, z: Array) -> Array:
        dx, dy, dz = x - cx, y - cy - bend*(x - cx)**2, z - cz
        if m is not None:
            dx, dy, dz = (m[0, 0]*dx + m[1, 0]*dy + m[2, 0]*dz,
                          m[0, 1]*dx + m[1, 1]*dy + m[2, 1]*dz,
                          m[0, 2]*dx + m[1, 2]*dy + m[2, 2]*dz)
        k0 = np.sqrt((dx/rx)**2 + (dy/ry)**2 + (dz/rz)**2)
        k1 = np.sqrt((dx/(rx*rx))**2 + (dy/(ry*ry))**2 + (dz/(rz*rz))**2)
        return k0*(k0 - 1)/np.maximum(k1, 1e-9)

    reach = max(radii)
    lo = (cx - reach, cy - reach, cz - reach)
    hi = (cx + reach, cy + reach + bend*reach*reach, cz + reach)
    return field, (lo, hi)


def capsule(a: Sequence[float], b: Sequence[float], ra: float, rb: float) -> Tuple[Field, Bounds]:
    """Tapered capsule between two points (radius blends linearly along the axis)."""
    ax, ay, az = a
    bx, by, bz = b[0] - ax, b[1] - ay, b[2] - az
    length2 = bx*bx + by*by + bz*bz

    def field(x: Array, y: Array, z: Array) -> Array:
        px, py, pz = x - ax, y - ay, z - az
        h = np.clip((px*bx + py*by + pz*bz)/length2, 0, 1)
        dx, dy, dz = px - bx*h, py - by*h, pz - bz*h
        return np.sqrt(dx*dx + dy*dy + dz*dz) - (ra + (rb - ra)*h)

    r = max(ra, rb)
    lo = tuple(min(p, q) - r for p, q in zip(a, b))
    hi = tuple(max(p, q) + r for p, q in zip(a, b))
    return field, (lo, hi)


def sphere(centre: Sequence[float], radius: float) -> Tuple[Field, Bounds]:
    cx, cy, cz = centre

    def field(x: Array, y: Array, z: Array) -> Array:
        return np.sqrt((x - cx)**2 + (y - cy)**2 + (z - cz)**2) - radius

    return field, (tuple(c - radius for c in centre), tuple(c + radius for c in centre))


# ------------------------------------------------------------------ sculpt

class Sculpt:
    """An ordered list of soft boolean operations, evaluable on a grid or at points."""

    OUTSIDE = .05

    def __init__(self) -> None:
        self.ops: List[Tuple[str, Field, Array, Array, float]] = []

    def _add(self, op: str, shape: Tuple[Field, Bounds], k: float) -> None:
        field, (lo, hi) = shape
        pad = 2*k + .002
        self.ops.append((op, field, np.array(lo) - pad, np.array(hi) + pad, k))

    def union(self, shape: Tuple[Field, Bounds], k: float = 0.0) -> None:
        self._add('union', shape, k)

    def subtract(self, shape: Tuple[Field, Bounds], k: float = 0.0) -> None:
        self._add('subtract', shape, k)

    @staticmethod
    def _combine(op: str, current: Array, d: Array, k: float) -> Array:
        if op == 'union':
            return smin(current, d, k)
        return smax(current, -d, k)

    def points(self, p: Array) -> Array:
        """Field value at an (N, 3) array of points."""
        values = np.full(len(p), self.OUTSIDE)
        for op, field, lo, hi, k in self.ops:
            inside = np.all((p >= lo) & (p <= hi), axis=1)
            if not inside.any():
                continue
            q = p[inside]
            values[inside] = self._combine(op, values[inside], field(q[:, 0], q[:, 1], q[:, 2]), k)
        return values

    def grid(self, lo: Sequence[float], hi: Sequence[float], step: float) -> Tuple[Array, Array]:
        """Field sampled on a regular grid; returns (values, origin)."""
        origin = np.array(lo, dtype=np.float64)
        count = np.ceil((np.array(hi) - origin)/step).astype(int) + 1
        values = np.full(tuple(count), self.OUTSIDE, dtype=np.float32)
        axes = [origin[i] + step*np.arange(count[i]) for i in range(3)]
        for op, field, olo, ohi, k in self.ops:
            span = []
            for i in range(3):
                a = max(0, int(math.floor((olo[i] - origin[i])/step)))
                b = min(count[i], int(math.ceil((ohi[i] - origin[i])/step)) + 1)
                span.append(slice(a, b))
            if any(s.start >= s.stop for s in span):
                continue
            x = axes[0][span[0]][:, None, None]
            y = axes[1][span[1]][None, :, None]
            z = axes[2][span[2]][None, None, :]
            block = values[tuple(span)]
            d = field(x, y, z)
            values[tuple(span)] = self._combine(op, block, np.broadcast_to(d, block.shape), k)
        return values, origin

    def surface_along(self, origins: Array, directions: Array, near: float, far: float,
                      step: float = .00015) -> Array:
        """Distance along each ray to the outermost exit from the solid (nan where none)."""
        t = np.arange(near, far, step)
        samples = origins[:, None, :] + directions[:, None, :]*t[None, :, None]
        values = self.points(samples.reshape(-1, 3)).reshape(len(origins), len(t))
        inside = values < 0
        exits = inside[:, :-1] & ~inside[:, 1:]
        last = np.where(exits.any(axis=1), exits.shape[1] - 1 - np.argmax(exits[:, ::-1], axis=1), -1)
        result = np.full(len(origins), np.nan)
        ok = last >= 0
        i = last[ok]
        rows = np.nonzero(ok)[0]
        f0, f1 = values[rows, i], values[rows, i + 1]
        result[ok] = t[i] + step*f0/(f0 - f1)
        return result


# ------------------------------------------------------------ surface nets

def surface_nets(values: Array, origin: Array, step: float) -> Tuple[Array, Array]:
    """Quad mesh of the zero level set (inside is negative). Returns (verts, quads)."""
    inside = values < 0
    nx, ny, nz = values.shape
    corners = np.zeros((nx - 1, ny - 1, nz - 1), dtype=np.uint8)
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                corners += inside[dx:nx - 1 + dx, dy:ny - 1 + dy, dz:nz - 1 + dz]
    active = (corners > 0) & (corners < 8)
    del corners
    cell_id = np.full(active.shape, -1, dtype=np.int32)
    cells = np.nonzero(active)
    count = len(cells[0])
    cell_id[cells] = np.arange(count, dtype=np.int32)
    total = np.zeros((count, 3))
    hits = np.zeros(count)
    quads = []
    cell_shape = active.shape
    for axis in range(3):
        lower = [slice(None)]*3
        upper = [slice(None)]*3
        lower[axis] = slice(0, -1)
        upper[axis] = slice(1, None)
        f0 = values[tuple(lower)]
        f1 = values[tuple(upper)]
        crossing = (f0 < 0) != (f1 < 0)
        edges = np.nonzero(crossing)
        a, b = f0[edges].astype(np.float64), f1[edges].astype(np.float64)
        t = a/(a - b)
        position = np.stack(edges, axis=1).astype(np.float64)
        position[:, axis] += t
        others = [i for i in range(3) if i != axis]
        corner_ids = []
        for d1, d2 in ((1, 1), (0, 1), (0, 0), (1, 0)):
            index = [edges[0].copy(), edges[1].copy(), edges[2].copy()]
            index[others[0]] -= d1
            index[others[1]] -= d2
            valid = ((index[others[0]] >= 0) & (index[others[0]] < cell_shape[others[0]]) &
                     (index[others[1]] >= 0) & (index[others[1]] < cell_shape[others[1]]) &
                     (index[axis] < cell_shape[axis]))
            ids = np.full(len(t), -1, dtype=np.int64)
            ids[valid] = cell_id[index[0][valid], index[1][valid], index[2][valid]]
            corner_ids.append(ids)
            good = ids >= 0
            for c in range(3):
                total[:, c] += np.bincount(ids[good], weights=position[good, c], minlength=count)
            hits += np.bincount(ids[good], minlength=count)
        ring = np.stack(corner_ids, axis=1)
        complete = np.all(ring >= 0, axis=1)
        ring = ring[complete]
        inward = (a[complete] < 0)
        flip = inward if axis == 1 else ~inward
        ring[flip] = ring[flip][:, ::-1]
        quads.append(ring)
    verts = origin + step*total/np.maximum(hits, 1)[:, None]
    return verts, np.concatenate(quads)


def taubin(verts: Array, quads: Array, rounds: int = 3, lam: float = .5, mu: float = -.53,
           pinned: Array | None = None) -> Array:
    """Volume-preserving smoothing to take the voxel stair-steps out of a surface-nets mesh."""
    edges = np.concatenate([quads[:, [0, 1]], quads[:, [1, 2]], quads[:, [2, 3]], quads[:, [3, 0]]])
    edges = np.concatenate([edges, edges[:, ::-1]])
    degree = np.bincount(edges[:, 0], minlength=len(verts)).astype(np.float64)
    degree[degree == 0] = 1
    v = verts.copy()
    for _ in range(rounds):
        for factor in (lam, mu):
            mean = np.stack([np.bincount(edges[:, 0], weights=v[edges[:, 1], c], minlength=len(v))
                             for c in range(3)], axis=1)/degree[:, None]
            move = factor*(mean - v)
            if pinned is not None:
                move[pinned] = 0
            v += move
    return v
