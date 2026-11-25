using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using UnityEngine;

namespace Vikram.Dialogue
{
    // A timeline sampler shared by editor renders and scene playback. Time is
    // measured from the first frame of the cut, independently of Unity playback.
    public sealed class DialogueLipSync
    {
        private static readonly string[] MouthShapes =
        {
            "Mouth_Ah", "Mouth_O", "Mouth_Ee", "Mouth_MBP",
            "Mouth_FV", "Mouth_U", "Mouth_L", "Mouth_Consonant"
        };

        // Rhubarb A–H, the IPA front-vowel extension I, and neutral X.
        private static readonly float[][] Visemes =
        {
            new float[] {  0,  0,  0, 100,  0,  0,  0,  0 },
            new float[] {  0,  0,  0,   0,  0,  0,  0, 85 },
            new float[] { 43,  0, 18,   0,  0,  0,  0,  0 },
            new float[] { 82,  0,  0,   0,  0,  0,  0,  0 },
            new float[] {  0, 60,  0,   0,  0,  0,  0,  0 },
            new float[] {  0,  0,  0,   0,  0, 90,  0,  0 },
            new float[] {  0,  0,  0,   0, 85,  0,  0,  0 },
            new float[] {  0,  0,  0,   0,  0,  0, 80,  0 },
            new float[] {  9,  0, 72,   0,  0,  0,  0,  0 },
            new float[] {  0,  0,  0,   0,  0,  0,  0,  0 },
        };

        private const int Quiet = 9;
        private const float MaxTransition = 0.05f;

#pragma warning disable CS0649 // Populated by Unity's JSON serializer.
        [Serializable]
        private sealed class Track
        {
            public Cue[] cues;
        }

        [Serializable]
        private sealed class Cue
        {
            public string speaker;
            public float start;
            public float duration;
            public MouthCue[] mouthCues;
        }

        [Serializable]
        private sealed class MouthCue
        {
            public float start;
            public float end;
            public string value;
        }
#pragma warning restore CS0649

        private sealed class ActorTrack
        {
            public readonly List<Cue> Cues = new();
            public readonly List<ShapeBinding> Shapes = new();
        }

        private readonly struct ShapeBinding
        {
            private readonly SkinnedMeshRenderer renderer;
            private readonly int shape;
            private readonly int mouth;
            private readonly float gain;

            public ShapeBinding(SkinnedMeshRenderer renderer, int shape, int mouth, float gain = 1f)
            {
                this.renderer = renderer;
                this.shape = shape;
                this.mouth = mouth;
                this.gain = gain;
            }

            public void Apply(int from, int to, float blend)
            {
                float weight = gain * Mathf.Lerp(Visemes[from][mouth], Visemes[to][mouth], blend);
                renderer.SetBlendShapeWeight(shape, Mathf.Min(100f, weight));
            }
        }

        private readonly Dictionary<string, ActorTrack> actors = new(StringComparer.OrdinalIgnoreCase);

        public int BoundSpeakerCount { get; private set; }
        public int BoundMouthShapeCount { get; private set; }

