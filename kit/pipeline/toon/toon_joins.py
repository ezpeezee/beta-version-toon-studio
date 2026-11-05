"""Shot joins for toon_compose. join(j, p, q, t, W, H): p old frame, q new frame (float32 RGB), t 0..1 across the join, j = dict(kind, ...) from story.JOINS.
Kinds:
 dissolve             plain cross-fade, both shots moving
 whip   dir='x'|'y'   blur slide
 through at=(x,y) shape='circle'|'<png in reel assets or path>' r0=.1 rim=(r,g,b) zoom=.5   an object from the line grows to fill the frame with the next shot inside it
 iris   at=(x,y) at2=(x,y) dark=(r,g,b) rim=(r,g,b)    circle closes on a prop or face, opens on the next one
 puff   at=(x,y) seed=     cartoon smoke fills the frame, then opens around at
 blast  at=(x,y)           fireball fills the frame white-hot, then fades to the next shot
 flash  col=(r,g,b)        bright flash at the cut point, for impacts
 passby col=(r,g,b) img=   something crosses right by the lens, and the next shot is behind it"""
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SPRITES = {}


def _ease_in(t):
    return t * t


def _zoom(a, at, z, W, H):
    """Scale a frame about a point by z >= 1."""
    if abs(z - 1) < 1e-3:
        return a
    cx, cy = at[0] * W, at[1] * H
    w2, h2 = W / z, H / z
    x0, y0 = max(0, min(W - w2, cx - cx / z)), max(0, min(H - h2, cy - cy / z))
    im = Image.fromarray(a.astype(np.uint8)).resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + w2, y0 + h2))
    return np.asarray(im, np.float32)


def _circle_mask(W, H, at, r):
    yy, xx = np.ogrid[0:H, 0:W]
    d = np.sqrt((xx - at[0] * W) ** 2 + (yy - at[1] * H) ** 2)
    return np.clip(r - d + .5, 0, 1)[..., None].astype(np.float32), d


def _shape_mask(j, W, H, at, r):
    """Mask of the object's silhouette at radius r (half its width in px)."""
    shape = j.get('shape', 'circle')
    if shape == 'circle':
        return _circle_mask(W, H, at, r)[0]
    if shape not in SPRITES:
        p = Path(shape)
        if not p.exists():
            p = Path(j['_reel']) / 'assets' / shape
        SPRITES[shape] = Image.open(p).convert('RGBA').getchannel('A')
    al = SPRITES[shape]
    w = max(2, int(r * 2))
    h = max(2, int(w * al.size[1] / al.size[0]))
    m = Image.new('L', (W, H), 0)
    m.paste(al.resize((w, h), Image.BILINEAR), (int(at[0] * W - w / 2), int(at[1] * H - h / 2)))
    return (np.asarray(m, np.float32) / 255)[..., None]


