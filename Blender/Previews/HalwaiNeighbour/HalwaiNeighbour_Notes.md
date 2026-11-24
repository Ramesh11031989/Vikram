# हलवाई की पड़ोसन: witness package notes

Chapter 1 says: "पड़ोसन ने अपनी गाय की रस्सी काटी थी". During the flood she freed her cow by cutting its tether. Ramesh's row for her reads: **"रस्सी काटते समय हाथ, रस्सी और गाय का आकार आपस में मेल खाएँ"**. Everything here is built at real scale so that her hands, the rope and the cow match.

## How to rebuild

```
blender --background --python Blender/tools/build_halwai_neighbour.py -- --samples 96
```

Add `--no-render` to skip the previews, or `--cut-only` to re-render just the two rope-cut shots. One run writes everything below.

| Output | What it is |
| --- | --- |
| `Blender/HalwaiNeighbour_Witness.blend` | Scenes: `HN • Character` (A-pose), `HN • Scale sheet`, `HN • Rope cut` (the staged moment) and `HN • Props`. Each has its review cameras. Her two poses are kept as the actions `HN_A_Pose` and `HN_Rope_Cut`. |
| `Blender/Exports/CH_HalwaiNeighbour.fbx` | Her, in the rest T-pose, with the shared skeleton plus 20 finger/thumb bones, blink, speech and expression shape keys. |
| `Blender/Exports/AN_MalviCow.fbx` | The cow and her quadruped FK rig (jaw, eyes, ears, tail). |
| `Blender/Exports/PR_Tether.fbx` | The rope intact and cut, the knot, the peg and the sickle. |
| `Blender/Previews/HalwaiNeighbour/*.png` | Turnaround, portrait, scale sheet, rope-cut close-up and medium shot. |
| `HalwaiNeighbour_scale_check.json` | The measured sizes and pass/fail checks for the hand, rope, sickle and cow. |

## Source files

- `sculpted_face.py`: her volumetric head. `SculptedFace(c, FaceSpec)`, with the presets `NEIGHBOUR` and `ADULT_MAN`. It has real eyeballs and lids, speech shape keys driven by the shared mouth controls, and blinks.
- `sculpted_hand.py`: sculpted hands. They have palm pads and creases, knuckles, fingertip pads, nail beds and nail plates with a pale free edge. The weights come from the 20 finger bones.
- `halwai_neighbour.py`: her body, costume, odhni, hair and jewellery.
- `cattle.py`: the Malvi-type cow. She is one sculpted body with a particle short-hair coat that follows the armature.
- `tether_props.py`: the 14 mm three-strand jute tether, the overhand knot, the lead with two turns and a hitch round the peg, the cut version with unlaid and frayed ends, and the sickle.
- `build_halwai_neighbour.py`: the staging, review scenes, exports, scale check and .blend.

## The staged cut

- Her left fist holds the lead up at hip height.
- The knot hangs under the cow's throat.
- The sickle is hooked round the lead from the cow's side. The rope passes through the crescent square to the blade, and the inner edge pulls toward her. The cut is 62% of the way from the knot to her fist.
- The build turns the sickle round the rope, and tilts it, by the least amount that puts her right wrist in front of her skirt with the elbow still bent.
- Both arms reach their grips by two-bone IK solved in the build. The scale check reports any miss.
- Her fingers close round the 14 mm rope and the 30 mm sickle handle.

## Scale check

The build measures these and writes them to `HalwaiNeighbour_scale_check.json`. All four checks pass.

| Measure | Value |
| --- | --- |
| Her height | 154 cm |
| Hand, wrist to middle fingertip | 17.7 cm (adult woman: 16.5 to 18.5) |
| Hand breadth | 7.5 cm (adult woman: 7 to 8.5) |
| Finger width | 16.8 mm |
| Rope | 14 mm, 0.83 of a finger's width, so her fist closes round it |
| Sickle overall | 33.6 cm, handle 12.2 cm long and 3 cm thick (1.63 times her hand breadth) |
| Cow at the withers | 118 cm (she is 1.31 times that) |
| Cow's neck at the rope | 131 cm round |
| Knot height | 57.7 cm |
| Cut height | 69.8 cm, 26.4 cm from the knot |
| Left fist to the lead, right fist to the handle | 0 mm and 0 mm off |

## Guesses to confirm (not from the text)

- **Cow:** a Malvi-type zebu (white-grey with a smoky hump and neck), 1.18 m at the withers, with a short summer coat. The Malwa breed matches the Malwa village costume already guessed for her.
- **Rope:** 14 mm three-strand jute. Village tethers are usually 12 to 16 mm.
- **Knot:** an overhand knot hanging under the throat. The loop goes round the neck behind the horns.
- **Sickle (हँसिया):** a serrated crescent blade, about 34 cm overall, on a turned sheesham handle 12 cm long.
- **Peg (खूँटा):** split wood, 6 cm across, standing 45 cm proud.
- **Her:** 1.54 m, about 7.3 heads.
- **Costume and jewellery:** a Malwa ghagra, a kurti, and a bandhani odhni drawn over her head. Kajal, a nose stud, ear hoops and bangles. No marital markers, because the chapter doesn't say she is married. No red cloth, because red belongs to Nandu's clue.
- **Setting:** the previews use dry packed earth for clarity. The episode's moment is during the flood, so water, mud and wet cloth still need to be added for the shot itself.

## Known limits

- The cow's hair coat is a Blender particle system. It renders in Cycles and EEVEE but does not go into the FBX. For Unity, use a fur shader or cards.
- The cut rope is still geometry posed for the moment of the cut, not a simulation. For animation, swap the intact rope for the cut one on the cutting frame.
- The odhni is relaxed once by cloth simulation at build time and then skinned to the rig. Big head turns will need a cloth pass.
