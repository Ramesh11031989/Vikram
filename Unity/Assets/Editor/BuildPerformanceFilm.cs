using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using Vikram.Performance;
using Object = UnityEngine.Object;

namespace Vikram.Editor
{
    public static class BuildPerformanceFilm
    {
        private const string DefaultArt = "Assets/Art/E01/SC04";
        private const string DefaultScene = "Assets/Scenes/E01_SC04_Performance.unity";

        [MenuItem("Tools/Vikram/Performance/Build Scene")]
        public static void Build()
        {
            if (!Application.isBatchMode && !EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())
                return;

            string art = Option("-vikramArt", DefaultArt);
            string scenePath = Option("-vikramScene", DefaultScene);
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            TextAsset source = AssetDatabase.LoadAssetAtPath<TextAsset>($"{art}/Performance.json");
            Require(source != null, $"Export the Blender performance to {art}/Performance.json first.");
            var manifest = JsonUtility.FromJson<PerformanceManifest>(source.text);
            CheckManifest(manifest);

            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var root = new GameObject("Chapter performance");
            var film = root.AddComponent<PerformanceFilm>();
            var lantern = manifest.lights?.FirstOrDefault(light => light.name == "Lamp light");
            var palette = CreatePalette(art, manifest.materials, lantern);
            FilmModelTrack[] models = manifest.assets.Select(asset => Import(root.transform, art, asset, palette)).ToArray();
            var sets = BuildSets(root.transform, models, manifest);
            foreach (FilmCameraTrack track in manifest.cameras)
            {
                Camera camera = Child(root.transform, track.name).gameObject.AddComponent<Camera>();
                camera.clearFlags = CameraClearFlags.SolidColor;
                camera.allowHDR = false;
                camera.allowMSAA = true;
                camera.nearClipPlane = Mathf.Max(.01f, track.near);
                camera.farClipPlane = Mathf.Max(30f, track.far);
                camera.orthographic = track.orthographicSize > 0f;
                if (camera.orthographic)
                    camera.orthographicSize = track.orthographicSize;
                string shotSet = manifest.shots.First(shot => shot.camera == track.name).set;
                camera.backgroundColor = shotSet == "river" ? new Color(.036f, .062f, .116f) : new Color(.25f, .21f, .17f);
                camera.enabled = false;
                track.camera = camera;
            }

            var audio = root.AddComponent<AudioSource>();
            root.AddComponent<AudioListener>();
            audio.playOnAwake = false;
            audio.spatialBlend = 0f;
            audio.clip = AssetDatabase.LoadAssetAtPath<AudioClip>($"{art}/Soundtrack.wav");
            var lips = AssetDatabase.LoadAssetAtPath<TextAsset>($"{art}/Unity_Visemes.json");
            film.Configure(manifest, models, sets, audio, lips);
            if (lips != null)
            {
                Require(film.MouthShapes > 0, "Dialogue cue track is present but no mouth blend shapes bound in this scene.");
                if (art == DefaultArt)
                    Require(film.SpeakingActors == 2 && film.MouthShapes >= 16, "SC04 needs the dialogue shapes for both Vikram and Gopal.");
            }

            AssetDatabase.SaveAssets();
            Require(EditorSceneManager.SaveScene(scene, scenePath), $"Could not save {scenePath}.");
            Debug.Log($"VIKRAM FILM READY {scenePath}: {models.Length} art imports, {models.Count(model => model.clip != null)} animated, " +
                $"{manifest.shots.Length} edits, {film.SpeakingActors} speaking actors, {film.MouthShapes} mouth shapes, {film.FrameCount} frames.");
        }

        public static void BuildAndRenderProofs()
        {
            Build();
            RenderProofs();
        }

        public static void BuildProofsAndFilm()
        {
            BuildAndRenderProofs();
            RenderFilm();
        }

