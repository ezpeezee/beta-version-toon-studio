"""Cast for toon reels on the approved puppet engine: 7 characters, held props, flat FX. A reel can add/override characters (story.CAST) and prop text (story.PROP_TEXT) via configure(S)."""
import math
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

os.environ.setdefault('SHOT', 'A')
os.environ.setdefault('CAST', 'H')
sys.path.insert(0, str(Path(__file__).parent))
import toon_fx as FX  # noqa: E402
import toon_puppet as P  # noqa: E402
from toon_roles import ROLES, ROLE_PROPS, TOP_HATS, costume, hat_art, role_prop, skirt  # noqa: E402

BRAND = str(Path(__file__).resolve().parents[2] / 'assets' / 'brand' / 'logo.png')
ANTON = str(Path(__file__).resolve().parents[2] / 'assets' / 'brand' / 'fonts' / 'Anton-Regular.ttf')
PROP_TEXT = dict(drive=('DATA', 'DRIVE'), clipboard='FORM', label='LABEL')
_MK = str(Path(__file__).resolve().parent / 'assets' / 'ui' / 'ink_dot_07.png')
_TINTS = [((46, 120, 196), (86, 150, 216), (28, 84, 150), (40, 104, 170)), ((222, 118, 66), (240, 150, 96), (168, 80, 44), (196, 100, 56)),
          ((130, 96, 196), (160, 130, 220), (92, 66, 148), (112, 82, 172)), ((70, 150, 90), (100, 180, 120), (40, 100, 60), (56, 124, 74)),
          ((200, 70, 80), (226, 104, 110), (150, 44, 54), (176, 58, 66))]
SS, W, H, INK = P.SS, P.W, P.H, P.INK
A = (255,)
CAST = {
    'H': dict(style='vest'),
    'E1': dict(style='vest', vest=((222, 118, 66), (240, 150, 96), (168, 80, 44), (196, 100, 56)), hair=(52, 40, 40), cap=((170, 44, 60), (246, 226, 214), (90, 24, 36))),
    'E2': dict(style='vest', vest=((130, 96, 196), (160, 130, 220), (92, 66, 148), (112, 82, 172)), hair=(30, 28, 40), cap=((226, 164, 48), (70, 50, 40), (120, 84, 24))),
    'B': dict(style='suit', suit=(38, 56, 104), tie=(206, 40, 58), hair=(120, 116, 118), tor=(340, 400), cap=None),
    'S': dict(style='suit', suit=(70, 74, 86), tie=(44, 110, 190), hair=(26, 24, 30), tor=(300, 420), cap=None, glasses=True),
    'P': dict(style='cardigan', hair=(176, 178, 188), tor=(300, 400), cap=None, bald=True, beard=True),
    'M': dict(style='vest', vest=((46, 120, 196), (86, 150, 216), (28, 84, 150), (40, 104, 170)), hair=(88, 56, 36), cap=((46, 120, 196), (235, 240, 250), (24, 50, 96))),
}
CAST.update(ROLES)
HEADS, CAPS, HATS, FONT_C, SPRITES = {}, {}, {}, {}, {}


def font(s):
    if s not in FONT_C:
        FONT_C[s] = ImageFont.truetype(ANTON, s * SS)
    return FONT_C[s]


def hair_on(im, pts, c, mask, jag_from):
    """Wedge and its ink edge both clipped to the head, so no tick sticks out past the outline."""
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
    abs_pts = [(c + x, c + y) for x, y in pts]
    P.poly(ImageDraw.Draw(lay), abs_pts, P.HAIR)
    d = ImageDraw.Draw(lay)
    edge = abs_pts[1:jag_from]
    for a, b in zip(edge, edge[1:]):
        P.stroke(d, [(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t) for t in np.linspace(0, 1, 24)], 11, amp=.03)
    lay.putalpha(Image.fromarray((np.asarray(lay)[..., 3] * (np.asarray(mask) / 255)).astype(np.uint8)))
    im.alpha_composite(lay)


P.hair_on = hair_on
TUFT_L = [(-262, -46), (-262, 46), (-228, 40), (-218, -46)]
TUFT_R = [(262, -46), (262, 46), (228, 40), (218, -46)]


SIDE_L = [(-266, -170), (-266, 40), (-236, 74), (-208, 44), (-196, -30), (-150, -170)]
SIDE_R = [(-x, y) for x, y in SIDE_L]


FRINGE_F = [(-262, -215), (-262, 40), (-214, 70), (-190, 0), (-120, -50), (-30, -95), (60, -118), (150, -100), (262, -90), (262, -215)]
FRINGE_Q = [(-262, -215), (-262, 20), (-214, 52), (-150, -8), (-70, -52), (10, -92), (110, -118), (262, -118), (262, -215)]
BOB_L = [(-210, -140), (-268, -60), (-300, 40), (-298, 150), (-278, 232), (-236, 248), (-196, 226), (-178, 170), (-186, 110)]
LONG_L = [(-200, -150), (-262, -80), (-300, 20), (-310, 140), (-300, 250), (-288, 332), (-252, 358), (-218, 336), (-196, 352), (-168, 300), (-176, 200), (-190, 120)]


