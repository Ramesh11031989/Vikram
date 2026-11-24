# Vikram-Betal in Unity

Open this `Unity` directory as a Unity **6000.3.25f1** project. The opening scene is [E01_GhatSightlines.unity](Assets/Scenes/E01_GhatSightlines.unity). Enter Play Mode to review the camera cuts, changing waterline and boat turn at the chapter’s 24 fps timebase.

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