        public static void CheckAndRenderFilm()
        {
            CheckMouthDeformation();
            RenderProofs();
            RenderFilm();
        }

        [MenuItem("Tools/Vikram/Performance/Check Mouth Deformation")]
        public static void CheckMouthDeformation()
        {
            PerformanceFilm film = OpenScene(false);
            int[] samples = Option("-vikramMouthSamples", "132,137,478,510").Split(',')
                .Select(text => int.Parse(text, CultureInfo.InvariantCulture)).ToArray();
            var mouthBindings = film.GetComponentsInChildren<SkinnedMeshRenderer>()
                .Where(renderer => renderer.sharedMesh != null)
                .Select(renderer => (renderer, shapes: Enumerable.Range(0, renderer.sharedMesh.blendShapeCount)
                    .Where(index => renderer.sharedMesh.GetBlendShapeName(index).Contains("Mouth_", StringComparison.OrdinalIgnoreCase))
                    .ToArray()))
                .Where(binding => binding.shapes.Length > 0)
                .ToArray();
            using var skin = new SampledSkinningPass(film);
            foreach (int frame in samples)
            {
                film.ApplyFrame(frame);
                bool inspectPicture = SystemInfo.graphicsDeviceType != GraphicsDeviceType.Null &&
                    mouthBindings.Any(binding => binding.renderer.enabled &&
                        binding.shapes.Any(index => binding.renderer.GetBlendShapeWeight(index) > 0f));
                if (inspectPicture)
                {
                    skin.UpdateGeometry();
                    CaptureMouthProof(film.ActiveCamera, $"mouth_{frame:D5}_active.png");
                }
                foreach (var (renderer, mouths) in mouthBindings)
                {
                    var mesh = renderer.sharedMesh;
                    string weights = string.Join(", ", mouths.Select(index => $"{mesh.GetBlendShapeName(index)}={renderer.GetBlendShapeWeight(index):0.00}"));
                    var delta = new Vector3[mesh.vertexCount];
                    float maxImportedDelta = 0f;
                    foreach (int index in mouths)
                    {
                        mesh.GetBlendShapeFrameVertices(index, 0, delta, null, null);
                        foreach (Vector3 displacement in delta)
                            maxImportedDelta = Mathf.Max(maxImportedDelta, renderer.localToWorldMatrix.MultiplyVector(displacement).magnitude);
                    }

                    var baked = new Mesh();
                    try
                    {
                        renderer.BakeMesh(baked);
                        Vector3[] speaking = baked.vertices;
                        foreach (int index in mouths)
                            renderer.SetBlendShapeWeight(index, 0f);
                        renderer.BakeMesh(baked);
                        Vector3[] rest = baked.vertices;
                        float maxAppliedDelta = 0f;
                        for (int index = 0; index < rest.Length; index++)
                            maxAppliedDelta = Mathf.Max(maxAppliedDelta, renderer.localToWorldMatrix.MultiplyVector(speaking[index] - rest[index]).magnitude);
                        Debug.Log($"VIKRAM MOUTH CHECK {frame}: {renderer.name}, visible={renderer.enabled}, {mesh.vertexCount} vertices, " +
                            $"imported delta={maxImportedDelta:F6} m, applied delta={maxAppliedDelta:F6} m, {weights}");
                    }
                    finally
                    {
                        Object.DestroyImmediate(baked);
                    }
                }

                if (inspectPicture)
                {
                    skin.UpdateGeometry();
                    CaptureMouthProof(film.ActiveCamera, $"mouth_{frame:D5}_rest.png");
                    string directory = OutputDirectory("mouth_check");
                    byte[] active = File.ReadAllBytes(Path.Combine(directory, $"mouth_{frame:D5}_active.png"));
                    byte[] rest = File.ReadAllBytes(Path.Combine(directory, $"mouth_{frame:D5}_rest.png"));
                    Require(!active.SequenceEqual(rest), "Speaking and resting mouth proofs were pixel-identical.");
                }
            }

            film.ApplyFrame(0);
        }

