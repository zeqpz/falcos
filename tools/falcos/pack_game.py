"""Pack the Falcos art into the game's asset formats under art/falcos/game/ (nothing in frontend/ is
touched; tools/falcos/install_game.py copies the result in).

  .venv/bin/python tools/falcos/pack_game.py [ui] [symbols] [scene]

ui      - plates, logos, win lettering, digits, board frame, bonus banners -> game file names
symbols - sym/<dd>/<ID>_<clip>.webp grid sheets + sym/manifest.json (same schema as the base game,
          clips idle/land/hit/burn) and flat/<ID>.webp 400 px stills
scene   - bonus_wall.webp (the 4K plate), scene/ overlays (sign_off, blinks, fx loops as frame sheets)
"""
import os, sys, json, glob, math
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
A = os.path.join(ROOT, 'art', 'falcos')
G = os.path.join(A, 'game')
SYMS = ['H1', 'H2', 'H3', 'H4', 'L1', 'L2', 'L3', 'L4', 'L5', 'ZP', 'ST', 'GT', 'GP', 'FDG', 'FDA', 'FDR', 'BS', 'DS']
CLIPS = {'idle': (72, True), 'land': (24, False), 'hit': (46, False), 'burn': (36, False)}
DENS = {'d10': 1.0, 'd12': 1.2, 'd16': 1.6, 'd24': 2.4}       # icon px = 100 * density
CAM, ICON = 13.0, 10.0                                          # render frame spans 13 units, icon 10


def latest(n):
    c = [f for f in os.listdir(os.path.join(A, 'raw')) if f == n + '.png' or (f.startswith(n + '.v') and f.endswith('.png'))]
    return os.path.join(A, 'raw', sorted(c, key=lambda f: (len(f), f))[-1])


def save(im, rel, q=88):
    p = os.path.join(G, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    im.save(p, quality=q, method=6)
    return p


def trim(im):
    bb = im.getbbox()
    return im.crop(bb) if bb else im


def fit_w(im, w):
    return im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)


def ui():
    T = lambda n: trim(Image.open(latest(n)).convert('RGBA'))
    jobs = {
        'title_logo.webp': (T('title_logo'), 1700), 'big_win.webp': (T('big_win'), 1800), 'mega_win.webp': (T('mega_win'), 1800),
        'xtreme_win.webp': (T('epic_win'), 1800), 'total_win.webp': (T('total_win'), 1800), 'tier_bg.webp': (T('tier_bg'), 1980),
        'total_bg.webp': (T('total_bg'), 1800), 'bonus_btn_text.webp': (T('bonus_btn_text'), 1140), 'bonus_btn_bg.webp': (T('bonus_btn_bg'), 950),
        'xbonus_text.webp': (T('logo_midnight'), 1400), 'logo_fillup.webp': (T('logo_fillup'), 1400), 'logo_premium.webp': (T('logo_premium'), 1400),
        'bonus_panel.webp': (T('bonus_panel'), 2250), 'info_panel.webp': (T('info_panel'), 1600), 'feature_box.webp': (T('feature_box'), 840),
        'win_box.webp': (T('win_box'), 900), 'banner_box.webp': (T('banner_box'), 1440), 'ui_box.webp': (T('ui_box'), 550),
        'frame.webp': (T('board_frame'), 2200),
    }
    for rel, (im, w) in jobs.items():
        save(fit_w(im, w), rel)
    bp = Image.open(latest('board_plate')).convert('RGB')
    save(bp.resize((1935, 1135), Image.LANCZOS), 'plate_grey.webp')
    for key, n in (('fs', 'banner_fillup'), ('boost', 'banner_premium'), ('xfs', 'banner_midnight'), ('chance', 'banner_chance'), ('nitro', 'banner_nitro')):
        save(Image.open(latest(n)).convert('RGB').resize((720, 405), Image.LANCZOS), f'bonus/banner_{key}.webp')
    for c, n in [(str(i), f'num_{i}') for i in range(10)] + [('dot', 'num_dot'), ('comma', 'num_comma'), ('x', 'num_x')]:
        im = Image.open(latest(n)).convert('RGBA')
        if c in ('dot', 'comma'):
            # keep the baseline: crop to the digits' common box, not the glyph's own
            im = im.crop((262, 60, 762, 980))
        else:
            im = trim(im)
        im = im.resize((round(im.width * 343 / im.height), 343), Image.LANCZOS) if c not in ('dot', 'comma') else im.resize((round(im.width * 343 / im.height), 343), Image.LANCZOS)
        if c in ('dot', 'comma'):
            im = trim(Image.new('RGBA', im.size, (0, 0, 0, 0))) if False else im
        save(im, f'num/{c}.webp')
    print('ui packed')


