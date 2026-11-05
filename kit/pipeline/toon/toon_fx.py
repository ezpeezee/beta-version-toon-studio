"""Flat outlined effect sprites, drawn from their age so any frame can be drawn alone (no simulation state). Items come from toon_story.burst().
Item: (kind, x, y, size, age, seed, opts) in card px; also pattern_shadow() for shadows that cross a character. Plain PIL, no Blender."""
import math
import random

import numpy as np
from PIL import Image

from toon_story import FX_LIFE as LIFE

INK = (24, 18, 30, 255)


def _disc(d, ss, x, y, r, fill, ink=INK, w=8):
    if r <= 0:
        return
    d.ellipse([(x - r - w) * ss, (y - r - w) * ss, (x + r + w) * ss, (y + r + w) * ss], fill=ink)
    d.ellipse([(x - r) * ss, (y - r) * ss, (x + r) * ss, (y + r) * ss], fill=fill)


def _poly(d, ss, pts, fill, ink=INK, w=6):
    pp = [(x * ss, y * ss) for x, y in pts]
    if w:
        d.line(pp + pp[:2], fill=ink, width=int(w * 2 * ss), joint='curve')
    d.polygon(pp, fill=fill)


def _cloud(d, ss, puffs, fill, ink, w):
    """A union of circles with one outline round the whole: all ink first, then all fill."""
    for x, y, r in puffs:
        if r > 0:
            d.ellipse([(x - r - w) * ss, (y - r - w) * ss, (x + r + w) * ss, (y + r + w) * ss], fill=ink)
    for x, y, r in puffs:
        if r > 0:
            d.ellipse([(x - r) * ss, (y - r) * ss, (x + r) * ss, (y + r) * ss], fill=fill)


def _smoke(d, ss, x, y, s, age, seed, o):
    r = random.Random(seed)
    life = o.get('life', LIFE['smoke'])
    col = o.get('col', (244, 240, 232, 255))
    ink = o.get('ink', (150, 146, 150, 255))
    u = age / life
    grow = min(1, age / 5) ** .6
    shrink = 1 if u < .7 else max(0, 1 - (u - .7) / .3)
    puffs = []
    for i in range(o.get('n', 7)):
        a = r.uniform(0, 6.28)
        dist = r.uniform(.15, .75) * s * (.5 + grow * .5 + u * .5)
        pr = r.uniform(.32, .55) * s * grow * shrink
        puffs.append((x + dist * math.cos(a), y + dist * math.sin(a) * .7 - u * s * .7, pr))
    _cloud(d, ss, puffs, col, ink, 10)


def _flame(d, ss, x, y, h, w, ph, col):
    sway = math.sin(ph) * w * .25
    pts = [(x - w, y), (x - w * .7, y - h * .35), (x - w * .35 + sway * .5, y - h * .55), (x - w * .25 + sway, y - h * .78), (x + sway * 1.4, y - h),
           (x + w * .3 + sway, y - h * .7), (x + w * .45 + sway * .5, y - h * .5), (x + w * .75, y - h * .3), (x + w, y), (x, y + w * .35)]
    _poly(d, ss, pts, col, INK, 6)


def _fire(d, ss, x, y, s, age, seed, o):
    r = random.Random(seed)
    life = o.get('life', LIFE['fire'])
    grow = min(1, age / 6) * min(1, (life - age) / 8 + .001)
    for i in range(o.get('n', 5)):
        ox, ph, k = r.uniform(-.55, .55) * s, r.uniform(0, 6), r.uniform(.7, 1.15)
        fl = 1 + .18 * math.sin(age * .9 + ph)
        h, w = s * k * grow * fl, s * .34 * grow
        _flame(d, ss, x + ox, y, h, w, age * .5 + ph, (240, 96, 28, 255))
        _flame(d, ss, x + ox, y, h * .68, w * .62, age * .5 + ph + 1, (255, 170, 40, 255))
        _flame(d, ss, x + ox, y, h * .38, w * .34, age * .5 + ph + 2, (255, 236, 130, 255))