        private static void CaptureMouthProof(Camera camera, string filename)
        {
            string directory = OutputDirectory("mouth_check");
            Directory.CreateDirectory(directory);
            var target = RenderTexture.GetTemporary(1280, 720, 24, RenderTextureFormat.ARGB32);
            var image = new Texture2D(1280, 720, TextureFormat.RGB24, false);
            RenderTexture prior = RenderTexture.active;
            try
            {
                DrawCamera(camera, target, image, Path.Combine(directory, filename));
            }
            finally
            {
                RenderTexture.active = prior;
                RenderTexture.ReleaseTemporary(target);
                Object.DestroyImmediate(image);
            }
        }

        [MenuItem("Tools/Vikram/Performance/Attach Soundtrack")]
        public static void AttachSoundtrack()
        {
            PerformanceFilm film = OpenScene();
            string asset = $"{Option("-vikramArt", DefaultArt)}/Soundtrack.wav";
            AssetDatabase.ImportAsset(asset, ImportAssetOptions.ForceSynchronousImport);
            var clip = AssetDatabase.LoadAssetAtPath<AudioClip>(asset);
            Require(clip != null, $"Add the mixed soundtrack at {asset}.");
            Require(Mathf.Abs(clip.length - film.FrameCount / (float)film.Fps) < .12f,
                $"The soundtrack duration {clip.length:0.00}s does not match the edit.");
            film.GetComponent<AudioSource>().clip = clip;
            EditorSceneManager.MarkSceneDirty(film.gameObject.scene);
            Require(EditorSceneManager.SaveScene(film.gameObject.scene), "Could not save the scene soundtrack.");
            Debug.Log($"VIKRAM FILM SOUNDTRACK ATTACHED {clip.length:0.000}s {clip.channels} channels {clip.frequency} Hz");
        }

        [MenuItem("Tools/Vikram/Performance/Render Shot Proofs")]
        public static void RenderProofs()
        {
            PerformanceFilm film = OpenScene();
            string directory = OutputDirectory("proofs");
            Draw(film, directory, film.Shots.Select(shot => (shot.startFrame + shot.endFrame - 1) / 2));
        }

        [MenuItem("Tools/Vikram/Performance/Render Film Frames")]
        public static void RenderFilm()
        {
            PerformanceFilm film = OpenScene();
            int start = ReadInt("-vikramStartFrame", 0);
            int end = ReadInt("-vikramEndFrame", film.FrameCount);
            Require(start >= 0 && end > start && end <= film.FrameCount, "Output frame range is outside the edit.");
            int step = ReadInt("-vikramStep", 1);
            Require(step > 0, "Output frame step must be positive.");
            Draw(film, OutputDirectory("frames"), Enumerable.Range(start, end - start).Where(frame => (frame - start) % step == 0));
        }

        private static PerformanceFilm OpenScene(bool requireGraphics = true)
        {
            Require(!requireGraphics || SystemInfo.graphicsDeviceType != GraphicsDeviceType.Null, "Movie rendering requires Unity graphics mode.");
            string path = Option("-vikramScene", DefaultScene);
            if (EditorSceneManager.GetActiveScene().path != path)
                EditorSceneManager.OpenScene(path, OpenSceneMode.Single);
            var film = Object.FindFirstObjectByType<PerformanceFilm>();
            Require(film != null, "Build the Blender performance before rendering the Unity movie.");
            return film;
        }

        private static string OutputDirectory(string subdirectory)
        {
            string defaultOutput = Path.Combine(Application.dataPath, "../../Renders/Unity/E01_SC04");
            return Path.GetFullPath(Path.Combine(Option("-vikramOutput", defaultOutput), subdirectory));
        }

