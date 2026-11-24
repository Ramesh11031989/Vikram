# विक्रम-बेताल: तर्क पच्चीसी

Hindi animated series made with Blender and Unity. The first chapter is **सात गवाह, एक आवाज़**.

| File | Use |
| --- | --- |
| [Vikram hero model](Blender/Characters/Vikram/README.md) | Adult character model with an anatomical bind pose, layered court costume and Blender review renders |
| [श्याम मुंशी उर्फ़ बेताल](Blender/Characters/Betal/README.md) | Former royal clerk, with a right-ankle state control and four story poses |
| [गोपाल, नाविक](Blender/Characters/Gopal/README.md) | Adult boatman, dry-silt foot material, and three editable Chapter 1 poses |
| [Chapter 1 sightlines and asset screenshots](Production/E01/Sightlines/README.md) | Shared Palace, Ghat and Town scene, five camera proofs and a visual review of the Chapter 1 assets |
| [Chapter 1 Unity project](Unity/README.md) | Imported ghat scene, three cameras, water and boat animation, and the Blender-to-Unity rebuild |
| [नंदू](Blender/Nandu.blend) · [नंदू की बेटी](Blender/Nandu_Daughter_README.md) | Gatekeeper, bound hands, daughter and the shared reed boat |
| [हलवाई](Blender/Halwai_README.md) · [पड़ोसन](Blender/Previews/HalwaiNeighbour/HalwaiNeighbour_Notes.md) | Rooftop witness and the tether-cutting scene |
| [बाकी गवाह](Blender/Characters/Citizen_Witnesses/README.md) · [मौसी का ब्लॉकआउट](mausi_witness_both.blend) | Reusable citizen rigs and the aunt’s two staged scenes |
| [काग़ज़ और राजकीय सबूत](Blender/Props/Documents/Documents.blend) | Seven statements, arrival list, order, withdrawal, tally, decree and ledger |
| [सहायक: दो नाविक](Blender/Characters/Sailor_Assistants/README.md) | Two sailor assistants who write the refuge list on the slope, built on the citizen rig with boatman dress, for the previous-night scenes |
| [Agent notes](AGENTS.md) | Blender 5.2.2 executable path (`D:\Tools\Blender\blender-5.2.2-windows-x64\blender.exe`) and scripting conventions |
| [Art production gates](Production/ART_PASSES.md) | Modeling, palace kit, performance, reusable effects and export checks |
| [Chapter 1](अध्याय%2001%20-%20सात%20गवाह,%20एक%20आवाज़.md) | Original Hindi story |
| [Chapter 2](अध्याय%2002%20-%20जिस%20मुहल्ले%20में%20कोई%20नहीं%20मरा.md) | Original Hindi story |
| [Pilot shooting script](Production/E01/E01_SC04_Pilot_Shooting_Script.md) | Gopal's testimony, 11 shots at 24 fps |
| [Dialogue cue sheet](Production/E01/E01_SC04_Dialogue_Cues.csv) | Hindi dialogue IDs, provisional timing, performance notes and WAV filenames |
| [Interrogation animatic](Production/E01/ANIMATIC_README.md) | Eleven staged shots, synthetic Hindi scratch dialogue, audio-measured timing and editable Blender scene |
| [Interrogation performance](Production/E01/PERFORMANCE_README.md) | Grounded acting, facial/costume detail, acoustic lip sync, rigged clerk and animated river inserts |
| [Performance review video](Production/E01/Performance/E01_SC04_Performance_v0_3.mp4) | Completed v0.3 motion review with Hindi captions and synthetic scratch voices |
| [Current cast performance scene](Production/E01/Performance/E01_SC04_Performance_Current_Cast.blend) | Working interrogation scene with the merged acting and latest hair, skin and fabric art |
| [v0.3 review scene](Production/E01/Performance/E01_SC04_Performance_v0_3.blend) | Editable scene used for the existing review video |
| [Set 1: महल](Blender/Sets/SET_Palace_README.md) | Private chamber, interrogation room and open court |
| [Set 2: नदी, घाट और फाटक](Blender/Sets/SET_Ghat_README.md) | River bend, steps, gate, chowki and Gopal’s boat route |
| [Set 3: निचली बस्ती और अनाज मंडी](Blender/Sets/SET_Town_README.md) | Halwai roof, front roof, neighbour's cattle place, tall grain-market shed, open refuge floor and modular houses, on the same map as the palace and ghat sets |
| [Set 4: श्मशान, बरगद और चबूतरा](Blender/Sets/SET_Smashan_README.md) | Horse tie, banyan with a low climbing branch, hanging white cloth over two heels, entrance path, chabutra seat and a root seat for the last scene, on a local map |
| [Set 5: शरण की ढलान और बेताल की झोपड़ी](Blender/Sets/SET_Sharan_README.md) | Refuge slope with 14 numbered seats (Gopal third, eleven after him), the sailors' list board, a footpath up the slope and the outside of Betal's hut, on a local map |
| [Blender cast library](Blender/Vikram_Betal_Cast.blend) | Editable Vikram, Betal and Gopal models and rigs |
| [Current cast facial FBX exports](Production/E01/Performance/Exports/Current_Cast/) | Neutral models for Vikram, Gopal, Betal and the court clerk, with extended speech and expression shapes |
| [Cast-library FBX exports](Blender/Exports/) | Latest strand-groom geometry for Vikram, Gopal and Betal, with five speech shapes |
| [Surface detail](Blender/Previews/Cast_Detail.png) | Close-up of the strand grooms, skin, eyes, lips and woven cloth |
| [Betal sash motion](Blender/Previews/Betal_Cloth_Wind.mp4) | Three-second wind test at 24 fps |