def _seg_pts(pts, closed=True):
    out = []
    n = len(pts)
    for i in range(n if closed else n - 1):
        a, b = pts[i], pts[(i + 1) % n]
        out += [(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t) for t in np.linspace(0, 1, 18, endpoint=False)]
    return out


def hair_piece(im, pts, edge=None, c=380):
    """Hair shape: flat fill plus the hair's 11 px ink on its outer edge only (edge=(i0, i1) stroke pts[i0..i1]; default all round)."""
    d = ImageDraw.Draw(im)
    ab = [(c + x, c + y) for x, y in pts]
    P.poly(d, ab, P.HAIR)
    es = ab if edge is None else ab[edge[0]:edge[1] + 1]
    P.stroke(d, _seg_pts(es, edge is None), 11, amp=.03)


def ribbon(path, w0, w1):
    n = len(path)
    L, R = [], []
    for i, (x, y) in enumerate(path):
        a, b = path[min(n - 1, i + 1)], path[max(0, i - 1)]
        dx, dy = a[0] - b[0], a[1] - b[1]
        ln = math.hypot(dx, dy) or 1
        w = (w0 + (w1 - w0) * i / (n - 1)) / 2
        L.append((x - dy / ln * w, y + dx / ln * w))
        R.append((x + dy / ln * w, y - dx / ln * w))
    return L + R[::-1]


def add_hair(im, c, view, style):
    """Women's hair around a finished head layer (long | bob | bun | ponytail): pieces behind the head, plus pieces over the back view."""
    hat_top = c.get('hat') in TOP_HATS
    behind = Image.new('RGBA', im.size, (0, 0, 0, 0))
    front = Image.new('RGBA', im.size, (0, 0, 0, 0))
    q = view == 'q_r'
    if style in ('long', 'bob') and view != 'back':
        lk = LONG_L if style == 'long' else BOB_L
        left = [(x - (14 if q else 0), y) for x, y in lk]
        if q:
            right = [(-x * .5 - 30, y * .72) for x, y in reversed(lk)]
        else:
            right = [(-x, y - (12 if i % 3 == 0 else 0)) for i, (x, y) in enumerate(reversed(lk))]
        hair_piece(behind, left)
        hair_piece(behind, right)
    elif style in ('long', 'bob') and view == 'back':
        bot = 330 if style == 'long' else 236
        pts = [(-262, -10), (-296, 60), (-304, bot * .5), (-290, bot - 30), (-250, bot), (-200, bot - 22), (-140, bot + 6), (-70, bot - 18), (0, bot + 8), (70, bot - 18), (140, bot + 6), (200, bot - 22), (250, bot),
               (290, bot - 30), (304, bot * .5), (296, 60), (262, -10)]
        hair_piece(front, pts, (0, len(pts) - 1))
    elif style == 'ponytail':
        if view == 'front':
            path = P.bez((120, -150), (380, -190), (310, 130), 36)
            hair_piece(behind, ribbon(path, 84, 30))
        elif q:
            path = P.bez((-110, -150), (-350, -170), (-296, 140), 36)
            hair_piece(behind, ribbon(path, 90, 30))
        else:
            path = P.bez((0, -140), (30, 40), (-6, 270), 36)
            hair_piece(front, ribbon(path, 96, 34))
            ImageDraw.Draw(front).ellipse([(380 - 56) * SS, (380 - 150) * SS, (380 + 56) * SS, (380 - 96) * SS], fill=(214, 70, 100, 255), outline=INK, width=5 * SS)
    elif style == 'bun':
        if view == 'back':
            by_ = 150 if hat_top else -225
            tgt = front
        else:
            by_ = None if hat_top else -228
            tgt = behind
        if by_ is not None:
            bx = -70 if q else 0
            ball = P.blob(380 + bx, 380 + by_, 74, 66, amp=.004, seed=3, sq=2.1)
            hair_piece(tgt, [(x - 380, y - 380) for x, y in ball])
            P.stroke(ImageDraw.Draw(tgt), P.bez((380 + bx - 36, 380 + by_ - 10), (380 + bx, 380 + by_ - 44), (380 + bx + 38, 380 + by_ + 6), 20), 6, amp=0)
    out = Image.new('RGBA', im.size, (0, 0, 0, 0))
    out.alpha_composite(behind)
    out.alpha_composite(im)
    out.alpha_composite(front)
    return out


