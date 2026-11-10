"""Falcos symbol animations, built and rendered in Blender.

  Inside Blender (MCP or background):
      import symanim; symanim.build('H1')            # scene for one symbol, all clips on one timeline
      symanim.render('H1', out_root)                  # PNG frames  <out_root>/<ID>/<clip>/####.png
  Background batch:
      Blender -b --factory-startup --python tools/falcos/blender/run_symbols.py -- H1,H2,... [res]

Conventions: the icon canvas (2048 px art) is a plane in the XZ plane facing the camera (-Y). The
painted object spans 10 units across its longer side; the orthographic camera is 13 units across, so
motion and particles have room. Clips sit back to back on one timeline (CLIPS below); land / hit start
and end on the rest pose, idle loops, burn ends empty.
"""
import bpy, math, os, random, json
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
SYM = os.path.join(ROOT, 'art', 'falcos', 'symbols')
PART = os.path.join(ROOT, 'art', 'falcos', 'particles')
FPS = 30
CAM = 13.0
PLANE = 10.0 * 2048 / 1760          # canvas size so the painted object is 10 units across
CLIPS = {'idle': 72, 'land': 24, 'hit': 46, 'burn': 36}

# glow colour per symbol (linear-ish RGB), pivot 'bottom' or 'top', particles, motion personality
P = {
    'H1': dict(glow=(1.0, 0.72, 0.15), gs=2.2, pivot='bottom', parts=['coin', 'coin_tilt', 'bill', 'sparkle'], n=16, hit='shake', land='heavy'),
    'H2': dict(glow=(1.0, 0.75, 0.2), gs=1.8, pivot='top', parts=['sparkle', 'coin', 'sparkle'], n=12, hit='swing', land='spin'),
    'H3': dict(glow=(1.0, 0.16, 0.2), gs=1.6, pivot='bottom', parts=['fueldrop', 'sparkle', 'fueldrop'], n=12, hit='pump', land='bounce'),
    'H4': dict(glow=(0.25, 0.45, 1.0), gs=1.6, pivot='bottom', parts=['fueldrop', 'sparkle'], n=12, hit='slosh', land='heavy'),
    'L1': dict(glow=(0.4, 1.0, 0.3), gs=0.0, pivot='bottom', parts=['bubble', 'bubble', 'sparkle'], n=12, hit='fizz', land='bounce'),
    'L2': dict(glow=(0.3, 0.6, 1.0), gs=0.0, pivot='bottom', parts=['ice_blue', 'ice_red', 'sparkle'], n=12, hit='jelly', land='jelly'),
    'L3': dict(glow=(1.0, 0.6, 0.2), gs=0.0, pivot='bottom', parts=['ember', 'smoke', 'sparkle'], n=10, hit='bounce', land='bounce'),
    'L4': dict(glow=(1.0, 0.8, 0.2), gs=0.0, pivot='bottom', parts=['crumb', 'crumb', 'sparkle'], n=12, hit='puff', land='jelly'),
    'L5': dict(glow=(1.0, 0.4, 0.8), gs=0.0, pivot='bottom', parts=['sprinkles', 'sprinkles', 'sparkle'], n=12, hit='roll', land='bounce'),
    'ZP': dict(glow=(1.0, 0.45, 0.1), gs=2.4, pivot='bottom', parts=['flame', 'ember', 'ember', 'sparkle'], n=16, hit='flare', land='spin'),
    'ST': dict(glow=(0.4, 1.0, 0.95), gs=2.0, pivot='bottom', parts=['flake_silver', 'sparkle', 'flake_silver'], n=14, hit='shake', land='spin'),
    'GT': dict(glow=(1.0, 0.8, 0.2), gs=2.6, pivot='bottom', parts=['flake_gold', 'sparkle', 'coin'], n=18, hit='shake', land='spin'),
    'GP': dict(glow=(1.0, 0.15, 0.2), gs=2.6, pivot='bottom', parts=['neon_star', 'sparkle', 'fueldrop'], n=14, hit='pump', land='heavy'),
    'FDG': dict(glow=(0.45, 1.0, 0.3), gs=1.6, pivot='bottom', parts=['sparkle'], n=8, hit='jelly', land='jelly'),
    'FDA': dict(glow=(1.0, 0.7, 0.15), gs=1.8, pivot='bottom', parts=['sparkle'], n=10, hit='jelly', land='jelly'),
    'FDR': dict(glow=(1.0, 0.1, 0.12), gs=2.2, pivot='bottom', parts=['sparkle', 'ember'], n=12, hit='jelly', land='jelly'),
    'BS': dict(glow=(1.0, 0.18, 0.22), gs=2.6, pivot='center', parts=['neon_star', 'sparkle', 'coin'], n=16, hit='flip', land='flip'),
    'DS': dict(glow=(0.6, 0.1, 0.5), gs=2.8, pivot='center', parts=['smoke', 'neon_star', 'sparkle'], n=16, hit='flip', land='flip'),
}


