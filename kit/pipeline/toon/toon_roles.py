"""Wardrobe: a costume, headwear and carried things per role, in the same flat inked art. A role name is a cast id: card('king', ...). Sheet of all of them: COSTUMES.jpg."""
import math

from PIL import Image, ImageDraw

import toon_puppet as P

SS, INK = P.SS, P.INK
A = (255,)
GOLD, GOLD_D, WHITE, STEEL, STEEL_D = (236, 186, 52), (176, 124, 30), (246, 244, 240), (178, 186, 198), (118, 126, 140)
SHIRT = (236, 238, 244)
ROLES = {
    'king': dict(style='robe', robe=(176, 28, 52), ermine=True, cape=(136, 20, 44), belt=GOLD, tor=(320, 430), cap=None, hat='crown', hair=(92, 62, 40), carry=('scepter', 'shield')),
    'knight': dict(style='armor', tor=(320, 420), cap=None, hat='helm', cape=(40, 70, 150), carry=('sword', 'shield')),
    'engineer': dict(style='hiviz', hv=(250, 150, 30), shirt=(62, 92, 150), tor=(300, 430), cap=None, hat='hardhat', hat_col=(250, 206, 44), hair=(44, 34, 34), carry=('blueprint',)),
    'worker': dict(style='overalls', denim=(52, 84, 140), shirt=(206, 90, 60), tor=(310, 430), cap=None, hat='hardhat', hat_col=(240, 124, 40), hair=(70, 46, 34), stache=True, carry=('wrench',)),
    'dev': dict(style='hoodie', hood=(58, 64, 84), tor=(310, 420), cap=None, hat='headset', hair=(30, 26, 32), glasses=True),
    'doctor': dict(style='coat', coat=WHITE, shirt=(92, 170, 190), tie=(40, 90, 150), steth=True, tor=(300, 430), cap=None, hat='mirror', hair=(44, 36, 40)),
    'scientist': dict(style='coat', coat=WHITE, shirt=(236, 238, 244), tie=(150, 50, 90), tor=(300, 430), cap=None, hat='goggles', hair=(150, 150, 160), carry=('flask',)),
    'police': dict(style='uniform', uni=(36, 56, 112), belt=(30, 26, 30), badge=GOLD, tor=(320, 420), cap=None, hat='peaked', hat_col=(30, 46, 96), hair=(40, 32, 34)),
    'soldier': dict(style='uniform', uni=(92, 104, 62), belt=(58, 44, 30), tor=(330, 420), cap=None, hat='helmet', hat_col=(82, 94, 54), hair=(40, 32, 34)),
    'pilot': dict(style='uniform', uni=(28, 36, 72), belt=(20, 20, 30), badge=GOLD, epaulette=GOLD, tor=(310, 430), cap=None, hat='peaked', hat_col=(244, 244, 248), hair=(70, 56, 50)),
    'astronaut': dict(style='spacesuit', tor=(370, 430), cap=None, hat='bubble', hair=(60, 44, 36)),
    'chef': dict(style='apron', shirt=WHITE, apron=(244, 240, 228), tor=(330, 410), cap=None, hat='toque', hair=(50, 40, 36), stache=True, carry=('pan',)),
    'shopkeeper': dict(style='apron', shirt=(196, 96, 70), apron=(58, 128, 92), tor=(330, 410), cap=None, hair=(60, 46, 40)),
    'farmer': dict(style='overalls', denim=(70, 104, 160), shirt=(200, 62, 56), tor=(310, 430), cap=None, hat='straw', hair=(112, 76, 44)),
    'judge': dict(style='robe', robe=(34, 32, 42), bands=True, belt=None, tor=(320, 430), cap=None, hat='wig', hair=(220, 220, 226)),
    'banker': dict(style='suit', suit=(40, 44, 58), tie=(216, 170, 50), tor=(330, 400), cap=None, hair=(70, 60, 60), glasses=True, carry=('briefcase',)),
    'tycoon': dict(style='suit', suit=(26, 26, 32), tie=(170, 30, 50), tor=(380, 400), cap=None, hat='tophat', hair=(150, 146, 150), stache=True, carry=('moneybag',)),
    'trader': dict(style='suit', suit=(40, 110, 170), tie=(244, 196, 60), tor=(300, 420), cap=None, hat='headset', hair=(50, 40, 40)),
    'piper': dict(style='motley', motley=((206, 40, 46), (246, 196, 40), (40, 110, 196), (60, 160, 80), (236, 120, 30), (140, 60, 160)), tor=(300, 430), cap=None, hat='pointed', hat_col=(40, 150, 90), feather=(226, 50, 46), hair=(150, 70, 30), stache=True, skin=(236, 190, 154), carry=('pipe',)),
    'teacher': dict(style='cardigan', hair=(120, 90, 70), tor=(300, 400), cap=None, glasses=True, carry=('tablet',)),
}


def _f(r, hair_style, **kw):
    """Female variant of a role: same costume and proportions, slimmer torso (width x .88), hair style, lashes, earrings."""
    c = dict(ROLES[r])
    for k in ('stache', 'beard', 'bald'):
        c.pop(k, None)
    tw, th = c['tor']
    c.update(tor=(int(tw * .88), th), hair_style=hair_style, lashes=True, earrings=True)
    c.update(kw)
    return c


ROLES.update({
    'kurta': dict(style='kurta', kurta=(238, 226, 200), jacket=(40, 78, 124), tor=(310, 430), cap=None, hair=(30, 26, 30), stache=True),
})
_QUEEN = dict(style='robe', robe=(120, 34, 126), ermine=True, belt=GOLD, tor=(290, 430), cap=None, hat='crown', hair=(70, 40, 30), robe_long=True, carry=('scepter',),
              hair_style='long', lashes=True, earrings=True)
