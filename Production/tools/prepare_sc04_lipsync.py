"""Analyze the existing Hindi recordings with Rhubarb's phonetic recognizer."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import wave


ROOT = Path(__file__).resolve().parents[2]
EPISODE = ROOT / 'Production/E01'
DESTINATION = EPISODE / 'Performance/LipSync'


def main(executable: Path) -> None:
    timeline = json.loads((EPISODE/'E01_SC04_Animatic_Timeline.json').read_text(encoding='utf-8'))
    version = subprocess.check_output([str(executable), '--version'], text=True).strip()
    DESTINATION.mkdir(parents=True, exist_ok=True)
    manifest = []
    for cue in timeline['cues']:
        recording = EPISODE / cue['audio_file']
        digest = hashlib.sha256(recording.read_bytes()).hexdigest()
        output = DESTINATION / f"{cue['cue_id']}.json"
        fingerprint = output.with_suffix('.sha256')
        signature = f'{digest}\n{version}\nphonetic/GHX\n'
        if not output.exists() or not fingerprint.exists() or fingerprint.read_text() != signature:
            subprocess.run([str(executable), '-r', 'phonetic', '-f', 'json',
                            '--extendedShapes', 'GHX', '--threads', '2', '--quiet',
                            '-o', str(output), str(recording)], check=True)
            data = json.loads(output.read_text())
            data['metadata']['soundFile'] = cue['audio_file']
            output.write_text(json.dumps(data, indent=2)+'\n')
            fingerprint.write_text(signature)
        data = json.loads(output.read_text())
        with wave.open(str(recording), 'rb') as stream:
            duration = stream.getnframes()/stream.getframerate()
        if abs(data['metadata']['duration']-duration) > .04:
            raise ValueError(f"Recording and viseme durations differ: {cue['cue_id']}")
        previous_end = 0
        for segment in data['mouthCues']:
            if abs(segment['start']-previous_end) > .025 or segment['end'] < segment['start']:
                raise ValueError(f"Invalid viseme coverage: {cue['cue_id']}")
            if segment['value'] not in 'ABCDEFGHX':
                raise ValueError('Unexpected mouth shape')
            previous_end = segment['end']
        manifest.append({'cue_id': cue['cue_id'], 'segments': len(data['mouthCues']),
                         'audio_sha256': digest, 'duration': duration})
        print(f"Aligned {cue['cue_id']}: {len(data['mouthCues'])} speech shapes", flush=True)
    (DESTINATION/'manifest.json').write_text(json.dumps({
        'tool': version, 'recognizer': 'phonetic',
        'method': 'Language-independent acoustic viseme recognition on the existing WAVs',
        'limitation': 'Automatic viseme estimates, not a linguist-verified Hindi phoneme alignment',
        'cues': manifest,
    }, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rhubarb', required=True, type=Path)
    main(parser.parse_args().rhubarb.resolve())
