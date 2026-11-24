# सहायक दरबारी मुंशी

Assistant court scribe. He records testimony and writes the return (वापसी) beneath the old order. The two scribes' writing styles from the story's opening are shown as two handwritings on his slanted desk:

| Hand | Look |
| --- | --- |
| Old order (upper sheet) | Broad, upright, evenly spaced, heavy black ink |
| Return (lower sheet, his own) | Small, right-slanted, tight, thin brown ink |

The writing is modelled as stroke geometry (headline plus stems, bowls, hooks and tails), so it needs no font. It is decorative, not legible text. Style parameters are `HAND_OLD` and `HAND_RETURN` in `Blender/tools/court_munshi.py`.

| File | Use |
| --- | --- |
| `Sahayak_Darbari_Munshi.blend` | Editable model, 34-bone rig shared with the cast |
| `CH_SahayakDarbariMunshi.fbx` | Skinned handoff (rig and meshes, no animation) |
| `Sahayak_Darbari_Munshi.png` | Full-body review render |
| `Sahayak_Darbari_Munshi_Handwriting.png` | Top-down view of the two handwritings |

Rebuild from the repository root (see AGENTS.md for the Blender path):

```powershell
& 'D:\Tools\Blender\blender-5.2.2-windows-x64\blender.exe' --background --factory-startup --python-exit-code 1 --python Blender/tools/build_court_munshi.py
```

Limitations: the desk and papers are weighted to `root`, so they stay fixed. There is no writing animation or IK yet.