        private static void Draw(PerformanceFilm film, string directory, IEnumerable<int> frames)
        {
            int width = ReadInt("-vikramWidth", 1280);
            int height = ReadInt("-vikramHeight", 720);
            Require(width > 0 && height > 0, "Film resolution must be positive.");
            Directory.CreateDirectory(directory);
            int pixelLights = QualitySettings.pixelLightCount;
            ShadowQuality shadows = QualitySettings.shadows;
            ShadowResolution shadowResolution = QualitySettings.shadowResolution;
            float shadowDistance = QualitySettings.shadowDistance;
            RenderTexture prior = RenderTexture.active;
            var target = RenderTexture.GetTemporary(width, height, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.Default, 2);
            var image = new Texture2D(width, height, TextureFormat.RGB24, false);
            try
            {
                using var skin = new SampledSkinningPass(film);
                QualitySettings.pixelLightCount = 8;
                QualitySettings.shadows = ShadowQuality.All;
                QualitySettings.shadowResolution = ShadowResolution.High;
                QualitySettings.shadowDistance = 35f;
                int written = 0;
                foreach (int frame in frames)
                {
                    film.ApplyFrame(frame);
                    skin.UpdateGeometry();
                    Camera camera = film.ActiveCamera;
                    Require(camera != null, $"No active camera at film frame {frame}.");
                    DrawCamera(camera, target, image, Path.Combine(directory, $"frame_{frame:D5}.png"));

                    if (++written == 1 || written % 48 == 0)
                        Debug.Log($"VIKRAM FILM FRAME {frame:D5} {camera.name}");
                }

                Debug.Log($"VIKRAM FILM RENDERED {written} frames at {width}x{height} into {directory}");
            }
            finally
            {
                QualitySettings.pixelLightCount = pixelLights;
                QualitySettings.shadows = shadows;
                QualitySettings.shadowResolution = shadowResolution;
                QualitySettings.shadowDistance = shadowDistance;
                RenderTexture.active = prior;
                RenderTexture.ReleaseTemporary(target);
                Object.DestroyImmediate(image);
                film.ApplyFrame(0);
            }
        }

        private static void DrawCamera(Camera camera, RenderTexture target, Texture2D image, string path)
        {
            RenderTexture source = camera.targetTexture;
            try
            {
                camera.targetTexture = target;
                camera.Render();
                RenderTexture.active = target;
                image.ReadPixels(new Rect(0, 0, target.width, target.height), 0, 0, false);
                File.WriteAllBytes(path, ImageConversion.EncodeToPNG(image));
            }
            finally
            {
                camera.targetTexture = source;
            }
        }

        // Repeated Camera.Render calls in one Editor update reuse stale skinning data.
        // Bake the sampled pose into disposable meshes for frame-accurate batch renders.
        private sealed class SampledSkinningPass : IDisposable
        {
            private sealed class Deformation
            {
                public SkinnedMeshRenderer source;
                public MeshFilter filter;
                public MeshRenderer target;
                public Mesh buffer;
                public bool hidden;
            }

            private readonly List<Deformation> meshes = new();

