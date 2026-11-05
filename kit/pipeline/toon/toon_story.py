"""Story helpers for toon reels. A reel's story.py does `from toon_story import *` and defines LEN, SHOTS, GRADE (see API.md). Plain Python, also runs inside Blender.
python toon_story.py <reel>   -> hand-vs-head overlap check over every card frame."""
import importlib.util
import json
import math
import random
import re
import sys
from pathlib import Path

M0 = .00115
RED_G = (1, 1, 1)


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def tk(f, keys):
    """Eased keys [(frame, number or tuple), ...]."""
    if f <= keys[0][0]:
        return keys[0][1]
    for (a, va), (b, vb) in zip(keys, keys[1:]):
        if f <= b:
            u = ease((f - a) / max(1, b - a))
            if isinstance(va, tuple):
                return tuple(x + (y - x) * u for x, y in zip(va, vb))
            return va + (vb - va) * u
    return keys[-1][1]


def st(f, keys):
    """Stepped keys [(frame, value), ...]."""
    v = keys[0][1]
    for a, x in keys:
        if f >= a:
            v = x
    return v


def over(t):
    """Pop with overshoot, 0 to 1."""
    t = max(0.0, min(1.0, t))
    return 1 + 2.7 * (t - 1) ** 3 + 1.7 * (t - 1) ** 2 if t > 0 else 0.0


def base(f, seed=0.0, **kw):
    """Idle life on every frame. kw overrides any pose key."""
    b = 5 * math.sin(f * .19 + seed) + 2.2 * math.sin(f * .47 + 1 + seed)
    p = dict(view='front', bob=b, lean=2.5 * math.sin(f * .11 + seed), tilt=-3 + 3.5 * math.sin(f * .13 + seed), hat_y=0, hat_rot=0,
             knee=16 * math.sin(f * .17 + seed), sweat=False, star=False, ham_rot=0, eyes='smug', brows='flat', mouth='tick',
             hand_l=(430, 1240 + b), hand_r=(790, 1230 + b), bend_l=-70, bend_r=-70)
    if (f + int(seed * 30)) % 71 < 3:
        kw.setdefault('blink', True)
    p.update(kw)
    if p.pop('blink', False) and p['eyes'] in ('smug', 'dot'):
        p['eyes'] = 'shut'
    return p