def _impact(d, ss, x, y, s, age, seed, o):
    r_ = s * (.35 + age * .16)
    w = max(1, int((o.get('w', 16) - age * 2) * ss))
    col = o.get('col', (255, 244, 180, 255))
    d.ellipse([(x - r_) * ss, (y - r_) * ss, (x + r_) * ss, (y + r_) * ss], outline=col, width=w)
    if age < 3:
        n = 8
        pts = [(x + (s * .28 if i % 2 else s * (1 - age * .15)) * math.cos(i * math.pi / n), y + (s * .28 if i % 2 else s * (1 - age * .15)) * math.sin(i * math.pi / n)) for i in range(2 * n)]
        _poly(d, ss, pts, (255, 248, 200, 255), INK, 5)


def _boom(d, ss, x, y, s, age, seed, o):
    """Flash star, then fire, then a white outlined cloud on top that hangs and fades."""
    if age < 4:
        _impact(d, ss, x, y, s * 1.9, age, seed, dict(w=34))
    if age >= 1:
        for k, (sc, col) in enumerate(((1.0, (226, 60, 36, 255)), (.72, (255, 150, 40, 255)), (.42, (255, 232, 110, 255)))):
            _fire_one(d, ss, x, y + s * .4, s * 1.7 * sc, age - 1, seed + k, col, life=26)
    if age >= 4:
        u = min(1, (age - 4) / 26)
        sm = _ramp(u * 1.3, ((0, (120, 100, 80)), (.5, (84, 70, 62)), (1, (44, 38, 44))))
        _smoke(d, ss, x, y - s * .15, s * 1.3, age - 4, seed + 1, dict(life=28, n=10, col=sm, ink=INK))
    _shatter(d, ss, x, y, s * 1.1, age, seed + 3, dict(life=34, n=24, col=[(90, 70, 60), (200, 90, 40), (60, 50, 56)]))
    _debris(d, ss, x, y, s * 1.2, age, seed + 2, dict(life=30, n=10, col=(90, 70, 60, 255)))


def _ramp(u, stops):
    u = min(1, max(0, u))
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if u <= b:
            t = (u - a) / (b - a)
            return tuple(int(ca[i] + (cb[i] - ca[i]) * t) for i in range(3)) + (255,)
    return tuple(stops[-1][1]) + (255,)


def _fire_one(d, ss, x, y, s, age, seed, col, life=26):
    """One flame layer in a single colour (boom stacks three)."""
    r = random.Random(seed)
    grow = min(1, age / 6) * min(1, max(0, (life - age) / 8))
    for i in range(7):
        ox, ph, k = r.uniform(-.6, .6) * s, r.uniform(0, 6), r.uniform(.7, 1.15)
        fl = 1 + .18 * math.sin(age * .9 + ph)
        _flame(d, ss, x + ox, y, s * k * grow * fl, s * .34 * grow, age * .5 + ph, col)


def _column(d, ss, x, y, s, age, seed, o):
    """Huge rising smoke column: puffs born at the base, rising and growing, coloured by their own age."""
    r = random.Random(seed)
    life = o.get('life', LIFE['column'])
    n = o.get('n', 22)
    H = s * 2.6
    stops = ((0, (255, 214, 70)), (.18, (246, 150, 44)), (.45, (150, 88, 52)), (.75, (74, 56, 52)), (1, (34, 28, 36)))
    items = []
    for i in range(n):
        k = i / (n - 1)
        born = (1 - k) * life * .3
        t = age - born
        if t < 0:
            continue
        e = min(1, t / (life * .45))
        e = 1 - (1 - e) ** 2.2
        lat = math.sin(i * 1.9 + r.uniform(0, 1)) * s * (.12 + .22 * k)
        px = x + lat * (.4 + e) + math.sin(t * .05 + i) * s * .04
        py = y - k * H * e - t * s * .006
        grow = t / (t + 7)
        rr = s * (.2 + .3 * k) * (.35 + .65 * grow) * (1 + t / life * .35)
        rr *= min(1, max(0, (life - age) / 12 + .0))
        col = _ramp(t / (life * .8), stops)
        items.append((px, py, rr, col, t))
    items.sort(key=lambda a: -a[4])
    for px, py, rr, col, t in items:
        if rr > 0:
            wi = min(9, rr * .3)
            d.ellipse([(px - rr - wi) * ss, (py - rr - wi) * ss, (px + rr + wi) * ss, (py + rr + wi) * ss], fill=INK)
    for px, py, rr, col, t in items:
        if rr > 0:
            d.ellipse([(px - rr) * ss, (py - rr) * ss, (px + rr) * ss, (py + rr) * ss], fill=col)


