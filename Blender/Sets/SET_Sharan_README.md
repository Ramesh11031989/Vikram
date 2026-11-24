# Set 5 — शरण की ढलान और बेताल की झोपड़ी (refuge slope and Betal's hut)

`SET_Sharan.blend` is the high ground behind the cremation ground. Families and boatmen sat there on the previous night, in arrival order. A footpath climbs from the cremation-ground wall to the outside of Betal's hut. It uses a **local map** in metres: +X east, +Y north (uphill), Z up, origin at the foot of the path. The story gives no route from the ghat or town, so it is not yet placed on the palace map.

## What is in the set

| Area | Contents |
| --- | --- |
| ढलान | 48 × 60 m terrain: flat ground at the foot, a 1.5 m terrace for the seating, then a rise to a 4.8 m platform for the hut |
| बैठने की जगह | 14 numbered `SEAT 01…14` mats on two arcs around the sailors' list board. `SEAT 03` is Gopal (marked with a sphere empty). Seats 4–14 come after him |
| मौसी | A mat beside Gopal and a `MARK \| Mausi sits beside Gopal` empty |
| और परिवार | Four more family mats east of the path, with bundles and water pots |
| सूची का पटरा | Plank with four papers, mats for Betal and the two sailors, and `MARK` empties for each |
| पगडंडी | 1.5 m wide, winding path with edge stones and log steps, from the wall gap to the hut veranda |
| श्मशान का किनारा | Low wall with a gap for the path, an ash bed and two memorial stones below the slope |
| झोपड़ी का बाहरी हिस्सा | Mud-plaster walls, thatch roof, open door, window with shutter, plinth, veranda step, water pot, firewood, a dhuni, a lantern and a bundle on a peg. The inside is a dark box with a charpai |
| पेड़ | Eight neem trees, rocks and grass tufts |

## Story checks

* Gopal's seat is third. Eleven seats follow his, all within 6 m of him (the farthest is 5.9 m) and with a clear line of sight, so many later arrivals can hear him.
* The path is 1.5 m wide and its steepest part is about 16°, so Vikram (1.84 m) can carry Betal up it. Its end has an open veranda with a 1.84 m clear height above it.
* The hut door is 1.0 × 1.8 m. `MARK | Vikram sets Betal down on the veranda` and `MARK | Hut door` give the end of the walk.
* `MARK | Vikram starts the climb`, three `MARK | Vikram carries Betal up the path` empties and `MARK | Nandu stands and tells everyone` give the other placement points.

## Cameras

`CAM | Slope from the foot` (active), `CAM | Seating and Gopal's place`, `CAM | Path up to the hut`, `CAM | Hut exterior`, `CAM | Door close` and `CAM | Top map (sharan)`.

## Rebuild, check and render

Replace `blender` with `D:\Tools\Blender\blender-5.2.2-windows-x64\blender.exe` (see [AGENTS.md](../../AGENTS.md)).

```powershell
blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_sharan_set.py
blender --background --python-exit-code 1 Blender/Sets/SET_Sharan.blend --python Blender/tools/validate_sharan_set.py
blender --background --python-exit-code 1 Blender/Sets/SET_Sharan.blend --python Blender/tools/render_sharan_set.py -- --percent 50 --samples 32
```

| Script | Builds |
| --- | --- |
| `sharan_layout.py` | Terrain profile, path, hut, seating plan (no Blender needed) |
| `sharan_world.py` | Materials, terrain, path and cremation-ground edge |
| `sharan_seating.py` | Seats, list board, trees and scatter |
| `sharan_hut.py` | Hut exterior and yard props |
| `sharan_view.py` | Moon and fire lights, cameras |
| `build_sharan_set.py` | Runs all of them, saves the `.blend` and `SET_Sharan_Manifest.json` |
| `validate_sharan_set.py` | 21 checks, writes `SET_Sharan_Validation.json` (all pass) |
| `render_sharan_set.py` | Review stills `Sharan_*.png` in `Blender/Previews/Sets/` |

## Guesses and limits

* All positions and sizes are guesses. The story fixes only the slope, the arrival-order list, Gopal's third place and the hut at the top.
* People are not included. The `SEAT`, `MARK` and Mausi empties show where to put the character rigs.
* Only the outside of the hut is modelled.
* The mats are flat slabs. The tree canopies are simple blobs and leaves are not modelled individually.
* The scene is lit by a moon sun, a dark sky, and warm lantern and dhuni lights.
