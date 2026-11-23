"""Generate replaceable Hindi scratch speech and an audio-measured shot timeline."""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import wave


ROOT = Path(__file__).resolve().parents[2]
EPISODE = ROOT / 'Production' / 'E01'
FPS = 24
SAMPLE_RATE = 24000
SHOTS = (
    ('SH01', 0, 84, 'Chalk map', 'court'),
    ('SH02', 84, 204, 'Gopal recalls the lamp', 'court'),
    ('SH03', 204, 360, 'Boat point of view', 'river'),
    ('SH04', 360, 450, 'Water on the steps', 'river'),
    ('SH05', 450, 516, 'How much of the face?', 'court'),
    ('SH06', 516, 606, 'Gopal demonstrates the angle', 'court'),
    ('SH07', 606, 685, 'How much of the gate?', 'court'),
    ('SH08', 685, 770, 'Shadow below the lamp', 'river'),
    ('SH09', 770, 954, 'Oar and the niece\'s hand', 'river'),
    ('SH10', 954, 1070, 'I thought I knew', 'court'),
    ('SH11', 1070, 1428, 'Record what was observed', 'court'),
)
PROFILES = {
    'Vikram': {'voice': 'hi-IN-MadhurNeural', 'rate': '-6%', 'pitch': '-10Hz'},
    'Gopal': {'voice': 'hi-IN-MadhurNeural', 'rate': '+0%', 'pitch': '+4Hz'},
}


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def read_cues() -> list[dict[str, str]]:
    with (EPISODE / 'E01_SC04_Dialogue_Cues.csv').open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def samples_in(path: Path) -> int:
    with wave.open(str(path), 'rb') as stream:
        if stream.getframerate() != SAMPLE_RATE or stream.getnchannels() != 1:
            raise ValueError(f'Expected mono {SAMPLE_RATE} Hz PCM: {path}')
        return stream.getnframes()


async def generate_speech(ca_bundle: str | None) -> None:
    import edge_tts

    if ca_bundle:
        # Add the execution environment's trusted CA; keep verification enabled.
        import edge_tts.communicate
        edge_tts.communicate._SSL_CTX.load_verify_locations(cafile=ca_bundle)

    destination = EPISODE / 'Audio' / 'Scratch'
    destination.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []
    for cue in read_cues():
        profile = PROFILES[cue['speaker_id']]
        output = destination / cue['wav_filename']
        fingerprint = hashlib.sha256(json.dumps(
            {'text': cue['dialogue_hi'], **profile}, ensure_ascii=False, sort_keys=True
        ).encode()).hexdigest()
        metadata = output.with_suffix('.json')
        cached = metadata.exists() and output.exists()
        if cached:
            cached = json.loads(metadata.read_text(encoding='utf-8')).get('fingerprint') == fingerprint
        if not cached:
            compressed = output.with_suffix('.mp3')
            speech = edge_tts.Communicate(cue['dialogue_hi'], **profile)
            await asyncio.wait_for(speech.save(str(compressed)), timeout=50)
            run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(compressed),
                 '-af', 'silenceremove=start_periods=1:start_duration=0.02:start_threshold=-48dB,'
                 'areverse,silenceremove=start_periods=1:start_duration=0.02:start_threshold=-48dB,'
                 'areverse,loudnorm=I=-20:TP=-2:LRA=8',
                 '-ar', str(SAMPLE_RATE), '-ac', '1', '-c:a', 'pcm_s16le', str(output)])
            compressed.unlink()
            metadata.write_text(json.dumps({'fingerprint': fingerprint, **profile}, indent=2))
        manifest.append({'cue_id': cue['cue_id'], 'speaker': cue['speaker_id'],
                         'file': output.name, 'samples': samples_in(output), **profile})
        print(f"Prepared {cue['cue_id']}: {samples_in(output) / SAMPLE_RATE:.2f}s", flush=True)
    (destination / 'voice_manifest.json').write_text(json.dumps({
        'status': 'SYNTHETIC SCRATCH DIALOGUE — replace before final production',
        'provider': 'Microsoft Edge online TTS through edge-tts',
        'note': 'Both roles use a stock male Hindi voice with different pitch/rate settings.',
        'sample_rate': SAMPLE_RATE, 'cues': manifest,
    }, ensure_ascii=False, indent=2), encoding='utf-8')


