"""No smoking in the scene (owner, 2026-11-10, compliance): the woman's cigarette (and, on the zombie plate, its
painted smoke) replaced by a takeaway coffee cup in the same raised hand.

    .venv/bin/python tools/falcos/remove_smoke.py

The edits were made on a 640 x 640 crop of each 4K plate (art/falcos/work/nosmoke/plate_*_crop.png, sent to the
image model at 1024: art/falcos/raw/nosmoke_{lit,zombie}.png - checked: no shift against the original). Only her
hand, the cup and the air where the cigarette and smoke were are blended back, with a soft edge - her face stays
the original pixels, so the blinking-eyes overlay (scene.json blink_woman) still sits on it exactly. The originals
are kept as art/falcos/scene/plate_{lit,zombie}.smoking.png. Then the game's plates are written at full size for
compress_assets.py to shrink (bonus_wall.webp, scene/plate_zombie.webp and their _m twins).
"""
import os
import shutil
import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SC = os.path.join(ROOT, 'art', 'falcos', 'scene')
RAW = os.path.join(ROOT, 'art', 'falcos', 'raw')
F = os.path.join(ROOT, 'frontend', 'assets')
BOX = (400, 640, 1040, 1280)            # the crop the edits were made on (plate px)
PATCH = {                               # plate px rectangles: hand + cigarette + cup (+ the zombie plate's smoke)
    'lit': (560, 860, 690, 1066),
    'zombie': (560, 730, 700, 1066),
}
OUT = {'lit': 'bonus_wall.webp', 'zombie': 'scene/plate_zombie.webp'}

for n, rect in PATCH.items():
    src = os.path.join(SC, f'plate_{n}.png')
    keep = os.path.join(SC, f'plate_{n}.smoking.png')
    if not os.path.exists(keep):
        shutil.copyfile(src, keep)
    plate = Image.open(keep).convert('RGB')
    w, h = BOX[2] - BOX[0], BOX[3] - BOX[1]
    edit = Image.open(os.path.join(RAW, f'nosmoke_{n}.png')).convert('RGB').resize((w, h), Image.LANCZOS)
    mask = Image.new('L', (w, h), 0)
    x0, y0, x1, y1 = (rect[0] - BOX[0], rect[1] - BOX[1], rect[2] - BOX[0], rect[3] - BOX[1])
    m = np.zeros((h, w), np.uint8); m[y0:y1, x0:x1] = 255
    mask = Image.fromarray(m).filter(ImageFilter.GaussianBlur(9))
    region = plate.crop(BOX)
    region.paste(edit, (0, 0), mask)
    plate.paste(region, BOX[:2])
    plate.save(src)
    plate.save(os.path.join(F, OUT[n]), 'WEBP', quality=95, method=4)   # full size: compress_assets.py makes 2560 + _m
    print(n, '->', os.path.relpath(src, ROOT), '+', OUT[n])
