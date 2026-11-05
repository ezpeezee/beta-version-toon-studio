"""Detail layer for toon sets: painted floors/walls/sky (baked with numpy, cached as PNG in <reel>\\assets\\_baked), scattered small props,
moving background life and light shapes. In sets.py: `from toon_detail import *` (includes toon_sets). Movers go to toon_sets.MOVERS (same list).
floor_paint wall_paint sky_paint scatter ambient light_pattern. Blender 5.x python only (numpy, no PIL)."""
import hashlib
import itertools
import math
import random

import numpy as np

from toon_sets import *  # noqa: F401,F403
from toon_sets import MOVERS, _lerp, _mover  # noqa: F401

BAKE = REEL / 'assets' / '_baked'
PPM = 160
VER = 'd5'
_k = itertools.count()


# ----------------------------------------------------------------------------- numpy painting kit
def _c(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32) / 255


def _mx(a, b, t):
    return a + (b - a) * np.asarray(t, np.float32)[..., None]


def _up(g, h, w, cy, cx):
    y, x = np.arange(h, dtype=np.float32) / cy, np.arange(w, dtype=np.float32) / cx
    y0, x0 = y.astype(int), x.astype(int)
    fy, fx = y - y0, x - x0
    fy, fx = (fy * fy * (3 - 2 * fy))[:, None], (fx * fx * (3 - 2 * fx))[None]
    r0, r1 = g[y0], g[y0 + 1]
    return (r0[:, x0] * (1 - fx) + r0[:, x0 + 1] * fx) * (1 - fy) + (r1[:, x0] * (1 - fx) + r1[:, x0 + 1] * fx) * fy


def _fbm(h, w, cell, rn, octs=4):
    cy, cx = cell if isinstance(cell, tuple) else (cell, cell)
    out, amp, tot = 0, 1.0, 0
    for o in range(octs):
        a, b = max(2, cy / 2 ** o), max(2, cx / 2 ** o)
        out = out + amp * _up(rn.random((int(h / a) + 3, int(w / b) + 3)).astype(np.float32), h, w, a, b)
        tot += amp
        amp *= .5
    return (out / tot).astype(np.float32)


