"""Crowds, vehicles and insert props for toon reels (Blender side). In a reel's sets.py:
    from toon_lib import *
    from toon_props import *
Movers: this module's MOVERS list (also movers_list()); merge it into the reel's own MOVERS (see API notes). Plain-Python helpers for story.py live in
toon_props_story.py (calendar_flip, newspaper_png). All world locations include the set's ox. Vehicles face +X."""
import glob
import math
import random
from pathlib import Path

import bpy
from toon_lib import *  # noqa: F401,F403
from toon_lib import KIT, ANTON, asset, bx, cyl, group, image_plane, mat, plate, sc, sock, out_color, srgb, text3d

MOVERS = []


def movers_list():
    """Same list as MOVERS (use when a sets.py star-imports both toon_sets and toon_props and one MOVERS name would shadow the other)."""
    return MOVERS


# ---------------------------------------------------------------- shared flat sprites
_MESH, _MAT = {}, {}


def _sprite_mat(key, path, grade=None, alpha_only=None):
    k = (key, tuple(grade) if grade else None)
    if k in _MAT:
        return _MAT[k]
    m = bpy.data.materials.new(f'spr_{key}')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    tx = nt.nodes.new('ShaderNodeTexImage')
    tx.image = bpy.data.images.load(str(path), check_existing=True)
    tx.interpolation = 'Linear'
    gr = nt.nodes.new('ShaderNodeMix')
    gr.data_type, gr.blend_type = 'RGBA', 'MULTIPLY'
    gr.inputs[0].default_value = 1
    sock(gr, 'B_Color').default_value = (*(grade or (1, 1, 1))[:3], 1)
    nt.links.new(tx.outputs['Color'], sock(gr, 'A_Color'))
    em = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(out_color(gr), em.inputs['Color'])
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(tx.outputs['Alpha'], mx.inputs[0])
    nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], nt.nodes.new('ShaderNodeOutputMaterial').inputs['Surface'])
    m.surface_render_method = 'BLENDED'
    _MAT[k] = m
    return m


def _sprite_mesh(path, grade=None):
    """One shared mesh (unit height, feet at origin, facing -Y) + material per image/grade."""
    k = (str(path), tuple(grade) if grade else None)
    if k in _MESH:
        return _MESH[k]
    img = bpy.data.images.load(str(path), check_existing=True)
    asp = img.size[0] / max(1, img.size[1])
    me = bpy.data.meshes.new('spr_' + str(path)[-12:])
    me.from_pydata([(-asp / 2, 0, 0), (asp / 2, 0, 0), (asp / 2, 0, 1), (-asp / 2, 0, 1)], [], [(0, 1, 2, 3)])
    me.uv_layers.new().data.foreach_set('uv', [0, 0, 1, 0, 1, 1, 0, 1])
    me.update()
    me.materials.append(_sprite_mat(str(path), path, grade))
    _MESH[k] = me
    return me


_SHADOW = {}


def _shadow_mesh():
    if 'm' in _SHADOW:
        return _SHADOW['m']
    m = bpy.data.materials.new('crowd_shadow')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    tc = nt.nodes.new('ShaderNodeTexCoord')
    vm = nt.nodes.new('ShaderNodeVectorMath')
    vm.operation = 'LENGTH'
    nt.links.new(tc.outputs['Object'], vm.inputs[0])
    ra = nt.nodes.new('ShaderNodeValToRGB')
    ra.color_ramp.elements[0].position, ra.color_ramp.elements[0].color = .1, (.5, .5, .5, 1)
    ra.color_ramp.elements[1].position, ra.color_ramp.elements[1].color = 1, (0, 0, 0, 1)
    nt.links.new(vm.outputs['Value'], ra.inputs['Fac'])
    mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(ra.outputs['Color'], mx.inputs[0])
    nt.links.new(nt.nodes.new('ShaderNodeBsdfTransparent').outputs[0], mx.inputs[1])
    e = nt.nodes.new('ShaderNodeEmission')
    e.inputs['Color'].default_value = (.04, .03, .06, 1)
    nt.links.new(e.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], nt.nodes.new('ShaderNodeOutputMaterial').inputs['Surface'])
    m.surface_render_method = 'BLENDED'
    me = bpy.data.meshes.new('crowd_shadow')
    r = 1.0
    me.from_pydata([(-r, -r * .55, .004), (r, -r * .55, .004), (r, r * .55, .004), (-r, r * .55, .004)], [], [(0, 1, 2, 3)])
    me.update()
    me.materials.append(m)
    # Object coordinates of the plane run -1..1 so the ramp fades to the edge
    _SHADOW['m'] = me
    return me