def lashes(ld, p, lk):
    """2-3 short ink ticks at each eye's outer corner (women)."""
    ey = 398
    dx, dy = {'ring': (40, -20), 'dot': (15, -15), 'happy': (35, 8), 'shut': (37, 2), 'slit': (34, 2)}.get(p['eyes'], (33, 1))
    for ex, sg in ((320 + lk, -1), (450 + lk, 1)):
        x0, y0 = ex + sg * dx, ey + dy
        for ang, ln in ((10, 26), (40, 28), (70, 24)):
            a = math.radians(ang)
            P.stroke(ld, [(x0 + sg * math.cos(a) * ln * t / 6, y0 - math.sin(a) * ln * t / 6) for t in range(7)], 8, amp=0)


def earrings(ld, c, view):
    colr = tuple(c['earrings']) + A if isinstance(c.get('earrings'), (tuple, list)) else (236, 186, 52, 255)
    xs = (-1, 1) if view != 'q_r' else (-1,)
    for sg in xs:
        x, y = 380 + sg * 246, 380 + 78
        P.stroke(ld, [(x, y - 6 + t * 3) for t in range(5)], 7, amp=0)
        ld.ellipse([(x - 17) * SS, (y + 6) * SS, (x + 17) * SS, (y + 40) * SS], fill=colr, outline=INK, width=5 * SS)


def head_for(cid, view):
    """Cast key skin=(r,g,b) tints the head; the painted shade follows it (default = the kit's white head)."""
    c = CAST[cid]
    if not c.get('skin'):
        return head_styled(cid, view)
    keep = P.WHITE, P.LILAC
    P.WHITE, P.LILAC = tuple(c['skin']), tuple(int(v * .78) for v in c['skin'])
    try:
        return head_styled(cid, view)
    finally:
        P.WHITE, P.LILAC = keep


def tears(ld, p, lk):
    """Pose key tears=0..1: streams from both eyes down the cheeks, with a drop at the end."""
    t = p['tears']
    for ex in (320 + lk, 450 + lk):
        y0, y1 = 424, 424 + 120 * t
        ld.line([(ex * SS, y0 * SS), (ex * SS, y1 * SS)], fill=(150, 214, 240, 255), width=14 * SS)
        ld.ellipse([(ex - 12) * SS, (y1 - 8) * SS, (ex + 12) * SS, (y1 + 18) * SS], fill=(150, 214, 240, 255), outline=INK, width=3 * SS)


def head_styled(cid, view):
    c = CAST[cid]
    hs = c.get('hair_style')
    if not hs:
        return head_core(cid, view)
    keep = P.JAG_F, P.JAG_Q
    if not ((c.get('cap', 1) or c.get('hat') in TOP_HATS) and view != 'back'):
        P.JAG_F, P.JAG_Q = FRINGE_F, FRINGE_Q
    try:
        im = head_core(cid, view)
    finally:
        P.JAG_F, P.JAG_Q = keep
    return add_hair(im, c, view, hs)


def head_core(cid, view):
    c = CAST[cid]
    if (c.get('cap', 1) or c.get('hat') in TOP_HATS) and view != 'back':
        # the reference: bare forehead, a wedge of hair at each temple coming out from under the cap
        keep = P.JAG_F, P.JAG_Q
        P.JAG_F = P.JAG_Q = SIDE_L
        im = P.head_art(view)
        P.JAG_F, P.JAG_Q = keep
        s = 760 * SS
        mask = Image.new('L', (s, s), 0)
        ImageDraw.Draw(mask).polygon([(x * SS, y * SS) for x, y in P.head_shape(380)], fill=255)
        hair_on(im, SIDE_R if view != 'q_r' else [(x + 40, y) for x, y in SIDE_R], 380, mask, 6)
        return im
    if not c.get('bald'):
        return P.head_art(view)
    keep = P.JAG_F, P.JAG_Q, P.JAG_B
    P.JAG_F = P.JAG_Q = TUFT_L
    P.JAG_B = [(-270, -215), (-270, 150), (-180, 176), (-90, 146), (0, 180), (90, 146), (180, 176), (270, 150), (270, -215)]
    im = P.head_art(view)
    P.JAG_F, P.JAG_Q, P.JAG_B = keep
    s = 760 * SS
    mask = Image.new('L', (s, s), 0)
    ImageDraw.Draw(mask).polygon([(x * SS, y * SS) for x, y in P.head_shape(380)], fill=255)
    if view != 'back':
        hair_on(im, TUFT_R, 380, mask, 4)
    if c.get('beard'):
        # white beard covering the jaw, mouth sits in it
        pts = [(380 + x, 380 + y) for x, y in [(-205, 118), (-150, 150), (-90, 172), (-40, 160), (0, 172), (40, 160), (90, 172), (150, 150), (205, 118), (262, 240), (-262, 240)]]
        lay = Image.new('RGBA', (s, s), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lay)
        P.poly(ld, pts, (176, 178, 188, 255))
        for a, b in zip(pts[:8], pts[1:9]):
            P.stroke(ld, [(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t) for t in np.linspace(0, 1, 18)], 5, (120, 122, 134, 255), amp=.03)
        lay.putalpha(Image.fromarray((np.asarray(lay)[..., 3] * (np.asarray(mask) / 255)).astype(np.uint8)))
        im.alpha_composite(lay)
    return im