def rest_glow(sid):
    """Glow level every clip starts / ends on (tiers glow a little at rest, lows not at all)."""
    return 0.0 if P[sid]['gs'] == 0 else 0.10 + 0.05 * P[sid]['gs']


def clip_range(name):
    f = 1
    for k, n in CLIPS.items():
        if k == name:
            return f, f + n - 1
        f += n + 4          # 4 spare frames between clips
    raise KeyError(name)


# ---------------------------------------------------------------- scene

def reset():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.materials, bpy.data.images, bpy.data.meshes, bpy.data.actions, bpy.data.cameras):
        for x in list(coll):
            if x.users == 0:
                coll.remove(x)


def setup_scene(res):
    sc = bpy.context.scene
    try:
        sc.render.engine = 'BLENDER_EEVEE'
    except TypeError:
        sc.render.engine = 'BLENDER_EEVEE_NEXT'
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.fps = FPS
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.image_settings.color_depth = '8'
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = 0
    sc.view_settings.gamma = 1
    try:
        sc.eevee.taa_render_samples = 32
    except Exception:
        pass
    cam_data = bpy.data.cameras.new('cam')
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = CAM
    cam = bpy.data.objects.new('cam', cam_data)
    sc.collection.objects.link(cam)
    cam.location = (0, -20, 0)
    cam.rotation_euler = (math.radians(90), 0, 0)
    sc.camera = cam
    sc.frame_start = 1
    last = clip_range('burn')[1]
    sc.frame_end = last


def _img(path):
    for im in bpy.data.images:
        if im.filepath == path:
            return im
    im = bpy.data.images.load(path)
    im.alpha_mode = 'STRAIGHT'
    return im


