"""Quick EEVEE review stills of the town set (finishes in seconds, unlike Cycles on this scene).

  blender --background Blender/Sets/SET_Town.blend --python Blender/tools/render_town_check.py -- [slug ...]
Slugs: cattle, lane, mandi, halwai, refuge.  Default: cattle, lane.
"""

from pathlib import Path
import sys

import bpy

CAMERAS = {'cattle': 'CAM | Cattle place', 'lane': 'CAM | Lane A looking west',
           'mandi': 'CAM | Mandi shed from lane B', 'halwai': 'CAM | Halwai roof eye to the ghat',
           'refuge': 'CAM | Refuge floor'}
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
out = Path(__file__).resolve().parents[2] / 'Renders' / 'Town'
slugs = args or ['cattle', 'lane']
out.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
scene.render.resolution_percentage = 100
for slug in slugs:
    scene.camera = bpy.data.objects[CAMERAS[slug]]
    scene.render.filepath = str(out / f'{slug}.png')
    bpy.ops.render.render(write_still=True)
    print('Rendered', slug, flush=True)
print('CHECK_DONE', flush=True)
