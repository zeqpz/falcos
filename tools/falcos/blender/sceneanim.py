"""Falcos background life, made in Blender: overlays that sit exactly on the 3840x2160 scene plate.

  Blender -b --factory-startup --python tools/falcos/blender/sceneanim.py -- [woman,cashier] [preview]

Each overlay is rendered as an RGBA frame loop of its own region of the plate (plate pixels, 4K
master) to art/falcos/scene/fx/<name>/####.png, plus art/falcos/scene/fx/regions.json with each
region's [x, y, w, h] in plate pixels so the game can place it. Units: 100 plate px = 1 Blender unit,
plate centre at the origin, the camera looks along +Y.
"""
import bpy, math, os, sys, json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
PLATE = os.path.join(ROOT, 'art', 'falcos', 'scene', 'plate_lit.png')
PART = os.path.join(ROOT, 'art', 'falcos', 'particles')
OUT = os.path.join(ROOT, 'art', 'falcos', 'scene', 'fx')
W, H = 3840, 2160
LOOP = 240                     # 8 s at 30 fps

REGIONS = {
    'woman': (420, 300, 600, 680),        # smoke, ember, exhale
    'cashier': (2870, 660, 960, 740),     # glass reflection sweep, coin glints
}
TIP = (630, 917)
MOUTH = (497, 926)
HAND = (3372, 1168)
WINDOW = (2885, 690, 3815, 1380)


def P(x, y, depth=0.0):
    return (x / 100 - W / 200, depth, H / 200 - y / 100)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    try:
        sc.render.engine = 'BLENDER_EEVEE'
    except TypeError:
        sc.render.engine = 'BLENDER_EEVEE_NEXT'
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.film_transparent = True
    sc.render.fps = 30
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.view_settings.view_transform = 'Standard'
    try:
        sc.eevee.taa_render_samples = 16
    except Exception:
        pass
    cd = bpy.data.cameras.new('cam'); cd.type = 'ORTHO'; cd.ortho_scale = W / 100
    cam = bpy.data.objects.new('cam', cd); sc.collection.objects.link(cam)
    cam.location = (0, -50, 0); cam.rotation_euler = (math.radians(90), 0, 0); sc.camera = cam
    sc.frame_start, sc.frame_end = 1, LOOP
    return sc


