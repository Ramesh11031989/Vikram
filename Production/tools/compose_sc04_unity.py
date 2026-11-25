"""Master the Unity interrogation cut with timed Hindi dialogue, foley and score."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import wave


ROOT = Path(__file__).resolve().parents[2]
EPISODE = ROOT / 'Production/E01'
MUSIC = EPISODE / 'Audio/Music/Review/E01_river_mystery_15s_4516.wav'
COURT_MUSIC = EPISODE / 'Audio/Music/Review/E01_royal_court_18s_4517.wav'
FOLEY = EPISODE / 'Audio/E01_SC04_Ambience_Foley.wav'
RENDER = ROOT / 'Renders/Unity/E01_SC04'
VOICE = ROOT / 'Renders/E01_SC04_Dialogue'


def ass_time(frame, fps):
    seconds, fraction = divmod(round(frame * 100 / fps), 100)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f'{hours}:{minutes:02}:{seconds:02}.{fraction:02}'


def subtitle_script(timeline, font):
    fps = timeline['fps']
    headers = f'''[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Series,{font},27,&H00C9E1EF,&H00000000,&H48141210,&H58141210,0,0,0,0,100,100,0,0,1,1.6,1,8,46,46,54,1
Style: Chapter,{font},53,&H00E4F4FF,&H00000000,&H48141210,&H58141210,-1,0,0,0,100,100,0,0,1,2,1,8,46,46,92,1
Style: Scene,{font},26,&H00C9E1EF,&H00000000,&H48141210,&H58141210,0,0,0,0,100,100,0,0,1,1.6,1,8,46,46,160,1
Style: Dialogue,{font},39,&H00F8F5F2,&H00000000,&H00120E0B,&H7C120E0B,0,0,0,0,100,100,0,0,1,2.6,0.6,2,90,90,45,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
'''
    title = [
        ('Series', r'{\fad(380,430)}विक्रम-बेताल: तर्क पच्चीसी'),
        ('Chapter', r'{\fad(440,430)}सात गवाह, एक आवाज़'),
        ('Scene', r'{\fad(530,430)}गोपाल की गवाही'),
    ]
    title_end = min(round(fps * 3.35), timeline['shots'][0]['end_frame_exclusive'])
    rows = [f'Dialogue: 0,0:00:00.00,{ass_time(title_end, fps)},{style},,0,0,0,,{caption}'
            for style, caption in title]
    for cue in timeline['cues']:
        text = cue['dialogue_hi'].replace('{', '｛').replace('}', '｝').replace('\n', r'\N')
        start = ass_time(cue['start_frame'], fps)
        end = ass_time(cue['end_frame_exclusive'], fps)
        rows.append(f'Dialogue: 0,{start},{end},Dialogue,,0,0,0,,{text}')
    return headers + '\n'.join(rows) + '\n'


def score_filter(timeline, court_duration):
    fps = timeline['fps']
    shots = {shot['id'].rsplit('_', 1)[1]: shot['start_frame'] / fps for shot in timeline['shots']}
    duration = timeline['total_frames'] / fps
    stereo = 'aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo'
    # Court motif brackets the recollection, with two short river excerpts under the night inserts.
    placements = [
        ('courtintro', 'intro', 0., 0., min(shots['SH03'] + .28, 9.0), .42, .90, .55),
        ('courtoutro', 'outro', 0., max(shots['SH11'] - .18, duration - court_duration), duration, .52, 1.85, .52),
        ('riverfirst', 'water1', .36, shots['SH03'] - .14, shots['SH05'] + .36, .58, 1.05, .82),
        ('riversecond', 'water2', 1.28, shots['SH08'] - .18, shots['SH10'] + .34, .65, 1.10, .73),
    ]
    filters = [f'[2:a]{stereo},asplit=2[riverfirst][riversecond]',
               f'[3:a]{stereo},asplit=2[courtintro][courtoutro]']
    for source, tag, offset, start, end, fade_in, fade_out, level in placements:
        cue_length = end - start
        filters.append(f'[{source}]atrim=start={offset:.6f}:duration={cue_length:.6f},asetpts=PTS-STARTPTS,'
                       f'afade=t=in:d={fade_in},afade=t=out:st={cue_length-fade_out:.6f}:d={fade_out},'
                       f'volume={level},adelay={round(start * 48000)}S:all=1[{tag}]')
    filters.extend([
        f'[intro][outro][water1][water2]amix=inputs=4:duration=longest:normalize=0,{stereo},apad[score]',
        f'[0:a]{stereo},highpass=f=65,acompressor=threshold=.13:ratio=2:attack=5:release=90:makeup=1.12,'
        f'{stereo},asplit=2[dialogue][duck]',
        '[score][duck]sidechaincompress=threshold=.045:ratio=4.5:attack=18:release=380[ducked]',
        f'[1:a]{stereo},volume=1.45[foley]',
        '[dialogue][ducked][foley]amix=inputs=3:duration=first:normalize=0,volume=1.42,'
        f'alimiter=limit=.92:attack=5:release=50:level=disabled,apad,atrim=duration={duration:.8f}[master]',
    ])
    return ';'.join(filters)


def validate_soundtrack(soundtrack, timeline):
    with wave.open(str(soundtrack), 'rb') as stream:
        expected = round(timeline['total_frames'] * stream.getframerate() / timeline['fps'])
        if stream.getnchannels() != 2 or abs(stream.getnframes() - expected) > 1:
            raise ValueError('The stereo soundtrack duration does not match the picture edit.')


def mix(args, timeline, soundtrack):
    court = args.court_music.resolve()
    with wave.open(str(court), 'rb') as stream:
        court_duration = stream.getnframes() / stream.getframerate()
    command = [args.ffmpeg, '-hide_banner', '-loglevel', 'warning', '-y',
               '-i', str(args.dialogue.resolve()), '-i', str(FOLEY),
               '-i', str(MUSIC), '-i', str(court),
               '-filter_complex', score_filter(timeline, court_duration), '-map', '[master]',
               '-c:a', 'pcm_s16le', '-ar', '48000', str(soundtrack)]
    subprocess.run(command, check=True)
    validate_soundtrack(soundtrack, timeline)


def encode(args, timeline):
    fps = timeline['fps']
    total = timeline['total_frames']
    frames = args.frames.resolve()
    pattern = args.pattern
    for index in range(total):
        frame = frames / (pattern % index)
        if not frame.is_file() or frame.stat().st_size < 100:
            raise FileNotFoundError(f'Missing Unity picture frame {frame}')

    output = (args.output or RENDER / 'E01_Gopal_Testimony_Unity.mp4').resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='unity-master-', dir=output.parent) as work:
        work = Path(work)
        (work / 'captions.ass').write_text(subtitle_script(timeline, args.font), encoding='utf-8')
        soundtrack = args.use_soundtrack.resolve() if args.use_soundtrack else work / 'soundtrack.wav'
        if args.use_soundtrack:
            validate_soundtrack(soundtrack, timeline)
        else:
            mix(args, timeline, soundtrack)
        movie = work / 'master.mp4'
        command = [args.ffmpeg, '-hide_banner', '-loglevel', 'warning', '-y',
                   '-framerate', str(fps), '-start_number', '0', '-i', str(frames / pattern),
                   '-i', str(soundtrack), '-map', '0:v:0', '-map', '1:a:0',
                   '-vf', f'fps=fps={fps}:eof_action=pass,ass=captions.ass',
                   '-frames:v', str(total), '-t', f'{total / fps:.8f}', '-c:v', 'libx264', '-crf', '17',
                   '-preset', 'fast', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
                   '-ar', '48000', '-movflags', '+faststart', str(movie)]
        subprocess.run(command, cwd=work, check=True)
        probe = json.loads(subprocess.check_output([args.ffprobe, '-v', 'error', '-show_streams',
                                                     '-of', 'json', str(movie)], text=True))
        video = next(stream for stream in probe['streams'] if stream['codec_type'] == 'video')
        audio = next(stream for stream in probe['streams'] if stream['codec_type'] == 'audio')
        if (int(video['nb_frames']) != total or abs(float(audio['duration']) - total / fps) > .08
                or audio.get('channels') != 2 or video['r_frame_rate'] != f'{fps}/1'):
            raise ValueError(f'Unexpected picture or sound timing. Video: {video}; audio: {audio}')
        movie.replace(output)
    print(f'{output}\n{video["width"]}x{video["height"]} at {fps} fps, {total} frames, {total/fps:.3f}s, stereo audio')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frames', type=Path, default=RENDER / 'frames')
    parser.add_argument('--pattern', default='frame_%05d.png')
    parser.add_argument('--timeline', type=Path, default=VOICE / 'E01_SC04_Animatic_Timeline.json')
    parser.add_argument('--dialogue', type=Path, default=VOICE / 'Audio/E01_SC04_Dialogue_Mix.wav')
    parser.add_argument('--court-music', type=Path, default=COURT_MUSIC)
    parser.add_argument('--mix-only', action='store_true', help='Export a Unity-ready stereo WAV instead of a movie')
    parser.add_argument('--use-soundtrack', type=Path, help='Use a pre-mixed WAV when encoding the movie')
    parser.add_argument('--font', default='Nirmala UI' if os.name == 'nt' else 'FreeSans')
    parser.add_argument('--ffmpeg', default='ffmpeg')
    parser.add_argument('--ffprobe', default='ffprobe')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        timeline = json.loads(args.timeline.read_text(encoding='utf-8'))
        if args.mix_only:
            destination = (args.output or RENDER / 'E01_SC04_Master.wav').resolve()
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='unity-mix-', dir=destination.parent) as work:
                soundtrack = Path(work) / 'soundtrack.wav'
                mix(args, timeline, soundtrack)
                soundtrack.replace(destination)
            print(destination)
        else:
            encode(args, timeline)
    except (OSError, ValueError, wave.Error, subprocess.CalledProcessError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
