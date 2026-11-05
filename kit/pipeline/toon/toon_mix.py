r"""Sound mix from a cue CSV, CPU only: coded bed (pad + room tone, ducked under the voice, rises in voice gaps), synthesized SFX, master -14 LUFS.
python toon_mix.py <reel> --voice <voice.wav> --cues <cues.csv> [--words voice_words.json] [--out <reel>\sound] [--sfx_db 0]
cues.csv columns: frame,dur_f,kind,level_db_vs_voice,arg   (level: -6 loudest ... -26 quietest; dur_f/arg optional, blank = kind default)
kinds: tap click pop whoosh thud ding paper bell alarm boing stab ticks roll slam buzz blip zip rise
Writes final_mix.wav (voice+bed+sfx) and final_nomusic.wav (voice+sfx, same gain), 48 kHz 24-bit stereo, and _work\levels.json.
Optional <reel>\mix_extra.py: extra(M) may call M.place(stem, x, t_seconds, rel_db_vs_voice) on M.sfx for bespoke cues."""
import csv
import json
import os
import re
import subprocess
import sys

import numpy as np
import soundfile as sf
from scipy.ndimage import minimum_filter1d, uniform_filter1d
from scipy.signal import butter, fftconvolve, sosfilt

sys.path[:0] = [os.path.dirname(os.path.abspath(__file__))]
from toon_story import load_story  # noqa: E402

SR, FPS = 48000, 30
TARGET_LUFS, TP_LIMIT = -14.0, -1.0
BED_UNDER_VOICE_DB = -21.7          # bed RMS re voice speech RMS
BED_GAP_RISE_DB = 5.0               # bed rises this much in voice gaps
GAP_MIN_S, GAP_LEAD_S, GAP_TAIL_S = .3, .25, .08
AMB_REL_DB = -9.0                   # room tone re pad
PAD_NOTES = [(73.42, 1.0), (146.83, 0.8), (174.61, 0.6), (220.0, 0.6), (293.66, 0.35), (349.23, 0.2)]
AMB_HUM_HZ = 110
SFX_STRONG_DB = -17.5               # peak 50 ms frame re voice for a level -6 cue
LEVEL_REF, LEVEL_SLOPE = 6, .5      # rel = SFX_STRONG_DB - LEVEL_SLOPE * (|level| - LEVEL_REF)
LIMIT_CEIL = .9                     # voice look-ahead limiter ceiling
VOICE_BOOSTS = []                   # [(t0 s, t1 s, +dB)]
END_FADE_S = .01
SEED = 11

a = sys.argv[1:]
opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
REEL = os.path.abspath(a[0])
S = load_story(REEL)
N = S.LEN * SR // FPS
OUTD = opt('--out', os.path.join(REEL, 'sound'))
WORK = os.path.join(OUTD, '_work')
os.makedirs(WORK, exist_ok=True)
rng = np.random.default_rng(SEED)
db = lambda x: 10 ** (x / 20)
F = lambda f: f / FPS


def lp(x, f, o=2): return sosfilt(butter(o, f, 'lowpass', fs=SR, output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'highpass', fs=SR, output='sos'), x)
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], 'bandpass', fs=SR, output='sos'), x)
def nz(n): return rng.normal(0, 1, n)


def lufs(path):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', path, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True)
    t = r.stderr[r.stderr.rfind('Summary:'):]
    g = lambda k: float(re.search(k + r':\s+(-?[\d.]+)', t).group(1))
    return g('I'), g('LRA'), float(re.search(r'Peak:\s+(-?[\d.]+) dBFS', t).group(1))


def frames_rms(x, win=0.05, hop=0.005):
    w, h = int(win * SR), int(hop * SR)
    c = np.concatenate([[0], np.cumsum(x.astype(np.float64) ** 2)])
    idx = np.arange(0, len(x) - w, h)
    return idx, np.sqrt((c[idx + w] - c[idx]) / w + 1e-12)


# ---------------- voice
vraw = sf.read(opt('--voice', os.path.join(REEL, 'voice.wav')))[0]
if vraw.ndim > 1:
    vraw = vraw.mean(1)
VOICE = np.pad(vraw, (0, max(0, N - len(vraw))))[:N]
for t0, t1, g_ in VOICE_BOOSTS:
    env = np.zeros(N)
    env[int(t0 * SR):int(t1 * SR)] = 1
    VOICE = VOICE * (1 + (db(g_) - 1) * np.clip(lp(env, 40, 1), 0, 1))
