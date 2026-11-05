"""Ready-made 3D sets for toon reels. A reel's sets.py does `from toon_sets import *` (this re-exports everything from toon_lib).
Each `<place>_set(name, ox=0.0, **colours)` builds one set at world x=ox and returns its group; names are prefixed with `name`.
Sets sit 60 m apart in x. Characters stand near (ox, 0, 0); the camera is on the -Y side. Everything stays inside a 32 m sky dome centred on ox.
Outdoor: street_set desert_set rooftop_set sea_set. Indoor: bank_set trading_set datacenter_set factory_set store_set.
Helpers: sky clouds haze sunbeam skyline fog win_mat. Moving parts are appended to MOVERS (the renderer reads ns['MOVERS']).
Import in sets.py with `from toon_sets import *` and never rebind MOVERS."""
import itertools
import random

from toon_lib import *  # noqa: F401,F403  (re-exported on purpose)

MOVERS = []
R_SKY = 32.0
_ctr = itertools.count()


# ----------------------------------------------------------------------------- small helpers
def _id(p, k):
    return f'{p}{k}{next(_ctr)}'


def _lerp(h1, h2, t):
    a = [int(h1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(h2[i:i + 2], 16) for i in (1, 3, 5)]
    return '#%02x%02x%02x' % tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def _rad(r):
    return tuple(math.radians(a) for a in r)


def _noshadow(o):
    o.visible_shadow = False
    return o


def box(g, p, k, size, loc, m, bevel=0.0, rot=None, shadow=True):
    o = bx(_id(p, k), size, loc, m, g, bevel)
    if rot:
        o.rotation_euler = _rad(rot)
    if not shadow:
        o.visible_shadow = False
    return o


def cy(g, p, k, r, d, loc, m, rot=(0, 0, 0), seg=20, shadow=True):
    """Cylinder; rot in degrees. Default axis is Z; rot=(90,0,0) lies along Y, (0,90,0) along X."""
    o = cyl(_id(p, k), r, d, loc, m, g, _rad(rot), seg)
    if not shadow:
        o.visible_shadow = False
    return o


def ball(g, p, k, r, loc, m, scl=(1, 1, 1), seg=14, shadow=True):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=seg, ring_count=max(6, seg // 2), location=loc)
    o = bpy.context.object
    o.name = _id(p, k)
    o.scale = scl
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    o.parent = g
    if not shadow:
        o.visible_shadow = False
    return o


def cone(g, p, k, r1, r2, d, loc, m, seg=16, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=d, vertices=seg, location=loc, rotation=_rad(rot))
    o = bpy.context.object
    o.name = _id(p, k)
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    o.parent = g
    return o


def ring(g, p, k, R, r, loc, m, rot=(90, 0, 0), seg=28):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=seg, minor_segments=8, location=loc, rotation=_rad(rot))
    o = bpy.context.object
    o.name = _id(p, k)
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    o.parent = g
    return o


def dup(src, g, loc, rot=None, scl=None, name=None):
    """Linked duplicate (shares mesh and materials)."""
    o = bpy.data.objects.new(name or f'{src.name.split(".")[0]}_d{next(_ctr)}', src.data)
    sc.collection.objects.link(o)
    o.location = loc
    o.parent = g
    if rot:
        o.rotation_euler = _rad(rot)
    if scl:
        o.scale = scl
    o.visible_shadow = src.visible_shadow
    return o


def quad(g, name, w, h, loc, m, roll=0.0):
    """Flat plane standing in XZ facing -Y (UV 0..1); roll = degrees around Y."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-w / 2, 0, -h / 2), (w / 2, 0, -h / 2), (w / 2, 0, h / 2), (-w / 2, 0, h / 2)], [], [(0, 1, 2, 3)])
    me.uv_layers.new().data.foreach_set('uv', [0, 0, 1, 0, 1, 1, 0, 1])
    me.update()
    o = bpy.data.objects.new(name, me)
    sc.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (0, math.radians(roll), 0)
    o.parent = g
    o.visible_shadow = False
    me.materials.append(m)
    return o


def disc(g, p, k, r, loc, m, scl=(1, 1, 1), seg=24):
    """Flat filled disc standing in XZ facing -Y."""
    bpy.ops.mesh.primitive_circle_add(vertices=seg, radius=r, fill_type='NGON', location=loc, rotation=(math.pi / 2, 0, 0))
    o = bpy.context.object
    o.name = _id(p, k)
    o.scale = scl
    o.data.materials.append(m)
    o.parent = g
    o.visible_shadow = False
    return o


def lamp(g, p, loc, energy=600, hex='#ffd9a0', size=.3, shadow=False):
    ld = bpy.data.lights.new(_id(p, 'L'), 'POINT')
    ld.energy, ld.color, ld.shadow_soft_size, ld.use_shadow = energy, srgb(hex), size, shadow
    o = bpy.data.objects.new(ld.name, ld)
    sc.collection.objects.link(o)
    o.location = loc
    o.parent = g
    return o


# ----------------------------------------------------------------------------- node-graph helpers
def _set(nt, s, v):
    if isinstance(v, str):
        s.default_value = (*srgb(v), 1)
    elif isinstance(v, (int, float)):
        s.default_value = v
    elif isinstance(v, tuple):
        s.default_value = v
    else:
        nt.links.new(v, s)


def _m(nt, op, a=None, b=None, c=None, clamp=False):
    n = nt.nodes.new('ShaderNodeMath')
    n.operation = op
    n.use_clamp = clamp
    for i, v in enumerate((a, b, c)):
        if v is not None:
            _set(nt, n.inputs[i], v)
    return n.outputs[0]


def _mix(nt, fac, a, b):
    n = nt.nodes.new('ShaderNodeMix')
    n.data_type = 'RGBA'
    _set(nt, n.inputs[0], fac)
    _set(nt, sock(n, 'A_Color'), a)
    _set(nt, sock(n, 'B_Color'), b)
    return out_color(n)


def _wn(nt, w):
    n = nt.nodes.new('ShaderNodeTexWhiteNoise')
    n.noise_dimensions = '1D'
    _set(nt, n.inputs['W'], w)
    return n.outputs['Value']


def _pos(nt):
    ge = nt.nodes.new('ShaderNodeNewGeometry')
    se = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(ge.outputs['Position'], se.inputs[0])
    return se.outputs['X'], se.outputs['Y'], se.outputs['Z']


def _objpos(nt):
    tc = nt.nodes.new('ShaderNodeTexCoord')
    se = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Object'], se.inputs[0])
    return se.outputs['X'], se.outputs['Y'], se.outputs['Z']


def _new_mat(name):
    m = bpy.data.materials.get(name)
    if m:
        return None, m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m.node_tree, m


def flat(name, h, alpha=1.0, strength=1.0):
    """Unlit flat colour (emission), optionally translucent."""
    nt, m = _new_mat(name)
    if nt is None:
        return m
    nt.nodes.clear()
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*srgb(h), 1)
    em.inputs['Strength'].default_value = strength
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    if alpha < 1:
        tr = nt.nodes.new('ShaderNodeBsdfTransparent')
        mx = nt.nodes.new('ShaderNodeMixShader')
        mx.inputs[0].default_value = alpha
        nt.links.new(tr.outputs[0], mx.inputs[1])
        nt.links.new(em.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out.inputs['Surface'])
        m.surface_render_method = 'BLENDED'
    else:
        nt.links.new(em.outputs[0], out.inputs['Surface'])
    return m


def glass(name, h='#9fd4ff', alpha=.28):
    return flat(name, h, alpha, 1.0)


def fog(m, h, r0, r1):
    """Blend a ground material toward colour h between r0 and r1 metres from the object's centre (so it melts into the sky's horizon)."""
    nt = m.node_tree
    pr = nt.nodes['Principled BSDF']
    bc = pr.inputs['Base Color']
    src = bc.links[0].from_socket if bc.links else tuple(bc.default_value)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    vm = nt.nodes.new('ShaderNodeVectorMath')
    vm.operation = 'LENGTH'
    nt.links.new(tc.outputs['Object'], vm.inputs[0])
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value, mr.inputs['From Max'].default_value = r0, r1
    nt.links.new(vm.outputs['Value'], mr.inputs['Value'])
    nt.links.new(_mix(nt, mr.outputs['Result'], src, h), bc)
    return m


def win_mat(name, wall, wall2=None, glass_hex='#2b4163', lit='#ffd27a', sx=1.7, sz=2.1, frac=.3, below=0.0, glow=3.0, seed=0.0):
    """Building wall: soft painted colour forms, a grid of windows, a fraction lit. Uses world position, so it works on every face."""
    nt, m = _new_mat(name)
    if nt is None:
        return m
    pr = nt.nodes['Principled BSDF']
    pr.inputs['Roughness'].default_value = .9
    X, Y, Z = _pos(nt)
    cu = _m(nt, 'DIVIDE', _m(nt, 'ADD', X, Y), sx)
    cz = _m(nt, 'DIVIDE', Z, sz)
    fx, fz = _m(nt, 'FRACT', cu), _m(nt, 'FRACT', cz)
    mk = _m(nt, 'MULTIPLY', _m(nt, 'GREATER_THAN', fx, .2), _m(nt, 'LESS_THAN', fx, .76))
    mk = _m(nt, 'MULTIPLY', mk, _m(nt, 'GREATER_THAN', fz, .28))
    mk = _m(nt, 'MULTIPLY', mk, _m(nt, 'LESS_THAN', fz, .8))
    if below:
        mk = _m(nt, 'MULTIPLY', mk, _m(nt, 'GREATER_THAN', Z, below))
    cell = _m(nt, 'ADD', _m(nt, 'ADD', _m(nt, 'FLOOR', cu), _m(nt, 'MULTIPLY', _m(nt, 'FLOOR', cz), 7.31)), seed)
    litm = _m(nt, 'MULTIPLY', mk, _m(nt, 'GREATER_THAN', _wn(nt, cell), 1 - frac))
    wc = wall
    if wall2:
        tc = nt.nodes.new('ShaderNodeTexCoord')
        no = nt.nodes.new('ShaderNodeTexNoise')
        no.inputs['Scale'].default_value, no.inputs['Detail'].default_value = .22, 3
        nt.links.new(tc.outputs['Generated'], no.inputs['Vector'])
        ge = nt.nodes.new('ShaderNodeNewGeometry')
        nt.links.new(ge.outputs['Position'], no.inputs['Vector'])
        wc = _mix(nt, _m(nt, 'MULTIPLY_ADD', no.outputs['Fac'], 3.0, -1.2, clamp=True), wall, wall2)
    nt.links.new(_mix(nt, mk, wc, glass_hex), pr.inputs['Base Color'])
    pr.inputs['Emission Color'].default_value = (*srgb(lit), 1)
    nt.links.new(_m(nt, 'MULTIPLY', litm, glow), pr.inputs['Emission Strength'])
    return m


def stripe_mat(name, c1, c2, period=.8, duty=.5, diag=True):
    """Diagonal (hazard) stripes in the XY plane, or stripes along Y if diag is False."""
    nt, m = _new_mat(name)
    if nt is None:
        return m
    pr = nt.nodes['Principled BSDF']
    pr.inputs['Roughness'].default_value = .7
    X, Y, Z = _pos(nt)
    u = _m(nt, 'DIVIDE', _m(nt, 'ADD', X, Y) if diag else Y, period)
    nt.links.new(_mix(nt, _m(nt, 'GREATER_THAN', _m(nt, 'FRACT', u), duty), c1, c2), pr.inputs['Base Color'])
    return m


def checker_mat(name, c1, c2, size=1.6, rough=.3):
    nt, m = _new_mat(name)
    if nt is None:
        return m
    pr = nt.nodes['Principled BSDF']
    pr.inputs['Roughness'].default_value = rough
    tc = nt.nodes.new('ShaderNodeTexCoord')
    ch = nt.nodes.new('ShaderNodeTexChecker')
    ch.inputs['Scale'].default_value = 1.0 / size
    ch.inputs['Color1'].default_value = (*srgb(c1), 1)
    ch.inputs['Color2'].default_value = (*srgb(c2), 1)
    ge = nt.nodes.new('ShaderNodeNewGeometry')
    nt.links.new(ge.outputs['Position'], ch.inputs['Vector'])
    no = nt.nodes.new('ShaderNodeTexNoise')
    no.inputs['Scale'].default_value, no.inputs['Detail'].default_value = .5, 4
    nt.links.new(ge.outputs['Position'], no.inputs['Vector'])
    va = _m(nt, 'MULTIPLY_ADD', no.outputs['Fac'], .35, .82)
    mx = nt.nodes.new('ShaderNodeVectorMath')
    mx.operation = 'SCALE'
    nt.links.new(ch.outputs['Color'], mx.inputs[0])
    nt.links.new(va, mx.inputs['Scale'])
    nt.links.new(mx.outputs['Vector'], pr.inputs['Base Color'])
    return m


def plank_mat(name, c1, c2, w=.55, ln=3.2):
    """Deck planks along X: staggered butt joints, a dark seam and a tone shift per board (uses world position)."""
    nt, m = _new_mat(name)
    if nt is None:
        return m
    pr = nt.nodes['Principled BSDF']
    pr.inputs['Roughness'].default_value = .75
    X, Y, Z = _pos(nt)
    row = _m(nt, 'FLOOR', _m(nt, 'DIVIDE', Y, w))
    off = _m(nt, 'MULTIPLY', _wn(nt, row), ln)
    cx = _m(nt, 'DIVIDE', _m(nt, 'ADD', X, off), ln)
    board = _m(nt, 'ADD', _m(nt, 'MULTIPLY', row, 13.7), _m(nt, 'FLOOR', cx))
    tone = _wn(nt, board)
    base = _mix(nt, tone, c1, c2)
    seam = _m(nt, 'LESS_THAN', _m(nt, 'FRACT', _m(nt, 'DIVIDE', Y, w)), .07)
    seam2 = _m(nt, 'LESS_THAN', _m(nt, 'FRACT', cx), .012)
    sm = _m(nt, 'MAXIMUM', seam, seam2)
    nt.links.new(_mix(nt, sm, base, _lerp(c1, '#000000', .55)), pr.inputs['Base Color'])
    return m


def screen_mat(name, w, h, n=14, up='#38e08a', down='#ff4d5e', bg='#07111c', strength=1.6, seed=0.0):
    """Emissive bar/candle chart for a box of size w x h standing in XZ (uses object coords)."""
    nt, m = _new_mat(name)
    if nt is None:
        return m
    nt.nodes.clear()
    X, Y, Z = _objpos(nt)
    u = _m(nt, 'MULTIPLY_ADD', X, 1.0 / w, .5)
    v = _m(nt, 'MULTIPLY_ADD', Z, 1.0 / h, .5)
    un = _m(nt, 'MULTIPLY', u, n)
    i = _m(nt, 'ADD', _m(nt, 'FLOOR', un), seed)
    n1, n2 = _wn(nt, i), _wn(nt, _m(nt, 'ADD', i, 17.3))
    hh = _m(nt, 'MULTIPLY_ADD', n1, .62, .18)
    fu = _m(nt, 'FRACT', un)
    bar = _m(nt, 'MULTIPLY', _m(nt, 'LESS_THAN', v, hh), _m(nt, 'MULTIPLY', _m(nt, 'GREATER_THAN', fu, .16), _m(nt, 'LESS_THAN', fu, .84)))
    bar = _m(nt, 'MULTIPLY', bar, _m(nt, 'MULTIPLY', _m(nt, 'GREATER_THAN', u, .03), _m(nt, 'LESS_THAN', u, .97)))
    col = _mix(nt, _m(nt, 'GREATER_THAN', n2, .45), down, up)
    fin = _mix(nt, bar, bg, col)
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Strength'].default_value = strength
    nt.links.new(fin, em.inputs['Color'])
    nt.links.new(em.outputs[0], nt.nodes.new('ShaderNodeOutputMaterial').inputs['Surface'])
    return m


def stock_mat(name, palette, cw=.34, ch=.36, board=.07, pitch=.8):
    """Shelves stocked with products (colour cells), boards every `pitch` metres. Works on x- and y-facing faces."""
    nt, m = _new_mat(name)
    if nt is None:
        return m
    pr = nt.nodes['Principled BSDF']
    pr.inputs['Roughness'].default_value = .8
    X, Y, Z = _pos(nt)
    cu = _m(nt, 'DIVIDE', _m(nt, 'ADD', X, Y), cw)
    cz = _m(nt, 'DIVIDE', Z, ch)
    cell = _m(nt, 'ADD', _m(nt, 'FLOOR', cu), _m(nt, 'MULTIPLY', _m(nt, 'FLOOR', cz), 5.9))
    pick = _wn(nt, cell)
    col = palette[0]
    k = len(palette)
    for j in range(1, k):
        col = _mix(nt, _m(nt, 'GREATER_THAN', pick, j / k), col, palette[j])
    gapx = _m(nt, 'MULTIPLY', _m(nt, 'GREATER_THAN', _m(nt, 'FRACT', cu), .08), _m(nt, 'LESS_THAN', _m(nt, 'FRACT', cu), .92))
    topgap = _m(nt, 'LESS_THAN', _m(nt, 'FRACT', cz), _m(nt, 'ADD', .55, _m(nt, 'MULTIPLY', _wn(nt, _m(nt, 'ADD', cell, 3.1)), .4)))
    prod = _m(nt, 'MULTIPLY', gapx, topgap)
    fz = _m(nt, 'FRACT', _m(nt, 'DIVIDE', Z, pitch))
    brd = _m(nt, 'LESS_THAN', fz, board / pitch)
    base = _mix(nt, prod, '#2a2f3a', col)
    nt.links.new(_mix(nt, brd, base, '#cdbb99'), pr.inputs['Base Color'])
    return m


def led_mat(name, base='#1b2433', pitch=.65, cells=7, cols=('#3dff8a', '#4aa8ff', '#ffb040'), z0=.3, z1=2.1, glow=5.0):
    """Server-rack front: dark panel, rack seams every `pitch` along Y, rows of blinking-looking LEDs."""
    nt, m = _new_mat(name)
    if nt is None:
        return m
    pr = nt.nodes['Principled BSDF']
    pr.inputs['Roughness'].default_value = .5
    pr.inputs['Metallic'].default_value = .4
    X, Y, Z = _pos(nt)
    cs = pitch / cells
    u, v = _m(nt, 'DIVIDE', Y, cs), _m(nt, 'DIVIDE', Z, cs)
    fu, fv = _m(nt, 'FRACT', u), _m(nt, 'FRACT', v)
    dot = _m(nt, 'MULTIPLY', _m(nt, 'MULTIPLY', _m(nt, 'GREATER_THAN', fu, .2), _m(nt, 'LESS_THAN', fu, .6)),
             _m(nt, 'MULTIPLY', _m(nt, 'GREATER_THAN', fv, .3), _m(nt, 'LESS_THAN', fv, .55)))
    band = _m(nt, 'MULTIPLY', _m(nt, 'GREATER_THAN', Z, z0), _m(nt, 'LESS_THAN', Z, z1))
    seam = _m(nt, 'GREATER_THAN', _m(nt, 'FRACT', _m(nt, 'DIVIDE', Y, pitch)), .03)
    cell = _m(nt, 'ADD', _m(nt, 'FLOOR', u), _m(nt, 'MULTIPLY', _m(nt, 'FLOOR', v), 5.17))
    lit = _m(nt, 'MULTIPLY', _m(nt, 'MULTIPLY', dot, band), _m(nt, 'MULTIPLY', seam, _m(nt, 'GREATER_THAN', _wn(nt, cell), .3)))
    n2 = _wn(nt, _m(nt, 'ADD', cell, 3.3))
    ec = _mix(nt, _m(nt, 'GREATER_THAN', n2, .86), _mix(nt, _m(nt, 'GREATER_THAN', n2, .42), cols[0], cols[1]), cols[2])
    nt.links.new(_mix(nt, _m(nt, 'LESS_THAN', _m(nt, 'FRACT', _m(nt, 'DIVIDE', Y, pitch)), .035), base, '#0b0f16'), pr.inputs['Base Color'])
    nt.links.new(ec, pr.inputs['Emission Color'])
    nt.links.new(_m(nt, 'MULTIPLY', lit, glow), pr.inputs['Emission Strength'])
    return m


def _mover(obj_name, vel, wrap=None, bob=None):
    d = dict(obj=obj_name, vel=tuple(vel))
    if wrap:
        d['wrap'] = wrap
    if bob:
        d['bob'] = tuple(bob)
    MOVERS.append(d)


def _hide_wrap(base, hidden):
    return 2 * (hidden + abs(base))


# ----------------------------------------------------------------------------- shared backdrops
def sky(name, ox=0.0, top='#3d79c4', horizon='#ffc48e', mid=None, r=R_SKY):
    """Gradient sky dome: unlit sphere of radius r (32 m) centred on the set. Everything of the set must sit inside it; it does not reach other sets."""
    g = group(name, None, (ox, 0, 0))
    m = bpy.data.materials.new(name + '_m')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    X, Y, Z = _objpos(nt)
    f = _m(nt, 'POWER', _m(nt, 'MULTIPLY_ADD', Z, 1.15, .02, clamp=True), .85, clamp=True)
    ra = nt.nodes.new('ShaderNodeValToRGB')
    el = ra.color_ramp.elements
    el[0].position, el[0].color = 0.0, (*srgb(horizon), 1)
    el[1].position, el[1].color = 1.0, (*srgb(top), 1)
    e = el.new(.42)
    e.color = (*srgb(mid or _lerp(horizon, top, .5)), 1)
    nt.links.new(f, ra.inputs['Fac'])
    em = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(ra.outputs['Color'], em.inputs['Color'])
    nt.links.new(em.outputs[0], nt.nodes.new('ShaderNodeOutputMaterial').inputs['Surface'])
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=48, ring_count=24, location=(0, 0, 0))
    o = bpy.context.object
    o.name = name + '_dome'
    o.scale = (r, r, r)
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    o.parent = g
    o.visible_shadow = False
    return g


def clouds(name, ox=0.0, n=6, seed=1, hex='#ffffff', outline='#7fa6d6', vel=.012, y=(17, 25), z=(7, 20), span=17, scale=(1.6, 2.8)):
    """Flat outlined painted clouds (discs, white with a blue outline) that drift along +X and wrap (MOVERS). Each cloud is a parentless group."""
    rn = random.Random(seed)
    fill, line = flat(name + '_cf', hex), flat(name + '_co', outline)
    out = []
    for i in range(n):
        s = rn.uniform(*scale)
        cx, cy_, cz = ox + rn.uniform(-span, span), rn.uniform(*y), rn.uniform(*z)
        g = group(f'{name}_c{i}', None, (cx, cy_, cz))
        bl = [(0, 0, 1.0), (-1.15, -.22, .72), (1.2, -.18, .8), (.45, .42, .78), (-.5, .38, .62), (2.0, -.4, .5), (-1.9, -.45, .46)]
        for k, (dx, dz, rr) in enumerate(bl):
            disc(g, name, 'o', rr * s * 1.13, (dx * s, .25, dz * s), line, seg=20)
        for k, (dx, dz, rr) in enumerate(bl):
            disc(g, name, 'f', rr * s, (dx * s, k * .01, dz * s), fill, seg=20)
        _mover(g.name, (vel * rn.uniform(.7, 1.3), 0, 0), wrap=_hide_wrap(cx - ox, 24))
        out.append(g)
    return out


def haze(name, ox=0.0, y=20.0, hex='#ffd9b8', alpha=.5, h=13.0, w=58.0, z0=-1.0, parent=None):
    """Soft translucent layer for distance: opaque at the ground, fading to nothing at height h."""
    nt, m = _new_mat(name + '_m')
    if nt is not None:
        nt.nodes.clear()
        tc = nt.nodes.new('ShaderNodeTexCoord')
        se = nt.nodes.new('ShaderNodeSeparateXYZ')
        nt.links.new(tc.outputs['UV'], se.inputs[0])
        a = _m(nt, 'MULTIPLY', _m(nt, 'POWER', _m(nt, 'SUBTRACT', 1.0, se.outputs['Y']), 1.6), alpha)
        em = nt.nodes.new('ShaderNodeEmission')
        em.inputs['Color'].default_value = (*srgb(hex), 1)
        tr = nt.nodes.new('ShaderNodeBsdfTransparent')
        mx = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(a, mx.inputs[0])
        nt.links.new(tr.outputs[0], mx.inputs[1])
        nt.links.new(em.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], nt.nodes.new('ShaderNodeOutputMaterial').inputs['Surface'])
        m.surface_render_method = 'BLENDED'
    return quad(parent, name, w, h, (ox, y, z0 + h / 2), m)


def sunbeam(name, loc, w=3.0, h=14.0, rot=20.0, hex='#fff1c8', alpha=.22, parent=None):
    """Flat translucent light band (soft edges, fades toward its far end). loc is in the parent's space (world if parent is None); rot = roll in degrees."""
    nt, m = _new_mat(name + '_m')
    if nt is not None:
        nt.nodes.clear()
        tc = nt.nodes.new('ShaderNodeTexCoord')
        se = nt.nodes.new('ShaderNodeSeparateXYZ')
        nt.links.new(tc.outputs['UV'], se.inputs[0])
        side = _m(nt, 'POWER', _m(nt, 'SINE', _m(nt, 'MULTIPLY', se.outputs['X'], math.pi)), 1.4)
        lon = _m(nt, 'MULTIPLY', _m(nt, 'POWER', _m(nt, 'SUBTRACT', 1.0, se.outputs['Y']), .8), _m(nt, 'MULTIPLY', se.outputs['Y'], 6.0, clamp=True))
        a = _m(nt, 'MULTIPLY', _m(nt, 'MULTIPLY', side, lon), alpha)
        em = nt.nodes.new('ShaderNodeEmission')
        em.inputs['Color'].default_value = (*srgb(hex), 1)
        tr = nt.nodes.new('ShaderNodeBsdfTransparent')
        mx = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(a, mx.inputs[0])
        nt.links.new(tr.outputs[0], mx.inputs[1])
        nt.links.new(em.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], nt.nodes.new('ShaderNodeOutputMaterial').inputs['Surface'])
        m.surface_render_method = 'BLENDED'
    return quad(parent, name, w, h, loc, m, roll=rot)