def _crowd_files(heads):
    fs = sorted(glob.glob(str(KIT / 'assets' / 'crowd' / ('h*.png' if heads else 'c*.png'))))
    if not fs:
        raise FileNotFoundError('crowd art missing (pipeline\\toon\\assets\\crowd)')
    return fs


def _people(name, pts, height, bob, grade, heads_only, seed, sink=0.0, shadow=True, lift=0.0):
    """pts: world (x, y, z) feet positions. Returns object names. One shared mesh per image, one top-level object per person (movers need that)."""
    rnd = random.Random(seed)
    files = _crowd_files(heads_only)
    hh = height * (.42 if heads_only else 1.0)
    names = []
    for i, (x, y, z) in enumerate(pts):
        fpath = rnd.choice(files)
        s = hh * rnd.uniform(.92, 1.08)
        o = bpy.data.objects.new(f'{name}_{i}', _sprite_mesh(fpath, grade))
        sc.collection.objects.link(o)
        o.location = (x, y, z - sink * s + lift)
        o.scale = (s * rnd.choice((-1, 1)), s, s)
        o.visible_shadow = False
        MOVERS.append(dict(obj=o.name, vel=(0, 0, 0), bob=(bob * rnd.uniform(.5, 1.3), rnd.uniform(.12, .3), rnd.uniform(0, 6.28))))
        names.append(o.name)
        if shadow and not heads_only:
            sh = bpy.data.objects.new(f'{name}_s{i}', _shadow_mesh())
            sc.collection.objects.link(sh)
            sh.location = (x, y + .02, z)
            sh.scale = (s * .3, s * .3, 1)
            sh.visible_shadow = False
    return names


def crowd(name, x0, x1, y0, y1, n, seed=1, z=0, height=1.9, bob=.03, grade=None, heads_only=False):
    """n small flat people standing on the ground in the world rectangle x0..x1, y0..y1 (jittered grid, back rows first), idle bob via MOVERS.
    height = metres (a person); heads_only: head+shoulders sprites only (for stands, fences). Faces -Y. Returns names."""
    rnd = random.Random(seed)
    w, d = max(.1, x1 - x0), max(.1, y1 - y0)
    cols = max(1, round(math.sqrt(n * w / d)))
    rows = max(1, math.ceil(n / cols))
    cells = [(c, r) for r in range(rows) for c in range(cols)]
    rnd.shuffle(cells)
    pts = []
    for c, r in cells[:n]:
        x = x0 + (c + rnd.uniform(.1, .9)) / cols * w
        y = y0 + (r + rnd.uniform(.1, .9)) / rows * d
        pts.append((x, y, z))
    pts.sort(key=lambda p: -p[1])
    return _people(name, pts, height, bob, grade, heads_only, seed + 7)


def grandstand(name, loc, w, rows, seed=1, depth=.8, rise=.5, crowd_h=1.55, bob=.03, grade=None, heads_only=False, hex='#5d6674', fill=.92):
    """Tiered seating, back at +Y, front step at loc.y, with people sunk into the steps (seated look). loc = world position of the front-centre
    on the ground. Returns the group."""
    g = group(name, None, loc)
    top = mat('stand_top', '#7c8696', .7)
    face = mat('stand_face_' + hex[1:], hex, .8)
    for r in range(rows):
        dep = (rows - r) * depth
        o = bx(f'{name}_t{r}', (w, dep, (r + 1) * rise), (0, r * depth + dep / 2, (r + 1) * rise / 2), face, g)
        bx(f'{name}_tt{r}', (w, depth * .98, .04), (0, r * depth + depth / 2, (r + 1) * rise + .002), top, g)
    hmax = rows * rise
    bx(f'{name}_back', (w + .3, .2, hmax + 1.8), (0, rows * depth + .1, (hmax + 1.8) / 2), mat('stand_back', '#3d4452', .8), g)
    for sx in (-1, 1):
        bx(f'{name}_side{sx}', (.2, rows * depth + .2, hmax + .9), (sx * (w / 2 + .1), rows * depth / 2, (hmax + .9) / 2), mat('stand_back', '#3d4452', .8), g)
    rail = mat('stand_rail', '#e8ecf2', .5, .4)
    bx(f'{name}_rail', (w, .06, .06), (0, -.05, .95), rail, g)
    for k in range(int(w / 1.6) + 1):
        bx(f'{name}_rp{k}', (.05, .05, .95), (-w / 2 + k * w / max(1, int(w / 1.6)), -.05, .475), rail, g)
    rnd = random.Random(seed)
    pts = []
    sp = .5 if not heads_only else .42
    per = max(1, int(w * fill / sp))
    for r in range(rows):
        for c in range(per):
            x = -w * fill / 2 + (c + .5 + rnd.uniform(-.25, .25)) * (w * fill / per)
            pts.append((loc[0] + x, loc[1] + r * depth + depth * .5 + rnd.uniform(-.08, .08), loc[2] + (r + 1) * rise))
    pts.sort(key=lambda p: -p[1])
    _people(name + '_p', pts, crowd_h, bob, grade, heads_only, seed + 3, sink=.0 if heads_only else .44, shadow=False, lift=.0 if not heads_only else .12)
    return g


