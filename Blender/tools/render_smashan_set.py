"""Render review stills of SET_Smashan.blend to Blender/Previews/Sets/Smashan_*.png

  blender --background Blender/Sets/SET_Smashan.blend --python Blender/tools/render_smashan_set.py -- --percent 50 --samples 32
"""

import argparse
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Blender/Previews/Sets'
SHOTS = (('CAM | Banyan, branch and chabutra', 1, 'Smashan_Banyan_Branch_Chabutra'),
         ('CAM | Cloth and heels from the path', 1, 'Smashan_Cloth_Down'),
         ('CAM | Heels close', 60, 'Smashan_Heels_Cloth_Lifted'),
         ('CAM | Root seat', 1, 'Smashan_Root_Seat'),
         ('CAM | Top map (smashan)', 1, 'Smashan_Top_Map'))

parser = argparse.ArgumentParser()
parser.add_argument('--percent', type=int, default=50)
parser.add_argument('--samples', type=int, default=32)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])

scene = bpy.context.scene
scene.render.resolution_percentage = args.percent
scene.cycles.samples = args.samples
OUT.mkdir(parents=True, exist_ok=True)
for camera, frame, slug in SHOTS:
    scene.camera = bpy.data.objects[camera]
    scene.frame_set(frame)
    scene.render.filepath = str(OUT / f'{slug}.png')
    bpy.ops.render.render(write_still=True)
    print('Rendered', scene.render.filepath)
