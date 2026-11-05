"""Join shots (6 f dissolves, whips from story.WHIPS), per-frame grade from story.GRADE, watermark, hard-swap word captions, audio.
python toon_compose.py <reel> <frames dir> <out.mp4> --audio <wav|m4a> [--words voice_words.json] [--no-captions]
No voice file yet: the video gets a silent track."""
import json
import os
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path[:0] = [str(Path(__file__).parent)]
from toon_grade import apply as apply_finish, gain_for, resolve  # noqa: E402
from toon_joins import join  # noqa: E402
from toon_story import load_story  # noqa: E402

BRAND = str(Path(__file__).resolve().parents[2] / 'assets' / 'brand' / 'logo.png')
CAP_FONT = r'C:\Windows\Fonts\ariblk.ttf'
CAP_SIZE, CAP_Y, CAP_MAXW, CAP_WORDS, CAP_GAP = 56, .7, .88, 2, .18
CAP_FONT_V2 = str(Path(__file__).resolve().parents[2] / 'assets' / 'brand' / 'fonts' / 'Poppins-Bold.ttf')
CAP_SIZE_V2, CAP_STROKE_V2 = 66, 8  # the study's "something" = 387 px wide at 1080
WM_W, WM_ALPHA, WM_RIGHT, WM_TOP = .12, .7, .04, .075
FPS, CRF = 30, 17

a = sys.argv[1:]
REEL, FR, OUT = Path(a[0]), Path(a[1]), a[2]
opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
CAPS, BRANDING = '--no-captions' not in a, True
_UI = Path(__file__).resolve().parent / 'assets' / 'ui'
BRAND = str(_UI / 'paper_grain_03.png')
STING = 30  # frames of the end card
TAGS = ['-metadata', 'comment=Made with Beta Version Toon Studio', '-metadata', 'encoded_by=Beta Version Toon Studio']
AUDIO = Path(opt('--audio', ''))
ASRC = ['-i', str(AUDIO)] if AUDIO.is_file() else ['-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo']   # no voice yet: silence
RANGE = opt('--range')  # a:b = one worker's frames, video only
JOBS = int(opt('--jobs', max(1, (os.cpu_count() or 2) - 4)))
S = load_story(REEL)
if not RANGE and JOBS > 1:
    # parent: contiguous frame ranges on JOBS processes, lossless concat, then the audio
    cuts = [S.LEN * i // JOBS for i in range(JOBS + 1)]
    parts = [f'{OUT}.part{i:02d}.mp4' for i in range(JOBS)]
    base = [x for i, x in enumerate(a) if i != 2 and not (i > 0 and a[i - 1] == '--jobs') and x != '--jobs']
    ps = [subprocess.Popen([sys.executable, __file__, base[0], base[1], parts[i], *base[2:], '--range', f'{cuts[i]}:{cuts[i + 1]}'],
                           stdout=subprocess.PIPE, text=True) for i in range(JOBS)]
    bad = sum(int(p.communicate()[0].split()[-1]) for p in ps)
    lst = Path(f'{OUT}.parts.txt')
    lst.write_text(''.join(f"file '{Path(p).resolve().as_posix()}'\n" for p in parts))
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), *ASRC, '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-af', 'apad', '-t', f'{(S.LEN + STING) / FPS}', *TAGS, OUT], check=True)
    for p in parts + [lst]:
        Path(p).unlink()
    print('COMPOSE_OK', S.LEN, 'missing', bad)
    sys.exit()
words = json.load(open(opt('--words', REEL / 'voice_words.json'), encoding='utf-8-sig')) if CAPS else []
sample = next(FR.glob('s00_*.png'))
W0, H0 = Image.open(sample).size
W, H = W0 // 2 * 2, H0 // 2 * 2
CAP_V2 = getattr(S, 'CAPTION', 'v2') != 'v1'
font = ImageFont.truetype(CAP_FONT_V2 if CAP_V2 else CAP_FONT, int((CAP_SIZE_V2 if CAP_V2 else CAP_SIZE) * W / 1080))
stroke = max(2, int((CAP_STROKE_V2 if CAP_V2 else 7) * W / 1080))
# caption chunks: at most CAP_WORDS words, a new chunk at any pause or line change
chunks, cur = [], []
for w in words:
    if cur and (len(cur) == CAP_WORDS or w['start'] - cur[-1]['end'] > CAP_GAP or w['line'] != cur[-1]['line']):
        chunks.append(cur)
        cur = []
    cur.append(w)
if cur:
    chunks.append(cur)
merged = []
for c in chunks:
    if merged and int(merged[-1][-1]['end'] * FPS) - int(merged[-1][0]['start'] * FPS) < 10 and merged[-1][0]['line'] == c[0]['line']:
        merged[-1] = merged[-1] + c
    else:
        merged.append(c)
