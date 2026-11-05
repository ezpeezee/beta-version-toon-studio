r"""Flat screen textures: grey avatar placeholder (use until the real avatar is approved) and text screens.
python toon_flat.py <reel> placeholder                       -> <reel>\assets\avatar_placeholder.png
python toon_flat.py <reel> screen <name> "BIG" "line 2" ...  -> <reel>\assets\<name>.png (960x600 navy, first line gold, rest white)"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = str(Path(__file__).resolve().parents[2] / 'assets' / 'brand' / 'fonts' / 'Anton-Regular.ttf')
SIZES = (170, 96, 96, 80)
a = sys.argv[1:]
OUT = Path(a[0]) / 'assets'
OUT.mkdir(parents=True, exist_ok=True)
f = lambda s: ImageFont.truetype(FONT, s)


def centre(d, y, t, size, col, W):
    w = d.textlength(t, font=f(size))
    d.text(((W - w) / 2, y), t, font=f(size), fill=col)


if a[1] == 'placeholder':
    im = Image.new('RGB', (960, 600), (120, 124, 130))
    d = ImageDraw.Draw(im)
    d.ellipse((330, 90, 630, 390), fill=(170, 174, 180))
    d.pieslice((200, 370, 760, 900), 180, 360, fill=(170, 174, 180))
    d.rounded_rectangle((250, 470, 710, 570), 16, fill=(20, 24, 32))
    centre(d, 482, 'AVATAR PLACEHOLDER', 60, (255, 255, 255), 960)
    im.save(OUT / 'avatar_placeholder.png')
else:
    im = Image.new('RGB', (960, 600), (16, 21, 34))
    d = ImageDraw.Draw(im)
    y = 90
    for i, t in enumerate(a[3:]):
        centre(d, y, t, SIZES[min(i, 3)], (255, 211, 77) if i == 0 else (255, 255, 255), 960)
        y += SIZES[min(i, 3)] + 40
    im.save(OUT / f'{a[2]}.png')
print('FLAT_OK')
