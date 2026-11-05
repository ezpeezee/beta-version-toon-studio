"""Blender helpers for toon sets: materials, painted surfaces, boxes, cylinders, 3D text and plates, image planes, ceilings, distant view, models.
A reel's sets.py does `from toon_lib import *` and builds its sets with these (see API.md). Imported only inside Blender (toon_world.py)."""
import json
import math
import os
import sys
from pathlib import Path

import bpy

KIT = Path(__file__).parent
ROOT = Path(__file__).resolve().parents[3]   # project root: <ROOT>\Reels\pipeline\toon\toon_lib.py
REEL = Path(os.environ['TOON_REEL']) if 'TOON_REEL' in os.environ else KIT
ANTON = str(ROOT / 'Reels' / 'assets' / 'brand' / 'fonts' / 'Anton-Regular.ttf')
BRAND = str(ROOT / 'Reels' / 'assets' / 'brand' / 'logo.png')   # your logo (transparent PNG); the shipped one is blank
TEX = ROOT / 'Reels' / 'assets' / 'polyhaven' / 'textures'
MODELS = ROOT / 'Reels' / 'assets' / 'polyhaven' / 'models'
MAX_CARDS = 10
sc = bpy.context.scene
font = bpy.data.fonts.load(ANTON)


def asset(name):
    """<reel>\\assets\\name if it exists, else the kit's assets\\name."""
    p = REEL / 'assets' / name
    return p if p.exists() else KIT / 'assets' / name


