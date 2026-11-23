"""Check cross-file timing, audible cue assets and the encoded review video."""

from __future__ import annotations

import array
import csv
import json
from pathlib import Path
import subprocess
import wave


ROOT = Path(__file__).resolve().parents[2]
EPISODE = ROOT/'Production/E01'


def main() -> None:
    timeline = json.loads((EPISODE/'E01_SC04_Animatic_Timeline.json').read_text(encoding='utf-8'))
    shots, cues = timeline['shots'], timeline['cues']
    if len(shots) != 11 or len(cues) != 12:
        raise ValueError('Expected the approved eleven-shot, twelve-line scene')
    if [shot['id'] for shot in shots] != [f'E01_SC04_SH{index:02}' for index in range(1,12)]:
        raise ValueError('Shot identities or ordering changed')
    with (EPISODE/'E01_SC04_Dialogue_Cues.csv').open(encoding='utf-8',newline='') as stream:
        original = list(csv.DictReader(stream))
    if [(cue['cue_id'],cue['dialogue_hi']) for cue in cues] != [(cue['cue_id'],cue['dialogue_hi']) for cue in original]:
        raise ValueError('Dialogue identities, ordering or Hindi wording changed')
    if shots[0]['start_frame'] != 0 or shots[-1]['end_frame_exclusive'] != timeline['total_frames']:
        raise ValueError('Shot timeline does not cover the declared duration')
    for previous, following in zip(shots, shots[1:]):
        if previous['end_frame_exclusive'] != following['start_frame']:
            raise ValueError('Shot gap or overlap')
    previous_end = 0
    for cue in cues:
        if cue['start_frame'] < previous_end:
            raise ValueError(f"Dialogue overlap: {cue['cue_id']}")
        previous_end = cue['end_frame_exclusive']
        with wave.open(str(EPISODE/cue['audio_file']), 'rb') as stream:
            if stream.getnframes() != cue['audio_samples']:
                raise ValueError(f"Audio changed without rebuilding timing: {cue['cue_id']}")
            if stream.getnchannels() != 1 or stream.getsampwidth() != 2 or stream.getframerate() != timeline['sample_rate']:
                raise ValueError('Expected mono 16-bit scratch WAV files')
            samples = array.array('h', stream.readframes(stream.getnframes()))
        if not samples or max(map(abs, samples)) < 100:
            raise ValueError(f"Empty or silent line: {cue['cue_id']}")
        if max(map(abs, samples)) >= 32767:
            raise ValueError(f"Clipped audio: {cue['cue_id']}")
        available = (cue['end_frame_exclusive']-cue['start_frame'])/timeline['fps']
        if cue['audio_seconds'] > available + 0.00001:
            raise ValueError(f"Audio would be truncated: {cue['cue_id']}")
    bridge = next(cue for cue in cues if cue['cue_id'].endswith('L03'))
    cut = shots[2]['end_frame_exclusive']
    if not bridge['start_frame'] < cut < bridge['end_frame_exclusive']:
        raise ValueError('L03 must continue across the SH03/SH04 cut')
    for shot in shots:
        panel = EPISODE/'Animatic/Frames'/f"{shot['id']}.png"
        if not panel.exists() or panel.stat().st_size < 1024:
            raise ValueError(f'Missing rendered panel: {panel}')
    movie = EPISODE/'Animatic/E01_SC04_Animatic_v0_1.mp4'
    result = subprocess.check_output(['ffprobe','-v','error','-show_streams',
                                      '-show_format','-of','json',str(movie)], text=True)
    probe = json.loads(result)
    video = next(stream for stream in probe['streams'] if stream['codec_type']=='video')
    audio = next(stream for stream in probe['streams'] if stream['codec_type']=='audio')
    if int(video['nb_frames']) != timeline['total_frames']:
        raise ValueError('Encoded frame count differs from the timing manifest')
    if (video['width'],video['height']) != (1280,720) or video['r_frame_rate'] != '24/1':
        raise ValueError('Expected 1280 × 720 at 24 fps')
    if abs(float(audio['duration'])-timeline['duration_seconds']) > .1:
        raise ValueError('Audio/video duration mismatch')
    report = {'status':'PASS', 'shots':len(shots), 'audible_cues':len(cues),
              'frames':timeline['total_frames'], 'seconds':timeline['duration_seconds'],
              'video':'1280x720 / 24 fps / H.264', 'audio':'mono AAC / synthetic Hindi scratch',
              'L03_cross_cut':True, 'no_dialogue_overlap':True, 'no_truncated_cues':True}
    (EPISODE/'E01_SC04_Validation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