ROLES.update({
    'queen': _QUEEN, 'king_f': dict(_QUEEN),
    'knight_f': _f('knight', 'long'),
    'engineer_f': _f('engineer', 'ponytail'),
    'worker_f': _f('worker', 'ponytail'),
    'dev_f': _f('dev', 'long'),
    'doctor_f': _f('doctor', 'bun'),
    'scientist_f': _f('scientist', 'bob', robe_long=True, hair=(86, 54, 66)),
    'police_f': _f('police', 'bun'),
    'soldier_f': _f('soldier', 'ponytail'),
    'pilot_f': _f('pilot', 'ponytail'),
    'astronaut_f': _f('astronaut', 'ponytail', tor=(340, 430)),
    'chef_f': _f('chef', 'bun'),
    'shopkeeper_f': _f('shopkeeper', 'bun'),
    'farmer_f': _f('farmer', 'long'),
    'judge_f': _f('judge', None, robe_long=True),
    'banker_f': _f('banker', 'bob', skirt=(40, 44, 58)),
    'tycoon_f': _f('tycoon', 'bun', tor=(330, 400), skirt=(26, 26, 32)),
    'trader_f': _f('trader', 'ponytail'),
    'teacher_f': _f('teacher', 'bob', skirt=(92, 70, 120)),
    'office_f': dict(style='suit', suit=(150, 52, 78), skirt=(150, 52, 78), tor=(264, 400), cap=None, hair=(52, 36, 34), hair_style='bob', lashes=True, earrings=True),
    'kurta_f': dict(style='kurta', kurta=(216, 78, 112), kurta_drop=300, scarf=(250, 214, 96), tor=(270, 430), cap=None, hair=(30, 24, 28), hair_style='long', lashes=True, earrings=True),
    'saree_f': dict(style='saree', saree=(34, 136, 120), blouse=(224, 164, 52), skirt_hem=1830, skirt_flare=.84, skirt_trim=GOLD, robe_long=True,
                    tor=(262, 430), cap=None, hair=(26, 22, 26), hair_style='bun', lashes=True, earrings=True),
})
TOP_HATS = {'crown', 'helm', 'hardhat', 'helmet', 'peaked', 'toque', 'tophat', 'straw', 'pointed', 'beret', 'wimple'}   # these hide the top of the head; other headwear shows the full hair
ROLE_PROPS = {'scepter', 'shield', 'sword', 'blueprint', 'wrench', 'flask', 'pan', 'briefcase', 'moneybag', 'tablet', 'pistol', 'cup', 'cola', 'vodka', 'pen', 'camera', 'pipe', 'shotgun', 'lantern'}


def dk(c, v=.7):
    return tuple(int(x * v) for x in c[:3]) + A


def col(c):
    return tuple(c[:3]) + A


def dot(d, x, y, r, fill, w=4):
    d.ellipse([(x - r) * SS, (y - r) * SS, (x + r) * SS, (y + r) * SS], fill=fill, outline=INK, width=w * SS)


def line(d, a, b, w, c=INK):
    P.stroke(d, [(a[0] + (b[0] - a[0]) * t / 20, a[1] + (b[1] - a[1]) * t / 20) for t in range(21)], w, c, amp=0)


def egg(d, c, tx, ty, ink=17):
    b = P.blob(tx, ty, P.TOR_W / 2, P.TOR_H / 2, amp=.003, seed=5, sq=2.3, belly=.22)
    P.inked(d, b, col(c), ink)
    return b