def init_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    sc.render.engine = 'BLENDER_EEVEE'
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.render.resolution_x, sc.render.resolution_y = 1080, 1920
    sc.render.fps = 30
    sc.render.film_transparent = False
    try:
        sc.eevee.use_raytracing = True
        sc.eevee.fast_gi_method = 'GLOBAL_ILLUMINATION'
        sc.eevee.fast_gi_distance = 2.5
        sc.eevee.ray_tracing_options.resolution_scale = '4'
    except Exception as e:
        print('NO_RT', e)
    wnt = bpy.data.worlds.new('w')
    sc.world = wnt
    wnt.use_nodes = True
    sd = bpy.data.lights.new('sun', 'SUN')
    sun = bpy.data.objects.new('sun', sd)
    sc.collection.objects.link(sun)
    cd = bpy.data.cameras.new('cam')
    cam = bpy.data.objects.new('cam', cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.rotation_mode = 'QUATERNION'
    apply_scene({})


def apply_scene(o):
    """SCENE dict from sets.py: world, world_strength, sun, sun_energy, sun_angle, sun_rot (deg xyz), lens."""
    w = bpy.data.worlds['w'].node_tree.nodes['Background']
    w.inputs['Color'].default_value = (*srgb(o.get('world', '#ffe8d0')), 1)
    w.inputs['Strength'].default_value = o.get('world_strength', .5)
    sd = bpy.data.lights['sun']
    # Studio edition: a softer, dimmer sun and fill
    w.inputs['Strength'].default_value *= .8
    sd.energy, sd.angle, sd.color = o.get('sun_energy', 3.2) * .7, math.radians(max(14, o.get('sun_angle', 3.5))), srgb(o.get('sun', '#fff1d8'))
    bpy.data.objects['sun'].rotation_euler = tuple(math.radians(v) for v in o.get('sun_rot', (58, 0, -32)))
    bpy.data.cameras['cam'].lens = o.get('lens', 26)




def pool(key, prefix, n, img, size, scale=1.0):
    """Hidden slip/bill sprites the renderer flies along story streams (story key `key`)."""
    m = bpy.data.materials.new(key)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    tx = nt.nodes.new('ShaderNodeTexImage')
    tx.image = bpy.data.images.load(str(asset(img)))
    em = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(tx.outputs['Color'], em.inputs['Color'])
    nt.links.new(em.outputs[0], nt.nodes.new('ShaderNodeOutputMaterial').inputs['Surface'])
    me = bpy.data.meshes.new(prefix)
    w, h = size[0] / 2, size[1] / 2
    me.from_pydata([(-w, 0, -h), (w, 0, -h), (w, 0, h), (-w, 0, h)], [], [(0, 1, 2, 3)])
    me.uv_layers.new().data.foreach_set('uv', [0, 0, 1, 0, 1, 1, 0, 1])
    me.update()
    me.materials.append(m)
    for i in range(n):
        o = bpy.data.objects.new(f'{prefix}{i}', me)
        sc.collection.objects.link(o)
        o.hide_render = True
        o.visible_shadow = False
    return dict(key=key, prefix=prefix, n=n, scale=scale)


def finish(ns, out):
    """After sets.py ran: scene overrides, sprite pools, card planes + contact shadows, metadata for the renderer, save."""
    apply_scene(ns.get('SCENE', {}))
    pools = ns.get('POOLS')
    if pools is None:
        pools = [pool('tickets', 'tk', 260, 'slip.png', (.18, .1), 1.6), pool('bills', 'bl', 70, 'bill.png', (.26, .12))]
    for i in range(MAX_CARDS):
        card_plane(f'card{i}', None, (0, 0, 0), 1200 / 1900, 1.0, base=True)
    shm = bpy.data.materials.new('contact')
    shm.use_nodes = True
    nt = shm.node_tree
    nt.nodes.clear()
    tc = nt.nodes.new('ShaderNodeTexCoord')
    vm = nt.nodes.new('ShaderNodeVectorMath')
    vm.operation = 'LENGTH'
    nt.links.new(tc.outputs['Object'], vm.inputs[0])
    ra = nt.nodes.new('ShaderNodeValToRGB')
    ra.color_ramp.elements[0].position, ra.color_ramp.elements[0].color = 0, (.62, .62, .62, 1)
    ra.color_ramp.elements[1].position, ra.color_ramp.elements[1].color = 1, (0, 0, 0, 1)
    nt.links.new(vm.outputs['Value'], ra.inputs['Fac'])
    mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(ra.outputs['Color'], mx.inputs[0])
    nt.links.new(nt.nodes.new('ShaderNodeBsdfTransparent').outputs[0], mx.inputs[1])
    sh_col = nt.nodes.new('ShaderNodeEmission')
    sh_col.inputs['Color'].default_value = (.04, .03, .06, 1)
    nt.links.new(sh_col.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], nt.nodes.new('ShaderNodeOutputMaterial').inputs['Surface'])
    shm.surface_render_method = 'BLENDED'
    for i in range(MAX_CARDS):
        bpy.ops.mesh.primitive_circle_add(vertices=32, radius=1, fill_type='NGON', location=(0, 0, 0))
        o = bpy.context.object
        o.name = f'shadow{i}'
        o.data.materials.append(shm)
        o.visible_shadow = False
        o.hide_render = True
    # toon_sets and toon_props each keep a MOVERS list; a star import of both shadows one, so merge them all by object
    movers = {m['obj']: m for lst in (getattr(sys.modules.get(k), 'MOVERS', []) for k in ('toon_sets', 'toon_props')) for m in lst}
    movers.update({m['obj']: m for m in ns.get('MOVERS', [])})
    sc['toon'] = json.dumps(dict(hidden=ns.get('HIDDEN', []), face_cam=ns.get('FACE_CAM', []), pools=pools, movers=list(movers.values()), max_cards=MAX_CARDS))
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    print('WORLD_OK', out)


def srgb(h):
    return tuple(((int(h[i:i + 2], 16) / 255 + .055) / 1.055) ** 2.4 for i in (1, 3, 5))


