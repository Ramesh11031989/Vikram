using System;
using UnityEngine;
using UnityEngine.Rendering;
using Vikram.Dialogue;

namespace Vikram.Performance
{
    [Serializable]
    public sealed class PerformanceManifest
    {
        public int fps;
        public int frameCount;
        public string[] assets;
        public FilmShot[] shots;
        public FilmCameraTrack[] cameras;
        public FilmLightData[] lights;
        public FilmMaterial[] materials;
        public FilmVisibility[] visibility;
    }

    [Serializable]
    public sealed class FilmShot
    {
        public string camera;
        public string set;
        public int startFrame;
        public int endFrame;
    }

    [Serializable]
    public sealed class FilmCameraTrack
    {
        public string name;
        public float near;
        public float far;
        public float orthographicSize;
        public FilmCameraPose[] poses;
        [HideInInspector] public Camera camera;
    }

    [Serializable]
    public struct FilmCameraPose
    {
        public int frame;
        public Vector3 position;
        public Vector3 forward;
        public Vector3 up;
        public float fov;

        public Quaternion Rotation => Quaternion.LookRotation(forward, up);
    }

    [Serializable]
    public sealed class FilmLightData
    {
        public string name;
        public string set;
        public string type;
        public Vector3 position;
        public Vector3 forward;
        public Vector3 up;
        public Color color;
        public float energy;
        public float size;
        public float spotAngle;
    }

    [Serializable]
    public sealed class FilmMaterial
    {
        public string name;
        public Color color;
        public float roughness;
        public float metallic;
        public Color emissionColor;
        public float emissionIntensity;
    }

    [Serializable]
    public sealed class FilmVisibility
    {
        public string name;
        public string set;
    }

    [Serializable]
    public sealed class FilmModelTrack
    {
        public GameObject root;
        public AnimationClip clip;
    }

    [Serializable]
    public sealed class FilmSetTrack
    {
        public string set;
        public Renderer[] renderers;
        public Light[] lights;
    }

    [DisallowMultipleComponent]
    public sealed class PerformanceFilm : MonoBehaviour
    {
        [SerializeField] private int fps = 24;
        [SerializeField] private int frameCount;
        [SerializeField] private FilmShot[] shots;
        [SerializeField] private FilmCameraTrack[] cameras;
        [SerializeField] private FilmModelTrack[] models;
        [SerializeField] private FilmSetTrack[] sets;
        [SerializeField] private AudioSource soundtrack;
        [SerializeField] private TextAsset lipTrack;
        [SerializeField] private bool playOnStart = true;
        private string activeSet;
        private Camera activeCamera;
        private double startTime;
        private bool playing;
        private DialogueLipSync lips;

        public int Fps => fps;
        public int FrameCount => frameCount;
        public Camera ActiveCamera => activeCamera;
        public FilmShot[] Shots => shots;
        public int SpeakingActors => lips?.BoundSpeakerCount ?? 0;
        public int MouthShapes => lips?.BoundMouthShapeCount ?? 0;

        public void Configure(PerformanceManifest manifest, FilmModelTrack[] modelTracks,
            FilmSetTrack[] setTracks, AudioSource audio, TextAsset dialogue)
        {
            fps = manifest.fps;
            frameCount = manifest.frameCount;
            shots = manifest.shots;
            cameras = manifest.cameras;
            models = modelTracks;
            sets = setTracks;
            soundtrack = audio;
            lipTrack = dialogue;
            lips = null;
            activeSet = null;
            ApplyFrame(0);
        }

        private void OnEnable()
        {
            if (frameCount == 0)
                return;

            activeSet = null;
            ApplyFrame(0);
            if (Application.isPlaying && playOnStart)
            {
                startTime = Time.unscaledTimeAsDouble;
                if (soundtrack != null && soundtrack.clip != null)
                    soundtrack.Play();
                playing = true;
            }
        }

        private void Update()
        {
            if (!playing)
                return;

            double offset = soundtrack != null && soundtrack.isPlaying
                ? soundtrack.timeSamples / (double)soundtrack.clip.frequency
                : Time.unscaledTimeAsDouble - startTime;
            float frame = (float)(offset * fps);
            ApplyFrame(frame);
            if (frame >= frameCount)
                playing = false;
        }

        public void ApplyFrame(float frame)
        {
            if (frameCount == 0)
                return;

            frame = Mathf.Clamp(frame, 0f, frameCount - 1);
            float seconds = frame / fps;
            foreach (FilmModelTrack model in models)
            {
                if (model.clip != null)
                    model.clip.SampleAnimation(model.root, Mathf.Min(seconds, model.clip.length));
            }

            if (lipTrack != null)
            {
                lips ??= new DialogueLipSync(gameObject, lipTrack.text);
                lips.Apply(seconds);
            }

            FilmShot current = shots[0];
            foreach (FilmShot shot in shots)
            {
                if (shot.startFrame > frame)
                    break;
                current = shot;
            }

            if (activeSet != current.set)
            {
                ApplySet(current.set);
                activeSet = current.set;
            }

            foreach (FilmCameraTrack track in cameras)
            {
                track.camera.enabled = track.name == current.camera;
                if (track.camera.enabled)
                {
                    activeCamera = track.camera;
                    ApplyCamera(track, frame);
                }
            }

            Shader.SetGlobalFloat("_FilmTime", seconds);
        }

        private void ApplySet(string shotSet)
        {
            foreach (FilmSetTrack track in sets)
            {
                bool visible = string.IsNullOrEmpty(track.set) || track.set == shotSet;
                foreach (Renderer renderer in track.renderers)
                    renderer.enabled = visible;
                foreach (Light light in track.lights)
                    light.enabled = visible;
            }

            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = shotSet == "river"
                ? new Color(.137f, .172f, .243f)
                : new Color(.47f, .44f, .41f);
            RenderSettings.fog = false;
        }

        private static void ApplyCamera(FilmCameraTrack track, float frame)
        {
            FilmCameraPose[] poses = track.poses;
            int lo = 0;
            int hi = poses.Length - 1;
            while (lo + 1 < hi)
            {
                int mid = (lo + hi) / 2;
                if (poses[mid].frame > frame)
                    hi = mid;
                else
                    lo = mid;
            }

            FilmCameraPose first = poses[lo];
            FilmCameraPose last = poses[hi];
            float progress = Mathf.InverseLerp(first.frame, last.frame, frame);
            track.camera.transform.SetPositionAndRotation(Vector3.Lerp(first.position, last.position, progress),
                Quaternion.Slerp(first.Rotation, last.Rotation, progress));
            if (!track.camera.orthographic)
                track.camera.fieldOfView = Mathf.Lerp(first.fov, last.fov, progress);
        }
    }
}
