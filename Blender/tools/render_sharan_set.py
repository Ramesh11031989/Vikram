"""Render review stills of SET_Sharan.blend to Blender/Previews/Sets/Sharan_*.png

  blender --background Blender/Sets/SET_Sharan.blend --python Blender/tools/render_sharan_set.py -- --percent 50 --samples 32
"""

import argparse
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Blender/Previews/Sets'
SHOTS = (('CAM | Slope from the foot', 1, 'Sharan_Slope_From_Foot'),
         ("CAM | Seating and Gopal's place", 1, 'Sharan_Seating_Gopal'),
         ('CAM | Path up to the hut', 1, 'Sharan_Path_To_Hut'),
         ('CAM | Hut exterior', 1, 'Sharan_Hut_Exterior'),
         ('CAM | Door close', 1, 'Sharan_Door_Close'),
         ('CAM | Top map (sharan)', 1, 'Sharan_Top_Map'))

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