gr = np.minimum(1.0, LIMIT_CEIL / (np.abs(VOICE) + 1e-9))
VOICE = VOICE * uniform_filter1d(minimum_filter1d(gr, 961, mode='nearest'), 481, mode='nearest')
vi, vr = frames_rms(VOICE)
vd = 20 * np.log10(vr)
SPEECH = vd > np.percentile(vd, 95) - 25
V_DB = 10 * np.log10(np.mean(vr[SPEECH] ** 2))


def peak_frame_db(x):
    _, r = frames_rms(np.pad(x, (0, 2400)))
    return 20 * np.log10(r.max() + 1e-12)


def place(stem, x, t, rel_db):
    x = x / (10 ** (peak_frame_db(x) / 20) + 1e-12) * db(V_DB + rel_db)
    i = int(round(t * SR))
    j = min(len(stem), i + len(x))
    if j > i:
        stem[i:j] += x[:j - i]


def ex(n, a=0.002, d=0.1, k=5.0):
    x = np.arange(n) / SR
    e = np.exp(-k * x / max(d, 1e-3))
    na = max(1, int(a * SR))
    e[:na] *= np.linspace(0, 1, na)
    return e


def fade(x, a=0.003, b=0.003):
    x = x.copy()
    na, nb = int(a * SR), int(b * SR)
    if na:
        x[:na] *= np.linspace(0, 1, na)
    if nb:
        x[-nb:] *= np.linspace(1, 0, nb)
    return x


# ---------------- bed
def pad_(n):
    t = np.arange(n) / SR
    y = np.zeros(n)
    for f, a_ in PAD_NOTES:
        for det, ph in ((-0.12, 0.3), (0.12, 1.9)):
            ff = f * (1 + det / 100)
            for h in range(1, 7):
                y += a_ / h ** 1.4 * np.sin(2 * np.pi * ff * h * t + ph * h)
    y = lp(y, 1100)
    y *= 1 + 0.03 * np.sin(2 * np.pi * 0.11 * t)
    return y / np.abs(y).max()


def amb(n):
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * AMB_HUM_HZ * t) + 0.25 * np.sin(2 * np.pi * 2 * AMB_HUM_HZ * t) + 0.5 * lp(nz(n), 700, 2)


words = json.load(open(opt('--words', os.path.join(REEL, 'voice_words.json')), encoding='utf-8-sig'))
iv = sorted((w['start'], w['end']) for w in words)
merged = []
for s0, e in iv:
    if merged and s0 <= merged[-1][1]:
        merged[-1][1] = max(merged[-1][1], e)
    else:
        merged.append([s0, e])
END_T = N / SR
GAPS = [(merged[k][1], merged[k + 1][0]) for k in range(len(merged) - 1) if merged[k + 1][0] - merged[k][1] >= GAP_MIN_S]
if END_T - merged[-1][1] >= GAP_MIN_S:
    GAPS.append((merged[-1][1], END_T))
pts_t, pts_g = [0.0], [0.0]
for e, s0 in GAPS:
    peak = BED_GAP_RISE_DB * min(1.0, max(0.0, (s0 - GAP_TAIL_S - e) / GAP_LEAD_S))
    for t_, g_ in zip([e, min(e + GAP_LEAD_S, s0 - GAP_TAIL_S), s0 - GAP_TAIL_S, s0], [0, peak, peak, 0]):
        if t_ > pts_t[-1]:
            pts_t.append(t_)
            pts_g.append(g_)
pts_t.append(END_T + 1)
pts_g.append(0)
GDB = np.interp(np.arange(N) / SR, pts_t, pts_g)


def make_bed():
    p, a_ = pad_(N), amb(N)
    a_ = a_ / np.sqrt(np.mean(a_ ** 2)) * np.sqrt(np.mean(p ** 2)) * db(AMB_REL_DB)
    raw = fade(p + a_, 0.004, 0.0) * db(GDB)
    _, r = frames_rms(raw)
    cur = 10 * np.log10(np.mean(r[SPEECH[:len(r)]] ** 2))
    return raw * db(V_DB + BED_UNDER_VOICE_DB - cur)


# ---------------- SFX building blocks
def tapclick(f=1500, ms=14):
    n = int(ms / 1000 * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * f * t) * ex(n, 0.0005, ms / 1000, 5) + 0.3 * hp(nz(n), 3000) * ex(n, 0.0002, 0.004, 5)


