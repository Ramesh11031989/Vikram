# Vikram-Betal in Unity

Open this `Unity` directory as a Unity **6000.3.25f1** project. The opening scene is [E01_GhatSightlines.unity](Assets/Scenes/E01_GhatSightlines.unity). Enter Play Mode to review the camera cuts, changing waterline and boat turn at the chapter’s 24 fps timebase.

## Gopal’s testimony

Open [E01_SC04_Performance.unity](Assets/Scenes/E01_SC04_Performance.unity) and press Play to see the 11-shot testimony. The scene plays the synchronized soundtrack with the baked body, camera, prop and costume motion. The live mouth controller applies Kokoro’s Hindi phoneme timings to the cast’s imported blend shapes. The soundtrack includes two Hindi voices, foley and the ACE-Step river and court cues. The [film export](../Production/E01/Unity_Review/E01_Gopal_Testimony_Unity.mp4) adds a Devanagari title and timed dialogue captions.

The cut covers Gopal’s testimony in Chapter 1. The Blender performance scene remains the source of the acting and camera work. The witness by the diya has a shaped nape, ears and a mesh hair groom on the original animated rig. His turned head preserves the limits of what Gopal saw. Unity uses its own real-time lights and materials, and the batch capture evaluates the skinned poses and lip shapes for every exported frame.

To replace the readings, generate a new set and viseme track with the [dialogue instructions](../Production/E01/ANIMATIC_README.md) and the [lip-sync instructions](../Production/E01/PERFORMANCE_README.md). Place that `Unity_Visemes.json` in `Unity/Assets/Art/E01/SC04`. Rebuild the soundtrack and scene against the same 1,484-frame edit.

```powershell
$blender = 'D:\Tools\Blender\blender-5.2.2-windows-x64\blender.exe'
$python = 'D:\Tools\Blender\blender-5.2.2-windows-x64\5.2\python\bin\python.exe'
$unity = 'D:\Unity\Hub\Editor\6000.3.25f1\Editor\Unity.exe'

& $blender --background 'Production/E01/Performance/E01_SC04_Performance_Current_Cast.blend' --python-exit-code 1 --python Blender/tools/export_sc04_unity.py
& $python -X utf8 Production/tools/compose_sc04_unity.py --mix-only --output Unity/Assets/Art/E01/SC04/Soundtrack.wav
$projectPath = '"' + (Resolve-Path 'Unity').Path + '"'
$renderLog = New-Item -ItemType Directory -Path 'Renders/Unity' -Force
$logPath = '"' + (Join-Path $renderLog.FullName 'sc04_unity_film.log') + '"'
$run = Start-Process -FilePath $unity -ArgumentList @('-batchmode', '-force-d3d11', '-projectPath', $projectPath, '-executeMethod', 'Vikram.Editor.BuildPerformanceFilm.BuildProofsAndFilm', '-logFile', $logPath, '-quit') -Wait -PassThru -WindowStyle Hidden
if ($run.ExitCode -ne 0) { throw 'Unity film render failed. Check the render log.' }
& $python -X utf8 Production/tools/compose_sc04_unity.py --timeline Production/E01/Unity_Review/E01_SC04_Unity_Timeline.json --use-soundtrack Unity/Assets/Art/E01/SC04/Soundtrack.wav
```

Run from the repository root. Add FFmpeg and FFprobe to `PATH` or pass the binaries to the Python script with `--ffmpeg` and `--ffprobe`. Unity writes its render frames under `Renders/Unity/E01_SC04/frames`. To encode newly generated readings, use their matching timing file from `Renders/E01_SC04_Dialogue` in the final command. The master script checks the final picture count and soundtrack duration before replacing the output movie.

## Ghat sightlines

| Blender frame | Review |
| ---: | --- |
| 1 | Palace window, five dry treads at −2.2 m |
| 49 | Same window and lens, three dry treads at −1.4 m |
| 97 | Halwai’s rooftop view across the market |
| 145 | Gopal’s seated view of the diya and the red cloth |
| 238 | Boat and seated camera turned downstream |

Unity editor captures for each review frame are available as [001](../Production/E01/Unity_Review/E01_Unity_001.png), [049](../Production/E01/Unity_Review/E01_Unity_049.png), [097](../Production/E01/Unity_Review/E01_Unity_097.png), [145](../Production/E01/Unity_Review/E01_Unity_145.png) and [238](../Production/E01/Unity_Review/E01_Unity_238.png).

The editable Blender file holds the authored procedural materials. The Unity builder uses exported colors, emission, metallic and roughness for the initial material pass. It imports the palace, ghat and town as groups, with the actor, boat, gate and water as separate scene objects. The reusable river shader takes the scene’s day or night state and animates ripples from the shot clock. [Blender sightlines and evidence](../Production/E01/Sightlines/README.md)

Chapter 1’s AI dialogue generator is available in `Production/tools/prepare_sc04.py`. It runs locally once the model weights are available. The current Unity sightline scene is a silent camera and lighting review. [AI voice generation and cue preparation](../Production/E01/ANIMATIC_README.md)

## Build the Unity scene from Blender

The FBXs and shot data are in `Assets/Art/E01/GhatSightlines/`. `SightlineTimeline` uses the shot table, tracks and lighting cues to drive the Unity scene and can be reused with another shot manifest. To update the export or check it in batch mode, run these commands from the repository root.

```powershell
$blender = 'D:\Tools\Blender\blender-5.2.2-windows-x64\blender.exe'
$unity = 'D:\Unity\Hub\Editor\6000.3.25f1\Editor\Unity.exe'
& $blender --background 'Production/E01/Sightlines/E01_Ghat_Sightlines.blend' --python-exit-code 1 --python Blender/tools/export_e01_unity_sightlines.py
& $unity -batchmode -nographics -projectPath (Resolve-Path 'Unity').Path -executeMethod Vikram.Editor.BuildGhatSightlines.Run -logFile - -quit
& $unity -batchmode -projectPath (Resolve-Path 'Unity').Path -executeMethod Vikram.Editor.BuildGhatSightlines.RenderProofs -logFile - -quit
```

In the editor, use **Tools → Vikram → E01 → Build Ghat Sightlines** to rebuild the generated scene from the FBXs and manifest. Keep shot-specific Unity edits in a separate scene when you need to regenerate this review.