def skyline(name, ox=0.0, y=22.0, base='#7d8fb8', hi=16.0, n=14, seed=3, lit='#ffd27a', span=30.0, glow=1.2, parent=None, top_hex=None):
    """A row of towers (painted, windows, a few lit) at depth y, clamped to stay inside the sky dome. Reuse twice (far hazier, near darker) for depth."""
    rn = random.Random(seed)
    g = parent or group(name, None, (ox, 0, 0))
    mats = [win_mat(f'{name}_wm{i}', _lerp(base, '#ffffff', .05 * i), _lerp(base, '#000000', .1), _lerp(base, '#1c2a4a', .55), lit, sx=1.3, sz=1.7, frac=.28, glow=glow, seed=i * 3.3) for i in range(3)]
    hmax = max(3.0, math.sqrt(max(1.0, R_SKY * R_SKY - y * y)) * .93)
    x = -span
    k = 0
    while x < span:
        w = rn.uniform(2.6, 5.2)
        hh = min(hmax, rn.uniform(.3, 1.0) ** 1.3 * hi + 3)
        o = bx(f'{name}_t{k}', (w, rn.uniform(3, 5), hh + 2), (x + w / 2, y, hh / 2 - 1), mats[k % 3], g)
        o.visible_shadow = False
        if rn.random() < .3 and hh > 9:
            cy(g, name, 'ant', .06, 3.0, (x + w / 2, y, hh + 1.5), flat(name + '_ant', '#c9d2e6'), seg=6, shadow=False)
        x += w + rn.uniform(-.3, .5)
        k += 1
    return g