def _plane(name, w, h):
    me = bpy.data.meshes.new(name)
    hw, hh = w / 2, h / 2
    me.from_pydata([(-hw, 0, -hh), (hw, 0, -hh), (hw, 0, hh), (-hw, 0, hh)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new()
    for i, c in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[i].uv = c
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _blend(mat, method='BLENDED'):
    for attr, val in (('surface_render_method', method), ('blend_method', 'BLEND' if method == 'BLENDED' else 'HASHED')):
        try:
            setattr(mat, attr, val)
        except Exception:
            pass
    try:
        mat.use_backface_culling = False
    except Exception:
        pass


def art_material(sid):
    """Unlit art + shine sweep + white flash + burn dissolve with a fiery edge.
    Driven by custom props on the material: shine (sweep position), flash (0-1), burn (0-1)."""
    mat = bpy.data.materials.new(f'art_{sid}')
    mat.use_nodes = True
    _blend(mat, 'DITHERED')
    nt = mat.node_tree; N = nt.nodes; L = nt.links
    for n in list(N):
        N.remove(n)
    out = N.new('ShaderNodeOutputMaterial')
    tex = N.new('ShaderNodeTexImage'); tex.image = _img(os.path.join(SYM, sid + '.png')); tex.interpolation = 'Cubic'
    tc = N.new('ShaderNodeTexCoord')
    sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs[0])

    def val(name, v=0.0):
        n = N.new('ShaderNodeValue'); n.name = name; n.label = name; n.outputs[0].default_value = v
        return n
    shine, flash, burn = val('shine', -20), val('flash'), val('burn')

    def math_(op, a, b=None, clamp=False):
        n = N.new('ShaderNodeMath'); n.operation = op; n.use_clamp = clamp
        for i, x in enumerate((a, b)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                n.inputs[i].default_value = x
            else:
                L.new(x, n.inputs[i])
        return n.outputs[0]

    # shine: diagonal band where u = x + z*0.6 is near `shine`
    u = math_('ADD', sep.outputs['X'], math_('MULTIPLY', sep.outputs['Z'], 0.6))
    d = math_('ABSOLUTE', math_('SUBTRACT', u, shine.outputs[0]))
    band = math_('POWER', math_('SUBTRACT', 1.0, math_('DIVIDE', d, 0.9), clamp=True), 2.0)
    band = math_('MULTIPLY', band, 0.32)
    # burn: noise + rising gradient vs threshold
    noise = N.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 0.55; noise.inputs['Detail'].default_value = 6
    L.new(tc.outputs['Object'], noise.inputs['Vector'])
    grad = math_('MULTIPLY', math_('ADD', sep.outputs['Z'], 6.0), 1 / 12.0)          # 0 bottom .. 1 top
    field = math_('ADD', math_('MULTIPLY', noise.outputs['Fac'], 0.55), math_('MULTIPLY', grad, 0.45))
    thr = math_('MULTIPLY', burn.outputs[0], 1.15)
    keep = math_('GREATER_THAN', field, thr)
    edge = math_('SUBTRACT', 1.0, math_('DIVIDE', math_('SUBTRACT', field, thr), 0.07), clamp=True)
    edge = math_('MULTIPLY', edge, keep)
    edge = math_('MULTIPLY', edge, math_('GREATER_THAN', burn.outputs[0], 0.001))
    char = math_('SUBTRACT', 1.0, math_('MULTIPLY', math_('SUBTRACT', 1.0, math_('DIVIDE', math_('SUBTRACT', field, thr), 0.22), clamp=True), 0.85), clamp=True)
    # colour = art * char + white*(band+flash) + fire*edge
    col = N.new('ShaderNodeMix'); col.data_type = 'RGBA'; col.blend_type = 'MULTIPLY'; col.inputs['Factor'].default_value = 1.0
    L.new(tex.outputs['Color'], col.inputs[6])
    charc = N.new('ShaderNodeCombineColor'); [L.new(char, charc.inputs[i]) for i in range(3)]
    L.new(charc.outputs[0], col.inputs[7])
    lift = math_('ADD', band, flash.outputs[0])
    # brighten in proportion to the art (a linear-light screen would wash the darks out)
    gain = math_('ADD', 1.0, math_('MULTIPLY', lift, 2.2))
    gainc = N.new('ShaderNodeCombineColor'); [L.new(gain, gainc.inputs[i]) for i in range(3)]
    mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
    L.new(col.outputs[2], mul.inputs[6]); L.new(gainc.outputs[0], mul.inputs[7])
    add1 = N.new('ShaderNodeMix'); add1.data_type = 'RGBA'; add1.blend_type = 'ADD'
    L.new(math_('MULTIPLY', lift, 0.035), add1.inputs['Factor']); L.new(mul.outputs[2], add1.inputs[6]); add1.inputs[7].default_value = (1, 0.97, 0.9, 1)
    fire = N.new('ShaderNodeMix'); fire.data_type = 'RGBA'; fire.blend_type = 'ADD'
    L.new(edge, fire.inputs['Factor']); L.new(add1.outputs[2], fire.inputs[6]); fire.inputs[7].default_value = (1.0, 0.55, 0.12, 1)
    em = N.new('ShaderNodeEmission'); L.new(fire.outputs[2], em.inputs['Color']); em.inputs['Strength'].default_value = 1.0
    alpha = math_('MULTIPLY', tex.outputs['Alpha'], keep)
    alpha = math_('MAXIMUM', alpha, math_('MULTIPLY', edge, tex.outputs['Alpha']))
    tr = N.new('ShaderNodeBsdfTransparent')
    mix = N.new('ShaderNodeMixShader'); L.new(alpha, mix.inputs['Fac']); L.new(tr.outputs[0], mix.inputs[1]); L.new(em.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], out.inputs['Surface'])
    return mat


def glow_material(sid, color):
    """A soft halo from the blurred silhouette (made once in PIL-free Blender: we blur by sampling a
    pre-made file art/falcos/symbols/glow/<ID>.png). Strength driven by the 'glow' value node."""
    path = os.path.join(SYM, 'glow', sid + '.png')
    mat = bpy.data.materials.new(f'glow_{sid}')
    mat.use_nodes = True
    _blend(mat)
    nt = mat.node_tree; N = nt.nodes; L = nt.links
    for n in list(N):
        N.remove(n)
    out = N.new('ShaderNodeOutputMaterial')
    tex = N.new('ShaderNodeTexImage'); tex.image = _img(path)
    g = N.new('ShaderNodeValue'); g.name = 'glow'; g.outputs[0].default_value = 0.0
    m = N.new('ShaderNodeMath'); m.operation = 'MULTIPLY'; L.new(tex.outputs['Alpha'], m.inputs[0]); L.new(g.outputs[0], m.inputs[1])
    m2 = N.new('ShaderNodeMath'); m2.operation = 'MINIMUM'; m2.inputs[1].default_value = 0.6; L.new(m.outputs[0], m2.inputs[0])
    em = N.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*color, 1); em.inputs['Strength'].default_value = 1.0
    tr = N.new('ShaderNodeBsdfTransparent')
    mix = N.new('ShaderNodeMixShader'); L.new(m2.outputs[0], mix.inputs['Fac']); L.new(tr.outputs[0], mix.inputs[1]); L.new(em.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], out.inputs['Surface'])
    return mat