def mat(name, h, rough=.85, metal=0.0, glow=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*srgb(h), 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    if glow:
        p.inputs['Emission Color'].default_value = (*srgb(h), 1)
        p.inputs['Emission Strength'].default_value = glow
    return m


def sock(node, ident):
    return next(x for x in node.inputs if x.identifier == ident)


def out_color(node):
    return next(x for x in node.outputs if x.identifier == 'Result_Color')


# Real surfaces (the default look): painted() swaps chosen tex names for real CC0 maps (assets\tex\<key>\diff/nor/rough.jpg,
# Poly Haven) tinted toward the painted colour. Off unless sets.py calls real_surfaces(); keys: cobblestone plaster_wall roof_tiles stone_blocks
# dirt_path planks dark_timber (a reel's assets\tex\<key> wins; add new ones from Poly Haven and log them in CREDITS).
OLD_TOWN = dict(floor_tiles_06=('cobblestone', .7), painted_plaster_wall=('plaster_wall', .55), metal_plate=('roof_tiles', .55),
                concrete_wall_008=('stone_blocks', .45), dry_ground_01=('dirt_path', .4))
WOOD = ('door', 'stall', 'crate', 'barrel', 'desk', 'pew', 'plank', 'gate_dr', 'bench', 'shelf', 'table')
_REAL = dict(on=False, map={}, wood=())


def real_surfaces(map=OLD_TOWN, wood=WOOD):
    """Call at the top of sets.py: painted() then routes tex names in map to real(), and material names containing a wood word to planks/dark_timber."""
    return None  # Studio edition: plain painted surfaces only


def _img(nt, path, nonc):
    t = nt.nodes.new('ShaderNodeTexImage')
    t.image = bpy.data.images.load(str(path), check_existing=True)
    if nonc:
        t.image.colorspace_settings.name = 'Non-Color'
    t.projection, t.projection_blend = 'BOX', .3
    return t


def real(name, key, h, h2, tsc, nstr=.8, tint=.55, gain=1.35):
    """Real texture tinted toward the set's painted colour: diffuse x colour, normal map, roughness map, box-projected in object space."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = mat(name, h)
    nt = m.node_tree
    pr = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    ma = nt.nodes.new('ShaderNodeMapping')
    ma.inputs['Scale'].default_value = (tsc, tsc, tsc)
    nt.links.new(tc.outputs['Object'], ma.inputs['Vector'])
    d, n, r = (_img(nt, asset(f'tex/{key}/{f}'), nc) for f, nc in (('diff.jpg', 0), ('nor.jpg', 1), ('rough.jpg', 1)))
    for t in (d, n, r):
        nt.links.new(ma.outputs['Vector'], t.inputs['Vector'])
    mx = nt.nodes.new('ShaderNodeMix')
    mx.data_type, mx.blend_type = 'RGBA', 'MULTIPLY'
    sock(mx, 'Factor_Float').default_value = tint
    c = [(x + y) / 2 for x, y in zip(srgb(h), srgb(h2))]
    sock(mx, 'B_Color').default_value = (*[min(1, v * 1.6) for v in c], 1)
    nt.links.new(d.outputs['Color'], sock(mx, 'A_Color'))
    hs = nt.nodes.new('ShaderNodeHueSaturation')
    hs.inputs['Value'].default_value = gain
    nt.links.new(out_color(mx), hs.inputs['Color'])
    nt.links.new(hs.outputs['Color'], pr.inputs['Base Color'])
    nm = nt.nodes.new('ShaderNodeNormalMap')
    nm.inputs['Strength'].default_value = nstr
    nt.links.new(n.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], pr.inputs['Normal'])
    nt.links.new(r.outputs['Color'], pr.inputs['Roughness'])
    return m


def spot(name, loc, aim, energy, col, size_deg, blend=.12, radius=.04):
    """A hard spot light (sun through a window) aimed from loc at aim: sharp shafts and character shadows on interior walls."""
    from mathutils import Vector
    o = bpy.data.objects.new(name, None)  # Studio edition: no window shafts, just a marker
    sc.collection.objects.link(o)
    o.location = loc
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = (Vector(aim) - Vector(loc)).to_track_quat('-Z', 'Y')
    return o


def painted(name, h, h2, scale=.55, cut=.56, tex='painted_plaster_wall', tscale=.6, grain=.45, grad=None, bump=.25):
    """Painted surface: soft colour forms, optional darkening toward the floor (grad = (z0, z1, dark factor))."""
    tex, bump = None, 0  # Studio edition: no texture grain or bump
    if _REAL['on']:
        if any(w in name for w in _REAL['wood']):
            return real(name, 'planks' if 'plank' in name or 'desk' in name else 'dark_timber', h, h2, .9, tint=.5)
        if tex in _REAL['map']:
            k, s = _REAL['map'][tex]
            return real(name, k, h, h2, s)
    m = mat(name, h)
    nt = m.node_tree
    pr = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    no = nt.nodes.new('ShaderNodeTexNoise')
    no.inputs['Scale'].default_value = scale
    no.inputs['Detail'].default_value = 4
    ra = nt.nodes.new('ShaderNodeValToRGB')
    # the two swatches pushed apart so the forms actually read
    c0 = tuple(v * .9 for v in srgb(h))
    c1 = tuple(min(1, v * 1.08) for v in srgb(h2))
    ra.color_ramp.elements[0].position = .34
    ra.color_ramp.elements[0].color = (*c0, 1)
    ra.color_ramp.elements[1].position = .66
    ra.color_ramp.elements[1].color = (*c1, 1)
    nt.links.new(tc.outputs['Object'], no.inputs['Vector'])
    nt.links.new(no.outputs['Fac'], ra.inputs['Fac'])
    last = ra.outputs['Color']
    if tex:
        ma = nt.nodes.new('ShaderNodeMapping')
        ma.inputs['Scale'].default_value = (tscale, tscale, tscale)
        nt.links.new(tc.outputs['Object'], ma.inputs['Vector'])
        ti = nt.nodes.new('ShaderNodeTexImage')
        ti.image = bpy.data.images.load(str(TEX / tex / f'{tex}_diff_1k.jpg'), check_existing=True)
        ti.projection = 'BOX'
        ti.projection_blend = .25
        nt.links.new(ma.outputs['Vector'], ti.inputs['Vector'])
        bw = nt.nodes.new('ShaderNodeRGBToBW')
        nt.links.new(ti.outputs['Color'], bw.inputs['Color'])
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.inputs['From Min'].default_value, mr.inputs['From Max'].default_value = .15, .75
        mr.inputs['To Min'].default_value, mr.inputs['To Max'].default_value = 1 - grain, 1 + grain * .35
        nt.links.new(bw.outputs['Val'], mr.inputs['Value'])
        mx = nt.nodes.new('ShaderNodeVectorMath')
        mx.operation = 'SCALE'
        nt.links.new(last, mx.inputs[0])
        nt.links.new(mr.outputs['Result'], mx.inputs['Scale'])
        last = mx.outputs['Vector']
        if bump:
            bu = nt.nodes.new('ShaderNodeBump')
            bu.inputs['Strength'].default_value = bump
            bu.inputs['Distance'].default_value = .02
            nt.links.new(bw.outputs['Val'], bu.inputs['Height'])
            nt.links.new(bu.outputs['Normal'], pr.inputs['Normal'])
    if grad:
        ge = nt.nodes.new('ShaderNodeNewGeometry')
        se = nt.nodes.new('ShaderNodeSeparateXYZ')
        nt.links.new(ge.outputs['Position'], se.inputs[0])
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.inputs['From Min'].default_value, mr.inputs['From Max'].default_value = grad[0], grad[1]
        mr.inputs['To Min'].default_value, mr.inputs['To Max'].default_value = grad[2], 1
        nt.links.new(se.outputs['Z'], mr.inputs['Value'])
        mx = nt.nodes.new('ShaderNodeVectorMath')
        mx.operation = 'SCALE'
        nt.links.new(last, mx.inputs[0])
        nt.links.new(mr.outputs['Result'], mx.inputs['Scale'])
        last = mx.outputs['Vector']
    nt.links.new(last, pr.inputs['Base Color'])
    return m


def model(name, loc, scale=1.0, rz=0.0, parent=None):
    """Import a CC0 Poly Haven glTF under one empty (an empty group if the model is not installed)."""
    if not (MODELS / name / f'{name}_1k.gltf').exists():
        return group(f'{name}_{len(bpy.data.objects)}', parent, loc)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(MODELS / name / f'{name}_1k.gltf'))
    new = set(bpy.data.objects) - before
    g = group(f'{name}_{len(bpy.data.objects)}', parent, loc)
    for o in new:
        if o.parent is None:
            o.parent = g
    g.scale = (scale, scale, scale)
    g.rotation_euler = (0, 0, math.radians(rz))
    return g


def group(name, parent=None, loc=(0, 0, 0)):
    o = bpy.data.objects.new(name, None)
    sc.collection.objects.link(o)
    o.location = loc
    o.parent = parent
    return o


def bx(name, size, loc, m, parent=None, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True, location=False, rotation=False)
    o.data.materials.append(m)
    if parent:
        o.parent = parent
    if bevel:
        b = o.modifiers.new('b', 'BEVEL')
        b.width, b.segments = bevel, 2
    return o


def cyl(name, r, depth, loc, m, parent=None, rot=(0, 0, 0), seg=32):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=rot, vertices=seg)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    if parent:
        o.parent = parent
    return o


FONTS = dict(anton=ANTON, **{k: str(ROOT / 'Reels' / 'assets' / 'brand' / 'fonts' / v) for k, v in dict(
    slab='AlfaSlabOne-Regular.ttf', serif='PlayfairDisplay.ttf', chalk='Caveat.ttf', type='SpecialElite-Regular.ttf', black='UnifrakturMaguntia-Regular.ttf').items()})
_fonts = {}


def get_font(f):
    """None = Anton; a FONTS key (slab serif chalk type black) or a path to a .ttf. Period signs use the serif faces."""
    if not f:
        return font
    p = FONTS.get(f, f)
    if p not in _fonts:
        _fonts[p] = bpy.data.fonts.load(p)
    return _fonts[p]


def text3d(name, body, size, loc, m, parent=None, rz=0.0, ext=.012, align='CENTER', font_=None):
    """Real extruded, bevelled text standing on a wall that faces -Y. font_: see get_font."""
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body, cu.font, cu.size = body, get_font(font_), size
    cu.extrude, cu.bevel_depth = ext, ext * .3
    cu.align_x, cu.align_y = align, 'CENTER'
    o = bpy.data.objects.new(name, cu)
    sc.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (math.radians(90), 0, rz)
    cu.materials.append(m)
    if parent:
        o.parent = parent
    return o


def aged(name, h, grime=.3):
    """Old paper / painted board: flat matte colour in this edition."""
    return mat(name, h, .9)


def plate(name, body, size, loc, bg, fg, pad=(.16, .1), parent=None, depth=.03, font_=None, flat_=False, aged_=False):
    """Text on a contrasting plate (rule 42). Width estimated per face (Anton is narrow, the slab is wide).
    flat_=True prints the text flat on the plate (paint, chalk, ink) instead of raised letters.
    aged_=True makes it a period thing that belongs to the world: aged board/paper (see aged), matte printed ink, hung a hair off level on two nails,
    lit by the scene only (no glow). Use it for every sign, notice and label in a period set."""
    g = group(name, parent, loc)
    wk = dict(slab=.74, serif=.56, chalk=.42, type=.62, black=.5).get(font_, .46)
    w = max(len(l) for l in body.split('\n')) * size * wk + pad[0] * 2
    h = (body.count('\n') + 1) * size * 1.15 + pad[1] * 2
    bx(name + '_bg', (w, depth, h), (0, 0, 0), aged(name + '_bgm', bg) if aged_ else mat(name + '_bgm', bg), g, bevel=.008)
    text3d(name + '_tx', body, size, (0, -depth / 2 - .004, 0), mat(name + '_fgm', fg, .95 if aged_ else .85), g,
           ext=.0005 if (flat_ or aged_) else min(.012, size * .025), font_=font_)
    if aged_:
        g.rotation_euler.y = math.radians(((sum(map(ord, name)) % 7) - 3) * .4)
        for sx in (-1, 1):
            cyl(f'{name}_nail{sx}', min(.02, h * .04), .02, (sx * (w / 2 - min(.06, w * .06)), -depth / 2 - .006, h / 2 - min(.06, h * .1)),
                mat('aged_nail', '#3a3430', .4, .7), g, rot=(math.radians(90), 0, 0), seg=8)
    return g


def image_plane(name, path, w, loc, parent=None, rx=90.0, lit=False):
    """Picture plane facing -Y. Default is unlit (a screen or overlay); lit=True is a printed thing in the world (map, poster, photo):
    lit by the scene, matte, casts a shadow."""
    img = bpy.data.images.load(str(path), check_existing=True)
    h = w * img.size[1] / max(1, img.size[0])
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)], [], [(0, 1, 2, 3)])
    me.uv_layers.new().data.foreach_set('uv', [0, 0, 1, 0, 1, 1, 0, 1])
    me.update()
    o = bpy.data.objects.new(name, me)
    sc.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (math.radians(rx), 0, 0)
    o.parent = parent
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    tx = nt.nodes.new('ShaderNodeTexImage')
    tx.image = img
    if lit:
        em = nt.nodes.new('ShaderNodeBsdfPrincipled')
        em.inputs['Roughness'].default_value = .88
        nt.links.new(tx.outputs['Color'], em.inputs['Base Color'])
    else:
        em = nt.nodes.new('ShaderNodeEmission')
        nt.links.new(tx.outputs['Color'], em.inputs['Color'])
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(tx.outputs['Alpha'], mx.inputs[0])
    nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], nt.nodes.new('ShaderNodeOutputMaterial').inputs['Surface'])
    m.surface_render_method = 'BLENDED'
    me.materials.append(m)
    o.visible_shadow = lit
    return o


def card_plane(name, parent, loc, w, h, base=False):
    """Unlit flat picture plane: image node TEX through a Multiply GRADE into Emission + alpha. Stands in XZ, facing -Y."""
    z0, z1 = (0, h) if base else (-h / 2, h / 2)
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-w / 2, 0, z0), (w / 2, 0, z0), (w / 2, 0, z1), (-w / 2, 0, z1)], [], [(0, 1, 2, 3)])
    me.uv_layers.new().data.foreach_set('uv', [0, 0, 1, 0, 1, 1, 0, 1])
    me.update()
    o = bpy.data.objects.new(name, me)
    sc.collection.objects.link(o)
    o.location = loc
    o.parent = parent
    o.visible_shadow = False
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    tx = nt.nodes.new('ShaderNodeTexImage')
    tx.name = 'TEX'
    gr = nt.nodes.new('ShaderNodeMix')
    gr.name = 'GRADE'
    gr.data_type = 'RGBA'
    gr.blend_type = 'MULTIPLY'
    gr.inputs[0].default_value = 1
    sock(gr, 'B_Color').default_value = (1, 1, 1, 1)
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
    me.materials.append(m)
    return o


def set_ceiling(prefix, parent, w, y0, y1, z, tile='#eee7d8', lamp='#fff6df', step=.75):
    """Ceiling tiles with a grid and light panels; never blocks the sun."""
    cy = (y0 + y1) / 2
    o = bx(prefix + 'ceil', (w, y1 - y0, .1), (0, cy, z + .06), painted(prefix + 'ceilm', tile, tile, .6, tscale=2.2, grain=.2), parent)
    o.visible_shadow = False
    g = mat(prefix + 'grid', '#b6ad9b', .6)
    for k in range(int(-w / 2 / step), int(w / 2 / step) + 1):
        o = bx(f'{prefix}gx{k}', (.03, y1 - y0, .03), (k * step, cy, z), g, parent)
        o.visible_shadow = False
    n = int((y1 - y0) / step)
    for k in range(n + 1):
        o = bx(f'{prefix}gy{k}', (w, .03, .03), (0, y0 + k * step, z), g, parent)
        o.visible_shadow = False
    for i, xx in enumerate((-3, 0, 3)):
        for j, yy in enumerate((y1 - 1.2, y1 - 3.5)):
            o = bx(f'{prefix}l{i}_{j}', (1.42, .68, .02), (xx, yy, z - .005), mat(prefix + 'lampm', lamp, glow=1.5), parent)
            o.visible_shadow = False


def distant_view(prefix, cx, wy, parent=None):
    """The far view: sky, then three skyline layers fading into haze, each a real distance behind the wall."""
    for nm, dy, w, zc in (('sky', 70, 170, 30), ('far', 48, 150, 19), ('mid', 24, 80, 7.5), ('near', 10, 40, 2.4)):
        o = image_plane(prefix + nm, asset(f'view_{nm}.png'), w, (cx, wy + dy + cx * .01, zc), parent)
        o.active_material.use_backface_culling = False






def room_set(name, ox=0.0, floor=('#d9782f', '#e08a3c'), wall=('#e9dcc0', '#f4e8cc'), wain=('#17908f', '#1fa7a2'), trim='#f2c14e', view=True, wy=2.7):
    """A ready room: tiled floor, wainscot + plaster back wall with a ribbon window onto the distant view, side walls, lit ceiling. Camera side is -Y, back wall at y=wy.
    Returns the group. Names are prefixed with `name`; call once per set, each at its own ox (sets sit 60 m apart)."""
    g = group(name, None, (ox, 0, 0))
    p = name + '_'
    bx(p + 'floor', (40, 16, .1), (0, -3, -.05), painted(p + 'fl', floor[0], floor[1], .35, tex='floor_tiles_06', tscale=.45, grain=.6, bump=.5), g)
    wall_m = painted(p + 'wall', wall[0], wall[1], .4, grad=(2.5, 5.2, .82))
    wain_m = painted(p + 'wain', wain[0], wain[1], .5, tex='floor_tiles_06', tscale=.9, grain=.5, bump=.5, grad=(0, 2.5, .7))
    frame_m = painted(p + 'frame', '#b8bcc4', '#d0d3d8', 2.0, tex='metal_plate', tscale=1.0, grain=.3)
    bx(p + 'wall_low', (22, .2, 2.5), (0, wy, 1.25), wain_m, g)
    bx(p + 'wall_top', (22, .2, 2.0), (0, wy, 5.9), wall_m, g)
    bx(p + 'wall_trim', (22, .34, .12), (0, wy - .03, 2.56), mat(p + 'trim', trim, .5), g)
    bx(p + 'wall_head', (22, .3, .1), (0, wy - .02, 4.92), frame_m, g)
    for k in range(-8, 9):
        wide = k in (-3, -1, 2)
        bx(f'{p}mull{k}', (.95 if wide else .1, .3 if wide else .24, 2.4), (k * 1.3, wy + .02, 3.74), wall_m if wide else frame_m, g)
        bx(f'{p}tran{k}', (1.3, .1, .05), ((k + .5) * 1.3, wy, 3.7), frame_m, g)
    if view:
        distant_view(p + 'v_', ox, wy)
    side_m = painted(p + 'side', wain[0], wain[1], .45, grad=(0, 5.2, .72))
    bx(p + 'wall_left', (.2, 14, 11), (-5.6, -3, 5.5), side_m, g)
    bx(p + 'wall_right', (.2, 14, 11), (5.6, -3, 5.5), side_m, g)
    set_ceiling(p, g, 22, -11, 3, 5.3)
    return g