def _disc_ground(g, p, k, r, z, m, seg=72, thick=.3):
    return cy(g, p, k, r, thick, (0, 0, z - thick / 2), m, seg=seg)


# ----------------------------------------------------------------------------- OUTDOOR SETS
def street_set(name, ox=0.0, **c):
    """City street at dusk: pavement where the characters stand, a road with lane marks and traffic across, shop fronts with signs, tall framing buildings, lamp posts, skyline. Camera -Y."""
    g = group(name, None, (ox, 0, 0))
    p = name + '_'
    rn = random.Random(11)
    top, hor = c.get('sky_top', '#3f7fcf'), c.get('sky_hor', '#ffc48e')
    sky(p + 'sky', ox, top, hor)
    asph = painted(p + 'asph', c.get('road', '#2f3447'), '#444b63', .3, tex='concrete_floor_painted', tscale=.5, grain=.3, bump=.3)
    fog(asph, _lerp(hor, '#6f7f9f', .35), 12, 32)
    _disc_ground(g, p, 'gr', R_SKY + 2, -.12, asph)
    pave = painted(p + 'pave', c.get('pave', '#cfc9d2'), '#d4ced7', 3.0, tex='concrete_floor_painted', tscale=.9, grain=.12, bump=.2)
    box(g, p, 'pv', (62, 16.5, .2), (0, -5.5, -.1), pave)
    box(g, p, 'pv', (62, 3.4, .2), (0, 11.3, -.1), pave)
    cur = mat(p + 'cur', '#b9a888', .8)
    box(g, p, 'cb', (62, .25, .2), (0, 2.87, -.1), cur)
    box(g, p, 'cb', (62, .25, .2), (0, 9.73, -.1), cur)
    # lane marks
    wh, ye = flat(p + 'wh', '#f4efe2'), flat(p + 'ye', '#f2c230')
    d0 = box(g, p, 'dash', (1.8, .16, .02), (-30, 6.3, -.1), wh, shadow=False)
    for i in range(-14, 15):
        if i:
            dup(d0, g, (i * 3.4, 6.3, -.1))
    box(g, p, 'el', (62, .14, .02), (0, 3.45, -.1), wh, shadow=False)
    box(g, p, 'el', (62, .14, .02), (0, 9.15, -.1), wh, shadow=False)
    z0 = box(g, p, 'zeb', (3.4, .5, .02), (7.5, 3.6, -.1), wh, shadow=False)
    for i in range(1, 6):
        dup(z0, g, (7.5, 3.6 + i * 1.0, -.1))
    # cars crossing (parentless group at world position, mover on the group)
    carcols = (c.get('car1', '#e0483d'), c.get('car2', '#f2b83d'))
    for i, (cx, cyy, dirn) in enumerate(((-12, 4.9, -1), (9, 7.7, 1))):
        cg = group(f'{p}car{i}', None, (ox + cx, cyy, 0))
        cm = painted(f'{p}carm{i}', carcols[i], carcols[i], .8, tex=None)
        box(cg, p, 'cb', (3.9, 1.7, .75), (0, 0, .62), cm, bevel=.08)
        box(cg, p, 'cc', (2.1, 1.5, .62), (-.15 * dirn, 0, 1.28), mat(p + 'cglass', '#2a3b57', .2), bevel=.06)
        for wx in (-1.25, 1.25):
            for wy in (-.85, .85):
                cy(cg, p, 'w', .36, .28, (wx, wy, .36), mat(p + 'tire', '#15171d', .9), rot=(90, 0, 0), seg=14)
        for wy in (-.55, .55):
            box(cg, p, 'hl', (.06, .3, .16), (1.96 * dirn, wy, .72), mat(p + 'hl', '#fff2c0', .3, 0, 3.0))
        _mover(cg.name, (.2 * dirn, 0, 0), wrap=_hide_wrap(cx, 22))
    # far shop row facing the camera (front face y=13), a side street gap in the middle
    pal = c.get('walls', ('#e86a52', '#2a9d9b', '#f2b83d', '#7c6cc4', '#e8d9c0'))
    signs = [('BAKERY', '#7a2b1f', '#ffe9b0'), ('CAFE', '#14463f', '#fff2d2'), ('TICKETS', '#1d2b5c', '#ffd34d'), ('BANK', '#10261f', '#e8c35a'), ('OPEN', '#a8222d', '#ffffff'), ('PIZZA', '#2b2235', '#ff9a52'), ('SHOP', '#14463f', '#ffffff'), ('HOTEL', '#10162b', '#ff8fa0')]
    row = [(-30, -23, 13.5), (-23, -15.5, 19), (-15.5, -9.5, 12), (-9.5, -3, 16.5), (4.2, 11.5, 21), (11.5, 18.5, 15), (18.5, 25.5, 18.5), (25.5, 31, 12)]
    fr = 13.0
    for i, (x0, x1, h) in enumerate(row):
        w = x1 - x0
        wc = pal[i % len(pal)]
        wm = win_mat(f'{p}wm{i}', wc, _lerp(wc, '#ffffff', .22), c.get('glass', '#2b4163'), '#ffd27a', sx=1.8, sz=2.2, frac=.28, below=3.9, glow=2.6, seed=i * 5.0)
        cx = (x0 + x1) / 2
        box(g, p, 'bd', (w, 6.5, h), (cx, fr + 3.25, h / 2), wm)
        box(g, p, 'cn', (w + .3, .7, .5), (cx, fr - .15, h + .1), mat(p + 'cn', _lerp(wc, '#000000', .45), .6))
        box(g, p, 'sf', (w - .5, .3, 3.2), (cx, fr - .15, 1.6), mat(p + 'sf', '#2a2430', .6))
        box(g, p, 'gl', (w - 1.6, .05, 2.0), (cx, fr - .33, 1.55), mat(p + 'shopgl', '#ffe0a0', .4, 0, .9))
        box(g, p, 'aw', (w - .8, 1.7, .12), (cx, fr - 1.0, 3.45), mat(f'{p}aw{i % 3}', ('#d94a4a', '#f2f0e6', '#2a9d9b')[i % 3], .8), rot=(-12, 0, 0))
        tx, bg, fg = signs[i % len(signs)]
        plate(f'{p}sign{i}', tx, .62, (cx, fr - .4, 4.55), bg, fg, pad=(.22, .08), parent=g)
        if i % 3 == 0:
            cy(g, p, 'tk', 1.0, 1.6, (cx + w * .25, fr + 3, h + .8), mat(p + 'rooftank', '#6b4a38', .9), seg=12)
        if i % 2:
            box(g, p, 'ac', (1.8, 1.2, 1.0), (cx - w * .25, fr + 2, h + .5), mat(p + 'acbox', '#aab2c0', .6))
    # tall framing buildings left and right (windows on their street faces too)
    for sx_, x0, x1, y0, y1, h, ci in ((-1, -15.5, -8.8, -3.5, 10, 24, 3), (1, 9.0, 15.5, -1, 10, 19, 1)):
        wc = pal[ci]
        wm = win_mat(f'{p}fw{ci}', wc, _lerp(wc, '#ffffff', .2), c.get('glass', '#2b4163'), '#ffd27a', sx=1.9, sz=2.3, frac=.3, below=1.2, glow=2.6, seed=ci * 2.0)
        box(g, p, 'fb', (x1 - x0, y1 - y0, h), ((x0 + x1) / 2, (y0 + y1) / 2, h / 2), wm)
        box(g, p, 'fc', (x1 - x0 + .3, y1 - y0 + .3, .5), ((x0 + x1) / 2, (y0 + y1) / 2, h + .1), mat(p + 'cn', _lerp(wc, '#000000', .45), .6))
        face = x1 if sx_ < 0 else x0
        plate(f'{p}fsign{ci}', ('HOTEL', 'OPEN')[ci == 1], .55, (face, y0 + 3, 4.0), '#10162b' if ci == 3 else '#a8222d', '#ffd34d' if ci == 3 else '#ffffff', pad=(.2, .07), parent=g)
        g.children  # noqa
    # the signs on side faces are flat toward -Y; turn them to face the street
    for ci, sx_ in ((3, 1), (1, -1)):
        o = bpy.data.objects.get(f'{p}fsign{ci}')
        if o:
            o.rotation_euler = (0, 0, math.radians(90 * sx_))
    # lamp posts, props
    iron = mat(p + 'iron', '#2a2f3d', .5, .6)
    lampg = mat(p + 'lampg', '#fff0b8', .3, 0, 4.0)
    for i, (lx, ly) in enumerate(((-5.8, 1.6), (6.2, 1.6), (-6.4, -8.5), (7.4, -9.5))):
        cy(g, p, 'lp', .09, 5.6, (lx, ly, 2.8), iron, seg=8)
        cy(g, p, 'lb', .22, .18, (lx, ly, .1), iron, seg=8)
        box(g, p, 'la', (.9 * (1 if lx < 0 else -1), .1, .1), (lx + .45 * (1 if lx < 0 else -1), ly, 5.5), iron)
        ball(g, p, 'lh', .3, (lx + .9 * (1 if lx < 0 else -1), ly, 5.4), lampg, scl=(1, 1, .7), seg=10, shadow=False)
    lamp(g, p, (-4.9, 1.6, 5.2), 900, '#ffcf8a', .5)
    lamp(g, p, (5.3, 1.6, 5.2), 900, '#ffcf8a', .5)
    # traffic light, hydrant, bin, bollards, mailbox, trees with planters, bench
    cy(g, p, 'tp', .08, 4.2, (10.5, 2.2, 2.1), iron, seg=8)
    box(g, p, 'th', (.38, .3, 1.1), (10.5, 2.2, 4.4), mat(p + 'thb', '#1a1c22', .6))
    for j, hx in enumerate(('#ff3b30', '#ffb020', '#2fd45a')):
        ball(g, p, 'tl', .11, (10.5, 2.04, 4.75 - j * .34), mat(f'{p}tl{j}', hx, .3, 0, 3.0 if j == 2 else .6), seg=8, shadow=False)
    hy = mat(p + 'hyd', '#d63a2e', .6)
    cy(g, p, 'hy', .2, .7, (-3.8, -.4, .35), hy, seg=10)
    ball(g, p, 'hy', .22, (-3.8, -.4, .72), hy, scl=(1, 1, .7), seg=10)
    cy(g, p, 'bn', .35, .95, (3.8, 1.0, .48), mat(p + 'bin', '#3a7d6a', .7), seg=12)
    for i in range(5):
        cy(g, p, 'bo', .11, .8, (-9.5 + i * 1.5, -9.5, .4), mat(p + 'bol', '#f2b83d', .6), seg=10)
    box(g, p, 'mb', (.7, .55, 1.15), (6.0, 2.0, .6), mat(p + 'mail', '#2d5fb8', .6), bevel=.05)
    for tx_, ty_ in ((-7.2, -.5), (8.2, -2.5)):
        box(g, p, 'pl', (1.2, 1.2, .6), (tx_, ty_, .3), mat(p + 'plant', '#8b5a3c', .9))
        cy(g, p, 'tr', .16, 3.0, (tx_, ty_, 2.0), mat(p + 'trunk', '#5a3d2a', .9), seg=8)
        ball(g, p, 'fo', 1.5, (tx_, ty_, 4.1), mat(p + 'leaf', '#4d9a58', .9), scl=(1, 1, 1.1), seg=12)
        ball(g, p, 'fo', 1.0, (tx_ + .8, ty_, 3.5), mat(p + 'leaf2', '#69b564', .9), seg=10)
    wood = mat(p + 'wood', '#8a5a36', .8)
    box(g, p, 'bs', (2.0, .5, .1), (-4.2, 2.1, .55), wood)
    box(g, p, 'bs', (2.0, .1, .5), (-4.2, 2.35, .85), wood)
    for sx_ in (-1.0, 1.0):
        box(g, p, 'bl', (.08, .45, .5), (-4.2 + sx_, 2.1, .25), iron)
    box(g, p, 'nw', (.7, .5, 1.0), (7.4, -3.2, .5), mat(p + 'news', '#d94a4a', .6), bevel=.04)
    plate(p + 'busstop', 'BUS', .5, (-2.5, 2.7, 3.0), '#2d5fb8', '#ffffff', pad=(.15, .06), parent=g)
    cy(g, p, 'bsp', .05, 3.0, (-2.5, 2.7, 1.5), iron, seg=6)
    # brand on a dark plate on the bus stop pole side
    box(g, p, 'bp', (.9, .04, .3), (-2.5, 2.66, 2.4), mat(p + 'bpm', '#101522', .5))
    image_plane(p + 'brand', BRAND, .78, (-2.5, 2.63, 2.4), g)
    # far fog, skyline, sun beams, clouds
    skyline(p + 'sk1', ox, 23.5, _lerp(hor, '#6d7fa8', .6), 17, 14, 5, parent=g)
    haze(p + 'hz1', ox, 21.0, _lerp(hor, '#ffffff', .15), .55, 24, parent=g)
    skyline(p + 'sk0', ox, 18.0, _lerp(hor, '#4c5d8a', .7), 17, 11, 7, parent=g, glow=1.6)
    haze(p + 'hz2', ox, 16.0, hor, .3, 16, parent=g)
    sunbeam(p + 'sb1', (ox - 4, 8, 11), 3.5, 22, 24, '#ffe7b0', .22)
    sunbeam(p + 'sb2', (ox + 5, 6, 12), 2.2, 20, 20, '#ffe7b0', .16)
    clouds(p + 'cl', ox, 7, 4)
    return g