def costume(d, st, c, tx, ty, back):
    tw, th = P.TOR_W, P.TOR_H
    top = ty - th * .5 + 20
    if st == 'cape':
        hem = P.FEET - 120
        P.inked(d, [(tx - tw * .5, top + 10), (tx + tw * .5, top + 10), (tx + tw * .95, hem), (tx + tw * .3, hem + 26), (tx, hem), (tx - tw * .3, hem + 26), (tx - tw * .95, hem)], col(c['cape']), 14)
    elif st == 'robe':
        hem = P.FEET - 250
        if c.get('robe_long'):
            hem = P.FEET - 30
            P.inked(d, [(tx - tw * .4, top), (tx + tw * .4, top)] + hem_pts(tx, hem, tw * .86, c.get('hem', 0)), col(c['robe']), 17)
        else:
            P.inked(d, [(tx - tw * .4, top), (tx + tw * .4, top), (tx + tw * .62, hem), (tx - tw * .62, hem)], col(c['robe']), 17)
        if back:
            return
        if c.get('ermine'):
            P.inked(d, [(tx - tw * .46, top - 6), (tx + tw * .46, top - 6), (tx + tw * .3, top + 92), (tx, top + 130), (tx - tw * .3, top + 92)], col(WHITE), 7)
            for x, y in ((-90, 34), (0, 40), (90, 34), (-45, 76), (45, 76), (0, 104)):
                d.ellipse([(tx + x - 7) * SS, (top + y - 11) * SS, (tx + x + 7) * SS, (top + y + 11) * SS], fill=INK)
            P.inked(d, [(tx - 26, top + 130), (tx + 26, top + 130), (tx + 26, hem), (tx - 26, hem)], col(GOLD_D), 5)
            dot(d, tx, top + 176, 36, col(GOLD), 6)
            dot(d, tx, top + 176, 15, (200, 30, 60, 255), 4)
        if c.get('bands'):
            for sg in (-1, 1):
                P.inked(d, [(tx + sg * 6, top + 8), (tx + sg * 52, top + 8), (tx + sg * 58, top + 118), (tx + sg * 14, top + 118)], col(WHITE), 5)
        if c.get('belt'):
            P.inked(d, [(tx - tw * .5, ty + th * .22), (tx + tw * .5, ty + th * .22), (tx + tw * .52, ty + th * .3), (tx - tw * .52, ty + th * .3)], col(c['belt']), 6)
    elif st == 'coat':
        hem = ty + th * .72
        if c.get('robe_long'):
            hem = P.FEET - 30
            P.inked(d, [(tx - tw * .42, top), (tx + tw * .42, top)] + hem_pts(tx, hem, tw * .74, c.get('hem', 0)), col(c['coat']), 17)
        else:
            P.inked(d, [(tx - tw * .42, top), (tx + tw * .42, top), (tx + tw * .58, hem), (tx - tw * .58, hem)], col(c['coat']), 17)
        if back:
            return
        P.inked(d, [(tx - 70, top), (tx + 70, top), (tx, top + 230)], col(c['shirt']), 6)
        P.inked(d, [(tx - 18, top + 16), (tx + 18, top + 16), (tx + 22, top + 170), (tx, top + 205), (tx - 22, top + 170)], col(c['tie']), 5)
        for sg in (-1, 1):
            P.inked(d, [(tx + sg * 70, top - 4), (tx + sg * 118, top + 80), (tx + sg * 70, top + 108), (tx + sg * 6, top + 240)], (226, 226, 230, 255), 6)
        line(d, (tx, top + 236), (tx, hem - 8), 6)
        P.rrect(d, tx + 56, ty + 40, tx + 124, ty + 116, 4, (232, 232, 236, 255), INK, 5)
        line(d, (tx + 76, ty + 18), (tx + 76, ty + 56), 9, (40, 90, 170, 255))
        P.rrect(d, tx - 124, ty + 112, tx - 52, ty + 176, 4, (232, 232, 236, 255), INK, 5)
        if c.get('steth'):
            P.stroke(d, P.bez((tx - 92, top + 20), (tx - 118, top + 180), (tx - 30, top + 236), 40), 11, amp=0)
            P.stroke(d, P.bez((tx + 92, top + 20), (tx + 118, top + 180), (tx - 30, top + 236), 40), 11, amp=0)
            dot(d, tx - 30, top + 256, 25, col(STEEL), 6)
    elif st == 'hiviz':
        v = c['hv']
        egg(d, c['shirt'], tx, ty)
        if back:
            P.inked(d, [(tx - tw * .38, top + 30), (tx + tw * .38, top + 30), (tx + tw * .46, ty + th * .3), (tx - tw * .46, ty + th * .3)], col(v), 6)
        else:
            for sg in (-1, 1):
                P.inked(d, [(tx + sg * 26, top + 18), (tx + sg * tw * .4, top + 26), (tx + sg * tw * .49, ty + th * .3), (tx + sg * 8, ty + th * .3)], col(v), 6)
            line(d, (tx - 64, ty + 70), (tx - 64, ty + 70), 1)
        for dy in (-.04, .14):
            for sg in (-1, 1):
                x0, x1 = (tx + sg * 12, tx + sg * tw * .47)
                P.inked(d, [(x0, ty + th * dy), (x1, ty + th * dy), (x1, ty + th * dy + 30), (x0, ty + th * dy + 30)], (232, 236, 216, 255), 3)
        P.inked(d, [(tx - tw * .5, ty + th * .3), (tx + tw * .5, ty + th * .3), (tx + tw * .5, ty + th * .37), (tx - tw * .5, ty + th * .37)], (84, 58, 36, 255), 6)
        if not back:
            P.rrect(d, tx + 60, ty + th * .34, tx + 130, ty + th * .34 + 74, 5, (120, 84, 50, 255), INK, 5)
            P.rrect(d, tx - 16, ty + th * .3 + 2, tx + 16, ty + th * .37 - 2, 3, col(GOLD), INK, 4)
    elif st == 'overalls':
        egg(d, c['shirt'], tx, ty)
        if back:
            return
        den = c['denim']
        P.inked(d, [(tx - 96, top + 96), (tx + 96, top + 96), (tx + tw * .5, ty + th * .28), (tx + tw * .46, ty + th * .46), (tx - tw * .46, ty + th * .46), (tx - tw * .5, ty + th * .28)], col(den), 7)
        for sg in (-1, 1):
            P.stroke(d, [(tx + sg * (80 + t * .12), top + 96 - t) for t in range(0, 90, 4)], 28, col(den), amp=0)
            dot(d, tx + sg * 76, top + 112, 16, col(GOLD), 4)
        P.rrect(d, tx - 58, top + 150, tx + 58, top + 236, 5, dk(den, .82), INK, 5)
    elif st == 'hoodie':
        egg(d, c['hood'], tx, ty)
        if back:
            P.inked(d, [(tx - 110, top - 10), (tx + 110, top - 10), (tx + 70, top + 110), (tx - 70, top + 110)], dk(c['hood'], .8), 7)
            return
        P.inked(d, [(tx - 128, top - 20), (tx + 128, top - 20), (tx + 86, top + 62), (tx, top + 92), (tx - 86, top + 62)], dk(c['hood'], .75), 7)
        for sx in (-34, 34):
            line(d, (tx + sx, top + 80), (tx + sx, top + 176), 7, (232, 232, 236, 255))
        P.inked(d, [(tx - 106, ty + 38), (tx + 106, ty + 38), (tx + 132, ty + 138), (tx - 132, ty + 138)], dk(c['hood'], .85), 6)
    elif st == 'uniform':
        u = c['uni']
        egg(d, u, tx, ty)
        P.inked(d, [(tx - tw * .5, ty + th * .25), (tx + tw * .5, ty + th * .25), (tx + tw * .52, ty + th * .33), (tx - tw * .52, ty + th * .33)], col(c['belt']), 6)
        if back:
            return
        P.inked(d, [(tx - 66, top), (tx + 66, top), (tx, top + 120)], col(SHIRT), 6)
        P.inked(d, [(tx - 14, top + 16), (tx + 14, top + 16), (tx + 16, top + 90), (tx, top + 116), (tx - 16, top + 90)], dk(u, .55), 4)
        for sg in (-1, 1):
            P.inked(d, [(tx + sg * 66, top - 4), (tx + sg * 104, top + 62), (tx + sg * 66, top + 78), (tx + sg * 6, top + 128)], dk(u, .78), 5)
            if c.get('epaulette'):
                P.inked(d, [(tx + sg * 86, top + 6), (tx + sg * 150, top + 22), (tx + sg * 150, top + 54), (tx + sg * 86, top + 40)], col(c['epaulette']), 5)
            P.rrect(d, tx + sg * 92 - 40, ty - 18, tx + sg * 92 + 40, ty + 44, 4, dk(u, .82), INK, 4)
        for y in (top + 146, ty + 12, ty + 78):
            dot(d, tx, y, 12, col(GOLD), 3)
        P.rrect(d, tx - 20, ty + th * .25 + 2, tx + 20, ty + th * .33 - 2, 3, col(GOLD), INK, 4)
        if c.get('badge'):
            dot(d, tx + 94, ty - 58, 26, col(c['badge']), 5)
    elif st == 'armor':
        egg(d, STEEL, tx, ty)
        if back:
            return
        P.inked(d, [(tx - tw * .42, top + 6), (tx + tw * .42, top + 6), (tx + tw * .3, ty + th * .24), (tx, ty + th * .33), (tx - tw * .3, ty + th * .24)], (204, 212, 222, 255), 6)
        line(d, (tx, top + 20), (tx, ty + th * .3), 7, col(STEEL_D))
        for sg in (-1, 1):
            P.inked(d, [(tx + sg * tw * .36, top - 8), (tx + sg * tw * .68, top + 16), (tx + sg * tw * .66, top + 92), (tx + sg * tw * .34, top + 70)], col(STEEL_D), 7)
            for y in (top + 54, ty, ty + 56):
                dot(d, tx + sg * 86, y, 8, col(GOLD), 3)
        P.inked(d, [(tx - tw * .5, ty + th * .3), (tx + tw * .5, ty + th * .3), (tx + tw * .5, ty + th * .37), (tx - tw * .5, ty + th * .37)], col(GOLD_D), 6)
    elif st == 'spacesuit':
        egg(d, (232, 234, 238), tx, ty)
        P.inked(d, [(tx - 130, top - 16), (tx + 130, top - 16), (tx + 120, top + 44), (tx - 120, top + 44)], col(STEEL_D), 7)
        if back:
            P.rrect(d, tx - 110, top + 66, tx + 110, ty + 120, 12, col(STEEL), INK, 7)
            return
        P.rrect(d, tx - 88, top + 104, tx + 88, top + 214, 8, (50, 56, 72, 255), INK, 6)
        for i, cl in enumerate(((226, 60, 60), (70, 200, 110), (240, 190, 50))):
            dot(d, tx - 50 + i * 50, top + 158, 15, col(cl), 3)
        for sg in (-1, 1):
            line(d, (tx + sg * 104, top + 230), (tx + sg * 128, ty + 90), 12, (216, 84, 50, 255))
    elif st == 'apron':
        egg(d, c['shirt'], tx, ty)
        if back:
            line(d, (tx - 110, ty + 30), (tx + 110, ty + 30), 10, col(c['apron']))
            return
        ap = c['apron']
        P.inked(d, [(tx - 76, top + 92), (tx + 76, top + 92), (tx + tw * .46, ty + th * .22), (tx + tw * .5, ty + th * .48), (tx - tw * .5, ty + th * .48), (tx - tw * .46, ty + th * .22)], col(ap), 7)
        for sg in (-1, 1):
            line(d, (tx + sg * 68, top + 96), (tx + sg * 94, top - 2), 12, dk(ap, .86))
        P.rrect(d, tx - 74, ty + 62, tx + 74, ty + 138, 5, dk(ap, .9), INK, 5)
    elif st == 'kurta':
        kc = c['kurta']
        drop = c.get('kurta_drop', 150)
        hem = ty + th * .5 + drop
        sway = c.get('hem', 0)
        egg(d, kc, tx, ty)
        lowtop = ty + th * .3
        if drop:
            P.inked(d, [(tx - tw * .48, lowtop), (tx + tw * .48, lowtop)] + hem_pts(tx, hem, tw * .58, sway, n=4, amp=4), col(kc), 17)
            P.poly(d, [(tx - tw * .48 + 16, lowtop - 8), (tx + tw * .48 - 16, lowtop - 8), (tx + tw * .5 - 16, lowtop + 70), (tx - tw * .5 + 16, lowtop + 70)], col(kc))
        if c.get('scarf'):
            sc = c['scarf']
            for sg, o in ((-1, 0), (1, 18)):
                if back:
                    break
                P.inked(d, [(tx + sg * tw * .38, top - 4), (tx + sg * tw * .38 - sg * 46, top - 4), (tx + sg * tw * .3 - sg * 30 + o, ty + th * .4), (tx + sg * tw * .3 + sg * 16 + o, ty + th * .4)], col(sc), 6)
        if back:
            if c.get('jacket'):
                P.inked(d, [(tx - tw * .44, top + 10), (tx + tw * .44, top + 10), (tx + tw * .46, ty + th * .42), (tx - tw * .46, ty + th * .42)], col(c['jacket']), 8)
            return
        line(d, (tx, top + 12), (tx, lowtop + 40), 6, dk(kc, .68))
        if c.get('jacket'):
            jk = c['jacket']
            for sg in (-1, 1):
                P.inked(d, [(tx + sg * 30, top + 8), (tx + sg * tw * .47, top + 4), (tx + sg * tw * .49, ty + th * .42), (tx + sg * 12, ty + th * .42)], col(jk), 7)
            for yy in (top + 120, top + 180, top + 240):
                dot(d, tx + 8, yy, 9, col(GOLD), 3)
        else:
            for yy in (top + 58, top + 112, top + 166):
                dot(d, tx, yy, 8, col(c.get('btn', GOLD)), 3)
        P.inked(d, [(tx - 50, top - 2), (tx + 50, top - 2), (tx + 34, top + 28), (tx - 34, top + 28)], dk(kc, .9), 5)
        if not c.get('scarf'):
            P.rrect(d, tx + 56, ty + 30, tx + 116, ty + 92, 4, dk(kc, .92), INK, 4)
    elif st == 'motley':
        # pied tunic: halves in two colours, diamond patches in the rest, dagged hem and collar
        cs = c['motley']
        hem = ty + th * .5 + c.get('motley_drop', 220)
        sway = c.get('hem', 0)
        egg(d, cs[0], tx, ty)
        P.inked(d, [(tx - tw * .48, top + 6), (tx + tw * .48, top + 6)] + hem_pts(tx, hem, tw * .62, sway, n=4, amp=4), col(cs[0]), 17)
        P.poly(d, [(tx + 4, top + 14), (tx + tw * .46, top + 14), (tx + tw * .6 + sway * .5, hem - 6), (tx + 4 + sway * .5, hem - 6)], col(cs[1] if not back else cs[0]))
        n = len(cs)
        for i, t in enumerate((-.62, -.28, .06, .4)):
            if back:
                break
            y = ty + th * t + 40
            for j, u in enumerate((-.24, .24)):
                x = tx + u * tw + (sway * .3 if t > 0 else 0)
                P.inked(d, [(x, y - 52), (x + 40, y), (x, y + 52), (x - 40, y)], col(cs[2 + (i + j) % (n - 2)]), 5)
        for k in range(7):
            u = -1 + 2 * k / 6
            x = tx + u * tw * .58 + sway
            P.inked(d, [(x - 26, hem - 10), (x + 26, hem - 10), (x, hem + 40)], col(cs[(k + 2) % n]), 5)
        if back:
            return
        for k in range(5):
            x = tx - 120 + k * 60
            P.inked(d, [(x - 32, top - 6), (x + 32, top - 6), (x, top + 56)], col(cs[(k + 3) % n]), 5)
        P.inked(d, [(tx - tw * .5, ty + th * .28), (tx + tw * .5, ty + th * .28), (tx + tw * .52, ty + th * .36), (tx - tw * .52, ty + th * .36)], col(c.get('belt') or (70, 44, 26)), 6)
        P.rrect(d, tx - 18, ty + th * .28 + 2, tx + 18, ty + th * .36 - 2, 3, col(GOLD), INK, 4)
    elif st == 'saree':
        sc, bl = c['saree'], c['blouse']
        egg(d, bl, tx, ty)
        skirt(d, dict(c, skirt=sc, skirt_y0=.02, skirt_top=.5), tx, ty, back, c.get('hem', 0))
        if back:
            P.inked(d, [(tx - tw * .3, top + 70), (tx + tw * .3, top + 70), (tx + tw * .42, ty + th * .36), (tx - tw * .1, ty + th * .42)], dk(sc, .86), 6)
            return
        P.inked(d, [(tx - tw * .34 - 30, top + 6), (tx - tw * .34 + 38, top - 4), (tx + tw * .52, ty + th * .34), (tx + tw * .52 - 78, ty + th * .46)], dk(sc, .9), 7)
        P.stroke(d, [(tx - tw * .34 + 4 + (tw * .86 - 6) * t / 40, top + 2 + (ty + th * .4 - top - 2) * t / 40) for t in range(41)], 8, col(GOLD), amp=0)


