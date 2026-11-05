"""Template sets: one room built with room_set plus a desk and two plates. Names used by the story: sign (vis), count_tx (texts).
Most reels start instead from the ready sets, 60 m apart: from toon_sets import *; from toon_props import *; street_set('street', 0); trading_set('floor', 60) (API.md)."""
from toon_lib import *

SCENE = dict(sun_energy=3.0, world='#c8d4e4', world_strength=.6)
room_set('room', 0)
bx('desk', (2.4, .8, .08), (-1.0, 1.4, .8), painted('desk_m', '#6b3a1e', '#7c4526', 1.5))
for sx in (-1, 1):
    bx(f'desk_leg{sx}', (.08, .7, .8), (-1.0 + sx * 1.1, 1.4, .4), mat('desk_leg', '#6b3a1e', .6))
plate('sign', 'SALE', .6, (-1.0, 2.55, 3.2), '#b0302a', '#f6ead0', pad=(.2, .08), font_='slab')
plate('count', '$000M', .5, (1.9, 2.55, 2.9), '#f1e4c3', '#241a12', pad=(.2, .08), font_='type')
# logo plate on the wall
bx('brand_plate', (.72, .02, .22), (-2.2, 2.57, 1.9), mat('brand_bg', '#101522', .5))
image_plane('brand', BRAND, .62, (-2.2, 2.55, 1.9), lit=True)

HIDDEN = ['sign']      # objects hidden every frame unless the story's vis key pops them
FACE_CAM = []          # objects that always turn to face the lens
