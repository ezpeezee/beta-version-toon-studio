"""Code-drawn flat character, redrawn from full-res reference crops (ref f20, f40, f62, f66).
python puppet_v3.py <out dir> [frames: 1,25,60 ... default all]
Canvas 1200x1900, feet baseline at y 1860, drawn at 2x and downsampled in premultiplied alpha."""
import json
import math
import os
import random
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SHOT, CAST = os.environ.get('SHOT', 'A'), os.environ.get('CAST', 'H')

NF, W, H, SS = (120 if SHOT == 'A' else 110), 1200, 1900, 2
CX, FEET = 600, 1860
HEAD_W, HEAD_H = 500, 415
TOR_W, TOR_H = (285, 430) if CAST == 'H' else (340, 400)
TY = FEET - 625 - TOR_H / 2 + 20       # torso centre: legs about 1.25 head widths
INK = (44, 33, 46, 255)
WHITE, LILAC = (250, 245, 246), (226, 212, 228)
TEAL, TEAL_L, TEAL_D, PANTS = (52, 188, 160, 255), (92, 208, 182, 255), (30, 128, 112, 255), (72, 66, 70, 255)
BACK = (44, 160, 138, 255)
HAIR, RED, GOLD = (122, 80, 44, 255), (206, 40, 58, 255), (216, 178, 58, 255)
if CAST == 'C':
    TEAL, TEAL_L, TEAL_D, BACK, HAIR = (222, 118, 66, 255), (240, 150, 96, 255), (168, 80, 44, 255), (196, 100, 56, 255), (52, 40, 40, 255)
CAP_B, CAP_W, CAP_D = (54, 88, 150, 255), (230, 238, 250, 255), (30, 40, 70, 255)
STITCH = (235, 232, 224, 255)
SHOULDER = (725, TY - 170)
HIT_XY = (880, 1270)      # hand on contact, at arm length from the shoulder


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def seg(f, a, b, v0, v1):
    return v0 + (v1 - v0) * ease((f - a) / max(1, b - a))


def wob(i, amp, seed=0.0):
    """Fixed hand wobble: depends on position along the stroke, not on the frame, so the line doesn't boil."""
    return amp * (math.sin(i * .37 + seed) + .6 * math.sin(i * .83 + seed * 2.1) + .35 * math.sin(i * 1.9 + seed * .7))


def mouth_track():
    """Seeded holds of 1-4 f, closed in the pauses; never a fixed cycle."""
    r, out, last = random.Random(7), {}, ''
    for a, b in ((30, 69), (93, 118)):
        f = a
        while f <= b:
            m = r.choice([x for x in ('o', 'wide', 'line', 'smile', 'open', 'pout') if x != last])
            for k in range(f, min(b + 1, f + r.randint(1, 4))):
                out[k] = m
            f, last = k + 1, m
    return out


MOUTH = mouth_track()
# expression holds of 5-15 f: (first, last, eyes, brows)
FACE = ((1, 36, 'smug', 'flat'), (37, 44, 'happy', None), (45, 54, 'smug', 'up'), (55, 55, 'slit', 'up'), (56, 57, 'shut', 'up'), (58, 59, 'slit', 'up'),
        (60, 69, 'dot', 'up'), (70, 78, 'smug', 'angry'), (79, 92, 'ring', None), (93, 99, 'dot', 'sad'), (100, 100, 'slit', 'sad'), (101, 102, 'shut', 'sad'),
        (103, 104, 'slit', 'sad'), (105, NF, 'smug', 'flat'))


def hand_r(f):
    """Low with the hammer, raise, long hold, big backswing, 4 f arc around the shoulder at arm length, flat face on the crate, dip with it, rebound, recover."""
    swy, sw2 = 4 * math.sin(f * .3), 5 * math.sin(f * .23)
    if f <= 70:
        return seg(f, 40, 52, 800, 960) + swy, seg(f, 40, 52, 1220, 640) + sw2, seg(f, 40, 52, 25, 38)
    if f <= 74:
        return seg(f, 70, 74, 960, 900), seg(f, 70, 74, 640, 520), seg(f, 70, 74, 38, 4)
    if f < 78:
        u = ((f - 74) / 4) ** 2
        a0, r0 = math.atan2(520 - SHOULDER[1], 900 - SHOULDER[0]), math.hypot(900 - SHOULDER[0], 520 - SHOULDER[1])
        a1, r1 = math.atan2(HIT_XY[1] - SHOULDER[1], HIT_XY[0] - SHOULDER[0]), math.hypot(HIT_XY[0] - SHOULDER[0], HIT_XY[1] - SHOULDER[1])
        a, r = a0 + (a1 - a0) * u, r0 + (r1 - r0) * u
        return SHOULDER[0] + r * math.cos(a), SHOULDER[1] + r * math.sin(a), 4 + 86 * u
    if f <= 82:
        k = int(f)
        return {78: (HIT_XY[0], HIT_XY[1], 90), 79: (HIT_XY[0] + 2, HIT_XY[1] + 34, 90), 80: (HIT_XY[0] + 4, HIT_XY[1] + 16, 88), 81: (HIT_XY[0] + 4, HIT_XY[1] - 28, 84), 82: (HIT_XY[0], HIT_XY[1] - 45, 80)}[k]
    return seg(f, 82, 96, HIT_XY[0], 800) + swy * ease((f - 82) / 14), seg(f, 82, 96, HIT_XY[1] - 45, 1220) + sw2 * ease((f - 82) / 14), seg(f, 82, 96, 80, 32)


