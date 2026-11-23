"""Realistic head-to-body proportion for new cast built on the shared Character.

The shared Character head is about 5.75 heads tall overall (stylised). Ramesh's
direction for all new cast (2026-11-23) is realistic proportion like the Vikram
reference: about 7+ heads. `realistic_head` shrinks everything that rides only on
the head and eyes (skull, face, ears, eyes, mouth, groom, head wrap, every shape
key) about the base of the skull, and moves the head and eye bones to match. It
runs after the character is fully built, so face shapes and grooms are unchanged
relative to the face.
"""

from __future__ import annotations

from mathutils import Vector


HEAD_BASE_Z = 1.50      # head bone head (unscaled)
CHIN_Z = 1.497          # lowest point of the shared skull profile
CROWN_Z = 1.812         # top of the shared skull profile
REALISTIC_HEAD = .76    # 5.75 heads → about 7.3 heads
HEAD_GROUPS = ('head', 'eye.L', 'eye.R')


def head_z(z: float, factor: float = REALISTIC_HEAD) -> float:
    """Where an unscaled face height ends up after the head is shrunk (still unscaled)."""
    return HEAD_BASE_Z + (z - HEAD_BASE_Z)*factor


def heads_tall(factor: float = REALISTIC_HEAD) -> float:
    return head_z(CROWN_Z, factor) / ((CROWN_Z - CHIN_Z)*factor)


def height_for(target_metres: float, factor: float = REALISTIC_HEAD) -> float:
    """Character SPEC['height'] that puts the crown at target_metres after shrinking the head."""
    return target_metres / head_z(CROWN_Z, factor)


def _scale(point: Vector, pivot: Vector, factor: float) -> Vector:
    return pivot + (point - pivot)*factor


def realistic_head(c, factor: float = REALISTIC_HEAD) -> int:
    """Shrink head-only geometry and bones about the skull base. Returns vertices moved."""
    import bpy

    pivot = Vector((0, -.013, HEAD_BASE_Z))*c.scale
    moved = 0
    for part in c.parts:
        names = {group.index: group.name for group in part.vertex_groups}
        on_head = []
        for vertex in part.data.vertices:
            weight = sum(item.weight for item in vertex.groups if names.get(item.group) in HEAD_GROUPS)
            on_head.append(weight > .999)
        if not any(on_head):
            continue
        blocks = part.data.shape_keys.key_blocks if part.data.shape_keys else ()
        for index, flag in enumerate(on_head):
            if not flag:
                continue
            part.data.vertices[index].co = _scale(part.data.vertices[index].co, pivot, factor)
            for block in blocks:
                block.data[index].co = _scale(block.data[index].co, pivot, factor)
            moved += 1
        part.data.update()
        if part.data.attributes.get('TextileRest'):
            from textile import store_rest_positions
            store_rest_positions(part.data)

    rig = c.rig
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    for name in HEAD_GROUPS:
        bone = rig.data.edit_bones[name]
        bone.head = _scale(bone.head, pivot, factor)
        bone.tail = _scale(bone.tail, pivot, factor)
    bpy.ops.object.mode_set(mode='OBJECT')
    rig['Proportion'] = f'Realistic head: {heads_tall(factor):.1f} heads tall (head scale {factor})'
    return moved
