"""Generate instrumental film cues locally with the ACE-Step 1.5 GGUF runtime."""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import wave


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNTIME = ROOT / "Renders" / "Tools" / "ACE-Step.cpp"
DEFAULT_OUTPUT = ROOT / "Renders" / "Audio" / "Music"
MODEL = "acestep-v15-turbo-Q4_K_M.gguf"
REQUIRED_MODELS = (
    MODEL,
    "Qwen3-Embedding-0.6B-Q8_0.gguf",
    "vae-BF16.gguf",
)


def find_executable(runtime):
    name = "ace-synth.exe" if os.name == "nt" else "ace-synth"
    for directory in (runtime, runtime / "build" / "Release", runtime / "build"):
        executable = directory / name
        if executable.is_file():
            return executable
    raise FileNotFoundError(f"Could not find {name} under {runtime}. Set --runtime-dir to the ACE-Step.cpp folder.")


def make_request(cue, duration, seed):
    return {
        "task_type": "text2music",
        "caption": cue["caption"],
        "lyrics": "[Instrumental]",
        "bpm": cue["bpm"],
        "duration": duration,
        "keyscale": cue["keyscale"],
        "timesignature": cue["timesignature"],
        "vocal_language": "unknown",
        "synth_model": MODEL,
        "synth_batch_size": 1,
        "inference_steps": 8,
        "guidance_scale": 1.0,
        "shift": 3.0,
        "output_format": "wav16",
        "seed": seed,
    }


def synthesize(runtime, device, request, destination):
    executable = find_executable(runtime)
    models = runtime / "models"
    missing = [name for name in REQUIRED_MODELS if not (models / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing model files in {models}: {', '.join(missing)}")
    if destination.exists():
        raise FileExistsError(f"Output already exists at {destination}. Use a different --seed or --output-dir.")

    # Windows builds of the native CLI use narrow paths. Relative ASCII names
    # work even when the project and the subprocess working directory use Hindi.
    with tempfile.TemporaryDirectory(prefix="cue-", dir=runtime) as temporary:
        work = Path(temporary)
        (work / "cue.json").write_text(json.dumps(request) + "\n", encoding="utf-8")
        command = [str(executable), "--models", "../models", "--request", "cue.json",
                   "--vae-chunk", "128", "--vae-overlap", "16"]
        if device != "auto":
            command.extend(("--device", device))
        subprocess.run(command, cwd=work, check=True)

        # ace-synth writes one numbered WAV next to the request.
        audio = work / "cue0.wav"
        with wave.open(str(audio), "rb") as recording:
            if (recording.getnchannels(), recording.getsampwidth(), recording.getframerate()) != (2, 2, 48000):
                raise ValueError("Expected a stereo, 48 kHz, 16-bit WAV from ace-synth.")
            frames = recording.getnframes()
            seconds = frames / recording.getframerate()
            if abs(seconds - request["duration"]) > 0.25:
                raise ValueError(f"Unexpected WAV duration: {seconds:.2f}s.")
            samples = recording.readframes(frames)
            if len(samples) != frames * 4 or not any(samples):
                raise ValueError("ACE-Step produced a truncated or silent WAV.")

        destination.parent.mkdir(parents=True, exist_ok=True)
        with audio.open("rb") as source, destination.open("xb") as output:
            try:
                shutil.copyfileobj(source, output)
            except BaseException:
                output.close()
                destination.unlink()
                raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cue", nargs="?", help="cue ID from the episode's Music_Cues.json")
    parser.add_argument("--episode", default="E01", help="episode folder under Production (default: E01)")
    parser.add_argument("--list", action="store_true", help="list available cues and their durations")
    parser.add_argument("--dry-run", action="store_true", help="print the request without loading a model")
    parser.add_argument("--runtime-dir", default=DEFAULT_RUNTIME, type=Path, help="ACE-Step.cpp folder with models/")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT, type=Path, help="directory for the generated WAV")
    parser.add_argument("--device", default="CPU", help="ACE-Step device (default: CPU), or auto for native selection")
    parser.add_argument("--duration", type=int, help="override the cue duration in seconds")
    parser.add_argument("--seed", type=int, help="override the cue seed for another variation")
    args = parser.parse_args()
    if not re.fullmatch(r"E[0-9]{2,3}", args.episode):
        parser.error("episode must look like E01")
    cue_file = ROOT / "Production" / args.episode / "Audio" / "Music" / "Music_Cues.json"
    try:
        cues = json.loads(cue_file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        parser.error(f"could not read {cue_file}: {error}")

    if args.list:
        for name, cue in cues.items():
            print(f"{name:<16} {cue['duration']:>2}s  {cue['label']}")
        return
    if args.cue is None:
        parser.error("select a cue or use --list")
    if args.cue not in cues:
        parser.error(f"unknown cue {args.cue!r}. Available cues: {', '.join(cues)}")

    cue = cues[args.cue]
    duration = cue["duration"] if args.duration is None else args.duration
    seed = cue["seed"] if args.seed is None else args.seed
    if not 10 <= duration <= 600:
        parser.error("duration must be between 10 and 600 seconds")
    if not 0 <= seed < 2**63:
        parser.error("seed must be a nonnegative signed 64-bit integer")
    request = make_request(cue, duration, seed)
    destination = args.output_dir.resolve() / f"{args.episode}_{args.cue}_{duration}s_{seed}.wav"
    if args.dry_run:
        print(json.dumps(request, indent=2))
        return
    try:
        synthesize(args.runtime_dir.resolve(), args.device, request, destination)
    except (OSError, ValueError, wave.Error, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Music generation failed: {error}\n")
    print(destination)


if __name__ == "__main__":
    # Preserve Devanagari paths when Windows redirects output to a pipe or log.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    main()