def puffs(im, f):
    """Flat outlined dust sprites and a dot ring at the contact, as the channel draws its FX."""
    sx, sy = HIT_XY[0] + 279, HIT_XY[1] + 110
    t = (f - 78) / 16
    d = ImageDraw.Draw(im)
    r = random.Random(11)
    for i in range(6):
        a = math.radians(-170 + i * 32 + r.uniform(-8, 8))
        dist, size = r.uniform(120, 240), r.uniform(48, 86)
        k = ease(t * 1.6) * dist
        rad = size * math.sin(min(1, t * 1.15) * math.pi) ** .6
        if rad > 3:
            inked(d, blob(sx + k * math.cos(a), sy + k * math.sin(a) * .7 - 40 * t, rad, rad * .86, amp=.05, seed=i), (246, 226, 196, 255) if i % 2 else (226, 196, 176, 255), 7)
    if f <= 85:
        for i in range(10):
            a = i * .628 + .3
            k = 60 + (f - 78) * 42
            q = 15 * (1 - (f - 78) / 8)
            x, y = sx + k * math.cos(a), sy + k * .75 * math.sin(a)
            d.ellipse([(x - q) * SS, (y - q) * SS, (x + q) * SS, (y + q) * SS], fill=(255, 226, 120, 255))


def walk_feet(f, v, T=16, dirn=1):
    """Planted foot slides back at exactly the card's speed, so it doesn't skate; the other swings ahead with a lift."""
    stride = v * T / 2
    out = []
    for ph in (f / T, f / T + .5):
        u = ph % 1
        if u < .5:
            out.append((CX + dirn * stride * (.5 - 2 * u), 0.0))
        else:
            q = (u - .5) * 2
            out.append((CX + dirn * stride * (-.5 + ease(q)), 62 * math.sin(q * math.pi)))
    return out


def pose_b(f):
    """Dusk shot: walk to the door, stop, squeeze turn, walk in. wx/wy are world metres; sq is the card's width scale."""
    M = 1.7 / 1760
    b = 5 * math.sin(f * .19)
    if CAST == 'C':
        talk = 26 <= f <= 56
        p = dict(view='front', bob=b, lean=2.5 * math.sin(f * .11), tilt=-4 + 4 * math.sin(f * .13), hat_y=0, hat_rot=0, knee=14 * math.sin(f * .17), sweat=False, star=False, ham_rot=0, wx=1.02, wy=2.35, sq=1.0)
        p['hand_l'] = (seg(f, 28, 36, 440, 190) + 12 * math.sin(f * .7) * (1 if 36 <= f <= 56 else 0) + seg(f, 56, 66, 0, 250), seg(f, 28, 36, 1240, 880) + seg(f, 56, 66, 0, 360) + b)
        p['bend_l'] = -60
        p['hand_r'] = (780, 1240 + b)
        p['bend_r'] = -120
        p['eyes'], p['brows'] = ('happy', None) if f >= 80 else ('dot', 'up') if f >= 26 else ('smug', 'flat')
        p['mouth'] = MOUTH.get(f, 'tick') if talk else 'smile' if f >= 80 else 'tick'
        p['feet'] = ((CX - 150, 0), (CX + 150, 0))
        return p
    V = 40            # px per frame across the card = 40 * M m/f
    if f <= 42:
        wx = -1.75 + V * M * f
        feet, toe, view, walk = walk_feet(f, V), 1, 'q_r', 1
    elif f <= 54:
        wx = -1.75 + V * M * 42
        feet, toe, view, walk = ((CX - 90, 0), (CX + 90, 0)), None, 'q_r' if f < 52 else 'front', 0
    else:
        wx = -1.75 + V * M * 42
        feet, toe, view, walk = ((CX - 90, 0), (CX + 90, 0)), None, 'front', 0
    # 10 f squeeze, art swaps at the narrow point
    sq = 1.0
    if 56 <= f <= 66:
        sq = .1 + .9 * abs(f - 61) / 5
        view = 'q_r' if f < 61 else 'back'
    elif f > 66:
        view = 'back'
    wy = 1.7
    if f > 66:
        q = (f - 66) * .062
        wy = 1.7 + min(q, 2.1)
        wx = wx + (0.0 - wx) * ease((f - 66) / 16)
        s_ = min(1, (f - 66) / 6)
        ph = f * .4
        feet = ((CX - 62 + 16 * math.sin(ph), 44 * s_ * max(0, math.sin(ph))), (CX + 62 + 16 * math.sin(ph + 3.14), 44 * s_ * max(0, math.sin(ph + 3.14))))
        toe = None
    swing = 110 * math.sin(f * math.pi / 8) * walk
    bob = (10 * abs(math.sin(f * math.pi / 8)) if walk or f > 66 else 0) + b * .5
    p = dict(view=view, bob=bob, lean=6 * walk, tilt=-3 + 3 * math.sin(f * .13) + 3.5 * math.sin(f * math.pi / 8) * walk, hat_y=0, hat_rot=0, knee=10 * math.sin(f * .17), sweat=False, star=False, ham_rot=0, wx=wx, wy=wy, sq=sq, feet=feet, hip=16 if walk else 52)
    if toe:
        p['toe'] = toe
    bk = 30 * math.sin(f * math.pi / 8) if f > 66 else 0
    p['hand_l'], p['hand_r'] = (430 + swing + bk, 1240 + bob), (790 - swing - bk, 1230 + bob)
    p['bend_l'], p['bend_r'] = -70, -70
    p['eyes'], p['brows'] = ('smug', 'flat') if f < 44 else ('dot', 'up')
    p['mouth'] = 'tick' if f < 44 else 'o' if f < 52 else 'line'
    return p


