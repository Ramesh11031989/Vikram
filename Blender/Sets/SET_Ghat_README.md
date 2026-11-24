# Set 2 — नदी, घाट और फाटक (river, ghat and gate)

`SET_Ghat.blend` is the night ghat from Gopal's testimony. It uses the same world map as `SET_Palace.blend`: metres, +X east, +Y north, Z = 0 at the top quay, origin at the top step centre.

## What is in the set

| Area | Contents |
| --- | --- |
| नदी का मोड़ | River bend with near and far banks, bed and night water at Z −1.4 m (3 dry treads, same as the palace evening frame) |
| पत्थर की सीढ़ियाँ | 8 stone steps of 0.40 m, each with stepped cheek walls and two mooring posts |
| उठने वाला फाटक | Two stone posts, head beam, windlass, iron-and-teak grille. It stays down through frame 149 and rises on frames 150–210, after the testimony |
| चौकी | Stone platform, rear wall and posts, thatched shade |
| दीये की जगह | Lamp pillar, ledge, clay lamp, flame and a warm spot light |
| किनारे की नीची दीवार | 0.75 m wall with coping on the quay edge, broken at the gate and the steps, with high-water silt marks |
| नाव का रास्ता | Boat with a seated eye camera, a route curve with 7 marker points, and hull rock |
| Person | Unidentified back-only stand-in with the red cloth, standing by the lamp |

## Sight lines (checked by `validate_ghat_set.py`, 11 of 11 pass)

* The boat camera, at Gopal's seated eye height, has the lamp and the red cloth in frame on frame 1. The person's back is turned about 50° to the boat, so the view is oblique.
* The lamp is a spot light aimed at the cloth. Its cone is 60°, and the gate samples under the lamp are more than 120° off its axis, so the gate stays in the dark.
* The boat yaws about 85° downstream on frames 36–90. By frame 94 the lamp and the person are out of frame, and the boat looks about 130° away from the chowki.
* No gate movement happens in the testimony frames (1–149).

## Cameras

`CAM | Boat POV — Gopal seated eye` (35 mm, active), `CAM | Boat POV — wide`, `CAM | Gate and lamp from the river`, `CAM | Quay west — gate and chowki`, `CAM | Steps from the river` and `CAM | Top map (river bend, ghat, boat route)`.

## Rebuild and check

Replace `blender` with `D:\Tools\Blender\blender-5.2.2-windows-x64\blender.exe` (see [AGENTS.md](../../AGENTS.md)).

```powershell
blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_ghat_set.py
blender --background --python-exit-code 1 Blender/Sets/SET_Ghat.blend --python Blender/tools/validate_ghat_set.py
```

| Script | Builds |
| --- | --- |
| `ghat_layout.py` | Positions, water level, boat route and timing (no Blender needed) |
| `ghat_kit.py` | Primitives and procedural materials |
| `ghat_world.py` | River, banks, steps and the low wall |
| `ghat_story.py` | Gate, chowki, lamp and person |
| `ghat_boat.py` | Boat, route, cameras and lights |
| `build_ghat_set.py` | Runs all of them, saves the `.blend` and `SET_Ghat_Manifest.json` |

## Guesses and limits

* The gate, chowki, lamp and person positions come from the palace `map_anchors`, which are guesses. The story fixes only their order.
* The person is a silhouette, not a rig. Replace it with the `Anonymous_Red_Cloth` figure at `MARK | Person`.
* The water is an opaque plane. The market and town are not included, so the market-roof block between the Halwai roof and the gate still needs checking in set 3.
* This set is not yet merged into `SET_Palace.blend`, and its `PLACEHOLDER` collection has not been replaced. The two files share coordinates, so they can be linked later.
