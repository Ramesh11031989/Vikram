# Interrogation performance — v0.3

This pass turns the eleven-shot panel animatic into continuously keyed 3D
performance. The original dialogue and 1,484-frame / 61.833-second edit are kept.

## Files

| File | Purpose |
| --- | --- |
| `Performance/E01_SC04_Performance_v0_3.mp4` | Full motion review with Hindi captions and synthetic voices |
| `Performance/E01_SC04_Performance_v0_3.blend` | Editable scene, grounded acting, facial/costume artwork, prop animation and relative dialogue link |
| `Performance/LipSync/` | Twelve acoustic viseme analyses and source-audio hashes |
| `Performance/Exports/` | Four neutral FBX characters with deformation rigs and facial blend shapes |
| `Performance/Proofs/` | Representative scene compositions |
| `Audio/E01_SC04_Performance_Mix.wav` | Dialogue plus locally synthesized room, river and foley cues |
| `Audio/E01_SC04_Ambience_Foley.wav` | Separate ambience/foley stem |
| `E01_SC04_Performance_Manifest.json` | Scope, rendering settings and original-mesh hashes |
| `E01_SC04_Polish_Manifest.json` | Woven materials, facial artwork, stitches, embroidery and natural-movement layers |
| `E01_SC04_Performance_Scene_Check.json` | Scene and control checks |
| `E01_SC04_Performance_Media_Check.json` | Final frame count, duration and motion-sampling checks |
| `E01_SC04_Cast_Export_Check.json` | Four FBX round-trip checks |

The completed scene, facial FBX assets, audio, high-resolution proofs and review
video are versioned with the project. The downloadable review package is another
way to open the same deliverables: extract it at the repository root, keeping
`Production/E01/Performance` beside `Production/E01/Audio`. Temporary frame/video
caches and the intermediate v0.2 scene are ignored.

The included v0.3 scene and movie keep the cast geometry used for this performance
pass. The separate cast library also contains later surface and groom work.
Rebuilding the performance uses the current cast generator; render the rebuilt
scene and export its FBX assets together to refresh those deliverables.

## What changed

- **Acting:** continuous breath and weight movement; an opening step, Gopal's
  shoulder demonstration and admission gesture, Vikram's listening and question
  reactions, and a small camera move into the final exchanges.
- **Speech:** 271 acoustic speech-shape segments from the existing twelve WAVs,
  mapped to eight mouth controls. Mouths hold their rest state before each cue.
- **Facial controls:** blinks, brows, worry/smile, eye-bone gaze and new speech
  shapes on Vikram, Gopal, Betal and the court clerk. The original 273 Vikram/Gopal
  rest meshes are preserved; controls and mouth-interior geometry are added.
- **Court clerk:** a distinct supporting character with a kurta, cap and spectacles,
  two hand IK targets, a writing action, reed pen, inkpot and ledger strokes. This
  is not Betal, the former clerk.
- **River:** dressed anonymous back-view figure, folded red cloth, lamp flicker,
  analytic water waves, scaled hand insert and animated contact ripples. The
  figure has no facial features and is never shown from the front. Gate
  movement is not introduced as evidence.
- **Sound:** footsteps, cloth, oar knock, finger/water contact, pen friction and
  a restrained room/river bed. All foley in this pass is synthesized locally.

The v0.3 polish adds planted-foot IK, phrase-aware blinks with a small left/right
offset, restrained gaze and brow asymmetry, less periodic head motion and
secondary cloth settling. It adds subtle skin colour/roughness variation,
expression creases, woven costume surfaces, seam stitchwork and restrained gold
diamond embroidery on Vikram's sash. Faces, hair, costume silhouettes and the
main palette are retained. Leg pole rotation is calibrated against the approved
rest pose so planted feet do not twist the trousers.

## Review quality and limits

The review renders **960 × 540**, with one unique motion sample every two
timeline frames, then encodes the edit at **24 fps**. This is animation on twos,
not a panel zoom edit. The editable scene and audio timing remain at 24 fps.
Higher-resolution rendering and sampling every frame are available below.

The dialogue remains the replaceable synthetic readings from v0.1. Both roles
use the same stock Hindi voice with different delivery settings. No actor
recording or approved final casting is claimed.