def pose(f):
    if SHOT == 'B':
        return pose_b(f)
    """Everything that moves. Character is alive on every frame; art swaps are hard."""
    b = 5 * math.sin(f * .19) + 2.2 * math.sin(f * .47 + 1)
    view = 'back' if f < 25 else 'q_r' if 42 <= f <= 78 or f >= 93 else 'front'
    p = dict(view=view, bob=b, lean=2.5 * math.sin(f * .11), tilt=-3 + 3.5 * math.sin(f * .13) + (9 * (1 - ease((f - 25) / 6)) if 25 <= f <= 31 else 0) + seg(f, 40, 52, 0, -9) + seg(f, 76, 80, 0, -5) + seg(f, 79, 90, 0, 17))
    hx, hy, rot = hand_r(f)
    p['hand_r'], p['ham_rot'] = (hx, hy + b), rot
    # left arm: hand on hip, flung up beside the head on the shock, back to the hip
    p['hand_l'] = (seg(f, 79, 86, 445, 255) + seg(f, 96, 108, 0, 190) + 6 * math.sin(f * .5), seg(f, 79, 86, 1205, 610) + seg(f, 96, 108, 0, 595) + 8 * math.sin(f * .61) + b)
    p['bend_l'] = seg(f, 79, 86, -190, -90) + seg(f, 96, 108, 0, -100)
    p['bend_r'] = seg(f, 40, 52, -170, -90) + seg(f, 74, 78, 0, 90) + seg(f, 82, 96, 0, -170)
    # cap: real hop with one spin, lands f98
    u = max(0.0, min(1.0, (f - 79) / 19))
    p['hat_y'], p['hat_rot'] = -255 * 4 * u * (1 - u), 26 * math.sin(u * 2 * math.pi)
    p['hat_sq'] = .46 + .54 * abs(math.cos(u * 2 * math.pi)) if 0 < u < 1 else 1.0
    p['knee'] = 22 * math.sin(f * .17) + seg(f, 78, 86, 0, 34)
    p['eyes'], p['brows'] = next((e, br) for a, z, e, br in FACE if a <= f <= z)
    p['mouth'] = 'smile' if 37 <= f <= 44 else MOUTH.get(f, 'open' if 79 <= f <= 92 else 'tick')
    p['sweat'] = f >= 82
    p['star'] = 78 <= f <= 80
    return p


def stroke(d, pts, w, col=INK, seed=0.0, amp=.05):
    """Round-capped ink line of near-constant width."""
    for i, (x, y) in enumerate(pts):
        r = (w / 2 + wob(i, w * amp, seed)) * SS
        d.ellipse((x * SS - r, y * SS - r, x * SS + r, y * SS + r), fill=col)


def taper(d, pts, w0, w1, col=INK, seed=0.0):
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        r = (w0 + (w1 - w0) * i / max(1, n - 1)) / 2 * SS + wob(i, .8, seed) * SS
        d.ellipse((x * SS - r, y * SS - r, x * SS + r, y * SS + r), fill=col)