# ---------------------------------------------------------------- vehicles (+X forward, origin = ground centre, flat painted look)
def _vm(hexc):
    return dict(body=mat('veh_' + hexc[1:], hexc, .42), dark=mat('veh_dark', '#232730', .6), tire=mat('veh_tire', '#14161b', .9),
                hub=mat('veh_hub', '#aab0bc', .7), glass=mat('veh_glass', '#8cc6e6', .15, .1, .25), trim=mat('veh_trim', '#eef0f4', .5),
                head=mat('veh_head', '#ffe9a0', .3, 0, 3.0), tail=mat('veh_tail', '#e02b2b', .3, 0, 2.0))


def _wheel(n, g, x, y, r, w, m):
    cyl(f'{n}_t', r, w, (x, y, r), m['tire'], g, rot=(math.pi / 2, 0, 0), seg=20)
    cyl(f'{n}_h', r * .55, w + .03, (x, y, r), m['hub'], g, rot=(math.pi / 2, 0, 0), seg=14)


def _wheels(n, g, xs, track, r, w, m):
    for i, x in enumerate(xs):
        for s in (-1, 1):
            _wheel(f'{n}_w{i}{"p" if s > 0 else "m"}', g, x, s * (track / 2 - w / 2), r, w, m)


def _lights(n, g, xf, xb, wid, z, m, hz=.2):
    for s in (-1, 1):
        bx(f'{n}_hl{s}', (.08, .32, hz), (xf, s * wid * .33, z), m['head'], g, bevel=.02)
        bx(f'{n}_tl{s}', (.08, .32, hz), (xb, s * wid * .33, z), m['tail'], g, bevel=.02)


def car(name, loc, hex='#d63a3a'):
    """Chunky flat-shaded hatchback, 4.4 m long, facing +X. Returns the top-level group."""
    g = group(name, None, loc)
    m = _vm(hex)
    bx(f'{name}_ch', (4.4, 1.85, .66), (0, 0, .62), m['body'], g, bevel=.14)
    bx(f'{name}_bump', (4.5, 1.8, .22), (0, 0, .36), m['dark'], g, bevel=.05)
    bx(f'{name}_glass', (2.3, 1.74, .62), (-.35, 0, 1.26), m['glass'], g, bevel=.12)
    bx(f'{name}_roof', (2.2, 1.7, .1), (-.35, 0, 1.6), m['body'], g, bevel=.05)
    for k, x in enumerate((-.35 + .5, -.35 - .5)):
        bx(f'{name}_pil{k}', (.12, 1.76, .6), (x, 0, 1.26), m['body'], g)
    bx(f'{name}_stripe', (4.42, 1.87, .08), (0, 0, .72), m['trim'], g)
    _lights(name, g, 2.2, -2.2, 1.85, .72, m)
    _wheels(name, g, (1.4, -1.4), 1.85, .4, .26, m)
    return g