def tone(dur, f0, f1=None, dec=None, k=4.0, a_=0.003, harm=0.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f1 = f0 if f1 is None else f1
    ph = 2 * np.pi * np.cumsum(f0 + (f1 - f0) * (t / dur)) / SR
    return (np.sin(ph) + harm * np.sin(2 * ph)) * ex(n, a_, dec or dur, k)


def thud(f=70, dur=0.2, sweep=25, k=4.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * np.cumsum(f + sweep * np.exp(-t * 30)) / SR) * ex(n, 0.002, dur, k)


def click(lo=1200, hi=3000, ms=10):
    n = int(ms / 1000 * SR)
    return bp(nz(n), lo, hi) * ex(n, 0.0003, ms / 1000, 5)


def whoosh(dur, lo=900, hi=3000, p=1.5):
    n = int(dur * SR)
    return bp(nz(n), lo, hi) * np.sin(np.pi * np.arange(n) / n) ** p


def paper(dur, top=3000, dens=40, swell=False):
    n = int(dur * SR)
    base = bp(nz(n), 900, top)
    am = np.abs(lp(nz(n), 14, 1))
    am = am / (am.max() + 1e-9)
    y = base * am ** 1.3 * 0.5
    for _ in range(int(dens * dur)):
        i = rng.integers(0, max(1, n - 800))
        L = int(rng.uniform(0.008, 0.03) * SR)
        y[i:i + L] += (bp(nz(L), 1500, top) * ex(L, 0.001, L / SR, 4) * rng.uniform(0.4, 1.2))[:max(0, n - i)]
    if swell:
        y *= np.sin(np.pi * np.arange(n) / n) ** 0.8
    return fade(y, 0.01, 0.02)


def pop(f0=800, f1=320, dur=0.12, shim=2400):
    n = int(dur * SR)
    t = np.arange(n) / SR
    return fade(tone(dur, f0, f1, dur, 5) + 0.25 * np.sin(2 * np.pi * shim * t) * ex(n, 0.002, 0.12, 4), 0.001, 0.01)


def ding(f=1568, dur=0.45):
    n = int(dur * SR)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 1.5 * t)) * ex(n, 0.002, dur, 6)


def metal(f=300, dur=0.4, ratios=(1, 2.76, 5.4, 8.9), k=6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * f * r * t) / (i + 1) * ex(n, 0.001, dur / (1 + 0.4 * i), k) for i, r in enumerate(ratios))


def stab(freqs, dur=0.18):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = sum(np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * 2 * f * t) + 0.3 * np.sin(2 * np.pi * 3 * f * t) for f in freqs)
    return lp(y, 2500) * ex(n, 0.004, dur, 5)


def boing(dur=0.28, f0=300, f1=900):
    n = int(dur * SR)
    t = np.arange(n) / SR
    fr = f0 + (f1 - f0) * (t / dur) + 40 * np.sin(2 * np.pi * 14 * t)
    return lp(np.sin(2 * np.pi * np.cumsum(fr) / SR) + 0.3 * np.sin(4 * np.pi * np.cumsum(fr) / SR), 1800) * ex(n, 0.004, dur, 4)


def blip_thud(fa, fb, th=70):
    nb = int(0.075 * SR)
    t = np.arange(nb) / SR
    b1 = np.sin(2 * np.pi * fa * t) * ex(nb, 0.003, 0.07, 3.5)
    b2 = np.sin(2 * np.pi * fb * t) * ex(nb, 0.003, 0.07, 3.5)
    nt = int(0.2 * SR)
    tt = np.arange(nt) / SR
    cue = np.zeros(nt + int(0.1 * SR))
    cue[:nt] += 1.3 * np.sin(2 * np.pi * (th + 25 * np.exp(-tt * 30)) * tt) * ex(nt, 0.002, 0.18, 4)
    cue[:nb] += b1
    cue[int(0.085 * SR):int(0.085 * SR) + nb] += b2
    return cue


# ---------------- cue kinds: (arg, dur_s) -> sound
def k_roll(arg, d):
    K = 22
    times = d * (1 - (1 - np.linspace(0, 1, K)) ** 1.7)
    y = np.zeros(int((d + 0.1) * SR))
    for t_ in times:
        c = lp(fade(tapclick(2200, 8)), 2500)
        i = int(t_ * SR)
        y[i:i + len(c)] += c[:len(y) - i]
    rum = lp(nz(len(y)), 160) + 0.5 * np.sin(2 * np.pi * 55 * np.arange(len(y)) / SR)
    rum *= np.linspace(0.2, 1, len(y))
    return y / np.abs(y).max() + 0.25 * rum / np.abs(rum).max()