Rhubarb's **phonetic** recognizer estimates acoustic visemes for non-English
recordings. This improves speech shapes over amplitude-only motion; it is not a
linguist-verified Hindi phoneme transcript. Review pronunciation and mouth
performance before final delivery. Water uses analytic surface animation rather
than a fluid simulation.

## Blender controls

Open the main scene `E01_SC04 | Performance v0.3`. Character rigs expose speech
and expression controls in Custom Properties. The separate `Library | ...`
scenes retain the four reusable characters, including Betal, who is absent from
the interrogation shot itself.

| Controls | Use |
| --- | --- |
| `Mouth_Ah`, `Mouth_O`, `Mouth_Ee`, `Mouth_MBP`, `Mouth_FV` | Core speech shapes |
| `Mouth_U`, `Mouth_L`, `Mouth_Consonant` | Additional speech shapes |
| `blink_L`, `blink_R` | Eyelid closure |
| `brow_raise`, `brow_frown` | Listening and uncertainty |
| `brow_asymmetry` | Small left/right brow difference |
| `mouth_worry`, `mouth_smile` | Subtle mouth-corner expression |
| `eye.L`, `eye.R` pose bones | Gaze |
| `CourtClerk_Hand_R_Control`, `CourtClerk_Hand_L_Control` | Writing-hand IK |
| `Vikram_Foot_*_Control`, `Gopal_Foot_*_Control` | Planted-foot IK and the opening step |

The neutral FBX exports contain the deformation skeleton and blend shapes.
Blender's custom-property drivers and IK targets do not become a complete facial
controller in another application; rebind those blend shapes or bake the desired
performance there. These FBX files are neutral assets, not exported movie clips.
The woven/skin materials are Blender procedural shaders; FBX users must recreate
or bake those material details in their destination application. Mesh stitches,
embroidery and facial blend shapes are included in the exported geometry.

## Build and resume

The workflow was run in Blender 4.3.2. The original Blender 5.2.2 cast library is
not overwritten. Run from the repository root:

```powershell
python -m pip install -r Production/requirements.txt

# Install Rhubarb Lip Sync 1.14.0 for your OS; give the actual executable path.
python Production/tools/prepare_sc04_lipsync.py --rhubarb C:/Tools/Rhubarb/rhubarb.exe

blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_sc04_performance.py

blender --background Production/E01/Performance/E01_SC04_Performance_v0_2.blend --python-exit-code 1 --python Blender/tools/polish_sc04_performance.py

blender --background Production/E01/Performance/E01_SC04_Performance_v0_3.blend --python-exit-code 1 --python Production/tools/validate_sc04_performance_scene.py

blender --background Production/E01/Performance/E01_SC04_Performance_v0_3.blend --python-exit-code 1 --python Blender/tools/render_sc04_performance.py

python Production/tools/compose_sc04_performance.py

blender --background Production/E01/Performance/E01_SC04_Performance_v0_3.blend --python-exit-code 1 --python Blender/tools/export_sc04_facial_cast.py
```

Rhubarb downloads: [official releases](https://github.com/DanielSWolf/rhubarb-lip-sync/releases/tag/v1.14.0).
Use Noto Sans Devanagari for the Hindi captions and FFmpeg with libass/libx264.
The existing scratch recordings can be analyzed offline once Rhubarb is installed.

Rendering caches complete PNG frames under a directory derived from the scene
hash and sampling settings. Rerun the same render command after interruption to
reuse complete frames. Rebuilding the scene changes its hash and starts a fresh
cache. Old caches can be removed after a successful review export.

For a frame-by-frame render, append `-- --step 1 --samples 32` to the render
command. Increase the saved scene's resolution for a larger output. Ray-tracing
or higher-quality Eevee settings should be chosen for the final render on the
target workstation; the cloud review settings prioritize completion of the
performance pass.

For 1080p review stills, append `-- --proof 1031 1249 --step 1 --samples 8 --scale 2`
to the render command. These higher-resolution proofs are saved with an `_2x`
suffix under `Performance/Proofs`.

## Editorial review

Review the L10 admission, the L03 boat turn across the cut, the visibility of the
red cloth and the clerk's writing. Final voice casting, pronunciation approval
and shot-specific performance polish remain editorial decisions. The two source
chapters and their evidence-based story logic are unchanged.
