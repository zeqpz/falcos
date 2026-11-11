"""Small idle motion for the people in the night scene (owner, 2026-11-10: "make the girl with the coffee move her
arms a little bit ... make the two people inside the gas station have small animations nothing too crazy").

    .venv/bin/python tools/falcos/scene_idle.py      -> frontend/assets/scene/fx_arm_0.webp, fx_people_0.webp (+ scene.json)

No new drawing: each loop is the plate itself (art/falcos/scene/plate_lit.png), gently warped frame by frame - a smooth
displacement field that is strongest on the moving part and fades to nothing around it, so the background stays put
and nothing tears. The frame's edges fade out (alpha), so the loop melts into the still plate with no seam:
  fx_arm     her raised coffee arm sways a couple of degrees about the elbow, always away from her face, and lifts a
             touch - her face is left exactly as it is (the blink overlay sits on it)
  fx_people  the cashier breathes (shoulders up a pixel or two) and his hands move a little - the coins, the receipt;
             the customer breathes, tilts his head a hair and his open hand rises and falls
Each is a 4 s loop at 12 fps, written as a grid sheet in the format scenefx.js plays (scene.json: rect in plate px,
frames, fps, w, h, cols, per_sheet, sheets); fx_people is drawn under fx_cashier's glass reflection.
"""
import json, math, os
import numpy as np
import cv2
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLATE = os.path.join(ROOT, 'art', 'falcos', 'scene', 'plate_lit.png')
OUT = os.path.join(ROOT, 'frontend', 'assets', 'scene')
FPS, SECS = 12, 4.0
N = int(FPS * SECS)
TAU = 2 * math.pi


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def ellipse_w(X, Y, cx, cy, rx, ry, fall):
    """1 inside the ellipse, easing to 0 over `fall` px outside it"""
    d = np.sqrt(((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2)          # 1 on the rim
    out = (d - 1) * min(rx, ry)                                          # ~px outside the rim
    return 1 - smooth(0, fall, out)


def rotate_disp(X, Y, px, py, ang):
    """where each point goes rotated by `ang` (radians, + = clockwise on screen) about (px, py): its displacement"""
    c, s = math.cos(ang), math.sin(ang)
    dx, dy = X - px, Y - py
    return (c * dx - s * dy) - dx, (s * dx + c * dy) - dy


def render(name, rect, scale, motion):
    x, y, w, h = rect
    pad = 24
    src = np.asarray(Image.open(PLATE).convert('RGB').crop((x - pad, y - pad, x + w + pad, y + h + pad)), np.float32)
    X, Y = np.meshgrid(np.arange(w, dtype=np.float32) + x, np.arange(h, dtype=np.float32) + y)
    edge = np.minimum.reduce([X - x, x + w - 1 - X, Y - y, y + h - 1 - Y])
    alpha = smooth(0, 14, edge)                                          # melt into the plate at the rect's edge
    fw, fh = round(w * scale), round(h * scale)
    frames = []
    for i in range(N):
        t = i / N
        dx, dy = motion(X, Y, t)
        # inverse map: the output pixel shows what sat where it came from (small fields: -disp is close enough)
        mx = (X - dx - x + pad).astype(np.float32); my = (Y - dy - y + pad).astype(np.float32)
        warped = cv2.remap(src, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        rgba = np.dstack([np.clip(warped, 0, 255), alpha * 255]).astype(np.uint8)
        frames.append(Image.fromarray(rgba).resize((fw, fh), Image.LANCZOS))
    cols = max(1, min(N, 4096 // fw))
    rows = math.ceil(N / cols)
    sheet = Image.new('RGBA', (cols * fw, rows * fh), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        sheet.paste(f, ((i % cols) * fw, (i // cols) * fh))
    sheet.save(os.path.join(OUT, f'{name}_0.webp'), 'WEBP', quality=86, alpha_quality=90, method=6)
    return {'rect': [x, y, w, h], 'frames': N, 'fps': FPS, 'w': fw, 'h': fh, 'cols': cols, 'per_sheet': N,
            'sheets': [f'{name}_0.webp']}


def arm(X, Y, t):
    # her forearm, hand and cup: rotate about the elbow (600, 1112), 0 .. 2.4 deg clockwise (away from her face),
    # with a little lift; the face (x < 552) and the elbow itself stay still
    ang = math.radians(1.2 + 1.2 * math.sin(TAU * t) + .35 * math.sin(2 * TAU * t + 1.1))
    lift = -2.2 * (.5 - .5 * math.cos(TAU * t + .6))
    wgt = ellipse_w(X, Y, 590, 955, 62, 118, 46) * smooth(1112, 1030, Y) * smooth(546, 560, X)
    dx, dy = rotate_disp(X, Y, 600, 1112, ang)
    return dx * wgt, (dy + lift) * wgt


def people(X, Y, t):
    dx = np.zeros_like(X); dy = np.zeros_like(Y)
    # the cashier breathes twice a loop: from the counter (1205) up, the shoulders rise ~1.8 px; the head goes along
    br = .5 - .5 * math.cos(2 * TAU * t)
    body = ellipse_w(X, Y, 3220, 1060, 150, 190, 40) * smooth(1205, 1040, Y)
    dy += -1.8 * br * body
    # his hands: the receipt hand sways sideways, the coin hand bobs
    dx += 3.0 * math.sin(2 * TAU * t + .4) * ellipse_w(X, Y, 3410, 1150, 46, 42, 34)
    dy += 1.8 * math.sin(2 * TAU * t + 1.7) * ellipse_w(X, Y, 3305, 1172, 52, 34, 30)
    # the customer: one slow breath, a hair of head tilt about his neck, his open hand rising and falling
    br2 = .5 - .5 * math.cos(TAU * t + 2.0)
    cbody = ellipse_w(X, Y, 3650, 1230, 150, 200, 40) * smooth(1390, 1080, Y)
    dy += -2.0 * br2 * cbody
    head = ellipse_w(X, Y, 3612, 985, 88, 98, 36)
    hx, hy = rotate_disp(X, Y, 3600, 1075, math.radians(1.1 * math.sin(TAU * t + .3)))
    dx += hx * head; dy += hy * head + (-2.0 * br2 * head)
    dy += 2.6 * math.sin(TAU * t + 2.6) * ellipse_w(X, Y, 3470, 1222, 52, 36, 32)
    return dx, dy


if __name__ == '__main__':
    sp = os.path.join(OUT, 'scene.json')
    cfg = json.load(open(sp))
    arm_l = render('fx_arm', (520, 792, 196, 336), .67, arm)        # the desktop plate's own scale (2560 / 3840)
    ppl_l = render('fx_people', (3060, 850, 760, 545), .62, people)   # a phone decodes it smaller (scenefx)
    layers = {}
    for k, v in cfg['layers'].items():
        if k == 'fx_cashier':                  # the people under the glass reflection
            layers['fx_people'] = ppl_l
        if k not in ('fx_people', 'fx_arm'):
            layers[k] = v
    layers['fx_arm'] = arm_l
    cfg['layers'] = layers
    json.dump(cfg, open(sp, 'w'), indent=1)
    for n in ('fx_arm', 'fx_people'):
        print(n, os.path.getsize(os.path.join(OUT, n + '_0.webp')) // 1024, 'KB', cfg['layers'][n]['w'], 'x', cfg['layers'][n]['h'], 'x', N)
