using UnityEditor;
using UnityEngine;
using Vikram.Sightlines;

namespace Vikram.Editor
{
    [CustomEditor(typeof(SightlineTimeline))]
    public sealed class SightlineTimelineEditor : UnityEditor.Editor
    {
        public override void OnInspectorGUI()
        {
            DrawDefaultInspector();
            var timeline = (SightlineTimeline)target;
            if (timeline.Shots == null || timeline.Shots.Length == 0)
                return;

            using (new EditorGUI.DisabledScope(Application.isPlaying))
            {
                EditorGUI.BeginChangeCheck();
                int frame = EditorGUILayout.IntSlider("Preview frame", Mathf.RoundToInt(timeline.Frame),
                    timeline.StartFrame, timeline.EndFrame);
                if (EditorGUI.EndChangeCheck())
                    Preview(timeline, frame);

                foreach (SightlineShot shot in timeline.Shots)
                {
                    if (GUILayout.Button($"{shot.frame:000}  {shot.label}"))
                        Preview(timeline, shot.frame);
                }
            }
        }

        private static void Preview(SightlineTimeline timeline, int frame)
        {
            timeline.ApplyFrame(frame);
            SceneView.RepaintAll();
            EditorApplication.QueuePlayerLoopUpdate();
        }
    }
}
