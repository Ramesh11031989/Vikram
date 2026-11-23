"""Add non-destructive facial controls to the existing cast geometry."""

from __future__ import annotations

import math

import bpy
from mathutils import Vector


MOUTH_KEYS = ('Mouth_Ah', 'Mouth_O', 'Mouth_Ee', 'Mouth_MBP', 'Mouth_FV',
              'Mouth_U', 'Mouth_L', 'Mouth_Consonant')
VISEMES = {
    'A': {'Mouth_MBP': 1.0},
    'B': {'Mouth_Consonant': .85},
    'C': {'Mouth_Ah': .43, 'Mouth_Ee': .18},
    'D': {'Mouth_Ah': .82},
    'E': {'Mouth_O': .60},
    'F': {'Mouth_U': .90},
    'G': {'Mouth_FV': .85},
    'H': {'Mouth_L': .80},
    'X': {},
}


def property_control(rig, name: str, description: str) -> None:
    rig[name] = 0.0
    rig.id_properties_ui(name).update(min=0, max=1, soft_min=0, soft_max=1,
                                       description=description)


def driver_from_property(block, rig, name: str, expression: str = 'min(1,max(0,value))') -> None:
    curve = block.driver_add('value')
    driver = curve.driver
    driver.type = 'SCRIPTED'
    variable = driver.variables.new()
    variable.name = 'value'
    variable.type = 'SINGLE_PROP'
    variable.targets[0].id = rig
    variable.targets[0].data_path = f'["{name}"]'
    driver.expression = expression


def shape_from_delta(obj, name: str, transform):
    if obj.data.shape_keys is None:
        obj.shape_key_add(name='Basis')
    key = obj.shape_key_add(name=name)
    basis = obj.data.shape_keys.key_blocks['Basis']
    for destination, source in zip(key.data, basis.data):
        destination.co = transform(source.co.copy())
    return key


def add_facial_controls(character) -> None:
    rig, scale = character.rig, character.scale
    mouth = next(part for part in character.parts if part.name == f'{character.name}_Mouth')
    keys = mouth.data.shape_keys.key_blocks
    if mouth.data.shape_keys.animation_data:
        mouth.data.shape_keys.animation_data_clear()
    basis = keys['Basis']
    for name, sources in {
        'Mouth_U': {'Mouth_O': .9},
        'Mouth_L': {'Mouth_Ah': .58, 'Mouth_Ee': .15},
        'Mouth_Consonant': {'Mouth_Ee': .32, 'Mouth_Ah': .10},
    }.items():
        key = mouth.shape_key_add(name=name)
        for index, item in enumerate(key.data):
            point = basis.data[index].co.copy()
            for source, amount in sources.items():
                point += (keys[source].data[index].co-basis.data[index].co)*amount
            if name == 'Mouth_U':
                point.x *= .78
            item.co = point
    for name in MOUTH_KEYS:
        property_control(rig, name, f'Viseme control: {name}')
        keys[name].value = 0
        driver_from_property(keys[name], rig, name)
    for name in ('blink_L', 'blink_R', 'brow_raise', 'brow_frown', 'mouth_worry', 'mouth_smile'):
        property_control(rig, name, name.replace('_', ' '))

    for side in ('L', 'R'):
        # The refined cast combines pupil pigment with the iris and replaces
        # the separate upper lid with a continuous eyelid mesh. Keep the older
        # scene layout supported as well; require every part in either layout.
        refined_eye = f'{character.name}_Eyelids.{side}' in bpy.data.objects
        labels = ('Eye', 'Iris', 'Eyelids') if refined_eye else (
            'Eye', 'Iris', 'Pupil', 'Eye glint', 'Upper lid')
        for label in labels:
            obj = bpy.data.objects[f'{character.name}_{label}.{side}']
            def blink(point, eyelid=label in ('Upper lid', 'Eyelids')):
                point.z = 1.675*scale + (point.z-1.675*scale)*.035
                point.y += (-.003 if eyelid else .028)*scale
                return point
            key = shape_from_delta(obj, 'Blink', blink)
            driver_from_property(key, rig, f'blink_{side}')
        brow = bpy.data.objects[f'{character.name}_Brow.{side}']
        for name, delta, property_name in (('Raise', .0065, 'brow_raise'), ('Frown', -.005, 'brow_frown')):
            def reshape(point, amount=delta):
                weight = max(0.25, 1-abs(point.x)/(0.11*scale))
                point.z += amount*scale*weight
                return point
            key = shape_from_delta(brow, name, reshape)
            driver_from_property(key, rig, property_name)
    for name, sign, control in (('Worry', -1, 'mouth_worry'), ('Smile', 1, 'mouth_smile')):
        def corners(point, direction=sign):
            point.z += direction*.004*scale*min(1,abs(point.x)/(.034*scale))**2
            return point
        key = shape_from_delta(mouth, name, corners)
        driver_from_property(key, rig, control)
    rig['Facial_controls'] = 'Custom Properties: eight speech shapes, two blinks, brows, worry and smile. Eye bones control gaze.'
    rig['Lip_sync_method'] = 'Rhubarb phonetic acoustic visemes; automatic estimates requiring visual review.'
    add_mouth_interior(character, mouth)


