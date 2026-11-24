"""Generate replaceable Hindi speech offline with Indic Parler-TTS and build an audio-measured shot timeline."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
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
MODEL_ID = 'ai4bharat/indic-parler-tts'
# One entry per speaker_id in the cue sheet. Each character gets a different named
# speaker and a plain-English voice description. Edit `description` to change the
# voice; `seed` keeps every re-run reproducible. Add Betal etc. here for new scenes.
PROFILES = {
    'Vikram': {
        'speaker': 'Aman', 'seed': 11,
        'description': ("Aman speaks in Hindi with a deep, calm, authoritative male voice at a slow, "
                        "measured pace. Very clear, close-up studio recording with no background noise."),
    },
    'Gopal': {
        'speaker': 'Rohit', 'seed': 23,
        'description': ("Rohit speaks in Hindi with a slightly higher, tired, older working man's voice, "
                        "at a moderate pace with some hesitation. Very clear, close-up studio recording "
                        "with no background noise."),
    },
}


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def read_cues() -> list[dict[str, str]]:
    with (EPISODE / 'E01_SC04_Dialogue_Cues.csv').open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def samples_in(path: Path) -> int:
    with wave.open(str(path), 'rb') as stream:
        if (stream.getframerate() != SAMPLE_RATE or stream.getnchannels() != 1
                or stream.getsampwidth() != 2 or stream.getnframes() == 0):
            raise ValueError(f'Expected nonempty mono {SAMPLE_RATE} Hz 16-bit PCM: {path}')
        return stream.getnframes()


def load_model():
    """Load Indic Parler-TTS once (downloads ~3.8 GB on first use, then runs offline)."""
    import torch
    from parler_tts import ParlerTTSForConditionalGeneration
    from transformers import AutoTokenizer

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    dtype = torch.float16 if device == 'cuda' else torch.float32
    model = ParlerTTSForConditionalGeneration.from_pretrained(MODEL_ID, torch_dtype=dtype).to(device)
    prompt_tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    description_tokenizer = AutoTokenizer.from_pretrained(model.config.text_encoder._name_or_path)
    print(f'Loaded {MODEL_ID} on {device}', flush=True)
    return torch, model, prompt_tokenizer, description_tokenizer, device


def synthesize(engine, text: str, profile: dict[str, object], target: Path) -> None:
    """Render one line to a raw WAV at the model's native sample rate."""
    import numpy as np

    torch, model, prompt_tokenizer, description_tokenizer, device = engine
    torch.manual_seed(int(profile['seed']))
    description = description_tokenizer(str(profile['description']), return_tensors='pt').to(device)
    prompt = prompt_tokenizer(text, return_tensors='pt').to(device)
    with torch.no_grad():
        generation = model.generate(
            input_ids=description.input_ids, attention_mask=description.attention_mask,
            prompt_input_ids=prompt.input_ids, prompt_attention_mask=prompt.attention_mask)
    audio = generation.float().cpu().numpy().squeeze()
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype('<i2')
    with wave.open(str(target), 'wb') as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(int(model.config.sampling_rate))
        stream.writeframes(pcm.tobytes())


def cached_samples(output: Path, fingerprint: str) -> int | None:
    try:
        metadata = json.loads(output.with_suffix('.json').read_text(encoding='utf-8'))
        if isinstance(metadata, dict) and metadata.get('fingerprint') == fingerprint:
            return samples_in(output)
    except (OSError, ValueError, wave.Error, EOFError):
        return None
    return None


def publish_speech(staged: list[Path], destination: Path, work: Path) -> None:
    backup = work / 'previous'
    backup.mkdir()
    for source in staged:
        target = destination / source.name
        if target.exists():
            shutil.copy2(target, backup / source.name)

    published = []
    try:
        for source in staged:
            target = destination / source.name
            source.replace(target)
            published.append(target)
    except (OSError, KeyboardInterrupt):
        for target in reversed(published):
            saved = backup / target.name
            if saved.exists():
                saved.replace(target)
            else:
                target.unlink()
        raise


def generate_speech() -> None:
    destination = EPISODE / 'Audio' / 'Scratch'
    destination.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []
    engine = None
    with TemporaryDirectory(prefix='sc04-speech-', dir=destination.parent) as temporary:
        work = Path(temporary)
        staged = []
        for cue in read_cues():
            profile = PROFILES[cue['speaker_id']]
            filename = cue['wav_filename']
            fingerprint = hashlib.sha256(json.dumps(
                {'text': cue['dialogue_hi'], 'model': MODEL_ID, **profile}, ensure_ascii=False, sort_keys=True
            ).encode()).hexdigest()
            count = cached_samples(destination / filename, fingerprint)
            provenance = {'speaker': cue['speaker_id'], 'voice': profile['speaker'],
                          'seed': profile['seed'], 'description': profile['description']}
            if count is None:
                if engine is None:
                    if shutil.which('ffmpeg') is None:
                        raise RuntimeError('Add FFmpeg to PATH before generating speech.')
                    engine = load_model()
                output = work / filename
                raw = output.with_suffix('.raw.wav')
                synthesize(engine, cue['dialogue_hi'], profile, raw)
                run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(raw),
                     '-af', 'silenceremove=start_periods=1:start_duration=0.02:start_threshold=-48dB,'
                     'areverse,silenceremove=start_periods=1:start_duration=0.02:start_threshold=-48dB,'
                     'areverse,loudnorm=I=-20:TP=-2:LRA=8',
                     '-ar', str(SAMPLE_RATE), '-ac', '1', '-c:a', 'pcm_s16le', str(output)])
                count = samples_in(output)
                raw.unlink()
                metadata = output.with_suffix('.json')
                metadata.write_text(json.dumps({'fingerprint': fingerprint, **provenance}, indent=2),
                                    encoding='utf-8')
                staged.extend((output, metadata))
            manifest.append({'cue_id': cue['cue_id'], 'file': filename, 'samples': count, **provenance})
            print(f"Prepared {cue['cue_id']}: {count / SAMPLE_RATE:.2f}s", flush=True)
        voice_manifest = work / 'voice_manifest.json'
        voice_manifest.write_text(json.dumps({
            'status': 'AI-GENERATED DIALOGUE — review pronunciation before final production',
            'provider': MODEL_ID,
            'note': 'Generated locally with role-specific voice descriptions and fixed seeds.',
            'sample_rate': SAMPLE_RATE, 'cues': manifest,
        }, ensure_ascii=False, indent=2), encoding='utf-8')
        publish_speech([*staged, voice_manifest], destination, work)


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
    args = parser.parse_args()
    if args.generate_speech:
        generate_speech()
    build_timeline()
