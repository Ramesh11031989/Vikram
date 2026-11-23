# श्याम मुंशी उर्फ़ बेताल

श्याम मुंशी और बेताल एक ही व्यक्ति हैं। यह पूर्व राजकीय मुंशी का 1.75 m adult character asset है। धूसर अंगरखा, हाथ से बुनी धोती और कंधे का सफ़ेद कपड़ा अलग meshes हैं। खुली हथेलियाँ और पैर anatomical mesh पर skinned हैं। बाल, दाढ़ी और भौंहें strand geometry हैं।

| File | Use |
| --- | --- |
| [Betal_Hero.blend](Betal_Hero.blend) | Editable model, 34-bone rig, costume, two ankle states, and staged poses |
| [Betal_Hero.fbx](Betal_Hero.fbx) | Neutral A-pose with the right-ankle swelling shape and separate linen wrapping meshes |
| [Portrait](Betal_Portrait.png) | Face, groom and costume under Blender studio lighting |
| [Right ankle comparison](Betal_Right_Ankle.png) | Swollen state at left and wrapped state at right |
| [Banyan branch](Betal_On_Branch.png) | Seated with the injured ankle hanging free and the closed bundle at hand |
| [On Vikram’s back](Betal_On_Vikrams_Back.png) | Carry pose with the approved Vikram model and the closed bundle |
| [Opening the bundle](Betal_Opening_Bundle.png) | On the chabutra with oilcloth spread over the lap and papers showing |
| [Tying the ankle](Betal_Tying_Ankle.png) | Closing pose beside the banyan root |

## Pose and ankle controls

Open **Betal | Model and rig** for the asset at its bind pose. Select `BetalHero_Rig` and change **Right ankle state** under Object Custom Properties. Set it to **0** for neutral, **1** for the exposed swollen ankle or **2** for the linen wrap over the swelling. The swelling affects the character’s anatomical right. The FBX exposes the same swelling as a blend shape and includes the wrap pieces as separate meshes for visibility control.

Open the corresponding scene for the complete pose, contact points and placement of props. The four Betal poses are also named `Shyam Munshi | …` in the Asset Browser. The **Vikram | Supporting Shyam Munshi** action is the companion carry pose. The open and closed bundle collections are assets. The portrait and staging scenes are static modeling reviews. The [art gates](../../../Production/ART_PASSES.md) cover animation, facial acting and the Unity handoff.

## Rebuild

The builder uses the realistic adult anatomy from [Blender Foundation Human Base Meshes v1.4.1](https://www.blender.org/download/demo-files/#assets), CC0, and the approved Vikram file at `Blender/Characters/Vikram/Vikram_Hero.blend`. The source geometry is appended into the built pose scenes.

```powershell
blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_betal_hero.py -- --base C:/path/to/human_base_meshes_bundle.blend
```