            public SampledSkinningPass(PerformanceFilm film)
            {
                foreach (var source in film.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                {
                    if (source.sharedMesh == null)
                        continue;
                    var proxy = new GameObject("Frame render mesh")
                    {
                        hideFlags = HideFlags.HideAndDontSave,
                        layer = source.gameObject.layer
                    };
                    proxy.transform.SetParent(source.transform, false);
                    var buffer = new Mesh { hideFlags = HideFlags.HideAndDontSave };
                    buffer.MarkDynamic();
                    var filter = proxy.AddComponent<MeshFilter>();
                    var target = proxy.AddComponent<MeshRenderer>();
                    target.enabled = false;
                    target.sharedMaterials = source.sharedMaterials;
                    target.shadowCastingMode = source.shadowCastingMode;
                    target.receiveShadows = source.receiveShadows;
                    target.lightProbeUsage = source.lightProbeUsage;
                    target.reflectionProbeUsage = source.reflectionProbeUsage;
                    meshes.Add(new Deformation { source = source, filter = filter, target = target, buffer = buffer, hidden = source.forceRenderingOff });
                    source.forceRenderingOff = true;
                }
            }

            public void UpdateGeometry()
            {
                foreach (Deformation entry in meshes)
                {
                    bool visible = !entry.hidden && entry.source.enabled && entry.source.gameObject.activeInHierarchy;
                    if (visible)
                    {
                        // Publish a populated mesh and its sampled bounds before registering it for culling.
                        bool firstVisibleFrame = !entry.target.enabled;
                        entry.source.BakeMesh(entry.buffer);
                        entry.buffer.RecalculateBounds();
                        if (firstVisibleFrame)
                            entry.filter.sharedMesh = entry.buffer;
                        entry.target.localBounds = entry.buffer.bounds;
                    }
                    entry.target.enabled = visible;
                }
            }

            public void Dispose()
            {
                foreach (Deformation entry in meshes)
                {
                    entry.source.forceRenderingOff = entry.hidden;
                    Object.DestroyImmediate(entry.target.gameObject);
                    Object.DestroyImmediate(entry.buffer);
                }
            }
        }

        private static FilmModelTrack Import(Transform parent, string art, string filename, IReadOnlyDictionary<string, Material> palette)
        {
            Require(Path.GetFileName(filename) == filename && filename.EndsWith(".fbx", StringComparison.OrdinalIgnoreCase),
                $"Unexpected performance asset filename {filename}.");
            string path = $"{art}/{filename}";
            var importer = AssetImporter.GetAtPath(path) as ModelImporter;
            Require(importer != null, $"No Unity ModelImporter for {path}.");
            if (importer.animationType != ModelImporterAnimationType.Generic ||
                importer.animationCompression != ModelImporterAnimationCompression.Off ||
                !importer.importBlendShapes || !importer.importAnimation || importer.optimizeGameObjects)
            {
                importer.animationType = ModelImporterAnimationType.Generic;
                importer.animationCompression = ModelImporterAnimationCompression.Off;
                importer.importBlendShapes = true;
                importer.importAnimation = true;
                importer.optimizeGameObjects = false;
                importer.SaveAndReimport();
            }

            var source = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            Require(source != null, $"Could not load {path}.");
            Transform correction = Child(parent, Path.GetFileNameWithoutExtension(filename) + " | FBX axes");
            var instance = (GameObject)PrefabUtility.InstantiatePrefab(source, correction);
            Transform[] nodes = instance.GetComponentsInChildren<Transform>(true);
            if (nodes.Any(node => node.name == "E01_Axis_Origin"))
                BuildGhatSightlines.Calibrate(correction, nodes);
            foreach (var renderer in instance.GetComponentsInChildren<Renderer>(true))
            {
                Material[] materials = renderer.sharedMaterials;
                for (int slot = 0; slot < materials.Length; slot++)
                {
                    if (materials[slot] != null && palette.TryGetValue(Normalize(materials[slot].name), out Material material))
                        materials[slot] = material;
                }

                renderer.sharedMaterials = materials;
                if (renderer is SkinnedMeshRenderer deforming)
                    deforming.updateWhenOffscreen = true;
            }

            AnimationClip clip = AssetDatabase.LoadAllAssetsAtPath(path).OfType<AnimationClip>()
                .Where(candidate => !candidate.name.StartsWith("__preview__", StringComparison.Ordinal))
                .OrderByDescending(candidate => candidate.length).FirstOrDefault();
            return new FilmModelTrack { root = instance, clip = clip };
        }

