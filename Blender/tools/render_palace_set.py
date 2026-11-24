"""Render review stills of the palace set from its story cameras.

    python Blender/tools/render_palace_set.py -- --cameras window darbar_story --frames 1 2
    blender --background Blender/Sets/SET_Palace.blend --python Blender/tools/render_palace_set.py -- --all

Camera keys are the keys of `cameras` in SET_Palace_Manifest.json. Frame 1 is
morning (five ghat steps dry), frame 2 is evening (three steps, lamps lit).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

import bpy


ROOT = Path(__file__).resolve().parents[2]
BLEND = ROOT / 'Blender' / 'Sets' / 'SET_Palace.blend'
MANIFEST = ROOT / 'Blender' / 'Sets' / 'SET_Palace_Manifest.json'
OUTPUT = ROOT / 'Blender' / 'Previews' / 'Sets'


def main() -> None:
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cameras', nargs='*', default=[])
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--frames', nargs='*', type=int, default=[1])
    parser.add_argument('--percent', type=int, default=100)
    parser.add_argument('--samples', type=int, default=0)
    parser.add_argument('--out', type=Path, default=OUTPUT)
    parser.add_argument('--prefix', default='Palace')
    args = parser.parse_args(argv)
    if Path(bpy.data.filepath or '').resolve() != BLEND.resolve():
        bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    scene = bpy.context.scene
    data = json.loads(MANIFEST.read_text(encoding='utf-8'))
    keys = list(data['cameras']) if args.all else args.cameras
    scene.render.resolution_percentage = args.percent
    if args.samples:
        scene.cycles.samples = args.samples
    args.out.mkdir(parents=True, exist_ok=True)
    for key in keys:
        camera = bpy.data.objects[data['cameras'][key]['name']]
        scene.camera = camera
        for frame in args.frames:
            scene.frame_set(frame)
            label = 'Morning' if frame == 1 else 'Evening'
            path = args.out / f'{args.prefix}_{key}_{label}.png'
            scene.render.filepath = str(path)
            start = time.time()
            bpy.ops.render.render(write_still=True)
            print(f'{path.name}: {time.time() - start:.0f}s', flush=True)


if __name__ == '__main__':
    main()
