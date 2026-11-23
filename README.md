# विक्रम-बेताल: तर्क पच्चीसी

Hindi animated series made with Blender and Unity. The first chapter is **सात गवाह, एक आवाज़**.

| File | Use |
| --- | --- |
| [Chapter 1](अध्याय%2001%20-%20सात%20गवाह,%20एक%20आवाज़.md) | Original Hindi story |
| [Chapter 2](अध्याय%2002%20-%20जिस%20मुहल्ले%20में%20कोई%20नहीं%20मरा.md) | Original Hindi story |
| [Pilot shooting script](Production/E01/E01_SC04_Pilot_Shooting_Script.md) | Gopal's testimony, 11 shots at 24 fps |
| [Dialogue cue sheet](Production/E01/E01_SC04_Dialogue_Cues.csv) | Hindi dialogue IDs, provisional timing, performance notes and WAV filenames |
| [Interrogation animatic](Production/E01/ANIMATIC_README.md) | Eleven staged shots, synthetic Hindi scratch dialogue, audio-measured timing and editable Blender scene |
| [Interrogation performance](Production/E01/PERFORMANCE_README.md) | Grounded acting, facial/costume detail, acoustic lip sync, rigged clerk and animated river inserts |
| [Performance review video](Production/E01/Performance/E01_SC04_Performance_v0_3.mp4) | Completed v0.3 motion review with Hindi captions and synthetic scratch voices |
| [Editable performance scene](Production/E01/Performance/E01_SC04_Performance_v0_3.blend) | Polished scene with four reusable facial rigs, planted-foot acting and costume artwork |
| [Blender cast library](Blender/Vikram_Betal_Cast.blend) | Editable Vikram, Betal and Gopal models and rigs |
| [FBX exports](Blender/Exports/) | Rest-pose models with skeletons, skinning and mouth shapes |

![Preview of Vikram, Betal and Gopal](Blender/Previews/Cast_Lineup.png)

## Using the cast library

Open `Blender/Vikram_Betal_Cast.blend` in Blender 5.2.2. The file opens on `Cast Preview`. Switch to the `Vikram`, `Betal` or `Gopal` scene to edit a character at the origin. To use a character in a new Blender file, append the corresponding `CH_` collection from the library. Use the armature in Pose Mode for body movement. On the character's `Mouth` mesh, use the `Mouth_Ah`, `Mouth_O`, `Mouth_Ee`, `Mouth_MBP` and `Mouth_FV` shape keys to pose dialogue.

The FBX files are the starting point for Unity import. Material appearance should be checked against the Blender preview, especially metal trim and near-skin details. The character scenes use the same bone names and 24 fps timebase so later episodes can reuse clips. Add episode-specific material, shots and audio under `Production/E02` and the corresponding episode folder in the Unity project as production progresses.

The editable `.blend` is the working asset. `Blender/tools/build_cast.py` recreates the initial library and exports as kept in this repository. Run it in a separate checkout when testing changes to the generator, since it writes the same output filenames.

```powershell
blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_cast.py
```

For a portable install, use the full `blender.exe` path in the command.
