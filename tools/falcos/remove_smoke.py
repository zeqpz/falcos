"""No smoking in the scene (owner, 2026-11-10, compliance): the woman's cigarette (and, on the zombie plate, its
painted smoke) replaced by a takeaway coffee cup in the same raised hand.

    .venv/bin/python tools/falcos/remove_smoke.py

The edits were made on a 640 x 640 crop of each 4K plate (art/falcos/work/nosmoke/plate_*_crop.png, sent to the
image model at 1024: art/falcos/raw/nosmoke_{lit,zombie}.png, then the cup made bigger in .v2 - checked: no shift
against the original). Only what the edit actually changed inside a box round her hand - the hand, the cup and the
air where the cigarette and smoke were - is blended back, with a soft edge; her face stays the original pixels, so
the blinking-eyes overlay (scene.json blink_woman) still sits on it. The originals
are kept as art/falcos/scene/plate_{lit,zombie}.smoking.png. Then the game's plates are written at full size for
compress_assets.py to shrink (bonus_wall.webp, scene/plate_zombie.webp and their _m twins).
"""
import os
import shutil
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SC = os.path.join(ROOT, 'art', 'falcos', 'scene')
RAW = os.path.join(ROOT, 'art', 'falcos', 'raw')
F = os.path.join(ROOT, 'frontend', 'assets')
BOX = (400, 640, 1040, 1280)            # the crop the edits were made on (plate px)
PATCH = {                               # plate px boxes the change may lie in: hand, cigarette, cup (+ the zombie smoke)
    'lit': (536, 840, 700, 1070),
    'zombie': (536, 720, 710, 1070),
}
EDIT = 'nosmoke_{}.v2.png'              # the latest edit (the bigger cup)
FORCE = {'zombie': (575, 725, 705, 950)}  # the zombie plate's painted smoke: taken whole (its faint edges under the threshold)
OUT = {'lit': 'bonus_wall.webp', 'zombie': 'scene/plate_zombie.webp'}

for n, rect in PATCH.items():
    src = os.path.join(SC, f'plate_{n}.png')
    keep = os.path.join(SC, f'plate_{n}.smoking.png')
    if not os.path.exists(keep):
        shutil.copyfile(src, keep)
    plate = Image.open(keep).convert('RGB')
    w, h = BOX[2] - BOX[0], BOX[3] - BOX[1]
    edit = Image.open(os.path.join(RAW, EDIT.format(n))).convert('RGB').resize((w, h), Image.LANCZOS)
    region = plate.crop(BOX)
    x0, y0, x1, y1 = (rect[0] - BOX[0], rect[1] - BOX[1], rect[2] - BOX[0], rect[3] - BOX[1])
    # the pixels the edit changed (the model's re-render noise elsewhere is a few levels: under the threshold)
    diff = np.abs(np.asarray(edit, np.int16) - np.asarray(region, np.int16)).max(axis=2) > 36
    diff = ndimage.binary_opening(diff, iterations=1)
    inbox = np.zeros_like(diff); inbox[y0:y1, x0:x1] = True
    m = ndimage.binary_closing(diff & inbox, iterations=4)
    m = ndimage.binary_fill_holes(ndimage.binary_dilation(m, iterations=7)) & inbox
    if n in FORCE:
        fx0, fy0, fx1, fy1 = (FORCE[n][0] - BOX[0], FORCE[n][1] - BOX[1], FORCE[n][2] - BOX[0], FORCE[n][3] - BOX[1])
        m[fy0:fy1, fx0:fx1] = True
    mask = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(4))
    region.paste(edit, (0, 0), mask)
    plate.paste(region, BOX[:2])
    plate.save(src)
    plate.save(os.path.join(F, OUT[n]), 'WEBP', quality=95, method=4)   # full size: compress_assets.py makes 2560 + _m
    print(n, '->', os.path.relpath(src, ROOT), '+', OUT[n])
