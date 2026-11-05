"""Plain-Python helpers for toon_props (no bpy): import from a reel's story.py or from the reel's build script.
  calendar_flip(name, f, f0, n_pages, every=6) -> objs dict for the story state (rotate/hide the calendar pages)
  newspaper_png(reel, name, headline, sub='') -> writes <reel>\\assets\\news_<name>.png (PIL), call before the world is built
  calendar_png(reel, name, pages, year, days, start) -> <reel>\\assets\\cal_<name>_<i>.png period pages for calendar(..., period=True)
  age_paper(im, seed) -> old-paper grain, stain and worn edges on any printed PIL texture"""
import math
import random
from pathlib import Path

ANTON = str(Path(__file__).resolve().parents[2] / 'assets' / 'brand' / 'fonts' / 'Anton-Regular.ttf')


def _ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def calendar_flip(name, f, f0, n_pages, every=6, dur=None):
    """objs dict for story state: `objs=calendar_flip('cal', f, 40, 3)`. Page i (front one is p0) flips up and over the top (rot x 0 -> -180)
    over `dur` frames (default min(every, 8)) starting at f0 + i*every; once flipped it is hidden. The last page never flips."""
    dur = dur or min(every, 8)
    out = {}
    for i in range(n_pages):
        t = 0.0 if i == n_pages - 1 else _ease((f - (f0 + i * every)) / dur)
        deg = -180.0 * t
        out[f'{name}_p{i}'] = dict(rot=(deg, 0, 0), show=t < .999)
    return out


