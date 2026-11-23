"""Render the keyed performance, with a scene-hash cache for safe resumption."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import bpy


ROOT=Path(__file__).resolve().parents[2]
EPISODE=ROOT/'Production/E01'
OUTPUT=EPISODE/'Performance'


def main(proof_frames,step,samples):
    scene=bpy.data.scenes['E01_SC04 | Performance v0.2']
    bpy.context.window.scene=scene
    timeline=json.loads((EPISODE/'E01_SC04_Animatic_Timeline.json').read_text(encoding='utf-8'))
    scene.render.engine='BLENDER_EEVEE_NEXT'
    scene.eevee.taa_render_samples=samples
    scene.render.image_settings.file_format='PNG'
    scene.render.image_settings.color_mode='RGB'
    scene.render.image_settings.compression=20
    width=round(scene.render.resolution_x*scene.render.resolution_percentage/100)
    height=round(scene.render.resolution_y*scene.render.resolution_percentage/100)
    signature=hashlib.sha256(Path(bpy.data.filepath).read_bytes()+f'{step}/{samples}/{width}/{height}'.encode()).hexdigest()
    cache=OUTPUT/'RenderCache'/signature[:16]
    cache.mkdir(parents=True,exist_ok=True)
    manifest={'scene_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
              'signature':signature,'step':step,'samples':samples,'resolution':[width,height],
              'fps':timeline['fps'],'total_frames':timeline['total_frames'],'shots':[]}
    started=time.monotonic()
    for shot in timeline['shots']:
        camera=scene.timeline_markers[shot['id']].camera
        frame_numbers=list(range(shot['start_frame'],shot['end_frame_exclusive'],step))
        directory=cache/shot['id']
        directory.mkdir(exist_ok=True)
        manifest['shots'].append({**shot,'directory':str(directory.relative_to(EPISODE)),
                                  'rendered_frames':frame_numbers})
        for index,frame in enumerate(frame_numbers):
            if proof_frames and frame not in proof_frames:
                continue
            destination=(OUTPUT/'Proofs'/f'frame_{frame:05}.png') if proof_frames else directory/f'frame_{index:05}.png'
            destination.parent.mkdir(exist_ok=True)
            if not proof_frames and destination.exists():
                # A complete PNG ends with the IEND chunk, including its CRC.
                raw=destination.read_bytes()
                if len(raw)>1024 and raw[-8:]==b'IEND\xaeB`\x82':
                    continue
            scene.frame_set(frame)
            scene.camera=camera
            scene.render.filepath=str(destination)
            bpy.ops.render.render(write_still=True)
            print(f'PERFORMANCE_FRAME {shot["id"]} {index+1}/{len(frame_numbers)} source={frame} elapsed={time.monotonic()-started:.1f}',flush=True)
    if not proof_frames:
        (OUTPUT/'Render_Manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        print('PERFORMANCE_RENDER_COMPLETE',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proof',nargs='+',type=int)
    parser.add_argument('--step',type=int,choices=(1,2),default=2)
    parser.add_argument('--samples',type=int,default=4)
    arguments=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    args=parser.parse_args(arguments)
    main(set(args.proof or []),args.step,args.samples)
