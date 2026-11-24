"""Render the Devanagari document textures with Pillow + Raqm (no Blender, no numpy).

python3 Blender/tools/document_textures.py     (WSL: Nirmala from /mnt/c/Windows/Fonts)

Text is shaped by Raqm, so conjuncts and matras are correct. Oil stains are only
drawn in the outer margin band, never over words or boxes.
"""

import math
import random
import sys
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import document_text as T

OUT = Path(__file__).resolve().parents[1] / 'Props' / 'Documents' / 'Textures'
W, H = 1200, 1600
MARGIN = 150  # stains stay in this outer band
FONT_FILES = ('/mnt/c/Windows/Fonts/Nirmala.ttc', 'C:/Windows/Fonts/Nirmala.ttc')
# (font index in Nirmala.ttc, ink, tilt degrees, size, wobble): four distinct hands
HANDS = (
    (0, (28, 24, 22), 0.0, 52, 1.2),
    (2, (22, 38, 78), -1.6, 50, 2.4),
    (1, (60, 26, 22), 1.2, 46, 1.8),
    (3, (24, 52, 40), -.6, 54, 3.0),
)
INK_BLACK = (20, 18, 18)
SEAL_RED = (150, 28, 24)
PAPERS = {'plain': (226, 208, 170), 'order': (232, 215, 176), 'ledger': (214, 196, 156)}
LINE = (110, 92, 64)


def font(index, size):
    for path in FONT_FILES:
        if Path(path).exists():
            return ImageFont.truetype(path, size, index=index, layout_engine=ImageFont.LAYOUT_RAQM)
    raise FileNotFoundError('Nirmala.ttc not found')


def paper(kind, seed):
    rng = random.Random(seed)
    base = Image.new('RGB', (W, H), PAPERS[kind])
    img = Image.blend(base, Image.effect_noise((W, H), 14).convert('RGB'), .07)
    fibres = ImageDraw.Draw(img)
    for _ in range(900):
        x, y, a = rng.randrange(W), rng.randrange(H), rng.uniform(0, math.tau)
        n = rng.randint(6, 22)
        c = tuple(v - rng.randint(4, 12) for v in PAPERS[kind])
        fibres.line((x, y, x + n*math.cos(a), y + n*math.sin(a)), fill=c, width=1)
    return img


