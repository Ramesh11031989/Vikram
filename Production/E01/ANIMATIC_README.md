# E01 SC04 — interrogation animatic v0.1

This is a timed, staged 3D panel edit of Gopal's questioning. It uses the existing
Vikram and Gopal character generators, synthetic Hindi scratch dialogue, and
simple court and river blocking sets. The original chapters, shooting script,
cue sheet, cast library and FBX exports remain the source references.

Generated video, audio, panels and the editable scene are delivered in the review
package rather than stored as Git blobs. Extract that package into the repository
root to use the prepared assets, or regenerate them with the commands below.

## Review files

| File | Purpose |
| --- | --- |
| `Animatic/E01_SC04_Animatic_v0_1.mp4` | 1280 × 720 review video, 24 fps, Hindi captions |
| `Animatic/E01_SC04_Storyboard.jpg` | All eleven shot compositions |
| `Animatic/E01_SC04_Animatic.blend` | Editable court/river staging, eleven shot cameras, body/mouth blocking keys and scratch sound strip |
| `E01_SC04_Animatic_Timeline.json` | Measured dialogue and shot timing; exclusive out frames |
| `E01_SC04_Dialogue_Timed.csv` | Audio-adjusted dialogue cues; original timings retained in separate columns |
| `E01_SC04_Animatic.srt` | Hindi subtitles |
| `Audio/Scratch/` | Twelve replaceable mono 24 kHz PCM dialogue files and voice provenance |
| `E01_SC04_Validation.json` | Cross-file timing and media validation result |

The first pass runs **1,484 frames / 61.833 seconds**. The original pilot plan is
1,428 frames / 59.5 seconds. L01, L06, L09 and L11 need additional room with the
current synthetic readings. L03 continues across the SH03/SH04 cut. Speech is
never sped up to fit the original slots.

## Editorial intent

- Betal remains Shyam Munshi, the former clerk. He does not appear in this scene.
- The court clerk is a separate, anonymous blocking figure.
- The river figure has no face detail. The red cloth is observed; identity and
  gate movement remain unproven.
- The niece appears only as a hand insert. Her full character is outside this pass.
- Daylight court shots and cooler lamp-lit river shots distinguish the interview
  from Gopal's recollection.

## Scope of this pass

The review video is an animatic: staged rendered panels, cuts, gentle framing
moves, and scratch sound. The Blender scene includes FK gesture keys and simple
audio-amplitude mouth keys for a later motion pass; those are not a finished
performance or phoneme-accurate lip sync. Sets, water, the court clerk and river
inserts are production stand-ins. Placeholder room/water ambience is synthesized
locally, and there is no music.

Both speaking roles currently use `hi-IN-MadhurNeural`, with different rate and
pitch settings. These are stock synthetic scratch performances, not actor
recordings or approved final voices. Replace the individual WAV files with the
approved readings and rebuild the timeline before final animation.

## Rebuild

Requirements: Python 3.10+, FFmpeg/ffprobe with libx264 and libass, and Blender.
The new scene generator was run with Blender 4.3.2. The original cast library
still specifies Blender 5.2.2 and is not rewritten by this workflow.

Run from the repository root:

In the commands below, replace `blender` with `D:\Tools\Blender\blender-5.2.2-windows-x64\blender.exe` (see [AGENTS.md](../../AGENTS.md)).


```powershell
python -m pip install -r Production/requirements.txt

# The committed WAV files can be retimed entirely offline.
python Production/tools/prepare_sc04.py

# Optional: regenerate synthetic scratch readings. This sends the twelve lines
# to the Microsoft Edge speech service and requires an internet connection.
python Production/tools/prepare_sc04.py --generate-speech

blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_sc04_animatic.py

# Install Noto Sans Devanagari for correct Hindi caption shaping.
# Give --font a local Latin font path if the default Linux font is unavailable.
python Production/tools/compose_sc04.py
python Production/tools/validate_sc04.py

blender --background Production/E01/Animatic/E01_SC04_Animatic.blend --python-exit-code 1 --python Production/tools/validate_sc04_scene.py
```

Use a full executable path if Blender or FFmpeg is not on PATH. On Windows,
pass `--font C:/Windows/Fonts/arial.ttf` to the compose command. To trust an
organization's additional certificate bundle for speech generation, provide
`--ca-bundle path/to/trusted-ca.pem`; TLS certificate verification stays enabled.

The Blender builder overwrites its derived scene and rendered panels under
`Animatic/`. Run it in a separate checkout when experimenting. It does not write
`Blender/Vikram_Betal_Cast.blend` or the original FBX exports.

To render selected panels after a framing adjustment, append, for example,
`-- --shots SH01 SH10 SH11` to the Blender command. A normal run renders all
eleven panels. CPU ray tracing dominates build time; this panel edit renders
eleven frames rather than all 1,484 frames of a full motion pass.

## Next production pass

Review Hindi pronunciation, pauses, shot geography and the emotional change in
L10. Then approve or replace the performances, refine the court clerk and the
river inserts, animate full body acting and eye movement, and complete facial
controls and phoneme timing before the final render.