def desert_set(name, ox=0.0, **c):
    """Desert highway: sand, stepped mesas, a road and a railway running into the distance, poles with wires, cacti, rocks, a diner sign, low sun."""
    g = group(name, None, (ox, 0, 0))
    p = name + '_'
    rn = random.Random(5)
    top, hor = c.get('sky_top', '#3f86d6'), c.get('sky_hor', '#ffcf9c')
    sky(p + 'sky', ox, top, hor)
    sand = painted(p + 'sand', c.get('sand', '#d9a05f'), '#ebbd7c', .25, tex='dry_ground_01', tscale=.35, grain=.4, bump=.3)
    fog(sand, _lerp(hor, '#e8b58a', .3), 13, 32)
    _disc_ground(g, p, 'gr', R_SKY + 2, 0, sand)
    # road along Y at x 2..6.4, rail at x -6
    asph = painted(p + 'asph', '#3b3e4a', '#4a4e5c', .4, tex='concrete_floor_painted', tscale=.6, grain=.3, bump=.2)
    box(g, p, 'rd', (4.6, 70, .08), (4.2, 8, .04), asph)
    ye, wh = flat(p + 'ye', '#f0c030'), flat(p + 'wh', '#f4efe2')
    for xx in (4.1, 4.3):
        box(g, p, 'cl', (.09, 70, .02), (xx, 8, .09), ye, shadow=False)
    box(g, p, 'el', (.12, 70, .02), (2.1, 8, .09), wh, shadow=False)
    box(g, p, 'el', (.12, 70, .02), (6.3, 8, .09), wh, shadow=False)
    gravel = painted(p + 'gravel', '#8f8478', '#b0a595', .6, tex='dirt', tscale=1.2, grain=.4, bump=.4)
    box(g, p, 'bal', (3.2, 70, .1), (-6, 8, .05), gravel)
    steel = mat(p + 'steel', '#7b8190', .4, .7)
    sl = mat(p + 'sleeper', '#5a3d2a', .9)
    s0 = box(g, p, 'sl', (2.4, .34, .08), (-6, -13, .13), sl)
    for i in range(1, 38):
        dup(s0, g, (-6, -13 + i * 1.7, .13))
    for xx in (-6.72, -5.28):
        box(g, p, 'rl', (.09, 70, .14), (xx, 8, .21), steel)
    # mesas: stepped cones, hazier with distance
    cols = c.get('mesa', ('#c4572f', '#d9743f', '#b04a2b', '#e08d55'))
    for i, (mx_, my_, mr, mh) in enumerate(((-17, 22, 7.5, 9), (-4, 25, 6, 6.5), (9, 23, 8.5, 11), (21, 20, 6.5, 8), (-26, 17, 5.5, 7), (-9, 15, 3.2, 3.6), (28, 13, 4, 5))):
        t = min(.55, my_ / 40)
        lay = 4
        z0 = 0
        for k in range(lay):
            hh = mh / lay
            col = _lerp(cols[(i + k) % 4], hor, t)
            cone(g, p, 'ms', mr * (1.0 - k * .045) * (1.15 if k == 0 else 1), mr * (1.0 - (k + 1) * .045) * 1.0, hh, (mx_, my_, z0 + hh / 2),
                 painted(f'{p}ms{i}_{k}', col, _lerp(col, '#ffffff', .15), .6, tex=None), seg=11)
            z0 += hh
        cy(g, p, 'mt', mr * .84, .5, (mx_, my_, z0 + .25), mat(f'{p}mt{i}', _lerp('#c99a63', hor, t), .9), seg=11)
    # distant low ridge
    for i in range(7):
        ball(g, p, 'rg', rn.uniform(5, 9), (-27 + i * 9, 27, -1), mat(f'{p}rg{i % 2}', _lerp(hor, '#b8765a', .55 + .1 * (i % 2)), .95), scl=(1.8, .7, .5), seg=12)
    # sun and halo (flat)
    disc(g, p, 'sun', 3.4, (-9, 25, 11), flat(p + 'sunc', '#fff3cf'), seg=36)
    disc(g, p, 'halo', 7.5, (-9, 25.5, 11), flat(p + 'halo', '#ffe2a8', .35), seg=36)
    # poles + wires along the road
    wood = mat(p + 'pole', '#6b4a33', .9)
    for i in range(6):
        yy = -10 + i * 7.5
        cy(g, p, 'po', .12, 7.5, (8.6, yy, 3.75), wood, seg=8)
        box(g, p, 'ca', (2.4, .14, .14), (8.6, yy, 7.0), wood)
        box(g, p, 'ca', (1.6, .14, .14), (8.6, yy, 6.0), wood)
    for dx in (-1.0, 0, 1.0):
        box(g, p, 'wi', (.03, 62, .03), (8.6 + dx, 8, 6.95 - abs(dx) * .02), mat(p + 'wire', '#15171d', .7), shadow=False)
    # cacti
    cg = mat(p + 'cact', '#4a9a5a', .8)
    for i, (cx, cyy, hh) in enumerate(((-3, 4, 3.0), (-10.5, 6, 2.4), (11, 3, 3.4), (13, -2, 2.2), (-13, -4, 3.2), (7.8, 14, 2.8), (-2.5, 16, 2.0))):
        cy(g, p, 'cc', .3, hh, (cx, cyy, hh / 2), cg, seg=10)
        ball(g, p, 'cc', .3, (cx, cyy, hh), cg, seg=10)
        for sx_, az in ((-1, .55), (1, .7)):
            cy(g, p, 'ca', .2, .8 + .2 * i % 3 * .1, (cx + sx_ * .5, cyy, hh * az + .2), cg, rot=(0, 90, 0), seg=8)
            cy(g, p, 'ca', .2, hh * .3, (cx + sx_ * .9, cyy, hh * az + .4), cg, seg=8)
    # rocks, bones of the landscape
    for i in range(12):
        rr = rn.uniform(.35, 1.2)
        rx, ry = rn.uniform(-14, 14), rn.uniform(-9, 18)
        if -7.5 < rx < 9.5:
            rx += 7 if rx > 1 else -7
        ball(g, p, 'rk', rr, (rx, ry, rr * .3), mat(f'{p}rock{i % 3}', _lerp(('#a9623f', '#b9744c', '#8e5238')[i % 3], hor, min(.4, ry / 60)), .95), scl=(1, rn.uniform(.7, 1), .6), seg=7)
    # roadside diner sign, brand on a dark plate
    cy(g, p, 'sp', .1, 4.2, (9.2, -5.0, 2.1), mat(p + 'signpole', '#2a2f3d', .5, .6), seg=8)
    plate(p + 'diner', 'DINER', .85, (9.2, -5.05, 4.2), '#a8222d', '#fff2d2', pad=(.25, .12), parent=g)
    plate(p + 'gas', 'GAS', .55, (9.2, -5.05, 3.2), '#14463f', '#ffd34d', pad=(.2, .08), parent=g)
    box(g, p, 'bp', (1.0, .04, .32), (9.2, -5.05, 2.4), mat(p + 'bpm', '#101522', .5))
    image_plane(p + 'brand', BRAND, .86, (9.2, -5.08, 2.4), g)
    # tumbleweed
    ballw = ball(g, p, 'tw', .5, (0, 0, 0), mat(p + 'tum', '#9a7340', .95), seg=8)
    ballw.parent = None
    ballw.name = p + 'tumble'
    ballw.location = (ox - 12, -3, .5)
    _mover(ballw.name, (.07, 0, 0), wrap=_hide_wrap(-12, 22), bob=(.25, .3, 0))
    haze(p + 'hz1', ox, 24, _lerp(hor, '#ffffff', .1), .55, 16, parent=g)
    haze(p + 'hz2', ox, 14, hor, .25, 9, parent=g)
    sunbeam(p + 'sb', (ox - 3, 12, 9), 4, 20, -22, '#ffe7b0', .16)
    clouds(p + 'cl', ox, 6, 9, y=(19, 26), z=(9, 20))
    return g


def rooftop_set(name, ox=0.0, **c):
    """Rooftop at dusk: concrete roof with parapet, water tank, vents, AC units, string lights, a big lit skyline behind and the city dropping away below."""
    g = group(name, None, (ox, 0, 0))
    p = name + '_'
    rn = random.Random(21)
    top, hor = c.get('sky_top', '#2c5cae'), c.get('sky_hor', '#ff9d78')
    sky(p + 'sky', ox, top, hor, mid=c.get('sky_mid', '#b36a9a'))
    cityf = mat(p + 'cityf', _lerp(hor, '#2a3050', .55), 1.0)
    cy(g, p, 'cf', R_SKY + 2, .3, (0, 0, -27), cityf, seg=48)
    roofm = painted(p + 'roof', c.get('roof', '#8a8fa0'), '#8f94a6', 3.0, tex='concrete_floor_painted', tscale=.6, grain=.15, bump=.3)
    box(g, p, 'rf', (30, 21, .6), (0, -3, -.3), roofm)
    cap = mat(p + 'cap', '#c9bfae', .7)
    box(g, p, 'pb', (30.6, .7, 1.2), (0, 7.1, .6), roofm)
    box(g, p, 'pc', (30.8, .9, .14), (0, 7.1, 1.27), cap)
    for sx_ in (-1, 1):
        box(g, p, 'ps', (.7, 21, 1.2), (sx_ * 14.9, -3, .6), roofm)
        box(g, p, 'pt', (.9, 21, .14), (sx_ * 14.9, -3, 1.27), cap)
    bw = win_mat(p + 'bwall', '#8d6d7c', '#a3818f', '#2b3350', '#ffd27a', sx=1.9, sz=2.4, frac=.3, glow=2.2)
    box(g, p, 'bd', (30, .4, 44), (0, 7.1, -22), bw)
    # water tank on legs, with a plate
    woodm = mat(p + 'wood', '#6b4a33', .9)
    for lx in (-1.1, 1.1):
        for ly in (-1.1, 1.1):
            box(g, p, 'tl', (.18, .18, 2.4), (-8.5 + lx, 3.2 + ly, 1.2), woodm)
    box(g, p, 'tb', (3.1, 3.1, .2), (-8.5, 3.2, 2.45), woodm)
    tk = mat(p + 'tank', c.get('tank', '#9a5a3a'), .8)
    cy(g, p, 'tk', 1.5, 3.0, (-8.5, 3.2, 4.0), tk, seg=20)
    cone(g, p, 'tr', 1.7, .1, 1.1, (-8.5, 3.2, 6.05), mat(p + 'tcap', '#4a3a36', .8), seg=20)
    for zz in (3.1, 4.0, 4.9):
        cy(g, p, 'tr', 1.54, .09, (-8.5, 3.2, zz), mat(p + 'band', '#2a2f3d', .5, .6), seg=20)
    plate(p + 'water', 'WATER', .5, (-8.5, 1.64, 4.0), '#f2f0e6', '#14463f', pad=(.12, .06), parent=g)
    # stair hut
    box(g, p, 'hut', (4.0, 3.2, 3.4), (8.5, 4.6, 1.7), painted(p + 'hutm', '#c9b79a', '#ddd0b6', .6, tex='concrete_wall_008', tscale=.6, grain=.3), bevel=.02)
    box(g, p, 'hr', (4.4, 3.6, .25), (8.5, 4.6, 3.5), mat(p + 'hutroof', '#4a4f5e', .8))
    box(g, p, 'hd', (1.2, .08, 2.3), (8.5, 2.97, 1.15), mat(p + 'hutdoor', '#2d5fb8', .6))
    plate(p + 'exit', 'EXIT', .3, (8.5, 2.9, 2.75), '#0e2a1c', '#4dff88', pad=(.1, .04), parent=g)
    # vents, ducts, AC
    metal = mat(p + 'metal', '#a9b0bd', .45, .7)
    for i, vx in enumerate((-12.5, -4.8, 3.2, 12.0, 5.6)):
        vy = (4.5, 5.2, 4.0, -2.0, 5.5)[i]
        cy(g, p, 'vt', .35, 1.5, (vx, vy, .75), metal, seg=12)
        cone(g, p, 'vc', .65, .2, .45, (vx, vy, 1.7), metal, seg=12)
    cy(g, p, 'du', .3, 7.0, (-3.0, 6.1, 1.0), metal, rot=(0, 90, 0), seg=12)
    for k in range(3):
        cy(g, p, 'dj', .38, .2, (-5.5 + k * 2.3, 6.1, 1.0), mat(p + 'ring', '#7b8190', .5, .6), rot=(0, 90, 0), seg=12)
    for ax, ay in ((12.2, 1.0), (12.2, -3.0), (-12.5, -1.5)):
        box(g, p, 'ac', (2.0, 1.6, 1.3), (ax, ay, .65), mat(p + 'ac', '#dfe3ea', .6), bevel=.03)
        cy(g, p, 'af', .55, .06, (ax, ay - .82, .7), mat(p + 'fan', '#3a3f4c', .5), rot=(90, 0, 0), seg=14)
    # antenna + dish
    cy(g, p, 'an', .07, 7.0, (-13, 5.5, 3.5), metal, seg=6)
    ball(g, p, 'dsh', .8, (-13, 4.9, 3.2), mat(p + 'dish', '#e8ecf2', .5), scl=(1, .25, 1), seg=14)
    ball(g, p, 'rl', .12, (-13, 5.5, 7.1), mat(p + 'redl', '#ff3030', .4, 0, 5.0), seg=8, shadow=False)
    # string lights across the back, lounge chairs, crates
    bulb = mat(p + 'bulb', '#ffe2a0', .4, 0, 5.0)
    for i in range(14):
        bx_ = -6.6 + i * 1.0
        ball(g, p, 'bl', .1, (bx_, 5.0, 3.5 - .35 * math.sin(math.pi * i / 13)), bulb, seg=8, shadow=False)
    for sx_ in (-1, 1):
        cy(g, p, 'sp', .06, 3.5, (sx_ * 7.0, 5.0, 1.75), woodm, seg=6)
    box(g, p, 'wr', (14, .03, .03), (0, 5.0, 3.65), mat(p + 'wire', '#15171d', .7), shadow=False)
    lamp(g, p, (0, 4.5, 3.2), 500, '#ffcf8a', .4)
    for i, (cx, cyy) in enumerate(((5.2, -3.0), (-5.3, -2.0))):
        box(g, p, 'cr', (1.0, 1.0, 1.0), (cx, cyy, .5), mat(p + 'crate', '#b58a55', .85), bevel=.03)
        box(g, p, 'cr', (.8, .8, .8), (cx + .1, cyy, 1.4), mat(p + 'crate2', '#d6a76a', .85), bevel=.03)
    box(g, p, 'bp', (.9, .04, .3), (3.9, -2.45, .35), mat(p + 'bpm', '#101522', .5))
    image_plane(p + 'brand', BRAND, .78, (3.9, -2.48, .35), g)
    # big billboard frame at the back right, facing the camera
    box(g, p, 'bbp', (.25, .25, 4.0), (-4.0, 7.0, 3.0), metal)
    box(g, p, 'bbp', (.25, .25, 4.0), (-1.0, 7.0, 3.0), metal)
    plate(p + 'neon', 'CITY', 1.2, (-2.5, 6.8, 5.2), '#101522', '#ff5d8f', pad=(.4, .18), parent=g)
    # the skyline: lit towers, taller than the roof, layered into haze
    skyline(p + 'sk2', ox, 25.0, _lerp(hor, '#6a5a8a', .55), 22, 14, 3, '#ffcf80', parent=g)
    haze(p + 'hz3', ox, 23.0, _lerp(hor, '#ffffff', .1), .5, 30, z0=-8, parent=g)
    skyline(p + 'sk1', ox, 18.5, _lerp(hor, '#40386a', .75), 22, 12, 8, '#ffcf80', parent=g, glow=2.0)
    haze(p + 'hz2', ox, 16.5, hor, .35, 24, z0=-10, parent=g)
    skyline(p + 'sk0', ox, 12.0, '#2e3158', 15, 10, 13, '#ffcf80', parent=g, glow=2.5)
    # a landmark tower with a spire
    lm = win_mat(p + 'lm', '#4b4f80', '#5c61a0', '#232a4e', '#ffe0a0', sx=1.2, sz=1.6, frac=.5, glow=2.8)
    box(g, p, 'lm', (4.0, 4.0, 26), (13, 15, 11), lm)
    cy(g, p, 'lsp', .12, 6, (13, 15, 27), metal, seg=6)
    ball(g, p, 'lr', .2, (13, 15, 30.1), mat(p + 'redl', '#ff3030', .4, 0, 5.0), seg=8, shadow=False)
    sunbeam(p + 'sb', (ox - 5, 5, 8), 3.0, 18, 25, '#ffb98a', .18)
    clouds(p + 'cl', ox, 7, 6, hex='#ffd9c8', outline='#9a6fb0', z=(10, 22))
    return g