def van(name, loc, hex='#f2c14e'):
    """Panel van, 5.2 m long, facing +X."""
    g = group(name, None, loc)
    m = _vm(hex)
    bx(f'{name}_cargo', (3.6, 2.0, 2.0), (-.7, 0, 1.5), m['body'], g, bevel=.14)
    bx(f'{name}_cab', (1.9, 2.0, 1.45), (1.65, 0, 1.2), m['body'], g, bevel=.14)
    bx(f'{name}_hood', (.9, 1.95, .8), (2.2, 0, .85), m['body'], g, bevel=.12)
    bx(f'{name}_wind', (.9, 1.88, .7), (1.95, 0, 1.55), m['glass'], g, bevel=.1)
    bx(f'{name}_side', (1.0, 2.04, .6), (1.4, 0, 1.55), m['glass'], g, bevel=.08)
    bx(f'{name}_band', (5.0, 2.02, .12), (0, 0, .95), m['trim'], g)
    bx(f'{name}_bump', (5.3, 1.9, .24), (0, 0, .38), m['dark'], g, bevel=.05)
    _lights(name, g, 2.65, -2.5, 2.0, .6, m, .24)
    _wheels(name, g, (1.8, -1.6), 2.0, .43, .28, m)
    return g


def truck(name, loc, hex='#e8ecf2', cab_hex='#d63a3a'):
    """Box lorry, 10 m long: cab in cab_hex, cargo box in hex (a flat side for a decal), facing +X."""
    g = group(name, None, loc)
    m, mc = _vm(hex), _vm(cab_hex)
    bx(f'{name}_frame', (9.6, 1.9, .4), (0, 0, .75), m['dark'], g, bevel=.05)
    bx(f'{name}_cargo', (6.8, 2.5, 3.0), (-1.4, 0, 2.55), m['body'], g, bevel=.1)
    bx(f'{name}_cab', (2.0, 2.4, 2.3), (3.2, 0, 2.0), mc['body'], g, bevel=.18)
    bx(f'{name}_wind', (.5, 2.3, 1.0), (4.05, 0, 2.55), mc['glass'], g, bevel=.1)
    bx(f'{name}_side', (1.0, 2.44, .95), (3.4, 0, 2.55), mc['glass'], g, bevel=.08)
    bx(f'{name}_grille', (.12, 1.7, .5), (4.2, 0, 1.45), mc['dark'], g, bevel=.03)
    bx(f'{name}_bump', (.3, 2.4, .3), (4.25, 0, .8), mc['trim'], g, bevel=.05)
    _lights(name, g, 4.28, -4.82, 2.3, 1.05, m, .25)
    _wheels(name, g, (3.2, -1.2, -3.0), 2.3, .55, .36, m)
    return g


def bus(name, loc, hex='#f2a93b'):
    """City bus, 10.5 m long, window band + door, facing +X."""
    g = group(name, None, loc)
    m = _vm(hex)
    bx(f'{name}_body', (10.5, 2.5, 3.0), (0, 0, 1.95), m['body'], g, bevel=.25)
    bx(f'{name}_skirt', (10.55, 2.52, .4), (0, 0, .75), m['dark'], g, bevel=.05)
    bx(f'{name}_band', (10.6, 2.54, .16), (0, 0, 1.45), m['trim'], g)
    bx(f'{name}_win', (9.2, 2.54, .95), (-.3, 0, 2.25), m['glass'], g, bevel=.06)
    for k in range(6):
        bx(f'{name}_pil{k}', (.14, 2.56, 1.0), (-4.3 + k * 1.7, 0, 2.25), m['body'], g)
    bx(f'{name}_door', (.9, 2.55, 1.9), (3.6, 0, 1.75), m['glass'], g, bevel=.05)
    bx(f'{name}_wind', (.1, 2.2, 1.2), (5.28, 0, 2.3), m['glass'], g, bevel=.05)
    bx(f'{name}_dest', (.1, 1.6, .3), (5.28, 0, 3.15), m['dark'], g)
    bx(f'{name}_ac', (2.0, 1.4, .3), (-1.5, 0, 3.55), m['trim'], g, bevel=.05)
    _lights(name, g, 5.28, -5.28, 2.5, .85, m, .22)
    _wheels(name, g, (3.4, -3.2), 2.5, .58, .34, m)
    return g


