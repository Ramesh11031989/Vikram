"""Assemble the staged panels, measured Hindi dialogue and review subtitles."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
EPISODE = ROOT / 'Production/E01'
OUTPUT = EPISODE / 'Animatic'
WIDTH, HEIGHT = 1280, 720


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def review_mix(timeline: dict[str, object]) -> None:
    sample_rate = int(timeline['sample_rate'])
    fps = int(timeline['fps'])
    with wave.open(str(EPISODE/'Audio/E01_SC04_Dialogue_Mix.wav'), 'rb') as stream:
        dialogue = np.frombuffer(stream.readframes(stream.getnframes()), dtype='<i2').astype(np.float64)/32768
    rng = np.random.default_rng(171)
    ambience = np.zeros(len(dialogue))
    for shot in timeline['shots']:
        start = round(shot['start_frame']*sample_rate/fps)
        end = min(len(dialogue), round(shot['end_frame_exclusive']*sample_rate/fps))
        count = end-start
        noise = rng.normal(size=count)
        if shot['set'] == 'river':
            smoothed = np.convolve(noise, np.ones(35)/35, mode='same')
            time = np.arange(count)/sample_rate
            bed = .004*smoothed*(.6+.4*np.sin(time*2.2)**2)
        else:
            bed = .0006*np.convolve(noise, np.ones(55)/55, mode='same')
        fade = min(round(sample_rate*.15), count//2)
        bed[:fade] *= np.linspace(0, 1, fade)
        bed[-fade:] *= np.linspace(1, 0, fade)
        ambience[start:end] += bed
    mixed = np.clip(dialogue+ambience, -.95, .95)
    with wave.open(str(EPISODE/'Audio/E01_SC04_Review_Mix.wav'), 'wb') as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(sample_rate)
        stream.writeframes((mixed*32767).astype('<i2').tobytes())


def contact_sheet(timeline: dict[str, object], font_path: Path) -> None:
    columns, cell_width, cell_height = 3, 440, 294
    rows = math.ceil(len(timeline['shots'])/columns)
    sheet = Image.new('RGB', (columns*cell_width, rows*cell_height+76), '#15191d')
    draw = ImageDraw.Draw(sheet)
    title = ImageFont.truetype(str(font_path), 26)
    label = ImageFont.truetype(str(font_path), 17)
    small = ImageFont.truetype(str(font_path), 13)
    draw.text((18, 10), 'VIKRAM–BETAL / E01 SC04 / ANIMATIC v0.1', font=title, fill='#efe5d3')
    draw.text((18, 46), '11 staged shots • synthetic scratch dialogue • original character geometry', font=small, fill='#a4b2bb')
    for index, shot in enumerate(timeline['shots']):
        x, y = (index % columns)*cell_width, 76+(index//columns)*cell_height
        panel = Image.open(OUTPUT/'Frames'/f"{shot['id']}.png").convert('RGB')
        panel = panel.resize((cell_width-12, 241), Image.Resampling.LANCZOS)
        sheet.paste(panel, (x+6,y))
        duration=(shot['end_frame_exclusive']-shot['start_frame'])/timeline['fps']
        draw.text((x+10,y+246), f"{shot['id'][-4:]}  ·  {duration:.2f}s", font=label, fill='#e6d4ae')
        draw.text((x+10,y+271), shot['title'], font=small, fill='#bcc4ca')
    sheet.save(OUTPUT/'E01_SC04_Storyboard.jpg', quality=92)


def default_font() -> Path:
    candidates = [Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
                  Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts/arial.ttf']
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError('Supply a Latin font path with --font')


def main(font_path: Path | None) -> None:
    font_path = font_path or default_font()
    timeline = json.loads((EPISODE/'E01_SC04_Animatic_Timeline.json').read_text(encoding='utf-8'))
    cache = OUTPUT/'VideoCache'
    cache.mkdir(parents=True, exist_ok=True)
    for shot in timeline['shots']:
        panel = OUTPUT/'Frames'/f"{shot['id']}.png"
        if not panel.is_file():
            raise FileNotFoundError(f'Render the Blender panels first: {panel}')
        frames = shot['end_frame_exclusive']-shot['start_frame']
        clip = cache/f"{shot['id']}.mp4"
        # Only framing moves in this panel edit; full body animation stays in the .blend.
        zoom = f"zoompan=z='1+0.025*on/{max(1,frames-1)}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d={frames}:s={WIDTH}x{HEIGHT}:fps={timeline['fps']}"
        run(['ffmpeg','-hide_banner','-loglevel','error','-y','-loop','1','-i',str(panel),
             '-vf',zoom,'-frames:v',str(frames),'-an','-c:v','libx264',
             '-preset','fast','-crf','20','-pix_fmt','yuv420p',str(clip)])
    concat = cache/'shots.txt'
    concat.write_text(''.join(f"file '{shot['id']}.mp4'\n" for shot in timeline['shots']))
    silent = cache/'E01_SC04_Silent.mp4'
    run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','1',
         '-i',str(concat),'-c','copy',str(silent)])
    review_mix(timeline)
    contact_sheet(timeline, font_path)
    # Use relative paths for the subtitle filter on Windows and Linux.
    filter_font = font_path.as_posix().replace(':', '\\:').replace("'", "\\'")
    subtitle_filter = (
        "drawbox=x=0:y=0:w=iw:h=42:color=black@0.60:t=fill,"
        f"drawtext=fontfile='{filter_font}':text='VIKRAM - BETAL   /   E01 SC04   /   ANIMATIC v0.1   /   SCRATCH VOICES':"
        "fontcolor=white@0.85:fontsize=17:x=22:y=12,"
        "subtitles=Production/E01/E01_SC04_Animatic.srt:"
        "force_style='Fontname=Noto Sans Devanagari,Fontsize=16,Outline=1,Shadow=0,MarginV=14'"
    )
    run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(silent),
         '-i',str(EPISODE/'Audio/E01_SC04_Review_Mix.wav'),'-vf',subtitle_filter,
         '-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','fast','-crf','19',
         '-c:a','aac','-b:a','160k','-movflags','+faststart','-shortest',
         str(OUTPUT/'E01_SC04_Animatic_v0_1.mp4')])
    print(f"Review video: {OUTPUT/'E01_SC04_Animatic_v0_1.mp4'}", flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font', type=Path)
    main(parser.parse_args().font)