def sea_set(name, ox=0.0, **c):
    """Ship deck: planked deck with rails, two masts with sails, a cabin, cargo, a ship's wheel, and open sea to the horizon with distant islands. Camera -Y looks over the back rail."""
    g = group(name, None, (ox, 0, 0))
    p = name + '_'
    rn = random.Random(31)
    top, hor = c.get('sky_top', '#2b7bd0'), c.get('sky_hor', '#ffd8ae')
    sky(p + 'sky', ox, top, hor)
    seam = painted(p + 'sea', c.get('sea', '#1b6aa6'), '#3fa6cf', .12, tex=None)
    fog(seam, _lerp(hor, '#7fc3dc', .4), 16, 31)
    cy(g, p, 'sea', R_SKY + 2, .3, (0, 0, -3.15), seam, seg=72)
    deck = plank_mat(p + 'deck', c.get('deck', '#a56b3c'), '#c88a52')
    box(g, p, 'dk', (30, 16, .3), (0, -2.5, -.15), deck)
    hull = painted(p + 'hull', c.get('hull', '#3a2a3c'), '#5a3b52', .5, tex='dirt', tscale=.8, grain=.3, bump=.2)
    box(g, p, 'hl', (30.6, .6, 3.4), (0, 6.2, -1.6), hull)
    box(g, p, 'hs', (.6, 16, 3.4), (-14.9, -2.5, -1.6), hull)
    box(g, p, 'hs', (.6, 16, 3.4), (14.9, -2.5, -1.6), hull)
    box(g, p, 'hb', (30.6, 16, .4), (0, -2.5, -3.0), hull)
    stripe = mat(p + 'stripe', c.get('stripe', '#d9433a'), .7)
    box(g, p, 'st', (30.8, .62, .35), (0, 6.2, -.5), stripe)
    white = mat(p + 'white', '#f4efe2', .6)
    # rails: back and ends
    for k in range(22):
        box(g, p, 'rp', (.1, .1, 1.05), (-14.7 + k * 1.4, 6.0, .52), white)
    for zz in (.55, 1.05):
        box(g, p, 'rr', (30, .08, .08), (0, 6.0, zz), white)
    for sx_ in (-1, 1):
        for k in range(1, 10):
            box(g, p, 'rp', (.1, .1, 1.05), (sx_ * 14.7, 6.0 - k * 1.4, .52), white)
        for zz in (.55, 1.05):
            box(g, p, 'rr', (.08, 14, .08), (sx_ * 14.7, -.6, zz), white)
    # masts and sails
    wood = mat(p + 'mast', '#6b4a33', .85)
    sail = painted(p + 'sail', c.get('sail', '#efe3c8'), '#fbf3df', .5, tex='painted_plaster_wall', tscale=.6, grain=.25, bump=.1)
    for mx_, mh, sw in ((-9.5, 21, 6.6), (10.0, 17, 5.4)):
        cy(g, p, 'mt', .3, mh, (mx_, 2.0, mh / 2), wood, seg=12)
        for yz, ww in ((mh * .78, sw * .85), (mh * .45, sw)):
            cy(g, p, 'yd', .1, ww + 1.0, (mx_, 1.7, yz + 2.2), wood, rot=(0, 90, 0), seg=8)
            box(g, p, 'sl', (ww, .1, 5.0), (mx_, 1.74, yz), sail)
        ball(g, p, 'mb', .35, (mx_, 2.0, mh + .2), mat(p + 'mball', '#c8a24a', .4, .8), seg=10)
        for sx_, ex in ((-1, 13), (1, 13)):
            rope = box(g, p, 'rg', (.05, .05, 1), (mx_ + sx_ * 3.5, 4.0, mh * .5), mat(p + 'rope', '#3a2f26', .9), shadow=False)
            rope.scale = (1, 1, mh * .5)
            rope.rotation_euler = (0, math.radians(sx_ * 24), 0)
        flag = quad(g, f'{p}flag{mx_}', 1.8, 1.0, (ox + mx_ + .95, 1.9, mh + .9), flat(p + 'flagm', '#d9433a'))
        flag.parent = None
        _mover(flag.name, (0, 0, 0), bob=(.08, .35, mx_))
    ring(g, p, 'nest', .9, .08, (-9.5, 2.0, 17.5), wood, rot=(0, 0, 0))
    # cabin
    cab = painted(p + 'cab', '#e8d9c0', '#f5ead4', .5, tex='painted_plaster_wall', tscale=.6, grain=.3)
    box(g, p, 'cab', (5.5, 3.6, 3.2), (11.5, 3.6, 1.6), cab, bevel=.03)
    box(g, p, 'cr', (6.0, 4.0, .3), (11.5, 3.6, 3.4), mat(p + 'cabroof', '#a8222d', .8))
    for k in range(3):
        cy(g, p, 'po', .3, .06, (9.9 + k * 1.6, 1.78, 1.9), mat(p + 'porth', '#c8a24a', .4, .8), rot=(90, 0, 0), seg=16)
        cy(g, p, 'pg', .24, .08, (9.9 + k * 1.6, 1.74, 1.9), mat(p + 'portg', '#ffe2a0', .4, 0, 2.5), rot=(90, 0, 0), seg=16)
    box(g, p, 'cd', (1.0, .08, 2.1), (13.3, 1.78, 1.05), mat(p + 'cabdoor', '#2d5fb8', .6))
    plate(p + 'cabsign', 'CAPTAIN', .4, (11.5, 1.72, 3.0), '#101522', '#ffd34d', pad=(.15, .06), parent=g)
    # cargo, barrels, rope coil, lifebuoy, ship's wheel
    for i, (cx, cyy, s) in enumerate(((-10.5, 3.5, 1.4), (-9.0, 3.8, 1.1), (-9.8, 3.5, 1.0), (4.5, 4.4, 1.2), (-1.2, 4.8, 1.0))):
        zz = s / 2 if i != 2 else 1.4 + s / 2
        box(g, p, 'cg', (s, s, s), (cx, cyy, zz), mat(f'{p}cg{i % 3}', ('#b8864f', '#8a5a36', '#c9a066')[i % 3], .85), bevel=.03)
        box(g, p, 'cs', (s * 1.02, s * .1, s * .15), (cx, cyy - s * .5, zz), mat(p + 'cstrap', '#3a2f26', .8))
    for i, (cx, cyy) in enumerate(((1.8, 4.9), (2.7, 5.1), (-12.6, 1.5))):
        cy(g, p, 'br', .38, .95, (cx, cyy, .48), mat(p + 'barrel', '#7a4a2a', .8), seg=14)
        for zz in (.2, .75):
            cy(g, p, 'bb', .4, .07, (cx, cyy, zz), mat(p + 'hoop', '#2a2f3d', .5, .7), seg=14)
    cy(g, p, 'cl', .6, .25, (-1.0, 1.2, .13), mat(p + 'coil', '#c8ac7a', .9), seg=18)
    ring(g, p, 'lb', .45, .14, (2.0, 5.88, .75), mat(p + 'lifebuoy', '#e8453c', .6), rot=(90, 0, 0))
    plate(p + 'ship', 'SS HARBOR', .35, (-2.0, 5.88, .9), '#f2f0e6', '#14463f', pad=(.12, .05), parent=g)
    cy(g, p, 'wp', .1, 1.6, (4.5, 1.0, .8), wood, seg=8)
    ring(g, p, 'wh', .62, .06, (4.5, .9, 1.6), mat(p + 'wheel', '#8a5a36', .6), rot=(90, 0, 0))
    for a in range(4):
        cy(g, p, 'sk', .035, 1.4, (4.5, .9, 1.6), mat(p + 'wheel', '#8a5a36', .6), rot=(90, 0, a * 45), seg=6)
    box(g, p, 'bp', (.9, .04, .3), (-6.5, 5.9, .6), mat(p + 'bpm', '#101522', .5))
    image_plane(p + 'brand', BRAND, .78, (-6.5, 5.87, .6), g)
    cy(g, p, 'lt', .17, .35, (-3.0, 1.8, 3.2), mat(p + 'lantern', '#ffd88a', .3, 0, 3.0), seg=10, shadow=False)
    lamp(g, p, (-3.0, 1.0, 3.2), 300, '#ffcf8a', .3)
    # open sea: foam streaks that drift, distant islands and a far ship
    foam = flat(p + 'foam', '#e8f6fb', .8)
    for i in range(14):
        fx, fy = rn.uniform(-22, 22), rn.uniform(10, 28)
        fo = disc(g, p, 'fo', 1.0, (0, 0, 0), foam, scl=(rn.uniform(.8, 2.4), 1, .06), seg=12)
        fo.parent = None
        fo.name = f'{p}foam{i}'
        fo.rotation_euler = (0, 0, 0)   # lie flat on the sea
        fo.location = (ox + fx, fy, -3.1)
        fo.scale = (rn.uniform(.8, 2.2), rn.uniform(.08, .2), 1)
        _mover(fo.name, (.01, 0, 0), wrap=_hide_wrap(fx, 24))
    for i, (ix, iy, isz) in enumerate(((-18, 28, 3.2), (-6, 28.5, 1.6), (20, 26, 2.6))):
        ball(g, p, 'is', isz, (ix, iy, -isz * .45), flat(f'{p}isl{i}', _lerp(hor, '#3f6a8a', .6)), scl=(2.2, .6, .6), seg=12)
    hs = flat(p + 'farship', _lerp(hor, '#4b5f86', .6))
    box(g, p, 'fs', (2.2, .1, .6), (11, 27, -2.7), hs, shadow=False)
    box(g, p, 'fm', (.06, .06, 2.4), (11, 27, -1.4), hs, shadow=False)
    box(g, p, 'fsl', (1.1, .04, 1.8), (11.2, 27, -1.2), flat(p + 'farsail', '#f7ecd8'), shadow=False)
    haze(p + 'hz1', ox, 28, '#ffe6c8', .6, 8, z0=-4, parent=g)
    haze(p + 'hz2', ox, 20, hor, .22, 6, z0=-4, parent=g)
    sunbeam(p + 'sb', (ox - 6, 10, 8), 4, 22, 28, '#fff0c0', .18)
    clouds(p + 'cl', ox, 8, 2, y=(17, 26), z=(5, 19), scale=(1.8, 3.2))
    return g


