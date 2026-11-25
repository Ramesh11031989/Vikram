"""Render two local Hindi voices against the locked Chapter 1 testimony cut."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import wave

from prepare_sc04 import EPISODE, ROOT, SAMPLE_RATE, samples_in, timestamp


MODEL = "kokoro-v1.0.timed.fp16.onnx"
VOICES = "voices-v1.0.bin"
PROFILES = {
    "Gopal": ("hm_psi", 0.96),
    "Vikram": ("hm_omega", 0.91),
}


def prepare_pcm(audio, numpy):
    """Trim model edge silence and gain-match the two role tracks."""
    signal = numpy.asarray(audio, dtype=numpy.float32).reshape(-1)
    if not len(signal) or not numpy.isfinite(signal).all():
        raise ValueError("Kokoro returned empty or non-finite audio")
    signal = signal - signal.mean()
    block_size = SAMPLE_RATE // 100
    blocks = numpy.pad(signal, (0, -len(signal) % block_size)).reshape((-1, block_size))
    rms = numpy.sqrt(numpy.mean(blocks * blocks, axis=1))
    active = numpy.flatnonzero(rms > max(0.0025, rms.max() * 0.025))
    if not len(active):
        raise ValueError("Kokoro returned silent audio")

    start = max(0, active[0] - 2) * block_size
    signal = signal[start:(active[-1] + 4) * block_size].copy()
    gain = min(10 ** (-22 / 20) / numpy.sqrt(numpy.mean(signal * signal)),
               10 ** (-2 / 20) / numpy.max(numpy.abs(signal)))
    fade_length = min(SAMPLE_RATE // 125, len(signal) // 2)
    fade = numpy.linspace(0, 1, fade_length)
    if fade_length:
        signal[:fade_length] *= fade
        signal[-fade_length:] *= fade[::-1]
    return numpy.rint(signal * gain * 32767).astype("<i2").tobytes(), start / SAMPLE_RATE


def write_wave(path, pcm):
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(SAMPLE_RATE)
        stream.writeframes(pcm)


def record_line(engine, text, voice, speed, maximum_samples, numpy):
    for _ in range(3):
        audio, rate, native_timings = engine.create_timed(text.replace("।", "."), voice=voice,
                                                         speed=speed, lang="hi")
        if rate != SAMPLE_RATE:
            raise ValueError(f"Unexpected Kokoro sample rate: {rate}")
        pcm, trimmed = prepare_pcm(audio, numpy)
        samples = len(pcm) // 2
        if samples <= maximum_samples:
            phonemes = []
            for timing in native_timings:
                start = max(0, timing.start - trimmed)
                end = min(samples / SAMPLE_RATE, timing.end - trimmed)
                if end > start:
                    phonemes.append({"phoneme": timing.phoneme, "start": round(start, 6),
                                     "end": round(end, 6)})
            return pcm, speed, phonemes
        speed = min(2.0, speed * samples / maximum_samples * 1.05)
    raise ValueError(f"Voice line does not fit its locked cut: {text}")


def prepare(runtime, destination):
    if (runtime / "packages").is_dir():
        sys.path.insert(0, str(runtime / "packages"))
    import numpy
    import espeakng_loader
    from kokoro_onnx import EspeakConfig, Kokoro
    from onnxruntime import InferenceSession, SessionOptions

    options = SessionOptions()
    options.intra_op_num_threads = 4
    options.log_severity_level = 3
    session = InferenceSession(str(runtime / MODEL), sess_options=options,
                               providers=["CPUExecutionProvider"])
    print("Loaded Kokoro model on CPU", flush=True)
    data = Path(espeakng_loader.get_data_path())
    with TemporaryDirectory(prefix="e01-espeak-") as temporary:
        # The native eSpeak DLL cannot open its dictionary from a Devanagari path.
        if sys.platform == "win32" and not str(data).isascii():
            copy = Path(temporary) / data.name
            if not str(copy).isascii():
                raise ValueError("Set TEMP to an ASCII directory for the native eSpeak dictionary")
            shutil.copytree(data, copy)
            data = copy
        engine = Kokoro.from_session(session, str(runtime / VOICES), EspeakConfig(data_path=str(data)))
        prepare_timeline(engine, destination, numpy)


def prepare_timeline(engine, destination, numpy):
    timeline_path = EPISODE / "E01_SC04_Animatic_Timeline.json"
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    fps = timeline["fps"]
    shots = {shot["id"]: shot for shot in timeline["shots"]}
    cues = timeline["cues"]
    audio_dir = destination / "Audio" / "Scratch"
    audio_dir.mkdir(parents=True, exist_ok=True)
    mixed = bytearray(math.ceil(timeline["total_frames"] * SAMPLE_RATE / fps) * 2)
    manifest = []
    for index, cue in enumerate(cues):
        start = int(cue["start_frame"])
        next_start = (int(cues[index + 1]["start_frame"])
                      if index + 1 < len(cues) else timeline["total_frames"] - fps)
        maximum_end = min(next_start - 3, max(int(cue["end_frame_exclusive"]),
                           shots[cue["shot_id"]]["end_frame_exclusive"] - 3))
        voice, speed = PROFILES[cue["speaker_id"]]
        pcm, speed, phonemes = record_line(engine, cue["dialogue_hi"], voice, speed,
                                           (maximum_end - start) * SAMPLE_RATE // fps, numpy)
        relative = Path("Audio/Scratch") / cue["wav_filename"]
        output = destination / relative
        write_wave(output, pcm)
        samples = samples_in(output)
        if not phonemes:
            raise ValueError(f"Kokoro export is missing phoneme timings for {cue['cue_id']}")
        mouth_cues = audio_dir / f"{cue['cue_id']}.phonemes.json"
        mouth_cues.write_text(json.dumps(phonemes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        cue.update(audio_file=relative.as_posix(), audio_samples=samples,
                   audio_seconds=round(samples / SAMPLE_RATE, 5),
                   end_frame_exclusive=start + math.ceil(samples * fps / SAMPLE_RATE))
        offset = round(start * SAMPLE_RATE / fps) * 2
        mixed[offset:offset + len(pcm)] = pcm
        manifest.append({"cue_id": cue["cue_id"], "speaker": cue["speaker_id"],
                         "file": cue["wav_filename"], "samples": samples,
                         "voice": voice, "speed": round(speed, 3), "phonemes": mouth_cues.name})
        print(f"Prepared {cue['cue_id']}, {voice}, {samples / SAMPLE_RATE:.2f}s, {len(phonemes)} phoneme spans",
              flush=True)

    timeline["status"] = "Locked Unity cut with local Kokoro Hindi dialogue"
    timeline["voice_provider"] = "Kokoro 82M v1.0 FP16 (CPU ONNX)"
    (destination / timeline_path.name).write_text(
        json.dumps(timeline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (destination / "E01_SC04_Dialogue_Timed.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(cues[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(cues)
    subtitles = [f"{index}\n{timestamp(cue['start_frame'])} --> {timestamp(cue['end_frame_exclusive'])}\n"
                 f"{cue['dialogue_hi']}\n" for index, cue in enumerate(cues, start=1)]
    (destination / "E01_SC04_Animatic.srt").write_text("\n".join(subtitles), encoding="utf-8")
    write_wave(destination / "Audio" / "E01_SC04_Dialogue_Mix.wav", mixed)
    (audio_dir / "voice_manifest.json").write_text(json.dumps({
        "provider": timeline["voice_provider"],
        "model_source": "https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.1",
        "sample_rate": SAMPLE_RATE,
        "cues": manifest,
    }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, default=ROOT / "Renders/Tools/Kokoro")
    parser.add_argument("--output", type=Path, default=ROOT / "Renders/E01_SC04_Dialogue")
    args = parser.parse_args()
    prepare(args.runtime.resolve(), args.output.resolve())