def torso_for(d, im, p, tx, ty, back, cid):
    c = CAST[cid]
    st = c['style']
    if st == 'vest':
        return P.torso_art(d, im, p, tx, ty, back)
    if st not in ('suit', 'cardigan'):
        return costume(d, st, dict(c, hem=p['hem']) if p.get('hem') else c, tx, ty, back)
    tw, th = P.TOR_W, P.TOR_H
    if st == 'suit':
        col, tie = c['suit'] + A, c['tie'] + A if c.get('tie') else None
        dark = tuple(int(v * .7) for v in c['suit']) + A
    else:
        col, tie = (148, 112, 78, 255), (120, 88, 60, 255)
        dark = (108, 80, 54, 255)
    body = P.blob(tx, ty, tw / 2, th / 2, amp=.003, seed=5, sq=2.3, belly=.22)
    P.inked(d, body, col, 17)
    if back:
        P.stroke(d, [(tx, ty - th * .42 + t) for t in range(0, int(th * .68), 4)], 6, dark)
        return
    top = ty - th * .5 + 20
    if st == 'suit':
        P.inked(d, [(tx - 62, top), (tx + 62, top), (tx, top + 190)], (250, 246, 240, 255), 6)
        if tie:
            P.inked(d, [(tx - 20, top + 16), (tx + 20, top + 16), (tx + 11, top + 54), (tx + 20, top + 158), (tx, top + 188), (tx - 20, top + 158), (tx - 11, top + 54)], tie, 5)
        for sg in (-1, 1):
            P.inked(d, [(tx + sg * 62, top - 4), (tx + sg * 104, top + 66), (tx + sg * 62, top + 84), (tx + sg * 6, top + 196)], dark, 6)
        y = ty + th * .17
        d.ellipse([(tx - 15) * SS, (y - 15) * SS, (tx + 15) * SS, (y + 15) * SS], fill=(226, 226, 232, 255), outline=INK, width=4 * SS)
        P.rrect(d, tx + 50, ty + 58, tx + 112, ty + 88, 4, dark, INK, 4)
    else:
        for by in (-.2, .0, .2):
            y = ty + th * by
            d.ellipse([(tx - 17) * SS, (y - 17) * SS, (tx + 17) * SS, (y + 17) * SS], fill=(226, 196, 130, 255), outline=INK, width=4 * SS)
        P.stroke(d, [(tx, top + t) for t in range(0, int(th * .85), 4)], 6, dark, amp=0)
        P.rrect(d, tx - 112, ty + 40, tx - 50, ty + 102, 5, tie, dark, 5)
        P.rrect(d, tx + 50, ty + 40, tx + 112, ty + 102, 5, tie, dark, 5)


def rot_poly(pts, cx, cy, deg):
    a = math.radians(deg)
    return [(cx + (x - cx) * math.cos(a) - (y - cy) * math.sin(a), cy + (x - cx) * math.sin(a) + (y - cy) * math.cos(a)) for x, y in pts]


BR = {}


def paste_rgba(im, sprite, x, y):
    im.alpha_composite(sprite, (int(x - sprite.size[0] / 2), int(y - sprite.size[1] / 2)))