# ----------------------------------------------------------------------------- INDOOR SETS (tech and finance)
def _shell(g, p, w, y0, y1, h, floor_m, wall_m, ceil_m):
    """Closed room: floor, back wall at y1, side walls, a wall behind the camera and a ceiling. Walls and ceiling cast no shadow so the sun still lights the room."""
    d = y1 - y0
    cyy = (y0 + y1) / 2
    box(g, p, 'fl', (w + 2, d + 2, .3), (0, cyy, -.15), floor_m)
    box(g, p, 'bk', (w + 2, .4, h), (0, y1 + .2, h / 2), wall_m, shadow=False)
    for sx_ in (-1, 1):
        box(g, p, 'sw', (.4, d + 2, h), (sx_ * (w / 2 + .2), cyy, h / 2), wall_m, shadow=False)
    box(g, p, 'fw', (w + 2, .4, h), (0, y0 - .2, h / 2), wall_m, shadow=False)
    box(g, p, 'ce', (w + 2, d + 2, .4), (0, cyy, h + .2), ceil_m, shadow=False)


def _clock(g, p, loc, r=.8):
    disc(g, p, 'ck', r, loc, flat(p + 'ckf', '#f6efdc'))
    ring(g, p, 'cr', r, .07, (loc[0], loc[1] - .02, loc[2]), mat(p + 'gold', '#c8a24a', .35, .9), rot=(90, 0, 0))
    box(g, p, 'ch', (.07, .04, r * .55), (loc[0], loc[1] - .05, loc[2] + r * .25), flat(p + 'hand', '#2a2430'), shadow=False)
    box(g, p, 'ch', (r * .7, .04, .07), (loc[0] + r * .3, loc[1] - .05, loc[2]), flat(p + 'hand', '#2a2430'), shadow=False)


def bank_set(name, ox=0.0, **c):
    """Marble bank hall: chequered floor, red carpet, columns, teller counters with glass, a big round vault door with a BANK sign, chandeliers, tall windows."""
    g = group(name, None, (ox, 0, 0))
    p = name + '_'
    gold = mat(p + 'gold', '#c8a24a', .35, .9)
    marble = checker_mat(p + 'floor', c.get('floor1', '#e0d3b6'), c.get('floor2', '#a08f70'), 1.6, .22)
    wall = painted(p + 'wall', c.get('wall', '#efe0bd'), '#f8edd0', .4, tex='painted_plaster_wall', tscale=.5, grain=.3, grad=(2, 10, .8))
    ceil = mat(p + 'ceil', '#d9c9a4', .9)
    _shell(g, p, 30, -14, 12, 11, marble, wall, ceil)
    green = painted(p + 'green', c.get('wain', '#1d5a48'), '#277560', .5, tex='floor_tiles_06', tscale=.8, grain=.4, bump=.4)
    box(g, p, 'wb', (30, .2, 2.8), (0, 11.85, 1.4), green, shadow=False)
    for sx_ in (-1, 1):
        box(g, p, 'wb', (.2, 26, 2.8), (sx_ * 14.85, -1, 1.4), green, shadow=False)
        box(g, p, 'wt', (.26, 26, .12), (sx_ * 14.82, -1, 2.86), gold, shadow=False)
    box(g, p, 'wt', (30, .26, .12), (0, 11.82, 2.86), gold, shadow=False)
    # carpet
    box(g, p, 'rug', (3.4, 25, .03), (0, -1, .015), mat(p + 'rug', c.get('rug', '#8f1f2e'), .9), shadow=False)
    for sx_ in (-1, 1):
        box(g, p, 'rg', (.12, 25, .035), (sx_ * 1.55, -1, .02), gold, shadow=False)
    # coffered ceiling
    beam = mat(p + 'beam', '#d9c8a2', .7)
    for k in range(-2, 3):
        box(g, p, 'cb', (31, .55, .5), (0, k * 5.0 - 1, 10.7), beam, shadow=False)
        box(g, p, 'cb', (.55, 27, .5), (k * 6.0, -1, 10.7), beam, shadow=False)
    # columns
    stone = painted(p + 'stone', '#ece3d0', '#faf4e4', .5, tex='concrete_wall_008', tscale=.5, grain=.25, bump=.1)
    for cx in (-9.5, 9.5):
        for cyy in (-6.5, 2.0):
            cy(g, p, 'co', .62, 10.2, (cx, cyy, 5.1), stone, seg=18)
            box(g, p, 'cb', (1.6, 1.6, .4), (cx, cyy, .2), stone)
            box(g, p, 'cc', (1.8, 1.8, .45), (cx, cyy, 10.3), gold)
    # windows and light shafts
    sk = flat(p + 'win', '#cfe9ff')
    for sx_ in (-1, 1):
        for wy in (-6.0, 0.0, 6.0):
            box(g, p, 'wn', (.12, 2.6, 6.2), (sx_ * 14.78, wy, 6.0), sk, shadow=False)
            box(g, p, 'wf', (.2, .16, 6.4), (sx_ * 14.7, wy, 6.0), gold, shadow=False)
            box(g, p, 'wf', (.2, 2.8, .16), (sx_ * 14.7, wy, 6.0), gold, shadow=False)
    # vault door
    steel = painted(p + 'steel', '#8b95a6', '#b5bdca', 1.5, tex='metal_plate', tscale=.8, grain=.3)
    box(g, p, 'vf', (7.6, .8, 7.8), (0, 11.5, 3.9), mat(p + 'vframe', '#3a404e', .4, .7))
    cy(g, p, 'vd', 2.8, .6, (0, 10.95, 3.9), steel, rot=(90, 0, 0), seg=40)
    ring(g, p, 'v1', 2.8, .14, (0, 10.6, 3.9), gold, rot=(90, 0, 0), seg=40)
    ring(g, p, 'v2', 1.9, .08, (0, 10.58, 3.9), gold, rot=(90, 0, 0), seg=32)
    for a in range(12):
        t = a * math.tau / 12
        ball(g, p, 'vb', .13, (2.35 * math.cos(t), 10.55, 3.9 + 2.35 * math.sin(t)), gold, seg=8)
    ring(g, p, 'vw', .95, .09, (0, 10.4, 3.9), gold, rot=(90, 0, 0))
    for a in (0, 60, 120):
        cy(g, p, 'vs', .06, 1.9, (0, 10.4, 3.9), gold, rot=(0, a, 0), seg=8)
    ball(g, p, 'vh', .25, (0, 10.35, 3.9), gold, seg=10)
    box(g, p, 'vh', (.9, .5, 1.6), (-3.55, 10.95, 3.9), mat(p + 'hinge', '#3a404e', .4, .7))
    plate(p + 'vault', 'VAULT', 1.0, (0, 11.2, 8.3), '#14131a', '#e8c35a', pad=(.4, .15), parent=g)
    plate(p + 'bank', 'BANK', 1.5, (0, 11.8, 9.7), '#10261f', '#e8c35a', pad=(.5, .18), parent=g)
    _clock(g, p, (-7.5, 11.78, 6.3))
    _clock(g, p, (7.5, 11.78, 6.3))
    # teller counters with glass
    wood = painted(p + 'wood', '#5b3a26', '#744a30', 1.4, tex='dirt', tscale=1.0, grain=.3, bump=.2)
    top = mat(p + 'ctop', '#e9dfca', .25)
    glassm = glass(p + 'glass', '#a8d8ff', .25)
    for k, sx_ in enumerate((-1, 1)):
        cx = sx_ * 8.2
        box(g, p, 'ct', (7.8, 1.3, 1.1), (cx, 6, .55), wood, bevel=.02)
        box(g, p, 'cp', (8.1, 1.6, .1), (cx, 6, 1.15), top)
        box(g, p, 'gl', (7.8, .06, 1.7), (cx, 6.45, 2.0), glassm, shadow=False)
        for j in range(5):
            box(g, p, 'gp', (.08, .1, 1.8), (cx - 3.8 + j * 1.9, 6.45, 2.05), gold)
        for j in range(2):
            box(g, p, 'mn', (.55, .06, .38), (cx - 1.5 + j * 3.0, 5.7, 1.5), mat(p + 'mon', '#6fe3b4', .3, 0, 2.2), rot=(0, 0, 0))
        plate(f'{p}tl{k}', f'TELLER {k + 1}', .45, (cx, 5.5, 4.9), '#10261f', '#e8c35a', pad=(.2, .08), parent=g)
        for j in (-1, 1):
            cy(g, p, 'rd', .02, 6.4, (cx + j * .8, 5.5, 8.0), gold, seg=6)
    box(g, p, 'bp', (1.0, .04, .34), (-8.2, 5.33, .55), mat(p + 'bpm', '#101522', .5))
    image_plane(p + 'brand', BRAND, .88, (-8.2, 5.30, .55), g)
    # queue stanchions
    for j in range(5):
        cy(g, p, 'sp', .05, 1.0, (5.8, -5.5 + j * 1.6, .5), gold, seg=8)
        ball(g, p, 'sb', .08, (5.8, -5.5 + j * 1.6, 1.02), gold, seg=8)
        if j:
            box(g, p, 'sr', (.03, 1.6, .05), (5.8, -5.5 + j * 1.6 - .8, .9), mat(p + 'belt', '#8f1f2e', .7), shadow=False)
    # chandeliers
    for k, cyy in enumerate((-4.5, 4.0)):
        cy(g, p, 'cn', .03, 3.2, (0, cyy, 9.2), gold, seg=6, shadow=False)
        ring(g, p, 'cr', 1.0, .07, (0, cyy, 7.5), gold, rot=(0, 0, 0))
        ball(g, p, 'cl', .38, (0, cyy, 7.5), mat(p + 'bulb', '#fff0c0', .3, 0, 5.0), seg=10, shadow=False)
        for a in range(6):
            t = a * math.tau / 6
            ball(g, p, 'cb', .13, (math.cos(t), cyy + math.sin(t), 7.7), mat(p + 'bulb', '#fff0c0', .3, 0, 5.0), seg=8, shadow=False)
        lamp(g, p, (0, cyy, 7.2), 500, '#ffd9a0', .6)
    lamp(g, p, (-6, -6, 6), 300, '#ffd9a0', .6)
    lamp(g, p, (6, -6, 6), 300, '#ffd9a0', .6)
    # plants
    for px_, py_ in ((-13, -4), (13, -4), (-4.8, 10.6), (4.8, 10.6)):
        cy(g, p, 'pt', .5, .8, (px_, py_, .4), mat(p + 'pot', '#9a5a3a', .8), seg=12)
        ball(g, p, 'pl', .85, (px_, py_, 1.5), mat(p + 'leaf', '#3f8f54', .9), scl=(1, 1, 1.2), seg=10)
    sunbeam(p + 'sb1', (ox - 5, 4, 5), 2.6, 12, 22, '#fff0c8', .2)
    sunbeam(p + 'sb2', (ox + 6, 6, 5), 2.2, 12, -24, '#fff0c8', .16)
    return g


