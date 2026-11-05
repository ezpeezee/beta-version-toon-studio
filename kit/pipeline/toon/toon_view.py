r"""Distant view through the windows, painted in code: soft cloudy sky + three skyline layers fading into haze. Each layer is its own plane, so the view has real parallax.
python toon_view.py <reel>  ->  <reel>\assets\view_sky/far/mid/near.png (used by toon_lib.distant_view)"""
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(sys.argv[1]) / 'assets'
HERE.mkdir(parents=True, exist_ok=True)
HAZE = np.array([206, 222, 240], np.float32)


def fbm(w, h, seed, base=4, oct_=6, sx=1.0):
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(oct_):
        gx, gy = int(base * sx * 2 ** o) + 2, base * 2 ** o + 2
        g = rng.random((gy, gx), dtype=np.float32)
        im = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        out += np.asarray(im, np.float32) / 255 * amp
        tot += amp
        amp *= .52
    return out / tot


def sky():
    w, h = 2048, 1024
    yy = np.linspace(0, 1, h)[:, None]
    top, low = np.array([62, 128, 214], np.float32), np.array([190, 222, 244], np.float32)
    t = np.clip(yy / .78, 0, 1) ** 1.25
    a = (top[None, None] * (1 - t[..., None]) + low[None, None] * t[..., None]) * np.ones((h, w, 1), np.float32)
    # long soft clouds, stretched sideways like the reference skies
    n = fbm(w, h, 7, base=3, sx=.55)
    c = np.clip((n - .5) / .17, 0, 1) ** 1.3
    shade = np.clip((fbm(w, h, 8, base=5, sx=.7) - .4) / .3, 0, 1)
    col = np.array([250, 248, 244], np.float32)[None, None] * (1 - .22 * shade[..., None]) + np.array([150, 158, 205], np.float32)[None, None] * .22 * shade[..., None]
    a = a * (1 - c[..., None] * .92) + col * c[..., None] * .92
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)).save(HERE / 'view_sky.png')


def layer(name, w, h, seed, top, bw, cols, haze, detail, tanks=False):
    """top = (lo, hi) rooftop height as a fraction of image height from the bottom."""
    r = random.Random(seed)
    ss = 2
    im = Image.new('RGBA', (w * ss, h * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = -20
    while x < w:
        bwid = r.uniform(*bw)
        ht = r.uniform(*top) * h
        if r.random() < .12:
            ht *= 1.35
        y0 = h - ht
        c = np.array(r.choice(cols), np.float32) * r.uniform(.9, 1.08)
        d.rectangle([x * ss, y0 * ss, (x + bwid) * ss, h * ss], fill=tuple(int(v) for v in np.clip(c, 0, 255)) + (255,))
        # shaded side of the block
        sd = bwid * r.uniform(.22, .38)
        d.rectangle([(x + bwid - sd) * ss, y0 * ss, (x + bwid) * ss, h * ss], fill=tuple(int(v) for v in np.clip(c * .74, 0, 255)) + (255,))
        if detail:
            gx, gy = detail
            lit = np.clip(c * 1.28 + 14, 0, 255)
            dark = np.clip(c * .62, 0, 255)
            yy = y0 + gy
            while yy < h:
                xx = x + gx * .6
                while xx < x + bwid - gx * .6:
                    tone = lit if r.random() < .3 else dark
                    d.rectangle([xx * ss, yy * ss, (xx + gx * .52) * ss, (yy + gy * .58) * ss], fill=tuple(int(v) for v in tone) + (255,))
                    xx += gx
                yy += gy
        if r.random() < .4:
            # setback or roof box
            bw2 = bwid * r.uniform(.3, .6)
            ht2 = r.uniform(.02, .06) * h
            bx = x + r.uniform(0, bwid - bw2)
            d.rectangle([bx * ss, (y0 - ht2) * ss, (bx + bw2) * ss, y0 * ss], fill=tuple(int(v) for v in np.clip(c * .86, 0, 255)) + (255,))
        if tanks and r.random() < .35:
            tx = x + bwid * .5
            tw, th = h * .018, h * .03
            d.rectangle([(tx - tw) * ss, (y0 - th * 1.9) * ss, (tx + tw) * ss, (y0 - th * .7) * ss], fill=(120, 84, 62, 255))
            d.polygon([((tx - tw * 1.2) * ss, (y0 - th * 1.9) * ss), ((tx + tw * 1.2) * ss, (y0 - th * 1.9) * ss), (tx * ss, (y0 - th * 2.5) * ss)], fill=(92, 66, 54, 255))
            d.rectangle([(tx - tw * .7) * ss, (y0 - th * .7) * ss, (tx - tw * .5) * ss, y0 * ss], fill=(60, 50, 50, 255))
            d.rectangle([(tx + tw * .5) * ss, (y0 - th * .7) * ss, (tx + tw * .7) * ss, y0 * ss], fill=(60, 50, 50, 255))
        x += bwid + r.uniform(-.02, .08) * bwid
    im = im.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(.8))
    a = np.asarray(im, np.float32).copy()
    # haze: stronger low down, and a soft painted mottling across the blocks
    yy = np.linspace(0, 1, h)[:, None]
    k = np.clip(haze + (yy - .35) * .55, 0, .96)
    a[..., :3] = a[..., :3] * (1 - k[..., None]) + HAZE[None, None] * k[..., None]
    a[..., :3] *= (.92 + .16 * fbm(w, h, seed + 40, base=6))[..., None]
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA').save(HERE / f'view_{name}.png')


sky()
layer('far', 3072, 1024, 11, (.45, .86), (50, 130), [(120, 136, 178), (136, 146, 188), (112, 128, 170)], .58, None)
layer('mid', 3072, 1024, 12, (.42, .76), (70, 170), [(176, 128, 142), (150, 124, 160), (188, 150, 132), (130, 122, 164)], .34, (13, 16))
layer('near', 4096, 1024, 13, (.42, .82), (150, 340), [(190, 110, 84), (214, 156, 104), (150, 92, 86), (116, 124, 150), (206, 176, 136)], .10, (24, 34), tanks=True)
print('VIEW_OK')