def timestamp(frame: int) -> str:
    milliseconds = round(frame * 1000 / FPS)
    seconds, milliseconds = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f'{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}'


def build_timeline() -> None:
    cues = read_cues()
    spans: list[tuple[int, int, int, int]] = []
    timed: list[dict[str, object]] = []
    shift = 0
    for cue in cues:
        original_start, original_end = int(cue['start_frame']), int(cue['end_frame_exclusive'])
        audio = EPISODE / 'Audio' / 'Scratch' / cue['wav_filename']
        count = samples_in(audio)
        duration = math.ceil(count * FPS / SAMPLE_RATE)
        allocated = max(original_end - original_start, duration + 3)
        start = original_start + shift
        spans.append((original_start, original_end, start, start + allocated))
        crosses_cut = any(original_start < shot[2] < original_end for shot in SHOTS)
        audio_start = start + max(0, allocated-duration-3) if crosses_cut else start
        timed.append({**cue, 'original_start_frame': original_start,
                      'original_end_frame_exclusive': original_end,
                      'start_frame': audio_start, 'end_frame_exclusive': audio_start + duration,
                      'audio_samples': count, 'audio_seconds': round(count / SAMPLE_RATE, 5),
                      'audio_file': f"Audio/Scratch/{cue['wav_filename']}"})
        shift += allocated - (original_end - original_start)

    def map_frame(frame: int) -> int:
        previous_shift = 0
        for old_start, old_end, new_start, new_end in spans:
            if frame < old_start:
                return frame + previous_shift
            if frame <= old_end:
                return round(new_start + (frame-old_start) * (new_end-new_start)/(old_end-old_start))
            previous_shift = new_end - old_end
        return frame + previous_shift

    shots = [{'id': f'E01_SC04_{suffix}', 'title': title, 'set': location,
              'original_start_frame': start, 'original_end_frame_exclusive': end,
              'start_frame': map_frame(start), 'end_frame_exclusive': map_frame(end)}
             for suffix, start, end, title, location in SHOTS]
    total = map_frame(1428)
    timeline = {'version': 1, 'status': 'Animatic v0.1 — synthetic scratch dialogue',
                'fps': FPS, 'sample_rate': SAMPLE_RATE, 'total_frames': total,
                'duration_seconds': total/FPS, 'shots': shots, 'cues': timed}
    (EPISODE / 'E01_SC04_Animatic_Timeline.json').write_text(
        json.dumps(timeline, ensure_ascii=False, indent=2), encoding='utf-8')
    with (EPISODE / 'E01_SC04_Dialogue_Timed.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(timed[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(timed)
    subtitles = [f"{index}\n{timestamp(int(cue['start_frame']))} --> "
                 f"{timestamp(int(cue['end_frame_exclusive']))}\n{cue['dialogue_hi']}\n"
                 for index, cue in enumerate(timed, 1)]
    (EPISODE / 'E01_SC04_Animatic.srt').write_text('\n'.join(subtitles), encoding='utf-8')

    # Integer PCM placement keeps audio sample-exact; no lossy concatenation or tempo changes.
    mixed = bytearray(math.ceil(total * SAMPLE_RATE/FPS) * 2)
    for cue in timed:
        with wave.open(str(EPISODE / str(cue['audio_file'])), 'rb') as stream:
            audio = stream.readframes(stream.getnframes())
        offset = round(int(cue['start_frame']) * SAMPLE_RATE/FPS) * 2
        mixed[offset:offset+len(audio)] = audio
    with wave.open(str(EPISODE / 'Audio/E01_SC04_Dialogue_Mix.wav'), 'wb') as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(SAMPLE_RATE)
        stream.writeframes(mixed)
    print(f'Audio-measured timeline: {total} frames / {total/FPS:.2f} seconds', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate-speech', action='store_true')
    parser.add_argument('--ca-bundle', help='Optional additional trusted PEM CA bundle')
    args = parser.parse_args()
    if args.generate_speech:
        asyncio.run(generate_speech(args.ca_bundle))
    build_timeline()