def symbols():
    man = {'densities': list(DENS.values()), 'symbols': {}}
    for sid in SYMS:
        ent = {'icon': [ICON, ICON], 'clips': {}, 'sheets': {}}
        for clip, (n, loop) in CLIPS.items():
            fs = sorted(glob.glob(os.path.join(A, 'renders', sid, clip, '*.png')))
            assert len(fs) == n, (sid, clip, len(fs))
            frames = [Image.open(f).convert('RGBA') for f in fs]
            # the clip's box: union of every frame's opaque area, in rig units (frame = CAM units, centred)
            W = frames[0].width
            u = None
            for im in frames:
                bb = im.getbbox()
                if bb:
                    u = bb if u is None else (min(u[0], bb[0]), min(u[1], bb[1]), max(u[2], bb[2]), max(u[3], bb[3]))
            u = u or (0, 0, W, W)
            k = CAM / W
            box = [round(u[0] * k - CAM / 2, 4), round(CAM / 2 - u[3] * k, 4), round((u[2] - u[0]) * k, 4), round((u[3] - u[1]) * k, 4)]
            ent['clips'][clip] = {'frames': n, 'fps': 30, 'loop': loop, 'box': box}
            crops = [im.crop(u) for im in frames]
            for dd, dens in DENS.items():
                px = 10 * dens / (W / CAM)           # render px -> this density (an icon unit is 10 px at d1.0)
                fw, fh = max(1, round(crops[0].width * px)), max(1, round(crops[0].height * px))
                cols = max(1, min(n, int(4096 // fw)))
                cols = min(cols, math.ceil(math.sqrt(n * fh / fw)) + 3)
                rows = math.ceil(n / cols)
                sheet = Image.new('RGBA', (cols * fw, rows * fh), (0, 0, 0, 0))
                for i, c in enumerate(crops):
                    sheet.paste(c.resize((fw, fh), Image.LANCZOS), ((i % cols) * fw, (i // cols) * fh))
                p = save(sheet, f'sym/{dd}/{sid}_{clip}.webp', q=86)
                ent['sheets'].setdefault(dd, {})[clip] = {'w': fw, 'h': fh, 'cols': cols, 'bytes': os.path.getsize(p)}
        man['symbols'][sid] = ent
        # flat still for paytable / reduced motion: the idle clip's first frame, icon-framed
        f0 = Image.open(sorted(glob.glob(os.path.join(A, 'renders', sid, 'idle', '*.png')))[0]).convert('RGBA')
        W = f0.width; m = round(W * (CAM - ICON) / 2 / CAM)
        save(f0.crop((m, m, W - m, W - m)).resize((400, 400), Image.LANCZOS), f'flat/{sid}.webp', q=90)
        print('sym', sid, flush=True)
    json.dump(man, open(os.path.join(G, 'sym', 'manifest.json'), 'w'))


def scene():
    plate = Image.open(os.path.join(A, 'scene', 'plate_lit.png')).convert('RGB')
    save(plate, 'bonus_wall.webp', q=86)
    meta = {'size': [3840, 2160], 'layers': {}}
    so = Image.open(os.path.join(A, 'scene', 'sign_off.png')).convert('RGBA')
    save(so, 'scene/sign_off.webp', q=88); meta['layers']['sign_off'] = {'rect': [0, 0, so.width, so.height]}
    for k, r in json.load(open(os.path.join(A, 'scene', 'blinks.json'))).items():
        save(Image.open(os.path.join(A, 'scene', f'blink_{k}.png')).convert('RGBA'), f'scene/blink_{k}.webp', q=90)
        meta['layers']['blink_' + k] = {'rect': r}
    for k, v in json.load(open(os.path.join(A, 'scene', 'fx', 'regions.json'))).items():
        fs = sorted(glob.glob(os.path.join(A, 'scene', 'fx', k, '*.png')))
        S = 0.5                                     # the plate shows at <= ~0.5 scale on screen
        frames = [Image.open(f).convert('RGBA') for f in fs]
        fw, fh = round(frames[0].width * S), round(frames[0].height * S)
        cols = max(1, int(4096 // fw)); rows = math.ceil(len(frames) / cols)
        # split into sheets of at most 4096 px tall
        per = cols * max(1, int(4096 // fh)); sheets = []
        for s0 in range(0, len(frames), per):
            chunk = frames[s0:s0 + per]; r = math.ceil(len(chunk) / cols)
            sh = Image.new('RGBA', (cols * fw, r * fh), (0, 0, 0, 0))
            for i, im in enumerate(chunk):
                sh.paste(im.resize((fw, fh), Image.LANCZOS), ((i % cols) * fw, (i // cols) * fh))
            sheets.append(os.path.basename(save(sh, f'scene/fx_{k}_{len(sheets)}.webp', q=80)))
        meta['layers']['fx_' + k] = {'rect': v['rect'], 'frames': len(frames), 'fps': 30, 'w': fw, 'h': fh, 'cols': cols, 'per_sheet': per, 'sheets': sheets}
    json.dump(meta, open(os.path.join(G, 'scene', 'scene.json'), 'w'), indent=1)
    print('scene packed')


if __name__ == '__main__':
    what = sys.argv[1:] or ['ui', 'symbols', 'scene']
    for w in what:
        {'ui': ui, 'symbols': symbols, 'scene': scene}[w]()