def hem_pts(tx, hem, hw, sway=0.0, n=6, amp=8):
    """Bottom edge of a long garment, right to left: a gently scalloped hem that sways sideways by `sway` px (more at the bottom corners)."""
    out = []
    for i in range(n + 1):
        u = i / n
        out.append((tx + hw * (1 - 2 * u) + sway * (.55 + .45 * math.cos(u * 3.4)), hem + amp * math.sin(u * 6.3 + 1)))
    return out


def skirt(d, c, tx, ty, back, sway=0.0):
    """Skirt under the torso: drawn BEFORE it. skirt=rgb, skirt_hem=y of the hem (default knee length), skirt_flare, skirt_trim=rgb (border band)."""
    tw, th = P.TOR_W, P.TOR_H
    hem = c.get('skirt_hem', P.FEET - 300)
    fl = c.get('skirt_flare', .62)
    y0 = ty + th * c.get('skirt_y0', .16)
    tp = c.get('skirt_top', .44)
    P.inked(d, [(tx - tw * tp, y0), (tx + tw * tp, y0)] + hem_pts(tx, hem, tw * fl, sway, n=6, amp=6), col(c['skirt']), 15)
    if c.get('skirt_trim'):
        def hw(y):
            return tw * (tp + (fl - tp) * (y - y0) / (hem - y0))
        y1, y2 = hem - 74, hem - 30
        P.inked(d, [(tx - hw(y1) + sway * .45, y1), (tx + hw(y1) + sway * .45, y1), (tx + hw(y2) + sway * .5, y2), (tx - hw(y2) + sway * .5, y2)], col(c['skirt_trim']), 5)
    if not back:
        for u in (-.5, -.17, .17, .5):
            line(d, (tx + u * tw * .7, y0 + 96), (tx + u * tw * fl * 1.9 + sway * .5, hem - 18), 5, dk(c['skirt'], .72))