        private static FilmSetTrack[] BuildSets(Transform parent, FilmModelTrack[] models, PerformanceManifest manifest)
        {
            var visibility = (manifest.visibility ?? Array.Empty<FilmVisibility>())
                .GroupBy(item => Normalize(item.name), StringComparer.Ordinal)
                .ToDictionary(group => group.Key, group => group.First().set ?? string.Empty, StringComparer.Ordinal);

            string FindSet(Renderer renderer)
            {
                for (Transform node = renderer.transform; node != null && node != parent; node = node.parent)
                {
                    if (visibility.TryGetValue(Normalize(node.name), out string set))
                        return set;
                }

                return string.Empty;
            }

            ILookup<string, Renderer> renderers = models.SelectMany(model => model.root.GetComponentsInChildren<Renderer>(true)).ToLookup(FindSet);
            Transform lighting = Child(parent, "Shot lighting");
            FilmLightData[] entries = manifest.lights ?? Array.Empty<FilmLightData>();
            ILookup<string, Light> lights = entries.ToLookup(entry => entry.set ?? string.Empty, entry => CreateLight(lighting, entry));
            string[] labels = manifest.shots.Select(shot => shot.set).Append(string.Empty).Distinct().ToArray();
            foreach (string label in labels)
                Debug.Log($"VIKRAM FILM SET {label}: {renderers[label].Count()} renderers, {lights[label].Count()} lights");
            return labels.Select(label => new FilmSetTrack { set = label, renderers = renderers[label].ToArray(), lights = lights[label].ToArray() }).ToArray();
        }

        private static Light CreateLight(Transform parent, FilmLightData entry)
        {
            var light = Child(parent, entry.name).gameObject.AddComponent<Light>();
            light.transform.position = entry.position;
            if (entry.forward.sqrMagnitude > .01f)
                light.transform.rotation = Quaternion.LookRotation(entry.forward, entry.up);
            light.color = entry.color.gamma;
            light.shadows = LightShadows.Soft;
            light.shadowStrength = entry.set == "court" ? .62f : .88f;
            light.shadowNearPlane = .05f;
            light.shadowBias = .055f;
            light.shadowNormalBias = .24f;
            light.renderMode = LightRenderMode.ForcePixel;
            switch (entry.type)
            {
                case "SUN":
                    light.type = LightType.Directional;
                    light.intensity = entry.energy;
                    break;
                case "POINT":
                    light.type = LightType.Point;
                    light.range = entry.set == "river" ? 3.4f : 6f;
                    light.intensity = Mathf.Clamp(entry.energy / 34f, 0f, 2.8f);
                    break;
                default:
                    light.type = LightType.Spot;
                    light.range = Mathf.Max(9f, entry.size * 2.6f);
                    light.spotAngle = entry.spotAngle > 0f ? entry.spotAngle : 115f;
                    light.innerSpotAngle = light.spotAngle * .65f;
                    light.intensity = entry.set == "court"
                        ? Mathf.Clamp(entry.energy / 210f, 0f, 4.25f)
                        : Mathf.Clamp(entry.energy / 290f, 0f, 3.5f);
                    break;
            }

            if (entry.name.Contains("fill", StringComparison.OrdinalIgnoreCase) || entry.name.Contains("bounce", StringComparison.OrdinalIgnoreCase))
                light.shadows = LightShadows.None;

            if (entry.name == "Court warm window key")
                light.color = new Color(1f, .84f, .69f);
            if (entry.name == "Court cool soft fill")
                light.color = new Color(.66f, .82f, 1f);
            return light;
        }