def k_ticks(arg, d):
    y = np.zeros(int(d * SR) + 2000)
    for k in range(max(1, int(d * FPS / 4))):
        c = fade(tapclick(1800 if k % 2 else 1500, 12))
        i = int(k * 4 / FPS * SR)
        y[i:i + len(c)] += c
    return y


def k_alarm(arg, d):
    n = int(d * SR)
    t = np.arange(n) / SR
    fq = np.where(np.sin(2 * np.pi * 8 * t) > 0, 780.0, 1050.0)
    al = np.sin(2 * np.pi * np.cumsum(fq * (1 + 0.15 * t)) / SR)
    return fade(lp(al + 0.2 * np.sign(al), 2200) + 0.3 * lp(nz(n), 400) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 21 * t))), 0.01, 0.03)


def k_bell(arg, d):
    f0 = arg or 220
    n = int(max(d, 1.0) * SR)
    t = np.arange(n) / SR
    y = sum(a_ * np.sin(2 * np.pi * f0 * r_ * t) * (0.75 * np.exp(-t / (0.07 * (1 + 0.2 * i))) + 0.25 * np.exp(-t / (0.5 / (1 + 0.4 * i))))
            for i, (r_, a_) in enumerate([(1, 1.0), (2.0, 0.6), (2.4, 0.45), (3.0, 0.3), (4.1, 0.2), (5.4, 0.12)]))
    s0 = hp(nz(int(0.03 * SR)), 1800) * ex(int(0.03 * SR), 0.0005, 0.03, 5)
    y[:len(s0)] += 0.8 * s0 / np.abs(s0).max()
    y[:int(0.01 * SR)] *= np.linspace(0, 1, int(0.01 * SR))
    return y


def k_slam(arg, d):
    n = int(0.7 * SR)
    t = np.arange(n) / SR
    th = np.sin(2 * np.pi * np.cumsum(60 + 40 * np.exp(-t * 14)) / SR) * ex(n, 0.002, 0.5, 4)
    mt = lp(metal(arg or 140, 0.5, (1, 2.76, 4.07, 5.4), 5), 2500)
    dry = 1.2 * th
    dry[:len(mt)] += 0.5 * mt[:n]
    ir = lp(nz(int(0.9 * SR)), 3000) * np.exp(-3.4 * np.arange(int(0.9 * SR)) / SR)
    wet = fftconvolve(dry, ir)[:int(1.3 * SR)] * 0.0015
    cue = np.zeros(int(1.3 * SR))
    cue[:n] += dry
    return cue + wet * (np.abs(dry).max() / (np.abs(wet).max() + 1e-12)) * 0.35


def k_buzz(arg, d):
    n = int(max(d, 0.05) * SR)
    t = np.arange(n) / SR
    return lp(np.sign(np.sin(2 * np.pi * (arg or 110) * t)) + 0.3 * nz(n), 380) * ex(n, 0.002, d, 3)


def k_zip(arg, d):
    n = int(d * SR)
    t = np.arange(n) / SR
    zp = np.sin(2 * np.pi * np.cumsum(600 + 1800 * (t / t[-1]) ** 1.4) / SR) * 0.5
    cr = np.zeros(n)
    for i in rng.integers(0, n - 100, int(90 * d)):
        cr[i:i + 30] += rng.uniform(0.3, 1) * nz(30) * np.hanning(30)
    return lp(zp + cr / (np.abs(cr).max() + 1e-9) * 0.6, 3000) * np.sin(np.pi * t / t[-1]) ** 0.5


def k_rise(arg, d):
    """ascending pips, one per 4 f from arg Hz (default C5)"""
    K = max(2, int(d * FPS / 4))
    y = np.zeros(int(d * SR) + 4000)
    for k in range(K):
        x = tone(0.07, (arg or 523.25) * 2 ** (k / (K - 1)), None, 0.07, 4)
        i = int(k * 4 / FPS * SR)
        y[i:i + len(x)] += fade(x)
    return y