def oil_stains(img, seed, count=5):
    rng = random.Random(seed)
    layer = Image.new('L', (W, H), 0)
    draw = ImageDraw.Draw(layer)
    bands = ((0, 0, W, MARGIN), (0, H-MARGIN, W, H), (0, 0, MARGIN-40, H), (W-MARGIN+40, 0, W, H))
    for _ in range(count):
        x0, y0, x1, y1 = rng.choice(bands)
        r = rng.randint(30, 62)
        cx = rng.randint(x0+r//2, max(x0+r//2, x1-r//2))
        cy = rng.randint(y0+r//2, max(y0+r//2, y1-r//2))
        draw.ellipse((cx-r, cy-r*.8, cx+r, cy+r*.8), fill=rng.randint(70, 120))
    layer = layer.filter(ImageFilter.GaussianBlur(14)).point(lambda v: min(255, v*2))
    return Image.composite(Image.blend(img, Image.new('RGB', (W, H), (120, 84, 28)), .55), img, layer)


def write(img, x, y, text, hand, rng, centre=False):
    index, ink, tilt, size, wobble = hand
    f = font(index, size)
    text = unicodedata.normalize('NFC', text)
    width = f.getlength(text)
    if centre:
        x -= width/2
    layer = Image.new('L', (int(width)+60, size*2), 0)
    ImageDraw.Draw(layer).text((20, 10), text, font=f, fill=255)
    layer = layer.rotate(tilt + rng.uniform(-wobble, wobble)*.2, resample=Image.BICUBIC, expand=True)
    img.paste(Image.new('RGB', layer.size, ink), (int(x)-20, int(y)-10), layer)
    return width


def seal(img, cx, cy, radius=95):
    """The royal seal: one drawing, used identically on the order and the decree."""
    layer = Image.new('L', (radius*2+20, radius*2+20), 0)
    d = ImageDraw.Draw(layer)
    c = radius + 10
    d.ellipse((c-radius, c-radius, c+radius, c+radius), outline=255, width=9)
    d.ellipse((c-radius+20, c-radius+20, c+radius-20, c+radius-20), outline=255, width=3)
    f = font(1, 50)
    t = unicodedata.normalize('NFC', T.ORDER_SEAL)
    d.text((c-f.getlength(t)/2, c-34), t, font=f, fill=255)
    for k in range(12):
        a = math.tau*k/12
        px, py = c+(radius-10)*math.cos(a), c+(radius-10)*math.sin(a)
        d.ellipse((px-4, py-4, px+4, py+4), fill=255)
    layer = layer.filter(ImageFilter.GaussianBlur(.8)).point(lambda v: int(v*.88))
    img.paste(Image.new('RGB', layer.size, SEAL_RED), (cx-c, cy-c), layer)


def rules(img, ys):
    d = ImageDraw.Draw(img)
    for y in ys:
        d.line((120, y, W-120, y), fill=(150, 130, 96), width=2)


def statement(n):
    page, who, hand_i, header, lines = T.STATEMENTS[n-1]
    img = paper('plain', 100+n)
    index, ink, tilt, size, wobble = HANDS[hand_i]
    hand, rng = HANDS[hand_i], random.Random(n)
    write(img, W/2, 200, header, (index, ink, tilt, size+8, wobble), rng, True)
    rules(img, [300 + 110*k for k in range(10)])
    for k, line in enumerate(lines):
        write(img, 170, 215 + 110*(k+1), line, hand, rng)
    write(img, W-190, H-240, '— ' + who, hand, rng, True)
    return oil_stains(img, 500+n)


def arrival():
    img = paper('plain', 200)
    hand, rng = HANDS[0], random.Random(2)
    head = (1, INK_BLACK, 0, 44, 0)
    write(img, W/2, 110, T.ARRIVAL_TITLE, (1, INK_BLACK, 0, 58, 1), rng, True)
    d = ImageDraw.Draw(img)
    top, row, count = 330, 130, len(T.ARRIVAL)
    for k in range(count+1):
        d.line((150, top+k*row-20, W-150, top+k*row-20), fill=LINE, width=3)
    d.line((300, top-20, 300, top+count*row-20), fill=LINE, width=3)
    write(img, 225, top-90, T.ARRIVAL_HEAD[0], head, rng, True)
    write(img, 700, top-90, T.ARRIVAL_HEAD[1], head, rng, True)
    for k, (num, name) in enumerate(T.ARRIVAL):
        y = top + k*row + 22
        write(img, 225, y, num, hand, rng, True)
        write(img, 340, y, name, hand, rng)
    write(img, W/2, H-190, T.ARRIVAL_FOOT, (3, (60, 50, 40), 0, 36, 0), rng, True)
    return oil_stains(img, 600)


def order(returned):
    img = paper('order', 300)
    old, new, rng = HANDS[0], HANDS[1], random.Random(3)
    write(img, W/2, 190, T.ORDER_TITLE, (1, INK_BLACK, 0, 62, 0), rng, True)
    rules(img, [330 + 105*k for k in range(11)])
    for k, line in enumerate(T.ORDER_BODY):
        write(img, 160, 265 + 105*(k+1), line, old, rng)
    seal(img, 330, 800)
    if returned:  # the return is written below the same order
        write(img, 160, 960, 'वापसी', (1, new[1], 0, 48, 0), rng)
        for k, line in enumerate(T.ORDER_RETURN):
            write(img, 160, 960 + 105*(k+1), line, (new[0], new[1], new[2], 40, new[4]), rng)
    return oil_stains(img, 700 + int(returned))


def tally():
    img = paper('plain', 400)
    hand, rng = HANDS[2], random.Random(4)
    write(img, W/2, 190, T.TALLY_TITLE, (1, INK_BLACK, 0, 56, 0), rng, True)
    d = ImageDraw.Draw(img)
    top, row, count = 330, 140, len(T.TALLY)
    for k in range(count+1):
        d.line((150, top+k*row, W-150, top+k*row), fill=LINE, width=3)
    d.line((760, top, 760, top+count*row), fill=LINE, width=3)
    for k, (place, number) in enumerate(T.TALLY):
        y = top + k*row + 36
        write(img, 190, y, place, hand, rng)
        if number is not None:  # the blank box stays completely empty
            write(img, 955, y, number, hand, rng, True)
    write(img, 190, top+count*row+70, T.TALLY_TOTAL, (1, INK_BLACK, 0, 44, 0), rng)
    return oil_stains(img, 800)


def decree():
    img = paper('order', 500)
    rng = random.Random(5)
    write(img, W/2, 190, T.DECREE_TITLE, (1, INK_BLACK, 0, 70, 0), rng, True)
    rules(img, [330 + 105*k for k in range(11)])
    for k, line in enumerate(T.DECREE_BODY):
        write(img, 160, 265 + 105*(k+1), line, HANDS[0], rng)
    seal(img, 330, 800)  # same seal and spot as the order to Nandu
    return oil_stains(img, 900)


def ledger_cover():
    img = paper('ledger', 600)
    ImageDraw.Draw(img).rectangle((90, 90, W-90, H-90), outline=(90, 40, 30), width=10)
    write(img, W/2, 640, T.LEDGER_TITLE, (1, (90, 40, 30), 0, 96, 0), random.Random(6), True)
    return oil_stains(img, 950, 3)


def ledger_leaf():
    img = paper('ledger', 610)
    rules(img, [210 + 80*k for k in range(17)])
    ImageDraw.Draw(img).line((220, 150, 220, H-150), fill=(150, 60, 50), width=3)
    return img


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = {f'statement_{n}.png': (lambda n=n: statement(n)) for n in range(1, 8)}
    jobs.update({'arrival_list.png': arrival, 'order_original.png': lambda: order(False),
                 'order_returned.png': lambda: order(True), 'death_tally.png': tally,
                 'royal_decree.png': decree, 'ledger_cover.png': ledger_cover,
                 'ledger_leaf.png': ledger_leaf})
    for name, make in jobs.items():
        make().save(OUT / name)
        print('wrote', name, flush=True)


if __name__ == '__main__':
    main()
