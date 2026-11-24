# गोपाल, नाविक

गोपाल का चेहरा `Blender/Previews/Cast_Detail.png` के दाएँ वाले रेफ़रेंस पर आधारित है। नए adult sculpt में चौड़े गाल, पतली दो-हिस्सों वाली मूँछ, छोटी पीतल की बाली, फ़िरोज़ी सिरपट्टी और बाएँ कंधे का गेरुआ कपड़ा रखा गया है। बाल और मूँछें अलग-अलग पतले रेशों से बने हैं। दोनों पैरों की सूखी गाद का रंग, किनारे और दरारें उसी skin mesh पर हैं जिस पर पैर deform होते हैं।

| File | Use |
| --- | --- |
| [Gopal_Hero.blend](Gopal_Hero.blend) | Editable 1.78 m character, 34-bone rig, garments, look development and story scenes |
| [Gopal_Hero.fbx](Gopal_Hero.fbx) | Neutral skinned model with material slots and vertex colors |
| [Portrait](Gopal_Portrait.png) | Face, swept groom, headband and left shoulder cloth |
| [Dry silt](Gopal_Dry_Silt.png) | Clean feet at left and dry river silt at right |
| [At the oar](Gopal_At_The_Oar.png) | Two-handed oar grip inside the boat |
| [Oblique testimony](Gopal_Oblique_Testimony.png) | Gopal stands across the chalk river to show his limited view from the boat |
| [Reaching toward his niece](Gopal_Reaching_For_His_Niece.png) | Gopal extends his right hand while recalling the moment in court |

Append `CH_GopalHero` from the `.blend` or open **Gopal | Model and rig** to edit the neutral model. The story scenes keep their cameras, pose and props editable. Use the scene selector to switch among them. The **Gopal | Dry silt comparison** scene shows a clean-foot material override. To repeat it, assign `GopalHero • Skin` to the foot material slot on an instance of the skin mesh.

The skiff, oar and chalk plan are Blender collection assets. For the shot assembly, use the existing boat route and seated-eye cameras in `Blender/Sets/SET_Ghat.blend`, the interrogation room in `Blender/Sets/SET_Palace.blend`, and the **Hand in water** pose in `Blender/Characters/Gopal_Niece/Gopal_Niece.blend` when those local art packages are available. The oblique view and right-hand gesture are both staged in the court. The niece belongs in the river insert from his testimony.

The FBX is the neutral model handoff. For Unity, use a vertex-color shader for the included foot tint and recreate the Blender shader’s grain, roughness and drying cracks. The three posed scenes and rig actions are saved in Blender. Facial animation and lip sync follow in the performance pass.

## Rebuild

The anatomy is based on [Blender Studio Human Base Meshes v1.4.1](https://www.blender.org/download/demo-files/#assets), CC0.

Replace `blender` with `D:\Tools\Blender\blender-5.2.2-windows-x64\blender.exe` (see [AGENTS.md](../../../AGENTS.md)).


```powershell
& 'D:\Tools\Blender\blender-5.2.2-windows-x64\blender.exe' --background --factory-startup --python-exit-code 1 --python Blender/tools/build_gopal_hero.py -- --base C:/path/to/human_base_meshes_bundle.blend
```
