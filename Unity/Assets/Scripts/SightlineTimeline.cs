using System;
using UnityEngine;
using UnityEngine.Rendering;

namespace Vikram.Sightlines
{
    [Serializable]
    public struct SightlinePose
    {
        public int frame;
        public Vector3 position;
        public Quaternion rotation;
    }

    [Serializable]
    public struct SightlineShot
    {
        public int frame;
        public string label;
        public string camera;
    }

    [Serializable]
    public struct SightlineLighting
    {
        public int frame;
        public Color ambientColor;
        public Color backgroundColor;
        public Color sunColor;
        public Quaternion sunRotation;
        public float sunIntensity;
        public float lampIntensity;
    }

    [Serializable]
    public sealed class SightlineGeometryTrack
    {
        public Transform target;
        public int activeFromFrame;
        public SightlinePose[] poses;
    }

    [Serializable]
    public sealed class SightlineCameraTrack
    {
        public Camera camera;
        public SightlinePose[] poses;
    }

    [DisallowMultipleComponent]
    public sealed class SightlineTimeline : MonoBehaviour
    {
        [SerializeField] private bool playOnStart = true;
        [SerializeField] private bool loop;
        [SerializeField, HideInInspector] private int framesPerSecond = 24;
        [SerializeField, HideInInspector] private int startFrame = 1;
        [SerializeField, HideInInspector] private int endFrame = 384;
        [SerializeField, HideInInspector] private float frame;
        [SerializeField, HideInInspector] private SightlineShot[] shots;
        [SerializeField, HideInInspector] private SightlineCameraTrack[] cameras;
        [SerializeField, HideInInspector] private SightlineGeometryTrack[] geometry;
        [SerializeField, HideInInspector] private SightlineLighting[] lighting;
        [SerializeField, HideInInspector] private Light sunlight;
        [SerializeField, HideInInspector] private Light lamp;
        [SerializeField, HideInInspector] private Renderer[] river;

        private bool playing;
        private MaterialPropertyBlock riverProperties;
        private static readonly int RiverNight = Shader.PropertyToID("_RiverNight");
        private static readonly int RiverTime = Shader.PropertyToID("_RiverTime");

        public int StartFrame => startFrame;
        public int EndFrame => endFrame;
        public float Frame => frame;
        public SightlineShot[] Shots => shots;
        public Camera ActiveCamera { get; private set; }

        public void Configure(int fps, int first, int last, SightlineShot[] shotList,
            SightlineCameraTrack[] cameraTracks, SightlineGeometryTrack[] geometryTracks,
            SightlineLighting[] lightingCues, Light sun, Light spot, Renderer[] riverRenderers)
        {
            framesPerSecond = fps;
            startFrame = first;
            endFrame = last;
            shots = shotList;
            cameras = cameraTracks;
            geometry = geometryTracks;
            lighting = lightingCues;
            sunlight = sun;
            lamp = spot;
            river = riverRenderers;
            ApplyFrame(first);
        }

        private void OnEnable()
        {
            if (cameras == null || cameras.Length == 0)
                return;

            playing = playOnStart;
            ApplyFrame(playing ? startFrame : frame);
        }

        private void Update()
        {
            if (!playing)
                return;

            float next = frame + Time.unscaledDeltaTime * framesPerSecond;
            if (next > endFrame)
            {
                if (loop)
                    next = startFrame + Mathf.Repeat(next - startFrame, endFrame - startFrame + 1);
                else
                    playing = false;
            }

            ApplyFrame(next);
        }

        public void ApplyFrame(float next)
        {
            if (shots == null || shots.Length == 0)
                return;

            frame = Mathf.Clamp(next, startFrame, endFrame);
            foreach (SightlineGeometryTrack track in geometry)
            {
                bool visible = frame >= track.activeFromFrame;
                if (track.target.gameObject.activeSelf != visible)
                    track.target.gameObject.SetActive(visible);
                if (track.poses.Length > 0)
                    SetPose(track.target, track.poses, frame);
            }

            SightlineShot shot = shots[0];
            foreach (SightlineShot cue in shots)
            {
                if (cue.frame > frame)
                    break;
                shot = cue;
            }

            foreach (SightlineCameraTrack track in cameras)
            {
                SetPose(track.camera.transform, track.poses, frame);
                track.camera.enabled = track.camera.name == shot.camera;
                if (track.camera.enabled)
                    ActiveCamera = track.camera;
            }

            ApplyLighting();
        }

        private void ApplyLighting()
        {
            if (lighting == null || lighting.Length == 0)
                return;

            SightlineLighting active = lighting[0];
            foreach (SightlineLighting cue in lighting)
            {
                if (cue.frame > frame)
                    break;
                active = cue;
            }

            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = active.ambientColor;
            RenderSettings.sun = sunlight;
            if (ActiveCamera != null)
                ActiveCamera.backgroundColor = active.backgroundColor;
            sunlight.color = active.sunColor;
            sunlight.intensity = active.sunIntensity;
            sunlight.transform.rotation = active.sunRotation;
            lamp.intensity = active.lampIntensity;

            if (river == null || river.Length == 0)
                return;

            riverProperties ??= new MaterialPropertyBlock();
            foreach (Renderer renderer in river)
            {
                renderer.GetPropertyBlock(riverProperties);
                riverProperties.SetFloat(RiverNight, active.sunIntensity <= 0f ? 1f : 0f);
                riverProperties.SetFloat(RiverTime, (frame - startFrame) / framesPerSecond);
                renderer.SetPropertyBlock(riverProperties);
            }
        }

        private static void SetPose(Transform target, SightlinePose[] samples, float atFrame)
        {
            SightlinePose first = samples[0];
            SightlinePose last = samples[samples.Length - 1];
            if (atFrame <= first.frame || samples.Length == 1)
            {
                target.SetPositionAndRotation(first.position, first.rotation);
                return;
            }

            if (atFrame >= last.frame)
            {
                target.SetPositionAndRotation(last.position, last.rotation);
                return;
            }

            int low = 0;
            int high = samples.Length - 1;
            while (high - low > 1)
            {
                int middle = (low + high) / 2;
                if (samples[middle].frame > atFrame)
                    high = middle;
                else
                    low = middle;
            }

            SightlinePose before = samples[low];
            SightlinePose after = samples[high];
            float blend = Mathf.InverseLerp(before.frame, after.frame, atFrame);
            target.SetPositionAndRotation(Vector3.Lerp(before.position, after.position, blend),
                Quaternion.Slerp(before.rotation, after.rotation, blend));
        }
    }
}