def talk(f, seed=7):
    """Mouth shape that changes every 3 f."""
    r = random.Random(seed + f // 3)
    return r.choice(('o', 'wide', 'line', 'smile', 'open', 'pout'))


def walking(p, f, v, T=12, dirn=1):
    """v in px per frame across the card; feet stay planted against the ground motion, arms swing."""
    stride = v * T / 2
    feet = []
    for ph in (f / T, f / T + .5):
        u = ph % 1
        if u < .5:
            feet.append((600 + dirn * stride * (.5 - 2 * u), 0.0))
        else:
            q = (u - .5) * 2
            feet.append((600 + dirn * stride * (-.5 + ease(q)), 62 * math.sin(q * math.pi)))
    p['feet'], p['toe'], p['hip'] = feet, dirn, 16
    p['view'] = 'q_r' if dirn > 0 else p['view']
    s = math.sin(f * 2 * math.pi / T)
    p['bob'] = 12 * abs(s)
    p['lean'] = 8 * dirn
    if not p.get('prop'):
        p['hand_l'], p['hand_r'] = (430 + 90 * s, 1240 + p['bob']), (790 - 90 * s, 1230 + p['bob'])
    return p


LAPTOP = dict(prop='laptop', hand_l=(392, 1185), hand_r=(812, 1185), bend_l=-60, bend_r=-60)
CHEER = dict(hand_l=(205, 640), hand_r=(1000, 640), bend_l=-60, bend_r=-60)
SHOCK = dict(hand_l=(235, 700), hand_r=(975, 700), bend_l=-90, bend_r=-90, eyes='ring', brows=None, mouth='open', sweat=True)
SHRUG = dict(hand_l=(240, 1010), hand_r=(960, 1010), bend_l=-110, bend_r=-110, eyes='dot', brows='up', mouth='line', tilt=8)
SLUMP = dict(hand_l=(440, 1320), hand_r=(770, 1320), bend_l=-40, bend_r=-40, eyes='slit', brows='sad', mouth='pout', tilt=-11, lean=-14, bob=26)
HAPPY = dict(eyes='happy', brows=None, mouth='smile')
SIT = dict(sit=True, hand_l=(470, 1575), hand_r=(730, 1575), bend_l=-40, bend_r=-40)                       # seated, hands on lap (seat comes from the world)
SIT_DESK = dict(sit=True, hand_l=(455, 1410), hand_r=(745, 1410), bend_l=-80, bend_r=-80)                  # seated behind a desk, hands forward as if typing
TURN = dict(body='q', view='q_r')                                                                           # three-quarter body, near arm = hand_l
TURN_BACK = dict(body='q_back', view='back')
HIGH = dict(foreshorten=.6)                                                                                  # high camera / lying: big head, small body
REACH = dict(hand_r=(930, 800), stretch_r=2.6, bend_r=-30)                                                  # right arm stretches far beyond normal
POSES = dict(idle={}, laptop=LAPTOP, cheer=CHEER, shock=SHOCK, shrug=SHRUG, slump=SLUMP, happy=HAPPY, sit=SIT, sit_desk=SIT_DESK, turn=TURN, turn_back=TURN_BACK, high=HIGH, reach=REACH)


def card(cid, x, y, z=0.0, M=M0, sq=1.0, grade=RED_G, pose=None, src=None):
    """One picture card: character cid standing at world (x, y, z). M = metres per card pixel, sq = width squeeze."""
    return dict(id=cid, x=x, y=y, z=z, M=M, sq=sq, grade=grade, pose=pose, src=src or cid)


def axis(g, cam, tgt, y, off):
    """World x that sits on the camera's line at depth y, plus an offset: keeps a walker framed."""
    c_, t_ = tk(g, cam), tk(g, tgt)
    return c_[0] + (t_[0] - c_[0]) * (y - c_[1]) / (t_[1] - c_[1]) + off


def _k(f, v):
    return v(f) if callable(v) else tk(f, v) if isinstance(v, list) else v


# ---- framing: the study's reels mostly hold heads at 12-35 % of frame width, off-centre, from low down. Frame width at distance d = d * 16 / lens.
HEAD_PX, HEAD_Y = 530, 1240  # head width and head-centre height above the feet, in card px


def frame_w(d, lens=24):
    return d * 16 / lens


def hero_cam(x, y, z=0.0, M=M0, pct=.3, lens=24, side=.14, height=None, angle=-14, eye=.24):
    """Camera and target that frame a card at (x, y, z): head pct of frame width, hero off to one side (side = fraction of width, + puts them right of centre, 0 = centred), head near the upper third (eye = how far above centre, as a fraction of frame width).
    height = camera height (default about knee level, looking up), angle = degrees round the hero. Use: shot(set, **dolly(*hero_cam(0, 0), a, b), cards=[...])."""
    d = HEAD_PX * M / pct * lens / 16
    w = frame_w(d, lens)
    head_z = z + HEAD_Y * M
    a = math.radians(angle)
    cz = (z + .45) if height is None else height
    cam = (x + d * math.sin(a), y - d * math.cos(a), cz)
    # aim at the head's depth, moved so the head lands off-centre and high in frame
    tgt = (x - side * w * math.cos(a), y - side * w * math.sin(a), head_z - eye * w)
    return cam, tgt


def head_pct(c, cam_pos, lens):
    """Share of frame width taken by this card's head."""
    d = max(.2, math.dist(cam_pos, (c['x'], c['y'], c['z'] + HEAD_Y * c['M'])))
    return 100 * HEAD_PX * c['M'] / frame_w(d, lens)


def shake(move, hits, amp=.05, life=12):
    """Camera shake on hits (a frame or list). move = dict from push etc.; returns it with shaking cam and tgt, decaying over life frames."""
    hits = [hits] if isinstance(hits, int) else hits
    cam0, tgt0 = move['cam'], move['tgt']

    def off(f, seed):
        amt = 0.0
        for h in hits:
            if 0 <= f - h <= life:
                amt += amp * (1 - (f - h) / life) ** 1.5
        return amt * math.sin(f * 2.1 + seed), amt * math.sin(f * 2.9 + seed * 2)

    def cam_(f):
        p = _k(f, cam0)
        o = off(f, 1)
        return p[0] + o[0], p[1], p[2] + o[1]

    def tgt_(f):
        p = _k(f, tgt0)
        o = off(f, 4)
        return p[0] + o[0], p[1], p[2] + o[1]
    return dict(move, cam=cam_, tgt=tgt_)


# ---- acting: pose lists change with a wind-up, an overshoot and a settle (the shot builder eases between stepped poses). Hand spots stay clear of the head box.
POINT_R = dict(hand_l=(430, 1240), hand_r=(1060, 800), bend_l=-60, bend_r=-60, tilt=-4, eyes='smug', brows='flat')
POINT_L = dict(hand_l=(140, 800), hand_r=(780, 1240), bend_l=60, bend_r=60, tilt=4, eyes='smug', brows='flat')
EXPLAIN = dict(hand_l=(280, 1050), hand_r=(930, 1000), bend_l=-100, bend_r=-110, tilt=3, eyes='dot', brows='up', mouth='open')
THINK = dict(hand_l=(440, 1230), hand_r=(830, 960), bend_l=-70, bend_r=-125, tilt=7, eyes='slit', brows='flat', mouth='line')
LEAN_IN = dict(lean=26, tilt=-7, hand_l=(330, 1160), hand_r=(900, 1160), bend_l=-80, bend_r=-80, eyes='smug', brows='angry', mouth='smile')
RECOIL = dict(lean=-30, tilt=11, hand_l=(250, 930), hand_r=(960, 930), bend_l=-110, bend_r=-110, eyes='ring', brows=None, mouth='o', sweat=True)
SMUG = dict(eyes='smug', brows='flat', mouth='smile', tilt=-6, hand_l=(390, 1290), hand_r=(820, 1290), bend_l=40, bend_r=-40)
GRIT = dict(eyes='slit', brows='angry', mouth='wide', tilt=-5, lean=10, hand_l=(390, 1110), hand_r=(820, 1110), bend_l=-120, bend_r=-120)
DEFEAT = dict(SLUMP, eyes='shut')
POSES.update(point_r=POINT_R, point_l=POINT_L, explain=EXPLAIN, think=THINK, lean_in=LEAN_IN, recoil=RECOIL, smug=SMUG, grit=GRIT, defeat=DEFEAT)
ACT_SET = ('explain', 'think', 'point_r')
_EASE_F, _WIND_F = 6, 3  # frames to move between poses, frames of wind-up before it


class Acted(list):
    """Pose keys the shot builder eases between. A plain list stays hard-stepped, so older reels render as they did."""


def acted(keys):
    """Your own pose keys with wind-up, overshoot and settle: pose=acted([(f, 'point_r'), (f2, 'recoil')])."""
    return Acted(sorted(keys, key=lambda x: x[0]))


def acting(a, b, every=50, seed=1, poses=ACT_SET, at=None):
    """Stepped pose keys [(f, pose), ...] for a talking stretch a..b: a new whole-body pose about every `every` frames, never the same twice running. at={frame: pose} puts chosen poses on key words."""
    r = random.Random(seed)
    keys, f, last = [], a, None
    while f < b:
        p = r.choice([x for x in poses if x != last])
        keys.append((f, p))
        last = p
        f += every + r.randint(-6, 6)
    for k, v in (at or {}).items():
        keys = [x for x in keys if abs(x[0] - k) > 8] + [(k, v)]
    return acted(keys)


def _mix(a, b, u):
    out = dict(b)
    for k, vb in b.items():
        va = a.get(k)
        if isinstance(vb, (int, float)) and not isinstance(vb, bool) and isinstance(va, (int, float)) and not isinstance(va, bool):
            out[k] = va + (vb - va) * u
        elif isinstance(vb, tuple) and isinstance(va, tuple) and len(va) == len(vb) and all(isinstance(x, (int, float)) for x in vb + va):
            out[k] = tuple(x + (y - x) * u for x, y in zip(va, vb))
        elif u < .5 and k in a:
            out[k] = a[k]
    return out


def _acted(f, keys, seed):
    """Pose at f from stepped keys, with wind-up, overshoot and settle. Returns pose, squash (+ wide, - tall)."""
    cur = 0
    for i, (a_, _) in enumerate(keys):
        if f >= a_:
            cur = i
    def pose_of(i):
        p = keys[i][1]
        return base(f, seed, **(POSES[p] if isinstance(p, str) else p))
    now = pose_of(cur)
    squash = 0.0
    if cur + 1 < len(keys) and keys[cur + 1][0] - f <= _WIND_F:  # wind-up: lean away before the change
        u = 1 - (keys[cur + 1][0] - f) / _WIND_F
        nxt = pose_of(cur + 1)
        away = 1 if nxt.get('lean', 0) < now.get('lean', 0) else -1
        now['lean'] = now.get('lean', 0) + away * 12 * u
        now['bob'] = now.get('bob', 0) + 10 * u
        squash = .05 * u
    if cur > 0:
        t = f - keys[cur][0]
        if t < _EASE_F:
            u = over((t + 1) / _EASE_F)
            now = _mix(pose_of(cur - 1), now, u)
        if t < 10:  # landing squash, hat and hem still catching up
            q = math.sin(t / 10 * math.pi)
            squash -= .06 * q
            now['hat_rot'] = now.get('hat_rot', 0) + 7 * math.sin(t * .9) * (1 - t / 10)
            now['hem'] = now.get('hem', 0) + 14 * math.sin(t * .9) * (1 - t / 10)
    return now, squash


# ---- camera moves: each returns dict(cam=keys, tgt=keys, roll=keys); use as shot(set, **push(...), lens=24, cards=...)
def track(cam, tgt, a, b, dist=1.0, roll=1.5):
    """Sideways past the scene, target following part of the way: near things slide against far ones."""
    return dict(cam=[(a, cam), (b, (cam[0] + dist, cam[1], cam[2]))], tgt=[(a, tgt), (b, (tgt[0] + dist * .55, tgt[1], tgt[2]))], roll=[(a, -roll / 2), (b, roll / 2)])


def dolly(cam, tgt, a, b, pct=.5, drift=.4, roll=3.0):
    """New reels: a push strong enough to read on a phone. Plain push keeps its old gentle size so older reels re-render the same."""
    return push(cam, tgt, a, b, pct, drift, roll)


def dolly_out(cam, tgt, a, b, pct=.5, drift=.4, roll=3.0):
    return pull(cam, tgt, a, b, pct, drift, roll)


def push(cam, tgt, a, b, pct=.2, drift=.12, roll=2.0):
    """The staple: dolly pct of the way to the target over a..b, with a little sideways drift and roll against it. Keys run past both ends, so the move is already going at frame a."""
    pad = max(8, (b - a) // 4)
    def at(u):
        v = tuple(c + (t - c) * pct * u for c, t in zip(cam, tgt))
        return (v[0] + drift * (u - .5), v[1], v[2])
    return dict(cam=[(a - pad, at(-pad / (b - a))), (b + pad, at(1 + pad / (b - a)))], tgt=tgt, roll=[(a - pad, -roll / 2), (b + pad, roll / 2)])


def pull(cam, tgt, a, b, pct=.2, drift=.12, roll=2.0):
    """A push run backwards: cam is where it starts, nearest the hero."""
    m = push(cam, tgt, a, b, -pct, drift, roll)
    return m


def wide_push(wide, close, tgt, a, b, hold=20):
    """New place: open on the wide for `hold` frames (still drifting), then push to the close framing."""
    d = tuple((c - w) * .03 for w, c in zip(wide, close))
    return dict(cam=[(a - 6, wide), (a + hold, tuple(w + x for w, x in zip(wide, d))), (b, close)], tgt=tgt, roll=[(a, 1.5), (b, -1)])


def arc(tgt, r, z, a, b, deg0, deg1):
    """Orbit round the target: near and far things slide opposite ways. Angle 0 = straight in from -Y, positive = to the right."""
    n = 6
    pts = []
    for i in range(n + 1):
        d = math.radians(deg0 + (deg1 - deg0) * i / n)
        pts.append((a + (b - a) * i / n, (tgt[0] + r * math.sin(d), tgt[1] - r * math.cos(d), z)))
    return dict(cam=pts, tgt=tgt, roll=[(a, 1), (b, -1)])


def crane(cam, tgt, a, b, up=2.0, tilt=1.5):
    """Rise and tilt up, for facades and reveals."""
    return dict(cam=[(a, cam), (b, (cam[0], cam[1], cam[2] + up))], tgt=[(a, tgt), (b, (tgt[0], tgt[1], tgt[2] + tilt))], roll=[(a, -1), (b, 1)])


def low(pos, z=.45):
    """Same camera spot, down at shin height: the look's usual angle."""
    return (pos[0], pos[1], z)


# ---- colour worlds: a shot's look=... sets the sun and sky for that shot and grades the characters to match
LOOKS = dict(
    noon=dict(light=dict(sun='#fff4dc', sun_energy=2.6, world='#dfeeff', world_strength=.5, sun_rot=(50, 0, -30)), grade=(1, 1, 1)),
    # golden, dusk, moon, sick: brighter, a cool world fill against a warm key so every set holds two opposite colours (laughter test, 2026-11-03)
    golden=dict(light=dict(sun='#ffc78a', sun_energy=3.0, world='#a8c4e8', world_strength=.8, sun_rot=(62, 0, -60)), grade=(1, .97, .92)),
    dusk=dict(light=dict(sun='#ffb07a', sun_energy=3.4, world='#8a9ad0', world_strength=1.05, sun_rot=(62, 0, -60)), grade=(1, .93, .9)),
    moon=dict(light=dict(sun='#a8c4ff', sun_energy=2.4, world='#46609a', world_strength=1.25, sun_rot=(52, 0, 35)), grade=(.86, .9, 1.0)),
    sick=dict(light=dict(sun='#e2e8a4', sun_energy=3.2, world='#8fa6b8', world_strength=1.3, sun_rot=(58, 0, -40)), grade=(.96, 1, .88)),
    night=dict(light=dict(sun='#8fa8ff', sun_energy=1.2, world='#2a3560', world_strength=.5, sun_rot=(60, 0, 40)), grade=(.62, .68, .92)),
    fire=dict(light=dict(sun='#ff7a2e', sun_energy=2.8, world='#5a2a20', world_strength=.5, sun_rot=(70, 0, 70)), grade=(1, .72, .5)),
    neon=dict(light=dict(sun='#d060ff', sun_energy=1.6, world='#102a50', world_strength=.7, sun_rot=(65, 0, 30)), grade=(.78, .72, 1)),
    alarm=dict(light=dict(sun='#ff3030', sun_energy=2.4, world='#401418', world_strength=.6, sun_rot=(55, 0, 0)), grade=(1, .55, .55)),
    office=dict(light=dict(sun='#fff6e6', sun_energy=2.4, world='#eef2ff', world_strength=.8, sun_rot=(40, 0, -20)), grade=(1, .99, .96)),
)


RIMS = dict(noon=dict(col=(255, 244, 214), shade=(70, 80, 150)), golden=dict(col=(255, 196, 120), shade=(110, 60, 110)), dusk=dict(col=(255, 150, 110), shade=(70, 50, 120)), night=dict(col=(150, 180, 255), shade=(20, 26, 80)),
            sick=dict(col=(214, 232, 130), shade=(50, 70, 44)), moon=dict(col=(255, 170, 90), shade=(20, 28, 84)),
            fire=dict(col=(255, 150, 60), shade=(70, 24, 40)), neon=dict(col=(230, 110, 255), shade=(20, 50, 110)), alarm=dict(col=(255, 90, 80), shade=(60, 10, 30)), office=dict(col=(255, 248, 228), shade=(90, 100, 150)))


FX_LIFE = dict(smoke=34, fire=40, boom=30, sparks=22, dust=26, debris=34, money=70, confetti=70, steam=24, sweat=14, impact=8, column=70, shatter=45, lines=10, sparkle=18, anger=18, motes=120, puffring=24)


def burst(kind, f, f0, x, y, size=200, seed=1, **kw):
    """One effect as an fx item, [] outside its life. Kinds and lives in FX_LIFE. fx=dict(x=,y=,z=,items=burst(...)+burst(...))."""
    age = f - f0
    if age < 0 or age > kw.get('life', FX_LIFE[kind]):
        return []
    return [(kind, x, y, size, age, seed, kw)]


def peak(f, f0, x=600, y=1450, size=620, seed=1, col=None):
    """A visual peak, 2-3 s: flash and speed lines, shards, fire, then a dark rising column. Use with M about .0026 so it fills 40 %+ of the frame, plus shake() on the camera and a flash join or GRADE lift. y counts up from the feet at y=1860: at M .0026, y 1450 is about 1 m off the floor."""
    kw = dict(col=col) if col else {}
    return burst('lines', f, f0, x, y, size * 1.2, seed) + burst('column', f, f0 + 6, x, y + size * .3, size, seed + 1) + burst('boom', f, f0, x, y, size, seed + 2) + burst('shatter', f, f0, x, y, size, seed + 3, **kw) + burst('puffring', f, f0 + 1, x, y + size * .6, size, seed + 4)


def fx_list(s):
    """state['fx'] may be one dict or a list of them (one card each, up to the free card slots)."""
    fx = s.get('fx')
    return [] if not fx else fx if isinstance(fx, list) else [fx]


def fx_dir(i):
    return 'FX' if i == 0 else f'FX{i}'


def shot(set, cam, tgt, lens=24, roll=0, cards=(), **extra):
    """Declarative shot -> state function. cam/tgt/lens/roll/card x,y,z: a value or keyed list [(f, v), ...].
    card: dict(id, x, y, z=0, M=M0, sq=1, grade, pose='name'|dict|stepped keys [(f, pose), ...], seed=0, walk=dict(v=, T=, dirn=), walk_on=(f0, f1), talk=(f0, f1)).
    extra keys (vis, texts, objs, screens, tickets, bills, fx, ...) pass through; a callable value is called with f."""
    def fn(f):
        out = []
        for c in cards:
            p = c.get('pose', 'idle')
            squash = 0.0
            p = list(p) if isinstance(p, Acted) else p  # Studio edition: hard steps between poses, no wind-up or overshoot
            p = st(f, p) if isinstance(p, list) else p
            p = base(f, c.get('seed', 0), **dict(POSES[p] if isinstance(p, str) else p))
            if 'talk' in c and c['talk'][0] <= f <= c['talk'][1]:
                p['mouth'] = talk(f)
            if 'walk' in c and c.get('walk_on', (f, f))[0] <= f <= c.get('walk_on', (f, f))[1]:
                p = walking(p, f, **c['walk'])
            if 'pattern' in c:
                p['pattern'] = (c['pattern'], f)
            x, y, z = (_k(f, c.get(a, d)) for a, d in (('x', 0), ('y', 0), ('z', 0)))
            out.append(card(c['id'], x, y, z, _k(f, c.get('M', M0)) * (1 - squash * .6), _k(f, c.get('sq', 1.0)) * (1 + squash), c.get('grade', RED_G), p))
        s = dict(cam=(_k(f, cam), _k(f, tgt), _k(f, lens)), roll=_k(f, roll), set=set, cards=out)
        for key, v in extra.items():
            s[key] = v(f) if callable(v) else v
        return s
    return fn


def tickets_at(streams, f, cap):
    """Deterministic flying slips: list of (pos, tumble). Stream: src, to (or vel/g), via, frames, spread, rate, a, b."""
    out = []
    for si, s in enumerate(streams or []):
        n0 = max(s['a'], f - s.get('frames', s.get('life', 40)))
        for e in range(int(n0 * s['rate']) - 1, int(min(f, s['b']) * s['rate']) + 1):
            born = e / s['rate']
            age = f - born
            life = s.get('frames', s.get('life', 40))
            if age < 0 or age > life or born < s['a']:
                continue
            r = random.Random(si * 100003 + e)
            sp = s.get('spread', .1)
            off = (r.uniform(-sp, sp), r.uniform(-sp, sp), r.uniform(-sp, sp))
            if 'to' in s:
                u = age / life
                if 'via' in s:
                    a_, b_, v_ = (s['src'], s['via'], u / .75) if u < .75 else (s['via'], s['to'], (u - .75) / .25)
                    p = tuple(a + (b - a) * v_ + o * (.25 + u) for a, b, o in zip(a_, b_, off))
                else:
                    p = tuple(a + (b - a) * u + o * (.25 + u) for a, b, o in zip(s['src'], s['to'], off))
                p = (p[0], p[1], p[2] + .35 * math.sin(u * math.pi))
            else:
                g = s.get('g', 0)
                p = (s['src'][0] + off[0] + s['vel'][0] * age * 2 + .012 * age * r.uniform(-1, 1), s['src'][1] + off[1] + s['vel'][1] * age, s['src'][2] + off[2] + s['vel'][2] * age + g * age * age)
            out.append((p, (r.uniform(0, 6) + age * r.uniform(.1, .4), r.uniform(0, 6) + age * r.uniform(.1, .3), r.uniform(0, 6))))
    return out[-cap:]


TAN_W, TAN_H = 18 * 1080 / 1920, 18
CAM_GAIN = .35  # Studio edition: every camera move runs at about a third of its size
LITE_LIGHT = dict(sun='#fff1d8', sun_energy=1.9, world='#dfe6f0', world_strength=.45, sun_rot=(55, 0, -30))


def _proj(cam, tgt, lens, p):
    """World point -> (across, up) in -1..1 of the rendered frame, or None behind the camera."""
    fw = [b - a for a, b in zip(cam, tgt)]
    n = math.sqrt(sum(x * x for x in fw)) or 1
    fw = [x / n for x in fw]
    r = (fw[1], -fw[0], 0.0)
    rn = math.hypot(r[0], r[1]) or 1
    r = (r[0] / rn, r[1] / rn, 0.0)
    u = (r[1] * fw[2] - r[2] * fw[1], r[2] * fw[0] - r[0] * fw[2], r[0] * fw[1] - r[1] * fw[0])
    v = [b - a for a, b in zip(cam, p)]
    z = sum(a * b for a, b in zip(v, fw))
    if z <= .05:
        return None
    # Blender default sensor (36 mm, fit AUTO) on a 9:16 frame: the 36 mm spans the height
    return sum(a * b for a, b in zip(v, r)) / z / (TAN_W / lens), sum(a * b for a, b in zip(v, u)) / z / (TAN_H / lens)


def _aim(cam, tgt, lens, p, u0, v0):
    """Turn the camera (no roll) so world point p lands at screen (u0, v0)."""
    d = math.dist(cam, tgt)
    fw = [(b - a) / d for a, b in zip(cam, tgt)]
    th, ph = math.atan2(fw[1], fw[0]), math.asin(max(-1, min(1, fw[2])))
    tw, th_ = TAN_W / lens, TAN_H / lens
    for _ in range(8):
        tg = (cam[0] + d * math.cos(ph) * math.cos(th), cam[1] + d * math.cos(ph) * math.sin(th), cam[2] + d * math.sin(ph))
        q = _proj(cam, tg, lens, p)
        if q is None:
            return tgt
        th -= math.atan(q[0] * tw) - math.atan(u0 * tw)
        ph += math.atan(q[1] * th_) - math.atan(v0 * th_)
    return (cam[0] + d * math.cos(ph) * math.cos(th), cam[1] + d * math.cos(ph) * math.sin(th), cam[2] + d * math.sin(ph))


def _lock_raw(S, s, L):
    """One frame of the framing lock. Returns (cam, tgt) or None. See FRAME_LOCK in API.md."""
    cards = s.get('cards') or []
    hero = s.get('hero')
    heads = {c['id']: (c['x'], c['y'], c['z'] + HEAD_Y * c['M']) for c in cards}
    if isinstance(hero, tuple):
        H = hero
    elif hero == 'mid' and heads:
        H = tuple(sum(h[i] for h in heads.values()) / len(heads) for i in range(3))
    elif hero in heads:
        H = heads[hero]
    elif cards and hero is None:
        H = heads[cards[0]['id']]
    else:
        return None
    cam, tgt, lens = s['cam']
    u0, v0 = L.get('spot', (0, .28))
    du, dv = L.get('dead', (.08, .06))
    keep = [(c['x'], c['y'], c['z'] + (HEAD_Y + 330) * c['M']) for c in cards] if s.get('keep_cards', True) else []
    keep += [(c['x'] + sx * 300 * c['M'], c['y'], c['z'] + HEAD_Y * c['M']) for c in cards for sx in (-1, 1)] if s.get('keep_cards', True) else []
    keep += list(s.get('keep', ()))
    m = L.get('margin', .92)

    def aimed(c_):
        q = _proj(c_, tgt, lens, H)
        if q is None:
            return _aim(c_, tgt, lens, H, u0, v0)
        # dead zone: only pull the hero back to the box round the spot
        ut = min(max(q[0], u0 - du), u0 + du)
        vt = min(max(q[1], v0 - dv), v0 + dv)
        return _aim(c_, tgt, lens, H, ut, vt) if (ut, vt) != tuple(q) else tgt

    def fits(c_):
        t_ = aimed(c_)
        for p in keep:
            q = _proj(c_, t_, lens, p)
            if q is None or abs(q[0]) > m or abs(q[1]) > m:
                return False
        return True

    def at(kk):
        c_ = tuple(h + (c - h) * kk for h, c in zip(H, cam))
        return (c_[0], c_[1], max(.25, c_[2]))
    lo, hi = 1.0, L.get('max_back', 3.0)
    if not fits(at(lo)):
        if not fits(at(hi)):
            lo = hi
        else:
            for _ in range(14):
                mid = (lo + hi) / 2
                lo, hi = (lo, mid) if fits(at(mid)) else (mid, hi)
            lo = hi
    return lo, H


def lock_key(reel):
    """Sources the lock cache depends on: story.py, this file, and their mtimes."""
    reel = Path(reel)
    return [str(int(p.stat().st_mtime)) for p in (reel / 'story.py', Path(__file__))]


def _lock_cache(S):
    if not hasattr(S, 'LOCK_CACHE'):
        S.LOCK_CACHE = {}
        p = Path(S.REEL) / 'toon' / '_lock_cache.json'
        if p.exists():
            d = json.loads(p.read_text())
            if d.get('key') == lock_key(S.REEL):
                S.LOCK_CACHE = d['cams']
    return S.LOCK_CACHE


def _lock(S, k, f, s):
    c = _lock_cache(S).get(f'{k}:{f}')
    if c:  # solved ahead of time by toon_lockcache.py on all cores
        s['cam'] = (tuple(c[0]), tuple(c[1]), s['cam'][2])
        return
    L = S.FRAME_LOCK
    a, b = S.SHOTS[k][1:]
    over_ = getattr(S, 'LOCK', {}).get(a, {})  # per-shot hero / keep / lock=False, keyed by shot start frame
    s_ = dict(s, **over_)
    if s_.get('lock') is False:
        return
    r0 = _lock_raw(S, s_, L)
    if r0 is None:
        return
    # pull-back factor smoothed over the shot's neighbouring frames so the fit never jitters
    ks = []
    for g in range(f - 6, f + 7):
        g = min(max(g, a - 12), b + 12)
        r = r0 if g == f else _lock_raw(S, dict(S.SHOTS[k][0](g), **over_), L)
        if r:
            ks.append(r[0])
    kk = max(sum(ks) / len(ks), r0[0] * .97)
    H = r0[1]
    cam, tgt, lens = s['cam']
    c_ = tuple(h + (c - h) * kk for h, c in zip(H, cam))
    c_ = (c_[0], c_[1], max(.25, c_[2]))
    u0, v0 = L.get('spot', (0, .28))
    du, dv = L.get('dead', (.08, .06))
    q = _proj(c_, tgt, lens, H)
    if q is None:
        t_ = _aim(c_, tgt, lens, H, u0, v0)
    else:
        ut, vt = min(max(q[0], u0 - du), u0 + du), min(max(q[1], v0 - dv), v0 + dv)
        t_ = _aim(c_, tgt, lens, H, ut, vt) if (ut, vt) != tuple(q) else tgt
    s['cam'] = (c_, t_, lens)


def _state(S, k, f):
    s = S.SHOTS[k][0](f)
    s.setdefault('vis', {})
    s.setdefault('cards', [])
    s.setdefault('roll', 0)
    pos, tgt, lens = s['cam']
    a0 = S.SHOTS[k][1]
    if f != a0:  # Studio edition: slow, small moves measured from the shot's first frame
        p0, t0, _ = S.SHOTS[k][0](a0)['cam']
        pos = tuple(x + (y - x) * CAM_GAIN for x, y in zip(p0, pos))
        tgt = tuple(x + (y - x) * CAM_GAIN for x, y in zip(t0, tgt))
        s['cam'] = (pos, tgt, lens)
    if isinstance(s['roll'], (int, float)):
        s['roll'] *= CAM_GAIN
    s.pop('dof', None)
    drop = getattr(S, 'CAM_DROP', {}).get(s['set'])
    if drop:
        z_hi, span, amt = drop
        d = amt * max(0.0, min(1.0, (z_hi - pos[2]) / span))
        s['cam'] = (pos, (tgt[0], tgt[1], tgt[2] - d), lens)
    if getattr(S, 'FRAME_LOCK', None):
        _lock(S, k, f, s)
    set_g = getattr(S, 'SET_G', {})
    lk = None
    s['light'] = LITE_LIGHT  # Studio edition: one plain daylight for every shot
    rim_on = getattr(S, 'RIM', None)
    for c in s['cards']:
        if c['grade'] == RED_G:
            c['grade'] = lk['grade'] if lk else set_g.get(s['set'], RED_G)
        if rim_on and c['pose'] is not None and 'rim' not in c['pose']:  # RIM=True: every card lit from the shot's look; shot key rim=dict(col,side,shade) overrides
            d = {'w': 18, 'strength': .9, **RIMS.get(s.get('look') or getattr(S, 'SET_LOOK', {}).get(s['set']), RIMS['noon']), **(rim_on if isinstance(rim_on, dict) else {}), **s.get('rim', {})}
            c['pose']['rim'] = d
    for fx in fx_list(s):
        if lk:
            fx.setdefault('grade', lk['grade'])
    return s


def join_of(S, b):
    """The join at shot boundary frame b: dict(kind, len, ...). Unlisted = 6 f dissolve for old reels (lint warns), or a whip if b is in WHIPS."""
    j = getattr(S, 'JOINS', {}).get(b)
    if j:
        return dict(dict(len=DEFAULT_LEN.get(j['kind'], 6)), **j)
    return dict(kind='whip' if b in getattr(S, 'WHIPS', ()) else 'dissolve', len=6)


DEFAULT_LEN = dict(cut=0, dissolve=6, whip=6, through=18, iris=12, puff=10, blast=14, flash=6, passby=12)


def load_story(reel):
    """Load <reel>\\story.py and attach state(k, f), frames_of(k), grade_at(f), tickets_at."""
    reel = Path(reel)
    sys.path[:0] = [str(Path(__file__).parent)]
    spec = importlib.util.spec_from_file_location('story', reel / 'story.py')
    S = importlib.util.module_from_spec(spec)
    sys.modules['story'] = S
    spec.loader.exec_module(S)
    S.REEL = reel
    # Studio edition: no framing lock, rim light, bloom, motion blur, colour arc, lenses or showy joins
    S.FRAME_LOCK, S.RIM, S.BLOOM, S.MOTION_BLUR, S.GRADE, S.FINISH, S.LENSES, S.WHIPS = None, None, 0, 0, None, None, (), ()
    S.JOINS = {b: dict(kind='cut' if j.get('kind') == 'cut' else 'dissolve') for b, j in getattr(S, 'JOINS', {}).items()}
    S.state = lambda k, f: _state(S, k, f)
    def frames_of(k):
        a, b = S.SHOTS[k][1:]
        La, Lb = join_of(S, a)['len'], join_of(S, b)['len']
        return max(0, a - max(3, La // 2 if k else 3)), min(S.LEN - 1, b + max(3, Lb - Lb // 2 if k + 1 < len(S.SHOTS) else 3))
    S.frames_of = frames_of
    S.join_of = lambda b: join_of(S, b)
    S.fx_list, S.fx_dir = fx_list, fx_dir
    S.grade_at = lambda f: tk(f, S.GRADE) if getattr(S, 'GRADE', None) else (1, 1, 1, 1)
    S.tickets_at = tickets_at
    return S


def check(S):
    """Hands against head and cap, for every card frame: any entry is a clip to fix."""
    bad = []
    for k in range(len(S.SHOTS)):
        for f in range(*S.frames_of(k)):
            for c in S.state(k, f)['cards']:
                p = c['pose']
                if not p:
                    continue
                for h in (p['hand_l'], p['hand_r']):
                    if 340 < h[0] < 870 and h[1] < 860:
                        bad.append((k, f, c['id'], tuple(round(x) for x in h)))
    return bad


def lint(S):
    """Style numbers from the study, per reel: warnings to look at, not gates."""
    out = []
    locked = lateral = n = 0
    holds = []
    for k, (_, a, b) in enumerate(S.SHOTS):
        holds.append((b - a) / 30)
        for f in range(a, b, 3):
            p0, t0 = S.state(k, f)['cam'][:2]
            p1, t1 = S.state(k, f + 3)['cam'][:2]
            d = [y - x for x, y in zip(p0, p1)]
            view = [y - x for x, y in zip(p0, t0)]
            L = math.dist(p0, t0) or 1
            along = sum(x * y for x, y in zip(d, view)) / L
            mv = math.dist(p0, p1) + math.dist(t0, t1)
            n += 1
            locked += mv < .003
            lateral += mv >= .003 and abs(along) < .5 * math.dist(p0, p1)
    out.append(f'camera locked {100 * locked / max(1, n):.0f} % of frames (aim 0: always drifting), mostly sideways {100 * lateral / max(1, n):.0f} % (study 1-13 %)')
    long_ = [round(h, 1) for h in holds if h > 3.5]
    out.append(f'shots {len(S.SHOTS)}, one per {S.LEN / 30 / max(1, len(S.SHOTS)):.1f} s (study about 2.3 s, longest 5-7 s), over 3.5 s: {long_}')
    kinds = [S.join_of(s0)['kind'] for _, s0, _ in S.SHOTS[1:]]
    same = sum(x == y and x != 'dissolve' for x, y in zip(kinds, kinds[1:]))
    out.append('joins ' + ', '.join(f'{x} {kinds.count(x)}' for x in sorted(set(kinds))) + f'; same showy join twice in a row: {same}')
    unset = [s0 for _, s0, _ in S.SHOTS[1:] if s0 not in getattr(S, 'JOINS', {}) and s0 not in getattr(S, 'WHIPS', ())]
    if unset:
        out.append(f'joins not chosen, will dissolve (choose one for each scene): {unset}')
    sets = {}
    for k, (_, a, b) in enumerate(S.SHOTS):
        sets.setdefault(S.state(k, a)['set'], []).append(k)
    one = sum(len(v) == 1 for v in sets.values())
    out.append(f'places {len(sets)} (aim about 8-12 in 60 s), seen only once: {one}; ' + ', '.join(f'{x}:{len(v)} shots' for x, v in sets.items()))
    heads, small, centred, moves = [], [], 0, 0
    for k, (_, a, b) in enumerate(S.SHOTS):
        s = S.state(k, (a + b) // 2)
        p, t, ln = s['cam']
        if s['cards']:
            c = max(s['cards'], key=lambda c_: head_pct(c_, p, ln))
            h = head_pct(c, p, ln)
            heads.append(h)
            if h < 12 and (b - a) > 45:
                small.append(k)
            view = [y - x for x, y in zip(p, t)]
            L = math.hypot(view[0], view[1]) or 1
            side = ((c['x'] - p[0]) * view[1] - (c['y'] - p[1]) * view[0]) / L
            centred += abs(side) < .06 * frame_w(max(.2, math.dist(p, (c['x'], c['y'], c['z']))), ln)
        s0, s1 = S.state(k, a), S.state(k, b - 1)
        d0, d1 = math.dist(s0['cam'][0], s0['cam'][1]), math.dist(s1['cam'][0], s1['cam'][1])
        moves += d1 > d0 * 1.03
    if heads:
        out.append(f'head size median {sorted(heads)[len(heads) // 2]:.0f} % of width (study mostly 12-35), small heads held over 1.5 s in shots {small}, centred {100 * centred // len(heads)} % of shots (aim 35 or less)')
    out.append(f'shots that pull back: {moves} of {len(S.SHOTS)} (aim about 1 in 4)')
    peaks = []
    for f in range(0, S.LEN, 3):
        k = next((i for i, (_, a, b) in enumerate(S.SHOTS) if a <= f < b), len(S.SHOTS) - 1)
        for fx in S.fx_list(S.state(k, f)):
            if any(len(it) == 7 and it[0] in ('column', 'shatter', 'boom') and it[3] * fx.get('M', M0) >= .9 and it[4] <= 8 for it in fx['items']) and (not peaks or f - peaks[-1] > 45):
                peaks.append(f)
    out.append(f'big effect peaks at {[round(100 * p / S.LEN) for p in peaks]} % of the reel (aim 3, about 20, 55, 90)')
    sets_py = Path(getattr(S, '__file__', '')).with_name('sets.py') if getattr(S, '__file__', None) else None
    if sets_py and sets_py.exists():
        words = sum(len(m.split()) for m in re.findall(r"(?:plate|sign_board|text3d|newspaper)\([^,]+,\s*['\"]([^'\"]+)['\"]", sets_py.read_text(encoding='utf-8')))
        out.append(f'world text about {words} words in sets.py (aim about 40 in 60 s)')
    return out


if __name__ == '__main__':
    S_ = load_story(sys.argv[1])
    b = check(S_)
    print('hand-head overlaps:', len(b), b[:12])
    for line in lint(S_):
        print('LINT', line)
