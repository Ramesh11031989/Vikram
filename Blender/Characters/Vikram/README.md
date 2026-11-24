# Vikram hero model

Adult Vikram is the visual and scale reference for the cast and palace kit. The character faces negative Y, stands 1.84 m to the scalp, and uses the cast's 34 deformation bone names with an anatomical A-pose bind. Open `Vikram_Hero.blend` and select **Vikram | Model and rig** for editing, **Vikram | Turnaround** for silhouette review, or **Vikram | Portrait and pose** to inspect the face and dressed shoulders. The hidden **Vikram | Full anatomy reference** collection holds the complete weighted body for future costume fittings. The dressed model has exposed skin at the face, neck, wrists and ankles.

| Asset | Use |
| --- | --- |
| [Vikram_Hero.blend](Vikram_Hero.blend) | Editable anatomy, layered costume, groom and FK skeleton |
| [Vikram_Hero.fbx](Vikram_Hero.fbx) | Neutral A-pose model and bones for the asset handoff check |
| [Vikram_Portrait.png](Vikram_Portrait.png) | Actual Blender close-up with a neck and shoulder pose |
| [Vikram_Turnaround.png](Vikram_Turnaround.png) | Actual Blender front, three-quarter and rear views |
| [Vikram_Concept.png](Vikram_Concept.png) | Original visual reference generated with the built-in image generation tool |

The first hero build is for modeling review. Expression shapes, Hindi lip sync, garment simulation and export-ready material maps are later [production gates](../../../Production/ART_PASSES.md). Cloth, skin and metal shader details can be inspected in the Blender source.

## Rebuild

The anatomical starting point is the realistic male body and eyes from the Blender Foundation's CC0 Human Base Meshes v1.4.1. Extract the source bundle and use the path to its included `.blend` file. The hero builder adds the project-specific face shaping, pigment, costume, groom, rig and review scenes. [Blender Foundation asset bundles](https://www.blender.org/download/demo-files/#assets) · [Official v1.4.1 bundle](https://mirror.blender.org/demo/asset-bundles/human-base-meshes/human-base-meshes-bundle-v1.4.1.zip)

Replace `blender` with `D:\Tools\Blender\blender-5.2.2-windows-x64\blender.exe` (see [AGENTS.md](../../../AGENTS.md)).


```powershell
blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_vikram_hero.py -- --base C:/path/to/human_base_meshes_bundle.blend
```

<details>
<summary>Modeling reference prompt</summary>

Use case: stylized-concept. Generate a serious cinematic animation character modeling reference sheet for an original adult Indian Raja Vikram in a Vikram-Betal folk-tale film, a grounded 3D period-fantasy style suitable for a Blender modeler and Unity film. An adult in his late 30s with believable human scale and proportions, Indian features, slight natural facial asymmetry, deep-set warm brown eyes, controlled raised brow, neat trimmed black beard and mustache with fine individual hairs, black hair at temple beneath a folded deep teal indigo turban with one subtly aged bronze medallion, no crown. Keep believable human eyes, nose, ears, lips, neck, hands, and feet with approximately 7.5 head height. Wardrobe is authentic-feeling court costume: layered deep indigo matte handwoven cotton angarkha with real cloth drape and nonuniform folds, warm desaturated long gold-brocade sash angled over one shoulder and grown-in braided seam, restrained hammered antique brass belt signet, soft dhoti-style trousers with dusty cream and burnt tea color, embroidered oxblood/black leather juttis. Show adult dignity with restrained humor appropriate to an interrogation scene and a clear, non-heroic neutral stance. Output one large landscape clean sheet on warm charcoal-gray studio background, with three coordinated model views: large head-and-shoulders three-quarter portrait on the left, same character full-length front neutral stance at right-center, same character full-length rear view on the far right for costume topology. Strong neutral soft light with visible tactile stitching, natural skin transitions, hair breakup, woven texture and crease placement. Baselines and matched proportions throughout. Clear separation between figures, keep all feet visible. Grounded, warm, subtly stylized high-end cinematic CG, sophisticated reference for an animated series; no plasticky materials, no giant eyes or chibi, no armor plates, no oversized head, no text, no watermark, no weapons and no celebrity likeness. Preserve the same particular design across front, back and portrait.

</details>