def hat_art(kind, view, c):
    S = 1400
    im = Image.new('RGBA', (S * SS, S * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    o, y0, sx = 700, 700, 700 + (34 if view == 'q_r' else 0)
    hc = col(c.get('hat_col', (200, 200, 200)))
    show_face = view != 'back'
    def pts(lst, x0=sx):
        return [(x0 + x, y0 + y) for x, y in lst]
    def dome(rx, ry, base, fill, ink=9, cx=None):
        cx = sx if cx is None else cx
        b = [q for q in P.blob(cx, y0 + base, rx, ry, amp=.002, seed=2, sq=2.3) if q[1] <= y0 + base]
        P.inked(d, b, fill, ink)
    if kind == 'crown':
        P.inked(d, pts([(-172, -112), (172, -112), (182, -196), (232, -318), (128, -228), (72, -342), (0, -236), (-72, -342), (-128, -228), (-232, -318), (-182, -196)]), (170, 24, 50, 255), 2)
        P.inked(d, pts([(-190, -106), (190, -106), (206, -200), (244, -336), (136, -236), (80, -366), (0, -248), (-80, -366), (-136, -236), (-244, -336), (-206, -200)]), col(GOLD), 10)
        P.inked(d, pts([(-192, -152), (192, -152), (190, -104), (-190, -104)]), col(GOLD_D), 7)
        for x, cl in ((-112, (46, 110, 210)), (0, (210, 30, 60)), (112, (46, 170, 110))):
            dot(d, sx + x, y0 - 128, 18, col(cl), 4)
        for x, y in ((-244, -340), (-80, -372), (80, -372), (244, -340)):
            dot(d, sx + x, y0 + y, 17, col(WHITE), 4)
    elif kind == 'helm':
        P.stroke(d, P.bez((sx, y0 - 240), (sx - 60, y0 - 420), (sx - 210, y0 - 380), 40), 54, (200, 40, 50, 255), amp=.02)
        dome(258, 200, -70, col(STEEL), 11)
        P.inked(d, pts([(-262, -96), (262, -96), (262, -56), (-262, -56)]), col(STEEL_D), 7)
        P.inked(d, pts([(-22, -262), (22, -262), (22, -60), (-22, -60)]), col(GOLD), 5)
    elif kind == 'hardhat':
        dome(226, 196, -112, hc, 11)
        P.inked(d, pts([(-30, -304), (30, -304), (34, -116), (-34, -116)]), dk(hc, .86), 4)
        P.inked(d, pts([(-274, -122), (274, -122), (292, -92), (-292, -92)]), dk(hc, .9), 9)
    elif kind == 'helmet':
        dome(258, 216, -86, hc, 11)
        P.inked(d, pts([(-270, -96), (270, -96), (280, -62), (-280, -62)]), dk(hc, .8), 8)
    elif kind == 'peaked':
        P.inked(d, pts([(-196, -128), (196, -128), (272, -252), (150, -296), (-150, -296), (-272, -252)]), hc, 10)
        P.inked(d, pts([(-200, -146), (200, -146), (200, -106), (-200, -106)]), (24, 24, 30, 255), 6)
        if show_face:
            P.inked(d, pts([(-210, -110), (210, -110), (170, -60), (-170, -60)]), (20, 20, 26, 255), 6)
            dot(d, sx, y0 - 192, 32, col(GOLD), 6)
    elif kind == 'toque':
        for x, y, r in ((-130, -300, 96), (130, -300, 96), (-60, -372, 104), (60, -372, 104), (0, -300, 120)):
            dot(d, sx + x, y0 + y, r, col(WHITE), 9)
        P.inked(d, pts([(-196, -256), (196, -256), (206, -112), (-206, -112)]), col(WHITE), 9)
        for x in (-120, -40, 40, 120):
            line(d, (sx + x, y0 - 240), (sx + x, y0 - 130), 5, (206, 206, 212, 255))
    elif kind == 'tophat':
        P.inked(d, pts([(-168, -130), (168, -130), (190, -420), (-190, -420)]), (24, 24, 30, 255), 10)
        P.inked(d, pts([(-170, -192), (170, -192), (170, -138), (-170, -138)]), (170, 30, 50, 255), 4)
        P.inked(d, pts([(-268, -142), (268, -142), (276, -106), (-276, -106)]), (20, 20, 26, 255), 8)
    elif kind == 'straw':
        dome(186, 150, -118, (232, 196, 110, 255), 9)
        P.inked(d, pts([(-188, -152), (188, -152), (190, -118), (-190, -118)]), (170, 60, 50, 255), 5)
        P.inked(d, pts([(-352, -122), (352, -122), (300, -82), (-300, -82)]), (232, 196, 110, 255), 10)
    elif kind == 'pointed':
        # medieval peaked cap with a long feather
        P.stroke(d, P.bez((sx + 120, y0 - 190), (sx + 260, y0 - 420), (sx + 150, y0 - 560), 40), 34, col(c.get('feather', (226, 60, 50))), amp=.02)
        P.inked(d, pts([(-230, -120), (230, -120), (150, -230), (40, -330), (-110, -470), (-120, -300), (-200, -210)]), hc, 11)
        P.inked(d, pts([(-250, -150), (250, -150), (262, -104), (-262, -104)]), col(c.get('hat_band', (240, 196, 60))), 7)
    elif kind == 'beret':
        # soft medieval burgher cap
        dome(250, 120, -118, hc, 10)
        P.inked(d, pts([(-240, -140), (240, -140), (236, -102), (-236, -102)]), dk(hc, .8), 6)
    elif kind == 'wimple':
        # linen veil over the hair, falling to the shoulders
        for sg in (-1, 1):
            P.inked(d, pts([(sg * 200, -160), (sg * 290, -60), (sg * 300, 200), (sg * 220, 230), (sg * 236, -40)]), hc, 9)
        dome(262, 230, -100, hc, 10)
    elif kind == 'wig':
        for x, y in [(sgn * xx, yy) for sgn in (-1, 1) for xx, yy in ((256, 30), (262, -40), (254, -110), (216, -168), (154, -214), (80, -240))] + [(0, -250)]:
            dot(d, sx + x, y0 + y, 56, col(c['hair']), 8)
        for sg in (-1, 1):
            dot(d, sx + sg * 262, y0 + 98, 54, col(c['hair']), 8)
    elif kind == 'headset':
        P.stroke(d, [(sx + 262 * math.cos(a), y0 - 26 + 214 * math.sin(a) * 1.02) for a in [math.pi + t * math.pi / 60 for t in range(61)]], 24, (34, 36, 44, 255), amp=0)
        for sg in (-1, 1):
            P.rrect(d, sx + sg * 262 - 34, y0 - 64, sx + sg * 262 + 34, y0 + 44, 14, (64, 68, 82, 255), INK, 7)
        if show_face:
            P.stroke(d, P.bez((sx - 262, y0 + 40), (sx - 240, y0 + 150), (sx - 100, y0 + 138), 30), 11, (34, 36, 44, 255), amp=0)
            dot(d, sx - 96, y0 + 138, 17, (226, 60, 60, 255), 4)
    elif kind == 'mirror':
        P.inked(d, pts([(-252, -128), (252, -128), (246, -92), (-246, -92)]), (34, 36, 44, 255), 4)
        if show_face:
            dot(d, sx, y0 - 136, 64, col(STEEL), 8)
            dot(d, sx, y0 - 136, 18, (60, 66, 80, 255), 4)
    elif kind == 'goggles':
        P.inked(d, pts([(-252, -112), (252, -112), (246, -78), (-246, -78)]), (40, 40, 48, 255), 4)
        if show_face:
            for sg in (-1, 1):
                dot(d, sx + sg * 74, y0 - 112, 62, (150, 214, 226, 255), 10)
    elif kind == 'bubble':
        d.ellipse([(sx - 322) * SS, (y0 - 300) * SS, (sx + 322) * SS, (y0 + 300) * SS], outline=INK, width=15 * SS)
        d.ellipse([(sx - 310) * SS, (y0 - 288) * SS, (sx + 310) * SS, (y0 + 288) * SS], outline=(214, 226, 238, 255), width=8 * SS)
        P.stroke(d, [(sx + 262 * math.cos(a), y0 + 244 * math.sin(a)) for a in [math.radians(205 + t) for t in range(0, 44, 2)]], 20, (250, 250, 255, 255), amp=0)
    return im


def role_prop(d, kind, p):
    (lx, ly), (rx, ry) = p['hand_l'], p['hand_r']
    if kind == 'scepter':
        P.inked(d, [(rx - 13, ry + 90), (rx + 13, ry + 90), (rx + 13, ry - 330), (rx - 13, ry - 330)], col(GOLD), 7)
        dot(d, rx, ry - 370, 52, col(GOLD), 8)
        dot(d, rx, ry - 370, 22, (200, 30, 60, 255), 4)
    elif kind == 'shield':
        cx, cy = lx - 26, ly - 30
        P.inked(d, [(cx - 148, cy - 176), (cx + 148, cy - 176), (cx + 148, cy + 34), (cx + 70, cy + 150), (cx, cy + 212), (cx - 70, cy + 150), (cx - 148, cy + 34)], col(GOLD), 13)
        P.inked(d, [(cx - 112, cy - 140), (cx + 112, cy - 140), (cx + 112, cy + 24), (cx + 50, cy + 122), (cx, cy + 166), (cx - 50, cy + 122), (cx - 112, cy + 24)], (40, 70, 160, 255), 5)
        P.inked(d, [(cx - 16, cy - 104), (cx + 16, cy - 104), (cx + 16, cy - 30), (cx + 72, cy - 30), (cx + 72, cy + 2), (cx + 16, cy + 2), (cx + 16, cy + 110), (cx - 16, cy + 110), (cx - 16, cy + 2), (cx - 72, cy + 2), (cx - 72, cy - 30), (cx - 16, cy - 30)], col(GOLD), 4)
    elif kind == 'sword':
        P.inked(d, [(rx - 20, ry - 38), (rx + 20, ry - 38), (rx + 20, ry - 470), (rx, ry - 530), (rx - 20, ry - 470)], (222, 228, 236, 255), 8)
        P.inked(d, [(rx - 84, ry - 52), (rx + 84, ry - 52), (rx + 84, ry - 24), (rx - 84, ry - 24)], col(GOLD), 6)
        P.inked(d, [(rx - 13, ry - 26), (rx + 13, ry - 26), (rx + 13, ry + 54), (rx - 13, ry + 54)], (96, 60, 34, 255), 6)
    elif kind == 'pipe':
        # wooden pipe held in both hands, mouth end up at the lips (drawn under the head)
        mx, my = 604, 760
        ex, ey = rx + (rx - mx) * .7, ry + (ry - my) * .7
        P.inked(d, [(mx - 14, my), (mx + 14, my), (ex + 18, ey), (ex - 18, ey)], (150, 98, 52, 255), 7)
        for t in (.45, .58, .71):
            dot(d, mx + (ex - mx) * t, my + (ey - my) * t, 7, (40, 26, 18, 255), 2)
        dot(d, ex, ey, 22, (120, 76, 40, 255), 5)
    elif kind == 'blueprint':
        P.inked(d, [(lx - 26, ly - 210), (lx + 26, ly - 210), (lx + 26, ly + 120), (lx - 26, ly + 120)], (60, 110, 190, 255), 8)
        dot(d, lx, ly - 210, 26, (200, 220, 244, 255), 5)
    elif kind == 'wrench':
        P.inked(d, [(rx - 18, ry + 60), (rx + 18, ry + 60), (rx + 18, ry - 180), (rx - 18, ry - 180)], col(STEEL), 7)
        P.inked(d, [(rx - 58, ry - 262), (rx - 22, ry - 262), (rx - 16, ry - 214), (rx + 16, ry - 214), (rx + 22, ry - 262), (rx + 58, ry - 262), (rx + 44, ry - 170), (rx - 44, ry - 170)], col(STEEL), 8)
    elif kind == 'pistol':
        a = math.radians(p.get('gun_rot', 0))
        turn = lambda pts: [(rx + x * math.cos(a) - y * math.sin(a), ry + x * math.sin(a) + y * math.cos(a)) for x, y in pts]
        P.inked(d, turn([(-46, -34), (30, -34), (40, 84), (-40, 84)]), (58, 44, 36, 255), 8)
        P.inked(d, turn([(-62, -92), (230, -92), (230, -30), (-62, -30)]), (52, 56, 66, 255), 9)
        P.inked(d, turn([(204, -106), (224, -106), (224, -90), (204, -90)]), (52, 56, 66, 255), 4)
    elif kind == 'shotgun':  # 1850s double-barrel held across the body: stock at the right hand, barrels out past the left hand
        ux, uy = lx - rx, ly - ry
        n = math.hypot(ux, uy) or 1
        ux, uy = ux / n, uy / n
        nx, ny = -uy, ux
        at = lambda t, s: (rx + ux * t + nx * s, ry + uy * t + ny * s)
        P.inked(d, [at(-200, -34), at(30, -20), at(30, 20), at(-200, 50)], (122, 74, 40, 255), 7)
        P.inked(d, [at(20, -16), at(n + 330, -16), at(n + 330, 16), at(20, 16)], (60, 64, 74, 255), 7)
        P.inked(d, [at(30, 14), at(n * .8, 14), at(n * .8, 34), at(30, 34)], (122, 74, 40, 255), 5)
    elif kind == 'lantern':  # hand lantern hung from the left hand, warm glass
        cx, cy = lx, ly + 150
        P.inked(d, [(cx - 8, ly), (cx + 8, ly), (cx + 8, cy - 70), (cx - 8, cy - 70)], (40, 36, 34, 255), 4)
        P.inked(d, [(cx - 60, cy - 76), (cx + 60, cy - 76), (cx + 46, cy - 50), (cx - 46, cy - 50)], (52, 48, 44, 255), 6)
        P.inked(d, [(cx - 44, cy - 50), (cx + 44, cy - 50), (cx + 50, cy + 60), (cx - 50, cy + 60)], (255, 214, 120, 255), 7)
        dot(d, cx, cy + 6, 20, (255, 246, 210, 255), 3)
        P.inked(d, [(cx - 62, cy + 60), (cx + 62, cy + 60), (cx + 62, cy + 84), (cx - 62, cy + 84)], (52, 48, 44, 255), 6)
    elif kind == 'flask':
        cx, cy = rx, ry - 92
        P.inked(d, [(cx - 22, cy - 112), (cx + 22, cy - 112), (cx + 22, cy - 40), (cx + 78, cy + 66), (cx - 78, cy + 66), (cx - 22, cy - 40)], (214, 236, 240, 255), 8)
        P.poly(d, [(cx - 44, cy), (cx + 44, cy), (cx + 70, cy + 58), (cx - 70, cy + 58)], (80, 210, 130, 255))
    elif kind == 'pan':
        P.inked(d, [(rx - 13, ry + 40), (rx + 13, ry + 40), (rx + 13, ry - 130), (rx - 13, ry - 130)], (86, 60, 40, 255), 6)
        dot(d, rx, ry - 216, 100, (54, 54, 62, 255), 9)
    elif kind == 'briefcase':
        cx, cy = rx, ry + 120
        P.inked(d, [(cx - 118, cy - 76), (cx + 118, cy - 76), (cx + 118, cy + 80), (cx - 118, cy + 80)], (112, 68, 38, 255), 10)
        P.rrect(d, cx - 40, cy - 112, cx + 40, cy - 74, 8, None, INK, 9)
        P.rrect(d, cx - 18, cy - 20, cx + 18, cy + 14, 3, col(GOLD), INK, 4)
    elif kind == 'moneybag':
        cx, cy = rx, ry + 130
        dot(d, cx, cy + 10, 108, (206, 178, 120, 255), 10)
        P.inked(d, [(cx - 34, cy - 118), (cx + 34, cy - 118), (cx + 22, cy - 80), (cx - 22, cy - 80)], (206, 178, 120, 255), 7)
        d.text((cx * SS, (cy + 10) * SS), '$', fill=(50, 100, 50, 255), font=dfont(), anchor='mm')
    elif kind == 'cup':  # paper cup in the right hand
        cx, cy = rx, ry - 70
        P.inked(d, [(cx - 62, cy - 96), (cx + 62, cy - 96), (cx + 44, cy + 86), (cx - 44, cy + 86)], (246, 244, 236, 255), 8)
        P.poly(d, [(cx - 58, cy - 40), (cx + 58, cy - 40), (cx + 54, cy - 8), (cx - 54, cy - 8)], (206, 40, 52, 255))
        P.poly(d, [(cx - 53, cy - 2), (cx + 53, cy - 2), (cx + 50, cy + 26), (cx - 50, cy + 26)], (30, 70, 160, 255))
        P.poly(d, [(cx - 56, cy - 92), (cx + 56, cy - 92), (cx + 54, cy - 80), (cx - 54, cy - 80)], (70, 36, 26, 255))
    elif kind in ('cola', 'vodka'):  # glass bottle held up in the right hand
        cx, cy = rx, ry - 110
        body = (60, 30, 22, 255) if kind == 'cola' else (226, 240, 246, 255)
        P.inked(d, [(cx - 16, cy - 150), (cx + 16, cy - 150), (cx + 18, cy - 80), (cx + 44, cy - 30), (cx + 44, cy + 130), (cx - 44, cy + 130), (cx - 44, cy - 30), (cx - 18, cy - 80)], body, 8)
        if kind == 'cola':
            dot(d, cx, cy + 40, 34, (246, 244, 236, 255), 5)
            P.poly(d, [(cx - 30, cy + 30), (cx + 30, cy + 30), (cx + 30, cy + 40), (cx - 30, cy + 40)], (206, 40, 52, 255))
            P.poly(d, [(cx - 30, cy + 42), (cx + 30, cy + 42), (cx + 30, cy + 52), (cx - 30, cy + 52)], (30, 70, 160, 255))
        else:
            P.inked(d, [(cx - 40, cy + 10), (cx + 40, cy + 10), (cx + 40, cy + 90), (cx - 40, cy + 90)], (246, 238, 220, 255), 5)
            P.poly(d, [(cx - 36, cy + 22), (cx + 36, cy + 22), (cx + 36, cy + 36), (cx - 36, cy + 36)], (196, 36, 40, 255))
        P.inked(d, [(cx - 18, cy - 168), (cx + 18, cy - 168), (cx + 18, cy - 148), (cx - 18, cy - 148)], (196, 36, 40, 255) if kind == 'cola' else (210, 180, 70, 255), 5)
    elif kind == 'pen':
        a = math.radians(p.get('pen_rot', -35))
        turn = lambda pts: [(rx + x * math.cos(a) - y * math.sin(a), ry + x * math.sin(a) + y * math.cos(a)) for x, y in pts]
        P.inked(d, turn([(-12, 0), (12, 0), (12, -170), (-12, -170)]), (30, 30, 40, 255), 6)
        P.inked(d, turn([(-12, -170), (12, -170), (0, -205)]), col(GOLD), 4)
    elif kind == 'camera':  # 1950s press camera with a flash reflector, held at the face from the right hand
        cx, cy = rx - 60, ry - 40
        P.inked(d, [(cx - 110, cy - 70), (cx + 110, cy - 70), (cx + 110, cy + 80), (cx - 110, cy + 80)], (52, 56, 66, 255), 9)
        dot(d, cx, cy + 6, 50, (40, 42, 50, 255), 8)
        dot(d, cx, cy + 6, 24, (150, 196, 226, 255), 4)
        P.inked(d, [(cx + 96, cy - 60), (cx + 120, cy - 60), (cx + 120, cy - 190), (cx + 96, cy - 190)], col(STEEL), 5)
        P.inked(d, [(cx + 30, cy - 190), (cx + 186, cy - 190), (cx + 150, cy - 280), (cx + 66, cy - 280)], (226, 230, 236, 255), 8)
    elif kind == 'tablet':
        cx, cy = lx + 30, ly - 90
        P.inked(d, [(cx - 92, cy - 128), (cx + 92, cy - 128), (cx + 92, cy + 128), (cx - 92, cy + 128)], (46, 48, 58, 255), 9)
        P.poly(d, [(cx - 74, cy - 106), (cx + 74, cy - 106), (cx + 74, cy + 106), (cx - 74, cy + 106)], (150, 204, 232, 255))


_F = {}


def dfont():
    from PIL import ImageFont
    if 'f' not in _F:
        _F['f'] = ImageFont.truetype(str(__import__('pathlib').Path(__file__).resolve().parents[2] / 'assets' / 'brand' / 'fonts' / 'Anton-Regular.ttf'), 110 * SS)
    return _F['f']