def train_car(name, loc, hex='#2f6fbf'):
    """Passenger rail car, 14 m long, rounded body, two bogies, facing +X."""
    g = group(name, None, loc)
    m = _vm(hex)
    bx(f'{name}_body', (14, 2.9, 3.3), (0, 0, 2.45), m['body'], g, bevel=.55)
    bx(f'{name}_stripe', (14.05, 2.92, .45), (0, 0, 1.55), m['trim'], g)
    bx(f'{name}_win', (12.6, 2.94, .9), (0, 0, 2.7), m['glass'], g, bevel=.08)
    for k in range(8):
        bx(f'{name}_pil{k}', (.18, 2.96, .95), (-5.6 + k * 1.6, 0, 2.7), m['body'], g)
    bx(f'{name}_roof', (12, 1.6, .25), (0, 0, 4.2), m['dark'], g, bevel=.08)
    bx(f'{name}_frame', (13.2, 2.3, .5), (0, 0, .95), m['dark'], g, bevel=.05)
    for s, x in enumerate((4.6, -4.6)):
        bx(f'{name}_bg{s}', (3.2, 2.4, .35), (x, 0, .6), m['dark'], g, bevel=.05)
        _wheels(f'{name}_b{s}', g, (x - 1.0, x + 1.0), 2.5, .5, .22, m)
    _lights(name, g, 7.0, -7.0, 2.9, 1.2, m, .3)
    return g


def cargo_ship(name, loc, hex='#c0392b'):
    """Container ship, 30 m long, bow to +X, stacked containers, bridge aft. Origin = waterline centre."""
    g = group(name, None, loc)
    m = _vm(hex)
    bx(f'{name}_hull', (26, 6, 3.2), (-1, 0, .6), m['body'], g, bevel=.1)
    b = cyl(f'{name}_bow', 3.0, 3.2, (12, 0, .6), m['body'], g, seg=4)
    b.rotation_euler = (0, 0, 0)
    bx(f'{name}_boot', (26.1, 6.02, .5), (-1, 0, -.8), m['dark'], g)
    bx(f'{name}_deck', (26, 5.6, .15), (-1, 0, 2.28), m['dark'], g)
    cols = ('#e8503a', '#2f6fbf', '#f2c14e', '#3fa56b', '#e8ecf2', '#8a5ac8')
    rnd = random.Random(5)
    for i in range(7):
        for j in range(3):
            for k in range(rnd.choice((2, 3, 3))):
                bx(f'{name}_c{i}{j}{k}', (3.2, 1.7, 1.2), (-11 + i * 3.4, (j - 1) * 1.85, 3.0 + k * 1.25), mat('ship_c_' + cols[(i + j * 2 + k) % 6][1:], cols[(i + j * 2 + k) % 6], .55), g, bevel=.03)
    bx(f'{name}_bridge', (3.2, 5.2, 3.6), (-12.5, 0, 4.2), m['trim'], g, bevel=.08)
    bx(f'{name}_bwin', (.1, 4.6, .7), (-10.9, 0, 5.4), m['glass'], g)
    bx(f'{name}_fun', (1.4, 1.6, 1.8), (-13.2, 0, 6.8), m['body'], g, bevel=.1)
    return g


def forklift(name, loc, hex='#f2a93b'):
    """Compact forklift, 2.6 m long incl. forks, facing +X."""
    g = group(name, None, loc)
    m = _vm(hex)
    bx(f'{name}_body', (2.0, 1.15, .75), (-.2, 0, .75), m['body'], g, bevel=.1)
    bx(f'{name}_cw', (.7, 1.15, 1.0), (-1.0, 0, 1.0), m['dark'], g, bevel=.1)
    bx(f'{name}_seat', (.6, .7, .5), (-.35, 0, 1.4), m['dark'], g, bevel=.05)
    for sx in (.5, -.9):
        for sy in (-1, 1):
            bx(f'{name}_cg{sx}{sy}', (.07, .07, 1.2), (sx, sy * .5, 1.75), m['dark'], g)
    bx(f'{name}_roof', (1.5, 1.2, .08), (-.2, 0, 2.38), m['dark'], g)
    for sy in (-1, 1):
        bx(f'{name}_mast{sy}', (.1, .1, 2.4), (.95, sy * .3, 1.25), m['dark'], g)
        bx(f'{name}_fork{sy}', (1.1, .12, .06), (1.5, sy * .38, .1), m['trim'], g)
    bx(f'{name}_car', (.12, .95, .8), (1.0, 0, .85), m['dark'], g)
    _wheels(name, g, (.55, -.8), 1.15, .3, .2, m)
    return g


_KINDS = (car, van, bus, truck, car, van)
_PAL = ('#d63a3a', '#2f6fbf', '#f2c14e', '#3fa56b', '#e8ecf2', '#8a5ac8', '#f2863a')


