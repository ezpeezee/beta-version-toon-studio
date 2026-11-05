r"""Circuit board floor for inside the server: dark green board, copper traces, pads, painted in code. python toon_pcb.py <reel>  ->  <reel>\assets\pcb.png"""
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(sys.argv[1]) / 'assets'
HERE.mkdir(parents=True, exist_ok=True)
S = 2048
r = random.Random(4)
im = Image.new('RGB', (S, S), (22, 92, 66))
d = ImageDraw.Draw(im)
COPPER, DIM = (214, 168, 84), (38, 122, 88)
for n in range(150):
    x, y = r.randrange(S), r.randrange(S)
    col = COPPER if r.random() < .55 else DIM
    w = r.choice((6, 8, 12))
    pts = [(x, y)]
    for k in range(r.randint(2, 5)):
        L = r.randint(60, 340)
        dx, dy = r.choice(((1, 0), (0, 1), (1, 1), (1, -1), (-1, 0), (0, -1)))
        x, y = x + dx * L, y + dy * L
        pts.append((x, y))
    d.line(pts, fill=col, width=w, joint='curve')
    for px, py in (pts[0], pts[-1]):
        d.ellipse([px - w * 1.6, py - w * 1.6, px + w * 1.6, py + w * 1.6], fill=col, outline=(16, 60, 44), width=2)
for n in range(16):
    x, y, w, h = r.randrange(S), r.randrange(S), r.randint(70, 180), r.randint(70, 180)
    d.rectangle([x, y, x + w, y + h], fill=(26, 30, 38))
    for t in range(0, w, 18):
        d.rectangle([x + t, y - 12, x + t + 8, y], fill=COPPER)
        d.rectangle([x + t, y + h, x + t + 8, y + h + 12], fill=COPPER)
a = np.asarray(im.filter(ImageFilter.GaussianBlur(1)), np.float32)
rng = np.random.default_rng(3)
n = np.asarray(Image.fromarray((rng.random((64, 64)) * 255).astype(np.uint8)).resize((S, S), Image.BICUBIC), np.float32) / 255
a *= (.8 + .35 * n)[..., None]
Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(HERE / 'pcb.png')
print('PCB_OK')


