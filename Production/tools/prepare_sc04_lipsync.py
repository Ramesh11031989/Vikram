"""Analyze Hindi dialogue with Rhubarb and optionally export a Unity track."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import tempfile
import unicodedata
import wave


ROOT = Path(__file__).resolve().parents[2]
EPISODE = ROOT / 'Production/E01'
DEFAULT_TIMELINE = EPISODE / 'E01_SC04_Animatic_Timeline.json'
IPA_VISEMES = {
    phone: shape
    for shape, phones in {'A': 'bmpɱ', 'C': 'əɐɛæʌɜɘɚ', 'D': 'aɑɶ', 'E': 'oɔɒøœɵɞ',
                          'F': 'uʊwɯyʉ', 'G': 'fvʋɸβ', 'H': 'lɭɫ', 'I': 'iɪeɨ'}.items()
    for phone in phones
}


def phone_shape(phoneme: str, previous: str) -> str:
    marks = 'ːˑʰʱʲʷ˞'
    parts = unicodedata.normalize('NFD', phoneme.strip())
    if parts and all(part in marks or unicodedata.category(part).startswith('M') for part in parts):
        return previous
    for part in parts:
        if part in IPA_VISEMES:
            return IPA_VISEMES[part]
        if unicodedata.category(part) in ('Ll', 'Lo', 'Lu'):
            return 'B'
    return 'X'


def read_phone_cues(path: Path, duration: float) -> list[dict]:
    phones = json.loads(path.read_text(encoding='utf-8'))
    cues = []

    def append(start: float, end: float, shape: str) -> None:
        if end <= start:
            return
        if cues and cues[-1]['value'] == shape:
            cues[-1]['end'] = end
        else:
            cues.append({'start': start, 'end': end, 'value': shape})

    end = 0.0
    previous = 'X'
    for phone in phones:
        start = float(phone['start'])
        stop = float(phone['end'])
        if (not math.isfinite(start) or not math.isfinite(stop) or start < end - .003 or
                stop < start or stop > duration + .02):
            raise ValueError(f'Invalid phoneme timing in {path.name}')
        start = min(duration, max(end, start))
        stop = min(duration, max(start, stop))
        append(end, start, 'X')
        previous = phone_shape(phone['phoneme'], previous if start == end else 'X')
        append(start, stop, previous)
        end = stop
    append(end, duration, 'X')
    if not any(cue['value'] != 'X' for cue in cues):
        raise ValueError(f'No timed speech phonemes in {path.name}')
    return cues


def rhubarb_cues(executable: Path, version: str, audio: bytes, digest: str, cue: dict,
                 destination: Path, duration: float) -> list[dict]:
    output = destination / f"{cue['cue_id']}.json"
    fingerprint = output.with_suffix('.sha256')
    signature = f'{digest}\n{version}\nphonetic/GHX\n'
    if not output.exists() or not fingerprint.exists() or fingerprint.read_text() != signature:
        # Relative ASCII names work with native Windows builds under a Hindi project path.
        with tempfile.TemporaryDirectory(dir=destination) as temporary:
            work = Path(temporary)
            (work/'line.wav').write_bytes(audio)
            subprocess.run([str(executable), '-r', 'phonetic', '-f', 'json',
                            '--extendedShapes', 'GHX', '--threads', '2', '--quiet',
                            '-o', 'mouth.json', 'line.wav'], cwd=work, check=True)
            data = json.loads((work/'mouth.json').read_text(encoding='utf-8'))
        data['metadata']['soundFile'] = cue['audio_file']
        output.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
        fingerprint.write_text(signature)
    data = json.loads(output.read_text(encoding='utf-8'))
    if abs(data['metadata']['duration']-duration) > .04:
        raise ValueError(f"Recording and viseme durations differ: {cue['cue_id']}")
    return data['mouthCues']


def main(executable: Path | None, timeline_path: Path, destination: Path, unity_track: Path | None,
         prefer_phonemes: bool) -> None:
    timeline = json.loads(timeline_path.read_text(encoding='utf-8'))
    destination.mkdir(parents=True, exist_ok=True)
    version = None
    manifest = []
    unity_cues = []
    for cue in timeline['cues']:
        recording = timeline_path.parent / cue['audio_file']
        audio = recording.read_bytes()
        digest = hashlib.sha256(audio).hexdigest()
        with wave.open(str(recording), 'rb') as stream:
            duration = stream.getnframes()/stream.getframerate()
        phonemes = recording.with_name(f"{cue['cue_id']}.phonemes.json")
        use_phonemes = prefer_phonemes and phonemes.is_file()
        if use_phonemes:
            mouth_cues = read_phone_cues(phonemes, duration)
        else:
            if executable is None:
                raise ValueError(f"Supply --rhubarb to analyze {cue['cue_id']} without a phoneme file.")
            if version is None:
                version = subprocess.check_output([str(executable), '--version'], text=True).strip()
            mouth_cues = rhubarb_cues(executable, version, audio, digest, cue, destination, duration)
        previous_end = 0
        for segment in mouth_cues:
            if abs(segment['start']-previous_end) > .025 or segment['end'] < segment['start']:
                raise ValueError(f"Invalid viseme coverage: {cue['cue_id']}")
            if segment['value'] not in tuple('ABCDEFGHIX'):
                raise ValueError('Unexpected mouth shape')
            previous_end = segment['end']
        if abs(previous_end - duration) > .04:
            raise ValueError(f"Incomplete viseme coverage: {cue['cue_id']}")
        manifest.append({'cue_id': cue['cue_id'], 'segments': len(mouth_cues),
                         'audio_sha256': digest, 'duration': duration})
        if unity_track is not None:
            alignment = 'model IPA timings' if use_phonemes else 'Rhubarb phonetic'
            unity_cues.append({'speaker': cue['speaker_id'], 'start': cue['start_frame']/timeline['fps'],
                               'cue_id': cue['cue_id'], 'duration': duration, 'mouthCues': mouth_cues,
                               'alignment': alignment})
            manifest[-1]['alignment'] = alignment
        print(f"Aligned {cue['cue_id']}: {len(mouth_cues)} speech shapes", flush=True)
    method = 'Language-independent acoustic viseme recognition on the existing WAVs'
    if prefer_phonemes:
        method = 'Voice model IPA timings where available, otherwise acoustic viseme recognition'
    (destination/'manifest.json').write_text(json.dumps({
        'tool': version or 'model IPA timings', 'recognizer': 'phonetic' if version else 'timed IPA',
        'method': method,
        'limitation': 'Automatic viseme estimates, not a linguist-verified Hindi phoneme alignment',
        'cues': manifest,
    }, indent=2)+'\n', encoding='utf-8')
    if unity_track is not None:
        unity_track.parent.mkdir(parents=True, exist_ok=True)
        unity_track.write_text(json.dumps({'cues': unity_cues}, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rhubarb', type=Path, help='Rhubarb executable for WAVs without model phoneme timings.')
    parser.add_argument('--timeline', default=DEFAULT_TIMELINE, type=Path)
    parser.add_argument('--output-dir', type=Path, help='Defaults to Performance/LipSync next to the timeline.')
    parser.add_argument('--unity-track', type=Path, help='Optional JSON for the Unity DialogueLipSync driver.')
    parser.add_argument('--prefer-phonemes', action='store_true',
                        help='Use same-directory cue_id.phonemes.json timings for Unity where available.')
    args = parser.parse_args()
    if args.prefer_phonemes and args.unity_track is None:
        parser.error('--prefer-phonemes requires --unity-track')
    if not args.prefer_phonemes and args.rhubarb is None:
        parser.error('supply --rhubarb for acoustic alignment')
    timeline_path = args.timeline.resolve()
    destination = args.output_dir or timeline_path.parent/'Performance/LipSync'
    rhubarb = args.rhubarb.resolve() if args.rhubarb else None
    main(rhubarb, timeline_path, destination.resolve(), args.unity_track, args.prefer_phonemes)