def traffic(name, y, z, ox, n, speed, wrap=60, seed=1, spread=36, kinds=None):
    """A convoy of n vehicles on lane y (world), height z, spread evenly over `spread` m centred on ox at frame 0, driving +X at `speed` m per frame
    (0.15 = 4.5 m/s; negative drives -X and turns them round). The engine moves all cars by the same wrapped offset, so the convoy is rigid and
    jumps back by `wrap` m once it has travelled wrap/2: pick wrap > 2*speed*LEN (or keep the jump off camera) and ox so the convoy is in view
    when you need it. Top-level groups registered in MOVERS. Returns the names."""
    rnd = random.Random(seed)
    kinds = kinds or _KINDS
    out = []
    for i in range(n):
        x = ox - spread / 2 + (i + rnd.uniform(.15, .6)) * spread / n
        g = rnd.choice(kinds)(f'{name}_{i}', (x, y, z), rnd.choice(_PAL))
        if speed < 0:
            g.rotation_euler = (0, 0, math.pi)
        MOVERS.append(dict(obj=g.name, vel=(speed, 0, 0), wrap=wrap))
        out.append(g.name)
    return out

# ---------------------------------------------------------------- insert props
def _ink_for(bg):
    """white or near-black text colour, whichever contrasts more with bg (hex)."""
    def lum(h):
        c = [((int(h[i:i + 2], 16) / 255 + .055) / 1.055) ** 2.4 if int(h[i:i + 2], 16) / 255 > .04045 else int(h[i:i + 2], 16) / 255 / 12.92 for i in (1, 3, 5)]
        return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]
    lb = lum(bg)
    cw, cb = 1.05 / (lb + .05), (lb + .05) / (lum('#10131a') + .05)
    return '#ffffff' if cw >= cb else '#10131a'


def _fit(body, base, maxw):
    return min(base, maxw / (max(len(s) for s in body.split('\n')) * .40))


def phone(name, loc, screen_png=None, screen_lines=('Inbox (0)',), parent=None, hex='#20242c', scale=1.0, hero=False):
    """Phone facing -Y, centre at loc. scale=1: .30 x .62 m (fills the frame from ~.6 m; text readable at .5 m); hero=True x3 for wide shots.
    screen_png: image on the screen (fits width). screen_lines: first = header bar, rest = list rows (3D text on contrasting bars)."""
    s = scale * (3.0 if hero else 1.0)
    W, H, D = .30 * s, .62 * s, .034 * s
    g = group(name, parent, loc)
    body = mat(f'{name}_body', hex, .35, .3)
    bx(f'{name}_b', (W, D, H), (0, 0, 0), body, g, bevel=.035 * s)
    for k, z in enumerate((.12, .02)):
        bx(f'{name}_bt{k}', (.012 * s, .02 * s, .07 * s), (W / 2 + .004 * s, 0, z * s), body, g)
    sw, sh = W * .92, H * .95
    fy = -D / 2 - .001 * s
    bx(f'{name}_scr', (sw, .004 * s, sh), (0, fy + .002 * s, 0), mat(f'{name}_scrm', '#f4f6fb', .3), g)
    if screen_png:
        image_plane(f'{name}_img', screen_png, sw, (0, fy - .002 * s, 0), g)
    else:
        lines = list(screen_lines) or ['']
        top = sh / 2
        bx(f'{name}_notch', (.07 * s, .006 * s, .018 * s), (0, fy - .001 * s, top - .03 * s), mat('ph_dark', '#10131a', .5), g, bevel=.006 * s)
        hd = .1 * s
        hy = top - .08 * s - hd / 2
        bx(f'{name}_hd', (sw, .005 * s, hd), (0, fy - .002 * s, hy), mat(f'{name}_hdm', '#1c3a6b', .5), g)
        text3d(f'{name}_hdt', lines[0], _fit(lines[0], .055 * s, sw * .9), (0, fy - .006 * s, hy), mat('ph_white', '#ffffff', .5), g, ext=.002 * s)
        rest = lines[1:]
        rh = min(.085 * s, (sh - .21 * s) / max(1, len(rest)))
        for i, ln in enumerate(rest):
            zz = hy - hd / 2 - .012 * s - rh / 2 - i * (rh + .006 * s)
            bg = '#dfe6f2' if i % 2 == 0 else '#c9d4e8'
            bx(f'{name}_r{i}', (sw * .96, .005 * s, rh), (0, fy - .002 * s, zz), mat(f'ph_row{i % 2}', bg, .5), g)
            text3d(f'{name}_rt{i}', ln, _fit(ln, rh * .6, sw * .88), (0, fy - .006 * s, zz), mat('ph_ink', '#10131a', .5), g, ext=.002 * s)
    bx(f'{name}_home', (.09 * s, .006 * s, .006 * s), (0, fy - .003 * s, -sh / 2 + .012 * s), mat('ph_dark', '#10131a', .5), g)
    return g


