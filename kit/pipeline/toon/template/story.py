"""Template reel: 2 shots, 5 s. Copy this folder to Reels/reels/<date>-<slug>/ and edit. Shot = function of the frame -> state dict (see API.md)."""
from toon_story import *

LEN = 150
JOINS = {78: dict(kind='dissolve')}    # cut or dissolve at each shot boundary
SHADOW = True                          # contact shadow under the feet

# shot 1: the engineer walks in, the banker waits, the sign pops at f20
S1 = shot('room', **dolly((-1.4, -3.0, .9), (.1, 1, 1.45), 0, 78), lens=28,
          cards=[dict(id='engineer', x=[(0, -1.7), (78, -.7)], y=.4, pose='idle', seed=.3, walk=dict(v=8, T=12)),
                 dict(id='banker', x=.55, y=.5, pose=acting(0, 78, seed=2), seed=1.1, talk=(10, 70))],
          vis=lambda f: dict(sign=over((f - 20) / 9)), texts=dict(count_tx='$0M'))

# shot 2: closer on the banker as the number counts up
S2 = shot('room', **dolly(*hero_cam(.55, .5), 78, 150), lens=28,
          cards=[dict(id='banker', x=.55, y=.5, pose=acted([(78, 'explain'), (100, 'think')]), seed=1.1),
                 dict(id='worker', x=1.35, y=.9, pose='cheer', seed=2.0)],
          texts=lambda f: dict(count_tx=f'${int(ease((f - 84) / 50) * 460):,}M'))

SHOTS = [(S1, 0, 78), (S2, 78, 150)]       # (state function, first frame, last frame)