chunks = []
for c in merged:
    if len(c) <= 2:
        chunks.append(c)
        continue
    t0, t1 = c[0]['start'], c[-1]['end']
    for n in range(0, len(c), 2):
        part = [dict(x) for x in c[n:n + 2]]
        part[0]['start'] = t0 + (t1 - t0) * n / len(c)
        part[-1]['end'] = t0 + (t1 - t0) * min(len(c), n + 2) / len(c)
        chunks.append(part)
spans = []
for i, c in enumerate(chunks):
    s0 = int(c[0]['start'] * FPS)
    b = int(chunks[i + 1][0]['start'] * FPS) if i + 1 < len(chunks) else S.LEN
    b = min(b, int(c[-1]['end'] * FPS) + 8)
    spans.append((s0, b, ' '.join(x['word'] for x in c)))
wm = None
if BRANDING:
    wm = Image.open(BRAND).convert('RGBA')
    ww = int(W * WM_W)
    wm = wm.resize((ww, int(ww * wm.size[1] / wm.size[0])), Image.LANCZOS)
    wm.putalpha(wm.getchannel('A').point(lambda v: int(v * WM_ALPHA)))
    # dark backing keeps the wordmark readable on any wall
    wb = Image.new('RGBA', (wm.size[0] + 20, wm.size[1] + 14), (12, 16, 28, 150))
    wb.alpha_composite(wm, (10, 7))
    wm = wb
    wm_xy = (W - wm.size[0] - int(W * WM_RIGHT), int(H * WM_TOP))
    # faint tiled marks across the whole frame
    mk = Image.open(_UI / 'ink_dot_07.png').convert('RGBA')
    mw = int(W * .16)
    mk = mk.resize((mw, int(mw * mk.size[1] / mk.size[0])), Image.LANCZOS)
    mk.putalpha(mk.getchannel('A').point(lambda v: v * 9 // 255))
    tile = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for yy in range(0, H, int(H * .2)):
        for xx in range(-mw // 2 if (yy // int(H * .2)) % 2 else 0, W, int(W * .34)):
            tile.alpha_composite(mk, (max(0, xx), yy))
    wm_tile = tile
cache = {}
CAP_CACHE = {}


def caption(t):
    """Hard-swap caption as a full-frame layer. v2 (default) is the studied look: Poppins Bold, soft drop shadow."""
    if t in CAP_CACHE:
        return CAP_CACHE[t]
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    lines, cur_ = [], ''
    for w_ in t.split():
        if cur_ and d.textlength(cur_ + ' ' + w_, font=font) + 2 * stroke > W * CAP_MAXW:
            lines.append(cur_)
            cur_ = w_
        else:
            cur_ = (cur_ + ' ' + w_).strip()
    lines.append(cur_)
    place = [(W / 2, H * CAP_Y + (n_ - (len(lines) - 1) / 2) * font.size * 1.1, l_) for n_, l_ in enumerate(lines)]
    if CAP_V2:
        sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ds = ImageDraw.Draw(sh)
        off = 5 * W / 1080
        for x, y, l_ in place:
            ds.text((x, y + off), l_, font=font, fill=(0, 0, 0, 105), stroke_width=stroke, stroke_fill=(0, 0, 0, 105), anchor='mm')
        lay = sh.filter(ImageFilter.GaussianBlur(3 * W / 1080))
        d = ImageDraw.Draw(lay)
    for x, y, l_ in place:
        d.text((x, y), l_, font=font, fill=(255, 255, 255, 255), stroke_width=stroke, stroke_fill=(24, 18, 30, 255) if not CAP_V2 else (0, 0, 0, 255), anchor='mm')
    if len(CAP_CACHE) > 400:
        CAP_CACHE.clear()
    CAP_CACHE[t] = lay
    return lay


def blend(b, p, q, f):
    """The join at boundary b, frame f: L frames centred on b."""
    j = dict(S.join_of(b), _reel=REEL)
    L = j['len']
    return join(j, p, q, (f - (b - L // 2) + .5) / L, W, H)


def glow(a, amt):
    """Bloom: bright parts bleed light outward."""
    lum = a.max(2)
    hot = np.clip((lum - 222) / 33, 0, 1)[..., None] * a  # only lamps and highlights; cream walls must not wash out
    im = Image.fromarray(hot.astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(10)).resize((W, H), Image.BILINEAR)
    return np.clip(a + np.asarray(im, np.float32) * amt, 0, 255)


def lens(a, l):
    """Magnifier: a gold ring with a scaled copy of the frame inside it, a real lens on a flat prop. LENSES=[dict(a,b,x,y,r,zoom,[sx,sy])], fractions of width/height; r of width."""
    pop = min(1, (f - l['a'] + 1) / 5, (l['b'] - f) / 4)
    r = l['r'] * W * max(0, pop)
    if r < 2:
        return a
    cx, cy = l['x'] * W, l['y'] * H
    sx, sy = l.get('sx', l['x']) * W, l.get('sy', l['y']) * H
    z = l.get('zoom', 1.8)
    yy, xx = np.ogrid[0:H, 0:W]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    x0, y0, x1, y1 = int(max(0, cx - r - 30)), int(max(0, cy - r - 30)), int(min(W, cx + r + 30)), int(min(H, cy + r + 30))
    mx = np.clip(((np.arange(x0, x1) - cx) / z + sx).astype(int), 0, W - 1)
    my = np.clip(((np.arange(y0, y1) - cy) / z + sy).astype(int), 0, H - 1)
    out = a.copy()
    inner = np.clip(r - d[y0:y1, x0:x1], 0, 1)[..., None]
    region = a[np.ix_(my, mx)]
    out[y0:y1, x0:x1] = out[y0:y1, x0:x1] * (1 - inner) + (region * .94 + 15) * inner
    w = r * .1
    ring = np.clip(1 - np.abs(d[y0:y1, x0:x1] - r - w / 2) / (w / 2), 0, 1)[..., None]
    ink = np.clip(1 - np.abs(d[y0:y1, x0:x1] - r - w / 2) / (w / 2 + 5), 0, 1)[..., None]
    out[y0:y1, x0:x1] = out[y0:y1, x0:x1] * (1 - ink) + np.array((24, 18, 30), np.float32) * ink
    out[y0:y1, x0:x1] = out[y0:y1, x0:x1] * (1 - ring) + np.array((232, 186, 70), np.float32) * ring
    return out


def graded(img, f):
    r, g, b, sat = S.grade_at(f)
    r, g, b, sat = r * .86, g * .86, b * .88, sat * .8  # Studio edition: dimmer, flatter colour
    out = img * np.array((r, g, b), np.float32)
    lum = out @ np.array((.3, .59, .11), np.float32)
    return np.clip(lum[..., None] + (out - lum[..., None]) * sat, 0, 255)


GAINS, FORES = {}, {}


def finish_of(k):
    """FINISH on the story, shot key finish= overrides. Old reels have neither and stay as they were."""
    return resolve(S.state(k, S.SHOTS[k][1]).get('finish', getattr(S, 'FINISH', None)))


def fore_layer(d):
    """Near out-of-focus shape in front of everything: dark, soft, drawn once per shot. kind post|shoulder|foliage|rail|crate or a png path; side -1 left, 1 right; w = share of frame width."""
    pad = int(W * .25)
    lay = Image.new('RGBA', (W + 2 * pad, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(lay)
    kind, side, ww, col = d.get('kind', 'post'), d.get('side', 1), d.get('w', .2) * W, tuple(d.get('col', (16, 14, 28))) + (255,)
    x0 = W + 2 * pad - pad - ww if side > 0 else pad
    x1 = x0 + ww
    if kind == 'post':
        dr.rectangle((x0, -9, x1, H + 9), fill=col)
    elif kind == 'shoulder':
        cx = x1 if side > 0 else x0
        dr.ellipse((cx - ww * 1.5, H * .62, cx + ww * 1.5, H * 1.25), fill=col)
        dr.ellipse((cx - ww * .62, H * .42, cx + ww * .62, H * .72), fill=col)
    elif kind == 'foliage':
        r = random.Random(d.get('seed', 3))
        for _ in range(26):
            cx, cy, rr = r.uniform(x0, x1), r.uniform(0, H * .36), r.uniform(.25, .6) * ww
            dr.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=col)
    elif kind == 'rail':
        y = H * d.get('y', .95)
        dr.rectangle((0, y, W + 2 * pad, H), fill=col)
        for x in range(0, W + 2 * pad, int(W * .42)):
            dr.rectangle((x, y - H * .1, x + W * .05, y), fill=col)
        dr.rounded_rectangle((-9, y - H * .115, W + 2 * pad + 9, y - H * .09), 9, fill=col)
    elif kind == 'crate':
        dr.rounded_rectangle((x0, H * .8, x1, H + 40), 14, fill=col)
    else:
        pic = Image.open(kind).convert('RGBA')
        pic = pic.resize((int(ww), int(ww * pic.height / pic.width)), Image.LANCZOS)
        lay.alpha_composite(pic, (int(x0), H - pic.height))
    return np.asarray(lay.filter(ImageFilter.GaussianBlur(d.get('blur', .012) * W)), np.float32), pad


def with_fore(a, k, f):
    d = S.state(k, f).get('fore')
    if not d:
        return a
    if k not in FORES:
        FORES[k] = fore_layer(d)
    lay, pad = FORES[k]
    s0, b = S.SHOTS[k][1:]
    x = int(pad + d.get('drift', .08) * W * ((f - s0) / max(1, b - s0) - .5))
    part = lay[:, x:x + W]
    al = part[..., 3:] / 255 * d.get('alpha', 1)
    return a * (1 - al) + part[..., :3] * al


def rd(k, f):
    p = FR / f's{k:02d}_{f:04d}.png'
    if p not in cache:
        if len(cache) > 8:
            cache.clear()
        a_ = with_fore(np.asarray(Image.open(p).convert('RGB').crop((0, 0, W, H)), np.float32), k, f)
        g_ = finish_of(k)
        if g_ and k not in GAINS:
            # gain from the shot's first frame the serial pass would read, so every worker grades a shot the same
            s0 = S.SHOTS[k][1]
            f0 = s0 - S.join_of(s0)['len'] // 2 if k else 0
            p0 = FR / f's{k:02d}_{f0:04d}.png'
            a0 = a_ if p0 == p else with_fore(np.asarray(Image.open(p0).convert('RGB').crop((0, 0, W, H)), np.float32), k, f0)
            GAINS[k] = gain_for(a0, g_)
        if g_:
            a_ = apply_finish(a_, g_, GAINS[k])
        cache[p] = a_
    return cache[p]


F0, F1 = map(int, RANGE.split(':')) if RANGE else (0, S.LEN)
src = ASRC if not RANGE else []
enc = ['-c:a', 'aac', '-b:a', '192k', '-af', 'apad', '-t', f'{(S.LEN + STING) / FPS}', *TAGS] if not RANGE else ['-an', '-threads', '2']
ff = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', *src,
                       '-c:v', 'libx264', '-crf', str(CRF), '-preset', 'medium', '-pix_fmt', 'yuv420p', *enc, OUT], stdin=subprocess.PIPE)
bad = 0
for f in range(F0, F1):
    k = next(i for i, (_, s0, b) in enumerate(S.SHOTS) if s0 <= f < b or i == len(S.SHOTS) - 1)
    s0, b = S.SHOTS[k][1:]
    L_b = S.join_of(b)['len'] if k + 1 < len(S.SHOTS) else 0
    L_a = S.join_of(s0)['len'] if k else 0
    try:
        img = rd(k, f)
        if k + 1 < len(S.SHOTS) and f >= b - L_b // 2:
            img = blend(b, img, rd(k + 1, f), f)
        elif k > 0 and f < s0 + (L_a - L_a // 2):
            img = blend(s0, rd(k - 1, f), img, f)
    except FileNotFoundError:
        bad += 1
        continue
    arr = graded(img, f)
    for l_ in getattr(S, 'LENSES', ()):
        if l_['a'] <= f < l_['b']:
            arr = lens(arr, l_)
    if getattr(S, 'BLOOM', 0):
        arr = glow(arr, S.BLOOM)
    im = Image.fromarray(arr.astype(np.uint8)).convert('RGBA')
    if wm:
        im.alpha_composite(wm_tile)
        im.alpha_composite(wm, wm_xy)
    if CAPS:
        for x, y, t in spans:
            if x <= f < y:
                im.alpha_composite(caption(t))
                break
    ff.stdin.write(im.convert('RGB').tobytes())
if F1 == S.LEN:  # end card: Made with Beta Version
    card = Image.new('RGB', (W, H), (8, 10, 16))
    lg = Image.open(BRAND).convert('RGBA')
    lw = int(W * .6)
    lg = lg.resize((lw, int(lw * lg.size[1] / lg.size[0])), Image.LANCZOS)
    card.paste(lg, ((W - lw) // 2, int(H * .44) - lg.size[1] // 2), lg)
    dc = ImageDraw.Draw(card)
    fnt = ImageFont.truetype(CAP_FONT_V2, int(40 * W / 1080))
    dc.text((W / 2, H * .44 + lg.size[1] / 2 + 60 * W / 1080), 'MADE WITH BETA VERSION TOON STUDIO', font=fnt, fill=(200, 210, 225), anchor='mm')
    for i in range(STING):
        u = min(1, (i + 1) / 6)
        ff.stdin.write(Image.blend(Image.new('RGB', (W, H)), card, u).tobytes())
ff.stdin.close()
ff.wait()
print('COMPOSE_OK', S.LEN, 'missing', bad)