def _vor(h, w, cell, rn):
    """d1, d2 (distance to nearest / 2nd nearest point, px) and a random 0..1 per cell."""
    cell = max(3.0, cell)
    gh, gw = int(h / cell) + 4, int(w / cell) + 4
    py = (np.arange(gh)[:, None] - 1 + rn.random((gh, gw))) * cell
    px = (np.arange(gw)[None] - 1 + rn.random((gh, gw))) * cell
    rid = rn.random((gh, gw)).astype(np.float32)
    ys, xs = np.arange(h, dtype=np.float32)[:, None], np.arange(w, dtype=np.float32)[None]
    cy, cx = (ys // cell).astype(int) + 1, (xs // cell).astype(int) + 1
    d1 = np.full((h, w), 1e9, np.float32)
    d2, r = d1.copy(), np.zeros((h, w), np.float32)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            jy, jx = cy + dy, cx + dx
            d = np.hypot(ys - py[jy, jx], xs - px[jy, jx]).astype(np.float32)
            m = d < d1
            d2 = np.where(m, d1, np.minimum(d2, d))
            r = np.where(m, rid[jy, jx], r)
            d1 = np.where(m, d, d1)
    return d1, d2, r


def _dil(m, r=1):
    o, H, W = m.copy(), m.shape[0], m.shape[1]
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dy or dx:
                o[max(dy, 0):H + min(dy, 0), max(dx, 0):W + min(dx, 0)] |= m[max(-dy, 0):H + min(-dy, 0), max(-dx, 0):W + min(-dx, 0)]
    return o


def _cracks(h, w, n, rn, P, wd=1):
    m = np.zeros((h, w), bool)
    for _ in range(int(n)):
        x, y, a = rn.random() * w, rn.random() * h, rn.random() * 6.283
        for _k2 in range(int(rn.integers(14, 40))):
            a += rn.normal(0, .5)
            for t in np.linspace(0, 1, 5):
                xi, yi = int(x + math.cos(a) * .05 * P * t), int(y + math.sin(a) * .05 * P * t)
                if 0 <= xi < w and 0 <= yi < h:
                    m[yi, xi] = True
            x, y = x + math.cos(a) * .05 * P, y + math.sin(a) * .05 * P
            if rn.random() < .06:
                x2, y2, b = x, y, a + rn.normal(0, 1.1)
                for _j in range(int(rn.integers(4, 12))):
                    b += rn.normal(0, .5)
                    x2, y2 = x2 + math.cos(b) * .05 * P, y2 + math.sin(b) * .05 * P
                    if 0 <= int(x2) < w and 0 <= int(y2) < h:
                        m[int(y2), int(x2)] = True
    return _dil(m, wd)


def _stain(img, rn, amt, P, tint=(.2, .12, .06)):
    """Dark blotches and splotches."""
    if amt <= 0:
        return img
    h, w = img.shape[:2]
    b = np.clip((_fbm(h, w, P * 1.6, rn, 4) - (.71 - .2 * amt)) / .05, 0, 1)
    d1, _, r = _vor(h, w, P * .8, rn)
    sp = ((d1 < P * .11 * r) & (r > 1 - .35 * amt)).astype(np.float32)
    m = np.maximum(b, sp * .85)
    return _mx(img, img * .42 + np.array(tint, np.float32) * .3, m * .8)


def _tone(img, rn, P, amt=.16):
    h, w = img.shape[:2]
    f = _fbm(h, w, P * 1.3, rn, 3)
    q = np.floor(f * 5) / 5 * .55 + f * .45
    return img * (1 + (q - .5) * 2 * amt)[..., None]


def _grime(img, rn, P, hm=.7, k=.55):
    """Wall base dirt; rows run bottom (0) to top."""
    h, w = img.shape[:2]
    v = np.arange(h, dtype=np.float32)[:, None] / (hm * P)
    f = np.clip(1 - v + (_fbm(h, w, P * .35, rn, 3) - .5) * .7, 0, 1) ** 1.4
    return _mx(img, img * .38 + np.array([.12, .08, .05], np.float32) * .3, f * k)


def _paste(img, m, col):
    return np.where(m[..., None], col, img)


# ----------------------------------------------------------------------------- floor kinds: (h, w, P, c1, c2, rn, stains) -> HxWx3
def _planks(h, w, P, c1, c2, rn, st):
    pw, pl = max(8, int(.2 * P)), int(1.3 * P)
    ys, xs = np.arange(h)[:, None], np.arange(w)[None]
    row = ys // pw
    xo = xs + rn.integers(0, pl, h // pw + 2)[row]
    s = rn.random(4099).astype(np.float32)[(row * 131 + xo // pl * 17) % 4099]
    s = np.round(s * 3) / 3
    img = _mx(c1, c2, s)
    ln = np.sin(_fbm(h, w, (pw * .8, P * 1.2), rn, 3) * 50 + ys * .3 + s * 20) > .62
    img = np.where(ln[..., None], img * .78, img)
    dy, dx = ys % pw, xo % pl
    seam = (dy < 2) | (dx < 2)
    img = np.where(seam[..., None], c1 * .28, img)
    img = np.where(((dy == 2) & ~seam)[..., None], np.minimum(img * 1.2, 1), img)
    nail = (np.abs(dx - int(.05 * P) - 3) < 2) & ((np.abs(dy - 5) < 2) | (np.abs(dy - (pw - 6)) < 2))
    img = _paste(img, nail, c1 * .22)
    return _stain(_tone(img, rn, P, .1), rn, st, P)


def _gravel(h, w, P, c1, c2, rn, st):
    cs = P * .12
    d1, _, r = _vor(h, w, cs, rn)
    R = cs * (.3 + .3 * r)
    img = _mx(c1 * .35, c1 * .55, _fbm(h, w, P * .5, rn, 3))
    pc = _mx(c1, c2, (r * 7) % 1)
    pc = pc * np.clip(1.15 - d1 / R * .6, 0, 1.2)[..., None]
    pc = np.where((d1 > R * .78)[..., None], pc * .55, pc)
    img = np.where((d1 < R)[..., None], pc, img)
    D1, _, R2 = _vor(h, w, P * .45, rn)
    big = (D1 < P * .13 * R2) & (R2 > .6)
    img = _paste(img, big, _mx(c1, c2, .7) * (1.1 - D1 / (P * .13) * .35)[..., None])
    img = _paste(img, big & (D1 > P * .1 * R2), c1 * .3)
    return _stain(_tone(img, rn, P, .12), rn, st * .6, P)


def _tile(h, w, P, c1, c2, rn, st):
    t = int(.5 * P)
    ys, xs = np.arange(h)[:, None], np.arange(w)[None]
    ty, tx = ys % t, xs % t
    s = rn.random(2053).astype(np.float32)[((ys // t) * 57 + xs // t) % 2053]
    img = _mx(c1, c2, np.round(s * 3) / 3)
    g = max(2, int(.02 * P))
    img = np.where(((tx >= g) & (tx < g + 3) | (ty >= g) & (ty < g + 3))[..., None], np.minimum(img * 1.18, 1), img)
    img = np.where(((tx >= t - 3) | (ty >= t - 3))[..., None], img * .8, img)
    img = _paste(img, (tx < g) | (ty < g), _mx(c1, _c('#2a2a2a'), .8) * .75)
    d1, _, r = _vor(h, w, P * .7, rn)
    img = _paste(img, (d1 < 4 + 5 * r) & (r > .8), c1 * .55)
    img = _paste(img, _cracks(h, w, h * w / P ** 2 / 14 * (.3 + st), rn, P), c1 * .18)
    return _stain(_tone(img, rn, P, .1), rn, st, P)


def _checker(h, w, P, c1, c2, rn, st):
    t = int(.5 * P)
    ys, xs = np.arange(h)[:, None], np.arange(w)[None]
    img = _mx(c1, c2, ((ys // t + xs // t) % 2).astype(np.float32))
    img = img * (1 + (rn.random((h, w)).astype(np.float32) - .5) * .06)[..., None]
    g = (ys % t < 2) | (xs % t < 2)
    img = _paste(img, g, img * .55)
    img = _paste(img, _cracks(h, w, h * w / P ** 2 / 20 * st, rn, P), c1 * .2)
    return _stain(_tone(img, rn, P, .12), rn, st, P)


def _carpet(h, w, P, c1, c2, rn, st):
    s = int(.3 * P)
    ys, xs = np.arange(h, dtype=np.float32)[:, None], np.arange(w, dtype=np.float32)[None]
    dm = np.abs((xs / s) % 1 - .5) + np.abs((ys / s) % 1 - .5)
    img = _mx(c1, c2, (dm < .3) * .85)
    img = _paste(img, (dm > .46) & ((xs // s + ys // s) % 2 == 0), c2 * .8)
    img = img * (1 + (rn.random((h, w)).astype(np.float32) - .5) * .16)[..., None]
    e = np.minimum(np.minimum(xs, w - 1 - xs), np.minimum(ys, h - 1 - ys))
    img = _paste(img, (e > .06 * P) & (e < .1 * P), c2 * .65)
    img = _paste(img, (e > .125 * P) & (e < .135 * P), c1 * 1.2)
    img = _mx(img, img * 1.25, np.clip((_fbm(h, w, P * .8, rn, 3) - .62) * 4, 0, 1) * .5)
    return _stain(_tone(img, rn, P, .1), rn, st, P)


def _asphalt(h, w, P, c1, c2, rn, st):
    img = _mx(c1, c1 * 1.25, _fbm(h, w, P * 1.2, rn, 3))
    d1, _, r = _vor(h, w, 5, rn)
    img = _paste(img, (d1 < 1.3) & (r > .86), np.minimum(c1 * 1.5, 1))
    ys, xs = np.arange(h)[:, None], np.arange(w)[None]
    for y0 in rn.random(2) * h:
        for dy in (0, int(.45 * P)):
            band = (np.abs(ys - (y0 + dy)) < .1 * P)
            img = np.where((band & (_fbm(h, w, (P * .2, P * 2), rn, 2) > .38))[..., None], img * .6, img)
    for _p in range(3):
        y0, x0 = int(rn.random() * h * .8), int(rn.random() * w * .8)
        ph, pw = int(P * (.4 + rn.random() * .6)), int(P * (.8 + rn.random() * 1.2))
        img[y0:y0 + ph, x0:x0 + pw] *= .8 + rn.random() * .35
    img = _paste(img, _cracks(h, w, h * w / P ** 2 / 5 * (.4 + st), rn, P), c1 * .25)
    return _stain(_tone(img, rn, P, .12), rn, st, P, (.08, .08, .14))


def _sand(h, w, P, c1, c2, rn, st):
    f = _fbm(h, w, P * .9, rn, 3)
    img = _mx(c1, c2, f)
    ys = np.arange(h)[:, None]
    rp = np.sin((ys + _fbm(h, w, (P * .5, P * .9), rn, 3) * P * .5) * .22)
    img = np.where((rp > .5)[..., None], img * .85, np.where((rp < -.6)[..., None], np.minimum(img * 1.1, 1), img))
    d1, _, r = _vor(h, w, P * .12, rn)
    img = _paste(img, (d1 < 1.4) & (r > .7), c1 * .55)
    d1, _, r = _vor(h, w, P * .6, rn)
    img = _paste(img, (d1 < P * .05 * r) & (r > .75), c1 * .5)
    return _stain(img, rn, st * .5, P)


def _grass(h, w, P, c1, c2, rn, st):
    img = _mx(c1, c2, np.floor(_fbm(h, w, P * .9, rn, 3) * 4) / 4 * .7)
    ys = np.arange(h)[:, None]
    img = img * np.where(((ys // int(.7 * P)) % 2 == 0), 1.08, .94)[..., None]
    n = int(h * w / 45)
    by, bx_ = rn.integers(0, h - 8, n), rn.integers(0, w - 6, n)
    lt, dk = np.minimum(c2 * 1.25, 1), c1 * .6
    pick = rn.random(n) > .45
    sl = rn.integers(-1, 2, n)
    for k in range(7):
        yy, xx = by + k, np.clip(bx_ + (sl * k) // 3, 0, w - 1)
        img[yy[pick], xx[pick]] = lt
        img[yy[~pick], xx[~pick]] = dk
    n2 = int(h * w / P ** 2 * 1.5)
    fy, fx = rn.integers(2, h - 2, n2), rn.integers(2, w - 2, n2)
    fc = np.array([[1, 1, .9], [1, .85, .2], [.95, .5, .6]], np.float32)[rn.integers(0, 3, n2)]
    for dy in (0, 1):
        for dx in (0, 1):
            img[fy + dy, fx + dx] = fc
    m = np.clip((_fbm(h, w, P * 1.2, rn, 3) - (.79 - .2 * st)) / .04, 0, 1)
    return _mx(img, _mx(c1 * .6, _c('#7a5a34'), .6) * (1 + (rn.random((h, w)).astype(np.float32) - .5) * .2)[..., None], m * .85)


def _concrete(h, w, P, c1, c2, rn, st):
    img = _mx(c1, c2, np.floor(_fbm(h, w, P * .7, rn, 4) * 5) / 5)
    img = img * (1 + (rn.random((h, w)).astype(np.float32) - .5) * .08)[..., None]
    t = int(2 * P)
    ys, xs = np.arange(h)[:, None], np.arange(w)[None]
    j = (ys % t < 3) | (xs % t < 3)
    img = _paste(img, j, c1 * .35)
    img = _paste(img, ((ys % t >= 3) & (ys % t < 5)) | ((xs % t >= 3) & (xs % t < 5)), np.minimum(c1 * 1.12, 1))
    d1, _, r = _vor(h, w, P * .12, rn)
    img = _paste(img, (d1 < 1.8) & (r > .85), c1 * .5)
    img = _paste(img, _cracks(h, w, h * w / P ** 2 / 6 * (.4 + st), rn, P, 1), c1 * .22)
    return _stain(img, rn, st, P, (.05, .05, .07))


def _dirt(h, w, P, c1, c2, rn, st):
    img = _mx(c1, c2, np.floor(_fbm(h, w, P * 1.1, rn, 4) * 5) / 5)
    img = img * (1 + (rn.random((h, w)).astype(np.float32) - .5) * .12)[..., None]
    d1, _, r = _vor(h, w, P * .2, rn)
    img = _paste(img, (d1 < P * .035 * r) & (r > .55), np.minimum(c2 * 1.2, 1))
    img = _paste(img, (d1 < P * .045 * r) & (d1 > P * .035 * r) & (r > .55), c1 * .45)
    ys, xs = np.arange(h, dtype=np.float32)[:, None], np.arange(w, dtype=np.float32)[None]
    for y0 in rn.random(2) * h:
        wob = np.sin(xs * .02 + y0) * .1 * P + (_fbm(h, w, P, rn, 2) - .5) * .1 * P
        for dy in (0, .5 * P):
            d = np.abs(ys - (y0 + dy) - wob)
            img = np.where((d < .09 * P)[..., None], img * .65, img)
            img = np.where(((d >= .09 * P) & (d < .12 * P))[..., None], np.minimum(img * 1.12, 1), img)
    d1, d2, r = _vor(h, w, P * .35, rn)
    dry = _fbm(h, w, P * 2, rn, 2) > .5
    img = _paste(img, ((d2 - d1) < 1.8) & dry, c1 * .35)
    return _stain(img, rn, st, P)


FLOORS = dict(planks=_planks, gravel=_gravel, tile=_tile, checker=_checker, carpet=_carpet, asphalt=_asphalt, sand=_sand, grass=_grass, concrete=_concrete, dirt=_dirt)
DEF2 = dict(planks=.75, gravel=1.6, tile=1.4, checker=.35, carpet=1.3, asphalt=1.5, sand=1.2, grass=1.35, concrete=1.15, dirt=1.4)


# ----------------------------------------------------------------------------- wall kinds (rows run bottom to top)
def _brick_px(h, w, P, c1, c2, rn, bw=.3, bh=.1):
    bw, bh = int(bw * P), max(6, int(bh * P))
    ys, xs = np.arange(h)[:, None], np.arange(w)[None]
    row = ys // bh
    xo = xs + (row % 2) * (bw // 2)
    s = rn.random(2999).astype(np.float32)[(row * 71 + xo // bw * 13) % 2999]
    img = _mx(c1, c2, np.round(s * 4) / 4)
    dy, dx = ys % bh, xo % bw
    img = np.where((dy == bh - 2)[..., None] | (dy == bh - 3)[..., None], img * .78, img)
    img = np.where((dy == 2)[..., None] & (dx > 2)[..., None], np.minimum(img * 1.15, 1), img)
    mortar = (dy < 2) | (dx < 2)
    img = _paste(img, mortar, _mx(c1, _c('#d8cdb8'), .75) * (.9 + .1 * rn.random((h, w)).astype(np.float32))[..., None])
    d1, _, r = _vor(h, w, bw * .5, rn)
    img = _paste(img, (r > .8) & ~mortar & (d1 < 5), img * .65)
    return img


def _brick(h, w, P, c1, c2, rn, st):
    img = _brick_px(h, w, P, c1, c2, rn)
    f = np.clip((_fbm(h, w, P * .9, rn, 3) - .62) * 5, 0, 1) * .5
    img = _mx(img, np.minimum(img * 1.3 + .1, 1), f)
    ys = np.arange(h, dtype=np.float32)[:, None]
    soot = np.clip((_fbm(h, w, (P * 2, P * .06), rn, 2) - .5) * 5, 0, 1) * np.clip((ys - h * .35) / (h * .65), 0, 1)
    img = _mx(img, img * .5, soot * .6)
    img = _paste(img, _cracks(h, w, h * w / P ** 2 / 5 * st, rn, P), c1 * .2)
    return _grime(_stain(img, rn, st * .5, P), rn, P)


def _plaster(h, w, P, c1, c2, rn, st):
    img = _mx(c1, c2, np.floor(_fbm(h, w, P * 1.2, rn, 4) * 4) / 4 * .8 + _fbm(h, w, P * .25, rn, 2) * .2)
    pm = _fbm(h, w, P * .9, rn, 3)
    patch = pm > (.74 - .2 * st)
    br = _brick_px(h, w, P, _c('#a65a3e'), _c('#8e4a34'), rn)
    img = _paste(img, patch, br)
    img = _paste(img, _dil(patch, 2) & ~patch, img * .7)
    ys = np.arange(h, dtype=np.float32)[:, None]
    dr = np.clip((_fbm(h, w, (P * 1.6, P * .07), rn, 2) - .5) * 5, 0, 1) * np.clip((ys - h * .3) / (h * .7), 0, 1)
    img = _mx(img, img * .62 + np.array([.1, .08, .02], np.float32) * .25, dr * st * 1.4)
    img = _paste(img, _cracks(h, w, h * w / P ** 2 / 4 * (.3 + st), rn, P), c1 * .25)
    return _grime(img, rn, P)


def _wood(h, w, P, c1, c2, rn, st):
    bw = max(10, int(.22 * P))
    ys, xs = np.arange(h)[:, None], np.arange(w)[None]
    col = xs // bw
    s = np.round(rn.random(257).astype(np.float32)[col % 257] * 3) / 3
    img = _mx(c1, c2, s)
    ln = np.sin(_fbm(h, w, (P * 1.6, bw * .5), rn, 3) * 55 + xs * .5) > .55
    img = np.where(ln[..., None], img * .78, img)
    sm = (xs % bw < 2)
    img = _paste(img, sm, c1 * .25)
    img = np.where(((xs % bw == 2))[..., None], np.minimum(img * 1.2, 1), img)
    for ny in (int(.2 * P), int(h / 2), h - int(.2 * P)):
        for dx in (6, bw - 7):
            img = _paste(img, (np.abs(ys - ny) < 2) & (np.abs(xs % bw - dx) < 2), c1 * .2)
    d1, _, r = _vor(h, w, P * .9, rn)
    kn = (np.abs(xs % bw - bw // 2) < bw * .3) & (d1 < 6 + 5 * r) & (r > .82)
    img = _paste(img, kn & (d1 < 4), c1 * .3)
    img = _paste(img, kn & (d1 >= 4), c1 * .55)
    gr = np.clip((_fbm(h, w, (P * 2, P * .08), rn, 2) - .5) * 4, 0, 1)
    img = _mx(img, img.mean(2, keepdims=True) * .7 + .06, gr * st)
    return _grime(img, rn, P)


def _metal(h, w, P, c1, c2, rn, st):
    xs, ys = np.arange(w, dtype=np.float32)[None], np.arange(h, dtype=np.float32)[:, None]
    per = .11 * P
    s = np.sin(xs / per * 6.283)
    img = c1 * (.8 + .22 * s)[..., None] * np.ones((h, 1, 1), np.float32)
    img = np.minimum(img, 1)
    img = np.where((s > .9)[..., None], np.minimum(img * 1.25, 1), img)
    ph = int(1.0 * P)
    seam = (ys % ph < 3)
    img = _paste(img, seam, c1 * .35)
    for dx in np.arange(per / 2, w, per * 3):
        img = _paste(img, (np.abs(xs - dx) < 2.5) & (((ys % ph) > 5) & ((ys % ph) < 10) | ((ys % ph) > ph - 10) & ((ys % ph) < ph - 5)), c1 * 1.3)
    rust = np.clip((_fbm(h, w, (P * 1.3, P * .1), rn, 3) - (.68 - .2 * st)) * 6, 0, 1) * np.clip(1 - ys / h * .5, 0, 1)
    img = _mx(img, _mx(c2, c2 * .6, _fbm(h, w, P * .2, rn, 2)), rust)
    d1, _, r = _vor(h, w, P * .5, rn)
    img = _paste(img, (d1 < 2.5) & (r > .9), c1 * .4)
    img = img * (1 + (rn.random((h, w)).astype(np.float32) - .5) * .07)[..., None]
    return _grime(img, rn, P, .5)


def _wallpaper(h, w, P, c1, c2, rn, st):
    xs, ys = np.arange(w)[None], np.arange(h)[:, None]
    sw = int(.14 * P)
    img = _mx(c1, c2, ((xs // sw) % 2).astype(np.float32))
    ps = int(.28 * P)
    row = ys // ps
    cx, cy = ((xs + (row % 2) * ps // 2) % ps) - ps // 2, (ys % ps) - ps // 2
    rr = np.hypot(cx, cy)
    img = _paste(img, rr < ps * .17, _mx(c2, _c('#ffffff'), .35))
    img = _paste(img, rr < ps * .07, _mx(c1, c2, .2) * .85)
    for a in (0, 1.57, 3.14, 4.71):
        d = np.hypot(cx - math.cos(a) * ps * .27, cy - math.sin(a) * ps * .27)
        img = _paste(img, d < ps * .06, _mx(c2, _c('#ffffff'), .2))
    dado = int(.95 * P)
    img = _paste(img, (np.abs(ys - dado) < 4), _c('#f2ead8'))
    img = _paste(img, (np.abs(ys - dado + 5) < 2), c1 * .55)
    low = ys < dado
    img = np.where(low[..., None], img * .9, img)
    ed = _fbm(h, w, P * .7, rn, 3)
    peel = (ed < .26 * st + .1) & (ys < h * .35) & (ys < dado)
    img = _paste(img, _dil(peel, 2) & ~peel, img * .55)
    img = _paste(img, peel, _mx(_c('#d9cdb2'), _c('#b9a98a'), _fbm(h, w, P * .2, rn, 2)))
    dr = np.clip((_fbm(h, w, (P * 1.4, P * .07), rn, 2) - .5) * 5, 0, 1) * np.clip((ys - h * .4) / (h * .6), 0, 1)
    img = _mx(img, img * .6, dr * st * 1.4)
    return _grime(img, rn, P, .5)


def _wtile(h, w, P, c1, c2, rn, st):
    t = max(10, int(.15 * P))
    ys, xs = np.arange(h)[:, None], np.arange(w)[None]
    ty, tx = ys % t, xs % t
    s = rn.random(1999).astype(np.float32)[((ys // t) * 37 + xs // t) % 1999]
    img = _mx(c1, np.minimum(c1 * 1.12, 1), np.round(s * 3) / 3)
    band = (ys // t) == int(1.2 * P / t)
    img = np.where(band[..., None], c2, img)
    img = _paste(img, (ty > t - 6) & (ty < t - 3) & (tx > 2) & (tx < t // 2), np.minimum(img * 1.3 + .1, 1))
    img = _paste(img, (tx < 2) | (ty < 2), _mx(c1, _c('#d8d4c8'), .75) * .78)
    d1, _, r = _vor(h, w, P * .6, rn)
    img = _paste(img, (r > .9) & (d1 < 5), c1 * .3)
    img = _paste(img, _cracks(h, w, h * w / P ** 2 / 8 * st, rn, P), c1 * .25)
    ys1 = np.arange(h, dtype=np.float32)[:, None]
    top = np.clip((_fbm(h, w, (P * 1.2, P * .08), rn, 2) - .52) * 5, 0, 1)
    img = _mx(img, img * .55, top * np.clip(ys1 / h, 0, 1) * st * 1.3)
    return _grime(img, rn, P, .6)


WALLS = dict(brick=_brick, plaster=_plaster, wood=_wood, metal=_metal, wallpaper=_wallpaper, tile=_wtile)
WDEF = dict(brick=('#b5593d', '#9c4630'), plaster=('#e6dcc3', '#cdbd9a'), wood=('#8a5a32', '#a06e3f'), metal=('#7f93a3', '#a8582c'), wallpaper=('#c9a14a', '#a98235'), tile=('#cfe3e0', '#2c8f8b'))


# ----------------------------------------------------------------------------- baking, planes, materials
def _bake(key, make):
    p = BAKE / f'{key}.png'
    if not p.exists():
        a = np.clip(make(), 0, 1).astype(np.float32)
        h, w = a.shape[:2]
        if a.shape[2] == 3:
            a = np.concatenate([a, np.ones((h, w, 1), np.float32)], 2)
        im = bpy.data.images.new('dt_bake', w, h, alpha=True)
        im.pixels.foreach_set(np.ascontiguousarray(a).ravel())
        BAKE.mkdir(parents=True, exist_ok=True)
        im.filepath_raw, im.file_format = str(p), 'PNG'
        im.save()
        bpy.data.images.remove(im)
    im = bpy.data.images.load(str(p), check_existing=True)
    im.alpha_mode = 'STRAIGHT'
    return im


def _key(*a):
    return hashlib.md5(repr((VER,) + a).encode()).hexdigest()[:14]


def _dims(wm, hm, ppm=PPM):
    s = min(1.0, 2048 / (max(wm, hm) * ppm))
    return max(16, int(round(hm * ppm * s))), max(16, int(round(wm * ppm * s))), ppm * s


def _lit_mat(name, im, rough=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    pr = nt.nodes['Principled BSDF']
    ti = nt.nodes.new('ShaderNodeTexImage')
    ti.image, ti.extension = im, 'EXTEND'
    nt.links.new(ti.outputs['Color'], pr.inputs['Base Color'])
    pr.inputs['Roughness'].default_value = rough
    pr.inputs['Specular IOR Level'].default_value = .1
    return m


def _emit_mat(name, im, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    ti = nt.nodes.new('ShaderNodeTexImage')
    ti.image, ti.extension = im, 'EXTEND'
    em = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(ti.outputs['Color'], em.inputs['Color'])
    fa = nt.nodes.new('ShaderNodeMath')
    fa.operation = 'MULTIPLY'
    nt.links.new(ti.outputs['Alpha'], fa.inputs[0])
    fa.inputs[1].default_value = alpha
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(fa.outputs[0], mx.inputs[0])
    nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], nt.nodes.new('ShaderNodeOutputMaterial').inputs['Surface'])
    m.surface_render_method = 'BLENDED'
    return m


def _plane(name, w, h, loc, m, vertical=False, rz=0.0, shadow=False):
    me = bpy.data.meshes.new(name)
    v = [(-w / 2, 0, -h / 2), (w / 2, 0, -h / 2), (w / 2, 0, h / 2), (-w / 2, 0, h / 2)] if vertical else [(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)]
    me.from_pydata(v, [], [(0, 1, 2, 3)])
    me.uv_layers.new().data.foreach_set('uv', [0, 0, 1, 0, 1, 1, 0, 1])
    me.update()
    o = bpy.data.objects.new(name, me)
    sc.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (0, 0, math.radians(rz))
    o.visible_shadow = shadow
    me.materials.append(m)
    return o


def _kind(kinds, kind):
    if kind not in kinds:
        raise ValueError(f'unknown kind {kind!r}; use one of {sorted(kinds)}')


def floor_paint(name, x0, x1, y0, y1, kind, hex, hex2=None, z=.004, seed=1, stains=.5):
    """Textured plane on an existing floor (world x0..x1, y0..y1, height z). kinds: planks gravel tile checker carpet asphalt sand grass concrete dirt.
    hex = main colour, hex2 = second colour (default a kind-typical shift of hex). stains 0..1 = dirt/cracks/marks. ~160 px/m, max 2048 px."""
    _kind(FLOORS, kind)
    h, w, P = _dims(x1 - x0, y1 - y0)
    c1 = _c(hex)
    c2 = _c(hex2) if hex2 else np.clip(c1 * DEF2[kind], 0, 1)
    im = _bake(_key('f', kind, h, w, hex, hex2, seed, round(stains, 2)), lambda: FLOORS[kind](h, w, P, c1, c2, np.random.default_rng(seed), stains))
    return _plane(name, x1 - x0, y1 - y0, ((x0 + x1) / 2, (y0 + y1) / 2, z), _lit_mat(name + '_m', im))


def wall_paint(name, loc, w, h, kind, hex=None, hex2=None, rz=0, seed=1):
    """Textured wall plane facing -Y centred at loc (rz = degrees around z). kinds: brick plaster wood metal wallpaper tile; weathering and base grime baked in.
    Put it .01 m in front of the wall it covers. hex/hex2 default to a kind-typical pair."""
    _kind(WALLS, kind)
    d1, d2 = WDEF[kind]
    hex, hex2 = hex or d1, hex2 or (d2 if not hex else None)
    ph, pw, P = _dims(w, h)
    c1 = _c(hex)
    c2 = _c(hex2) if hex2 else np.clip(c1 * (1.18 if kind in ('brick', 'plaster', 'wood') else .8), 0, 1)
    im = _bake(_key('w', kind, ph, pw, hex, hex2, seed), lambda: WALLS[kind](ph, pw, P, c1, c2, np.random.default_rng(seed), .5))
    return _plane(name, w, h, loc, _lit_mat(name + '_m', im), vertical=True, rz=rz)


# ----------------------------------------------------------------------------- sky
_CL = [(0, 0, 1.0), (-1.15, -.22, .72), (1.2, -.18, .8), (.45, .42, .78), (-.5, .38, .62), (2.0, -.4, .5), (-1.9, -.45, .46)]


def _sky_img(top, horizon, cloud_hex, seed, W=4096, H=2048):
    rn = np.random.default_rng(seed)
    lat = ((np.arange(H, dtype=np.float32) + .5) / H - .5) * 180
    f = np.clip(np.clip(np.sin(np.radians(lat)) * 1.15 + .02, 0, 1) ** .85, 0, 1)
    f = f * .6 + .4 * np.floor(f * 18) / 18
    hz, tp = _c(horizon), _c(top)
    md = _c(_lerp(horizon, top, .5))
    stops = [0, .42, 1]
    row = np.stack([np.interp(f, stops, [hz[i], md[i], tp[i]]) for i in range(3)], 1).astype(np.float32)
    img = np.repeat(row[:, None, :], W, 1)
    ppd = W / 360.0
    cl, line = _c(cloud_hex), _mx(_c(cloud_hex), tp, .5) * .92
    cs = []
    for i in range(62):
        cs.append((rn.random() * W, rn.uniform(8, 58) ** 1 if rn.random() < .5 else rn.uniform(5, 28), rn.uniform(1.4, 3.3)))
    for i in range(30):
        cs.append((W * (.5 + rn.uniform(-.25, .25)), rn.uniform(6, 40), rn.uniform(1.6, 3.4)))
    for u0, la, sc_ in cs:
        v0 = (la / 180 + .5) * H
        cosl = max(.3, math.cos(math.radians(la)))
        hw, hh = int(3.2 * sc_ * ppd / cosl), int(2.6 * sc_ * ppd)
        xi = np.arange(int(u0) - hw, int(u0) + hw)
        y0, y1 = max(0, int(v0) - hh), min(H, int(v0) + hh)
        gx, gy = (xi[None] - u0) / ppd * cosl, (np.arange(y0, y1)[:, None] - v0) / ppd
        m = np.zeros((y1 - y0, len(xi)), bool)
        for dx, dz, rr in _CL:
            m |= (gx - dx * sc_) ** 2 + (gy - dz * sc_) ** 2 < (rr * sc_) ** 2
        m &= gy >= -.42 * sc_
        t = np.clip((gy + .42 * sc_) / (1.6 * sc_), 0, 1)
        col = _mx(cl * np.array([.8, .86, .97], np.float32), cl, t ** .6)
        ring = _dil(m, 3) & ~m
        reg = img[y0:y1][:, xi % W]
        reg = np.where(ring[..., None], line, reg)
        reg = np.where(m[..., None], col, reg)
        img[y0:y1, xi % W] = reg
    return img


def sky_paint(name, ox=0.0, top='#3d79c4', horizon='#ffc48e', cloud_hex='#ffffff', seed=1, r=R_SKY):
    """Painted sky dome (same radius as `sky`): banded gradient with outlined cartoon clouds baked in (4096x2048, cached). Use instead of `sky` when the sky reads flat."""
    im = _bake(_key('s', top, horizon, cloud_hex, seed), lambda: _sky_img(top, horizon, cloud_hex, seed))
    m = bpy.data.materials.new(name + '_m')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    ti = nt.nodes.new('ShaderNodeTexImage')
    ti.image = im
    em = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(ti.outputs['Color'], em.inputs['Color'])
    nt.links.new(em.outputs[0], nt.nodes.new('ShaderNodeOutputMaterial').inputs['Surface'])
    g = group(name, None, (ox, 0, 0))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=96, ring_count=48, location=(0, 0, 0))
    o = bpy.context.object
    o.name = name + '_dome'
    o.scale = (r, r, r)
    o.rotation_euler = (0, 0, math.radians(SKY_ROT))
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    o.parent = g
    o.visible_shadow = False
    return g


SKY_ROT = 0.0


# ----------------------------------------------------------------------------- scatter
_WOOD, _PAINT = ('#b9803f', '#a56f33', '#c99650', '#8f5f2c'), ('#d9552e', '#2f7fb3', '#e0b23a', '#3f9a5b', '#7b4fa3', '#c8cdd4')


def _m(hx, rough=.8):
    return mat('dt_' + hx[1:], hx, rough)


def _sph(g, nm, r, loc, sc3, m):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=16, ring_count=10, location=loc)
    o = bpy.context.object
    o.name, o.scale, o.parent = nm, sc3, g
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    return o


def _prop(g, nm, kind, rn, s):
    if kind == 'crate':
        w, d, h = .5 * s, .5 * s, .42 * s
        wd = rn.choice(_WOOD)
        bx(nm + 'b', (w, d, h), (0, 0, h / 2), _m(wd), g, .01)
        for k, zz in enumerate((.2, .8)):
            bx(f'{nm}s{k}', (w * 1.02, d * 1.02, h * .14), (0, 0, h * zz), _m(_lerp(wd, '#000000', .35)), g)
        br = bx(nm + 'x', (w * 1.0, .02, .05 * s), (0, -d / 2 - .005, h / 2), _m(_lerp(wd, '#000000', .45)), g)
        br.rotation_euler = (0, math.atan2(h, w), 0)
    elif kind == 'bin':
        c = rn.choice(('#3a6f5a', '#35557a', '#6b6f78', '#7a3b3b'))
        r_, h = .22 * s, .6 * s
        cyl(nm + 'b', r_, h, (0, 0, h / 2), _m(c), g, seg=20)
        cyl(nm + 'l', r_ * 1.1, .05 * s, (0, 0, h + .02), _m(_lerp(c, '#000000', .35)), g, seg=20)
        bx(nm + 'h', (.14 * s, .03, .03), (0, -r_ * 1.0, h + .06), _m('#222222'), g)
    elif kind == 'cone':
        bx(nm + 'p', (.34 * s, .34 * s, .03), (0, 0, .015), _m('#3a3f4a'), g)
        bpy.ops.mesh.primitive_cone_add(radius1=.15 * s, radius2=.02 * s, depth=.5 * s, vertices=16, location=(0, 0, .03 + .25 * s))
        o = bpy.context.object
        o.name, o.parent = nm + 'c', g
        o.data.materials.append(_m('#ee6a1c'))
        cyl(nm + 'w', .107 * s, .07 * s, (0, 0, .03 + .27 * s), _m('#f4f4f0'), g, seg=16)
    elif kind == 'barrel':
        c = rn.choice(_PAINT)
        r_, h = .26 * s, .72 * s
        cyl(nm + 'b', r_, h, (0, 0, h / 2), _m(c, .6), g, seg=20)
        for k, zz in enumerate((.18, .82)):
            cyl(f'{nm}r{k}', r_ * 1.04, .045 * s, (0, 0, h * zz), _m(_lerp(c, '#000000', .45), .5), g, seg=20)
        cyl(nm + 't', r_ * .85, .02, (0, 0, h + .005), _m(_lerp(c, '#000000', .25)), g, seg=20)
    elif kind == 'box':
        w, d, h = rn.uniform(.35, .55) * s, rn.uniform(.3, .45) * s, rn.uniform(.22, .4) * s
        bx(nm + 'b', (w, d, h), (0, 0, h / 2), _m(rn.choice(('#c89b5e', '#b78a50', '#d3aa6c'))), g, .008)
        bx(nm + 't', (.07 * s, d * 1.01, .006), (0, 0, h + .003), _m('#eddcb0'), g)
        bx(nm + 'f', (.07 * s, .006, h * 1.0), (0, -d / 2 - .002, h / 2), _m('#eddcb0'), g)
    elif kind == 'pebble':
        for k in range(rn.randint(2, 4)):
            r_ = rn.uniform(.05, .12) * s
            _sph(g, f'{nm}p{k}', r_, (rn.uniform(-.15, .15), rn.uniform(-.15, .15), r_ * .5), (1, rn.uniform(.7, 1), .55), _m(rn.choice(('#8c8a85', '#a39c90', '#6f6d6a', '#b5ab98'))))
    elif kind == 'bag':
        c = rn.choice(('#d8c9a4', '#b9b3a6', '#c9a96a', '#a8c3d4'))
        _sph(g, nm + 'b', .22 * s, (0, 0, .2 * s), (1, .8, 1.0), _m(c))
        cyl(nm + 't', .05 * s, .08 * s, (0, 0, .43 * s), _m(_lerp(c, '#000000', .3)), g, seg=10)
        bx(nm + 'l', (.18 * s, .01, .1 * s), (0, -.17 * s, .22 * s), _m(rn.choice(('#d94a3d', '#2f6fb0', '#2b2b2b'))), g)
    elif kind == 'cable':
        c = rn.choice(('#1f2330', '#d9822b', '#2f6fb0'))
        for k in range(3):
            bpy.ops.mesh.primitive_torus_add(major_radius=(.2 - k * .01) * s, minor_radius=.035 * s, major_segments=24, minor_segments=8, location=(0, 0, .035 * s + k * .06 * s))
            o = bpy.context.object
            o.name, o.parent = f'{nm}t{k}', g
            o.data.materials.append(_m(c, .6))
    else:
        raise ValueError(kind)


def scatter(name, x0, x1, y0, y1, n, kinds=('crate', 'bin', 'cone', 'barrel', 'box', 'pebble', 'bag', 'cable'), seed=1, z=0, keep_clear=None):
    """n small props (crate bin cone barrel box pebble bag cable) at random spots in x0..x1, y0..y1; keep_clear=(x,y,r) or a list of them stays empty."""
    rn = random.Random(seed)
    g = group(name, None, (0, 0, 0))
    kc = [] if keep_clear is None else ([keep_clear] if not isinstance(keep_clear[0], (tuple, list)) else list(keep_clear))
    got = []
    for i in range(n):
        for _t in range(40):
            x, y = rn.uniform(x0, x1), rn.uniform(y0, y1)
            if all(math.hypot(x - a, y - b) >= r for a, b, r in kc) and all(math.hypot(x - a, y - b) >= .42 for a, b in got):
                break
        else:
            continue
        got.append((x, y))
        pg = group(f'{name}_{i}', g, (x, y, z))
        pg.rotation_euler = (0, 0, rn.uniform(0, 6.283))
        _prop(pg, f'{name}_{i}_', rn.choice(kinds), rn, rn.uniform(.75, 1.35))
    return g


# ----------------------------------------------------------------------------- ambient life (movers loop forever; every wrap happens while invisible)
def _rm(nt, sock_, a, b, c, d):
    r = nt.nodes.new('ShaderNodeMapRange')
    r.interpolation_type = 'SMOOTHSTEP'
    for k, v in zip(('From Min', 'From Max', 'To Min', 'To Max'), (a, b, c, d)):
        r.inputs[k].default_value = v
    nt.links.new(sock_, r.inputs['Value'])
    return r.outputs['Result']


def _mul(nt, a, b):
    n = nt.nodes.new('ShaderNodeMath')
    n.operation = 'MULTIPLY'
    for i, v in enumerate((a, b)):
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def _fade_mat(name, hx, alpha, z=None, x=None, outline=None):
    """Unlit translucent colour whose alpha ramps to 0 outside world z=(lo, hi, fade_lo, fade_hi) and x=(lo, hi, fade): wraps happen unseen."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    ge = nt.nodes.new('ShaderNodeNewGeometry')
    se = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(ge.outputs['Position'], se.inputs[0])
    a = alpha
    if z:
        a = _mul(nt, _mul(nt, a, _rm(nt, se.outputs['Z'], z[0], z[0] + z[2], 0, 1)), _rm(nt, se.outputs['Z'], z[1] - z[3], z[1], 1, 0))
    if x:
        a = _mul(nt, _mul(nt, a, _rm(nt, se.outputs['X'], x[0], x[0] + x[2], 0, 1)), _rm(nt, se.outputs['X'], x[1] - x[2], x[1], 1, 0))
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*srgb(hx), 1)
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(a, mx.inputs[0])
    nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], nt.nodes.new('ShaderNodeOutputMaterial').inputs['Surface'])
    m.surface_render_method = 'BLENDED'
    return m


def _span(b, lo, hi, fade):
    """Wrap length so the travel from base b always covers lo..hi plus the fade zones at both ends."""
    return 2 * (max(b - lo, hi - b) + fade) + .01


def _a_dust(nm, ox, n, rn, a):
    x0, x1, y0, y1, z0, z1 = a
    fz, fx = .3, .5
    mt = _fade_mat(f'{nm}_m', '#fff6dc', .6, z=(z0, z1, fz, fz), x=(x0, x1, fx))
    out = []
    for i in range(n):
        xb, yb, zb = rn.uniform(x0, x1), rn.uniform(y0, y1), rn.uniform(z0, z1)
        gz = group(f'{nm}_z{i}', None, (0, 0, zb))
        o = disc(gz, nm, 'm', rn.uniform(.018, .04), (xb, yb, 0), mt, seg=10)
        _mover(gz.name, (0, 0, rn.choice((-1, 1)) * rn.uniform(.0015, .004)), wrap=_span(zb, z0, z1, fz))
        _mover(o.name, (rn.choice((-1, 1)) * rn.uniform(.002, .006), 0, 0), wrap=_span(xb, x0, x1, fx))
        out.append(gz)
    return out


def _a_leaves(nm, ox, n, rn, a):
    x0, x1, y0, y1, z0, z1 = a
    fz, fx = .3, .5
    mts = [_fade_mat(f'{nm}_m{k}', c, 1.0, z=(z0, z1, fz, fz), x=(x0, x1, fx)) for k, c in enumerate(('#d9822b', '#c0472f', '#e3b23c', '#7a8f2e'))]
    out = []
    for i in range(n):
        xb, yb, zb = rn.uniform(x0, x1), rn.uniform(y0, y1), rn.uniform(z0, z1)
        gz = group(f'{nm}_z{i}', None, (0, 0, zb))
        o = disc(gz, nm, 'l', rn.uniform(.03, .055), (xb, yb, 0), mts[i % 4], scl=(1, 1, .55), seg=12)
        o.rotation_euler[1] = rn.uniform(0, 6.283)
        _mover(gz.name, (0, 0, -rn.uniform(.012, .026)), wrap=_span(zb, z0, z1, fz), bob=(rn.uniform(.03, .07), rn.uniform(.1, .22), rn.uniform(0, 6.28)))
        _mover(o.name, (rn.uniform(.006, .014), 0, 0), wrap=_span(xb, x0, x1, fx))
        out.append(gz)
    return out


def _a_smoke(nm, ox, n, rn, a):
    x0, x1, y0, y1, z0, z1 = a
    px, py = (x0 + x1) / 2, (y0 + y1) / 2
    H = z1 - z0
    mt, ol = _fade_mat(f'{nm}_m', '#e4e6ec', .8, z=(z0, z1, .15, H * .6)), _fade_mat(f'{nm}_o', '#7f8598', .8, z=(z0, z1, .15, H * .6))
    vz = H / rn.uniform(240, 330)
    out = []
    for i in range(n):
        zb = z0 + H * i / n
        g = group(f'{nm}_g{i}', None, (px + rn.uniform(-.06, .06), py, zb))
        r_ = rn.uniform(.2, .3)
        for k, (dx, dz, rr) in enumerate(((0, 0, 1), (-.7, .2, .7), (.75, .15, .75))):
            disc(g, nm, 'o', r_ * rr * 1.14, (dx * r_, .02 + k * .001, dz * r_), ol, seg=16)
        for k, (dx, dz, rr) in enumerate(((0, 0, 1), (-.7, .2, .7), (.75, .15, .75))):
            disc(g, nm, 'f', r_ * rr, (dx * r_, k * .001, dz * r_), mt, seg=16)
        _mover(g.name, (0, 0, vz), wrap=_span(zb, z0, z1, .15 + H * .6) + H * .2)
        out.append(g)
    return out


def _a_birds(nm, ox, n, rn, a):
    x0, x1, y0, y1, z0, z1 = a
    mt = flat(nm + '_m', '#26304a')
    v = [(-.5, 0, .14), (-.5, 0, .08), (0, 0, -.08), (.5, 0, .08), (.5, 0, .14), (0, 0, .02)]
    me = bpy.data.meshes.new(nm + '_v')
    me.from_pydata(v, [], [(0, 1, 2, 3, 4, 5)])
    me.update()
    me.materials.append(mt)
    out, left = [], n
    while left > 0:
        k = min(left, rn.randint(3, 6))
        left -= k
        cx, cy, cz = rn.uniform(x0, x1), rn.uniform(y0, y1), rn.uniform(z0, z1)
        d = rn.choice((-1, 1))
        vx = d * rn.uniform(.07, .12)
        s = rn.uniform(.7, 1.1)
        for j in range(k):
            side = (j + 1) // 2 * (1 if j % 2 else -1)
            bxx, byy, bzz = cx - d * abs(side) * .5 * s * 2 + rn.uniform(-.1, .1), cy + side * .35 * s * 2, cz + rn.uniform(-.1, .1) - abs(side) * .1
            o = bpy.data.objects.new(f'{nm}_b{len(out)}', me)
            sc.collection.objects.link(o)
            o.location, o.scale = (bxx, byy, bzz), (s, s, s)
            o.visible_shadow = False
            _mover(o.name, (vx, 0, 0), wrap=_span(bxx, x0, x1, 4), bob=(.05 * s, rn.uniform(.3, .45), rn.uniform(0, 6.28)))
            out.append(o)
    return out


def _a_flags(nm, ox, n, rn, a):
    x0, x1, y0, y1, z0, z1 = a
    pole = _m('#8c929c', .5)
    pal = (('#d9382e', '#f5f0e6'), ('#1f5fa8', '#f2c230'), ('#2f8f5b', '#f5f0e6'), ('#e08a1e', '#7b2d5f'))
    out = []
    for i in range(n):
        x = x0 + (x1 - x0) * (i + .5) / n
        y = rn.uniform(y0, y1)
        cyl(f'{nm}_p{i}', .025, z1 - z0, (x, y, (z0 + z1) / 2), pole, seg=8)
        w_, h_ = .8, .5
        cz = z1 - h_ / 2 - .05
        c1, c2 = pal[i % 4]
        m = bpy.data.materials.new(f'{nm}_fm{i}')
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        tc = nt.nodes.new('ShaderNodeTexCoord')
        se = nt.nodes.new('ShaderNodeSeparateXYZ')
        nt.links.new(tc.outputs['UV'], se.inputs[0])
        oi = nt.nodes.new('ShaderNodeObjectInfo')
        sz = nt.nodes.new('ShaderNodeSeparateXYZ')
        nt.links.new(oi.outputs['Location'], sz.inputs[0])
        ph = _rm(nt, sz.outputs['Z'], cz, cz + .03, 0, 6.2832)
        ang = nt.nodes.new('ShaderNodeMath')
        ang.operation = 'MULTIPLY_ADD'
        nt.links.new(se.outputs['X'], ang.inputs[0])
        ang.inputs[1].default_value = 9.0
        nt.links.new(ph, ang.inputs[2])
        sn = nt.nodes.new('ShaderNodeMath')
        sn.operation = 'SINE'
        nt.links.new(ang.outputs[0], sn.inputs[0])
        br = nt.nodes.new('ShaderNodeMath')
        br.operation = 'MULTIPLY_ADD'
        nt.links.new(sn.outputs[0], br.inputs[0])
        br.inputs[1].default_value, br.inputs[2].default_value = .15, .88
        wob = nt.nodes.new('ShaderNodeMath')
        wob.operation = 'MULTIPLY_ADD'
        nt.links.new(sn.outputs[0], wob.inputs[0])
        wob.inputs[1].default_value, wob.inputs[2].default_value = .09, 0
        vv = nt.nodes.new('ShaderNodeMath')
        nt.links.new(se.outputs['Y'], vv.inputs[0])
        nt.links.new(wob.outputs[0], vv.inputs[1])
        ra = nt.nodes.new('ShaderNodeValToRGB')
        ra.color_ramp.interpolation = 'CONSTANT'
        ra.color_ramp.elements[0].position, ra.color_ramp.elements[0].color = 0, (*srgb(c1), 1)
        e = ra.color_ramp.elements.new(.34)
        e.color = (*srgb(c2), 1)
        e = ra.color_ramp.elements.new(.67)
        e.color = (*srgb(c1), 1)
        nt.links.new(vv.outputs[0], ra.inputs['Fac'])
        mc = nt.nodes.new('ShaderNodeMix')
        mc.data_type, mc.blend_type = 'RGBA', 'MULTIPLY'
        mc.inputs[0].default_value = 1
        nt.links.new(ra.outputs['Color'], sock(mc, 'A_Color'))
        nt.links.new(br.outputs[0], sock(mc, 'B_Color'))
        em = nt.nodes.new('ShaderNodeEmission')
        nt.links.new(out_color(mc), em.inputs['Color'])
        nt.links.new(em.outputs[0], nt.nodes.new('ShaderNodeOutputMaterial').inputs['Surface'])
        o = _plane(f'{nm}_f{i}', w_, h_, (x + w_ / 2 + .02, y - .02, cz), m, vertical=True)
        _mover(o.name, (0, 0, 0), bob=(.03, rn.uniform(.18, .3), rn.uniform(0, 6.28)))
        out.append(o)
    return out


def _a_lights(nm, ox, n, rn, a):
    x0, x1, y0, y1, z0, z1 = a
    out = []
    for i in range(n):
        w_, h_ = rn.uniform(.32, .5), rn.uniform(.45, .65)
        x, z = x0 + (x1 - x0) * (i + rn.uniform(.2, .8)) / n, rn.uniform(z0, z1)
        m = bpy.data.materials.new(f'{nm}_m{i}')
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        tc = nt.nodes.new('ShaderNodeTexCoord')
        se = nt.nodes.new('ShaderNodeSeparateXYZ')
        nt.links.new(tc.outputs['UV'], se.inputs[0])
        oi = nt.nodes.new('ShaderNodeObjectInfo')
        sz = nt.nodes.new('ShaderNodeSeparateXYZ')
        nt.links.new(oi.outputs['Location'], sz.inputs[0])
        t = _rm(nt, sz.outputs['Z'], z, z + .02, 0, 1)
        lit = nt.nodes.new('ShaderNodeMix')
        lit.data_type = 'RGBA'
        nt.links.new(t, lit.inputs[0])
        sock(lit, 'A_Color').default_value = (*srgb('#5b4a36'), 1)
        sock(lit, 'B_Color').default_value = (*srgb(rn.choice(('#ffd27a', '#ffe7a8', '#ffc25c'))), 1)
        dists = []
        for s_ in (se.outputs['X'], se.outputs['Y']):
            sb = nt.nodes.new('ShaderNodeMath')
            sb.operation = 'SUBTRACT'
            nt.links.new(s_, sb.inputs[0])
            sb.inputs[1].default_value = .5
            ab = nt.nodes.new('ShaderNodeMath')
            ab.operation = 'ABSOLUTE'
            nt.links.new(sb.outputs[0], ab.inputs[0])
            dists.append(ab.outputs[0])
        mxn = nt.nodes.new('ShaderNodeMath')
        mxn.operation = 'MAXIMUM'
        nt.links.new(dists[0], mxn.inputs[0])
        nt.links.new(dists[1], mxn.inputs[1])
        fr = nt.nodes.new('ShaderNodeMath')
        fr.operation = 'GREATER_THAN'
        nt.links.new(mxn.outputs[0], fr.inputs[0])
        fr.inputs[1].default_value = .4
        cr = nt.nodes.new('ShaderNodeMath')
        cr.operation = 'LESS_THAN'
        nt.links.new(mn := _min2(nt, dists[0], dists[1]), cr.inputs[0])
        cr.inputs[1].default_value = .035
        fm = nt.nodes.new('ShaderNodeMath')
        fm.operation = 'MAXIMUM'
        nt.links.new(fr.outputs[0], fm.inputs[0])
        nt.links.new(cr.outputs[0], fm.inputs[1])
        fc = nt.nodes.new('ShaderNodeMix')
        fc.data_type = 'RGBA'
        nt.links.new(fm.outputs[0], fc.inputs[0])
        nt.links.new(out_color(lit), sock(fc, 'A_Color'))
        sock(fc, 'B_Color').default_value = (*srgb('#2a2622'), 1)
        em = nt.nodes.new('ShaderNodeEmission')
        nt.links.new(out_color(fc), em.inputs['Color'])
        nt.links.new(em.outputs[0], nt.nodes.new('ShaderNodeOutputMaterial').inputs['Surface'])
        o = _plane(f'{nm}_w{i}', w_, h_, (x, y0 - .02, z), m, vertical=True)
        _mover(o.name, (0, 0, 0), bob=(.02, rn.uniform(.05, .45), rn.uniform(0, 6.28)))
        out.append(o)
    return out


def _min2(nt, a, b):
    n = nt.nodes.new('ShaderNodeMath')
    n.operation = 'MINIMUM'
    nt.links.new(a, n.inputs[0])
    nt.links.new(b, n.inputs[1])
    return n.outputs[0]


_AMB = dict(dust=(_a_dust, 26, lambda o: (o - 2.5, o + 2.5, -1.5, 5, .1, 2.8)),
            birds=(_a_birds, 9, lambda o: (o - 14, o + 14, 6, 11, 4, 8)),
            leaves=(_a_leaves, 10, lambda o: (o - 2.5, o + 2.5, -.5, 4, .1, 3.5)),
            smoke=(_a_smoke, 6, lambda o: (o + 1.5, o + 1.5, 5, 5, 2.5, 6.5)),
            flags=(_a_flags, 3, lambda o: (o - 3, o + 3, 4, 6, 0, 3.4)),
            lights=(_a_lights, 7, lambda o: (o - 4, o + 4, 2.7, 2.7, 1.2, 4.2)))


def ambient(name, ox=0, kinds=('dust', 'birds'), n=None, seed=1, area=None):
    """Looping background motion via MOVERS. kinds: dust birds leaves smoke flags lights. area=(x0,x1,y0,y1,z0,z1) in world metres (default from ox):
    dust/leaves fill it, birds fly through it (x = their lane), smoke rises from its centre x,y from z0 to z1, flags are poles spread along x with height z1,
    lights are window lights on the wall plane y0. n = count per kind (default per kind). Every wrap happens while faded out or beyond the sky dome."""
    rn = random.Random(seed)
    out = {}
    for kd in kinds:
        f, dn, da = _AMB[kd]
        out[kd] = f(f'{name}_{kd}', ox, n if n is not None else dn, rn, area or da(ox))
    return out


# ----------------------------------------------------------------------------- light shapes
def _light_img(kind, h, w, P, hx, seed):
    rn = np.random.default_rng(seed)
    xm = (np.arange(w, dtype=np.float32)[None] - w / 2) / P
    ym = (np.arange(h, dtype=np.float32)[:, None] - h / 2) / P
    sm = lambda d, e: np.clip(d / e, 0, 1)
    if kind == 'window':
        px, py = 2.0, 2.6
        u = ((xm - ym * .45 + px / 2) % px) - px / 2
        v = ((ym + py / 2) % py) - py / 2
        a = sm(.55 - np.abs(u), .05) * sm(.8 - np.abs(v), .05)
        a *= sm(np.abs(u) - .04, .02) * sm(np.abs(v) - .04, .02)
    elif kind == 'blinds':
        u, v = xm - ym * .25, ym
        a = sm(.65 - np.abs(u), .08) * sm(.9 - np.abs(v), .08)
        a *= np.clip(.5 - np.abs(((v + .1) % .14) / .14 - .5), 0, 1) * 5
        a = np.clip(a, 0, 1)
    elif kind == 'leaves':
        d1, _, r = _vor(h, w, P * .28, rn)
        f = _fbm(h, w, P * .25, rn, 3)
        a = sm(P * .1 * (.5 + r) - d1 + (f - .5) * P * .25, 4)
        a *= sm(_fbm(h, w, P * 1.2, rn, 2) - .3, .1)
    else:
        u = (xm + ym * .6) % .9
        a = sm(.2 - np.abs(u - .45), .03) * sm(.4 - np.minimum(np.abs(xm), 9) * .0, .1)
    img = np.empty((h, w, 4), np.float32)
    img[..., :3] = _c(hx)
    img[..., 3] = a
    return img


def light_pattern(name, x0, x1, y0, y1, kind='window', hex='#fff1c8', alpha=.35, z=.008, rot=0, seed=1):
    """Transparent plane of light shapes on the floor (glow, no shadow). kinds: window blinds leaves stripes. rot = degrees around z."""
    if kind not in ('window', 'blinds', 'leaves', 'stripes'):
        raise ValueError(kind)
    h, w, P = _dims(x1 - x0, y1 - y0, 80)
    im = _bake(_key('l', kind, h, w, hex, seed), lambda: _light_img(kind, h, w, P, hex, seed))
    return _plane(name, x1 - x0, y1 - y0, ((x0 + x1) / 2, (y0 + y1) / 2, z), _emit_mat(name + '_m', im, alpha), rz=rot)