def sprite_material(name):
    mat = bpy.data.materials.get('spr_' + name)
    if mat:
        return mat
    mat = bpy.data.materials.new('spr_' + name)
    mat.use_nodes = True
    _blend(mat, 'DITHERED')
    nt = mat.node_tree; N = nt.nodes; L = nt.links
    for n in list(N):
        N.remove(n)
    out = N.new('ShaderNodeOutputMaterial')
    tex = N.new('ShaderNodeTexImage'); tex.image = _img(os.path.join(PART, name + '.png'))
    oi = N.new('ShaderNodeObjectInfo')
    m = N.new('ShaderNodeMath'); m.operation = 'MULTIPLY'; L.new(tex.outputs['Alpha'], m.inputs[0]); L.new(oi.outputs['Alpha'], m.inputs[1])
    em = N.new('ShaderNodeEmission'); L.new(tex.outputs['Color'], em.inputs['Color'])
    tr = N.new('ShaderNodeBsdfTransparent')
    mix = N.new('ShaderNodeMixShader'); L.new(m.outputs[0], mix.inputs['Fac']); L.new(tr.outputs[0], mix.inputs[1]); L.new(em.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], out.inputs['Surface'])
    return mat


# ---------------------------------------------------------------- keys

def _key(ob, f, loc=None, rot=None, scl=None, interp='BEZIER'):
    if loc is not None:
        ob.location = loc; ob.keyframe_insert('location', frame=f)
    if rot is not None:
        ob.rotation_euler = (0, math.radians(rot), 0); ob.keyframe_insert('rotation_euler', frame=f)
    if scl is not None:
        ob.scale = scl; ob.keyframe_insert('scale', frame=f)


def _kval(node, f, v):
    node.outputs[0].default_value = v
    node.outputs[0].keyframe_insert('default_value', frame=f)


def _ease_all(interp='BEZIER'):
    for act in bpy.data.actions:
        for fc in _fcurves(act):
            for kp in fc.keyframe_points:
                kp.interpolation = interp
                kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'


def _fcurves(act):
    try:
        return list(act.fcurves)
    except AttributeError:          # Blender 5 layered actions
        out = []
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    out.extend(bag.fcurves)
        return out


REST = dict(loc=(0, 0, 0), rot=0, scl=(1, 1, 1))