def _rim(mask, col, w):
    """A round-cornered ring of colour just outside the mask edge."""
    m = Image.fromarray((mask[..., 0] * 255).astype(np.uint8))
    small = m.resize((m.size[0] // 4, m.size[1] // 4), Image.BILINEAR)
    blur = np.asarray(small.filter(ImageFilter.GaussianBlur(max(1, w / 6))), np.float32)
    big = Image.fromarray(np.clip(blur * 12, 0, 255).astype(np.uint8)).resize(m.size, Image.BILINEAR)
    return np.clip(np.asarray(big, np.float32) / 255 - mask[..., 0], 0, 1)[..., None]


def through(j, p, q, t, W, H):
    at = j.get('at', (.5, .45))
    r0, end = j.get('r0', .1) * W, 1.25 * math.hypot(W, H)
    r = r0 + (end - r0) * _ease_in(t) ** 1.2
    old = _zoom(p, at, 1 + j.get('zoom', .5) * t, W, H)
    new = _zoom(q, at, 1.18 - .18 * t, W, H)
    m = _shape_mask(j, W, H, at, r)
    out = old * (1 - m) + new * m
    rim = j.get('rim')
    if rim and t < .75:
        wd = max(4, r * .07)
        if j.get('shape', 'circle') == 'circle':
            d = _circle_mask(W, H, at, r)[1]
            rm = np.clip(r + min(30, wd) - d, 0, 1)[..., None].astype(np.float32) - m
            rm = np.clip(rm, 0, 1)
        else:
            rm = _rim(m, rim, min(30, wd))
        out = out * (1 - rm) + np.array(rim, np.float32) * rm
    return out


def iris(j, p, q, t, W, H):
    at, at2 = j.get('at', (.5, .4)), j.get('at2', j.get('at', (.5, .4)))
    dark = np.array(j.get('dark', (11, 7, 20)), np.float32)
    rim = np.array(j.get('rim', (232, 190, 80)), np.float32)
    big, small = .95 * math.hypot(W, H) * .6, .03 * W
    if t < .5:
        u = t * 2
        r, src, c = big + (small - big) * (1 - (1 - u) ** 2), p, at
    else:
        u = (t - .5) * 2
        r, src, c = small + (big - small) * u ** 2, q, at2
    m, d = _circle_mask(W, H, c, r)
    ring = np.clip(1 - np.abs(d - r - W * .008) / (W * .008), 0, 1)[..., None].astype(np.float32)
    out = src * m + dark * (1 - m)
    return out * (1 - ring) + rim * ring


def _puffs(W, H, seed, n=26):
    r = random.Random(seed)
    return [(r.uniform(-.05, 1.05) * W, r.uniform(-.05, 1.05) * H, r.uniform(.2, .34) * W) for _ in range(n)]


def _smoke(W, H, seed, fill, ink):
    """The smoke's inside: overlapping outlined puffs, so a full frame of it reads as smoke, not a white flash."""
    key = ('smoke', W, H, seed, fill, ink)
    if key not in SPRITES:
        r = random.Random(seed + 7)
        im = Image.new('RGB', (W // 2, H // 2), tuple(int(c * .9) for c in fill))
        d = ImageDraw.Draw(im)
        wd = W * .007
        for x, y, r_ in _puffs(W, H, seed + 1, 34):
            r_ *= .7
            tone = r.uniform(.9, 1)
            d.ellipse([(x - r_ - wd) / 2, (y - r_ - wd) / 2, (x + r_ + wd) / 2, (y + r_ + wd) / 2], fill=tuple(ink))
            d.ellipse([(x - r_) / 2, (y - r_) / 2, (x + r_) / 2, (y + r_) / 2], fill=tuple(int(c * tone) for c in fill))
        SPRITES[key] = np.asarray(im.resize((W, H), Image.BILINEAR), np.float32)
    return SPRITES[key]


def puff(j, p, q, t, W, H):
    """1-2 f to fill, about 3 f held, then a scalloped hole opens round at."""
    sw, sh = W // 2, H // 2
    fill, ink = j.get('col', (246, 242, 234)), j.get('ink', (150, 146, 150))
    lay = Image.new('L', (sw, sh), 0)
    edge = Image.new('L', (sw, sh), 0)
    d, e = ImageDraw.Draw(lay), ImageDraw.Draw(edge)
    at = j.get('at', (.5, .45))
    wd = W * .007
    if t < .55:
        g = min(1, t / .2)
        for x, y, r_ in _puffs(W, H, j.get('seed', 3)):
            x, y = at[0] * W + (x - at[0] * W) * g, at[1] * H + (y - at[1] * H) * g
            r_ *= .25 + .75 * g
            for a, v, w_ in ((e, 255, wd), (d, 255, 0)):
                a.ellipse([(x - r_ - w_) / 2, (y - r_ - w_) / 2, (x + r_ + w_) / 2, (y + r_ + w_) / 2], fill=v)
        if t >= .2:
            lay.paste(255, (0, 0, sw, sh))
            edge.paste(255, (0, 0, sw, sh))
        src = p if t < .25 else q
    else:
        u = (t - .55) / .45
        lay.paste(255, (0, 0, sw, sh))
        edge.paste(255, (0, 0, sw, sh))
        R = u ** 1.5 * .95 * math.hypot(W, H)
        r = random.Random(j.get('seed', 3))
        n = 18
        cx, cy = at[0] * W, at[1] * H
        d.ellipse([(cx - R) / 2, (cy - R) / 2, (cx + R) / 2, (cy + R) / 2], fill=0)
        if R > wd:
            e.ellipse([(cx - R + wd) / 2, (cy - R + wd) / 2, (cx + R - wd) / 2, (cy + R - wd) / 2], fill=0)
        for i in range(n):
            a = 6.283 * i / n + r.uniform(-.1, .1)
            sc = R * .36
            x, y = cx + R * .92 * math.cos(a), cy + R * .92 * math.sin(a)
            d.ellipse([(x - sc) / 2, (y - sc) / 2, (x + sc) / 2, (y + sc) / 2], fill=0)
            if sc > wd:
                e.ellipse([(x - sc + wd) / 2, (y - sc + wd) / 2, (x + sc - wd) / 2, (y + sc - wd) / 2], fill=0)
        src = q
    a_f = (np.asarray(lay.resize((W, H), Image.BILINEAR), np.float32) / 255)[..., None]
    a_e = (np.asarray(edge.resize((W, H), Image.BILINEAR), np.float32) / 255)[..., None]
    out = src * (1 - a_e) + np.array(ink, np.float32) * a_e
    return out * (1 - a_f) + _smoke(W, H, j.get('seed', 3), tuple(fill), tuple(ink)) * a_f


def blast(j, p, q, t, W, H):
    at = j.get('at', (.5, .55))
    out = p if t < .45 else q
    big = 1.1 * math.hypot(W, H)
    if t < .45:
        r = big * (t / .45) ** 1.4
        m, d = _circle_mask(W, H, at, r)
        wob = (np.sin(np.arctan2(*np.ogrid[-at[1] * H:(1 - at[1]) * H:complex(0, H), -at[0] * W:(1 - at[0]) * W:complex(0, W)]) * 11) * .06 * r)[..., None].astype(np.float32)
        dd = d[..., None] + wob
        hot = np.clip(r * .82 - dd, 0, 1)
        fire = np.clip(r - dd, 0, 1) - hot
        out = out * (1 - np.clip(hot + fire, 0, 1)) + np.array((255, 130, 40), np.float32) * np.clip(fire, 0, 1) + np.array((255, 250, 235), np.float32) * hot
    else:
        u = (t - .45) / .55
        a = (1 - u) ** 1.6
        tint = np.array((255, 250, 235), np.float32) * (1 - u) + np.array((255, 170, 90), np.float32) * u
        out = out * (1 - a) + tint * a
    return out


def flash(j, p, q, t, W, H):
    col = np.array(j.get('col', (255, 252, 240)), np.float32)
    a = 1 - abs(2 * t - 1) ** 1.5
    src = p if t < .5 else q
    return src * (1 - a) + col * a


def passby(j, p, q, t, W, H):
    """Foreground body crosses from right to left; old shot ahead of it, new shot behind."""
    bw = int(W * j.get('width', 1.0))
    x0 = int(W + (-bw - W) * t * t * (3 - 2 * t))
    out = q.copy()
    if x0 > 0:
        out[:, :min(W, x0)] = p[:, :min(W, x0)]
    a, b = max(0, x0), min(W, x0 + bw)
    if a < b:
        body = Image.open(j['img']).convert('RGB').resize((bw, H)) if j.get('img') else None
        if body is not None:
            out[:, a:b] = np.asarray(body, np.float32)[:, a - x0:b - x0]
        else:
            yy = np.linspace(.75, 1.15, H)[:, None, None].astype(np.float32)
            out[:, a:b] = np.array(j.get('col', (40, 44, 60)), np.float32) * yy
    # the body is too close to focus: blur along the move, strongest mid-pass
    k = int(W * .03 * math.sin(math.pi * t))
    if k < 2:
        return out
    r_ = range(-k, k + 1, max(1, k // 3))
    return sum(np.roll(out, s, 1) for s in r_) / len(r_)


def whip(j, p, q, t, W, H):
    ax = 0 if j.get('dir') == 'y' else 1
    span = H if ax == 0 else W
    s = int(span * .4)
    m = np.roll(p, -int(s * t), ax) * (1 - t) + np.roll(q, int(s * (1 - t)), ax) * t
    k = span * .18 * (1 - abs(2 * t - 1))
    return sum(np.roll(m, int(k * (n / 14 - .5)), ax) for n in range(15)) / 15


def join(j, p, q, t, W, H):
    k = j['kind']
    if k == 'dissolve':
        return p * (1 - t) + q * t
    return dict(whip=whip, through=through, iris=iris, puff=puff, blast=blast, flash=flash, passby=passby)[k](j, p, q, t, W, H)
