"""The woman and her car gone from the scene (owner, 2026-11-12: "remove the girl and the car"): on all four plates
(the base game's night plate and the PREMIUM / NITRO / MIDNIGHT bonus scenes) the forecourt left of the pump is empty.
Run after remove_smoke.py and zombie_arm.py (they rewrite plate_lit / plate_zombie); this one always starts from the
plates as they were with her (kept as art/falcos/scene/plate_<n>.withgirl.png on the first run), so it can re-run.

    .venv/bin/python tools/falcos/remove_girl.py
    .venv/bin/python tools/falcos/compress_assets.py        (the 2560 plates + their _m twins)

The edits were made on a 1152 x 1728 crop of each 4K plate (art/falcos/work/nogirl/plate_<n>_crop.png, sent at
1024 x 1536: art/falcos/raw/nogirl_<n>.png - checked: no shift against the original). Only what the edit actually
changed inside a box round her and the car is blended back, with a soft edge; the pump, its bollards, the canopy and
everything right of them stay the original pixels. Her overlays (scene.json blink_woman, fx_arm) are gone with her.
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
BOX = (0, 432, 1152, 2160)              # the crop the edits were made on (plate px)
AREA = (0, 600, 840, 2160)              # where she, the car (and the NITRO flag) and their reflections were (plate px)
EDIT = 'nogirl_{}.png'
OUT = {'lit': 'bonus_wall.webp', 'zombie': 'scene/plate_zombie.webp',
       'nitro': 'scene/plate_nitro.webp', 'midnight': 'scene/plate_midnight.webp'}

for n, out in OUT.items():
    src = os.path.join(SC, f'plate_{n}.png')
    keep = os.path.join(SC, f'plate_{n}.withgirl.png')
    if not os.path.exists(keep):
        shutil.copyfile(src, keep)
    plate = Image.open(keep).convert('RGB')
    w, h = BOX[2] - BOX[0], BOX[3] - BOX[1]
    edit = Image.open(os.path.join(RAW, EDIT.format(n))).convert('RGB').resize((w, h), Image.LANCZOS)
    region = plate.crop(BOX)
    x0, y0, x1, y1 = (AREA[0] - BOX[0], AREA[1] - BOX[1], AREA[2] - BOX[0], AREA[3] - BOX[1])
    # the pixels the edit changed (the model's re-render noise elsewhere is a few levels: under the threshold)
    diff = np.abs(np.asarray(edit, np.int16) - np.asarray(region, np.int16)).max(axis=2) > 36
    diff = ndimage.binary_opening(diff, iterations=1)
    inbox = np.zeros_like(diff); inbox[y0:y1, x0:x1] = True
    m = ndimage.binary_closing(diff & inbox, iterations=6)
    m = ndimage.binary_fill_holes(ndimage.binary_dilation(m, iterations=10)) & inbox
    mask = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))
    region.paste(edit, (0, 0), mask)
    plate.paste(region, BOX[:2])
    plate.save(src)
    plate.save(os.path.join(F, out), 'WEBP', quality=95, method=4)   # full size: compress_assets.py makes 2560 + _m
    print(n, '->', os.path.relpath(src, ROOT), '+', out, f'({int(m.sum())} px blended)')