def anim_land(sid, piv, f0, f1, mat, glow):
    p = P[sid]; style = p['land']; n = f1 - f0
    _key(piv, f0, loc=(0, 0, 0.6), rot=0, scl=(0.9, 1, 1.1))
    hitf = f0 + 2
    _key(piv, hitf, loc=(0, 0, 0), scl=(1.02, 1, 0.98))
    if style == 'heavy':
        _key(piv, hitf + 2, scl=(1.18, 1, 0.8)); _key(piv, hitf + 6, scl=(0.95, 1, 1.06)); _key(piv, hitf + 10, scl=(1.02, 1, 0.98))
    elif style == 'jelly':
        _key(piv, hitf + 2, scl=(1.22, 1, 0.78)); _key(piv, hitf + 5, scl=(0.88, 1, 1.12)); _key(piv, hitf + 8, scl=(1.07, 1, 0.94)); _key(piv, hitf + 11, scl=(0.98, 1, 1.02))
    elif style == 'spin':
        _key(piv, f0, rot=-12); _key(piv, hitf, rot=5); _key(piv, hitf + 4, rot=-3, scl=(1.1, 1, 0.9)); _key(piv, hitf + 8, rot=1, scl=(0.98, 1, 1.02))
    elif style == 'flip':
        _key(piv, f0, scl=(0.15, 1, 1.0)); _key(piv, hitf + 3, scl=(1.08, 1, 0.96)); _key(piv, hitf + 7, scl=(0.95, 1, 1.03)); _key(piv, hitf + 11, scl=(1.01, 1, 1))
    else:  # bounce
        _key(piv, hitf + 2, scl=(1.14, 1, 0.86)); _key(piv, hitf + 6, loc=(0, 0, 0.9), scl=(0.96, 1, 1.05)); _key(piv, hitf + 10, loc=(0, 0, 0), scl=(1.05, 1, 0.95))
    _key(piv, f1, **REST)
    _kval(mat['flash'], f0, 0); _kval(mat['flash'], hitf, 0.12); _kval(mat['flash'], hitf + 6, 0); _kval(mat['flash'], f1, 0)
    _kval(mat['shine'], f0, -20); _kval(mat['shine'], hitf, -9); _kval(mat['shine'], f1, 9); _kval(mat['shine'], f1 + 1, -20)
    if glow:
        g0 = rest_glow(sid); _kval(glow, f0, 0); _kval(glow, hitf, max(g0, 0.25) * 2.0); _kval(glow, f1, g0)


def anim_idle(sid, piv, f0, f1, mat, glow):
    n = f1 - f0 + 1
    for i in range(0, n + 1, 6):
        t = i / n * 2 * math.pi
        s = 1 + 0.018 * math.sin(t)
        _key(piv, f0 + i, loc=(0, 0, 0.05 * math.sin(t)), rot=1.2 * math.sin(t * 1 + 0.6) if P[sid]['pivot'] != 'top' else 3.0 * math.sin(t),
             scl=(1 - 0.01 * math.sin(t), 1, s))
    # shine sweeps once mid-loop
    _kval(mat['shine'], f0, -20); _kval(mat['shine'], f0 + 30, -11); _kval(mat['shine'], f0 + 50, 11); _kval(mat['shine'], f0 + 51, -20); _kval(mat['shine'], f1, -20)
    _kval(mat['flash'], f0, 0); _kval(mat['flash'], f1, 0)
    if glow:
        g0 = rest_glow(sid)
        for i in range(0, n + 1, 12):
            _kval(glow, f0 + i, g0 * (1 + 0.4 * math.sin(i / n * 2 * math.pi)))