        public DialogueLipSync(GameObject castRoot, string json)
        {
            Track track = JsonUtility.FromJson<Track>(json);
            if (track?.cues == null || track.cues.Length == 0)
                throw new ArgumentException("The dialogue track has no cues.", nameof(json));

            foreach (Cue cue in track.cues)
            {
                if (!actors.TryGetValue(cue.speaker, out ActorTrack actor))
                    actors.Add(cue.speaker, actor = new ActorTrack());
                actor.Cues.Add(cue);
            }

            SkinnedMeshRenderer[] renderers = castRoot.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            foreach (var entry in actors)
            {
                entry.Value.Cues.Sort((before, after) => before.start.CompareTo(after.start));
                var actorName = new Regex("(^|[^a-z0-9])" + Regex.Escape(entry.Key) + "([^a-z0-9]|$)",
                    RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
                int mouthCount = 0;
                foreach (SkinnedMeshRenderer renderer in renderers)
                {
                    Mesh mesh = renderer.sharedMesh;
                    if (mesh == null || mesh.blendShapeCount == 0 ||
                        (!actorName.IsMatch(mesh.name) && !MatchesActor(renderer.transform, castRoot.transform, actorName)))
                        continue;

                    for (int shape = 0; shape < mesh.blendShapeCount; shape++)
                    {
                        string shapeName = mesh.GetBlendShapeName(shape);
                        int mouth = Array.FindIndex(MouthShapes, key => shapeName.EndsWith(key, StringComparison.OrdinalIgnoreCase));
                        if (mouth >= 0)
                        {
                            mouthCount++;
                            entry.Value.Shapes.Add(new ShapeBinding(renderer, shape, mouth));
                        }
                        else if (shapeName.EndsWith("Show", StringComparison.OrdinalIgnoreCase))
                        {
                            string part = renderer.name.Replace('_', ' ');
                            if (part.Contains("Upper teeth", StringComparison.OrdinalIgnoreCase))
                                entry.Value.Shapes.Add(new ShapeBinding(renderer, shape, 0, 2f));
                            else if (part.Contains("Tongue", StringComparison.OrdinalIgnoreCase))
                                entry.Value.Shapes.Add(new ShapeBinding(renderer, shape, 6, 2f));
                        }
                    }
                }

                if (mouthCount == 0)
                    Debug.LogWarning($"No mouth blend shapes found for dialogue speaker {entry.Key}.");
                else
                {
                    BoundSpeakerCount++;
                    BoundMouthShapeCount += mouthCount;
                }
            }
        }

        public void Apply(float timelineSeconds)
        {
            foreach (ActorTrack actor in actors.Values)
            {
                int from = Quiet, to = Quiet;
                float blend = 0f;
                foreach (Cue cue in actor.Cues)
                {
                    float clock = timelineSeconds - cue.start;
                    if (clock < 0f)
                        break;
                    if (clock < cue.duration)
                    {
                        Sample(cue.mouthCues, clock, out from, out to, out blend);
                        break;
                    }
                }
                foreach (ShapeBinding shape in actor.Shapes)
                    shape.Apply(from, to, blend);
            }
        }

        private static bool MatchesActor(Transform renderer, Transform castRoot, Regex actor)
        {
            for (Transform node = renderer; node != null; node = node.parent)
            {
                if (actor.IsMatch(node.name))
                    return true;
                if (node == castRoot)
                    break;
            }
            return false;
        }

        private static void Sample(MouthCue[] cues, float clock, out int from, out int to, out float blend)
        {
            from = Quiet;
            to = Quiet;
            blend = 0f;
            for (int index = 0; index < cues.Length; index++)
            {
                MouthCue cue = cues[index];
                if (clock < cue.start)
                    break;
                if (clock >= cue.end)
                    continue;

                from = ShapeIndex(cue);
                to = from;
                float width = Mathf.Min(MaxTransition, (cue.end - cue.start) * 0.35f);
                float enter = clock - cue.start;
                float exit = cue.end - clock;
                if (enter < width)
                {
                    from = index == 0 ? Quiet : ShapeIndex(cues[index - 1]);
                    blend = 0.5f + 0.5f * Mathf.SmoothStep(0f, 1f, enter / width);
                }
                else if (exit < width)
                {
                    to = index == cues.Length - 1 ? Quiet : ShapeIndex(cues[index + 1]);
                    blend = 0.5f * (1f - Mathf.SmoothStep(0f, 1f, exit / width));
                }
                return;
            }
        }

        private static int ShapeIndex(MouthCue cue)
        {
            char shape = cue.value[0];
            return shape >= 'A' && shape <= 'I' ? shape - 'A' : Quiet;
        }
    }
}
