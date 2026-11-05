"""Finishing grade from the 12-reel frame study: tinted shadows, warm highlights, tamed whites, colour lifted per shot so dull shots gain most and hot ones stay.
In a reel: FINISH='day' (default for all shots) and shot key finish='night' (names in FINISHES; a dict overrides keys). FINISH=None turns it off; a reel without FINISH keeps its old look.
Test on any video: python toon_grade.py <in.mp4> <out.mp4> [finish name]"""
import numpy as np

LUM = np.array((.3, .59, .11), np.float32)
# sh, mid, hi = colour added to shadows, mids, highlights in 0-255 RGB. chroma = target colour strength of the shot's frame (0-255 RGB spread). white = soft ceiling.
FINISHES = dict(
    day=dict(sh=(10, -7, 22), mid=(2, -1, 0), hi=(3, 2, -4), chroma=62, white=246, black=0),
    warm=dict(sh=(16, -6, 10), mid=(5, 0, -4), hi=(6, 3, -9), chroma=64, white=246, black=0),
    night=dict(sh=(10, -8, 34), mid=(1, -3, 9), hi=(2, 2, -2), chroma=62, white=240, black=4),
    tension=dict(sh=(18, -10, 16), mid=(5, -4, 0), hi=(6, 0, -5), chroma=60, white=242, black=6),
    neutral=dict(sh=(4, -2, 6), mid=(0, 0, 0), hi=(0, 0, 0), chroma=50, white=248, black=0),
    # railroad-reference study (2026-11-03): mids about twice as bright, no crushed blacks, neutral whites
    bright=dict(sh=(8, -4, 14), mid=(2, 0, 0), hi=(0, 0, 0), chroma=60, white=248, black=0, gamma=.78, lift=10),
)
# gamma < 1 brightens mids without moving black or white; lift raises the black floor (0-255)


def resolve(v):
    """Name or dict -> full settings; a dict may name a base with base='night'."""
    if v is None or v is False:
        return None
    if isinstance(v, str):
        return FINISHES[v]
    return {**FINISHES[v.get('base', 'day')], **v}


def spread(a):
    """Colour strength of a frame: mean RGB distance from its own grey."""
    return float(np.abs(a - (a @ LUM)[..., None]).mean() * 3)


def gain_for(a, g):
    """Saturation gain for one shot, measured once on a sample frame so a shot never flickers."""
    return float(np.clip(g['chroma'] / max(6.0, spread(a)), 1.0, 1.5))  # above about 1.5 skin turns orange


def apply(a, g, gain=None):
    """a: float32 HxWx3, 0-255."""
    gain = gain_for(a, g) if gain is None else gain
    lum = a @ LUM
    out = lum[..., None] + (a - lum[..., None]) * gain
    u = np.clip(lum / 255, 0, 1)
    w_sh = np.clip(1 - u / .34, 0, 1)[..., None] ** 1.2
    w_hi = np.clip((u - .55) / .4, 0, 1)[..., None]
    w_mid = np.clip(1 - w_sh - w_hi, 0, 1)
    out = out + w_sh * np.array(g['sh'], np.float32) + w_mid * np.array(g['mid'], np.float32) + w_hi * np.array(g['hi'], np.float32)
    if g.get('black'):
        out = (out - g['black']) * 255 / (255 - g['black'])
    if g.get('gamma', 1) != 1:
        out = 255 * (np.clip(out, 0, 255) / 255) ** g['gamma']
    if g.get('lift'):
        out = g['lift'] + out * (255 - g['lift']) / 255
    knee, top = g['white'] - 28.0, float(g['white'])
    hot = out > knee
    out = np.where(hot, knee + (top - knee) * (1 - np.exp(-(out - knee) / (top - knee))), out)  # soft ceiling, no clipping
    return np.clip(out, 0, 255)


if __name__ == '__main__':
    import subprocess
    import sys

    import cv2
    src, dst = sys.argv[1:3]
    g = resolve(sys.argv[3] if len(sys.argv) > 3 else 'day')
    cap = cv2.VideoCapture(src)
    w, h = int(cap.get(3)), int(cap.get(4))
    ff = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{w}x{h}', '-r', '30', '-i', '-', '-c:v', 'libx264', '-crf', '20', '-pix_fmt', 'yuv420p', dst], stdin=subprocess.PIPE)
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        out = apply(fr[..., ::-1].astype(np.float32), g)
        ff.stdin.write(out[..., ::-1].astype(np.uint8).tobytes())
    ff.stdin.close()
    ff.wait()
    print('GRADE_OK', dst)