def bez(a, c, b, n=70):
    return [((1 - t) ** 2 * a[0] + 2 * t * (1 - t) * c[0] + t * t * b[0], (1 - t) ** 2 * a[1] + 2 * t * (1 - t) * c[1] + t * t * b[1]) for t in np.linspace(0, 1, n)]


def blob(cx, cy, rx, ry, n=220, amp=0.0, seed=0.0, sq=2.0, belly=0.0):
    """Superellipse; belly > 0 pushes the widest point below the middle (bun head, egg torso)."""
    out = []
    for i in range(n):
        a = 2 * math.pi * i / n
        c, s = math.cos(a), math.sin(a)
        k = 1 + wob(i * .25, amp, seed)
        sy = abs(s) ** (2 / sq) * np.sign(s)
        out.append((cx + k * rx * abs(c) ** (2 / sq) * np.sign(c) * (1 + belly * sy), cy + k * ry * sy))
    return out


def poly(d, pts, col):
    d.polygon([(x * SS, y * SS) for x, y in pts], fill=col)


def inked(d, pts, col, ink=8.0):
    """Fill with an uneven outline: thin on the left, heavy on the right and below, from an offset ink shape behind it."""
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sx, sy = 1 + 2 * ink / (max(xs) - min(xs)), 1 + 2 * ink / (max(ys) - min(ys))
    poly(d, [(mx + (x - mx) * sx + ink * .22, my + (y - my) * sy + ink * .16) for x, y in pts], INK)
    poly(d, pts, col)


def head_shape(c):
    return blob(c, c, HEAD_W / 2, HEAD_H / 2, amp=.003, seed=1.3, sq=2.25, belly=.075)


JAG_F = [(-262, -215), (-262, -40), (-205, -8), (-168, -44), (-96, -70), (-40, -105), (40, -105), (104, -74), (170, -48), (212, -14), (262, -40), (262, -215)]
JAG_Q = [(-262, -215), (-262, -4), (-205, 26), (-165, -14), (-90, -24), (-20, -70), (60, -118), (150, -130), (262, -130), (262, -215)]
JAG_B = [(-270, -215), (-270, 150), (-180, 176), (-90, 146), (0, 180), (90, 146), (180, 176), (270, 150), (270, -215)]


def hair_on(im, pts, c, mask, jag_from):
    """Hair wedge lying ON the head, clipped to the head shape, with an inked jagged edge."""
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
    abs_pts = [(c + x, c + y) for x, y in pts]
    poly(ImageDraw.Draw(lay), abs_pts, HAIR)
    lay.putalpha(Image.fromarray((np.asarray(lay)[..., 3] * (np.asarray(mask) / 255)).astype(np.uint8)))
    ImageDraw.Draw(lay)
    d = ImageDraw.Draw(lay)
    edge = abs_pts[1:jag_from]
    for a, b in zip(edge, edge[1:]):
        stroke(d, [(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t) for t in np.linspace(0, 1, 24)], 11, amp=.03)
    im.alpha_composite(lay)


def head_art(view):
    """Head + hair in its own layer, centred. Painted lilac shade is fixed in the art."""
    s = 760 * SS
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = 380
    pts = head_shape(c)
    inked(d, pts, WHITE + (255,), 22)
    mask = Image.new('L', (s, s), 0)
    ImageDraw.Draw(mask).polygon([(x * SS, y * SS) for x, y in pts], fill=255)
    yy, xx = np.mgrid[0:s, 0:s] / SS
    t = np.clip((((xx - c) * -.5 + (yy - c) * 1.0) / (HEAD_H * .62) - .24) / .72, 0, 1) ** 1.6
    shade = np.zeros((s, s, 4), np.uint8)
    shade[..., :3] = LILAC
    shade[..., 3] = (t * np.asarray(mask)).astype(np.uint8)
    im.alpha_composite(Image.fromarray(shade, 'RGBA').filter(ImageFilter.GaussianBlur(5 * SS)))
    if view == 'back':
        hair_on(im, JAG_B, c, mask, 8)
    elif view == 'q_r':
        hair_on(im, JAG_Q, c, mask, 9)
    else:
        hair_on(im, JAG_F, c, mask, 11)
    return im


def pillow(c, rx, top, bot, n=200):
    return [(c + rx * math.cos(t), c + (top if math.sin(t) < 0 else bot) * math.sin(t)) for t in np.linspace(0, 2 * math.pi, n, endpoint=False)]


def hat_art():
    """Second cast member: straw hat, wide brim, red band."""
    s = 660 * SS
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = 330
    inked(d, blob(c, c + 40, 290, 58, amp=.004, seed=2), (232, 196, 110, 255), 14)
    inked(d, pillow(c - 0, 160, 150, 30), (240, 208, 126, 255), 14)
    stroke(d, [(c + t * 158, c + 12 + 16 * math.sqrt(1 - t * t)) for t in np.linspace(-.97, .97, 90)], 30, RED, amp=0)
    return im