KINDS = {
    'tap': lambda arg, d: fade(tapclick(arg or 1500)),
    'click': lambda arg, d: click(1200, 3000, 10),
    'pop': lambda arg, d: pop(arg or 900, 380),
    'whoosh': lambda arg, d: whoosh(d, 900, 3000),
    'thud': lambda arg, d: thud(arg or 70, 0.25, 20),
    'ding': lambda arg, d: ding(arg or 1568, 0.45),
    'paper': lambda arg, d: lp(paper(d, 3000, 20), 3000),
    'bell': k_bell, 'alarm': k_alarm, 'boing': lambda arg, d: boing(0.3, 330, 800),
    'stab': lambda arg, d: stab([arg or 415.3, (arg or 415.3) * 1.06])[:int(0.2 * SR)],
    'ticks': k_ticks, 'roll': k_roll, 'slam': k_slam, 'buzz': k_buzz,
    'blip': lambda arg, d: fade(blip_thud(arg or 440, (arg or 440) * .75)[:int(0.30 * SR)]),
    'zip': k_zip, 'rise': k_rise,
}
DUR_DEFAULT_F = dict(whoosh=8, paper=40, alarm=28, roll=38, ticks=24, zip=35, buzz=4, rise=24, bell=42)


def rel_of(level):
    return SFX_STRONG_DB - LEVEL_SLOPE * (abs(level) - LEVEL_REF)


def build_cues(s):
    rows = list(csv.DictReader(open(opt('--cues'), encoding='utf-8-sig')))
    for r in rows:
        kind = r['kind'].strip()
        fr = int(r['frame'])
        df = int(float(r['dur_f'])) if r.get('dur_f', '').strip() else DUR_DEFAULT_F.get(kind, 8)
        arg = float(r['arg']) if r.get('arg', '').strip() else None
        lvl = float(r['level_db_vs_voice'] or -20)
        place(s, KINDS[kind](arg, df / FPS), F(fr), rel_of(lvl))
    return len(rows)


class M:                                   # namespace handed to mix_extra.extra
    pass


def main():
    bed = make_bed()
    s = np.zeros(N)
    nrows = build_cues(s)
    X = None
    if os.path.exists(os.path.join(REEL, 'mix_extra.py')):
        import importlib.util
        spec = importlib.util.spec_from_file_location('mix_extra', os.path.join(REEL, 'mix_extra.py'))
        X = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(X)
        M.place, M.sfx, M.voice, M.V_DB, M.F, M.SR, M.N, M.tools = place, s, VOICE, V_DB, F, SR, N, globals()
        if hasattr(X, 'bed_fx'):            # optional: bed = bed_fx(M, bed) (bed-only edits, e.g. a key-word silence drop)
            bed = X.bed_fx(M, bed)
        if hasattr(X, 'extra'):
            X.extra(M)
    s *= db(float(opt('--sfx_db', 0)))     # whole SFX layer re voice, e.g. 1.58 = +20 %
    sfx_pk = peak_frame_db(s)
    pre = VOICE + bed + s
    pre_p = os.path.join(WORK, 'mix_pre.wav')
    sf.write(pre_p, np.stack([pre, pre], 1), SR, subtype='PCM_24')
    I, LRA, TP = lufs(pre_p)
    g = db(TARGET_LUFS - I)

    def out(x, name):
        y = x * g
        y[-int(END_FADE_S * SR):] *= np.linspace(1, 0, int(END_FADE_S * SR))
        p = os.path.join(OUTD, name)
        sf.write(p, np.stack([y, y], 1), SR, subtype='PCM_24')
        return p, y
    pm, ym = out(pre, 'final_mix.wav')
    I2, L2, T2 = lufs(pm)
    note = ''
    if T2 > TP_LIMIT:
        g *= db(TP_LIMIT - T2 - 0.05)
        pm, ym = out(pre, 'final_mix.wav')
        I2, L2, T2 = lufs(pm)
        note = 'gain trimmed for TP'
    pn, _ = out(VOICE + s, 'final_nomusic.wav')
    In, Ln, Tn = lufs(pn)
    _, rb = frames_rms(bed)
    b_sp = 10 * np.log10(np.mean(rb[SPEECH[:len(rb)]] ** 2))
    res = dict(LUFS=I2, LRA=L2, TP=T2, nomusic_LUFS=In, nomusic_LRA=Ln, nomusic_TP=Tn, gain_db=20 * np.log10(g), note=note, cues=nrows, gaps=len(GAPS),
               bed_under_voice_speech=b_sp - V_DB, sfx_loudest_minus_voice=sfx_pk - V_DB, out_len_s=len(ym) / SR)
    json.dump(res, open(os.path.join(WORK, 'levels.json'), 'w'), indent=1)
    print(json.dumps(res, indent=1))


main()

