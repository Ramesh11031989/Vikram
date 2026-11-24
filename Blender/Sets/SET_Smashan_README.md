# Set 4 — श्मशान, बरगद और चबूतरा (cremation ground, banyan and platform)

`SET_Smashan.blend` is the cremation-ground set for the Vikram–Betal scenes. It uses a **local map** in metres: +X east, +Y north, Z up, origin on the entrance path. The story gives no route from the ghat or town, so it is not yet placed on the palace map.

## What is in the set

| Area | Contents |
| --- | --- |
| घोड़ा बाँधने की जगह | Two posts with a rail and rope loop outside the gate, and a `MARK \| Horse` empty |
| रास्ता और फाटक | 2.4 m path with edge stones, two gate posts with a lintel, and a low boundary wall |
| बरगद | Trunk with foot flares, surface roots, hanging roots and canopy |
| चढ़ने लायक निचली डाल | Low branch with its top at 1.05–1.12 m along the seat stretch |
| लटकता सफ़ेद कपड़ा | Cloth on the upper branch, with a `Hem lifted` shape key animated on frames 20–96 |
| दो एड़ियाँ | Two heels with ankles, hidden behind the cloth until the hem lifts |
| चबूतरा | 2 × 2 m platform, 0.45 m high, with a 0.22 m step on the path side |
| जड़ पर बैठने की जगह | Exposed root 0.43 m high, clear of the trunk, for the last scene |
| श्मशान | Two pyre beds (one with logs) and four memorial stones |

## Heights, checked against the characters

* Vikram is 1.84 m and Betal is 1.75 m.
* A seated Betal on the low branch sits at about 1.1 m. That is below Vikram's shoulder, so he can back up to it, take Betal on his back, and set him down again.
* The chabutra top at 0.45 m and the root seat at 0.43 m are sitting heights.
* The `MARK | Vikram carries Betal here`, `MARK | Betal seat on chabutra`, `MARK | Betal seat on low branch` and `MARK | Betal seat on root (last scene)` empties give the placement points.

## Cloth and heels

Frames 1–20 hold the cloth down, frames 20–44 lift the hem, frames 44–70 hold it up, and frames 70–96 let it fall. The heels sit 0.22 m behind the cloth plane. `validate_smashan_set.py` ray-casts from the path camera: the cloth blocks both heels on frame 1 and 96, and nothing blocks them once it is lifted.

## Cameras

`CAM | Cloth and heels from the path` (active), `CAM | Heels close`, `CAM | Entrance and horse`, `CAM | Banyan, branch and chabutra`, `CAM | Root seat` and `CAM | Top map (smashan)`.

## Rebuild, check and render

Replace `blender` with `D:\Tools\Blender\blender-5.2.2-windows-x64\blender.exe` (see [AGENTS.md](../../AGENTS.md)).

```powershell
blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_smashan_set.py
blender --background --python-exit-code 1 Blender/Sets/SET_Smashan.blend --python Blender/tools/validate_smashan_set.py
blender --background --python-exit-code 1 Blender/Sets/SET_Smashan.blend --python Blender/tools/render_smashan_set.py -- --percent 50 --samples 32
```

| Script | Builds |
| --- | --- |
| `smashan_layout.py` | Positions, limb profiles and heights (no Blender needed) |
| `smashan_world.py` | Materials, ground, path, wall, gate and horse post |
| `smashan_story.py` | Banyan, cloth and heels, chabutra, pyres, light and cameras |
| `build_smashan_set.py` | Runs all of them, saves the `.blend` and `SET_Smashan_Manifest.json` |
| `validate_smashan_set.py` | 14 checks, writes `SET_Smashan_Validation.json` (all pass) |
| `render_smashan_set.py` | Review stills in `Blender/Previews/Sets/` |

## Guesses and limits

* All positions and sizes are guesses. The story fixes only the order: horse, banyan, cloth, heels, branch, root.
* The heels are simple stand-ins, not the Betal rig. Swap in the rig at `MARK | Heels` if needed.
* The banyan canopy is made of simple blobs, and the leaves are not modelled individually.
* The cloth moves by a shape key, not a cloth simulation.
* The scene is lit by a moon sun and a dark sky only.