def prop(im, p, carry=()):
    """Held props sit on the hands; hands are redrawn after them, so a prop never swallows a hand."""
    d = ImageDraw.Draw(im)
    kind, (lx, ly), (rx, ry) = p.get('prop'), p['hand_l'], p['hand_r']
    extra = list(kind) if isinstance(kind, (list, tuple)) else [kind] if kind in ROLE_PROPS else [] if kind else list(carry)
    for k in extra:
        role_prop(d, k, p)
    if kind == 'laptop':
        cx, cy = (lx + rx) / 2, (ly + ry) / 2 - 62
        P.inked(d, [(cx - 200, cy - 118), (cx + 200, cy - 118), (cx + 200, cy + 118), (cx - 200, cy + 118)], (192, 198, 208, 255), 13)
        P.inked(d, [(cx - 214, cy + 118), (cx + 214, cy + 118), (cx + 226, cy + 140), (cx - 226, cy + 140)], (150, 156, 168, 255), 11)
        P.rrect(d, cx - 142, cy - 44, cx + 142, cy + 44, 8, (18, 22, 34, 255), None, 1)
        if 'bv' not in BR:
            b = Image.open(BRAND).convert('RGBA')
            BR['bv'] = b.resize((252 * SS, int(252 * SS * b.size[1] / b.size[0])), Image.LANCZOS)
        paste_rgba(im, BR['bv'], cx * SS, cy * SS)
    elif kind == 'drive':
        cx, cy = rx, ry - 88
        for k in range(10):
            a = k * 2 * math.pi / 10 + p.get('ph', 0) * .1
            P.stroke(d, [(cx + (150 + t) * math.cos(a), cy + (150 + t) * math.sin(a)) for t in range(0, 44, 3)], 13, (140, 255, 170, 255), amp=0)
        P.rrect(d, cx - 42, cy - 158, cx + 42, cy - 100, 3, (205, 208, 214, 255), INK, 8)
        for sx in (-18, 18):
            d.rectangle([(cx + sx - 8) * SS, (cy - 142) * SS, (cx + sx + 8) * SS, (cy - 126) * SS], fill=INK)
        P.inked(d, [(cx - 66, cy - 100), (cx + 66, cy - 100), (cx + 66, cy + 110), (cx - 66, cy + 110)], (68, 214, 118, 255), 11)
        d.text((cx * SS, (cy - 18) * SS), PROP_TEXT['drive'][0], font=font(56), fill=(8, 36, 16, 255), anchor='mm')
        d.text((cx * SS, (cy + 50) * SS), PROP_TEXT['drive'][1], font=font(46), fill=(8, 36, 16, 255), anchor='mm')
    elif kind == 'clipboard':
        cx, cy = lx + 40, ly - 70
        P.inked(d, [(cx - 92, cy - 124), (cx + 92, cy - 124), (cx + 92, cy + 124), (cx - 92, cy + 124)], (150, 96, 54, 255), 10)
        P.poly(d, [(cx - 74, cy - 96), (cx + 74, cy - 96), (cx + 74, cy + 108), (cx - 74, cy + 108)], (252, 248, 236, 255))
        d.text((cx * SS, (cy - 66) * SS), PROP_TEXT['clipboard'], font=font(50), fill=(16, 26, 60, 255), anchor='mm')
        for k in range(3):
            P.stroke(d, [(cx - 54 + t, cy - 10 + k * 36) for t in range(0, 108, 4)], 8, INK, amp=0)
        P.rrect(d, cx - 30, cy - 136, cx + 30, cy - 106, 4, (196, 200, 210, 255), INK, 5)
    elif kind == 'mallet':
        rot = p.get('ham_rot', 0)
        L = [(rx - 14, ry + 34), (rx + 14, ry + 34), (rx + 14, ry - 240), (rx - 14, ry - 240)]
        P.inked(d, rot_poly(L, rx, ry, rot), (150, 96, 54, 255), 7)
        hd = [(rx - 92, ry - 330), (rx + 92, ry - 330), (rx + 92, ry - 226), (rx - 92, ry - 226)]
        P.inked(d, rot_poly(hd, rx, ry, rot), (190, 60, 56, 255), 9)
    elif kind == 'label':
        cx, cy = lx, ly - 22
        P.inked(d, [(cx - 120, cy - 44), (cx + 120, cy - 44), (cx + 120, cy + 44), (cx - 120, cy + 44)], (45, 191, 110, 255), 8)
        d.text((cx * SS, cy * SS), PROP_TEXT['label'], font=font(50), fill=(7, 35, 15, 255), anchor='mm')
    d = ImageDraw.Draw(im)
    for h in (p['hand_l'], p['hand_r']):
        d.ellipse([(h[0] - 29) * SS, (h[1] - 29) * SS, (h[0] + 29) * SS, (h[1] + 29) * SS], fill=INK)


def fx_layer(im, items):
    """Flat outlined sprites: rings, sparks, Z letters."""
    d = ImageDraw.Draw(im)
    for it in items:
        kind = it[0]
        if kind == 'ring':
            _, x, y, r, w, col = it
            d.ellipse([(x - r) * SS, (y - r) * SS, (x + r) * SS, (y + r) * SS], outline=INK, width=int((w + 10) * SS))
            d.ellipse([(x - r + 5) * SS, (y - r + 5) * SS, (x + r - 5) * SS, (y + r - 5) * SS], outline=tuple(col) + A, width=int(w * SS))
        elif kind == 'star':
            _, x, y, s, n = it
            pts = [(x + (s * .45 if i % 2 else s) * math.cos(i * math.pi / n), y + (s * .45 if i % 2 else s) * math.sin(i * math.pi / n)) for i in range(2 * n)]
            P.inked(d, pts, (255, 214, 64, 255), 9)
        elif kind == 'z':
            _, x, y, s = it
            for o, c in ((7, INK), (0, (250, 250, 250, 255))):
                d.text((x * SS, y * SS), 'Z', font=font(int(s)), fill=c, anchor='mm', stroke_width=int(o * SS), stroke_fill=INK)
        else:
            FX.draw(d, it, SS)