![Preview of Vikram, Betal and Gopal](Blender/Previews/Cast_Lineup.png)

## Using the cast library

Open `Blender/Vikram_Betal_Cast.blend` in Blender 5.2.2. The file opens on `Cast Preview`. Switch to the `Vikram`, `Betal` or `Gopal` scene to edit a character at the origin. To use a character in a new Blender file, append the corresponding `CH_` collection from the library. Use the armature in Pose Mode for body movement. On the character's `Mouth` mesh, use the `Mouth_Ah`, `Mouth_O`, `Mouth_Ee`, `Mouth_MBP` and `Mouth_FV` shape keys to pose dialogue.

Use the `Surface Detail` scene to inspect the eye contour, iris, lip shapes, hair fibers, and fabric weave up close. Each groom uses tapering mesh fibers weighted to the head. The shared textile shader uses rest-mesh coordinates so the weave follows the garment as it deforms.

Open `Betal • Cloth Wind Test` and scrub frames 1–72 to see the baked sash motion. The panel is pinned at the knot and responds to an animated gust. It has self-collision and collision surfaces on the waist wrap and dhoti. The cloth's custom properties show the sampled peak and its frame. Free the bake in the cloth cache before changing the wind or the garment and baking again.

Continue the interrogation from the Current Cast performance scene. It contains the 11-shot edit, keyed acting and lip sync, and a relative link to the dialogue mix in `Production/E01/Audio`. The [performance rebuild](Production/E01/PERFORMANCE_README.md#build-and-resume) describes how to regenerate it from the current cast artwork.

Import the Current Cast facial FBXs into Unity with **Animation Type** set to **Generic**, **Avatar Definition** set to **Create From This Model**, and blend shapes enabled. The scene's body animation and speech curves live in Blender and need baking or rebinding for the Unity cut. Recreate the Blender shader and cloth settings for the Unity materials and simulation. The character scenes use the same bone names and 24 fps timebase so later episodes can reuse clips. Add episode-specific material, shots and audio under `Production/E02` and the corresponding episode folder in the Unity project as production progresses.

The editable `.blend` is the working asset. `Blender/tools/build_cast.py` recreates the initial library and exports as kept in this repository. Run it in a separate checkout when testing changes to the generator, since it writes the same output filenames.

```powershell
blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_cast.py
blender --background Blender/Vikram_Betal_Cast.blend --python-exit-code 1 --python Blender/tools/build_cast.py -- --wind-video
```

For a portable install, use the full `blender.exe` path in the command.

### Blender location on this machine

Blender 5.2.2 LTS is installed at `D:\Tools\Blender\blender-5.2.2-windows-x64\`. `blender` is not on PATH, so replace `blender` in every command in this repository's docs with the full executable path:

```powershell
& 'D:\Tools\Blender\blender-5.2.2-windows-x64\blender.exe' --background --factory-startup --python-exit-code 1 --python Blender/tools/build_cast.py
```

From WSL the same file is `/mnt/d/Tools/Blender/blender-5.2.2-windows-x64/blender.exe`. See [AGENTS.md](AGENTS.md) for notes aimed at AI agents.

use git from WSL
