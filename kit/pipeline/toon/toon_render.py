r"""Render the reel from world.blend + <reel>\story.py (+ optional hooks.py).
blender -b <world.blend> -P toon_render.py -- <reel> <cards dir> <out dir> <res %> <samples> <every Nth | frame list with a comma>
Frames are written as s{shot:02d}_{frame:04d}.png; existing files are skipped."""
import importlib.util
import json
import math
import sys
import types
from pathlib import Path

import bpy
from mathutils import Euler, Quaternion, Vector

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from toon_story import load_story  # noqa: E402

args = sys.argv[sys.argv.index('--') + 1:]
REEL, CARDS, OUT, RES, SAMPLES, PICK = Path(args[0]), Path(args[1]), Path(args[2]), int(args[3]), int(args[4]), args[5]
S = load_story(REEL)
OUT.mkdir(parents=True, exist_ok=True)
sc = bpy.context.scene
sc.render.resolution_percentage = RES
sc.eevee.taa_render_samples = SAMPLES
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.compression = 15
ob = bpy.data.objects
cam = sc.camera
META = json.loads(sc['toon'])
HIDDEN, FACE_CAM, POOLS = META['hidden'], META['face_cam'], META['pools']
SHADOW = dict(w=.52, d=.3)
if getattr(S, 'SHADOW', None):  # story SHADOW=True or dict(w, d, strength): firmer contact shadow
    SHADOW = {'w': .62, 'd': .3, **(S.SHADOW if isinstance(S.SHADOW, dict) else {})}
    _v = SHADOW.get('strength', .9)
    next(n for n in bpy.data.materials['contact'].node_tree.nodes if n.type == 'VALTORGB').color_ramp.elements[0].color = (_v, _v, _v, 1)


def tree(o):
    return [o] + list(o.children_recursive)


def show(name, on):
    for o in tree(ob[name]):
        o.hide_render = not on


def pop(name, v):
    """v: 0 hidden, else visible at scale v."""
    show(name, v > 0.001)
    ob[name].scale = (v, v, v) if v > 0.001 else (1, 1, 1)


def face_cam(o):
    d = Vector(cam.location) - Vector(o.location)
    o.rotation_mode = 'XYZ'
    o.rotation_euler = Euler((0, 0, math.atan2(d.x, -d.y)))


def look(pos, tgt, lens, roll=0.0):
    cam.location = pos
    q = (Vector(tgt) - Vector(pos)).to_track_quat('-Z', 'Y')
    cam.rotation_quaternion = q @ Quaternion((0, 0, 1), math.radians(roll))
    cam.data.lens = lens


IMG = {}


def load(path):
    p = str(path)
    if p not in IMG:
        im = bpy.data.images.load(p)
        im.colorspace_settings.name = 'sRGB'
        im.alpha_mode = 'STRAIGHT'
        IMG[p] = im
    return IMG[p]


def set_tex(o, path, grade=(1, 1, 1)):
    nt = o.active_material.node_tree
    nt.nodes['TEX'].image = load(path)
    next(x for x in nt.nodes['GRADE'].inputs if x.identifier == 'B_Color').default_value = (*grade, 1)
    return nt


def free(keep):
    """Drop every loaded image not in keep: a per-frame texture that is not added to keep renders black."""
    for p in list(IMG):
        if p not in keep:
            bpy.data.images.remove(IMG.pop(p))


def srgb(h):
    return tuple(((int(h[i:i + 2], 16) / 255 + .055) / 1.055) ** 2.4 for i in (1, 3, 5))


LIGHT_USED = [False]
R = types.SimpleNamespace(**globals())
HOOKS = None
if (REEL / 'hooks.py').exists():
    spec = importlib.util.spec_from_file_location('toon_hooks', REEL / 'hooks.py')
    HOOKS = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(HOOKS)
    if hasattr(HOOKS, 'setup'):
        HOOKS.setup(R)
PO = [(p['key'], [ob[f"{p['prefix']}{i}"] for i in range(p['n'])], p['scale']) for p in POOLS]
MAXC = META.get('max_cards', 6)
cards = [ob[f'card{i}'] for i in range(MAXC)]
MOVERS = [(ob[m['obj']], Vector(ob[m['obj']].location), m) for m in META.get('movers', [])]
SUN, BG = bpy.data.lights['sun'], bpy.data.worlds['w'].node_tree.nodes['Background']
LIGHT0 = dict(sun=tuple(SUN.color), sun_energy=SUN.energy, sun_rot=tuple(ob['sun'].rotation_euler), world=tuple(BG.inputs['Color'].default_value)[:3], world_strength=BG.inputs['Strength'].default_value)
BLUR_AT = getattr(S, 'MOTION_BLUR', 0)


def light(d):
    """A shot's light (story `look=` or `light=`); shots without one use the world's own."""
    d = d or {}
    col = lambda v: srgb(v) if isinstance(v, str) else v
    SUN.color = col(d.get('sun', LIGHT0['sun']))
    SUN.energy = d.get('sun_energy', LIGHT0['sun_energy'])
    ob['sun'].rotation_euler = tuple(math.radians(v) for v in d['sun_rot']) if 'sun_rot' in d else LIGHT0['sun_rot']
    BG.inputs['Color'].default_value = (*col(d.get('world', LIGHT0['world'])), 1)
    BG.inputs['Strength'].default_value = d.get('world_strength', LIGHT0['world_strength'])


