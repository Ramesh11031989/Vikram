# भीड़-किट (Crowd Kit)

पृष्ठभूमि के लिए साझा किट: बस्ती के परिवार, दीये लिए परिजन, दरबार के लोग। किसी नामित पात्र या रिश्ते को तय नहीं करता।

| Body | Rig | Notes |
| --- | --- | --- |
| `CrowdMan` | standard cast skeleton (34 bones) | cream kurta, dhoti trousers, madder shoulder cloth, saffron head cloth |
| `CrowdWoman` | standard cast skeleton | draped saree with pallu, ochre blouse, low bun |
| `CrowdElder` | standard cast skeleton | long kurta, grey hair, grey shawl over the head; poses add a stoop |
| `CrowdChild` | shared child rig (56 bones), 1.05 m | indigo kurta, shorts, centre-parted plaits |

## Poses (Pose Library assets, one set per body)

- **Stand in court** - relaxed standing, open court / crowd edge.
- **Hold diya** - both palms cupped at chest height. `Prop_Diya` is placed in the hands in the preview.
- **Spread mat** - kneeling, leaning forward, palms flat on the mat (`Prop_Chatai mat`).
- **Wait on steps** - seated on a stone step, feet on the step below (`Prop_Stone steps`, rise 0.20 m).

Hip height and thigh angle for the kneeling and seated poses are solved from each rig's own leg lengths, so one pose fits all four bodies.

## Files

- `Crowd_Kit.blend`, `CH_Crowd*.fbx` (one per body)
- `CrowdKit_*.png` - review renders, one per pose
- Code: `Blender/tools/crowd_kit.py`, `crowd_props.py`, `build_crowd_kit.py`

## Rebuild

```powershell
& 'D:\Tools\Blender\blender-5.2.2-windows-x64\blender.exe' --background --factory-startup --python-exit-code 1 --python Blender/tools/build_crowd_kit.py -- --render
```

`--render` writes the four review images (about 3 minutes); omit it to rebuild only the `.blend` and FBX files.

## Limits

- The props are simple stand-ins for the preview and are not skinned or exported in the FBX files.
- The seated pose uses a fixed 0.20 m step; change `SEAT_RISE` in `crowd_kit.py` for other steps.
- Faces are shared presets; vary `SPECS` in `crowd_kit.py` for more crowd variety.