def trading_set(name, ox=0.0, **c):
    """Trading floor: dark carpet, rows of desks with three screens each, a huge wall board with a scrolling ticker, side wall screens, hanging displays, cold strip lights."""
    g = group(name, None, (ox, 0, 0))
    p = name + '_'
    carpet = mat(p + 'carpet', c.get('floor', '#2a3550'), .9)
    wall = painted(p + 'wall', c.get('wall', '#1a2744'), '#25365e', .4, tex='painted_plaster_wall', tscale=.5, grain=.25, grad=(0, 10, .65))
    ceil = mat(p + 'ceil', '#161c2c', .9)
    _shell(g, p, 34, -14, 15, 12, carpet, wall, ceil)
    for k in range(-2, 3):
        box(g, p, 'ls', (.5, 30, .06), (k * 6.5, 0, 11.75), mat(p + 'strip', '#dff1ff', .3, 0, 4.0), shadow=False)
        box(g, p, 'tr', (.4, 30, .4), (k * 6.5 + 3.25, 0, 11.7), mat(p + 'truss', '#2b3552', .5, .5), shadow=False)
    amber = mat(p + 'amber', '#ffb040', .4, 0, 3.0)
    # wall board
    box(g, p, 'bf', (23, .5, 7.6), (0, 14.7, 6.6), mat(p + 'frame', '#0b1018', .5, .6))
    box(g, p, 'bs', (22, .1, 6.8), (0, 14.4, 6.6), screen_mat(p + 'wall_scr', 22, 6.8, 48, '#38e08a', '#ff4d5e', '#06101c', 1.4, 3.0))
    plate(p + 'title', 'MARKETS', 1.0, (0, 14.2, 10.8), '#07111c', '#ffb040', pad=(.4, .15), parent=g)
    box(g, p, 'tb', (22, .1, 1.0), (0, 14.3, 9.7), mat(p + 'tband', '#050a12', .5))
    items = (('ACME +2.1%', '#38e08a'), ('NOVA -0.8%', '#ff6b78'), ('BOLT +0.4%', '#38e08a'), ('ORCA +3.3%', '#38e08a'), ('PEAK -1.2%', '#ff6b78'), ('HALO +0.9%', '#38e08a'), ('DELTA -0.3%', '#ff6b78'))
    for i, (tx, fg) in enumerate(items):
        b0 = -9.0 + i * 3.0
        o = plate(f'{p}tk{i}', tx, .46, (ox + b0, 14.2, 9.7), '#050a12', fg, pad=(.12, .05), parent=None)
        _mover(o.name, (-.05, 0, 0), wrap=_hide_wrap(b0, 16))
    for sx_ in (-1, 1):
        box(g, p, 'bcov', (7, .3, 1.5), (sx_ * 14.1, 13.9, 9.7), wall)   # hides the ticker beyond the board
    # side wall screens
    for sx_ in (-1, 1):
        box(g, p, 'sf', (.4, 11, 5.6), (sx_ * 16.7, 4, 6.0), mat(p + 'frame', '#0b1018', .5, .6))
        box(g, p, 'ss', (10, .1, 5.0), (sx_ * 16.45, 4, 6.0), screen_mat(p + 'side_scr', 10, 5.0, 22, '#38e08a', '#ff4d5e', '#06101c', 1.3, 8.0), rot=(0, 0, 90 * -sx_))
    # desks, monitors, chairs
    desk = painted(p + 'desk', '#3a4668', '#4a5a82', 1.2, tex='metal_plate', tscale=1.0, grain=.2)
    dtop = mat(p + 'dtop', '#d7dbe6', .4)
    monm = [screen_mat(f'{p}mon{k}', .9, .55, 9, '#38e08a', '#ff4d5e', '#06101c', 2.0, k * 20.0) for k in range(3)]
    mon0 = [box(g, p, 'mon', (.9, .05, .55), (-50 + k, 0, 0), monm[k], shadow=False) for k in range(3)]
    kb0 = box(g, p, 'kb', (.9, .3, .03), (-50, 0, 0), mat(p + 'kb', '#16192a', .5))
    seat = mat(p + 'seat', '#cf4a4a', .8)
    ch0 = cy(g, p, 'chs', .4, .09, (-50, 0, 0), seat, seg=12)
    cb0 = box(g, p, 'chb', (.7, .09, .75), (-50, 0, 0), seat)
    cp0 = cy(g, p, 'chp', .04, .5, (-50, 0, 0), mat(p + 'chp', '#2a2f3d', .5, .6), seg=6)
    n = 0
    for row, ry in enumerate((4.6, 8.2, 11.8)):
        for dx in (-11, -3.7, 3.7, 11):
            box(g, p, 'dk', (3.5, 1.3, .75), (dx, ry, .38), desk)
            box(g, p, 'dt', (3.6, 1.4, .06), (dx, ry, .78), dtop)
            for k in range(3):
                dup(mon0[k], g, (dx - 1.05 + k * 1.05, ry + .45, 1.35))
            dup(kb0, g, (dx, ry - .15, .83))
            dup(ch0, g, (dx, ry - 1.35, .55))
            dup(cb0, g, (dx, ry - 1.78, .98))
            dup(cp0, g, (dx, ry - 1.35, .27))
            n += 1
    for o in mon0 + [kb0, ch0, cb0, cp0]:
        o.location = (0, 0, -60)
    # hanging displays
    for sx_ in (-1, 1):
        for rr in (.9, -.9):
            cy(g, p, 'hr', .03, 5.0, (sx_ * 9 + rr, 8.0, 9.0), mat(p + 'rod', '#2a2f3d', .5, .6), seg=6, shadow=False)
        box(g, p, 'hd', (3.8, .25, 2.0), (sx_ * 9, 8.0, 6.3), mat(p + 'frame', '#0b1018', .5, .6))
        box(g, p, 'hs', (3.5, .05, 1.7), (sx_ * 9, 7.86, 6.3), screen_mat(p + 'hang_scr', 3.5, 1.7, 14, '#38e08a', '#ff4d5e', '#06101c', 1.6, 40.0 + sx_), shadow=False)
        plate(f'{p}idx{sx_}', 'INDEX +1.2%' if sx_ > 0 else 'INDEX -0.6%', .38, (sx_ * 9, 7.7, 5.0), '#07111c', '#38e08a' if sx_ > 0 else '#ff6b78', pad=(.15, .06), parent=g)
    box(g, p, 'bp', (1.0, .04, .34), (-3.7, 3.93, .45), mat(p + 'bpm', '#101522', .5))
    image_plane(p + 'brand', BRAND, .88, (-3.7, 3.90, .45), g)
    # paper bins, water cooler
    for px_, py_ in ((-7, 1.8), (7.5, 2.2)):
        cy(g, p, 'bin', .3, .7, (px_, py_, .35), mat(p + 'bin', '#3a4668', .6), seg=10)
    cy(g, p, 'wc', .25, 1.1, (14.5, 1.0, .55), mat(p + 'cool', '#d7dbe6', .5), seg=10)
    cy(g, p, 'wb', .22, .45, (14.5, 1.0, 1.35), glass(p + 'wat', '#8fd0ff', .5), seg=10)
    lamp(g, p, (0, -5, 9), 1400, '#ffcf8a', .6)
    lamp(g, p, (0, 8, 10), 1800, '#9fc4ff', .8)
    lamp(g, p, (0, 12, 8), 900, '#ffb040', .8)
    return g