def camera_blur(k, f, s):
    """Real motion blur on fast camera moves only: keys the camera over this frame, so slow frames stay sharp and cost nothing."""
    cam.animation_data_clear()
    sc.render.use_motion_blur = False
    if not BLUR_AT:
        return
    n = S.state(k, f + 1)
    p0, p1 = Vector(s['cam'][0]), Vector(n['cam'][0])
    t0, t1 = Vector(s['cam'][1]), Vector(n['cam'][1])
    dist = max(.5, (t0 - p0).length)
    speed = ((p1 - p0).length + ((t1 - p1) - (t0 - p0)).length) / dist
    if speed < BLUR_AT:
        return
    sc.render.use_motion_blur = True
    sc.render.motion_blur_shutter = .5
    sc.frame_set(f)
    for fr, st_ in ((f - 1, S.state(k, f - 1)), (f, s), (f + 1, n)):
        look(*st_['cam'], st_.get('roll', 0))
        cam.keyframe_insert('location', frame=fr)
        cam.keyframe_insert('rotation_quaternion', frame=fr)
    sc.frame_set(f)


def apply(k, f):
    s = S.state(k, f)
    look(*s['cam'], s.get('roll', 0))
    camera_blur(k, f, s)
    if s.get('light') is not None or LIGHT_USED[0]:
        LIGHT_USED[0] = True
        light(s.get('light'))
    d_ = cam.data.dof
    d_.use_dof = bool(s.get('dof'))
    if s.get('dof'):
        d_.focus_distance, d_.aperture_fstop = s['dof']
    # movers: drifting clouds, traffic, bobbing crowds; they run on across cuts as one world
    for o, b0, m in MOVERS:
        p = b0 + Vector(m.get('vel', (0, 0, 0))) * f
        if m.get('wrap'):
            ax = int(max(range(3), key=lambda i: abs(m['vel'][i])))
            p[ax] = b0[ax] + ((p[ax] - b0[ax] + m['wrap'] / 2) % m['wrap']) - m['wrap'] / 2
        if m.get('bob'):
            amp, fq, ph = m['bob']
            p.z += amp * abs(math.sin(f * fq + ph))
        o.location = p
    for nm in HIDDEN:
        show(nm, False)
    for nm, v in s['vis'].items():
        pop(nm, float(v))
    # objs: {name: dict(show=bool, loc=(x,y,z), rot=(deg x,y,z), scale=v)}; texts: {name: body}
    for nm, d in s.get('objs', {}).items():
        if 'show' in d:
            show(nm, d['show'])
        if 'loc' in d:
            ob[nm].location = d['loc']
        if 'rot' in d:
            ob[nm].rotation_euler = tuple(math.radians(v) for v in d['rot'])
        if 'scale' in d:
            ob[nm].scale = (d['scale'],) * 3
    for nm, t in s.get('texts', {}).items():
        ob[nm].data.body = t
    for nm in FACE_CAM:
        face_cam(ob[nm])
    keep = set()
    # screens: {object: folder under <reel>\toon} -> that folder's {frame:04d}.png on the object's image texture
    for nm, dr in s.get('screens', {}).items():
        p_ = REEL / 'toon' / dr / f'{f:04d}.png'
        keep.add(str(p_))
        if p_.exists():
            next(n for n in ob[nm].active_material.node_tree.nodes if n.type == 'TEX_IMAGE').image = load(p_)
    if HOOKS and hasattr(HOOKS, 'apply'):
        HOOKS.apply(R, s, k, f, keep)
    # slip / bill streams
    for key, objs, scl in PO:
        tl = S.tickets_at(s.get(key), f, len(objs))
        for i, o in enumerate(objs):
            o.hide_render = i >= len(tl)
            if i < len(tl):
                o.location, o.rotation_euler = tl[i]
                if scl != 1.0:
                    o.scale = (scl, scl, scl)
    # picture cards
    n = 0
    for c in s['cards']:
        o = cards[n]
        n += 1
        o.hide_render = False
        path = CARDS / c['id'] / f'{k:02d}_{f:04d}.png'
        keep.add(str(path))
        set_tex(o, path, c['grade'])
        M = c['M']
        o.scale = (1900 * M * c['sq'], 1, 1900 * M)
        o.location = (c['x'], c['y'], c['z'] - 40 * M)
        face_cam(o)
        sh = ob[f'shadow{n - 1}']
        sh.hide_render = False
        sh.location = (c['x'], c['y'], c['z'] + .006)
        sh.scale = (SHADOW['w'], SHADOW['d'], 1)
    for i in range(n, MAXC):
        ob[f'shadow{i}'].hide_render = True
    for i, fx in enumerate(S.fx_list(s)):
        if not fx['items']:
            continue
        o = cards[n]
        n += 1
        o.hide_render = False
        path = CARDS / S.fx_dir(i) / f'{k:02d}_{f:04d}.png'
        keep.add(str(path))
        set_tex(o, path, fx.get('grade', (1, 1, 1)))
        M = fx.get('M', S.M0 if hasattr(S, 'M0') else .00115)
        o.scale = (1900 * M, 1, 1900 * M)
        o.location = (fx['x'], fx['y'], fx['z'])
        face_cam(o)
    for o in cards[n:]:
        o.hide_render = True
    free(keep)


wanted = {int(x) for x in PICK.split(',')} if ',' in PICK else None
step = None if wanted else int(PICK)
done = 0
for k in range(len(S.SHOTS)):
    a, b = S.frames_of(k)
    for f in range(a, b + 1):
        if (wanted and f not in wanted) or (step and f % step):
            continue
        path = OUT / f's{k:02d}_{f:04d}.png'
        if path.exists():
            continue
        apply(k, f)
        sc.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        done += 1
        if done % 25 == 0:
            print('RENDERED', done, flush=True)
print('RENDER_OK', done, flush=True)

