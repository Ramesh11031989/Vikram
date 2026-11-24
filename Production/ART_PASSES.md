# Character and environment art passes

Use the Blender gates first on Vikram as the visual standard. Apply the same checks to Betal, Gopal and the court clerk, and review the existing palace, Nandu, daughter, Halwai and neighbour assets for reuse. Start the Unity pilot once its required models have passed their neutral and posed reviews.

## Blender

Run every Blender gate and build script with Blender 5.2.2 LTS at `D:\Tools\Blender\blender-5.2.2-windows-x64\blender.exe` (WSL: `/mnt/d/Tools/Blender/blender-5.2.2-windows-x64/blender.exe`). `blender` is not on PATH. See [AGENTS.md](../AGENTS.md).

1. **Design reference.** Establish Vikram’s face, costume, palette and silhouette in front, side and three-quarter views. Carry the same material and proportion standards across the cast.
2. **Adult proportions.** Check a neutral full-body view against the design at a consistent meter scale. Review head size, shoulder width, limb lengths, hand size and stance from front and side.
3. **Face sculpt.** Review a close-up under neutral light. Check the brow, cheek, eyelids, nose, lips, jaw and ears from the front and profile.
4. **Body and hands.** Check shoulder and neck transitions, wrist anatomy, all fingers and the sole profile. Review relaxed hands, pointing and holding a prop.
5. **Costume construction.** Model the garment layers, collars, sleeves, sash, cuffs and shoes with readable thickness and folds. Check clearance at shoulders, elbows and waist in the review poses.
6. **Costume details.** Review seams, stitches, closures, embroidery, jewelry and repeated motifs at intended shot distance. Put wear where the garment or object is handled.
7. **Hair and facial hair.** Check scalp and hairline coverage, individual strands at close range, brow and beard silhouette, and continuity under the head wrap.
8. **Topology and UVs.** Check face and joint edge flow, outward normals, UV overlap where unique texture detail is required, and consistent texture scale across adjacent pieces.
9. **Materials.** Compare skin, eyes, lips, hair, cloth, leather and metal under neutral and warm test lights. Inspect roughness and texture at close-up and full-body distance.
10. **Rig and facial deformation.** Review planted feet, elbow and wrist bends, eye aim, blinks, smile and speech shapes. Check hand-to-prop contact and garment clearance in at least two acting poses.
11. **Palace kit.** Build the court from reusable floor, wall, column, arch, doorway, stair and trim modules. Verify anchor positions and repeatable joins by assembling one complete court bay at character scale.
12. **Blender handoff.** Review neutral front, side and three-quarter views, a face close-up and posed full-body renders. Open the editable `.blend` and reimport the export to check scale, mesh names, skin weights and facial targets.

## Unity

1. **Import verification.** Confirm the Unity model scale and forward axis, assigned materials, valid rig and every required facial target against the Blender handoff.
2. **Character prefabs.** Instantiate every cast prefab twice in a test scene. Check independent pose and face controls, attachment points and the detail levels used by the pilot cameras.
3. **Palace prefabs.** Snap the modular court pieces into the shot layout. Check floor heights against feet, door heights against adult silhouettes and seams from camera distance.
4. **Render baseline.** Set the pilot’s render pipeline, exposure reference, resolution and 24 fps timebase. Compare the same neutral view across Blender and Unity.
5. **Face and hair shading.** Match the skin, irises, lips and hair under neutral and palace lighting. Check for harsh reflections, aliasing and lost facial contrast.
6. **Costume and prop shading.** Check the fabric weave, trim, metal, leather and wood at shot distance. Check maps, filtering and consistent color under moving lights.
7. **Lighting.** Establish court daylight and the river lamp at night. Check skin exposure, silhouettes, eye highlights, shadows and readability throughout the edit.
8. **Camera and staging.** Block the edit at 24 fps and verify eyelines, screen direction, cuts and the visibility of clues. Review the river figure from the witness’s view.
9. **Body acting.** Block the performances before refining curves. Review weight shifts, arcs, holds and comic beats such as a pause, glance or delayed reaction against the dialogue.
10. **Facial acting and lip sync.** Use the selected Hindi dialogue to time mouth openings, closures and syllable emphasis. Check blinks, gaze, expressions and deadpan reactions in close-up at normal playback speed.
11. **Contacts and secondary motion.** Inspect hand-to-prop contact, foot plants, writing, hair and sash settling. Check animation transitions for sliding, clipping and sudden jumps.
12. **Reusable VFX.** Build lamp flicker, dust motes, river ripples and splash prefabs with editable intensity, color, scale, timing and seed. Trigger each from Timeline and reuse it in two shots.
13. **Shot VFX.** Check effect placement, contact timing and camera visibility. Review the lamp, red cloth and water effects at full speed so their motion supports the testimony.
14. **Sound and timing.** Mix Hindi dialogue, foley, room tone and river ambience against picture. Listen to the entire cut and check level, sync and intelligibility at the quieter lines.
15. **Color and editorial review.** Review continuity, grade, titles and Hindi subtitles at delivery size. Check performance readability, subtitle timing and the first and last frame of every cut.
16. **Final playback.** Export the master and decode it in a standard player. Verify the frame rate, duration, audible audio stream and dialogue sync near the start, middle and end. Keep the editable Timeline, reusable prefabs and source audio with the project.

## Anatomy source

The adult male foundation is **Body Male - Realistic** from **Human Base Meshes v1.4.1**, by Blender Studio and contributors, released under **CC0**. [Official Blender demo files](https://www.blender.org/download/demo-files/#assets) · [Official v1.4.1 ZIP](https://mirror.blender.org/demo/asset-bundles/human-base-meshes/human-base-meshes-bundle-v1.4.1.zip)