def calendar(name, loc, pages=('MAY', 'JUN', 'JUL'), size=.6, parent=None, days=(31, 30, 31), start=(3, 6, 1), period=False):
    """Wall calendar, `size` m wide, 1.3 x taller, faces -Y. Page groups `<name>_p0..` (p0 in front) hinged at the top edge: story objs
    `{<name>_p0: dict(rot=(deg,0,0))}`, negative degrees flip it up and over (toon_props_story.calendar_flip does it). days/start (weekday offset) per page.
    period=True: printed paper pages from toon_props_story.calendar_png (assets\\cal_<name>_<i>.png, same page count) on curled sheets lit by the
    scene, hung from a nail on a card back, the front page dog-eared: paper that belongs to the world. Hang it on plain wall, not over a window."""
    w, h = size, size * 1.3
    g = group(name, parent, loc)
    if period:
        bx(f'{name}_back', (w * 1.04, .006 * size, h * 1.03), (0, .004 * size, -h * .015), mat('calp_back', '#5b4630', .9), g)
        cyl(f'{name}_nail', .012 * size, .05 * size, (0, -.03 * size, h / 2 + .02 * size), mat('calp_nail', '#3a3430', .4, .7), g, rot=(math.radians(90), 0, 0), seg=10)
        n = len(pages)
        for i in range(n):
            p = group(f'{name}_p{i}', g, (0, -(.008 + .005 * (n - 1 - i)) * size, h / 2))
            _sheet(f'{name}_p{i}_bg', p, w, h, .03, asset(f'cal_{name}_{i}.png'), hang=True, curl=.02 + .012 * (n - 1 - i), ear=.05 if i == 0 else 0)
        return g
    bx(f'{name}_board', (w + .05 * size, .02 * size, h + .06 * size), (0, 0, 0), mat('cal_board', '#3b4252', .6), g, bevel=.01 * size)
    bx(f'{name}_pin', (.03 * size, .02 * size, .03 * size), (0, -.02 * size, h / 2 + .04 * size), mat('cal_pin', '#d0d3d8', .3, .8), g)
    paper = mat('cal_paper', '#fbfaf5', .8)
    red = mat('cal_red', '#c42b2b', .6)
    white = mat('cal_white', '#ffffff', .5)
    ink = mat('cal_ink', '#16202e', .6)
    wk = mat('cal_wk', '#8a1f1f', .6)
    n = len(pages)
    for i, mo in enumerate(pages):
        y = -(.014 + .006 * (n - 1 - i)) * size
        p = group(f'{name}_p{i}', g, (0, y, h / 2))
        bx(f'{name}_p{i}_bg', (w, .004 * size, h), (0, 0, -h / 2), paper, p)
        bx(f'{name}_p{i}_band', (w, .004 * size, h * .2), (0, -.003 * size, -h * .1), red, p)
        text3d(f'{name}_p{i}_mo', mo, h * .15, (0, -.008 * size, -h * .1), white, p, ext=.006 * size)
        gy0 = -h * .31
        for c, dn in enumerate('SMTWTFS'):
            text3d(f'{name}_p{i}_d{c}', dn, h * .042, (-w * .42 + c * w * .84 / 6, -.006 * size, gy0), wk if c in (0, 6) else ink, p, ext=.003 * size)
        nd, st = days[i % len(days)], start[i % len(start)]
        for d in range(nd):
            r, c = divmod(d + st, 7)
            text3d(f'{name}_p{i}_n{d}', str(d + 1), h * .052, (-w * .42 + c * w * .84 / 6, -.006 * size, gy0 - h * .075 - r * h * .105), wk if c in (0, 6) else ink, p, ext=.003 * size)
    return g


def newspaper(name, loc, headline, sub='', size=1.0, bend=.25, parent=None, glow=0.0):
    """Front page `size` m wide (1.3 x taller) curved toward the lens (bend = edge sag as a fraction of half-width), faces -Y. Texture comes from
    toon_props_story.newspaper_png(reel, name, headline, sub) (assets\\news_<name>.png) and bends with the surface; without it, a flat-tinted paper
    with the headline as 3D text on a plate (cannot bend). Lit by the scene like real paper; glow=.35 was the old self-lit look."""
    w, h = size, size * 1.3
    g = group(name, parent, loc)
    img = asset(f'news_{name}.png')
    _sheet(name, g, w, h, bend, img, glow)
    if not img.exists():
        plate(f'{name}_hl', headline.upper(), size * .12, (0, -.02, 0), '#16130f', '#efe6cf', parent=g)
    return g