        private static Dictionary<string, Material> CreatePalette(string art, FilmMaterial[] entries, FilmLightData lantern)
        {
            string path = $"{art}/PerformancePalette.mat";
            var palette = AssetDatabase.LoadAllAssetsAtPath(path).OfType<Material>()
                .ToDictionary(material => Normalize(material.name), StringComparer.Ordinal);
            Shader standard = Shader.Find("Standard");
            Shader textile = Shader.Find("Vikram/Performance Textile");
            Shader river = Shader.Find("Vikram/Performance River");
            Require(standard != null && textile != null && river != null,
                "The performance renderer needs the Standard, Performance Textile and Performance River shaders.");
            foreach (FilmMaterial entry in entries ?? Array.Empty<FilmMaterial>())
            {
                string key = Normalize(entry.name);
                bool redDrape = key.EndsWith("observedredcloth", StringComparison.Ordinal);
                bool fabric = redDrape || key.Contains("cotton") || key.Contains("linen") || key.Contains("turbancloth") ||
                    key.Contains("shouldercloth") || key.Contains("indigojacket") || key.Contains("hemptrousercloth");
                bool water = key == "riveropaquenightwater";
                Shader shader = water ? river : fabric ? textile : standard;
                if (!palette.TryGetValue(key, out Material material))
                {
                    material = new Material(shader) { name = entry.name };
                    if (palette.Count == 0)
                        AssetDatabase.CreateAsset(material, path);
                    else
                        AssetDatabase.AddObjectToAsset(material, path);
                    palette.Add(key, material);
                }

                material.shader = shader;
                if (water)
                {
                    material.color = new Color(.027f, .071f, .098f);
                    if (lantern != null)
                        material.SetVector("_LanternPosition", lantern.position);
                    EditorUtility.SetDirty(material);
                    continue;
                }

                material.color = entry.color.gamma;
                material.SetFloat("_Glossiness", 1f - Mathf.Clamp01(entry.roughness));
                material.SetFloat("_Metallic", Mathf.Clamp01(entry.metallic));
                if (redDrape)
                {
                    material.SetColor("_EmissionColor", new Color(.115f, .009f, .004f));
                }
                else if (entry.emissionIntensity > .02f)
                {
                    material.EnableKeyword("_EMISSION");
                    material.SetColor("_EmissionColor", entry.emissionColor.gamma * Mathf.Clamp01(entry.emissionIntensity / 3f));
                }
                else
                {
                    material.DisableKeyword("_EMISSION");
                    material.SetColor("_EmissionColor", Color.black);
                }

                EditorUtility.SetDirty(material);
            }

            return palette;
        }

        private static void CheckManifest(PerformanceManifest data)
        {
            Require(data != null && data.fps > 0 && data.frameCount > 0 && data.assets?.Length > 0 && data.shots?.Length > 0 && data.cameras?.Length > 0,
                "The performance manifest needs a timebase, asset files, camera tracks and shot ranges.");
            var tracks = data.cameras.ToDictionary(track => track.name, StringComparer.Ordinal);
            int next = 0;
            foreach (FilmShot shot in data.shots)
            {
                Require(shot.startFrame == next && shot.endFrame > shot.startFrame && tracks.ContainsKey(shot.camera),
                    $"The cut at frame {shot.startFrame} has a missing camera or invalid inclusive/exclusive range.");
                next = shot.endFrame;
                Require(tracks[shot.camera].poses?.Length > 0, $"{shot.camera} is missing its camera poses.");
            }

            Require(next == data.frameCount, "Shot ranges must cover the entire edit.");
        }

        private static Transform Child(Transform parent, string name)
        {
            Transform child = new GameObject(name).transform;
            child.SetParent(parent, false);
            return child;
        }

        private static string Normalize(string value) => new string(value.Where(char.IsLetterOrDigit).ToArray()).ToLowerInvariant();

        private static int ReadInt(string option, int fallback) => int.Parse(Option(option, fallback.ToString(CultureInfo.InvariantCulture)), CultureInfo.InvariantCulture);

        private static string Option(string option, string fallback)
        {
            string[] args = Environment.GetCommandLineArgs();
            int index = Array.IndexOf(args, option);
            return index >= 0 && index < args.Length - 1 ? args[index + 1] : fallback;
        }

        private static void Require(bool condition, string message)
        {
            if (!condition)
                throw new InvalidDataException(message);
        }
    }
}
