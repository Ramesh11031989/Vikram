"""Render review stills of SET_Town.blend to Blender/Previews/Sets/Town_<camera>.png

  blender --background Blender/Sets/SET_Town.blend --python Blender/tools/render_town_set.py -- --percent 50 --samples 32
  Add --all for every camera; the default is the four story cameras.
"""

import argparse
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Blender/Previews/Sets'
STORY = ['Halwai roof eye to the ghat', 'Halwai west parapet to the cattle place',
         'Top map (town, market, ghat)', 'Mandi shed from lane B']

parser = argparse.ArgumentParser()
parser.add_argument('--all', action='store_true')
parser.add_argument('--percent', type=int, default=50)
parser.add_argument('--samples', type=int, default=32)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])

scene = bpy.context.scene
scene.render.resolution_percentage = args.percent
scene.cycles.samples = args.samples
OUT.mkdir(parents=True, exist_ok=True)
for cam in sorted((o for o in bpy.data.objects if o.type == 'CAMERA'), key=lambda o: o.name):
    short = cam.name.replace('CAM | ', '')
    if not args.all and short not in STORY:
        continue
    scene.camera = cam
    slug = ''.join(c if c.isalnum() else '_' for c in short).strip('_')
    scene.render.filepath = str(OUT / f'Town_{slug}.png')
    bpy.ops.render.render(write_still=True)
    print('Rendered', scene.render.filepath)