def _shatter(d, ss, x, y, s, age, seed, o):
    """20-40 big shards on arcs with spin and gravity."""
    r = random.Random(seed)
    life = o.get('life', LIFE['shatter'])
    cols = o.get('col', (170, 120, 76))
    cols = [cols] if isinstance(cols[0], (int, float)) else list(cols)
    for i in range(o.get('n', r.randint(20, 40))):
        a, v = r.uniform(-3.2, -.0), r.uniform(.4, 1.0) * s / 13
        w, sp, rot0 = max(22, r.uniform(.05, .13) * s), r.uniform(-.35, .35), r.uniform(0, 6.28)
        c = r.choice(cols)
        sh = r.uniform(.8, 1.15)
        col = tuple(min(255, int(q * sh)) for q in c[:3]) + (255,)
        t = age
        sc = min(1, max(0, (life - age) / 10))
        _shard(d, ss, x + v * math.cos(a) * t, y + v * math.sin(a) * t + .3 * t * t, w * sc, w * .62 * sc, rot0 + sp * t, col)


def _lines(d, ss, x, y, s, age, seed, o):
    """Radial speed lines: tapered wedges from the card edge inward."""
    r = random.Random(seed + age // 2)
    life = o.get('life', LIFE['lines'])
    col = o.get('col', (255, 255, 255, 255))
    R = o.get('R', 1500)
    n = r.randint(18, 28)
    fade = min(1, max(0, (life - age) / 3 + .3))
    for i in range(n):
        a = (i + r.uniform(-.3, .3)) / n * 6.2832
        inner = s * r.uniform(.55, 1.1) + age * s * .03
        hw = r.uniform(.016, .04) * fade
        pts = [(x + R * math.cos(a - hw), y + R * math.sin(a - hw)), (x + R * math.cos(a + hw), y + R * math.sin(a + hw)),
               (x + inner * math.cos(a), y + inner * math.sin(a))]
        _poly(d, ss, pts, col, INK, 0)


def _star4(d, ss, x, y, rr, rot, col):
    pts = []
    for i in range(8):
        q = rr if i % 2 == 0 else rr * .24
        pts.append((x + q * math.cos(rot + i * math.pi / 4), y + q * math.sin(rot + i * math.pi / 4)))
    _poly(d, ss, pts, col, INK, 4)


def _sparkle(d, ss, x, y, s, age, seed, o):
    r = random.Random(seed)
    life = o.get('life', LIFE['sparkle'])
    for i in range(o.get('n', 7)):
        a, dist = r.uniform(0, 6.28), r.uniform(.35, 1.0) * s
        born, lf, sz = r.uniform(0, life * .45), r.uniform(.45, .6) * life, r.uniform(.12, .24) * s
        t = age - born
        if t < 0 or t > lf:
            continue
        u = t / lf
        pop = 1 + .35 * math.sin(min(1, t / 4) * math.pi) if t < 4 else 1
        sc = (min(1, t / 3) ** .7) * (1 - max(0, u - .6) / .4) * pop * (1 + .22 * math.sin(t * 1.3 + i))
        _star4(d, ss, x + dist * math.cos(a), y + dist * math.sin(a) * .8, sz * sc, .2 * math.sin(t * .3 + i), o.get('col', (255, 244, 170, 255)))


def _anger(d, ss, x, y, s, age, seed, o):
    """Manga cross-vein mark: four tapered crescents, popping with overshoot and pulsing."""
    life = o.get('life', LIFE['anger'])
    e = 1 - math.exp(-age * .55) * math.cos(age * .75)
    sc = e * (1 + .07 * math.sin(age * .9)) * min(1, max(0, (life - age) / 3))
    R = s * sc
    if R <= 2:
        return
    col = o.get('col', (232, 52, 48, 255))
    for k in range(4):
        ak = math.radians(45 + 90 * k)
        outer, inner = [], []
        for j in range(13):
            q = (j / 12) * 2 - 1
            th = ak + q * math.radians(38)
            ro = R * (.42 + .58 * q * q)  # pinched toward the centre, tips flung out: the vein shape
            ri = ro - R * .3 * (1 - q * q)
            outer.append((x + ro * math.cos(th), y + ro * math.sin(th)))
            inner.append((x + ri * math.cos(th), y + ri * math.sin(th)))
        _poly(d, ss, outer + inner[::-1], col, INK, 6)


def _motes(d, ss, x, y, s, age, seed, o):
    r = random.Random(seed)
    life = o.get('life', LIFE['motes'])
    col = o.get('col', (255, 244, 205))
    for i in range(o.get('n', 40)):
        a, dist = r.uniform(0, 6.28), math.sqrt(r.random()) * s
        ph, sp, rr = r.uniform(0, 6.28), r.uniform(.4, 1.0), r.uniform(5, 15)
        px = x + dist * math.cos(a) + math.sin(age * .03 * sp + ph) * 30 + age * .15 * sp
        py = y + dist * math.sin(a) * .8 - age * .35 * sp + math.cos(age * .025 * sp + ph) * 22
        fade = min(1, age / 15, (life - age) / 15) * (.65 + .35 * math.sin(age * .12 + ph))
        if fade <= 0:
            continue
        for k, (m, al) in enumerate(((2.2, .16), (1.5, .3), (1, .6))):
            d.ellipse([(px - rr * m) * ss, (py - rr * m) * ss, (px + rr * m) * ss, (py + rr * m) * ss], fill=tuple(col[:3]) + (int(255 * al * fade),))


def _puffring(d, ss, x, y, s, age, seed, o):
    """Ground-hugging dust ring racing sideways, 2-3x the width of dust."""
    r = random.Random(seed)
    life = o.get('life', LIFE['puffring'])
    u = age / life
    ex = 1 - (1 - min(1, u * 1.25)) ** 2.4
    grow = min(1, age / 4) ** .7 * (1 - max(0, u - .45) / .55)
    puffs = []
    for i in range(o.get('n', 16)):
        side = -1 if i % 2 else 1
        dist = r.uniform(.35, 1.0) * s * (.3 + 3.2 * ex)
        puffs.append((x + side * dist, y - r.uniform(0, .12) * s - u * s * .12, r.uniform(.16, .3) * s * grow * (.6 + .5 * (1 - dist / (s * 3.5)))))
    _cloud(d, ss, puffs, o.get('col', (226, 208, 170, 255)), (176, 152, 116, 255), 8)


def _sparks(d, ss, x, y, s, age, seed, o):
    r = random.Random(seed)
    life = o.get('life', LIFE['sparks'])
    for i in range(o.get('n', 26)):
        a, v, born, lf = r.uniform(-3.0, -.14), r.uniform(.35, 1.0) * s / 7, r.uniform(0, life * .3), r.uniform(.5, 1) * life * .7
        t = age - born
        if t < 0 or t > lf:
            continue
        p0 = (x + v * math.cos(a) * t, y + v * math.sin(a) * t + .9 * t * t)
        t2 = t - 1.4
        p1 = (x + v * math.cos(a) * t2, y + v * math.sin(a) * t2 + .9 * t2 * t2)
        wd = int(max(5, 15 * (1 - t / lf)) * ss)
        d.line([(p1[0] * ss, p1[1] * ss), (p0[0] * ss, p0[1] * ss)], fill=(255, 170, 60, 255), width=wd + int(3 * ss))
        d.line([(p1[0] * ss, p1[1] * ss), (p0[0] * ss, p0[1] * ss)], fill=(255, 242, 190, 255), width=wd)


def _dust(d, ss, x, y, s, age, seed, o):
    r = random.Random(seed)
    life = o.get('life', LIFE['dust'])
    u = age / life
    grow = min(1, age / 6) ** .7 * max(0, 1 - max(0, u - .5) / .5)
    puffs = []
    for i in range(o.get('n', 6)):
        side = r.choice((-1, 1))
        puffs.append((x + side * r.uniform(.1, 1.0) * s * (.4 + u), y - r.uniform(0, .25) * s - u * s * .2, r.uniform(.2, .36) * s * grow))
    _cloud(d, ss, puffs, o.get('col', (226, 208, 170, 255)), (176, 152, 116, 255), 7)


def _shard(d, ss, cx, cy, w, h, rot, col, ink=True):
    c, sn = math.cos(rot), math.sin(rot)
    pts = [(cx + a * c - b * sn, cy + a * sn + b * c) for a, b in ((-w, -h), (w, -h * .6), (w * .7, h), (-w * .8, h * .8))]
    _poly(d, ss, pts, col, INK, 4 if ink else 0)


def _debris(d, ss, x, y, s, age, seed, o):
    r = random.Random(seed)
    for i in range(o.get('n', 18)):
        a, v, w, sp = r.uniform(-3.05, -.1), r.uniform(.35, 1.0) * s / 8, r.uniform(8, 26), r.uniform(-.5, .5)
        shade = r.uniform(.8, 1.15)
        col = o.get('col', (170, 120, 76, 255))
        col = tuple(min(255, int(c * shade)) for c in col[:3]) + (255,)
        _shard(d, ss, x + v * math.cos(a) * age, y + v * math.sin(a) * age + .75 * age * age, w, w * .62, r.uniform(0, 6) + sp * age, col)


def _rain(d, ss, x, y, s, age, seed, o, kind):
    r = random.Random(seed)
    life = o.get('life', LIFE[kind])
    for i in range(o.get('n', 26 if kind == 'money' else 46)):
        born, ox, sp, ph, sw = r.uniform(0, life * .6), r.uniform(-1, 1) * s, r.uniform(5, 9), r.uniform(0, 6), r.uniform(10, 34)
        t = age - born
        if t < 0:
            continue
        px, py = x + ox + sw * math.sin(t * .13 + ph), y + sp * t
        turn = abs(math.cos(t * .17 + ph))
        rot = math.sin(t * .09 + ph) * .7
        if kind == 'money':
            w, h = 46, 24 * max(.18, turn)
            _shard(d, ss, px, py, w, h, rot, (92, 170, 96, 255))
            d.ellipse([(px - 7) * ss, (py - 7 * max(.18, turn)) * ss, (px + 7) * ss, (py + 7 * max(.18, turn)) * ss], fill=(214, 240, 200, 255))
        else:
            cols = ((236, 74, 74, 255), (250, 200, 60, 255), (74, 170, 236, 255), (90, 200, 120, 255), (240, 120, 200, 255))
            _shard(d, ss, px, py, 22, 14 * max(.18, turn), rot + t * .2, cols[i % 5], ink=False)


def _steam(d, ss, x, y, s, age, seed, o):
    """Anger puffs either side of the head."""
    pop = min(1, age / 2)
    for k, (dx, ph) in enumerate(((-1, 0), (1, 1.4), (-.45, 2.7))):
        u = (age + k * 6) % 18
        bob = math.sin(age * 1.05 + ph) * 8
        _cloud(d, ss, [(x + dx * s + (i - 1) * s * .24, y - u * 3 + bob - (i % 2) * s * .16, s * .24 * pop) for i in range(3)], (250, 250, 250, 255), INK, 7)


def _sweat(d, ss, x, y, s, age, seed, o):
    pop = min(1, age / 3 + .2)
    w = s * .3 * pop
    yy = y + age * 3.4
    pts = [(x, yy - s * .55 * pop)] + [(x + w * math.cos(a), yy + w * math.sin(a)) for a in np.linspace(-.25, math.pi + .25, 10)]
    _poly(d, ss, pts, (116, 190, 244, 255), INK, 5)


KINDS = dict(smoke=_smoke, fire=_fire, boom=_boom, sparks=_sparks, dust=_dust, debris=_debris, steam=_steam, sweat=_sweat, impact=_impact,
             column=_column, shatter=_shatter, lines=_lines, sparkle=_sparkle, anger=_anger, motes=_motes, puffring=_puffring)


def draw(d, it, ss):
    kind, x, y, s, age, seed, o = it
    if kind in ('money', 'confetti'):
        _rain(d, ss, x, y, s, age, seed, o, kind)
    else:
        KINDS[kind](d, ss, x, y, s, age, seed, o)


def rim_light(card, col, side=1, w=26, strength=.75, shade=None, shade_amt=.28):
    """A coloured light edge on the side the key light comes from (side=1 right, -1 left), inside the card's alpha only.
    shade (rgb) also multiplies a soft horizontal gradient toward that colour on the far side, up to shade_amt."""
    from PIL import ImageFilter
    im = card.convert('RGBA')
    a = np.asarray(im, np.float32).copy()
    al = a[..., 3] / 255
    h, wd = al.shape
    sh = np.zeros_like(al)
    k = int(w)
    if side >= 0:
        sh[:, :wd - k] = al[:, k:]
    else:
        sh[:, k:] = al[:, :wd - k]
    rim = np.clip(al - sh, 0, 1)
    rim = np.asarray(Image.fromarray((rim * 255).astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(max(1, w * .12))), np.float32) / 255
    m = (rim * strength * al)[..., None]
    rgb = a[..., :3]
    if shade is not None:
        cols = np.where(al > .02)[1]
        if cols.size:
            x0, x1 = cols.min(), cols.max()
            t = np.clip((np.arange(wd, dtype=np.float32) - x0) / max(1, x1 - x0), 0, 1)
            t = 1 - t if side >= 0 else t
            g = (t * t * (3 - 2 * t))[None, :, None] * shade_amt
            rgb = rgb * (1 - g) + rgb * (np.array(shade[:3], np.float32) / 255) * g
    rgb = rgb * (1 - m) + np.array(col[:3], np.float32) * m
    a[..., :3] = np.clip(rgb, 0, 255)
    return Image.fromarray(a.astype(np.uint8), 'RGBA')


def pattern_shadow(card, kind, f=0, strength=.42):
    """A shadow pattern from the world falling across a character, multiplied inside the card's own alpha: blinds, chain, leaves, water."""
    im = card.convert('RGBA')
    a = np.asarray(im, np.float32).copy()
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    if kind == 'blinds':
        m = ((yy + xx * .12) % 110) < 46
    elif kind == 'chain':
        m = (np.abs(((xx + yy) % 170) - 85) < 9) | (np.abs(((xx - yy) % 170) - 85) < 9)
    elif kind == 'leaves':
        v = np.sin(xx * .021 + f * .02) + np.sin(yy * .017 - f * .015) + np.sin((xx + yy) * .011 + 1)
        m = v > .7
    elif kind == 'water':
        v = np.sin(xx * .03 + np.sin(yy * .02 + f * .09) * 2.4) * np.sin(yy * .035 - f * .07)
        m = np.abs(v) < .11
        a[..., :3] = np.where(m[..., None], np.clip(a[..., :3] * 1.3 + 18, 0, 255), a[..., :3])
        return Image.fromarray(a.astype(np.uint8), 'RGBA')
    else:
        raise ValueError(kind)
    a[..., :3] = np.where(m[..., None], a[..., :3] * (1 - strength) + np.array((14, 12, 40), np.float32) * strength, a[..., :3])
    return Image.fromarray(a.astype(np.uint8), 'RGBA')