def add_mouth_interior(character, mouth) -> None:
    teeth = character.mat('Upper teeth', (.66,.62,.51), .42)
    tongue = character.mat('Tongue', (.20,.053,.047), .63)
    for label, center, size, material, control in (
        ('Upper teeth', (0,-.128,1.576), (.026,.003,.004), teeth, 'Mouth_Ah'),
        ('Tongue', (0,-.127,1.553), (.018,.003,.003), tongue, 'Mouth_L'),
    ):
        obj = character.ovoid(label, center, size, material, 'head')
        # Hidden behind the face at rest; the show shape moves it into the mouth.
        for vertex in obj.data.vertices:
            vertex.co.y += .035*character.scale
        key = shape_from_delta(obj, 'Show', lambda point: point-Vector((0,.035*character.scale,0)))
        driver_from_property(key, character.rig, control, 'min(1,value*2.0)')


def key_property(rig, name: str, frame: float, value: float) -> None:
    rig[name] = value
    rig.keyframe_insert(data_path=f'["{name}"]', frame=frame)


def animate_visemes(character, timeline, lip_directory) -> int:
    import json

    rig = character.rig
    count = 0
    for name in MOUTH_KEYS:
        key_property(rig, name, 0, 0)
    for cue in timeline['cues']:
        if cue['speaker_id'] != character.name:
            continue
        data = json.loads((lip_directory/f"{cue['cue_id']}.json").read_text())
        offset = cue['start_frame']
        for name in MOUTH_KEYS:
            key_property(rig, name, offset-1, 0)
        for segment in data['mouthCues']:
            start = offset+segment['start']*timeline['fps']
            end = offset+segment['end']*timeline['fps']
            blend = min(1.4,(end-start)*.35)
            values = VISEMES[segment['value']]
            for name in MOUTH_KEYS:
                key_property(rig, name, start+blend, values.get(name,0))
                key_property(rig, name, max(start+blend,end-blend),values.get(name,0))
            count += 1
        for name in MOUTH_KEYS:
            key_property(rig, name, cue['end_frame_exclusive'], 0)
    return count


def animate_blinks(character, timeline, seed_offset: int) -> int:
    import random

    randomizer = random.Random(122+seed_offset)
    frame = 38+seed_offset
    count = 0
    while frame < timeline['total_frames']-10:
        for side in ('L','R'):
            name = f'blink_{side}'
            for delta,value in ((-2,0),(0,.95),(1,1),(3,0)):
                key_property(character.rig,name,frame+delta,value)
        count += 1
        frame += randomizer.randint(70,128)
    return count
