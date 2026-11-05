"""Draw every picture card. python toon_cards.py <reel> <out dir> [every Nth frame, or a list 12,40,90]. Card files: <out>/<id>/<shot>_<frame>.png
If <reel>\\hooks.py has cards_extra(out, C), it runs once (e.g. extra faces)."""
import importlib.util
import sys
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).parent
sys.path[:0] = [str(HERE)]
import toon_cast as C  # noqa: E402
from toon_fx import pattern_shadow, rim_light  # noqa: E402
from toon_story import load_story  # noqa: E402

REEL, OUT = Path(sys.argv[1]), Path(sys.argv[2])
S = load_story(REEL)
C.configure(S)


def job(a):
    k, f, idx, path = a
    s = S.state(k, f)
    c = s['cards'][idx]
    if Path(path).exists():
        return 0
    im = C.draw_card(c['src'], c['pose'])
    pat = c['pose'].get('pattern') if c['pose'] else None
    if pat:
        im = pattern_shadow(im, *pat)
    rim = c['pose'].get('rim') if c['pose'] else None
    if rim:
        im = rim_light(im, **rim)
    im.save(path, compress_level=1)
    return 1


def fxjob(a):
    k, f, i, path = a
    s = S.state(k, f)
    if Path(path).exists():
        return 0
    C.draw_fx(S.fx_list(s)[i]['items']).save(path, compress_level=1)
    return 1


if __name__ == '__main__':
    arg = sys.argv[3] if len(sys.argv) > 3 else '1'
    wanted = {int(x) for x in arg.split(',')} if ',' in arg else None
    step = None if wanted else int(arg)
    OUT.mkdir(parents=True, exist_ok=True)
    if (REEL / 'hooks.py').exists():
        spec = importlib.util.spec_from_file_location('toon_hooks', REEL / 'hooks.py')
        H = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(H)
        if hasattr(H, 'cards_extra'):
            H.cards_extra(OUT, C)
    jobs, fx = [], []
    for k in range(len(S.SHOTS)):
        a, b = S.frames_of(k)
        for f in range(a, b + 1):
            if (wanted and f not in wanted) or (step and f % step):
                continue
            s = S.state(k, f)
            for i, c in enumerate(s['cards']):
                d = OUT / c['id']
                d.mkdir(exist_ok=True)
                jobs.append((k, f, i, str(d / f'{k:02d}_{f:04d}.png')))
            for i, _ in enumerate(S.fx_list(s)):
                d = OUT / S.fx_dir(i)
                d.mkdir(exist_ok=True)
                fx.append((k, f, i, str(d / f'{k:02d}_{f:04d}.png')))
    with Pool(6) as pool:
        n = sum(pool.imap_unordered(job, jobs, 4)) + sum(pool.imap_unordered(fxjob, fx, 4))
    print('CARDS_OK', n, 'of', len(jobs) + len(fx))
