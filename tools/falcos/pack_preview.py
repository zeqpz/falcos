"""Pack the Falcos art into a local preview page: art/falcos/previews/showcase/ (index.html + webp).

  .venv/bin/python tools/falcos/pack_preview.py      then serve the project root and open
  /art/falcos/previews/showcase/index.html
"""
import os, json, glob
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
A = os.path.join(ROOT, 'art', 'falcos')
OUT = os.path.join(A, 'previews', 'showcase')
os.makedirs(OUT, exist_ok=True)
S = 0.5                                     # scene preview scale (the plate shows at about half size)


def latest(n):
    c = [f for f in os.listdir(os.path.join(A, 'raw')) if f == n + '.png' or (f.startswith(n + '.v') and f.endswith('.png'))]
    return os.path.join(A, 'raw', sorted(c, key=lambda f: (len(f), f))[-1]) if c else None


def anim_webp(frames, out, size=None, scale=None, fps=30):
    ims = []
    for f in frames:
        im = Image.open(f).convert('RGBA')
        if size:
            im = im.resize((size, size), Image.LANCZOS)
        if scale:
            im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
        ims.append(im)
    ims[0].save(out, save_all=True, append_images=ims[1:], duration=round(1000 / fps), loop=0, quality=82, method=4)


data = {'symbols': {}, 'scene': {}, 'ui': []}
# scene
plate = Image.open(os.path.join(A, 'scene', 'plate_lit.png')).convert('RGB')
plate.resize((round(3840 * S), round(2160 * S)), Image.LANCZOS).save(os.path.join(OUT, 'plate.webp'), quality=88)
so = Image.open(os.path.join(A, 'scene', 'sign_off.png'))
so.resize((round(so.width * S), round(so.height * S)), Image.LANCZOS).save(os.path.join(OUT, 'sign_off.webp'), quality=88)
data['scene']['sign_off'] = [0, 0, so.width, so.height]
for k, r in json.load(open(os.path.join(A, 'scene', 'blinks.json'))).items():
    im = Image.open(os.path.join(A, 'scene', f'blink_{k}.png'))
    im.resize((round(im.width * S), round(im.height * S)), Image.LANCZOS).save(os.path.join(OUT, f'blink_{k}.webp'), quality=90)
    data['scene']['blink_' + k] = r
reg = os.path.join(A, 'scene', 'fx', 'regions.json')
if os.path.exists(reg):
    for k, v in json.load(open(reg)).items():
        fs = sorted(glob.glob(os.path.join(A, 'scene', 'fx', k, '*.png')))
        if len(fs) >= v['frames']:
            anim_webp(fs, os.path.join(OUT, f'fx_{k}.webp'), scale=S)
            data['scene']['fx_' + k] = v['rect']
# symbols
for sid in ['H1', 'H2', 'H3', 'H4', 'L1', 'L2', 'L3', 'L4', 'L5', 'ZP', 'ST', 'GT', 'GP', 'FDG', 'FDA', 'FDR', 'BS', 'DS']:
    clips = {}
    for clip in ('idle', 'land', 'hit', 'burn'):
        fs = sorted(glob.glob(os.path.join(A, 'renders', sid, clip, '*.png')))
        want = {'idle': 72, 'land': 24, 'hit': 46, 'burn': 36}[clip]
        if len(fs) == want:
            anim_webp(fs, os.path.join(OUT, f'{sid}_{clip}.webp'), size=256)
            clips[clip] = len(fs)
    data['symbols'][sid] = clips
# ui
for n in ['title_logo', 'big_win', 'mega_win', 'epic_win', 'total_win', 'tier_bg', 'total_bg', 'bonus_btn_text', 'bonus_btn_bg',
          'logo_fillup', 'logo_premium', 'logo_midnight', 'bonus_panel', 'info_panel', 'feature_box', 'win_box', 'banner_box',
          'ui_box', 'banner_chance', 'banner_fillup', 'banner_premium', 'banner_nitro', 'banner_midnight',
          'intro_word', 'intro_swash', 'intro_seal'] + [f'num_{c}' for c in '0123456789'] + ['num_dot', 'num_comma', 'num_x']:
    p = latest(n)
    if not p:
        continue
    im = Image.open(p).convert('RGBA')
    bb = im.getbbox()
    if bb and not n.startswith('num'):
        im = im.crop(bb)
    im.thumbnail((900, 900), Image.LANCZOS)
    im.save(os.path.join(OUT, f'ui_{n}.webp'), quality=88)
    data['ui'].append(n)
json.dump(data, open(os.path.join(OUT, 'data.json'), 'w'), indent=1)
print(json.dumps({k: (len(v) if not isinstance(v, dict) else {kk: vv for kk, vv in v.items()}) for k, v in data.items()})[:900])
