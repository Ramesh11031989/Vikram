using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using Vikram.Sightlines;
using Object = UnityEngine.Object;

namespace Vikram.Editor
{
    public static class BuildGhatSightlines
    {
        private const string ArtFolder = "Assets/Art/E01/GhatSightlines";
        private const string ManifestPath = ArtFolder + "/GhatSightlines.json";
        private const string MaterialsFolder = ArtFolder + "/Materials";
        private const string ScenePath = "Assets/Scenes/E01_GhatSightlines.unity";
        private const string RiverMaterialName = "E01_River_silty_flood_water";

        [Serializable]
        private sealed class Manifest
        {
            public int schemaVersion;
            public float fps;
            public int startFrame;
            public int endFrame;
            public Geometry[] geometry;
            public CameraData[] cameras;
            public SightlineShot[] shots;
            public SightlineLighting[] lighting;
            public LampData lamp;
            public Surface[] materials;
            public Tracks verification;
        }

        [Serializable]
        private sealed class Geometry
        {
            public string fileName;
            public string name;
            public int activeFromFrame;
            public SightlinePose[] poses;
        }

        [Serializable]
        private sealed class CameraData
        {
            public string name;
            public float verticalFovDegrees;
            public float nearClipPlane;
            public float farClipPlane;
            public SightlinePose[] poses;
        }

        [Serializable]
        private sealed class LampData
        {
            public Vector3 position;
            public Quaternion rotation;
            public Color color;
            public float spotAngle;
            public float range;
        }

        [Serializable]
        private sealed class Surface
        {
            public string name;
            public Color color;
            public float roughness;
            public float metallic;
            public Color emissionColor;
            public float emissionIntensity;
        }

        [Serializable]
        private sealed class Tracks
        {
            public string waterTrack;
            public string boatTrack;
            public string gateTrack;
        }