def datacenter_set(name, ox=0.0, **c):
    """Data centre: bright raised floor, two rows of server racks with LEDs down a long cold aisle, a cross aisle, cable trays and cold strip lights overhead, a far door."""
    g = group(name, None, (ox, 0, 0))
    p = name + '_'
    floor = checker_mat(p + 'floor', c.get('floor1', '#cfd6e2'), c.get('floor2', '#a9b3c4'), .6, .3)
    wall = mat(p + 'wall', c.get('wall', '#c3cad8'), .9)
    ceil = mat(p + 'ceil', '#9aa3b4', .9)
    _shell(g, p, 34, -14, 25, 9, floor, wall, ceil)
    cold = mat(p + 'cold', '#d6efff', .3, 0, 5.0)
    tray = mat(p + 'tray', '#6b7384', .5, .7)
    cabl = [mat(f'{p}cab{k}', h_, .5) for k, h_ in enumerate(('#2d7bff', '#ffb020', '#ff4d6a', '#2fd45a'))]
    for xx in (-3.5, 0, 3.5):
        box(g, p, 'ls', (.35, 38, .06), (xx, 5.5, 8.85), cold, shadow=False)
    for xx in (-6.2, 6.2):
        box(g, p, 'tr', (.9, 38, .12), (xx, 5.5, 7.2), tray)
        for k in range(4):
            box(g, p, 'cb', (.12, 38, .1), (xx - .3 + k * .2, 5.5, 7.32), cabl[k], shadow=False)
        for yy in range(-12, 24, 5):
            cy(g, p, 'hg', .03, 1.7, (xx - .4, yy, 8.0), tray, seg=6, shadow=False)
            cy(g, p, 'hg', .03, 1.7, (xx + .4, yy, 8.0), tray, seg=6, shadow=False)
    # racks (chunks of four), two rows, with a cross aisle at y 7..12
    led = led_mat(p + 'led', c.get('rack', '#1b2433'))
    for sx_ in (-1, 1):
        for y0, y1 in ((-12.6, 6.8), (12.4, 23.8)):
            n = int((y1 - y0) / 2.6)
            for k in range(n):
                box(g, p, 'rk', (1.05, 2.6, 2.4), (sx_ * 6.2, y0 + k * 2.6 + 1.3, 1.2), led)
        for yy in (-3, 3.5, 15.5):
            plate(f'{p}row{sx_}_{int(yy)}', 'ROW ' + ('A' if sx_ < 0 else 'B') + str(int(abs(yy)) % 4 + 1), .5, (sx_ * 6.2, yy, 5.6), '#101a2e', '#6ad1ff', pad=(.2, .08), parent=g)
            for rr in (-.7, .7):
                cy(g, p, 'rd', .02, 3.2, (sx_ * 6.2 + rr, yy, 7.2), tray, seg=6, shadow=False)
    # floor guide lines, vent tiles
    gl = mat(p + 'guide', '#37c8ff', .4, 0, 1.5)
    for xx in (-3.1, 3.1):
        box(g, p, 'gd', (.1, 38, .02), (xx, 5.5, .01), gl, shadow=False)
    v0 = box(g, p, 'vt', (.58, .58, .02), (-60, 0, 0), mat(p + 'vent', '#6b7384', .5), shadow=False)
    for k in range(10):
        dup(v0, g, (-1.8 + 1.2 * (k % 4), -2.0 + 1.2 * (k // 4), .015))
    v0.location = (0, 0, -60)
    # far end: door and AC units
    box(g, p, 'dr', (3.4, .2, 3.6), (0, 24.8, 1.8), mat(p + 'door', '#2a3550', .4, .5))
    box(g, p, 'dg', (2.4, .1, 2.0), (0, 24.65, 2.2), mat(p + 'doorgl', '#bfe8ff', .4, 0, 2.0))
    plate(p + 'exit', 'EXIT', .36, (0, 24.6, 4.0), '#0e2a1c', '#4dff88', pad=(.12, .05), parent=g)
    for sx_ in (-1, 1):
        box(g, p, 'ac', (4.0, 1.4, 2.6), (sx_ * 11, 24.1, 1.3), mat(p + 'acu', '#e8ecf2', .5), bevel=.03)
        for k in range(3):
            cy(g, p, 'af', .55, .06, (sx_ * 11 + (k - 1) * 1.2, 23.4, 1.3), mat(p + 'fan', '#3a3f4c', .5), rot=(90, 0, 0), seg=14)
    # crash cart with a screen in the aisle (brand on its front)
    box(g, p, 'cart', (1.5, .9, 1.0), (-2.6, 3.2, .5), mat(p + 'cart', '#3a4668', .5, .5), bevel=.02)
    box(g, p, 'cm', (.9, .06, .55), (-2.6, 3.3, 1.45), screen_mat(p + 'cart_scr', .9, .55, 8, '#38e08a', '#ff4d5e', '#06101c', 2.0, 5.0), shadow=False)
    box(g, p, 'bp', (.9, .04, .3), (-2.6, 2.73, .55), mat(p + 'bpm', '#101522', .5))
    image_plane(p + 'brand', BRAND, .78, (-2.6, 2.70, .55), g)
    for k in range(6):
        box(g, p, 'dn', (.08, .08, 4.6), (-5.4, -9.5 + k * 3.1, 4.9), cabl[k % 4], shadow=False)
    lamp(g, p, (0, 0, 7.5), 1200, '#bfe3ff', 1.0)
    lamp(g, p, (0, 12, 7.5), 1200, '#bfe3ff', 1.0)
    lamp(g, p, (0, -5, 4), 600, '#ffd9a0', 1.0)
    return g


def factory_set(name, ox=0.0, **c):
    """Factory floor: hazard-striped walkway, a long conveyor with moving cartons, robot arm, press, silos, pipes, catwalk, hanging lamps, a loading door."""
    g = group(name, None, (ox, 0, 0))
    p = name + '_'
    conc = painted(p + 'conc', c.get('floor', '#8a8f9a'), '#a6abb5', .4, tex='concrete_floor_painted', tscale=.6, grain=.35, bump=.4)
    wall = painted(p + 'wall', c.get('wall', '#4f6f8a'), '#6a8aa4', .45, tex='metal_plate', tscale=.5, grain=.3, bump=.3, grad=(0, 11, .7))
    ceil = painted(p + 'ceil', '#2c3444', '#3b4558', .5, tex='metal_plate', tscale=.6, grain=.3)
    _shell(g, p, 34, -14, 16, 12, conc, wall, ceil)
    haz = stripe_mat(p + 'haz', '#f2c230', '#1a1a1e', .7, .5)
    for yy in (-3.0, 2.2):
        box(g, p, 'hz', (34, .5, .02), (0, yy, .01), haz, shadow=False)
    # conveyor
    frame = mat(p + 'frame', '#3a4a64', .5, .6)
    belt = mat(p + 'belt', '#1d2028', .9)
    box(g, p, 'bt', (34, 1.5, .18), (0, 5.5, .95), belt)
    for yy in (4.7, 6.3):
        box(g, p, 'cr', (34, .12, .3), (0, yy, .95), frame)
    for k in range(-8, 9):
        for yy in (4.75, 6.25):
            box(g, p, 'cl', (.12, .12, .9), (k * 2.0, yy, .45), frame)
    r0 = cy(g, p, 'ro', .1, 1.5, (-60, 0, 0), mat(p + 'roller', '#8b92a0', .4, .8), rot=(90, 0, 0), seg=10)
    for k in range(-16, 17):
        dup(r0, g, (k * 1.0, 5.5, 1.08))
    r0.location = (0, 0, -60)
    cart = painted(p + 'carton', '#c49a5e', '#dcb676', .6, tex='dirt', tscale=1.0, grain=.3, bump=.2)
    tape = mat(p + 'tape', '#3a2f26', .8)
    for i in range(7):
        b0 = -10.5 + i * 3.1
        sz = (.8 + .15 * (i % 3), .8, .7 + .1 * (i % 2))
        o = box(g, p, 'pk', sz, (0, 0, 0), cart)
        o.parent = None
        o.name = f'{p}pkg{i}'
        o.location = (ox + b0, 5.5, 1.04 + sz[2] / 2)
        _mover(o.name, (.03, 0, 0), wrap=_hide_wrap(b0, 16))
    # robot arm
    org = mat(p + 'orange', '#f26a21', .5, .3)
    cy(g, p, 'rb', 1.0, .5, (-6.5, 8.5, .25), mat(p + 'rbase', '#2a2f3d', .5, .6), seg=20)
    cy(g, p, 'rb', .55, 1.8, (-6.5, 8.5, 1.4), org, seg=16)
    ball(g, p, 'rj', .65, (-6.5, 8.5, 2.5), org, seg=14)
    box(g, p, 'ra', (.5, .5, 3.8), (-5.8, 8.5, 4.2), org, rot=(0, -28, 0), bevel=.05)
    ball(g, p, 'rj', .45, (-4.8, 8.5, 6.0), org, seg=12)
    box(g, p, 'ra', (.4, .4, 3.2), (-3.4, 8.5, 5.0), org, rot=(0, 62, 0), bevel=.05)
    box(g, p, 'rg', (.2, 1.0, .25), (-1.9, 8.5, 4.3), mat(p + 'grip', '#2a2f3d', .5, .6))
    # press with a moving piston
    box(g, p, 'pf', (.7, 2.6, 5.6), (4.2, 9.0, 2.8), frame)
    box(g, p, 'pf', (.7, 2.6, 5.6), (8.0, 9.0, 2.8), frame)
    box(g, p, 'pt', (4.6, 2.8, .8), (6.1, 9.0, 5.8), frame)
    box(g, p, 'pb', (3.0, 2.0, .6), (6.1, 9.0, .85), mat(p + 'pbed', '#6b7384', .5, .6))
    pis = cy(g, p, 'pis', .35, 2.2, (0, 0, 0), mat(p + 'piston', '#c9ced8', .3, .9), seg=14)
    pis.parent = None
    pis.name = p + 'piston'
    pis.location = (ox + 6.1, 9.0, 3.9)
    _mover(pis.name, (0, 0, 0), bob=(-1.0, .22, 0))
    # silos, pipes, catwalk
    silo = painted(p + 'silo', c.get('silo', '#d9dde5'), '#f1f3f7', .5, tex='metal_plate', tscale=.5, grain=.3)
    for sx_, hh in ((-12.0, 8.6), (-9.0, 7.6), (12.0, 8.6)):
        cy(g, p, 'si', 1.4, hh, (sx_, 12.5, hh / 2), silo, seg=24)
        cone(g, p, 'sc', 1.4, .15, 1.2, (sx_, 12.5, hh + .6), mat(p + 'sico', '#d94a4a', .6), seg=24)
        cy(g, p, 'sb', 1.45, .15, (sx_, 12.5, 3.2), mat(p + 'band', '#2a2f3d', .5, .6), seg=24)
    pipe = mat(p + 'pipe', '#c8a24a', .4, .8)
    pipe2 = mat(p + 'pipe2', '#4aa8d9', .4, .5)
    cy(g, p, 'pp', .22, 30, (0, 14.6, 7.0), pipe, rot=(0, 90, 0), seg=12)
    cy(g, p, 'pp', .17, 30, (0, 14.6, 6.3), pipe2, rot=(0, 90, 0), seg=12)
    for xx in (-12, -4, 4, 12):
        cy(g, p, 'rs', .2, 7.0, (xx, 14.6, 3.5), pipe, seg=12)
    box(g, p, 'cw', (34, 1.8, .15), (0, 13.6, 5.0), frame)
    for k in range(-16, 17):
        cy(g, p, 'rp', .035, 1.0, (k * 1.0, 12.7, 5.6), frame, seg=6, shadow=False)
    for zz in (5.6, 6.1):
        box(g, p, 'rr', (34, .06, .06), (0, 12.7, zz), frame, shadow=False)
    # hanging lamps and trusses
    for k in range(-2, 3):
        box(g, p, 'tr', (.4, 31, .5), (k * 6.5 + 3.25, 1, 11.7), frame, shadow=False)
    for yy in (-8, 0, 8):
        box(g, p, 'tr', (35, .4, .5), (0, yy, 11.7), frame, shadow=False)
    lampm = mat(p + 'lampc', '#2a2f3d', .5, .5)
    for xx in (-10, 0, 10):
        for yy in (-2, 7):
            cy(g, p, 'lc', .02, 3.2, (xx, yy, 10.0), frame, seg=6, shadow=False)
            cone(g, p, 'lm', .9, .25, .7, (xx, yy, 8.2), lampm, seg=14)
            ball(g, p, 'lb', .32, (xx, yy, 7.9), mat(p + 'lbulb', '#ffe2a8', .3, 0, 8.0), seg=10, shadow=False)
        lamp(g, p, (xx, 3, 7.5), 1200, '#ffd9a0', .6)
    # loading door, signs
    box(g, p, 'ld', (7.0, .3, 6.0), (0, 15.8, 3.0), painted(p + 'door', '#c9a227', '#e0bb3a', .5, tex='metal_plate', tscale=.5, grain=.3, bump=.4))
    for k in range(9):
        box(g, p, 'lr', (7.0, .08, .08), (0, 15.6, .7 + k * .65), mat(p + 'rib', '#8a6d12', .5, .5), shadow=False)
    plate(p + 'load', 'LOADING', .8, (0, 15.5, 6.7), '#14131a', '#f2c230', pad=(.3, .12), parent=g)
    plate(p + 'line', 'LINE 3', .5, (-7.0, 15.7, 4.8), '#14131a', '#ffffff', pad=(.2, .08), parent=g)
    plate(p + 'caut', 'CAUTION', .45, (7.0, 15.7, 4.8), '#f2c230', '#14131a', pad=(.2, .08), parent=g)
    plate(p + 'exit', 'EXIT', .36, (13.5, 15.7, 3.0), '#0e2a1c', '#4dff88', pad=(.12, .05), parent=g)
    # cabinet with blinking lights + brand, cartons, barrels, pallets
    box(g, p, 'cab', (1.6, .8, 2.4), (-12.5, 4.5, 1.2), mat(p + 'cabinet', '#36445e', .5, .5), bevel=.03)
    for k in range(5):
        ball(g, p, 'bl', .06, (-12.9 + k * .22, 4.07, 2.0), mat(f'{p}led{k % 3}', ('#38e08a', '#ff4d5e', '#ffb040')[k % 3], .3, 0, 4.0), seg=6, shadow=False)
    box(g, p, 'bp', (.9, .04, .3), (-12.5, 4.08, 1.2), mat(p + 'bpm', '#101522', .5))
    image_plane(p + 'brand', BRAND, .78, (-12.5, 4.05, 1.2), g)
    for i, (cx, cyy) in enumerate(((10.5, 3.5), (12.0, 3.8), (11.2, 3.6), (-9.0, 2.5))):
        box(g, p, 'pl', (1.3, 1.1, .15), (cx, cyy, .08), mat(p + 'pallet', '#8a5a36', .9))
        box(g, p, 'cx', (1.1, .9, .9 + .2 * (i % 2)), (cx, cyy, .6 + (1.0 if i == 2 else 0)), cart)
    for bxx, byy in ((13.5, 1.0), (14.3, 1.8), (13.0, 2.0)):
        cy(g, p, 'bb', .4, 1.0, (bxx, byy, .5), mat(p + 'barrel', '#2d6fb8', .6), seg=14)
    cy(g, p, 'fe', .1, .55, (-14.2, 1.0, 1.2), mat(p + 'fe', '#d63a2e', .5), seg=10)
    lamp(g, p, (0, -6, 8), 900, '#ffd9a0', .8)
    return g


def store_set(name, ox=0.0, **c):
    """Corner shop: tiled floor, a stocked wall of shelves, two aisles of gondola shelves, fridge cases, a counter with a cash register, hanging SALE and OPEN signs, bunting."""
    g = group(name, None, (ox, 0, 0))
    p = name + '_'
    tiles = checker_mat(p + 'floor', c.get('floor1', '#f2efe6'), c.get('floor2', '#7fc4b8'), .8, .35)
    wall = painted(p + 'wall', c.get('wall', '#2a9d9b'), '#47bbb5', .4, tex='painted_plaster_wall', tscale=.5, grain=.3, grad=(2.5, 8, .78))
    ceil = mat(p + 'ceil', '#cfc4aa', .9)
    _shell(g, p, 26, -12, 13, 8, tiles, wall, ceil)
    pal = c.get('stock', ('#e8453c', '#f2b83d', '#3d8fd9', '#4fb86a', '#f2f0e6', '#9a5ac4', '#ff8fa0'))
    st = stock_mat(p + 'stock', pal)
    box(g, p, 'bk', (24, .7, 3.6), (0, 12.6, 1.8), st)
    box(g, p, 'sf', (24.4, .8, .12), (0, 12.55, 3.66), mat(p + 'shelfbar', '#e8d9b8', .6))
    box(g, p, 'sb', (24, .75, .3), (0, 12.58, .15), mat(p + 'shbase', '#3a2f26', .7))
    for sx_ in (-1, 1):
        for k, yy in enumerate((2.0, 4.0, 6.0, 8.0, 10.0)):
            if True:
                box(g, p, 'gd', (1.1, 1.9, 1.9), (sx_ * 7.6, yy + .3, .95), st, rot=None)
        box(g, p, 'gt', (1.2, 10.2, .08), (sx_ * 7.6, 6.2, 1.94), mat(p + 'gtop', '#e8d9b8', .6))
    # fridge cases left, glowing
    box(g, p, 'fr', (1.2, 6.0, 2.2), (-12.2, 6.0, 1.1), mat(p + 'fridge', '#dfe8f0', .5, .3))
    box(g, p, 'fg', (.06, 5.6, 1.9), (-11.58, 6.0, 1.15), mat(p + 'fridgeglow', '#bfe8ff', .4, 0, 1.6), shadow=False)
    plate(p + 'cold', 'FRESH', .5, (-12.2, 6.0, 3.0), '#14463f', '#ffffff', pad=(.18, .07), parent=g)
    p0 = bpy.data.objects[p + 'cold']
    p0.rotation_euler = (0, 0, math.radians(90))
    # counter, register, brand
    wood = painted(p + 'wood', '#8a5a36', '#a4703f', 1.2, tex='dirt', tscale=1.0, grain=.3, bump=.2)
    box(g, p, 'cn', (4.2, 1.2, 1.1), (5.2, 3.0, .55), wood, bevel=.02)
    box(g, p, 'ct', (4.5, 1.4, .08), (5.2, 3.0, 1.14), mat(p + 'ctop', '#f2efe6', .3))
    try:
        r = model('CashRegister_01', (4.4, 3.0, 1.18), 1.0, 180, g)
    except Exception as e:  # model missing: simple stand-in register
        print('NO_REGISTER', e)
        box(g, p, 'rg', (.5, .4, .35), (4.4, 3.0, 1.35), mat(p + 'reg', '#3a4668', .5))
    box(g, p, 'bp', (1.0, .04, .34), (5.2, 2.38, .6), mat(p + 'bpm', '#101522', .5))
    image_plane(p + 'brand', BRAND, .88, (5.2, 2.35, .6), g)
    for k in range(4):
        box(g, p, 'ba', (.5, .35, .25), (6.2 + (k % 2) * .6, 3.0 + (k // 2) * .4, 1.3), mat(f'{p}bask{k % 2}', ('#e8453c', '#2d6fb8')[k % 2], .7), bevel=.03)
    # signs
    plate(p + 'sale', 'SALE', .9, (-3.5, 8.0, 5.2), '#d63a2e', '#ffffff', pad=(.3, .1), parent=g)
    plate(p + 'open', 'OPEN', .6, (5.2, 2.7, 3.2), '#101522', '#ffd34d', pad=(.25, .1), parent=g)
    plate(p + 'market', 'MARKET', 1.2, (0, 12.2, 6.2), '#f2b83d', '#14463f', pad=(.4, .15), parent=g)
    for k, (tx, bg, fg) in enumerate((('SNACKS', '#e8453c', '#ffffff'), ('DRINKS', '#2d6fb8', '#ffffff'), ('FRUIT', '#4fb86a', '#10261f'))):
        plate(f'{p}cat{k}', tx, .5, (-7 + k * 7, 12.2, 4.5), bg, fg, pad=(.2, .08), parent=g)
    for xx in (-3.5 - .9, -3.5 + .9):
        cy(g, p, 'hr', .02, 3.0, (xx, 8.0, 6.5), mat(p + 'rod', '#2a2f3d', .5, .6), seg=6, shadow=False)
    # bunting
    for k in range(18):
        xx = -9 + k
        col = ('#e8453c', '#f2b83d', '#3d8fd9', '#4fb86a')[k % 4]
        cone(g, p, 'bu', .28, .02, .5, (xx, 9.0, 6.0 - .35 * math.sin(math.pi * k / 17)), mat(f'{p}bun{k % 4}', col, .8), seg=3, rot=(180, 0, 0))
    box(g, p, 'bw', (18, .03, .03), (0, 9.0, 6.15), mat(p + 'bwire', '#15171d', .7), shadow=False)
    # plants, crates, mats
    for px_, py_ in ((-10.5, -.5), (10.8, -.5)):
        cy(g, p, 'pt', .45, .8, (px_, py_, .4), mat(p + 'pot', '#d98a3a', .8), seg=12)
        ball(g, p, 'pl', .8, (px_, py_, 1.5), mat(p + 'leaf', '#4fb86a', .9), scl=(1, 1, 1.2), seg=10)
    box(g, p, 'mt', (2.2, 1.4, .03), (0, -1.0, .02), mat(p + 'mat', '#e8453c', .9), shadow=False)
    for i, (cx, cyy) in enumerate(((-3.5, 6.5), (-4.5, 6.8), (-2.8, 7.0))):
        box(g, p, 'cr', (.8, .6, .5), (cx, cyy, .25 + (.5 if i == 2 else 0)), mat(p + 'crate', '#c49a5e', .85), bevel=.03)
    lamp(g, p, (0, 0, 6.5), 1300, '#ffe2b8', .8)
    lamp(g, p, (0, 8, 6.5), 1000, '#ffe2b8', .8)
    lamp(g, p, (5, 3, 4.5), 500, '#ffd9a0', .6)
    return g