def cap_art(view):
    """Engineer's cap (ref f20, f66): soft pillow crown, stripes fan down from a button near the back rim to the band, heavy band, narrow striped visor."""
    if CAST == 'C':
        return hat_art()
    s = 660 * SS
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = 330
    rx, top, bot = 236, 112, 46
    ox = 40 if view == 'q_r' else 0
    bx, by = c - ox * .8, c - top * .8
    rim = lambda x: c + bot * math.sqrt(max(0, 1 - ((x - c) / rx) ** 2))
    if view != 'back':
        xs = np.linspace(c + ox - 178, c + ox + 178, 60)
        dep = 60 if view == 'q_r' else 40
        arc = [math.sin((x - xs[0]) / (xs[-1] - xs[0]) * math.pi) ** .7 for x in xs]
        brim = [(x, rim(x) - 4) for x in xs] + [(x, rim(x) + dep * k) for x, k in zip(xs[::-1], arc[::-1])]
        inked(d, brim, CAP_B, 12)
        for q in (.4, .72):
            stroke(d, [(x, rim(x) + q * dep * k) for x, k in zip(xs[5:-5], arc[5:-5])], 7, CAP_W, seed=q, amp=.06)
    crown = pillow(c, rx, top, bot)
    inked(d, crown, CAP_B, 15)
    lay = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    # stripes: curved wedges from the button to evenly spaced points along the band, plus short ones behind the button
    n = 13
    ends = [c - rx * 1.06 + 2 * rx * 1.06 * (k + .5) / n for k in range(n)]
    wd = rx * 2.12 / n * .27
    for ex in ends:
        side = (ex - bx) * .34
        l = bez((bx, by), (bx + (ex - wd - bx) * .62 + side * .5, c - top * .06), (ex - wd, rim(ex) + 8), 22)
        r = bez((ex + wd, rim(ex) + 8), (bx + (ex + wd - bx) * .62 + side * .5, c - top * .06), (bx, by), 22)
        poly(ld, l + r, CAP_W)
    for t in range(190, 351, 32):
        ca, sa = math.cos(math.radians(t)), math.sin(math.radians(t))
        poly(ld, [(bx, by), (bx + 340 * math.cos(math.radians(t - 5)), by + 340 * math.sin(math.radians(t - 5))), (bx + 340 * math.cos(math.radians(t + 5)), by + 340 * math.sin(math.radians(t + 5)))], CAP_W)
    # soft shade toward the band, painted in
    yy = np.mgrid[0:s, 0:s][0] / SS
    sh = np.zeros((s, s, 4), np.uint8)
    sh[..., :3] = CAP_D[:3]
    sh[..., 3] = (np.clip((yy - (c - 6)) / 56, 0, 1) * 96).astype(np.uint8)
    lay.alpha_composite(Image.fromarray(sh, 'RGBA'))
    mask = Image.new('L', (s, s), 0)
    ImageDraw.Draw(mask).polygon([(x * SS, y * SS) for x, y in crown], fill=255)
    lay.putalpha(Image.fromarray((np.asarray(lay)[..., 3] * (np.asarray(mask) / 255)).astype(np.uint8)))
    im.alpha_composite(lay)
    d = ImageDraw.Draw(im)
    d.ellipse([(bx - 15) * SS, (by - 11) * SS, (bx + 15) * SS, (by + 11) * SS], fill=(248, 248, 248, 255), outline=INK, width=5 * SS)
    stroke(d, [(c + t * rx, rim(c + t * rx)) for t in np.linspace(-.97, .97, 180)], 20, INK, amp=.03)
    return im


