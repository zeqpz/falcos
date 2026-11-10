"""Board look mockups (PIL): mock_board.py <frame.png> <out_prefix>
Draws the 7x5 board over the scene the way the new CSS will: rounded glass cell tiles, symbols at
~92% of a tile, tier tints on the tile for the high symbols; and the FILL UP board (fuel-window
tiles, big Fuel Drops with neon value labels, gauge)."""
import sys, os, random, json
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
A = os.path.join(ROOT, 'art', 'falcos')
FRAME, OUT = sys.argv[1], sys.argv[2]
W, H = 1920, 1080
plate = Image.open(os.path.join(A, 'scene', 'plate_lit.png')).convert('RGB').resize((W, H), Image.LANCZOS).convert('RGBA')

# board geometry (landscape): 7x5 cells
CW, CH, GAP = 128, 112, 8
BW, BH = 7 * CW + 6 * GAP, 5 * CH + 4 * GAP
BX, BY = (W - BW) // 2, 150


def tile(w, h, tint=None, kind='glass'):
    t = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=16, fill=255)
    g = np.zeros((h, w, 4), np.float32)
    yy = np.linspace(0, 1, h)[:, None]
    top, bot = (np.array([46, 52, 82]), np.array([16, 18, 34])) if kind == 'glass' else (np.array([40, 22, 14]), np.array([12, 8, 6]))
    col = top * (1 - yy) + bot * yy
    g[..., :3] = col[:, None, :] if col.ndim == 2 else col
    g[..., :3] = np.broadcast_to(col[:, None, :] if col.ndim == 2 else col, (h, w, 3))
    if tint:
        tc = np.array(tint, np.float32)
        cx, cy = w / 2, h * 0.55
        X, Y = np.meshgrid(np.arange(w), np.arange(h))
        r = np.sqrt(((X - cx) / (w * .6)) ** 2 + ((Y - cy) / (h * .6)) ** 2)
        k = np.clip(1 - r, 0, 1)[..., None] ** 1.5 * .55
        g[..., :3] = g[..., :3] * (1 - k) + tc * k
    g[..., 3] = 235
    t = Image.fromarray(g.clip(0, 255).astype(np.uint8)); t.putalpha(Image.fromarray((np.array(m) * .92).astype(np.uint8)))
    d = ImageDraw.Draw(t)
    d.rounded_rectangle([1, 1, w - 2, h - 2], radius=16, outline=(255, 255, 255, 38), width=2)
    d.rounded_rectangle([3, 3, w - 4, h // 2], radius=14, outline=None, fill=(255, 255, 255, 10))
    return t


TINT = {'H1': (210, 150, 30), 'H2': (200, 140, 40), 'H3': (190, 30, 40), 'H4': (40, 70, 200)}


def sym(sid, size):
    p = os.path.join(A, 'symbols_v2', sid + '.png')
    if not os.path.exists(p):
        p = os.path.join(A, 'symbols', sid + '.png')
    im = Image.open(p).convert('RGBA'); im = im.crop(im.getbbox()); im.thumbnail((size, size), Image.LANCZOS)
    sh = Image.new('RGBA', (im.width + 20, im.height + 20), (0, 0, 0, 0))
    a = im.split()[3].point(lambda v: v * .55)
    s = Image.new('RGBA', im.size, (0, 0, 0, 255)); s.putalpha(a); sh.alpha_composite(s, (14, 16)); sh = sh.filter(ImageFilter.GaussianBlur(5))
    sh.alpha_composite(im, (10, 10))
    return sh


def frame_layer():
    fr = Image.open(FRAME).convert('RGBA'); fr = fr.crop(fr.getbbox())
    a = np.array(fr.split()[3]); hh, ww = a.shape; cy, cx = hh // 2, ww // 2
    l = next(i for i in range(cx, 0, -1) if a[cy, i] > 128); r = next(i for i in range(cx, ww) if a[cy, i] > 128)
    t = next(i for i in range(int(hh * .45), 0, -1) if a[i, int(ww * .2)] > 128); b = next(i for i in range(cy, hh) if a[i, int(ww * .2)] > 128)
    pad = 18
    sx = (BW + 2 * pad) / (r - l); sy = (BH + 2 * pad) / (b - t)
    fr = fr.resize((round(ww * sx), round(hh * sy)), Image.LANCZOS)
    return fr, (BX - pad - round(l * sx), BY - pad - round(t * sy))


def base_board():
    img = plate.copy()
    dim = Image.new('RGBA', (BW + 40, BH + 40), (0, 0, 0, 0)); ImageDraw.Draw(dim).rounded_rectangle([0, 0, BW + 39, BH + 39], 24, fill=(8, 10, 22, 246))
    img.alpha_composite(dim, (BX - 20, BY - 20))
    return img


rng = random.Random(7)
# --- base game board
img = base_board()
ids = ['H1', 'H2', 'H3', 'H4', 'L1', 'L2', 'L3', 'L4', 'L5']
wts = [2, 3, 4, 5, 8, 9, 10, 11, 12]
grid = [[rng.choices(ids, wts)[0] for _ in range(5)] for _ in range(7)]
for c in range(7):
    for r in range(5):
        x, y = BX + c * (CW + GAP), BY + r * (CH + GAP)
        s = grid[c][r]
        img.alpha_composite(tile(CW, CH, TINT.get(s)), (x, y))
        sp = sym(s, int(CH * .96))
        img.alpha_composite(sp, (x + (CW - sp.width) // 2, y + (CH - sp.height) // 2 - 2))
fr, pos = frame_layer(); img.alpha_composite(fr, pos)
img.convert('RGB').save(OUT + '_board.jpg', quality=90)

# --- FILL UP board
img = base_board()
fd = {'FDG': [0.2, 0.5, 1, 2, 3], 'FDA': [5, 10, 15, 20], 'FDR': [50, 100]}
font = None
for f in ['/System/Library/Fonts/Supplemental/Arial Black.ttf', '/System/Library/Fonts/Supplemental/Impact.ttf', '/Library/Fonts/Arial Bold.ttf']:
    if os.path.exists(f):
        font = ImageFont.truetype(f, 30); break
for c in range(7):
    for r in range(5):
        x, y = BX + c * (CW + GAP), BY + r * (CH + GAP)
        roll = rng.random()
        if roll < .42:
            k = rng.choices(list(fd), [6, 3, 1])[0]; v = rng.choice(fd[k])
            img.alpha_composite(tile(CW, CH, {'FDG': (60, 200, 60), 'FDA': (230, 150, 20), 'FDR': (220, 30, 40)}[k], 'fuel'), (x, y))
            sp = sym(k, int(CH * .82)); img.alpha_composite(sp, (x + (CW - sp.width) // 2, y + 2))
            d = ImageDraw.Draw(img); txt = (f'x{v:g}')
            tw = d.textlength(txt, font=font)
            for o in ((2, 2), (-2, 2), (2, -2), (-2, -2), (0, 3)):
                d.text((x + (CW - tw) / 2 + o[0], y + CH - 40 + o[1]), txt, font=font, fill=(20, 8, 4))
            d.text((x + (CW - tw) / 2, y + CH - 40), txt, font=font, fill=(255, 240, 200))
        elif roll < .47:
            s = rng.choice(['ST', 'ZP', 'GP'])
            img.alpha_composite(tile(CW, CH, (230, 150, 20), 'fuel'), (x, y))
            sp = sym(s, int(CH * .9)); img.alpha_composite(sp, (x + (CW - sp.width) // 2, y + (CH - sp.height) // 2))
        else:
            t = tile(CW, CH, None, 'fuel'); img.alpha_composite(t, (x, y))
            d = ImageDraw.Draw(img); d.ellipse([x + CW / 2 - 9, y + CH / 2 - 9, x + CW / 2 + 9, y + CH / 2 + 9], outline=(120, 70, 30, 255), width=3)
fr, pos = frame_layer(); img.alpha_composite(fr, pos)
# gauge + total under the board
d = ImageDraw.Draw(img)
gx, gy = W // 2 - 160, BY + BH + 46
for i in range(3):
    d.rounded_rectangle([gx + i * 110, gy, gx + i * 110 + 100, gy + 30], 8, fill=(255, 181, 71) if i < 2 else (60, 40, 30), outline=(255, 226, 168), width=2)
img.convert('RGB').save(OUT + '_fillup.jpg', quality=90)
print('ok')
