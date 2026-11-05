r"""Build the world: runs <reel>\sets.py with toon_lib, adds card planes and sprite pools, saves the blend.
blender -b --factory-startup -P toon_world.py -- <reel> <out.blend>"""
import os
import runpy
import sys
from pathlib import Path

args = sys.argv[sys.argv.index('--') + 1:]
REEL, OUT = Path(args[0]).resolve(), Path(args[1])
os.environ['TOON_REEL'] = str(REEL)
sys.path.insert(0, str(Path(__file__).parent))
import toon_lib as L  # noqa: E402

L.init_scene()
ns = runpy.run_path(str(REEL / 'sets.py'))
OUT.parent.mkdir(parents=True, exist_ok=True)
L.finish(ns, OUT)