        [MenuItem("Tools/Vikram/E01/Build Ghat Sightlines")]
        public static void Run()
        {
            if (!Application.isBatchMode && !EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())
                return;

            AssetDatabase.Refresh();
            Manifest data = ReadManifest();
            EnsureAssetFolder("Assets/Scenes");
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var root = new GameObject("E01 Ghat Sightlines");
            var timeline = root.AddComponent<SightlineTimeline>();
            var materials = CreateMaterials(data.materials);
            var geometry = CreateGeometry(root.transform, data.geometry, materials);
            var cameras = CreateCameras(root.transform, data.cameras);
            Light sun = AddLight(root.transform, "Sunlight", LightType.Directional);
            sun.shadowBias = .08f;
            Light lamp = AddLight(root.transform, "Chowki lamp", LightType.Spot);
            lamp.transform.SetPositionAndRotation(data.lamp.position, data.lamp.rotation);
            lamp.color = data.lamp.color;
            lamp.spotAngle = data.lamp.spotAngle;
            lamp.innerSpotAngle = .65f * data.lamp.spotAngle;
            lamp.range = data.lamp.range;

            Renderer[] river = FindTrack(geometry, data.verification.waterTrack).GetComponentsInChildren<Renderer>(true)
                .Where(renderer => renderer.sharedMaterials.Contains(materials[RiverMaterialName])).ToArray();
            Require(river.Length > 0, "No imported river surface uses the sightline water shader.");
            timeline.Configure(Mathf.RoundToInt(data.fps), data.startFrame, data.endFrame, data.shots, cameras, geometry,
                PrepareLighting(data.lighting), sun, lamp, river);
            Verify(timeline, data, geometry, sun, lamp);
            timeline.ApplyFrame(data.startFrame);
            Require(EditorSceneManager.SaveScene(scene, ScenePath), "Unity could not save the sightline scene.");
            var others = EditorBuildSettings.scenes.Where(entry => entry.path != ScenePath);
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) }.Concat(others).ToArray();
            AssetDatabase.SaveAssets();
            Debug.Log($"VIKRAM UNITY READY {ScenePath}: {geometry.Length} FBX groups, {cameras.Length} cameras, {data.shots.Length} checked cuts");
        }

        public static void RunAndRenderProofs()
        {
            Run();
            RenderProofs();
        }

        [MenuItem("Tools/Vikram/E01/Render Sightline Proofs")]
        public static void RenderProofs()
        {
            Require(SystemInfo.graphicsDeviceType != GraphicsDeviceType.Null,
                "Sightline renders require a graphics device. Run Unity without -nographics.");
            if (!Application.isBatchMode && !EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())
                return;

            EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var timeline = Object.FindFirstObjectByType<SightlineTimeline>();
            Require(timeline != null, "Build the sightline scene before rendering its proofs.");
            string folder = Path.GetFullPath(Path.Combine(Application.dataPath, "../../Renders/Unity/E01_Sightlines"));
            Directory.CreateDirectory(folder);
            foreach (SightlineShot shot in timeline.Shots)
            {
                timeline.ApplyFrame(shot.frame);
                string path = Path.Combine(folder, $"E01_Unity_{shot.frame:D3}.png");
                DrawCamera(timeline.ActiveCamera, path);
                Debug.Log($"VIKRAM UNITY PROOF {shot.label}: {path}");
            }
            timeline.ApplyFrame(timeline.StartFrame);
        }

        private static Manifest ReadManifest()
        {
            var asset = AssetDatabase.LoadAssetAtPath<TextAsset>(ManifestPath);
            Require(asset != null, $"Run the Blender sightline exporter to create {ManifestPath}.");
            var data = JsonUtility.FromJson<Manifest>(asset.text);
            Require(data != null && data.schemaVersion == 1, "Unsupported sightline manifest schema.");
            Require(Mathf.Approximately(data.fps, 24f) && data.startFrame < data.endFrame && data.geometry?.Length > 0 &&
                data.cameras?.Length == 3 && data.shots?.Length == 5 && data.materials?.Length > 0 &&
                data.lighting?.Length > 0 && data.lamp != null && data.verification != null,
                "The sightline manifest is incomplete.");
            return data;
        }

        private static Dictionary<string, Material> CreateMaterials(Surface[] surfaces)
        {
            EnsureAssetFolder(MaterialsFolder);
            Shader standard = Shader.Find("Standard");
            Shader unlit = Shader.Find("Unlit/Color");
            Shader riverShader = Shader.Find("Vikram/River Sightline");
            Require(standard != null && unlit != null && riverShader != null,
                "The sightline materials require the Standard, Unlit/Color and Vikram river shaders.");
            var result = new Dictionary<string, Material>(StringComparer.Ordinal);
            foreach (Surface surface in surfaces)
            {
                bool water = surface.name == RiverMaterialName;
                bool emissive = surface.emissionIntensity > 0f;
                Shader shader = water ? riverShader : emissive ? unlit : standard;
                string path = $"{MaterialsFolder}/{surface.name}.mat";
                Material material = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (material == null)
                {
                    material = new Material(shader) { name = surface.name };
                    AssetDatabase.CreateAsset(material, path);
                }
                material.shader = shader;
                if (!water && emissive)
                    material.color = Color.Lerp(surface.emissionColor.gamma, Color.white,
                        surface.emissionIntensity / (12f + surface.emissionIntensity));
                else if (!water)
                {
                    material.color = surface.color.gamma;
                    material.SetFloat("_Metallic", surface.metallic);
                    material.SetFloat("_Glossiness", 1f - Mathf.Clamp01(surface.roughness));
                }
                EditorUtility.SetDirty(material);
                result.Add(surface.name, material);
            }
            return result;
        }

        private static SightlineLighting[] PrepareLighting(SightlineLighting[] presets)
        {
            // Ambient fill and camera sky serve different purposes in the built-in renderer.
            var morning = new Color(.61f, .71f, .79f);
            var evening = new Color(.45f, .50f, .59f);
            var night = new Color(.058f, .091f, .146f);
            for (int i = 0; i < presets.Length; i++)
            {
                SightlineLighting state = presets[i];
                state.backgroundColor = state.sunIntensity <= 0f ? night :
                    Color.Lerp(evening, morning, Mathf.InverseLerp(.24f, .74f, state.sunColor.b));
                state.sunIntensity *= .72f;
                state.lampIntensity *= .58f;
                presets[i] = state;
            }
            return presets;
        }

        private static SightlineGeometryTrack[] CreateGeometry(Transform root, Geometry[] entries,
            Dictionary<string, Material> materials)
        {
            var tracks = new List<SightlineGeometryTrack>(entries.Length);
            Transform art = AddChild(root, "Environment and story props");
            foreach (Geometry entry in entries)
            {
                string path = $"{ArtFolder}/{entry.fileName}";
                var model = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                Require(model != null, $"Missing source FBX {path}.");
                Transform pivot = AddChild(art, entry.name);
                Transform correction = AddChild(pivot, "FBX axes and scale");
                var instance = (GameObject)PrefabUtility.InstantiatePrefab(model, correction);
                Calibrate(correction, instance.GetComponentsInChildren<Transform>(true));
                MeshRenderer[] renderers = instance.GetComponentsInChildren<MeshRenderer>(true);
                Require(renderers.Length > 0, $"{entry.fileName} imported without mesh renderers.");
                foreach (MeshRenderer renderer in renderers)
                {
                    var assigned = renderer.sharedMaterials;
                    for (int i = 0; i < assigned.Length; i++)
                    {
                        Require(assigned[i] != null && materials.ContainsKey(assigned[i].name),
                            $"{entry.fileName}/{renderer.name} has an unmapped material slot ({assigned[i]?.name}).");
                        assigned[i] = materials[assigned[i].name];
                    }
                    renderer.sharedMaterials = assigned;
                }
                tracks.Add(new SightlineGeometryTrack
                {
                    target = pivot,
                    activeFromFrame = entry.activeFromFrame,
                    poses = entry.poses ?? Array.Empty<SightlinePose>()
                });
            }
            return tracks.ToArray();
        }

        internal static void Calibrate(Transform correction, Transform[] nodes)
        {
            Transform origin = Axis(nodes, "Origin");
            Transform x = Axis(nodes, "X");
            Transform y = Axis(nodes, "Y");
            Transform z = Axis(nodes, "Z");
            Transform parent = correction.parent;
            Vector3 localOrigin = parent.InverseTransformPoint(origin.position);
            Matrix4x4 modelAxes = Matrix4x4.identity;
            modelAxes.SetColumn(0, parent.InverseTransformPoint(x.position) - localOrigin);
            modelAxes.SetColumn(1, parent.InverseTransformPoint(y.position) - localOrigin);
            modelAxes.SetColumn(2, parent.InverseTransformPoint(z.position) - localOrigin);
            modelAxes.SetColumn(3, new Vector4(localOrigin.x, localOrigin.y, localOrigin.z, 1f));
            Require(Mathf.Abs(modelAxes.determinant) > 1e-8f, $"{parent.name} FBX calibration axes are degenerate.");
            Matrix4x4 inverse = modelAxes.inverse;
            Vector3 a = inverse.GetColumn(0);
            Vector3 b = inverse.GetColumn(1);
            Vector3 c = inverse.GetColumn(2);
            float handedness = Mathf.Sign(Vector3.Dot(Vector3.Cross(a, b), c));
            correction.localScale = new Vector3(a.magnitude, b.magnitude, handedness * c.magnitude);
            correction.localRotation = Quaternion.LookRotation(handedness * c, b);
            correction.localPosition = inverse.GetColumn(3);
            Require(Near(parent.InverseTransformPoint(origin.position), Vector3.zero) &&
                Near(parent.InverseTransformPoint(x.position), Vector3.right) &&
                Near(parent.InverseTransformPoint(y.position), Vector3.up) &&
                Near(parent.InverseTransformPoint(z.position), Vector3.forward),
                $"{parent.name} FBX axes differ from the Unity timeline axes after calibration.");
        }

        private static Transform Axis(Transform[] nodes, string axis)
        {
            Transform marker = nodes.SingleOrDefault(node => node.name == "E01_Axis_" + axis);
            Require(marker != null, $"Missing FBX calibration marker E01_Axis_{axis}.");
            return marker;
        }

        private static SightlineCameraTrack[] CreateCameras(Transform root, CameraData[] entries)
        {
            Transform group = AddChild(root, "Sightline cameras");
            var tracks = new List<SightlineCameraTrack>(entries.Length);
            foreach (CameraData entry in entries)
            {
                Require(entry.poses?.Length > 0, $"{entry.name} has no pose samples.");
                var camera = AddChild(group, entry.name).gameObject.AddComponent<Camera>();
                camera.fieldOfView = entry.verticalFovDegrees;
                camera.nearClipPlane = entry.nearClipPlane;
                camera.farClipPlane = entry.farClipPlane;
                camera.clearFlags = CameraClearFlags.SolidColor;
                camera.allowHDR = true;
                camera.allowMSAA = true;
                camera.enabled = false;
                tracks.Add(new SightlineCameraTrack { camera = camera, poses = entry.poses });
            }
            return tracks.ToArray();
        }

        private static Light AddLight(Transform root, string name, LightType type)
        {
            var light = AddChild(root, name).gameObject.AddComponent<Light>();
            light.type = type;
            light.shadows = LightShadows.Soft;
            return light;
        }

        private static Transform AddChild(Transform parent, string name)
        {
            var child = new GameObject(name).transform;
            child.SetParent(parent, false);
            return child;
        }

        private static void Verify(SightlineTimeline timeline, Manifest data, SightlineGeometryTrack[] geometry,
            Light sun, Light lamp)
        {
            var byName = data.cameras.ToDictionary(camera => camera.name, StringComparer.Ordinal);
            foreach (SightlineShot shot in data.shots)
            {
                timeline.ApplyFrame(shot.frame);
                Camera camera = timeline.ActiveCamera;
                var expected = byName[shot.camera];
                SightlinePose sample = expected.poses.LastOrDefault(pose => pose.frame <= shot.frame);
                Require(camera != null && camera.name == shot.camera && Near(camera.transform.position, sample.position) &&
                    Quaternion.Angle(camera.transform.rotation, sample.rotation) < .03f &&
                    Mathf.Abs(camera.fieldOfView - expected.verticalFovDegrees) < .01f,
                    $"Unity camera pose differs at frame {shot.frame}.");
            }

            Transform water = FindTrack(geometry, data.verification.waterTrack);
            Transform boat = FindTrack(geometry, data.verification.boatTrack);
            Transform gate = FindTrack(geometry, data.verification.gateTrack);
            timeline.ApplyFrame(1);
            Vector3 windowPosition = timeline.ActiveCamera.transform.position;
            Quaternion windowRotation = timeline.ActiveCamera.transform.rotation;
            Require(Mathf.Abs(water.position.y - -2.2f) < .02f, "Morning river level differs from Blender.");
            Require(sun.intensity > 0f && Mathf.Approximately(lamp.intensity, 0f), "Morning light cues differ from Blender.");
            timeline.ApplyFrame(49);
            Require(Mathf.Abs(water.position.y - -1.4f) < .02f && Near(windowPosition, timeline.ActiveCamera.transform.position) &&
                Quaternion.Angle(windowRotation, timeline.ActiveCamera.transform.rotation) < .03f,
                "The evening river level changed without retaining the fixed hall view.");

            timeline.ApplyFrame(145);
            Require(Mathf.Approximately(sun.intensity, 0f) && lamp.intensity > 0f,
                "The testimony requires the lamp and night illumination.");
            Quaternion before = boat.rotation;
            float closed = gate.position.y;
            timeline.ApplyFrame(238);
            Require(Quaternion.Angle(before, boat.rotation) > 60f && Mathf.Abs(gate.position.y - closed) < .02f,
                "The boat turn and gate during testimony did not survive import.");
            timeline.ApplyFrame(354);
            Require(gate.position.y - closed > 2f, "The late gate lift did not survive import.");
        }

        private static Transform FindTrack(SightlineGeometryTrack[] tracks, string name)
        {
            return tracks.Single(track => track.target.name == name).target;
        }

        private static bool Near(Vector3 first, Vector3 second) => (first - second).sqrMagnitude < .0001f;

        private static void DrawCamera(Camera camera, string path)
        {
            const int width = 1440;
            const int height = 810;
            var target = RenderTexture.GetTemporary(width, height, 24, RenderTextureFormat.ARGB32);
            var source = RenderTexture.active;
            var original = camera.targetTexture;
            var image = new Texture2D(width, height, TextureFormat.RGB24, false);
            try
            {
                camera.targetTexture = target;
                camera.Render();
                RenderTexture.active = target;
                image.ReadPixels(new Rect(0, 0, width, height), 0, 0);
                image.Apply();
                File.WriteAllBytes(path, ImageConversion.EncodeToPNG(image));
            }
            finally
            {
                camera.targetTexture = original;
                RenderTexture.active = source;
                Object.DestroyImmediate(image);
                RenderTexture.ReleaseTemporary(target);
            }
        }

        private static void EnsureAssetFolder(string path)
        {
            if (AssetDatabase.IsValidFolder(path))
                return;
            int slash = path.LastIndexOf('/');
            string parent = path.Substring(0, slash);
            EnsureAssetFolder(parent);
            AssetDatabase.CreateFolder(parent, path.Substring(slash + 1));
        }

        private static void Require(bool condition, string message)
        {
            if (!condition)
                throw new InvalidDataException(message);
        }
    }
}