def face(d, p, cx, cy):
    lk = 62 if p['view'] == 'q_r' else 0
    ex0, ex1, ey = cx - 60 + lk, cx + 70 + lk, cy + 18
    e = p['eyes']
    for i, ex in enumerate((ex0, ex1)):
        if e == 'ring':
            r = 44
            d.ellipse([(ex - r) * SS, (ey - r) * SS, (ex + r) * SS, (ey + r) * SS], fill=(255, 255, 255, 255), outline=INK, width=13 * SS)
            d.ellipse([(ex + 3 - 10) * SS, (ey + 2 - 10) * SS, (ex + 3 + 10) * SS, (ey + 2 + 10) * SS], fill=INK)
        elif e == 'dot':
            d.ellipse([(ex - 18) * SS, (ey - 22) * SS, (ex + 18) * SS, (ey + 22) * SS], fill=INK)
            d.ellipse([(ex + 3) * SS, (ey - 13) * SS, (ex + 11) * SS, (ey - 5) * SS], fill=(255, 255, 255, 255))
        elif e == 'happy':
            stroke(d, bez((ex - 34, ey + 10), (ex, ey - 34), (ex + 34, ey + 10), 34), 16)
        elif e == 'shut':
            stroke(d, [(ex - 36 + t, ey + 2 + (i * 2 - 1) * -.12 * (t - 36)) for t in range(0, 72, 2)], 20)
        elif e == 'slit':
            d.chord([(ex - 34) * SS, (ey - 12) * SS, (ex + 34) * SS, (ey + 18) * SS], 0, 180, fill=INK)
        else:
            d.chord([(ex - 32) * SS, (ey - 24) * SS, (ex + 32) * SS, (ey + 26) * SS], 0, 180, fill=INK)
            d.ellipse([(ex + 8) * SS, (ey + 5) * SS, (ex + 15) * SS, (ey + 12) * SS], fill=(255, 255, 255, 255))
        br = p['brows']
        if br:
            rise, slope = {'flat': (-30 if i == 0 else -38, (-.04, .12)[i]), 'up': (-52, (-.2, .2)[i]), 'angry': (-30, (.34, -.34)[i]), 'sad': (-46, (-.34, .34)[i])}[br]
            stroke(d, [(ex - 38 + t, ey + rise + slope * (t - 38)) for t in range(0, 76, 3)], 19, seed=i)
    mx, my = cx + 8 + lk * 1.1, cy + 104
    m = p['mouth']
    if m == 'tick':
        stroke(d, bez((mx - 38, my + 8), (mx, my + 20), (mx + 40, my - 16), 30), 14)
    elif m == 'line':
        stroke(d, bez((mx - 28, my + 3), (mx, my + 8), (mx + 28, my + 1), 26), 14)
    elif m == 'o':
        d.ellipse([(mx - 18) * SS, (my - 18) * SS, (mx + 18) * SS, (my + 20) * SS], fill=INK)
    elif m == 'pout':
        d.ellipse([(mx - 22) * SS, (my - 26) * SS, (mx + 16) * SS, (my + 22) * SS], fill=INK)
        d.ellipse([(mx - 12) * SS, (my + 2) * SS, (mx + 8) * SS, (my + 16) * SS], fill=(214, 160, 190, 255))
    elif m == 'wide':
        d.ellipse([(mx - 30) * SS, (my - 15) * SS, (mx + 30) * SS, (my + 20) * SS], fill=INK)
    elif m == 'laugh':
        # big crescent: ink, dark red inside, a row of teeth along the top lip
        poly(d, bez((mx - 104, my - 34), (mx, my - 12), (mx + 104, my - 34), 30) + bez((mx + 104, my - 34), (mx, my + 118), (mx - 104, my - 34), 30), INK)
        poly(d, bez((mx - 80, my - 20), (mx, my - 2), (mx + 80, my - 20), 30) + bez((mx + 80, my - 20), (mx, my + 92), (mx - 80, my - 20), 30), (112, 22, 34, 255))
        for k in range(-3, 4):
            yt = my - 16 + 7 * (1 - (k / 3.5) ** 2)
            d.rectangle([(mx + k * 19 - 8) * SS, yt * SS, (mx + k * 19 + 8) * SS, (yt + 20 - abs(k) * 2) * SS], fill=(250, 248, 240, 255))
    elif m == 'smile':
        poly(d, bez((mx - 68, my - 28), (mx - 12, my + 2), (mx + 66, my + 8), 30) + bez((mx + 66, my + 8), (mx + 10, my + 82), (mx - 68, my - 28), 30), INK)
        for k in (-12, 8):
            d.rectangle([(mx + k) * SS, (my + 1 + k * .2) * SS, (mx + k + 12) * SS, (my + 9 + k * .2) * SS], fill=(250, 250, 250, 255))
    else:
        d.ellipse([(mx - 36) * SS, (my - 30) * SS, (mx + 36) * SS, (my + 38) * SS], fill=INK)
        d.ellipse([(mx - 23) * SS, (my + 8) * SS, (mx + 23) * SS, (my + 34) * SS], fill=RED)
    if CAST == 'C':
        stroke(d, bez((mx - 82, my - 6), (mx - 30, my - 46), (mx, my - 24), 30), 24)
        stroke(d, bez((mx, my - 24), (mx + 30, my - 46), (mx + 82, my - 6), 30), 24)
    if p['sweat']:
        sx, sy = cx + 188, cy - 10
        drop = [(sx + 19 * math.sin(a) * (1 - math.cos(a)) * .75, sy - 26 * math.cos(a)) for a in np.linspace(0, 2 * math.pi, 40)]
        inked(d, drop, (150, 214, 240, 255), 5)