def _sheet(name, parent, w, h, bend, img, glow=0.0, hang=False, curl=0.0, ear=0.0):
    """Paper sheet facing -Y, lit by the scene: bend sags the side edges (fraction of half-width), curl lifts the bottom edge toward the lens
    (fraction of width), ear dog-ears the bottom-right corner. hang=True hinges it at the top edge (z 0 .. -h). img (path) is printed on it;
    glow > 0 adds self light (0 = paper that belongs to the world, the default)."""
    nx, nz = 40, 20
    sag = bend * w / 2
    verts, uv = [], []
    for j in range(nz + 1):
        for i in range(nx + 1):
            u, v = i / nx, j / nz
            x = (u - .5) * w
            y = sag * (2 * u - 1) ** 2 + .015 * w * math.sin(v * 3.1) * (1 - abs(2 * u - 1)) - curl * w * (1 - v) ** 2
            y -= ear * w * max(0.0, (u - .82) / .18 + (.14 - v) / .14 - 1) ** 2
            verts.append((x, y, (v - 1) * h if hang else (v - .5) * h))
            uv.append((u, v))
    faces = [(j * (nx + 1) + i, j * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i) for j in range(nz) for i in range(nx)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    uvl = me.uv_layers.new()
    for li, lp in enumerate(me.loops):
        uvl.data[li].uv = uv[lp.vertex_index]
    for pl in me.polygons:
        pl.use_smooth = True
    me.update()
    o = bpy.data.objects.new(name + '_sheet', me)
    sc.collection.objects.link(o)
    o.parent = parent
    m = bpy.data.materials.new(name + '_paper')
    m.use_nodes = True
    nt = m.node_tree
    pr = nt.nodes['Principled BSDF']
    pr.inputs['Roughness'].default_value = .85
    if img and Path(img).exists():
        tx = nt.nodes.new('ShaderNodeTexImage')
        tx.image = bpy.data.images.load(str(img), check_existing=True)
        nt.links.new(tx.outputs['Color'], pr.inputs['Base Color'])
        if glow:
            nt.links.new(tx.outputs['Color'], pr.inputs['Emission Color'])
            pr.inputs['Emission Strength'].default_value = glow
    else:
        pr.inputs['Base Color'].default_value = (*srgb('#efe6cf'), 1)
    me.materials.append(m)
    return o


def sign_board(name, loc, lines, hex='#e8384f', parent=None, size=.5, width=None):
    """Wall board with a border and bolts; each text line is white or near-black (whichever contrasts most with `hex`) on the board itself.
    lines: str or list; first line is largest. size = text height of line 1 (m). Faces -Y, centre at loc."""
    lines = [lines] if isinstance(lines, str) else list(lines)
    g = group(name, parent, loc)
    sizes = [size] + [size * .55] * (len(lines) - 1)
    wmax = max(len(l) * sz * .46 for l, sz in zip(lines, sizes))
    W = width or wmax + size * .8
    H = sum(sz * 1.25 for sz in sizes) + size * .6
    fg = _ink_for(hex)
    bx(f'{name}_bd', (W, .06, H), (0, 0, 0), mat(f'{name}_bm', hex, .5), g, bevel=.02)
    bx(f'{name}_fr', (W + .08, .04, H + .08), (0, .02, 0), mat('sign_frame', '#2b303b', .5, .3), g, bevel=.02)
    fm = mat(f'{name}_fg', fg, .5)
    y = H / 2 - size * .3
    for i, (l, sz) in enumerate(zip(lines, sizes)):
        y -= sz * .62
        text3d(f'{name}_l{i}', l, sz, (0, -.034, y), fm, g, ext=min(.012, sz * .03))
        y -= sz * .62
    for sx in (-1, 1):
        for sz_ in (-1, 1):
            cyl(f'{name}_bolt{sx}{sz_}', .018, .02, (sx * (W / 2 - .06), -.035, sz_ * (H / 2 - .06)), mat('sign_bolt', '#c9ced8', .3, .8), g, rot=(math.pi / 2, 0, 0), seg=10)
    return g



