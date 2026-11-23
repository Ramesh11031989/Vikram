"""Encode real rendered motion, add Hindi subtitles, and mix dialogue with foley."""

from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess
import wave

import numpy as np

from compose_sc04 import default_font


ROOT=Path(__file__).resolve().parents[2]
EPISODE=ROOT/'Production/E01'
OUTPUT=EPISODE/'Performance'


def run(command: list[str]) -> None:
    subprocess.run(command,check=True)


def sound_mix(timeline) -> None:
    rate=timeline['sample_rate']
    with wave.open(str(EPISODE/'Audio/E01_SC04_Dialogue_Mix.wav'),'rb') as stream:
        dialogue=np.frombuffer(stream.readframes(stream.getnframes()),dtype='<i2').astype(np.float64)/32768
    rng=np.random.default_rng(20261123)
    ambience=np.zeros(len(dialogue))
    foley=np.zeros(len(dialogue))
    def noise_event(frame,length,gain,kind):
        start=round(frame*rate/24)
        count=round(length*rate)
        noise=rng.normal(size=count)
        time=np.arange(count)/rate
        if kind=='tap':
            signal=np.sin(time*math.tau*125)*np.exp(-time*38)+.10*noise*np.exp(-time*45)
        elif kind=='water':
            signal=np.convolve(noise,np.ones(9)/9,mode='same')*np.exp(-time*9)
        else:
            signal=np.convolve(noise,np.ones(3)/3,mode='same')*np.sin(np.pi*np.minimum(1,time/length))**2
        end=min(len(foley),start+count)
        if start>=0 and start<end:
            foley[start:end]+=signal[:end-start]*gain
    for shot in timeline['shots']:
        start=round(shot['start_frame']*rate/24)
        end=min(len(dialogue),round(shot['end_frame_exclusive']*rate/24))
        count=end-start
        noise=rng.normal(size=count)
        smoothed=np.convolve(noise,np.ones(25)/25,mode='same')
        time=np.arange(count)/rate
        gain=.0045 if shot['set']=='river' else .0008
        ambience[start:end]=smoothed*gain*(.65+.35*np.sin(time*2.5)**2)
    noise_event(12,.18,.023,'tap')
    noise_event(43,.22,.018,'tap')
    cues={cue['cue_id'][-3:]:cue for cue in timeline['cues']}
    noise_event(cues['L03']['start_frame']-2,.14,.013,'tap')
    noise_event(cues['L06']['start_frame']+12,.4,.008,'cloth')
    hand=next(shot for shot in timeline['shots'] if shot['id'].endswith('SH09'))
    noise_event(hand['start_frame']+28,.55,.012,'water')
    for frame in range(timeline['shots'][-1]['start_frame']+32,timeline['total_frames']-6,13):
        noise_event(frame,.22,.0038,'pen')
    mixed=np.clip(dialogue+ambience+foley,-.98,.98)
    for name,values in (('E01_SC04_Performance_Mix.wav',mixed),
                        ('E01_SC04_Ambience_Foley.wav',ambience+foley)):
        with wave.open(str(EPISODE/'Audio'/name),'wb') as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(rate)
            stream.writeframes((values*32767).astype('<i2').tobytes())


def main() -> None:
    render=json.loads((OUTPUT/'Render_Manifest.json').read_text())
    timeline=json.loads((EPISODE/'E01_SC04_Animatic_Timeline.json').read_text(encoding='utf-8'))
    cache=OUTPUT/'VideoCache'
    cache.mkdir(exist_ok=True)
    for shot in render['shots']:
        count=shot['end_frame_exclusive']-shot['start_frame']
        source=EPISODE/shot['directory']/'frame_%05d.png'
        run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(24/render['step']),
             '-i',str(source),'-vf','fps=24','-frames:v',str(count),'-an',
             '-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p',str(cache/f"{shot['id']}.mp4")])
    concat=cache/'shots.txt'
    concat.write_text(''.join(f"file '{shot['id']}.mp4'\n" for shot in render['shots']))
    silent=cache/'motion.mp4'
    run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','1',
         '-i',str(concat),'-c','copy',str(silent)])
    sound_mix(timeline)
    font=default_font().as_posix().replace(':','\\:')
    filters=("drawbox=x=0:y=0:w=iw:h=33:color=black@0.5:t=fill,"
             f"drawtext=fontfile='{font}':text='VIKRAM - BETAL  /  PERFORMANCE v0.2  /  SYNTHETIC VOICES':"
             "fontsize=13:fontcolor=white@0.85:x=14:y=10,"
             "subtitles=Production/E01/E01_SC04_Animatic.srt:"
             "force_style='Fontname=Noto Sans Devanagari,Fontsize=16,Outline=1,Shadow=0,MarginV=13'")
    movie=OUTPUT/'E01_SC04_Performance_v0_2.mp4'
    run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(silent),
         '-i',str(EPISODE/'Audio/E01_SC04_Performance_Mix.wav'),'-vf',filters,
         '-map','0:v:0','-map','1:a:0','-c:v','libx264','-crf','18','-preset','fast',
         '-c:a','aac','-b:a','160k','-movflags','+faststart','-shortest',str(movie)])
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(movie)],text=True))
    video=next(stream for stream in probe['streams'] if stream['codec_type']=='video')
    audio=next(stream for stream in probe['streams'] if stream['codec_type']=='audio')
    if int(video['nb_frames'])!=timeline['total_frames'] or abs(float(audio['duration'])-timeline['duration_seconds'])>.1:
        raise ValueError('Encoded edit differs from the measured timeline')
    report={'status':'PASS','output_frames':int(video['nb_frames']),
            'rendered_motion_samples':sum(len(shot['rendered_frames']) for shot in render['shots']),
            'motion_sample_fps':24/render['step'],'output_fps':24,'width':video['width'],'height':video['height'],
            'seconds':timeline['duration_seconds'],'dialogue_unchanged':True,
            'voices':'Synthetic scratch readings','rendering':'True keyed 3D frames, sampled on twos; no panel zoom substitution'}
    (EPISODE/'E01_SC04_Performance_Media_Check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    main()