def dashes(d, a, b, n=9, w=4):
    for k in range(n):
        t0, t1 = k / n + .012, (k + .55) / n
        stroke(d, [(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t) for t in np.linspace(t0, t1, 6)], w, STITCH, amp=0)


def rrect(d, x0, y0, x1, y1, r, fill, outline, w):
    d.rounded_rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], r * SS, fill=fill, outline=outline, width=w * SS)


def torso_art(d, im, p, tx, ty, back):
    """Egg torso, wider below: vest, stitched suspenders with gold buckles, two big buttons, pockets, polka-dot bandana, grey trousers."""
    tw, th = TOR_W, TOR_H
    body = blob(tx, ty, tw / 2, th / 2, amp=.003, seed=5, sq=2.3, belly=.22)
    inked(d, body, BACK if back else TEAL, 17)
    # trousers: clipped to the egg
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    poly(ld, [q for q in body if q[1] > ty + th * .27], PANTS)
    stroke(ld, [(tx - tw * .55 + t, ty + th * .27 + 3) for t in range(0, int(tw * 1.1), 4)], 8, INK, amp=0)
    mask = Image.new('L', im.size, 0)
    ImageDraw.Draw(mask).polygon([(x * SS, y * SS) for x, y in body], fill=255)
    lay.putalpha(Image.fromarray((np.asarray(lay)[..., 3] * (np.asarray(mask) / 255)).astype(np.uint8)))
    im.alpha_composite(lay)
    if back:
        stroke(d, [(tx, ty - th * .42 + t) for t in range(0, int(th * .68), 4)], 6, TEAL_D)
        for sx0, sx1 in ((-16, -74), (16, 74)):
            a, b = (tx + sx0, ty - th * .46), (tx + sx1, ty + th * .25)
            stroke(d, [(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t) for t in np.linspace(0, 1, 90)], 31, (54, 40, 40, 255), amp=.02)
            dashes(d, a, b)
        return
    # seam, pockets
    stroke(d, [(tx + 4, ty - th * .3 + t) for t in range(0, int(th * .56), 4)], 5, TEAL_D, amp=0)
    rrect(d, tx - 108, ty - 10, tx - 66, ty + 62, 5, TEAL_L, TEAL_D, 5)
    rrect(d, tx + 74, ty - 118, tx + 112, ty - 54, 5, TEAL_L, TEAL_D, 5)
    # suspenders with white stitching, gold buckles top and bottom
    for sx0, sx1 in ((-44, -66), (44, 72)):
        a, b = (tx + sx0, ty - th * .47), (tx + sx1, ty + th * .25)
        stroke(d, [(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t) for t in np.linspace(0, 1, 90)], 31, (54, 40, 40, 255), amp=.02)
        dashes(d, a, b)
        for bx, by in ((tx + sx0 + (sx1 - sx0) * .1, ty - th * .41), (b[0], b[1])):
            rrect(d, bx - 20, by - 16, bx + 20, by + 16, 3, GOLD, INK, 5)
            rrect(d, bx - 8, by - 6, bx + 8, by + 6, 1, (54, 40, 40, 255), None, 1)
    # big four-hole buttons
    for by in (-.12, .17):
        y = ty + th * by
        d.ellipse([(tx - 24) * SS, (y - 24) * SS, (tx + 24) * SS, (y + 24) * SS], fill=(245, 245, 245, 255), outline=INK, width=5 * SS)
        for dx, dy in ((-5, -5), (5, -5), (-5, 5), (5, 5)):
            d.ellipse([(tx + dx - 2.5) * SS, (y + dy - 2.5) * SS, (tx + dx + 2.5) * SS, (y + dy + 2.5) * SS], fill=INK)
    # bandana: big red triangle with white polka dots
    top = ty - th * .5 + 26
    inked(d, [(tx - 82, top), (tx + 82, top), (tx + 4, top + 136)], RED, 8)
    for dy, xs in ((20, (-44, -18, 8, 34)), (44, (-28, -2, 24)), (68, (-14, 12)), (92, (0,))):
        for x in xs:
            d.ellipse([(tx + x - 5.5) * SS, (top + dy - 5.5) * SS, (tx + x + 5.5) * SS, (top + dy + 5.5) * SS], fill=(252, 244, 244, 255))


HEADS, CAPS = {}, {}