def anim_hit(sid, piv, f0, f1, mat, glow):
    p = P[sid]; st = p['hit']
    _key(piv, f0, **REST)
    _key(piv, f0 + 4, scl=(0.9, 1, 0.9))                          # anticipation
    _key(piv, f0 + 9, loc=(0, 0, 0.35), scl=(1.2, 1, 1.2))         # pop
    wig = {'shake': (6, 3), 'swing': (14, 4), 'pump': (4, 2), 'slosh': (10, 3), 'fizz': (5, 4), 'jelly': (3, 3),
           'bounce': (4, 2), 'puff': (3, 2), 'roll': (12, 2), 'flare': (5, 3), 'flip': (0, 0)}[st]
    amp, cyc = wig
    span = list(range(f0 + 11, f1 - 10, 3))
    for i, f in enumerate(span):
        k = 1 - i / max(1, len(span))
        r = amp * k * (1 if i % 2 == 0 else -1)
        sx = sz = 1.2 - 0.12 * (1 - k)
        if st in ('jelly', 'puff'):
            sx, sz = (sx + 0.08 * k, sz - 0.08 * k) if i % 2 == 0 else (sx - 0.08 * k, sz + 0.08 * k)
        if st == 'pump':
            sz -= 0.1 * k * (i % 2)
        if st == 'flip':
            sx = max(0.08, abs(math.cos(i * math.pi / 2.5))) * 1.15
        if st == 'bounce':
            _key(piv, f, loc=(0, 0, 0.35 + (0.6 * k if i % 2 == 0 else 0)))
        _key(piv, f, rot=r, scl=(sx, 1, sz))
    _key(piv, f1 - 6, loc=(0, 0, 0.05), rot=0, scl=(0.97, 1, 1.03))
    _key(piv, f1, **REST)
    _kval(mat['flash'], f0, 0); _kval(mat['flash'], f0 + 9, 0.10); _kval(mat['flash'], f0 + 14, 0.02); _kval(mat['flash'], f1, 0)
    _kval(mat['shine'], f0, -20); _kval(mat['shine'], f0 + 8, -10); _kval(mat['shine'], f0 + 22, 10); _kval(mat['shine'], f0 + 23, -20); _kval(mat['shine'], f1, -20)
    if glow:
        g0 = rest_glow(sid); gp = 0.55 if p['gs'] == 0 else 0.35 + 0.12 * p['gs']
        _kval(glow, f0, g0); _kval(glow, f0 + 9, gp * 1.6); _kval(glow, f0 + 30, gp); _kval(glow, f1, g0)


def anim_burn(sid, piv, f0, f1, mat, glow):
    _key(piv, f0, **REST)
    _key(piv, f0 + 5, scl=(1.08, 1, 1.08), rot=2)
    _key(piv, f0 + 12, scl=(1.04, 1, 1.0), rot=-1)
    _key(piv, f1, scl=(0.98, 1, 0.94), rot=0, loc=(0, 0, 0.2))
    _kval(mat['flash'], f0, 0); _kval(mat['flash'], f0 + 4, 0.15); _kval(mat['flash'], f0 + 9, 0.0)
    _kval(mat['burn'], f0, 0); _kval(mat['burn'], f0 + 6, 0.02); _kval(mat['burn'], f1 - 3, 1.0); _kval(mat['burn'], f1, 1.0)
    _kval(mat['burn'], f1 + 1, 0.0)
    if glow:
        _kval(glow, f0, rest_glow(sid)); _kval(glow, f0 + 5, 0.7); _kval(glow, f0 + 12, 0.25); _kval(glow, f0 + 18, 0.0); _kval(glow, f1, 0)