def plane(name, cx, cy, w, h, depth=0.0):
    me = bpy.data.meshes.new(name)
    hw, hh = w / 200, h / 200
    me.from_pydata([(-hw, 0, -hh), (hw, 0, -hh), (hw, 0, hh), (-hw, 0, hh)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new()
    for i, c in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[i].uv = c
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    ob.location = P(cx, cy, depth)
    return ob


class G:
    """Tiny node-graph helper."""
    def __init__(self, mat):
        mat.use_nodes = True
        for attr, val in (('surface_render_method', 'BLENDED'), ('blend_method', 'BLEND')):
            try:
                setattr(mat, attr, val)
            except Exception:
                pass
        self.nt = mat.node_tree; self.N = self.nt.nodes; self.L = self.nt.links
        for n in list(self.N):
            self.N.remove(n)

    def node(self, t, **kw):
        n = self.N.new(t)
        for k, v in kw.items():
            setattr(n, k, v)
        return n

    def link(self, a, b):
        self.L.new(a, b)

    def m(self, op, a, b=None, clamp=False):
        n = self.N.new('ShaderNodeMath'); n.operation = op; n.use_clamp = clamp
        for i, x in enumerate((a, b)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                n.inputs[i].default_value = x
            else:
                self.L.new(x, n.inputs[i])
        return n.outputs[0]

    def value(self, name, v=0.0):
        n = self.N.new('ShaderNodeValue'); n.name = name; n.outputs[0].default_value = v
        return n

    def out(self, color, alpha):
        em = self.N.new('ShaderNodeEmission')
        if isinstance(color, tuple):
            em.inputs['Color'].default_value = (*color, 1)
        else:
            self.L.new(color, em.inputs['Color'])
        tr = self.N.new('ShaderNodeBsdfTransparent')
        mix = self.N.new('ShaderNodeMixShader')
        self.L.new(alpha, mix.inputs['Fac']); self.L.new(tr.outputs[0], mix.inputs[1]); self.L.new(em.outputs[0], mix.inputs[2])
        o = self.N.new('ShaderNodeOutputMaterial'); self.L.new(mix.outputs[0], o.inputs['Surface'])


def linear_time(node, f0=1, f1=LOOP + 1, v0=0.0, v1=1.0):
    node.outputs[0].default_value = v0; node.outputs[0].keyframe_insert('default_value', frame=f0)
    node.outputs[0].default_value = v1; node.outputs[0].keyframe_insert('default_value', frame=f1)
    for fc in _fcurves(node.id_data.animation_data.action):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'


def _fcurves(act):
    try:
        return list(act.fcurves)
    except AttributeError:
        out = []
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    out.extend(bag.fcurves)
        return out


def smoke_ribbon(name, x, y, w, h, alpha_max=0.5, seed=0.0, sway=1.0):
    """A cartoon wisp rising from (x, y) (plate px, bottom-centre of the plane), looping every LOOP."""
    ob = plane(name, x, y - h / 2, w, h, depth=-1.0)
    mat = bpy.data.materials.new(name); ob.data.materials.append(mat)
    g = G(mat)
    tc = g.node('ShaderNodeTexCoord'); sep = g.node('ShaderNodeSeparateXYZ'); g.link(tc.outputs['UV'], sep.inputs[0])
    u = g.m('SUBTRACT', g.m('MULTIPLY', sep.outputs['X'], 2.0), 1.0)    # -1 .. 1 across
    v = sep.outputs['Y']                                                 # 0 bottom .. 1 top
    t = g.value('t'); linear_time(t)
    tau = g.m('MULTIPLY', t.outputs[0], 2 * math.pi)
    # centre line: two travelling sine waves that grow with height (periodic in t)
    c1 = g.m('MULTIPLY', g.m('SINE', g.m('SUBTRACT', g.m('MULTIPLY', v, 7.0), g.m('MULTIPLY', tau, 2.0))), g.m('MULTIPLY', v, 0.32 * sway))
    c2 = g.m('MULTIPLY', g.m('SINE', g.m('ADD', g.m('MULTIPLY', v, 13.0), g.m('ADD', tau, seed))), g.m('MULTIPLY', v, 0.12 * sway))
    c = g.m('ADD', c1, c2)
    width = g.m('ADD', 0.035, g.m('MULTIPLY', v, 0.30))
    d = g.m('DIVIDE', g.m('ABSOLUTE', g.m('SUBTRACT', u, c)), width)
    core = g.m('SUBTRACT', 1.0, d, clamp=True)
    # flowing noise, seamless over the loop (crossfade of two offsets)
    def flow(offset_t):
        comb = g.node('ShaderNodeCombineXYZ')
        g.link(g.m('MULTIPLY', u, 1.4), comb.inputs['X'])
        g.link(g.m('SUBTRACT', g.m('MULTIPLY', v, 3.0), g.m('MULTIPLY', offset_t, 3.0)), comb.inputs['Y'])
        comb.inputs['Z'].default_value = seed
        nz = g.node('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 2.2; nz.inputs['Detail'].default_value = 4
        g.link(comb.outputs[0], nz.inputs['Vector'])
        return nz.outputs['Fac']
    n1 = flow(t.outputs[0]); n2 = flow(g.m('SUBTRACT', t.outputs[0], 1.0))
    n = g.m('ADD', g.m('MULTIPLY', n1, g.m('SUBTRACT', 1.0, t.outputs[0])), g.m('MULTIPLY', n2, t.outputs[0]))
    dens = g.m('MULTIPLY', core, g.m('ADD', g.m('MULTIPLY', n, 1.6), -0.25))
    fade_in = g.m('DIVIDE', v, 0.06, clamp=True)
    fade_out = g.m('SUBTRACT', 1.0, g.m('DIVIDE', g.m('SUBTRACT', v, 0.45), 0.55), clamp=True)
    dens = g.m('MULTIPLY', dens, g.m('MULTIPLY', fade_in, fade_out))
    # toon edge: a soft but defined wisp
    a = g.m('MULTIPLY', g.m('DIVIDE', g.m('SUBTRACT', dens, 0.12), 0.25, clamp=True), alpha_max)
    g.out((0.72, 0.76, 0.86), a)
    return ob


def glow_disc(name, x, y, r, color, keys):
    ob = plane(name, x, y, r * 2, r * 2, depth=-1.2)
    mat = bpy.data.materials.new(name); ob.data.materials.append(mat)
    g = G(mat)
    tc = g.node('ShaderNodeTexCoord'); sep = g.node('ShaderNodeSeparateXYZ'); g.link(tc.outputs['UV'], sep.inputs[0])
    dx = g.m('SUBTRACT', sep.outputs['X'], 0.5); dy = g.m('SUBTRACT', sep.outputs['Y'], 0.5)
    rr = g.m('SQRT', g.m('ADD', g.m('MULTIPLY', dx, dx), g.m('MULTIPLY', dy, dy)))
    fall = g.m('POWER', g.m('SUBTRACT', 1.0, g.m('MULTIPLY', rr, 2.0), clamp=True), 2.2)
    k = g.value('k', keys[0][1])
    for f, val in keys:
        k.outputs[0].default_value = val; k.outputs[0].keyframe_insert('default_value', frame=f)
    g.out(color, g.m('MULTIPLY', fall, k.outputs[0]))
    return ob


def puff(name, x, y, f0, f1, dx, dy, size0, size1, alpha):
    """An exhaled puff: a soft noisy blob that drifts and grows, fading out."""
    ob = plane(name, x, y, 100, 100, depth=-1.1)
    mat = bpy.data.materials.new(name); ob.data.materials.append(mat)
    g = G(mat)
    tc = g.node('ShaderNodeTexCoord'); sep = g.node('ShaderNodeSeparateXYZ'); g.link(tc.outputs['UV'], sep.inputs[0])
    ddx = g.m('SUBTRACT', sep.outputs['X'], 0.5); ddy = g.m('SUBTRACT', sep.outputs['Y'], 0.5)
    rr = g.m('SQRT', g.m('ADD', g.m('MULTIPLY', ddx, ddx), g.m('MULTIPLY', ddy, ddy)))
    nz = g.node('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.0; nz.inputs['Detail'].default_value = 5
    g.link(tc.outputs['Object'], nz.inputs['Vector'])
    body = g.m('SUBTRACT', 1.0, g.m('MULTIPLY', rr, 2.0), clamp=True)
    dens = g.m('MULTIPLY', body, g.m('ADD', g.m('MULTIPLY', nz.outputs['Fac'], 1.8), -0.45))
    k = g.value('k', 0.0)
    a = g.m('MULTIPLY', g.m('DIVIDE', g.m('SUBTRACT', dens, 0.1), 0.3, clamp=True), k.outputs[0])
    g.out((0.74, 0.78, 0.88), a)
    for f, val in ((1, 0), (f0, 0), (f0 + 4, alpha), (int(f0 + (f1 - f0) * 0.45), alpha * 0.8), (f1, 0)):
        k.outputs[0].default_value = val; k.outputs[0].keyframe_insert('default_value', frame=f)
    for f, s, ox, oy in ((f0, size0, 0, 0), (f1, size1, dx, dy)):
        ob.location = P(x + ox, y + oy, -1.1); ob.keyframe_insert('location', frame=f)
        ob.scale = (s / 100, 1, s / 100); ob.keyframe_insert('scale', frame=f)
    return ob


def sprite(name, img, x, y, size, keys):
    """A particle sprite (alpha keyed) - for glints."""
    im = bpy.data.images.load(os.path.join(PART, img + '.png')); im.alpha_mode = 'STRAIGHT'
    ob = plane(name, x, y, size, size, depth=-1.3)
    mat = bpy.data.materials.new(name); ob.data.materials.append(mat)
    g = G(mat)
    tex = g.node('ShaderNodeTexImage'); tex.image = im
    k = g.value('k', 0.0)
    g.out(tex.outputs['Color'], g.m('MULTIPLY', tex.outputs['Alpha'], k.outputs[0]))
    for f, val, sc, rot in keys:
        k.outputs[0].default_value = val; k.outputs[0].keyframe_insert('default_value', frame=f)
        ob.scale = (sc, 1, sc); ob.keyframe_insert('scale', frame=f)
        ob.rotation_euler = (0, math.radians(rot), 0); ob.keyframe_insert('rotation_euler', frame=f)
    return ob


def sweep(name, rect, f0, f1, alpha):
    """A diagonal glass reflection crossing the window."""
    x0, y0, x1, y1 = rect
    ob = plane(name, (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0, depth=-1.0)
    mat = bpy.data.materials.new(name); ob.data.materials.append(mat)
    g = G(mat)
    tc = g.node('ShaderNodeTexCoord'); sep = g.node('ShaderNodeSeparateXYZ'); g.link(tc.outputs['UV'], sep.inputs[0])
    s = g.value('s', -0.6)
    u = g.m('ADD', sep.outputs['X'], g.m('MULTIPLY', sep.outputs['Y'], 0.55))
    d = g.m('ABSOLUTE', g.m('SUBTRACT', u, s.outputs[0]))
    band = g.m('ADD', g.m('POWER', g.m('SUBTRACT', 1.0, g.m('DIVIDE', d, 0.09), clamp=True), 1.5),
               g.m('MULTIPLY', g.m('POWER', g.m('SUBTRACT', 1.0, g.m('DIVIDE', g.m('ABSOLUTE', g.m('SUBTRACT', d, 0.16)), 0.03), clamp=True), 1.5), 0.6))
    g.out((1.0, 0.98, 0.95), g.m('MULTIPLY', band, alpha))
    for f, val in ((1, -0.6), (f0, -0.6), (f1, 2.2), (LOOP, 2.2)):
        s.outputs[0].default_value = val; s.outputs[0].keyframe_insert('default_value', frame=f)
    return ob


def build_woman():
    smoke_ribbon('smoke_a', TIP[0] + 2, TIP[1] - 6, 300, 560, alpha_max=0.55, seed=0.0)
    smoke_ribbon('smoke_b', TIP[0] + 6, TIP[1] - 10, 260, 470, alpha_max=0.28, seed=3.7, sway=1.4)
    # ember: a soft glow that breathes, brighter around the middle of the loop (a drag)
    keys = [(1, 0.55)] + [(f, 0.55 + 0.12 * math.sin(f / 9.0)) for f in range(10, 110, 10)] + \
           [(118, 0.6), (126, 1.0), (140, 0.95), (156, 0.6)] + [(f, 0.55 + 0.12 * math.sin(f / 9.0)) for f in range(170, LOOP, 10)] + [(LOOP, 0.55)]
    glow_disc('ember', TIP[0], TIP[1], 26, (1.0, 0.45, 0.12), keys)
    # exhale after the drag: two puffs from her lips drifting up and to the right
    puff('exhale_a', MOUTH[0] + 18, MOUTH[1] + 4, 160, 222, 120, -150, 40, 230, 0.55)
    puff('exhale_b', MOUTH[0] + 24, MOUTH[1] + 10, 166, 228, 170, -95, 30, 170, 0.35)


def build_cashier():
    sweep('glass_sweep', WINDOW, 70, 112, 0.16)
    sweep('glass_sweep2', WINDOW, 76, 120, 0.06)
    glints = [(HAND[0] - 18, HAND[1] - 6, 20), (HAND[0] + 12, HAND[1] + 4, 95), (HAND[0] - 2, HAND[1] - 14, 180)]
    for i, (x, y, f) in enumerate(glints):
        sprite(f'glint{i}', 'sparkle', x, y, 46, [(1, 0, 0.2, 0), (f, 0, 0.2, 0), (f + 4, 1, 1.0, 20), (f + 10, 0.8, 0.8, 40), (f + 16, 0, 0.2, 60), (LOOP, 0, 0.2, 60)])


def render(name, preview=False):
    sc = bpy.context.scene
    x, y, w, h = REGIONS[name]
    sc.render.use_border = True; sc.render.use_crop_to_border = True
    sc.render.border_min_x, sc.render.border_max_x = x / W, (x + w) / W
    sc.render.border_min_y, sc.render.border_max_y = 1 - (y + h) / H, 1 - y / H
    d = os.path.join(OUT, name); os.makedirs(d, exist_ok=True)
    frames = range(1, LOOP + 1, 20) if preview else range(1, LOOP + 1)
    for f in frames:
        sc.frame_set(f)
        sc.render.filepath = os.path.join(d, f'{f - 1:04d}.png')
        bpy.ops.render.render(write_still=True)
    reg = os.path.join(OUT, 'regions.json')
    data = json.load(open(reg)) if os.path.exists(reg) else {}
    data[name] = dict(rect=[x, y, w, h], frames=LOOP, fps=30, loop=True)
    json.dump(data, open(reg, 'w'), indent=1)


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    names = argv[0].split(',') if argv else list(REGIONS)
    preview = 'preview' in argv
    for name in names:
        reset()
        {'woman': build_woman, 'cashier': build_cashier}[name]()
        render(name, preview)
        print(f'[scene] {name} done', flush=True)