def draw(f):
    if not HEADS:
        for v in ('front', 'q_r', 'back'):
            HEADS[v], CAPS[v] = head_art(v), cap_art(v)
    p = pose(f)
    im = Image.new('RGBA', (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    back = p['view'] == 'back'
    tx, ty = CX + p['lean'], TY + p['bob'] * .5
    hip_y = ty + TOR_H * .44
    k = p['knee']
    # legs: thick wires, slightly tapered, short blunt foot
    feet = p.get('feet', ((CX - 170, 0), (CX + 160, 0)))
    hip = p.get('hip', 52)
    for (sx, sd), (fx, lift) in zip(((-hip, 1), (hip, -1)), feet):
        fy = FEET - 8 - lift
        pts = bez((tx + sx, hip_y), (tx + sx + (fx - tx - sx) * .35 + sd * k, (hip_y + fy) / 2), (fx, fy), 90)
        taper(d, pts, 40, 30, seed=sd)
        dr = p.get('toe', sd * -1)
        taper(d, [(fx + dr * t, fy) for t in range(0, 34, 2)], 30, 32)
    # arms: thick single lines to ball hands
    sh_y = ty - 170
    arm = lambda sx, h, b, sd: stroke(d, bez((tx + sx, sh_y), ((tx + sx + h[0]) / 2 + b * sd, (sh_y + h[1]) / 2 + abs(b) * .25), h, 90), 31, seed=sd, amp=.03)
    if back:
        arm(-105, p['hand_l'], p['bend_l'], 1)
    torso_art(d, im, p, tx, ty, back)
    d = ImageDraw.Draw(im)
    if not back:
        arm(-120, p['hand_l'], p['bend_l'], 1)
    arm(125, p['hand_r'], p['bend_r'], -1)
    for h in (p['hand_l'], p['hand_r']):
        r = 29
        d.ellipse([(h[0] - r) * SS, (h[1] - r) * SS, (h[0] + r) * SS, (h[1] + r) * SS], fill=INK)
    # head layer: rotates as a unit, face decals drawn in it
    hx, hy = tx + 4, ty - TOR_H / 2 + 22 - HEAD_H / 2 + p['bob']
    lay = HEADS[p['view']].copy()
    if not back:
        face(ImageDraw.Draw(lay), p, 380, 380)
    im.alpha_composite(lay.rotate(p['tilt'], Image.BICUBIC), (int((hx - 380) * SS), int((hy - 380) * SS)))
    # cap: its own layer, can hop off the head with a spin
    ta = math.radians(p['tilt'])
    cx, cy = hx - 178 * math.sin(ta), hy - 178 * math.cos(ta) + p['hat_y']
    cl = CAPS[p['view']].rotate(p['tilt'] * 1.15 + p['hat_rot'], Image.BICUBIC)
    qs = p.get('hat_sq', 1.0)
    if qs < 1:
        cl2 = Image.new('RGBA', cl.size, (0, 0, 0, 0))
        hh = max(2, int(cl.size[1] * qs))
        cl2.alpha_composite(cl.resize((cl.size[0], hh), Image.BICUBIC), (0, (cl.size[1] - hh) // 2))
        cl = cl2
    im.alpha_composite(cl, (int((cx - 330) * SS), int((cy - 330) * SS)))
    if SHOT == 'A' and 78 <= f <= 94:
        puffs(im, f)
    if p['star']:
        d = ImageDraw.Draw(im)
        sx, sy, n, s = HIT_XY[0] + 279, HIT_XY[1] + 86, 9, 1 + (f - 78) * .3
        pts = [(sx + (42 if i % 2 else 100) * s * math.cos(i * math.pi / n), sy + (42 if i % 2 else 100) * s * math.sin(i * math.pi / n)) for i in range(2 * n)]
        inked(d, pts, (255, 214, 64, 255), 8)
    # premultiplied downsample so edges don't fringe
    a = np.asarray(im, np.float32) / 255
    a[..., :3] *= a[..., 3:]
    h, w = a.shape[:2]
    a = a[:h // SS * SS, :w // SS * SS].reshape(h // SS, SS, w // SS, SS, 4).mean((1, 3))
    al = np.maximum(a[..., 3:], 1e-4)
    a[..., :3] = np.clip(a[..., :3] / al, 0, 1)
    return f, Image.fromarray((a * 255 + .5).astype(np.uint8), 'RGBA'), p


def job(args):
    f, out = args
    f, im, p = draw(f)
    im.save(Path(out) / f'c_{f:04d}.png', compress_level=1)
    return f


if __name__ == '__main__':
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    fs = [int(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 else list(range(1, NF + 1))
    with Pool(6) as pool:
        for i, f in enumerate(pool.imap_unordered(job, [(f, str(out)) for f in fs])):
            pass
    json.dump({f: dict(hand=pose(f)['hand_r'], rot=pose(f)['ham_rot'], wx=pose(f).get('wx'), wy=pose(f).get('wy'), sq=pose(f).get('sq', 1.0)) for f in range(1, NF + 1)}, open(out / 'pose.json', 'w'))
    print('PUPPET_OK', len(fs))