def particles(sid, f0, f1, burst_at, rng, kinds, n, up=1.0, gravity=-0.022, life=(20, 34), scale=(0.9, 1.6)):
    for i in range(n):
        kind = kinds[i % len(kinds)]
        tex = _img(os.path.join(PART, kind + '.png'))
        w, h = tex.size; s = rng.uniform(*scale)
        ob = _plane(f'p_{sid}_{f0}_{i}', s * w / max(w, h), s * h / max(w, h))
        ob.data.materials.append(sprite_material(kind))
        start = burst_at + rng.randint(0, 4)
        end = min(f1 - 1, start + rng.randint(*life))
        ang = rng.uniform(0, 2 * math.pi)
        sp = rng.uniform(0.18, 0.36)
        vx, vz = math.cos(ang) * sp, abs(math.sin(ang)) * sp * up + 0.12 * up
        x0, z0 = rng.uniform(-1.5, 1.5), rng.uniform(-1.0, 1.5)
        spin = rng.uniform(-14, 14)
        y = -1.5 - i * 0.01
        ob.color = (1, 1, 1, 0); ob.keyframe_insert('color', frame=f0); ob.keyframe_insert('color', frame=start - 1)
        x, z = x0, z0
        for k, f in enumerate(range(start, end + 1, 2)):
            t = f - start
            x = x0 + vx * t; z = z0 + vz * t + 0.5 * gravity * t * t
            x = max(-6.0, min(6.0, x)); z = max(-6.0, min(6.0, z))
            life_t = t / max(1, end - start)
            ob.location = (x, y, z); ob.keyframe_insert('location', frame=f)
            ob.rotation_euler = (0, math.radians(spin * t), 0); ob.keyframe_insert('rotation_euler', frame=f)
            sc = (0.4 + 0.6 * min(1, t / 4)) * (1 - 0.5 * life_t)
            ob.scale = (sc, sc, sc); ob.keyframe_insert('scale', frame=f)
            a = 1.0 if life_t < 0.6 else max(0.0, 1 - (life_t - 0.6) / 0.4)
            ob.color = (1, 1, 1, a); ob.keyframe_insert('color', frame=f)
        ob.color = (1, 1, 1, 0); ob.keyframe_insert('color', frame=end + 1)


def build(sid, res=1024):
    reset()
    setup_scene(res)
    p = P[sid]
    piv = bpy.data.objects.new('pivot', None)
    bpy.context.scene.collection.objects.link(piv)
    art = _plane('art', PLANE, PLANE)
    mat = art_material(sid); art.data.materials.append(mat)
    pz = {'bottom': -5.0, 'top': 4.6, 'center': 0.0}[p['pivot']]
    art.parent = piv; art.location = (0, 0, -pz)
    piv.location = (0, 0, pz)
    # the pivot moves in its own space: wrap it in a holder at the pivot point
    holder = bpy.data.objects.new('holder', None); bpy.context.scene.collection.objects.link(holder)
    holder.location = (0, 0, pz); piv.parent = holder; piv.location = (0, 0, 0)
    glow_node = None
    if os.path.exists(os.path.join(SYM, 'glow', sid + '.png')):
        g = _plane('glow', PLANE * 1.12, PLANE * 1.12)
        gm = glow_material(sid, p['glow']); g.data.materials.append(gm)
        g.parent = piv; g.location = (0, 0.5, -pz)
        glow_node = gm.node_tree.nodes['glow']
    nodes = {k: mat.node_tree.nodes[k] for k in ('shine', 'flash', 'burn')}
    rng = random.Random(hash(sid) & 0xffff)
    for clip in CLIPS:
        f0, f1 = clip_range(clip)
        {'idle': anim_idle, 'land': anim_land, 'hit': anim_hit, 'burn': anim_burn}[clip](sid, piv, f0, f1, nodes, glow_node)
        if clip == 'hit':
            particles(sid, f0, f1, f0 + 8, rng, p['parts'], p['n'])
        if clip == 'land' and p['land'] in ('heavy', 'jelly'):
            particles(sid, f0, f1, f0 + 6, rng, ['sparkle'], 5, up=0.5, life=(10, 16), scale=(0.5, 0.9))
        if clip == 'burn':
            particles(sid, f0, f1, f0 + 8, rng, ['flame', 'ember', 'ember', 'smoke'], 14, up=1.3, gravity=0.004, life=(14, 24), scale=(0.8, 1.5))
    _ease_all()
    bpy.context.scene.frame_set(1)
    return dict(clips={k: clip_range(k) for k in CLIPS})


def render(sid, out_root, clips=None):
    sc = bpy.context.scene
    for clip in (clips or CLIPS):
        f0, f1 = clip_range(clip)
        d = os.path.join(out_root, sid, clip); os.makedirs(d, exist_ok=True)
        for i, f in enumerate(range(f0, f1 + 1)):
            sc.frame_set(f)
            sc.render.filepath = os.path.join(d, f'{i:04d}.png')
            bpy.ops.render.render(write_still=True)