def downsample(im):
    a = np.asarray(im, np.float32) / 255
    a[..., :3] *= a[..., 3:]
    h, w = a.shape[:2]
    a = a[:h // SS * SS, :w // SS * SS].reshape(h // SS, SS, w // SS, SS, 4).mean((1, 3))
    al = np.maximum(a[..., 3:], 1e-4)
    a[..., :3] = np.clip(a[..., :3] / al, 0, 1)
    return Image.fromarray((a * 255 + .5).astype(np.uint8), 'RGBA')


def setup(cid):
    c = CAST[cid]
    def_v = ((52, 188, 160), (92, 208, 182), (30, 128, 112), (44, 160, 138))
    v = c.get('vest', def_v)
    P.TEAL, P.TEAL_L, P.TEAL_D, P.BACK = [x + A for x in v]
    P.HAIR = c.get('hair', (122, 80, 44)) + A
    cap = c.get('cap', ((54, 88, 150), (230, 238, 250), (30, 40, 70)))
    if cap:
        P.CAP_B, P.CAP_W, P.CAP_D = [x + A for x in cap]
    P.TOR_W, P.TOR_H = c.get('tor', (285, 430))
    P.TY = P.FEET - 625 - P.TOR_H / 2 + 20


def ink_edge(card):
    from PIL import ImageFilter
    back = Image.new('RGBA', card.size, tuple(INK)[:3] + (0,))
    back.putalpha(card.getchannel('A').filter(ImageFilter.MaxFilter(9)))
    back.alpha_composite(card)
    return back


def head_sprite(folder, p):
    """A head from pre-made images (real person: photo cutout or traced cartoon): <folder>\\head_<mouth>.png + optional eyes_shut.png, square, head centre = image centre."""
    def get(name):
        key = str(Path(folder) / name)      # per folder: two real people in one reel have the same file names
        if key not in SPRITES:
            SPRITES[key] = Image.open(key).convert('RGBA')
        return SPRITES[key]
    m = p.get('mouth', 'line')
    lay = get(f'head_{m}.png' if (Path(folder) / f'head_{m}.png').exists() else 'head_line.png')
    if p.get('eyes') in ('shut', 'slit') and (Path(folder) / 'eyes_shut.png').exists():
        lay = lay.copy()
        lay.alpha_composite(get('eyes_shut.png'))
    return lay


def _same(cid):
    """Studio edition: every character uses one design; only the vest colour changes with the id."""
    key = 'same_' + cid
    if key not in CAST:
        CAST[key] = dict(style='vest', vest=_TINTS[sum(map(ord, cid)) % len(_TINTS)], hair=(52, 40, 40))
    return key


def _mark(im, x, y, w, alpha=255):
    if ('mk', w, alpha) not in BR:
        b = Image.open(_MK).convert('RGBA')
        b = b.resize((w * SS, int(w * SS * b.size[1] / b.size[0])), Image.LANCZOS)
        if alpha < 255:
            b.putalpha(b.getchannel('A').point(lambda v: v * alpha // 255))
        BR[('mk', w, alpha)] = b
    paste_rgba(im, BR[('mk', w, alpha)], x * SS, y * SS)


def draw_card(cid, p):
    cid = _same(cid)
    setup(cid)
    c = CAST[cid]
    if cid not in HEADS:
        HEADS[cid], CAPS[cid] = {}, {}
        for v in () if c.get('head_dir') else ('front', 'q_r', 'back'):
            HEADS[cid][v] = head_for(cid, v)
            if c.get('cap', 1):
                CAPS[cid][v] = P.cap_art(v)
        if c.get('hat'):
            HATS[cid] = {v: hat_art(c['hat'], v, c) for v in ('front', 'q_r', 'back')}
    TOR_H, TY, FEET, CX, HEAD_H = P.TOR_H, P.TY, P.FEET, P.CX, P.HEAD_H
    p = dict(p)
    sit, body, fs = p.get('sit'), p.get('body') or 'front', p.get('foreshorten') or 0
    sh, TH2 = 0.0, TOR_H
    if sit:
        sh = 300.0 if sit is True else float(sit)
        TH2 = TOR_H * (1 - .07 * min(1.0, sh / 300))
        P.TOR_H = TH2           # costumes read the torso height from here
    im = Image.new('RGBA', (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    back = p['view'] == 'back'
    tx, ty = CX + p['lean'], TY + p['bob'] * .5
    if sit:
        ty = TY - TOR_H / 2 + sh + TH2 / 2 + p['bob'] * .5
    hip_y = ty + TH2 * .44
    k = p['knee']
    qm = body in ('q', 'q_back')
    sx_l, sx_r, w_l, w_r, far = (-105 if back else -120), 125, 42, 42, None
    if body == 'q':
        sx_l, sx_r, w_l, w_r, far = -112, 66, 46, 34, 'r'
    elif body == 'q_back':
        sx_l, sx_r, w_l, w_r, far = -66, 112, 34, 46, 'l'
    sh_y = ty - 170
    if far:                     # the far hand rests just past the torso edge, its arm comes from behind the torso
        hy_ = min(max(p['hand_' + far][1], sh_y + 180), sh_y + 340)
        p['hand_' + far] = (tx + (150 if far == 'r' else -150), hy_)
    for side, sxx in (('l', sx_l), ('r', sx_r)):      # stretchy arms: the hand reaches `stretch` times its distance from the shoulder
        kk = p.get('stretch_' + side)
        if kk and kk != 1 and far != side:
            h_ = p['hand_' + side]
            p['hand_' + side] = (tx + sxx + (h_[0] - tx - sxx) * kk, sh_y + (h_[1] - sh_y) * kk)

    def warp(lay):
        """Turn a body layer: narrower, sheared, shifted (three-quarter body)."""
        sxq, shear, off = (.7, -.1, -20) if body == 'q' else (.7, .1, 20)
        a = 1 / sxq
        return lay.transform(lay.size, Image.AFFINE, (a, -shear * a, tx * SS + (-tx * SS + shear * ty * SS - off * SS) * a, 0, 1, 0), Image.BICUBIC)

    def part(draw_fn):
        if not qm:
            draw_fn(d, im)
            return
        lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
        draw_fn(ImageDraw.Draw(lay), lay)
        im.alpha_composite(warp(lay))

    if c.get('cape'):
        part(lambda dd, ii: costume(dd, 'cape', c, tx, ty, back))
    feet = p.get('feet', ((CX - 170, 0), (CX + 160, 0)))
    hip = p.get('hip', 52)
    if qm:
        feet = [(CX + (fx - CX) * .72 + (22 if body == 'q' else -22), lf) for fx, lf in feet]
        hip = hip * .7
    for (sx, sd), (fx, lift) in zip(((-hip, 1), (hip, -1)), feet):
        fy = FEET - 8 - lift
        if sit:
            sg_ = -1 if sx < 0 else 1
            hx0 = tx + sx * 1.3
            kx = tx + sg_ * (abs(sx) * 1.3 + 100)
            ky = hip_y + 84
            if 'feet' not in p:
                fx = tx + sg_ * (abs(sx) * 1.3 + 122)
            P.taper(d, P.bez((hx0, hip_y), ((hx0 + kx) / 2, hip_y + 8), (kx, ky), 40), 62, 54, seed=sd)
            P.taper(d, P.bez((kx, ky), (kx + (fx - kx) * .5, (ky + fy) / 2), (fx, fy), 50), 48, 42, seed=sd)
        else:
            pts = P.bez((tx + sx, hip_y), (tx + sx + (fx - tx - sx) * .35 + sd * k, (hip_y + fy) / 2), (fx, fy), 90)
            P.taper(d, pts, 54, 42, seed=sd)
        dr = p.get('toe', sd * -1)
        P.taper(d, [(fx + dr * t, fy) for t in range(0, 34, 2)], 42, 44)
    if c.get('skirt'):
        part(lambda dd, ii: skirt(dd, c, tx, ty, back, p.get('hem', 0)))

    def arm(sx, h, b, sd, w=42, kk=None):
        a = (tx + sx, sh_y)
        ln = math.hypot(h[0] - a[0], h[1] - a[1])
        ctrl = ((tx + sx + h[0]) / 2 + b * sd, (sh_y + h[1]) / 2 + abs(b) * .25)
        if kk and kk > 1:
            ctrl = ((tx + sx + h[0]) / 2 + b * sd / kk, (sh_y + h[1]) / 2 + abs(b) * .25 / kk)
        pts = P.bez(a, ctrl, h, max(90, int(ln / 10)))
        if kk and kk > 1:       # elastic: a soft ripple that dies out toward the hand
            amp, nn = min(26.0, 12 * (kk - 1)), len(pts)
            ux, uy = (h[0] - a[0]) / (ln or 1), (h[1] - a[1]) / (ln or 1)
            pts = [(x - uy * amp * math.sin(2 * math.pi * 1.25 * i / (nn - 1)) * (1 - i / (nn - 1)) ** .6, y + ux * amp * math.sin(2 * math.pi * 1.25 * i / (nn - 1)) * (1 - i / (nn - 1)) ** .6)
                   for i, (x, y) in enumerate(pts)]
        P.stroke(d, pts, w, seed=sd, amp=.03)
    if back or far == 'l':
        arm(sx_l, p['hand_l'], p['bend_l'], 1, w_l, p.get('stretch_l'))
    if far == 'r':
        arm(sx_r, p['hand_r'], p['bend_r'], -1, w_r)
    part(lambda dd, ii: torso_for(dd, ii, p, tx, ty, back, cid))
    if not back:
        _mark(im, tx + 78, ty - 70, 92)
    _mark(im, tx - 40, hip_y + 150, 70, 14)
    d = ImageDraw.Draw(im)
    if not back and far != 'l':
        arm(sx_l, p['hand_l'], p['bend_l'], 1, w_l, p.get('stretch_l'))
    if far != 'r':
        arm(sx_r, p['hand_r'], p['bend_r'], -1, w_r, p.get('stretch_r'))
    prop(im, p, c.get('carry', ()))
    hx, hy = tx + 4, ty - TH2 / 2 + 22 - HEAD_H / 2 + p['bob']
    if qm:
        hx += 14 if body == 'q' else -14
    hs = 1.0
    if fs:                      # high camera / lying figure: body and legs shrink toward the feet, the head grows
        s_ = 1 - .42 * fs
        a_ = 1 / s_
        im = im.transform(im.size, Image.AFFINE, (a_, 0, CX * SS * (1 - a_), 0, a_, FEET * SS * (1 - a_)), Image.BICUBIC)
        hs = 1 + .45 * fs
        nx, ny = CX + (hx - CX) * s_, FEET - (FEET - (hy + HEAD_H / 2)) * s_
        hx, hy = nx, ny - HEAD_H / 2 * hs
    d = ImageDraw.Draw(im)

    def put(lay, x0, y0, half, hz):
        """Composite a head-sized layer centred at (x0, y0); `half` = half its size in px; hz = scale."""
        if hz != 1.0:
            n_ = int(lay.size[0] * hz)
            lay = lay.resize((n_, n_), Image.BICUBIC)
        im.alpha_composite(lay, (int((x0 - half * hz) * SS), int((y0 - half * hz) * SS)))
    if c.get('head_dir'):
        lay = head_sprite(c['head_dir'], p)
        n = lay.size[0] // SS // 2
        im.alpha_composite(lay.rotate(p['tilt'], Image.BICUBIC), (int((hx - n) * SS), int((hy - n) * SS)))
        if p.get('fx'):
            fx_layer(im, p['fx'])
        return ink_edge(downsample(im))
    lay = HEADS[cid][p['view']].copy()
    ld = ImageDraw.Draw(lay)
    if not back:
        P.face(ld, p, 380, 380)
        lk = 62 if p['view'] == 'q_r' else 0
        if c.get('stache'):
            mx, my = 388 + lk * 1.1, 484
            P.stroke(ld, P.bez((mx - 70, my - 2), (mx - 28, my - 38), (mx, my - 20), 30), 20)
            P.stroke(ld, P.bez((mx, my - 20), (mx + 28, my - 38), (mx + 70, my - 2), 30), 20)
        if c.get('glasses'):
            for ex in (320 + lk, 450 + lk):
                ld.ellipse([(ex - 54) * SS, (398 - 50) * SS, (ex + 54) * SS, (398 + 50) * SS], outline=INK, width=10 * SS)
            P.stroke(ld, [(374 + lk + t, 392) for t in range(0, 22, 2)], 9, amp=0)
        if c.get('lashes'):
            lashes(ld, p, lk)
        if p.get('tears'):
            tears(ld, p, lk)
        if 'pipe' in (c.get('carry') or ()) and p.get('mouth') == 'pout' and p.get('prop') != []:
            # playing: the pipe's mouth end sits on the lips, over the face (the held part is drawn under the head by role_prop)
            mx, my = 392 + lk, 512
            P.inked(ld, [(mx - 14, my), (mx + 14, my), (mx + 112, 760), (mx + 80, 760)], (150, 98, 52, 255), 7)
            for t in (.45, .75):
                ld.ellipse([(mx + 96 * t - 7) * SS, (my + 248 * t - 7) * SS, (mx + 96 * t + 7) * SS, (my + 248 * t + 7) * SS], fill=(40, 26, 18, 255))
    if c.get('earrings'):
        earrings(ld, c, p['view'])
    if hs == 1.0:
        im.alpha_composite(lay.rotate(p['tilt'], Image.BICUBIC), (int((hx - 380) * SS), int((hy - 380) * SS)))
    else:
        put(lay.rotate(p['tilt'], Image.BICUBIC), hx, hy, 380, hs)
    if c.get('cap', 1):
        ta = math.radians(p['tilt'])
        cx, cy = hx - 196 * hs * math.sin(ta), hy - 196 * hs * math.cos(ta) + p['hat_y']
        cl = CAPS[cid][p['view']].rotate(p['tilt'] * 1.15 + p['hat_rot'], Image.BICUBIC)
        if hs == 1.0:
            im.alpha_composite(cl, (int((cx - 330) * SS), int((cy - 330) * SS)))
        else:
            put(cl, cx, cy, 330, hs)
    if c.get('hat'):
        hl = HATS[cid][p['view']].rotate(p['tilt'] + p['hat_rot'], Image.BICUBIC)
        if hs == 1.0:
            im.alpha_composite(hl, (int((hx - 700) * SS), int((hy - 700 + p['hat_y']) * SS)))
        else:
            put(hl, hx, hy + p['hat_y'], 700, hs)
    if p.get('fx'):
        fx_layer(im, p['fx'])
    return ink_edge(downsample(im))


def draw_fx(items):
    im = Image.new('RGBA', (W * SS, H * SS), (0, 0, 0, 0))
    fx_layer(im, items)
    return downsample(im)




def configure(S):
    CAST.update(getattr(S, 'CAST', {}))
    PROP_TEXT.update(getattr(S, 'PROP_TEXT', {}))