def _wrap(draw, text, font, maxw):
    words, lines, cur = text.split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if draw.textlength(t, font=font) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def newspaper_png(reel, name, headline, sub='', paper='#efe6cf', ink='#16130f', masthead='THE MORNING LEDGER', size=(1200, 1560)):
    """Front page texture: masthead, rule lines, big Anton headline, sub-head, photo block, fake column lines. Returns the path written."""
    from PIL import Image, ImageDraw, ImageFont
    W, H = size
    im = Image.new('RGB', size, paper)
    d = ImageDraw.Draw(im)
    rnd = random.Random(sum(map(ord, name)))
    F = lambda s: ImageFont.truetype(ANTON, s)
    m = 60
    mf = F(112)
    d.text((W / 2, 120), masthead, font=mf, fill=ink, anchor='mm')
    d.rectangle([m, 200, W - m, 208], fill=ink)
    d.rectangle([m, 216, W - m, 220], fill=ink)
    d.text((m, 250), 'LATE EDITION', font=F(34), fill=ink, anchor='lm')
    d.text((W - m, 250), 'PRICE 2 COINS', font=F(34), fill=ink, anchor='rm')
    d.rectangle([m, 280, W - m, 284], fill=ink)
    hs = 150
    while True:
        hf = F(hs)
        lines = _wrap(d, headline.upper(), hf, W - 2 * m)
        if len(lines) <= 3 or hs <= 80:
            break
        hs -= 8
    y = 300
    for ln in lines:
        d.text((W / 2, y), ln, font=hf, fill=ink, anchor='ma')
        y += int(hs * 1.1)
    y += 6
    if sub:
        sf = F(48)
        for ln in _wrap(d, sub, sf, W - 2 * m)[:2]:
            d.text((W / 2, y), ln, font=sf, fill='#3a342b', anchor='ma')
            y += 60
    y += 14
    d.rectangle([m, y, W - m, y + 4], fill=ink)
    y += 24
    # photo block with halftone-ish look
    ph_h = 340
    d.rectangle([m, y, m + 520, y + ph_h], fill='#8f8a7e')
    for k in range(0, 520, 14):
        d.line([m + k, y, m, y + k * ph_h // 520], fill='#76726a', width=3)
    d.ellipse([m + 170, y + 70, m + 350, y + 250], fill='#4f4c46')
    d.rectangle([m + 110, y + 230, m + 410, y + ph_h], fill='#4f4c46')
    d.text((m, y + ph_h + 8), 'FILE PHOTO', font=F(26), fill='#3a342b', anchor='la')
    # fake text beside the photo and below, in 3 columns
    colw = (W - 2 * m - 2 * 30) // 3

    def cols(x0, y0, x1, y1, step=18):
        yy = y0
        while yy < y1:
            n = rnd.choice((0, 0, 0, 1))
            w = x1 - x0 - (rnd.randint(30, 160) if rnd.random() < .18 else 0)
            d.rectangle([x0, yy, x0 + w, yy + 7], fill='#5a5348')
            yy += step * (2.4 if n else 1)
        return

    cols(m + 550, y, W - m, y + ph_h)
    y += ph_h + 50
    for c in range(3):
        x0 = m + c * (colw + 30)
        d.rectangle([x0, y, x0 + colw, y + 34], fill=ink)
        d.text((x0 + 10, y + 17), rnd.choice(('MARKETS', 'OPINION', 'CITY NEWS', 'WORLD', 'BUSINESS')), font=F(26), fill=paper, anchor='lm')
        cols(x0, y + 50, x0 + colw, H - 50)
        if c < 2:
            d.line([x0 + colw + 15, y, x0 + colw + 15, H - 50], fill='#5a5348', width=2)
    out = Path(reel) / 'assets'
    out.mkdir(parents=True, exist_ok=True)
    p = out / f'news_{name}.png'
    age_paper(im, sum(map(ord, name))).save(p)
    return p


FONT_DIR = Path(ANTON).parent


def pfont(face, size, weight=None):
    """PIL font from the brand folder: face = file name ('PlayfairDisplay.ttf', 'SpecialElite-Regular.ttf' ...); weight for variable fonts."""
    from PIL import ImageFont
    f = ImageFont.truetype(str(FONT_DIR / face), size)
    if weight:
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
    return f


def age_paper(im, seed=1, grime=1.0):
    """Old paper on a printed texture: fibre grain, a soft tea stain, darker worn edges and slightly lifted ink. Returns the new image."""
    from PIL import Image, ImageFilter, ImageChops
    W, H = im.size
    rnd = random.Random(seed)
    n = Image.effect_noise((W // 4, H // 4), 40).resize((W, H), Image.BICUBIC)
    g = Image.effect_noise((W, H), 18)
    blot = Image.new('L', (W, H), 255)
    from PIL import ImageDraw
    d = ImageDraw.Draw(blot)
    for _ in range(4):
        x, y, r = rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(.12, .3) * W
        d.ellipse([x - r, y - r, x + r, y + r], fill=int(255 - 18 * grime))
    blot = blot.filter(ImageFilter.GaussianBlur(W * .06))
    edge = Image.new('L', (W, H), 0)
    ImageDraw.Draw(edge).rectangle([W * .03, H * .03, W * .97, H * .97], fill=255)
    edge = edge.filter(ImageFilter.GaussianBlur(W * .04)).point(lambda v: int(255 - (255 - v) * .22 * grime))
    shade = ImageChops.multiply(ImageChops.multiply(blot, edge), n.point(lambda v: int(255 - (255 - v) * .12 * grime)))
    shade = ImageChops.multiply(shade, g.point(lambda v: int(255 - (255 - v) * .1 * grime)))
    tint = Image.merge('RGB', (shade, shade.point(lambda v: int(v * .985)), shade.point(lambda v: int(v * .95))))
    out = ImageChops.multiply(im.convert('RGB'), tint)
    return out.filter(ImageFilter.GaussianBlur(.6))  # ink sits in the paper, not on top


def calendar_png(reel, name, pages, year='', days=(31,), start=(0,), top='ALMANAC', paper='#f1e4c3', ink='#241a12', red='#8c2a1c', size=(1000, 1300)):
    """Period wall-calendar pages printed like old newsprint (top line in typewriter, serif month masthead, double rules, typewriter weekdays,
    serif dates on a ruled grid, fine print footer, aged paper). pages = month names; writes <reel>\\assets\\cal_<name>_<i>.png per page and returns the paths.
    calendar(..., period=True) puts them on lit, curled sheets."""
    from PIL import Image, ImageDraw
    W, H = size
    m = 56
    out = Path(reel) / 'assets'
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, mo in enumerate(pages):
        rnd = random.Random(sum(map(ord, name + mo)))
        im = Image.new('RGB', size, paper)
        d = ImageDraw.Draw(im)
        d.text((W / 2, 60), top, font=pfont('SpecialElite-Regular.ttf', 30), fill=ink, anchor='mm')
        d.rectangle([m, 92, W - m, 97], fill=ink)
        d.rectangle([m, 103, W - m, 105], fill=ink)
        d.text((W / 2, 205), mo.title() if len(mo) > 3 else mo, font=pfont('PlayfairDisplay.ttf', 150, 800), fill=ink, anchor='mm')
        if year:
            d.text((W / 2, 318), str(year), font=pfont('PlayfairDisplay.ttf', 64, 600), fill=red, anchor='mm')
        y0 = 370
        d.rectangle([m, y0, W - m, y0 + 4], fill=ink)
        cw = (W - 2 * m) / 7
        for c, dn in enumerate(('SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT')):
            d.text((m + cw * (c + .5), y0 + 42), dn, font=pfont('SpecialElite-Regular.ttf', 34), fill=red if c == 0 else ink, anchor='mm')
        y1 = y0 + 78
        d.rectangle([m, y1, W - m, y1 + 2], fill=ink)
        nd, st = days[i % len(days)], start[i % len(start)]
        rows = (nd + st + 6) // 7
        rh = (H - 150 - y1) / rows
        nf = pfont('PlayfairDisplay.ttf', int(min(86, rh * .62)), 700)
        for r in range(1, rows + 1):
            d.line([m, y1 + r * rh, W - m, y1 + r * rh], fill='#6b5c48', width=2)
        for c in range(1, 7):
            d.line([m + c * cw, y1, m + c * cw, y1 + rows * rh], fill='#6b5c48', width=2)
        for k in range(nd):
            r, c = divmod(k + st, 7)
            d.text((m + cw * (c + .5), y1 + rh * (r + .5)), str(k + 1), font=nf, fill=red if c == 0 else ink, anchor='mm')
        fy = H - 110
        d.rectangle([m, fy, W - m, fy + 3], fill=ink)
        for k in range(3):  # fine print, too small to read, like the reference's footer
            w = W - 2 * m - rnd.randint(0, 220)
            d.rectangle([m, fy + 22 + k * 20, m + w, fy + 29 + k * 20], fill='#6b5c48')
        p = out / f'cal_{name}_{i}.png'
        age_paper(im, sum(map(ord, name)) + i).save(p)
        paths.append(p)
    return paths
